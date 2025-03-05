"""
Task Classes for BenchPRO (Legacy Import).

This module re-exports task classes from their new locations for backward compatibility.
"""

# Re-export classes for backward compatibility
from benchpro.executor.task_base import Task
from benchpro.executor.application_task import Application
from benchpro.executor.benchmark_task import Benchmark
from benchpro.executor.task_factory import TaskFactory

__all__ = [
    'Task',
    'Application',
    'Benchmark',
    'TaskFactory'
] 