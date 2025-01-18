"""Task state management service."""

from typing import Callable, Dict, List, Optional, Set, TYPE_CHECKING
from benchpro.core.domain.states import TaskState
from benchpro.core.domain.events import TaskStateChangedEvent
from benchpro.core.services.event_bus import EventBus
from benchpro.core.services.logging import get_logger

if TYPE_CHECKING:
    from benchpro.core.domain.task import Task

logger = get_logger("task_state")

# Type aliases for hook functions
PreTransitionHook = Callable[['Task', TaskState, TaskState], None]
PostTransitionHook = Callable[['Task', TaskState, TaskState], None]

class InvalidStateTransitionError(Exception):
    """Raised when attempting an invalid state transition."""
    pass

class TaskStateManager:
    """Service for managing task state transitions."""
    
    def __init__(self):
        """Initialize the task state manager."""
        self._pre_transition_hooks: List[PreTransitionHook] = []
        self._post_transition_hooks: List[PostTransitionHook] = []
        self._event_bus = EventBus()
        
        # Initialize valid state transitions
        self._valid_transitions: Dict[TaskState, Set[TaskState]] = {
            TaskState.CREATED: {TaskState.STAGING, TaskState.PENDING, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.STAGING: {TaskState.PENDING, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.PENDING: {TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.RUNNING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.COMPLETED: set(),  # Terminal state
            TaskState.FAILED: set(),     # Terminal state
            TaskState.CANCELLED: set()   # Terminal state
        }
        
        logger.debug("Initialized TaskStateManager")
        
    def add_pre_transition_hook(self, hook: PreTransitionHook) -> None:
        """Add a hook to be called before state transitions."""
        self._pre_transition_hooks.append(hook)
        logger.debug("Added pre-transition hook")
        
    def add_post_transition_hook(self, hook: PostTransitionHook) -> None:
        """Add a hook to be called after state transitions."""
        self._post_transition_hooks.append(hook)
        logger.debug("Added post-transition hook")
        
    def can_transition_to(self, current_state: TaskState, new_state: TaskState) -> bool:
        """Check if a transition to the new state is valid."""
        # Special case: Allow direct transition to FAILED or CANCELLED from any state
        if new_state in (TaskState.FAILED, TaskState.CANCELLED):
            return True
            
        return new_state in self._valid_transitions[current_state]
        
    def transition_to(self, task: 'Task', new_state: TaskState, error: Optional[str] = None) -> None:
        """Transition a task to a new state."""
        old_state = task.state
        
        # Validate transition
        if not self.can_transition_to(old_state, new_state):
            valid_transitions = self._valid_transitions[old_state]
            error_msg = (
                f"Invalid state transition for task {task.id}: {old_state} -> {new_state}. "
                f"Valid transitions are: {valid_transitions}"
            )
            logger.error(error_msg)
            raise InvalidStateTransitionError(error_msg)
            
        try:
            # Execute pre-transition hooks
            for hook in self._pre_transition_hooks:
                try:
                    hook(task, old_state, new_state)
                except Exception as e:
                    logger.error("Pre-transition hook failed: %s", e)
                    raise
                    
            # Perform transition
            logger.debug(
                "Task %s state transition: %s -> %s (error: %s)",
                task.id,
                old_state,
                new_state,
                error if error else "None"
            )
            
            task._state = new_state  # Update internal state
            if error:
                task.error = error
                
            # Save state after transition
            task.save_state()
            
            # Publish state changed event
            event = TaskStateChangedEvent(
                task_id=task.id,
                old_state=old_state,
                new_state=new_state,
                error=error
            )
            self._event_bus.publish(event)
            
            # Execute post-transition hooks
            for hook in self._post_transition_hooks:
                try:
                    hook(task, old_state, new_state)
                except Exception as e:
                    logger.error("Post-transition hook failed: %s", e)
                    # Don't re-raise post-hook errors since state is already changed
                    
        except Exception as e:
            if not isinstance(e, InvalidStateTransitionError):
                logger.error("Failed to transition task %s: %s", task.id, e)
            raise 