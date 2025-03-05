"""
Application Task Class for BenchPRO.

This module defines the Application task class for building applications in BenchPRO.
"""

import os
import shutil
from typing import Dict, Any, Optional, Tuple, List

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.task_base import Task
from benchpro.utils.logger import get_logger
from benchpro.utils.user_dir import user_dir_manager


class Application(Task):
    """Task for building applications."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None):
        """
        Initialize the Application task.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
            registry_manager: Optional RegistryManager instance. If None, a new one is created.
        """
        super().__init__(config_manager, template_engine, workspace_manager)
        self.registry_manager = registry_manager or RegistryManager()
        self.logger.debug(f"Application task initialized with RegistryManager: {self.registry_manager.__class__.__name__}")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the application configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid.
        """
        self.logger.info("Validating application configuration")
        
        # Check task_type
        if config.get("task_type") != "application":
            raise ValueError("task_type must be 'application'")
        
        # Use the parent class validate_config method
        return super().validate_config(config)
    
    def check_application_exists(self, app_name: str, app_version: str, build_params: Dict[str, Any], force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Check if an application with the given name, version, and build parameters already exists.
        
        Args:
            app_name: Name of the application.
            app_version: Version of the application.
            build_params: Build parameters of the application.
            force: If True, ignore existing applications and return None.
            
        Returns:
            The existing application data if found and force=False, None otherwise.
            
        Raises:
            ValueError: If an application with the same name, version, and build parameters exists and force=False.
        """
        if force:
            return None
            
        # Search for applications with the same name, version, and build parameters
        criteria = {
            "name": app_name,
            "version": app_version,
            "build_parameters": build_params
        }
        
        apps = self.registry_manager.find_applications(criteria)
        
        if apps:
            # Application exists
            app = apps[0]  # Take the first match
            app_id = app.get("id", "unknown")
            
            # If force is False, raise an error
            if not force:
                raise ValueError(f"Application {app_name} {app_version} with the same build parameters already exists in the registry (ID: {app_id})")
                
            return app
            
        return None
    
    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None,
                dry_run: bool = False) -> Tuple[bool, Optional[str], str]:
        """
        Execute the application build.

        Args:
            profile_name: Name of the profile to use.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            dry_run: If True, generate the job script but don't submit it.

        Returns:
            Tuple containing:
                - Success flag (True if successful, False otherwise)
                - Job ID (if submitted, None otherwise)
                - Path to the generated script
        """
        # Prepare configuration
        self.prepare(profile_name, cli_overrides)

        # Extract application info - updated for new schema
        app_name = self.config["name"]
        app_version = self.config["version"]
        build_config = self.config["build"]
        
        # Extract force parameter from build_parameters if present
        force = False
        if cli_overrides and "build_parameters" in cli_overrides:
            force = cli_overrides["build_parameters"].get("force", False)
        
        # Check if application already exists
        build_params = {
            "compiler": build_config.get("compiler", ""),
            "flags": build_config.get("flags", "")
        }
        self.check_application_exists(app_name, app_version, build_params, force)
        
        # Set job name to application name only if not already set
        if "job" not in self.config:
            self.config["job"] = {}
        # Always set job name to application name to avoid using default_job
        self.config["job"]["name"] = app_name
        
        # Create workspace with application task type
        workspace = self.workspace_manager.create_workspace(self.config["job"]["name"], "application")
        
        # Update configuration with workspace paths
        self.config["workspace"] = workspace
        
        # Copy source files to workspace
        source_file = build_config.get("source")
        if source_file:
            # Look for source file in the source directory
            source_dir = user_dir_manager.get_source_directory()
            source_path = os.path.join(source_dir, source_file)
            
            if os.path.exists(source_path):
                self.logger.info(f"Copying source file from {source_path} to workspace")
                os.makedirs(workspace["source_dir"], exist_ok=True)
                shutil.copy(source_path, os.path.join(workspace["source_dir"], source_file))
            else:
                self.logger.error(f"Source file {source_file} not found in source directory: {source_dir}")
                raise FileNotFoundError(f"Source file {source_file} not found in source directory: {source_dir}")
        
        # Determine template to use
        template_name = self.config.get("template")
        if not template_name:
            # Default to using the application name as the template
            template_name = f"{app_name}.j2"
            self.logger.info(f"No template specified, defaulting to {template_name}")
        
        self.logger.info(f"Using template: {template_name}")
        
        # Generate job script path
        script_path = os.path.join(self.config["workspace"]["workspace_dir"], f"{self.config['job']['name']}_build.sh")
        
        # Generate the job script
        self.generate_script(template_name, script_path)
        
        # Submit the job if not a dry run
        job_id = None
        if not dry_run:
            success, job_id = self.submit_job(script_path)
            if not success:
                self.logger.error("Failed to submit job")
                return False, None, script_path
            
            # Register the application in the registry
            app_data = {
                "name": app_name,
                "version": app_version,
                "workspace_dir": workspace["workspace_dir"],
                "binary_path": os.path.join(workspace["build_dir"], build_config["output"]),
                "build_parameters": build_config,
                "metadata": {
                    "description": self.config.get("description", ""),
                    "tags": self.config.get("tags", [])
                }
            }
            
            self.registry_manager.register_application(app_data)
        else:
            self.logger.info("Dry run: Job not submitted.")
        
        return True, job_id, script_path 