"""
Build Executor for BenchPRO.

This module integrates configuration, templating, and job submission to execute a build.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.task import TaskFactory
from benchpro.workspace.workspace_manager import WorkspaceManager


class BuildExecutor:
    """
    Executes builds by integrating configuration, templating, and job submission.
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None):
        """
        Initialize the BuildExecutor.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
        """
        self.config_manager = config_manager or ConfigManager()
        self.template_engine = template_engine or TemplateEngine()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.logger = logging.getLogger(__name__)
        
    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None, 
                dry_run: bool = False) -> Tuple[bool, Optional[str], str]:
        """
        Execute a build for the specified profile.
        
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
        try:
            # Load basic profile info to determine task type
            profile_config = self.config_manager.load_profile_config(profile_name)
            task_type = profile_config.get("task_type", "benchmark")  # Default to benchmark for backward compatibility
            
            # Create appropriate task instance
            task = TaskFactory.create_task(
                task_type, 
                self.config_manager, 
                self.template_engine,
                self.workspace_manager
            )
            
            # Execute the task
            return task.execute(profile_name, cli_overrides, dry_run)
            
        except FileNotFoundError as e:
            self.logger.error(f"Profile not found: {str(e)}")
            raise
        except ValueError as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error during execution: {str(e)}")
            raise 