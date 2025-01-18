"""Task management service."""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from benchpro.core.domain.task import Task
from benchpro.core.validation.validators import FileValidator
from benchpro.core.services.logging import get_logger

logger = get_logger("task_manager")

class TaskManager:
    """Service for managing task operations."""
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize task manager.
        
        Args:
            workspace_dir: Root directory for tasks. Defaults to current directory.
        """
        self.workspace_dir = workspace_dir or Path.cwd()
        self.tasks_dir = self.workspace_dir / 'tasks'
        logger.debug("Initialized TaskManager with workspace=%s", self.workspace_dir)
        
    def validate_task_name(self, name: str) -> str:
        """Validate task name contains only allowed characters.
        
        Args:
            name: The task name to validate.
            
        Returns:
            str: The validated task name.
            
        Raises:
            ValueError: If the task name contains invalid characters.
        """
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', name):
            raise ValueError(
                "Invalid task name. Use only letters, numbers, underscores, and hyphens. "
                "Must start with a letter or number."
            )
        return name
        
    def get_task_dir(self, name: str) -> Path:
        """Get the directory for a task.
        
        Args:
            name: Name of the task.
            
        Returns:
            Path to the task directory.
        """
        return self.tasks_dir / name
        
    def get_task(self, name: str) -> Task:
        """Get a task by name.
        
        Args:
            name: The name of the task to retrieve.
            
        Returns:
            Task: The task object with the specified name.
            
        Raises:
            FileNotFoundError: If the task does not exist.
        """
        task_dir = self.get_task_dir(name)
        if not task_dir.exists():
            raise FileNotFoundError(f"Task '{name}' not found")
        
        # Find template path - should be run.sh in task directory
        template_path = task_dir / "run.sh"
        
        # Load task state from file
        state_data = Task.load_state(task_dir)
        
        # Create task with loaded state
        task = Task(
            name=name,
            working_dir=task_dir,
            template_path=template_path,
            state=state_data["state"],
            error=state_data["error"]
        )
        
        return task
        
    def create_task(
        self,
        name: str,
        template_path: Optional[Path] = None,
        working_dir: Optional[Path] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task.
        
        Args:
            name: Name of the task.
            template_path: Optional path to template script.
            working_dir: Optional working directory. Defaults to tasks_dir/name.
            variables: Optional task variables.
            
        Returns:
            The created task.
            
        Raises:
            ValueError: If task name is invalid or template is invalid.
            OSError: If task directory cannot be created.
        """
        # Validate task name
        name = self.validate_task_name(name)
        
        # Use provided working directory or default
        task_dir = working_dir or self.get_task_dir(name)
        logger.debug("Task directory: %s", task_dir)
        
        try:
            # Create task directory and parents
            task_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise OSError("Permission denied when creating directory")
        except Exception as e:
            raise OSError(f"Failed to create task directory: {str(e)}")
        
        # Handle template if provided
        final_template_path = None
        if template_path:
            # Validate template file
            validator = FileValidator(extensions=[".sh"])
            try:
                template_path = validator(Path(template_path))
                # Copy template to task directory as run.sh
                import shutil
                dest_path = task_dir / "run.sh"
                shutil.copy2(template_path, dest_path)
                final_template_path = dest_path
            except ValueError as e:
                raise ValueError(f"Invalid template file: {e}")
            except Exception as e:
                raise OSError(f"Failed to copy template file: {str(e)}")
        
        # Create task
        task = Task(
            name=name,
            working_dir=task_dir,
            template_path=final_template_path,
            variables=variables or {}
        )
        
        return task 