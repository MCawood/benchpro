"""Slurm executor implementations."""

from pathlib import Path
from typing import Dict, Any, Optional

from benchpro.core.executor.base import Executor
from benchpro.core.domain import Task, Job

class SlurmExecutorBase(Executor):
    """Base class for Slurm executors."""
    
    def __init__(self, working_dir: Path, env: Dict[str, str]):
        super().__init__(working_dir, env)

    async def prepare(self, task: Task) -> None:
        """Prepare task for execution."""
        pass

    async def run(self, task: Task, job: Job) -> None:
        """Run task."""
        pass

    async def status(self, task: Task) -> Dict[str, Any]:
        """Get task status."""
        return {}

    async def stop(self, task: Task) -> None:
        """Stop task."""
        pass

    async def cleanup(self, task: Task) -> None:
        """Clean up task."""
        pass

class SystemSlurmExecutor(SlurmExecutorBase):
    """Executor for system Slurm installation."""
    pass

class SlurmSimulatorExecutor(SlurmExecutorBase):
    """Executor for Slurm simulator."""
    pass 