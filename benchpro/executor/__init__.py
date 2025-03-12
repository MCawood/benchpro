"""
Executor Module for BenchPRO.

This module provides task execution functionality for BenchPRO using a composition-based architecture.
"""

from benchpro.executor.task import Task, Application, Benchmark
from benchpro.executor.task_factory import TaskFactory
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.executor.components.execution import LocalExecutionComponent, SlurmExecutionComponent
from benchpro.executor.scheduler import SlurmScheduler

__all__ = [
    'Task',
    'Application',
    'Benchmark',
    'TaskFactory',
    'TaskOrchestrator',
    'LocalExecutionComponent',
    'SlurmExecutionComponent',
    'SlurmScheduler'
]
