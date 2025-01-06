"""Job domain model for BenchPRO."""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from benchpro.core.domain.task import Task, TaskState
from benchpro.core.validation.validators import DirectoryPath, MemoryString


class JobState(str, Enum):
    """Job execution states."""
    
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid state transitions
VALID_TRANSITIONS = {
    JobState.CREATED: {JobState.QUEUED, JobState.CANCELLED},
    JobState.QUEUED: {JobState.RUNNING, JobState.CANCELLED},
    JobState.RUNNING: {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED},
    JobState.COMPLETED: set(),  # Terminal state
    JobState.FAILED: set(),  # Terminal state
    JobState.CANCELLED: set(),  # Terminal state
}


class JobResources(BaseModel):
    """Resource requirements for a job.
    
    Attributes:
        cores: Number of CPU cores required
        memory: Memory requirement (e.g., "8G", "16GB")
        nodes: Number of nodes required (for HPC jobs)
        walltime: Maximum runtime in seconds
    """
    
    cores: int = Field(gt=0)
    memory: MemoryString
    nodes: int = Field(default=1, gt=0)
    walltime: int = Field(default=3600, gt=0)  # 1 hour default


class Job(BaseModel):
    """A job represents a collection of related tasks.
    
    Attributes:
        id: Unique identifier for the job
        name: Human-readable name for the job
        working_dir: Base directory for job execution
        tasks: List of tasks to execute
        resources: Resource requirements
        state: Current state of the job
        error: Error message if job failed
        created_at: When the job was created
        started_at: When the job started running
        completed_at: When the job completed/failed/cancelled
    """
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1)
    working_dir: DirectoryPath
    tasks: List[Task] = Field(default_factory=list)
    resources: JobResources
    state: JobState = Field(default=JobState.CREATED)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate job name."""
        if not v.strip():
            raise ValueError("Job name cannot be empty or whitespace")
        return v.strip()

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v: List[Task]) -> List[Task]:
        """Validate task list."""
        if not v:
            raise ValueError("Job must have at least one task")
        return v

    def _validate_state_transition(self, new_state: JobState) -> None:
        """Validate state transition."""
        if new_state not in VALID_TRANSITIONS[self.state]:
            raise ValueError(
                f"Invalid state transition from {self.state} to {new_state}. "
                f"Valid transitions are: {VALID_TRANSITIONS[self.state]}"
            )

    def transition_to(self, new_state: JobState, error: Optional[str] = None) -> None:
        """Transition job to a new state.
        
        Args:
            new_state: The new state to transition to
            error: Optional error message for failed states
        
        Raises:
            ValueError: If the state transition is invalid
        """
        self._validate_state_transition(new_state)
        
        # Update timestamps based on state
        if new_state == JobState.RUNNING:
            self.started_at = datetime.now(UTC)
        elif new_state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            self.completed_at = datetime.now(UTC)
        
        self.state = new_state
        if error is not None:
            self.error = error

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return not bool(VALID_TRANSITIONS[self.state])

    @property
    def duration(self) -> Optional[float]:
        """Get job duration in seconds.
        
        Returns:
            Duration in seconds if job has started, None otherwise
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now(UTC)
        return (end_time - self.started_at).total_seconds()

    @property
    def task_states(self) -> Dict[TaskState, Set[UUID]]:
        """Get mapping of task states to task IDs."""
        states: Dict[TaskState, Set[UUID]] = {state: set() for state in TaskState}
        for task in self.tasks:
            states[task.state].add(task.id)
        return states

    @property
    def has_failed_tasks(self) -> bool:
        """Check if any tasks have failed."""
        return bool(self.task_states[TaskState.FAILED])

    @property
    def all_tasks_completed(self) -> bool:
        """Check if all tasks have completed successfully."""
        return all(task.state == TaskState.COMPLETED for task in self.tasks)

    def __str__(self) -> str:
        """Get string representation of job."""
        status = f"{self.name} ({self.state.value})"
        if self.error:
            status += f" - Error: {self.error}"
        elif self.duration is not None:
            status += f" - Duration: {self.duration:.1f}s"
        
        # Add task summary
        total = len(self.tasks)
        completed = len(self.task_states[TaskState.COMPLETED])
        failed = len(self.task_states[TaskState.FAILED])
        status += f" - Tasks: {completed}/{total} completed"
        if failed:
            status += f", {failed} failed"
        
        return status 