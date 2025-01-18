"""Event bus service for domain events."""

from typing import Callable, Dict, List, Type
from benchpro.core.domain.events import Event
from benchpro.core.services.logging import get_logger

logger = get_logger("event_bus")

EventHandler = Callable[[Event], None]

class EventBus:
    """Service for publishing and subscribing to domain events."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize event bus if not already initialized."""
        if not self._initialized:
            self._handlers: Dict[Type[Event], List[EventHandler]] = {}
            self._initialized = True
            logger.debug("Initialized EventBus")
    
    def subscribe(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Added handler for event type: %s", event_type.__name__)
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers.
        
        Args:
            event: Event to publish
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        logger.debug("Publishing event: %s", event_type.__name__)
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler failed: %s", e)
                # Continue with other handlers even if one fails 