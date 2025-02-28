"""Local executor implementation for BenchPRO.

This module provides a local executor that runs tasks on the local machine
using subprocess and asyncio.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from unittest.mock import AsyncMock
import os
import psutil
import re

from benchpro.core.domain import Task, TaskState, Job, JobState
from benchpro.core.domain.errors import TaskExecutionError, ResourceError, ExecutorError
from benchpro.core.executor.base import Executor
from benchpro.core.services.settings import Settings
from .process import ProcessManager
from .resources import ResourceManager

logger = logging.getLogger(__name__)

class LocalExecutor(Executor):
    """Local task executor.
    
    Executes tasks on the local system using asyncio subprocesses.
    """
    
    def __init__(self, working_dir: Path) -> None:
        """Initialize the executor.
        
        Args:
            working_dir: Working directory for execution
        """
        self._working_dir = working_dir
        self._process_manager = ProcessManager()
        self._resource_manager = ResourceManager(working_dir)
        self._jobs: Dict[str, Job] = {}

    @property
    def _processes(self) -> Dict[str, asyncio.subprocess.Process]:
        """Get processes from process manager."""
        return self._process_manager._processes

    @property
    def _monitors(self) -> Dict[str, asyncio.Task]:
        """Get monitors from process manager."""
        return self._process_manager._monitors

    def _parse_memory(self, memory_str: str) -> int:
        """Parse a memory string into bytes.

        Args:
            memory_str: Memory string (e.g. '1G', '500M')

        Returns:
            int: Memory in bytes

        Raises:
            ValueError: If memory string is invalid
        """
        return self._resource_manager._parse_memory(memory_str)

    def _format_memory(self, bytes_value: int) -> str:
        """Format bytes into a human-readable string.

        Args:
            bytes_value: Number of bytes

        Returns:
            str: Formatted memory string (e.g. '1.5G')
        """
        return self._resource_manager._format_memory(bytes_value)

    async def get_system_resources(self) -> Dict[str, Any]:
        """Get available system resources.

        Returns:
            Dict containing available CPU cores and memory
        """
        try:
            return {
                "cores": psutil.cpu_count(),
                "memory": psutil.virtual_memory().available
            }
        except Exception as e:
            logger.error("Error getting system resources: %s", str(e))
            return {"cores": 0, "memory": 0}

    async def validate_resources(self, job: Job) -> bool:
        """Validate that the job can be executed.

        Args:
            job: Job to validate

        Returns:
            bool: True if job can be executed

        Raises:
            ResourceError: If validation fails
        """
        try:
            # Basic validation that job exists and has tasks
            if not job or not job.tasks:
                raise ResourceError("Invalid job: No tasks defined")

            # Check with resource manager
            if not await self._resource_manager.validate_resources(job):
                return False

            return True

        except Exception as e:
            if not isinstance(e, ResourceError):
                raise ResourceError(f"Resource validation failed: {str(e)}")
            raise

    async def prepare(self, task: Task) -> None:
        """Prepare the execution environment for a task.
        
        This includes:
        - Creating necessary directories
        - Setting up environment variables
        - Preparing input files
        
        Args:
            task: The task to prepare for execution
            
        Raises:
            ExecutorError: If preparation fails
        """
        try:
            # Create working directory if it doesn't exist
            task.working_dir.mkdir(parents=True, exist_ok=True)
            
            # Set up environment variables
            task_env = self.env.copy()
            if task.variables:
                task_env.update(task.variables)
            task.variables = task_env
            
            # Validate template path
            if not task.template_path or not task.template_path.exists():
                raise ExecutorError(f"Template path does not exist: {task.template_path}")
            
            # Make template executable
            task.template_path.chmod(0o755)
            
            task.transition_to(TaskState.PENDING)
            
        except Exception as e:
            raise ExecutorError(f"Failed to prepare task: {str(e)}")

    async def run(self, task: Task) -> None:
        """Execute a task.
        
        Args:
            task: The task to execute
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        try:
            # Get the job for this task
            job = next(j for j in self._jobs.values() if task in j.tasks)
            await self._process_manager.execute_task(task, job, task.working_dir)
        except Exception as e:
            raise TaskExecutionError(f"Task execution failed: {str(e)}")

    async def status(self, task: Task) -> TaskState:
        """Get the current status of a task.
        
        Args:
            task: The task to check status for
            
        Returns:
            The current state of the task
        """
        try:
            process = self._process_manager.get_process(task.id)
            if not process:
                return task.state
            
            if process.returncode is None:
                return TaskState.RUNNING
            elif process.returncode == 0:
                return TaskState.COMPLETED
            else:
                return TaskState.FAILED
                
        except Exception as e:
            logger.error("Failed to get task status: %s", str(e))
            return task.state

    async def stop(self, task: Task) -> None:
        """Stop a running task.
        
        Args:
            task: The task to stop
            
        Raises:
            ExecutorError: If stopping the task fails
        """
        try:
            process = self._process_manager.get_process(task.id)
            if process:
                await self._process_manager.cancel_task(task)
                task.transition_to(TaskState.CANCELLED)
        except Exception as e:
            raise ExecutorError(f"Failed to stop task: {str(e)}")

    async def cleanup(self, task: Task) -> None:
        """Clean up after task completion.
        
        This includes:
        - Removing temporary files
        - Releasing resources
        - Archiving outputs if needed
        
        Args:
            task: The task to clean up after
            
        Raises:
            ExecutorError: If cleanup fails
        """
        try:
            # Remove process from manager
            self._process_manager.remove_process(task.id)
            
            # Release resources
            await self._resource_manager.release_resources(task)
            
        except Exception as e:
            raise ExecutorError(f"Failed to clean up task: {str(e)}")

    async def submit_job(self, job: Job) -> None:
        """Submit a job for execution.

        Args:
            job: Job to submit

        Raises:
            TaskExecutionError: If task execution fails
            ResourceError: If insufficient resources
        """
        logger.debug("Submitting job %s (id=%s)", job.name, job.id)
        # Add job to tracking
        self._jobs[job.id] = job

        # Validate resources
        logger.debug("Validating resources for job %s", job.name)
        if not await self.validate_resources(job):
            logger.debug("Resource validation failed for job %s", job.name)
            job.state = JobState.FAILED
            job.completed_at = datetime.now()
            raise ExecutorError("Resource validation failed")

        logger.debug("Resource validation passed for job %s", job.name)
        # Set job state to RUNNING
        job.state = JobState.RUNNING
        job.started_at = datetime.now()

        try:
            # Execute each task
            for task in job.tasks:
                try:
                    await self._process_manager.execute_task(task, job, task.working_dir)
                except TaskExecutionError as e:
                    # Process manager has already set states and error message
                    task.error = str(e)
                    task.transition_to(TaskState.FAILED)
                    job.state = JobState.FAILED
                    job.completed_at = datetime.now()
                    raise
                except asyncio.CancelledError:
                    # Handle cancellation
                    task.transition_to(TaskState.CANCELLED)
                    job.state = JobState.CANCELLED
                    job.completed_at = datetime.now()
                    raise
                except Exception as e:
                    # For unexpected errors, set states and wrap in TaskExecutionError
                    error_msg = f"Task failed with exit code 1: {str(e)}"
                    task.error = error_msg
                    task.transition_to(TaskState.FAILED)
                    job.state = JobState.FAILED
                    job.completed_at = datetime.now()
                    raise TaskExecutionError(error_msg) from e

            # If we get here, all tasks completed successfully
            job.state = JobState.COMPLETED
            job.completed_at = datetime.now()
        except (TaskExecutionError, asyncio.CancelledError):
            # Ensure job state and completion time are set
            job.completed_at = datetime.now()
            raise

    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job.

        Args:
            job: The job to cancel

        Raises:
            ExecutorError: If job cancellation fails
        """
        logger.debug("Attempting to cancel job %s (id=%s)", job.name, job.id)
        try:
            await self._process_manager.cancel_job(job)
            logger.debug("Successfully cancelled job %s", job.name)
            job.state = JobState.CANCELLED
            job.completed_at = datetime.now()
        except Exception as e:
            logger.debug("Failed to cancel job %s: %s", job.name, str(e))
            # Don't change job state if cancellation fails
            raise ExecutorError(f"Failed to cancel job: {str(e)}")

    async def get_job_status(self, job: Job) -> Dict[str, Any]:
        """Get the current status of a job.

        Args:
            job: The job to get status for

        Returns:
            Dict containing job status information

        Raises:
            ExecutorError: If status retrieval fails
        """
        logger.debug("Getting status for job %s (id=%s)", job.name, job.id)
        try:
            # Count tasks in each state
            task_counts = {
                "total": len(job.tasks),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for task in job.tasks:
                if task.state == TaskState.PENDING:
                    task_counts["pending"] += 1
                elif task.state == TaskState.RUNNING:
                    task_counts["running"] += 1
                elif task.state == TaskState.COMPLETED:
                    task_counts["completed"] += 1
                elif task.state == TaskState.FAILED:
                    task_counts["failed"] += 1
                elif task.state == TaskState.CANCELLED:
                    task_counts["cancelled"] += 1

            status = {
                "job_id": job.id,
                "state": job.state.value,
                "tasks": task_counts
            }
            
            logger.debug("Job %s status: %s", job.name, status)
            return status
            
        except Exception as e:
            logger.error("Failed to get job status: %s", str(e))
            raise ExecutorError("Failed to get job status")

    async def get_resource_usage(self, job: Job) -> Dict[str, Any]:
        """Get resource usage for a job.

        Args:
            job: The job to get resource usage for

        Returns:
            Dict containing resource usage information

        Raises:
            ExecutorError: If resource usage retrieval fails
        """
        logger.debug("Getting resource usage for job %s", job.name)
        try:
            return {
                "cores": job.resources.get("cores", 1),
                "memory": job.resources.get("memory", "1G")
            }
        except Exception as e:
            logger.error("Failed to get resource usage: %s", str(e))
            raise ExecutorError("Failed to get resource usage")

    async def cleanup_job(self, job: Job) -> None:
        """Clean up after job completion.

        Args:
            job: The job to clean up

        Raises:
            ExecutorError: If cleanup fails
        """
        try:
            # Remove job from tracking
            self._jobs.pop(job.id, None)
            
            # Clean up processes
            await self._process_manager.cleanup_job(job)
            
            # Release resources
            await self._resource_manager.release_resources(job.tasks[0])
            
        except Exception as e:
            raise ExecutorError(f"Failed to clean up job: {str(e)}") 