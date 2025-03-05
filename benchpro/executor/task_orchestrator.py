"""
Task Orchestrator for BenchPRO.

This module orchestrates the execution of tasks by integrating configuration, templating, and job submission.
"""

import os
from typing import Dict, Any, Optional, Tuple

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.task_factory import TaskFactory
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.logger import get_logger


class TaskOrchestrator:
    """
    Orchestrates the execution of tasks by integrating configuration, templating, and job submission.
    This class coordinates the workflow for both application builds and benchmark runs.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None):
        """
        Initialize the TaskOrchestrator.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
            registry_manager: Optional RegistryManager instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing TaskOrchestrator")
        
        self.config_manager = config_manager or ConfigManager()
        self.template_engine = template_engine or TemplateEngine()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.registry_manager = registry_manager or RegistryManager()
        
        self.logger.debug("TaskOrchestrator initialized with components:")
        self.logger.debug(f"  - ConfigManager: {self.config_manager.__class__.__name__}")
        self.logger.debug(f"  - TemplateEngine: {self.template_engine.__class__.__name__}")
        self.logger.debug(f"  - WorkspaceManager: {self.workspace_manager.__class__.__name__}")
        self.logger.debug(f"  - RegistryManager: {self.registry_manager.__class__.__name__}")
        
    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None, 
                dry_run: bool = False) -> Tuple[bool, Optional[str], str]:
        """
        Orchestrate the execution of a task for the specified profile.
        
        Args:
            profile_name: Name of the profile to use.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            dry_run: If True, generate the job script but don't submit it.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID (if submitted, None otherwise)
                - Path to the generated script
                
        Raises:
            FileNotFoundError: If the profile configuration file doesn't exist.
            ValueError: If the configuration validation fails.
        """
        self.logger.info(f"Orchestrating task execution for profile: {profile_name}")
        self.logger.debug(f"CLI overrides: {cli_overrides}")
        self.logger.debug(f"Dry run: {dry_run}")
        
        try:
            # Get task type from CLI overrides if specified
            task_type = cli_overrides.get("task_type") if cli_overrides else None
            
            # Load basic profile info to determine task type
            self.logger.debug(f"Loading profile configuration: {profile_name}")
            profile_config = self.config_manager.load_profile_config(profile_name, task_type)
            
            # If task_type not specified in CLI overrides, get it from the profile
            if not task_type:
                task_type = profile_config.get("task_type", "benchmark")  # Default to benchmark for backward compatibility
            
            self.logger.info(f"Task type determined: {task_type}")
            
            # Create appropriate task instance
            self.logger.debug(f"Creating task of type: {task_type}")
            task_factory = TaskFactory(
                config_manager=self.config_manager,
                template_engine=self.template_engine,
                workspace_manager=self.workspace_manager,
                registry_manager=self.registry_manager
            )
            task = task_factory.create_task(task_type)
            self.logger.debug(f"Task created: {task.__class__.__name__}")
            
            # Execute the task
            self.logger.info(f"Executing {task_type} task")
            result = task.execute(profile_name, cli_overrides, dry_run)
            
            success, job_id, script_path = result
            if success:
                self.logger.info(f"Task execution successful. Job ID: {job_id}, Script: {script_path}")
            else:
                self.logger.error(f"Task execution failed. Script: {script_path}")
                
            return result
            
        except FileNotFoundError as e:
            self.logger.error(f"Profile not found: {str(e)}")
            raise
        except ValueError as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error during execution: {str(e)}")
            raise 