"""Base class for job scheduler executors.

This module provides the abstract base class for job scheduler implementations like Slurm.
It defines the interface that all scheduler executors must implement and provides common
functionality for job management.

The SchedulerExecutor class handles:
- Job submission and cancellation
- Status monitoring
- Resource validation and translation
- Script generation
- Resource usage tracking
"""

import abc
from pathlib import Path
from typing import Dict, Optional, Any

from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.ports.executor import Executor, ExecutionError, ResourceError
from benchpro.core.executor.base import Executor

class SchedulerExecutor(Executor, abc.ABC):
    """Abstract base class for job scheduler executors.
    
    This class defines the interface that scheduler-specific implementations must provide.
    It includes methods for job submission, cancellation, status checking, and resource
    management.
    
    Attributes:
        working_dir: Base directory for job files
        env: Dictionary of environment variables to set in job scripts
        _job_ids: Mapping of BenchPRO job IDs to scheduler job IDs
    """
    
    def __init__(self, working_dir: Path, env: Optional[Dict[str, str]] = None):
        """Initialize scheduler executor.
        
        Args:
            working_dir: Base directory for executor operations
            env: Optional environment variables for task execution
        """
        super().__init__(working_dir, env)
        self._job_ids: Dict[str, str] = {}

    @abc.abstractmethod
    async def _submit_to_scheduler(self, job: Job, script_path: Path) -> str:
        """Submit job to scheduler and return job ID.
        
        Args:
            job: Job to submit
            script_path: Path to job script
            
        Returns:
            Scheduler-specific job ID
            
        Raises:
            ExecutionError: If submission fails
        """
        pass

    @abc.abstractmethod
    async def _cancel_scheduler_job(self, scheduler_job_id: str) -> None:
        """Cancel a running scheduler job.
        
        Args:
            scheduler_job_id: Scheduler-specific job ID to cancel
            
        Raises:
            ExecutionError: If cancellation fails
        """
        pass

    @abc.abstractmethod
    async def _get_scheduler_job_status(self, scheduler_job_id: str) -> str:
        """Get status of job from scheduler.
        
        Args:
            scheduler_job_id: Scheduler-specific job ID
            
        Returns:
            Job state as string
            
        Raises:
            ExecutionError: If status check fails
        """
        pass

    @abc.abstractmethod
    def _translate_resources(self, job: Job) -> Dict[str, str]:
        """Translate BenchPRO job resources to scheduler directives.
        
        Args:
            job: Job containing resource requirements
            
        Returns:
            Dictionary of scheduler-specific resource directives
        """
        pass

    @abc.abstractmethod
    async def validate_resources(self, job: Job) -> None:
        """Validate that requested resources are available.
        
        Args:
            job: Job to validate resources for
            
        Raises:
            ResourceError: If resources are invalid or unavailable
        """
        pass

    @abc.abstractmethod
    async def get_resource_usage(self, job: Job) -> Dict[str, float]:
        """Get current resource usage for job.
        
        Args:
            job: Job to get resource usage for
            
        Returns:
            Dictionary of resource usage metrics
            
        Raises:
            ExecutionError: If resource usage check fails
        """
        pass

    async def submit_job(self, job: Job) -> None:
        """Submit job to scheduler.
        
        This method:
        1. Validates requested resources
        2. Generates job script
        3. Submits to scheduler
        4. Updates job state and ID mapping
        
        Args:
            job: Job to submit
            
        Raises:
            ResourceError: If resources are invalid
            ExecutionError: If submission fails
        """
        await self.validate_resources(job)
        
        script_path = job.working_dir / "job.sh"
        self._generate_job_script(job, script_path)
        
        try:
            scheduler_job_id = await self._submit_to_scheduler(job, script_path)
            self._job_ids[job.id] = scheduler_job_id
            job.state = JobState.RUNNING
        except ExecutionError:
            if script_path.exists():
                script_path.unlink()
            raise

    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job.
        
        Args:
            job: Job to cancel
            
        Raises:
            ExecutionError: If job not found or cancellation fails
        """
        scheduler_job_id = self._job_ids.get(job.id)
        if not scheduler_job_id:
            raise ExecutionError("No scheduler job ID found for job")
            
        await self._cancel_scheduler_job(scheduler_job_id)
        job.state = JobState.CANCELLED

    async def get_job_status(self, job: Job) -> Dict[str, Any]:
        """Get current job status.
        
        Args:
            job: Job to get status for
            
        Returns:
            Dictionary containing job status and resource usage
            
        Raises:
            ExecutionError: If status check fails
        """
        scheduler_job_id = self._job_ids.get(job.id)
        if not scheduler_job_id:
            return {"status": job.state.value}
            
        status = await self._get_scheduler_job_status(scheduler_job_id)
        usage = await self.get_resource_usage(job)
        
        return {
            "status": status,
            "resource_usage": usage
        }

    async def cleanup_job(self, job: Job) -> None:
        """Clean up job resources.
        
        Args:
            job: Job to clean up
        """
        if job.id in self._job_ids:
            del self._job_ids[job.id]
            
        script_path = job.working_dir / "job.sh"
        if script_path.exists():
            script_path.unlink()

    def _generate_job_script(self, job: Job, script_path: Path) -> None:
        """Generate job submission script.
        
        Args:
            job: Job to generate script for
            script_path: Path to write script to
        """
        resources = self._translate_resources(job)
        
        with open(script_path, "w") as f:
            # Write resource directives
            for key, value in resources.items():
                f.write(f"#{key}={value}\n")
            
            f.write("\n")
            
            # Write environment setup
            if self.env:
                for key, value in self.env.items():
                    f.write(f"export {key}={value}\n")
                f.write("\n")
            
            # Write task commands
            for task in job.tasks:
                f.write(f"# Task: {task.name}\n")
                command = task.variables.get("command", "")
                f.write(f"{command}\n\n") 