"""Executor interface for BenchPRO."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from benchpro.core.domain.job import Job
from benchpro.core.domain.task import Task


class ExecutorError(Exception):
    """Base class for executor-related errors."""
    pass


class ResourceError(ExecutorError):
    """Error related to resource allocation or monitoring."""
    pass


class ExecutionError(ExecutorError):
    """Error during task/job execution."""
    pass


class Executor(ABC):
    """Abstract base class for job executors.
    
    An executor is responsible for:
    1. Validating resource requirements
    2. Managing task/job execution
    3. Monitoring resource usage
    4. Handling execution errors
    """
    
    @abstractmethod
    async def validate_resources(self, job: Job) -> None:
        """Validate that required resources are available.
        
        Args:
            job: Job to validate resources for
        
        Raises:
            ResourceError: If resources are not available or invalid
        """
        pass

    @abstractmethod
    async def submit_job(self, job: Job) -> None:
        """Submit a job for execution.
        
        Args:
            job: Job to submit
        
        Raises:
            ExecutionError: If job submission fails
            ResourceError: If required resources are not available
        """
        pass

    @abstractmethod
    async def cancel_job(self, job: Job) -> None:
        """Cancel a running job.
        
        Args:
            job: Job to cancel
        
        Raises:
            ExecutionError: If job cancellation fails
        """
        pass

    @abstractmethod
    async def get_job_status(self, job: Job) -> Dict[str, str]:
        """Get current status of a job.
        
        Args:
            job: Job to get status for
        
        Returns:
            Dictionary with status information
        
        Raises:
            ExecutionError: If status check fails
        """
        pass

    @abstractmethod
    async def get_resource_usage(self, job: Job) -> Dict[str, float]:
        """Get current resource usage of a job.
        
        Args:
            job: Job to get resource usage for
        
        Returns:
            Dictionary with resource usage metrics
        
        Raises:
            ExecutionError: If resource check fails
        """
        pass

    @abstractmethod
    async def cleanup_job(self, job: Job) -> None:
        """Clean up resources after job completion.
        
        Args:
            job: Job to clean up after
        
        Raises:
            ExecutionError: If cleanup fails
        """
        pass 