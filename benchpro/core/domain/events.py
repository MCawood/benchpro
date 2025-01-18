"""Domain events for BenchPRO."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from benchpro.core.domain.states import TaskState, JobState

class Event:
    """Base class for domain events."""
    def __init__(self):
        self.timestamp: datetime = datetime.now()

@dataclass
class TaskStateChangedEvent(Event):
    """Event emitted when a task's state changes."""
    task_id: str
    old_state: TaskState
    new_state: TaskState
    error: Optional[str] = None
    
    def __post_init__(self):
        super().__init__()

@dataclass
class JobStateChangedEvent(Event):
    """Event emitted when a job's state changes."""
    job_id: str
    task_id: str  # Reference to parent task
    old_state: JobState
    new_state: JobState
    error: Optional[str] = None
    
    def __post_init__(self):
        super().__init__() 