"""Domain models for BenchPRO."""

from .task import Task, TaskState
from .job import Job

__all__ = ['Task', 'TaskState', 'Job']
