"""Core domain models for BenchPRO."""

from benchpro.core.domain.task import Task
from benchpro.core.domain.job import Job
from benchpro.core.domain.states import TaskState, JobState

__all__ = [
    "Task",
    "TaskState",
    "Job", 
    "JobState"
]
