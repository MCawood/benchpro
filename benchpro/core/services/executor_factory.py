"""Factory for creating task executors."""

from typing import Dict, Any, Optional
from pathlib import Path

from benchpro.core.domain.errors import ExecutorError
from benchpro.core.executor.base import Executor
from benchpro.core.executor.local import LocalExecutor
from benchpro.core.executor.slurm import SlurmExecutor
from benchpro.core.services.settings import Settings

def create_executor(settings: Optional[Settings] = None) -> Executor:
    """Create a task executor based on settings.
    
    Args:
        settings: Application settings, if None will create new Settings instance
        
    Returns:
        An instance of the appropriate executor
        
    Raises:
        ValueError: If unknown executor type specified
    """
    if settings is None:
        settings = Settings()
        
    # First get executor settings
    executor_settings = settings.get("executor", {})
    executor_type = executor_settings.get("type", "local")
    
    # Then get working directory
    working_dir = Path(settings.get("task_locations", {}).get("build", "."))
    working_dir.mkdir(parents=True, exist_ok=True)
    
    if executor_type == "local":
        return LocalExecutor(working_dir=working_dir)
    elif executor_type == "slurm":
        return SlurmExecutor(working_dir=working_dir)
    else:
        raise ValueError(f"Unknown executor type: {executor_type}")

def create_executor() -> Executor:
    """Create an executor based on settings.
    
    Returns:
        An instance of the appropriate executor
    """
    settings = Settings()
    executor_settings = settings.get("executor", {})
    executor_type = executor_settings.get("type", "local")
    
    working_dir = Path(settings.get("task_locations", {}).get("build", "."))
    
    if executor_type == "local":
        return LocalExecutor(working_dir=working_dir)
    elif executor_type == "slurm":
        return SlurmExecutor(working_dir=working_dir)
    else:
        raise ValueError(f"Unknown executor type: {executor_type}")

def create_executor(settings: Settings) -> Executor:
    """Create a task executor based on settings.
    
    Args:
        settings: Settings instance
        
    Returns:
        Configured executor instance
        
    Raises:
        ExecutorError: If executor type is invalid
    """
    # Get executor config first
    executor_config = settings.get("executor", {})
    executor_type = executor_config.get("type", "local")
    
    # Get working directory
    working_dir = settings.get("working_dir", "/tmp/benchpro")

    if executor_type == "local":
        return LocalExecutor(working_dir=Path(working_dir))
    elif executor_type == "slurm":
        raise ExecutorError("Slurm executor not yet implemented")
    else:
        raise ExecutorError(f"Invalid executor type: {executor_type}")

def create_local_executor(settings: Settings) -> LocalExecutor:
    """Create a local executor.

    Args:
        settings: Settings instance

    Returns:
        LocalExecutor: Created local executor instance
    """
    working_dir = settings.get("working_dir", "/tmp/benchpro")
    return LocalExecutor(working_dir=Path(working_dir)) 