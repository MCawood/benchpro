"""Local executor for running tasks on the local machine."""

import asyncio
import subprocess
import psutil
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import os

from benchpro.core.domain.task import Task, TaskState
from benchpro.core.domain.job import Job, JobState
from benchpro.core.services.logging import get_logger
from benchpro.core.domain.errors import ResourceError, TaskExecutionError
from benchpro.core.domain.staging import StagingMode
from benchpro.core.services.settings import Settings
from benchpro.core.services.staging import FileStager

logger = get_logger("executor")

class LocalExecutor:
    """Local task executor."""

    def __init__(self):
        """Initialize local executor."""
        logger.debug("Initializing LocalExecutor")
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._monitors: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(1)  # Default to 1 concurrent task
        self._settings = Settings()
        self.file_stager = FileStager()
        logger.debug("LocalExecutor initialized with semaphore=%s", self._semaphore._value)

    async def validate_resources(self, job: Job) -> None:
        """Validate that sufficient resources are available."""
        # Check CPU cores
        available_cores = psutil.cpu_count()
        requested_cores = job.resources.get("cores", 1)
        if requested_cores > available_cores:
            raise ResourceError(f"Requested {requested_cores} cores but only {available_cores} available")

        # Check memory
        memory = psutil.virtual_memory()
        requested_memory = job.resources.get("memory", "1G")
        requested_bytes = self._parse_memory(requested_memory)
        if requested_bytes > memory.available:
            raise ResourceError(f"Requested {requested_memory} but only {memory.available / (1024**3):.1f}G available")

    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to bytes.
        
        Args:
            memory_str: Memory string (e.g., "1G", "512M")
            
        Returns:
            Number of bytes
        """
        units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
        value = float(memory_str[:-1])
        unit = memory_str[-1].upper()
        return int(value * units[unit])

    async def submit_job(self, job: Job) -> None:
        """Submit a job for execution.
        
        Args:
            job: Job to execute
            
        Raises:
            TaskExecutionError: If job execution fails
        """
        try:
            # Validate resources
            await self.validate_resources(job)
            
            # Transition job to QUEUED state
            job.transition_to(JobState.QUEUED)
            
            # Transition to RUNNING before starting tasks
            job.transition_to(JobState.RUNNING)
            
            # Execute tasks sequentially
            task_error = None
            for task in job.tasks:
                try:
                    async with self._semaphore:
                        await self._execute_task(task)
                except Exception as e:
                    task_error = e
                    break

            # If we had any task failures, transition job to FAILED and raise the error
            if task_error is not None:
                # Only transition to FAILED if not in a terminal state
                if job.state not in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
                    job.transition_to(JobState.FAILED, str(task_error))
                if isinstance(task_error, TaskExecutionError):
                    raise task_error
                raise TaskExecutionError(f"Job failed: {str(task_error)}")

            # If we get here, all tasks completed successfully
            job.transition_to(JobState.COMPLETED)

        except asyncio.CancelledError:
            # Handle cancellation at the job level
            if job.state not in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
                job.transition_to(JobState.CANCELLED)
            raise

        except Exception as e:
            # Only transition to FAILED if we're in a non-terminal state
            if job.state not in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
                job.transition_to(JobState.FAILED, str(e))
            # Re-raise TaskExecutionError or wrap other exceptions
            if isinstance(e, TaskExecutionError):
                raise e
            raise TaskExecutionError(f"Job failed: {str(e)}")

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        try:
            # Stage files
            logger.debug("Task %s: Starting file staging...", task.id)
            await self.prepare(task)

            # Transition to RUNNING
            logger.debug("Task %s: Starting task execution...", task.id)
            task.transition_to(TaskState.RUNNING)

            # Verify run script exists
            run_script = task.working_dir / "run.sh"
            if not run_script.exists():
                logger.error("Task %s: Run script not found at %s", task.id, run_script)
                raise TaskExecutionError("Run script not found in working directory")
            logger.debug("Task %s: Found run script at %s", task.id, run_script)

            # Start process
            logger.debug("Task %s: Starting process with script: %s", task.id, run_script)
            process = await asyncio.create_subprocess_exec(
                'bash',
                str(run_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(task.working_dir),
                env=os.environ.copy()
            )

            self._processes[task.name] = process
            logger.debug("Task %s: Process started with PID %s", task.id, process.pid)

            # Start monitoring
            monitor = asyncio.create_task(self._monitor_task(task))
            self._monitors[task.name] = monitor
            logger.debug("Task %s: Started monitoring task", task.id)

            # Wait for completion
            logger.debug("Task %s: Waiting for process completion...", task.id)
            stdout, stderr = await process.communicate()
            logger.debug("Task %s: Process completed with return code: %s", task.id, process.returncode)

            # Handle process exit
            if process.returncode == 0:
                logger.debug("Task %s: Task completed successfully", task.id)
                task.transition_to(TaskState.COMPLETED)
            elif process.returncode == -15:  # SIGTERM
                logger.debug("Task %s: Task was terminated", task.id)
                task.transition_to(TaskState.CANCELLED)
                raise asyncio.CancelledError("Task was terminated")
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error("Task %s: Task failed: %s", task.id, error_msg)
                full_error = f"Task failed with exit code {process.returncode}: {error_msg}"
                task.transition_to(TaskState.FAILED, full_error)
                raise TaskExecutionError(full_error)

        except asyncio.CancelledError:
            # Handle cancellation
            logger.debug("Task %s: Task was cancelled", task.id)
            if task.state not in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                task.transition_to(TaskState.CANCELLED)
            raise

        except Exception as e:
            # Only transition to FAILED if we're not in a terminal state
            logger.error("Task %s: Task failed with error: %s", task.id, str(e))
            if task.state not in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                task.transition_to(TaskState.FAILED, str(e))
            raise TaskExecutionError(f"Failed to execute task: {str(e)}")

    async def _monitor_task(self, task: Task) -> None:
        """Monitor a running task."""
        process = self._processes.get(task.name)
        if not process:
            return

        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise

    async def status(self, task: Task) -> TaskState:
        """Get task status."""
        process = self._processes.get(task.name)
        if not process:
            return task.state

        if process.returncode is None:
            if task.state != TaskState.RUNNING:
                # Transition to RUNNING through PENDING if needed
                if task.state == TaskState.CREATED:
                    task.transition_to(TaskState.PENDING)
                if task.state == TaskState.PENDING:
                    task.transition_to(TaskState.RUNNING)
            return TaskState.RUNNING
        elif process.returncode == 0:
            if task.state != TaskState.COMPLETED:
                # Transition to COMPLETED through proper states
                if task.state == TaskState.CREATED:
                    task.transition_to(TaskState.PENDING)
                if task.state == TaskState.PENDING:
                    task.transition_to(TaskState.RUNNING)
                if task.state == TaskState.RUNNING:
                    task.transition_to(TaskState.COMPLETED)
            return TaskState.COMPLETED
        else:
            # Failed state can be reached from any state
            if task.state != TaskState.FAILED:
                task.transition_to(TaskState.FAILED, f"Process exited with code {process.returncode}")
            return TaskState.FAILED

    async def stop(self, task: Task) -> None:
        """Stop a running task.

        Args:
            task: The task to stop
        """
        process = self._processes.get(task.name)
        if process:
            process.terminate()
            await process.wait()
            task.transition_to(TaskState.CANCELLED)

    async def cleanup(self, task: Task) -> None:
        """Clean up task resources."""
        if task.name in self._processes:
            del self._processes[task.name]
        if task.name in self._monitors:
            del self._monitors[task.name]

    async def get_job_status(self, job: Job) -> Dict[str, Any]:
        """Get job status."""
        status = {
            "state": job.state,
            "tasks": {
                "total": len(job.tasks),
                "completed": sum(1 for t in job.tasks if t.state == TaskState.COMPLETED),
                "running": sum(1 for t in job.tasks if t.state == TaskState.RUNNING),
                "failed": sum(1 for t in job.tasks if t.state == TaskState.FAILED),
                "cancelled": sum(1 for t in job.tasks if t.state == TaskState.CANCELLED)
            }
        }
        return status

    async def get_resource_usage(self, job: Job) -> Dict[str, Any]:
        """Get resource usage for a job."""
        return {
            "cores": job.resources.get("cores", 1),
            "memory": job.resources.get("memory", "1G"),
            "walltime": job.resources.get("walltime", 3600)
        }

    async def prepare(self, task: Task) -> None:
        """Prepare task for execution by staging files.
        
        Args:
            task: The task to prepare
            
        Raises:
            TaskExecutionError: If staging fails
        """
        try:
            logger.debug("Task %s: Creating working directory at %s", task.id, task.working_dir)
            task.working_dir.mkdir(parents=True, exist_ok=True)
            
            # Stage files (including template if provided)
            logger.debug("Task %s: Starting file staging with %d files", task.id, len(task.staging_files))
            task.transition_to(TaskState.STAGING)
            await self.file_stager.stage_files(task)
            task.transition_to(TaskState.PENDING)
            
            # Make run.sh executable if it exists
            run_script = task.working_dir / "run.sh"
            if run_script.exists():
                logger.debug("Task %s: Making run script executable: %s", task.id, run_script)
                os.chmod(run_script, 0o755)  # Make executable
            else:
                logger.warning("Task %s: Run script not found at %s", task.id, run_script)
                
        except Exception as e:
            logger.error("Task %s: Failed to prepare task: %s", task.id, str(e))
            task.transition_to(TaskState.FAILED, str(e))
            raise TaskExecutionError(f"Failed to prepare task: {str(e)}")

    async def cleanup_job(self, job: Job) -> None:
        """Clean up job resources.

        Args:
            job: The job to clean up
        """
        for task in job.tasks:
            await self.cleanup(task)

    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job.

        Args:
            job: The job to cancel
        """
        # First transition job to CANCELLED to prevent new tasks from starting
        job.transition_to(JobState.CANCELLED)

        # Stop all running tasks
        for task in job.tasks:
            if task.state == TaskState.RUNNING:
                await self.stop(task)
            elif task.state not in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                task.transition_to(TaskState.CANCELLED)

        # Clean up resources
        await self.cleanup_job(job) 

    async def run(self, task: Task) -> None:
        """Run a task.
        
        Args:
            task: The task to run
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        try:
            # Create a job with just this task
            job = Job(
                name=task.name,
                tasks=[task],
                resources=task.variables,
                working_dir=task.working_dir
            )
            
            # Submit the job
            await self.submit_job(job)
            
        except Exception as e:
            raise TaskExecutionError(f"Failed to run task: {str(e)}") 