"""Task model for BenchPRO."""

from pathlib import Path
from typing import Dict, Any, Optional, List
from typing_extensions import Annotated
from pydantic import BaseModel, Field, BeforeValidator, field_validator, PrivateAttr
from benchpro.core.validation.validators import FileValidator, validate_memory_string
from benchpro.core.domain.staging import StagingFile, StagingMode
from benchpro.core.domain.states import TaskState
from benchpro.core.services.task_state_manager import TaskStateManager, InvalidStateTransitionError
import uuid
import json
import subprocess
from benchpro.core.services.logging import get_logger

logger = get_logger("task")

# Global state manager instance
_state_manager = TaskStateManager()

def validate_optional_template(value: Optional[Path]) -> Optional[Path]:
    """Validate template path if provided."""
    if value is None:
        return None
    validator = FileValidator(extensions=[".sh"])
    return validator(value)

class Task(BaseModel):
    """A task that can be executed by an executor."""

    name: str = Field(..., description="Name of the task")
    working_dir: Path = Field(..., description="Working directory for task execution")
    template_path: Optional[Annotated[Path, BeforeValidator(validate_optional_template)]] = Field(
        None, description="Path to the task template script"
    )
    variables: Dict[str, Any] = Field(default_factory=dict, description="Task variables and resource requirements")
    error: Optional[str] = Field(None, description="Error message if task failed")
    staging_files: List[StagingFile] = Field(
        default_factory=list,
        description="Files that need to be staged before execution"
    )
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the task")
    _state: TaskState = PrivateAttr(default=TaskState.CREATED)

    def __init__(self, **data):
        state = data.pop('state', TaskState.CREATED)
        super().__init__(**data)
        self._state = state if isinstance(state, TaskState) else TaskState(state) if state else TaskState.CREATED
        
        # Add template file to staging files if provided
        if self.template_path:
            template_staging = StagingFile(
                source=self.template_path,
                destination=self.working_dir / "run.sh",
                mode=StagingMode.LOCAL_COPY
            )
            if template_staging not in self.staging_files:
                self.staging_files.append(template_staging)

    @property
    def state(self) -> TaskState:
        """Get current task state."""
        return self._state

    @state.setter
    def state(self, new_state: TaskState | str) -> None:
        """Set task state using transition_to method."""
        if isinstance(new_state, str):
            new_state = TaskState(new_state)
        self.transition_to(new_state)

    def transition_to(self, new_state: TaskState, error: Optional[str] = None) -> None:
        """Transition task to a new state.
        
        Args:
            new_state: State to transition to
            error: Optional error message if transitioning to FAILED state
            
        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        try:
            _state_manager.transition_to(self, new_state, error)
        except InvalidStateTransitionError as e:
            logger.error(str(e))
            raise

    def __eq__(self, other):
        """Compare task states."""
        if isinstance(other, Task):
            return super().__eq__(other)
        if isinstance(other, TaskState):
            return self._state == other
        return NotImplemented

    def __hash__(self):
        """Hash task."""
        return hash((super().__hash__(), self._state))

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Dump model to dict including state."""
        data = super().model_dump(*args, **kwargs)
        data['state'] = self._state
        return data

    def save_state(self) -> None:
        """Save task state to a file in the working directory."""
        self.working_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.working_dir / "task_state.json"
        state_data = {
            "state": self._state.value,
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

    def __str__(self) -> str:
        """Get string representation."""
        return f"Task(name={self.name}, state={self.state})"

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True 