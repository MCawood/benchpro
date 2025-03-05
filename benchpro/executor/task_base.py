"""
Base Task Class for BenchPRO.

This module defines the Task base class for handling common task functionality in BenchPRO.
"""

import os
from typing import Dict, Any, Optional, Tuple, List

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.executor import Executor
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.utils.logger import get_logger
from benchpro.config.validator import ConfigValidator


class Task:
    """Base class for all BenchPRO tasks (applications and benchmarks)."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None):
        """
        Initialize the Task.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.logger.info(f"Initializing {self.__class__.__name__}")
        
        self.config_manager = config_manager or ConfigManager()
        self.template_engine = template_engine or TemplateEngine()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        
        self.logger.debug(f"{self.__class__.__name__} initialized with components:")
        self.logger.debug(f"  - ConfigManager: {self.config_manager.__class__.__name__}")
        self.logger.debug(f"  - TemplateEngine: {self.template_engine.__class__.__name__}")
        self.logger.debug(f"  - WorkspaceManager: {self.workspace_manager.__class__.__name__}")
        
        self.config = {}
        self.workspace = None
        
    def prepare(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the task by loading and validating configuration.
        
        Args:
            profile_name: Name of the profile to use.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            The merged and validated configuration.
            
        Raises:
            FileNotFoundError: If the profile configuration file doesn't exist.
            ValueError: If the configuration validation fails.
        """
        self.logger.info(f"Preparing task for profile: {profile_name}")
        
        # Load and merge configuration
        self.logger.debug("Loading configuration")
        self.config = self.config_manager.merge_configs(profile_name, cli_overrides)
        
        # Validate configuration
        self.logger.debug("Validating configuration")
        self.config = self.validate_config(self.config)
        
        self.logger.info("Task preparation complete")
        return self.config
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the task configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid.
        """
        self.logger.info(f"Validating {self.__class__.__name__.lower()} configuration")
        
        # Use the ConfigValidator to validate the configuration
        validator = ConfigValidator()
        try:
            # Validate the configuration using the ConfigValidator
            return validator.validate(config)
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            raise
    
    def generate_script(self, template_name: str, output_path: str) -> str:
        """
        Generate a job script from a template.
        
        Args:
            template_name: Name of the template to use.
            output_path: Path where the generated script should be saved.
            
        Returns:
            Path to the generated script.
            
        Raises:
            FileNotFoundError: If the template file doesn't exist.
        """
        self.logger.info(f"Generating script from template: {template_name}")
        
        # Ensure scheduler information is available for templates
        if "job" in self.config and "scheduler" not in self.config:
            # Move scheduler information from job to top level for template compatibility
            self.config["scheduler"] = {
                "type": self.config["job"].get("scheduler", "slurm"),
                "queue": self.config["job"].get("queue"),
                "account": self.config["job"].get("account"),
                "nodes": self.config["job"].get("nodes", 1),
                "tasks_per_node": self.config["job"].get("tasks_per_node", 1),
                "time_limit": self.config["job"].get("time_limit", "01:00:00")
            }
        
        # Render the template and write to file
        self.template_engine.write_rendered_template(template_name, self.config, output_path)
        self.logger.info(f"Job script generated: {output_path}")
        
        return output_path
    
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit the job using the appropriate executor.
        
        Args:
            script_path: Path to the job script.
            
        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID (if submitted, None otherwise)
        """
        self.logger.info(f"Submitting job: {script_path}")
        
        try:
            # Get executor type from config (default to scheduler for backward compatibility)
            executor_type = self.config.get("execution", {}).get("type", "scheduler")
            self.logger.debug(f"Using executor type: {executor_type}")
            
            # Create executor instance
            executor = Executor.get_executor(executor_type, self.config.get("scheduler", {}))
            self.logger.debug(f"Created executor: {executor.__class__.__name__}")
            
            # Submit the job
            self.logger.debug("Submitting job to executor")
            success, job_id = executor.submit_job(script_path)
            
            if success:
                self.logger.info(f"Job submitted successfully. Job ID: {job_id}")
            else:
                self.logger.error("Job submission failed")
                
            return success, job_id
            
        except Exception as e:
            self.logger.error(f"Error during job submission: {str(e)}")
            return False, None 