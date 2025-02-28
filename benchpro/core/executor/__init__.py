"""Executor package for running tasks."""

from .base import Executor, ExecutorError, TaskExecutionError, ResourceError
from .local import LocalExecutor
from .slurm import SlurmExecutor

__all__ = [
    'Executor',
    'ExecutorError',
    'TaskExecutionError',
    'ResourceError',
    'LocalExecutor',
    'SlurmExecutor'
] 