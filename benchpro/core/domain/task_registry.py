"""Task registry for managing task locations and history."""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from benchpro.core.services.logging import get_logger
from benchpro.core.services.system_paths import SystemPaths

logger = get_logger("registry")

class TaskType(str, Enum):
    """Types of tasks that can be registered."""
    BUILD = "build"
    BENCHMARK = "benchmark"
    CUSTOM = "custom"

@dataclass
class TaskRecord:
    """Record of a task in the registry."""
    id: str
    name: str
    type: TaskType
    location: Path
    created_at: float
    variables: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class TaskRegistry:
    """Registry for managing task locations and history."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize task registry.
        
        Args:
            workspace_root: Optional workspace root directory. If provided, the registry
                          file will be stored in this directory instead of the default
                          system location.
        """
        self._system_paths = SystemPaths()
        if workspace_root:
            self.registry_file = workspace_root / ".benchpro" / "tasks.json"
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.registry_file = self._system_paths.get_state_file("tasks.json")
        self._tasks: Dict[str, TaskRecord] = {}
        self._load_registry()
        logger.debug("Initialized TaskRegistry at %s", self.registry_file)
    
    def _load_registry(self) -> None:
        """Load task registry from disk."""
        if not self.registry_file.exists():
            logger.debug("Registry file not found, creating new registry")
            return
            
        try:
            data = json.loads(self.registry_file.read_text())
            for task_data in data["tasks"]:
                record = TaskRecord(
                    id=task_data["id"],
                    name=task_data["name"],
                    type=TaskType(task_data["type"]),
                    location=Path(task_data["location"]),
                    created_at=task_data["created_at"],
                    variables=task_data.get("variables"),
                    metadata=task_data.get("metadata")
                )
                self._tasks[record.id] = record
            logger.debug("Loaded %d tasks from registry", len(self._tasks))
        except Exception as e:
            logger.error("Failed to load registry: %s", e)
            self._tasks = {}
    
    def _save_registry(self) -> None:
        """Save task registry to disk."""
        try:
            data = {
                "version": "1.0",
                "tasks": [
                    {
                        "id": task.id,
                        "name": task.name,
                        "type": task.type,
                        "location": str(task.location),
                        "created_at": task.created_at,
                        "variables": task.variables,
                        "metadata": task.metadata
                    }
                    for task in self._tasks.values()
                ]
            }
            self.registry_file.write_text(json.dumps(data, indent=2))
            logger.debug("Saved registry with %d tasks", len(self._tasks))
        except Exception as e:
            logger.error("Failed to save registry: %s", e)
    
    def register_task(
        self,
        task_id: str,
        name: str,
        task_type: TaskType,
        location: Path,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskRecord:
        """Register a new task.
        
        Args:
            task_id: Unique task ID
            name: Task name
            task_type: Type of task
            location: Task location
            variables: Optional task variables
            metadata: Optional task metadata
            
        Returns:
            Task record
        """
        record = TaskRecord(
            id=task_id,
            name=name,
            type=task_type,
            location=location,
            created_at=time.time(),
            variables=variables,
            metadata=metadata
        )
        self._tasks[task_id] = record
        self._save_registry()
        logger.debug("Registered task %s at %s", task_id, location)
        return record
    
    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get task record by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task record if found, None otherwise
        """
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        task_type: Optional[TaskType] = None,
        limit: Optional[int] = None
    ) -> List[TaskRecord]:
        """List registered tasks.
        
        Args:
            task_type: Optional filter by task type
            limit: Optional limit on number of tasks to return
            
        Returns:
            List of task records
        """
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        if limit:
            tasks = tasks[:limit]
        return tasks
    
    def prune_history(self, max_tasks: int) -> None:
        """Prune task history to maintain maximum size.
        
        Args:
            max_tasks: Maximum number of tasks to keep
        """
        if len(self._tasks) <= max_tasks:
            return
            
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        to_remove = tasks[max_tasks:]
        
        for task in to_remove:
            del self._tasks[task.id]
        
        self._save_registry()
        logger.debug("Pruned %d tasks from registry", len(to_remove)) 