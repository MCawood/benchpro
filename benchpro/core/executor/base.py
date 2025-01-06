"""Base executor interface for BenchPRO.

This module defines the abstract base class for task executors.
Executors are responsible for running tasks and managing their lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from benchpro.core.domain import Task, TaskState

class ExecutorError(Exception):
    """Base class for executor-related errors."""
    pass

class TaskExecutionError(ExecutorError):
    """Raised when a task fails to execute."""
    pass

class ResourceError(ExecutorError):
    """Raised when required resources are not available."""
    pass

class Executor(ABC):
    """Abstract base class for task executors.
    
    An executor is responsible for:
    1. Validating task requirements
    2. Preparing the execution environment
    3. Running the task
    4. Monitoring task status
    5. Cleaning up after task completion
    
    Attributes:
        working_dir: Base directory for executor operations
        env: Environment variables for task execution
    """
    
    def __init__(self, working_dir: Path, env: Optional[Dict[str, str]] = None):
        """Initialize the executor.
        
        Args:
            working_dir: Base directory for executor operations
            env: Optional environment variables for task execution
        """
        self.working_dir = working_dir
        self.env = env or {}
    
    @abstractmethod
    async def validate_resources(self, task: Task) -> bool:
        """Validate that required resources are available.
        
        Args:
            task: The task to validate resources for
            
        Returns:
            True if resources are available, False otherwise
            
        Raises:
            ResourceError: If resource validation fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def run(self, task: Task) -> None:
        """Execute a task.
        
        Args:
            task: The task to execute
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        pass
    
    @abstractmethod
    async def status(self, task: Task) -> TaskState:
        """Get the current status of a task.
        
        Args:
            task: The task to check status for
            
        Returns:
            The current state of the task
        """
        pass
    
    @abstractmethod
    async def stop(self, task: Task) -> None:
        """Stop a running task.
        
        Args:
            task: The task to stop
            
        Raises:
            ExecutorError: If stopping the task fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        pass 