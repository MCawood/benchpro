"""State enumerations for BenchPRO domain models."""

from enum import Enum

class TaskState(str, Enum):
    """Task state enumeration."""
    CREATED = "created"
    STAGING = "staging"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobState(str, Enum):
    """Job execution states."""
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled" 