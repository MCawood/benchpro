"""Process management for local task execution.

This module provides process management functionality for local task execution,
including process creation, monitoring, and cleanup.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

from benchpro.core.domain import Task, TaskState, Job, JobState
from benchpro.core.executor.base import TaskExecutionError, ExecutorError

logger = logging.getLogger(__name__)

class ProcessManager:
    """Manages processes for local task execution.
    
    This class handles process lifecycle including:
    - Process creation and execution
    - Process monitoring
    - Process cleanup and termination
    """
    
    def __init__(self) -> None:
        """Initialize the process manager."""
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._monitors: Dict[str, asyncio.Task] = {}
        
    async def execute_task(self, task: Task, job: Job, working_dir: Path) -> None:
        """Execute a task.

        Args:
            task: Task to execute
            job: Parent job
            working_dir: Working directory for task execution

        Raises:
            TaskExecutionError: If task execution fails
        """
        if not task.template_path or not task.template_path.exists():
            error_msg = f"Template path does not exist: {task.template_path}"
            task.transition_to(TaskState.FAILED, error_msg)
            job.state = JobState.FAILED
            job.completed_at = datetime.now()
            raise TaskExecutionError(error_msg)

        try:
            # Ensure task is in PENDING state before running
            if task.state == TaskState.CREATED:
                task.transition_to(TaskState.PENDING)

            process = await asyncio.create_subprocess_exec(
                str(task.template_path),
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Store process
            self._processes[job.id] = process
            
            # Update states
            task.transition_to(TaskState.RUNNING)
            job.state = JobState.RUNNING
            
            try:
                # Wait for completion
                stdout, stderr = await process.communicate()
            except asyncio.CancelledError:
                task.transition_to(TaskState.CANCELLED)
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                raise
            
            # Check return code
            if process.returncode == 0:
                task.transition_to(TaskState.COMPLETED)
                # Only set job to completed if all tasks are completed
                if all(t.state == TaskState.COMPLETED for t in job.tasks):
                    job.state = JobState.COMPLETED
                    job.completed_at = datetime.now()
            elif process.returncode == -15:  # SIGTERM
                task.transition_to(TaskState.CANCELLED)
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                raise asyncio.CancelledError()
            else:
                error_msg = f"Task failed with exit code {process.returncode}: {stderr.decode().strip()}"
                task.transition_to(TaskState.FAILED, error_msg)
                job.state = JobState.FAILED
                job.completed_at = datetime.now()
                raise TaskExecutionError(error_msg)
            
        except Exception as e:
            if not isinstance(e, (TaskExecutionError, asyncio.CancelledError)):
                error_msg = f"Task execution failed: {str(e)}"
                task.transition_to(TaskState.FAILED, error_msg)
                job.state = JobState.FAILED
                job.completed_at = datetime.now()
                raise TaskExecutionError(error_msg)
            raise
        finally:
            # Cleanup process
            if job.id in self._processes:
                del self._processes[job.id]
            
    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job.
        
        Args:
            job: The job to cancel
        """
        logger.debug("Cancelling job %s", job.name)

        # Get process for job
        process = self._processes.get(job.id)
        if process is None:
            logger.warning("No process found for job %s", job.id)
            return

        # Cancel any monitors
        monitor = self._monitors.get(job.id)
        if monitor:
            monitor.cancel()
            del self._monitors[job.id]

        # Terminate process if still running
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            del self._processes[job.id]
            
        # Update job state
        job.state = JobState.CANCELLED
        job.completed_at = datetime.now()
        for task in job.tasks:
            task.transition_to(TaskState.CANCELLED)
            
    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Get the process for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            The process if found, None otherwise
        """
        return self._processes.get(task_id)
        
    def remove_process(self, task_id: str) -> None:
        """Remove a process from tracking.
        
        Args:
            task_id: ID of the task whose process should be removed
        """
        if task_id in self._processes:
            del self._processes[task_id]
            logger.debug("Removed process for task %s", task_id)
            
        if task_id in self._monitors:
            del self._monitors[task_id]
            logger.debug("Removed monitor for task %s", task_id)

    async def cancel_task(self, task: Task) -> None:
        """Cancel a running task.

        Args:
            task: The task to cancel

        Raises:
            TaskExecutionError: If cancelling the task fails
        """
        process = self._processes.get(task.id)
        if process:
            try:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            except Exception as e:
                raise TaskExecutionError(f"Failed to cancel task: {str(e)}")
            finally:
                if task.id in self._processes:
                    del self._processes[task.id]

    async def cleanup_job(self, job: Job) -> None:
        """Clean up resources for a job.

        Args:
            job: The job to clean up

        Raises:
            TaskExecutionError: If cleanup fails
        """
        try:
            # Cancel any running processes
            process = self._processes.get(job.id)
            if process and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

            # Remove from tracking
            if job.id in self._processes:
                del self._processes[job.id]
            if job.id in self._monitors:
                monitor = self._monitors[job.id]
                monitor.cancel()
                del self._monitors[job.id]

        except Exception as e:
            raise TaskExecutionError(f"Failed to clean up job: {str(e)}") 