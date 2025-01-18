"""Service for managing task locations."""

import os
from pathlib import Path
from typing import Dict, Optional

from benchpro.core.domain.task_registry import TaskType
from benchpro.core.services.settings import Settings
from benchpro.core.services.logging import get_logger

logger = get_logger("locations")

class LocationError(Exception):
    """Raised when there is an error with task locations."""
    pass

class LocationManager:
    """Service for managing task locations."""
    
    def __init__(self, settings: Settings):
        """Initialize location manager.
        
        Args:
            settings: BenchPRO settings
        """
        self.settings = settings
        self._locations: Dict[TaskType, Path] = {}
        self._load_locations()
        logger.debug("Initialized LocationManager")
    
    def _load_locations(self) -> None:
        """Load task locations from settings."""
        locations = self.settings.get("task_locations")
        if not locations:
            raise LocationError("Task locations not configured")
            
        # Expand environment variables in paths
        for task_type in TaskType:
            if task_type.value in locations:
                path_str = locations[task_type.value]
                if path_str:
                    # Expand environment variables
                    path_str = os.path.expandvars(path_str)
                    path = Path(path_str).resolve()
                    self._locations[task_type] = path
                    logger.debug("Loaded location for %s: %s", task_type, path)
    
    def get_task_location(
        self,
        task_type: TaskType,
        custom_location: Optional[Path] = None
    ) -> Path:
        """Get location for a task.
        
        Args:
            task_type: Type of task
            custom_location: Optional custom location override
            
        Returns:
            Task location
            
        Raises:
            LocationError: If location cannot be resolved
        """
        if custom_location:
            # Use custom location if provided
            location = custom_location.resolve()
            logger.debug("Using custom location for %s: %s", task_type, location)
            return location
            
        if task_type not in self._locations:
            raise LocationError(f"No location configured for task type: {task_type}")
            
        location = self._locations[task_type]
        logger.debug("Resolved location for %s: %s", task_type, location)
        return location
    
    def update_location(self, task_type: TaskType, location: Path) -> None:
        """Update location for a task type.
        
        Args:
            task_type: Type of task
            location: New location
            
        Raises:
            LocationError: If location is invalid
        """
        try:
            # Resolve and validate path
            location = location.resolve()
            if not location.parent.exists():
                raise LocationError(f"Parent directory does not exist: {location.parent}")
                
            # Update settings
            locations = self.settings.get("task_locations")
            locations[task_type.value] = str(location)
            self.settings.set("task_locations", locations)
            
            # Update internal cache
            self._locations[task_type] = location
            logger.debug("Updated location for %s: %s", task_type, location)
            
        except Exception as e:
            raise LocationError(f"Failed to update location: {e}")
    
    def ensure_location(self, location: Path) -> None:
        """Ensure a location exists and is writable.
        
        Args:
            location: Location to check
            
        Raises:
            LocationError: If location is invalid or not writable
        """
        try:
            # Create directory if it doesn't exist
            location.mkdir(parents=True, exist_ok=True)
            
            # Check if writable by trying to create a test file
            test_file = location / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                raise LocationError(f"Location not writable: {e}")
                
            logger.debug("Verified location is writable: %s", location)
            
        except Exception as e:
            raise LocationError(f"Failed to ensure location: {e}") 