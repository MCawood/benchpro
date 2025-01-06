"""Task model for BenchPRO."""

from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from typing_extensions import Annotated
from pydantic import BaseModel, Field, BeforeValidator, field_validator
from benchpro.core.validation.validators import FileValidator, validate_memory_string
import uuid
import json

def validate_optional_template(value: Optional[Path]) -> Optional[Path]:
    """Validate template path if provided."""
    if value is None:
        return None
    validator = FileValidator(extensions=[".sh"])
    return validator(value)

class TaskState(str, Enum):
    """Task execution states."""
    CREATED = "created"     # Initial state when task is created
    PENDING = "pending"     # Task is ready to be executed
    RUNNING = "running"     # Task is currently executing
    COMPLETED = "completed" # Task has completed successfully
    FAILED = "failed"       # Task has failed
    CANCELLED = "cancelled" # Task was cancelled

    def can_transition_to(self, new_state: 'TaskState') -> bool:
        """Check if transition to new state is valid."""
        valid_transitions = {
            TaskState.CREATED: {TaskState.PENDING, TaskState.RUNNING, TaskState.FAILED, TaskState.COMPLETED},
            TaskState.PENDING: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED, TaskState.COMPLETED},
            TaskState.RUNNING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.COMPLETED: set(),  # Terminal state
            TaskState.FAILED: set(),     # Terminal state
            TaskState.CANCELLED: set(),  # Terminal state
        }
        return new_state in valid_transitions.get(self, set())

class Task(BaseModel):
    """A task represents a single unit of work to be executed."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the task")
    name: str = Field(..., description="Name of the task")
    working_dir: Path = Field(..., description="Working directory for the task")
    template_path: Optional[Annotated[Path, BeforeValidator(validate_optional_template)]] = Field(
        None, description="Path to the task template script"
    )
    variables: Dict[str, Any] = Field(default_factory=dict, description="Task variables and resource requirements")
    state: TaskState = Field(default=TaskState.CREATED, description="Current state of the task")
    error: Optional[str] = Field(None, description="Error message if task failed")

    def transition_to(self, new_state: TaskState, error: Optional[str] = None) -> None:
        """Transition task to a new state.
        
        Args:
            new_state: The new state to transition to.
            error: Optional error message if transitioning to FAILED state.
            
        Raises:
            ValueError: If the state transition is invalid.
        """
        if new_state == self.state:
            return  # No-op if transitioning to the same state
        
        if not self.state.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition from {self.state} to {new_state}"
            )
        self.state = new_state
        if error is not None and new_state == TaskState.FAILED:
            self.error = error
        self.save_state()

    def save_state(self) -> None:
        """Save task state to a file in the working directory."""
        self.working_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.working_dir / "task_state.json"
        state_data = {
            "state": self.state,
            "error": self.error
        }
        state_file.write_text(json.dumps(state_data))

    @classmethod
    def load_state(cls, task_dir: Path) -> Dict[str, Any]:
        """Load task state from a file in the working directory."""
        state_file = task_dir / "task_state.json"
        if state_file.exists():
            state_data = json.loads(state_file.read_text())
            return {
                "state": TaskState(state_data["state"]),
                "error": state_data.get("error")
            }
        return {
            "state": TaskState.CREATED,
            "error": None
        }

    @field_validator("variables")
    def validate_memory(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate memory specification in variables."""
        if "memory" in v:
            try:
                validate_memory_string(v["memory"])
            except ValueError as e:
                raise ValueError(f"Invalid memory format: {e}")
        return v

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True 