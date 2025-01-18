"""Event subscribers for domain events."""

from benchpro.core.domain.events import TaskStateChangedEvent, JobStateChangedEvent
from benchpro.core.services.event_bus import EventBus
from benchpro.core.services.logging import get_logger

logger = get_logger("events")

class StateChangeLogger:
    """Subscriber for logging state change events."""
    
    def __init__(self):
        """Initialize and register with event bus."""
        self._event_bus = EventBus()
        self._event_bus.subscribe(TaskStateChangedEvent, self._handle_task_state_change)
        self._event_bus.subscribe(JobStateChangedEvent, self._handle_job_state_change)
        logger.debug("Initialized StateChangeLogger")
        
    def _handle_task_state_change(self, event: TaskStateChangedEvent) -> None:
        """Handle task state change events."""
        if event.error:
            logger.warning(
                "Task %s state changed: %s -> %s (Error: %s)",
                event.task_id,
                event.old_state,
                event.new_state,
                event.error
            )
        else:
            logger.info(
                "Task %s state changed: %s -> %s",
                event.task_id,
                event.old_state,
                event.new_state
            )
            
    def _handle_job_state_change(self, event: JobStateChangedEvent) -> None:
        """Handle job state change events."""
        if event.error:
            logger.warning(
                "Job %s (Task %s) state changed: %s -> %s (Error: %s)",
                event.job_id,
                event.task_id,
                event.old_state,
                event.new_state,
                event.error
            )
        else:
            logger.info(
                "Job %s (Task %s) state changed: %s -> %s",
                event.job_id,
                event.task_id,
                event.old_state,
                event.new_state
            ) 