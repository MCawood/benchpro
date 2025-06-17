"""
Composition-Based Task Classes for BenchPRO.

This module defines the composition-based Task classes for BenchPRO, using the component
interfaces to enable more flexible and testable implementation.
"""

import os
import json
import time
import logging
import copy
from typing import Dict, Any, Optional, Tuple, List

from benchpro.executor.components.interfaces import (
    ConfigComponent, ValidationComponent, ExecutionComponent,
    ConfigError, ValidationError, ExecutionError
)
from benchpro.templates.script_generators import ScriptGenerationComponent
from benchpro.templates.blocks import TemplateError
from benchpro.utils.logger import get_logger
from benchpro.registry.registry_manager import RegistryManager


class Task:
    """
    Base class for all BenchPRO tasks, using component composition.
    
    This implementation uses composition rather than inheritance, accepting components
    that handle specific responsibilities as dependencies.
    """
    
    def __init__(self, 
                 config_component: ConfigComponent,
                 validation_component: ValidationComponent,
                 script_generation_component: ScriptGenerationComponent,
                 execution_component: ExecutionComponent):
        """
        Initialize the Task with its component dependencies.
        
        Args:
            config_component: Component for loading and managing configuration.
            validation_component: Component for validating configuration.
            script_generation_component: Component for generating scripts.
            execution_component: Component for executing scripts.
        """
        self.logger = get_logger(__name__)
        self.logger.info(f"Initializing {self.__class__.__name__} with component architecture")
        
        # Store component dependencies
        self.config_component = config_component
        self.validation_component = validation_component
        self.script_generation_component = script_generation_component
        self.execution_component = execution_component
        
        # Log component types for debugging
        self.logger.debug(f"{self.__class__.__name__} initialized with components:")
        self.logger.debug(f"  Config component: {type(config_component).__name__}")
        self.logger.debug(f"  Validation component: {type(validation_component).__name__}")
        self.logger.debug(f"  Script generation component: {type(script_generation_component).__name__}")
        self.logger.debug(f"  Execution component: {type(execution_component).__name__}")
    
    def run(self, force_override: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Run the task.
        
        Args:
            force_override: Force override of validator checks if true.
            
        Returns:
            A tuple containing:
                - True if the task was submitted successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
                
        Raises:
            ConfigError: If the configuration could not be loaded.
            ValidationError: If the configuration is invalid and force_override is False.
            TemplateError: If the script generation fails.
            ExecutionError: If the task execution fails.
        """
        # Get the current configuration
        try:
            config = self.config_component.get_config()
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise ConfigError(f"Failed to load configuration: {str(e)}")
        
        # Validate the configuration
        if not force_override:
            try:
                is_valid, errors = self.validation_component.validate(config)
                if not is_valid:
                    self.logger.error(f"Configuration validation failed: {errors}")
                    raise ValidationError(f"Configuration validation failed: {errors}")
            except Exception as e:
                self.logger.error(f"Error during validation: {str(e)}")
                raise ValidationError(f"Error during validation: {str(e)}")
        
        # Generate script from template
        try:
            # Get template file and output paths from derived implementations
            template_path, script_path = self._get_template_and_script_paths()
            
            # Generate the script
            self.generate_script(template_path, script_path)
        except Exception as e:
            self.logger.error(f"Error generating script: {str(e)}")
            raise TemplateError(f"Error generating script: {str(e)}")
        
        # Execute the script
        try:
            success, job_id = self.execution_component.execute(script_path)
            if success:
                self.logger.info(f"Task submitted successfully with job ID: {job_id}")
            else:
                self.logger.error("Task submission failed")
            
            return success, job_id
        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
            raise ExecutionError(f"Error executing task: {str(e)}")
    
    def generate_script(self, template_path: str, output_path: str) -> str:
        """
        Generate a job script from a template.
        
        Args:
            template_path: Path to the template file.
            output_path: Path where the generated script should be written.
            
        Returns:
            Path to the generated script.
            
        Raises:
            TemplateError: If the script generation fails.
        """
        self.logger.info(f"Generating script from template: {template_path}")
        
        try:
            # Get the current configuration
            config = self.config_component.get_config()
            
            # Prepare variables for the template
            variables = self.script_generation_component.prepare_variables(config)
            
            # Generate the script content
            script_content = self.script_generation_component.generate_script(
                template_path, variables
            )
            
            # Write script content to file
            with open(output_path, 'w') as f:
                f.write(script_content)
            
            # Make the script executable
            os.chmod(output_path, 0o755)
            
            self.logger.info(f"Script generated and saved to: {output_path}")
            
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to generate script: {str(e)}")
            raise TemplateError(f"Failed to generate script: {str(e)}")
    
    def _get_template_and_script_paths(self) -> Tuple[str, str]:
        """
        Get the template and script paths for this task.
        
        This method should be implemented by derived classes.
        
        Returns:
            A tuple containing the template path and script path.
            
        Raises:
            NotImplementedError: If this method is not implemented by the derived class.
        """
        raise NotImplementedError("Derived classes must implement _get_template_and_script_paths")

    def prepare(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the task by loading and validating configuration.
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            The prepared configuration dictionary.
            
        Raises:
            ConfigError: If configuration loading fails.
            ValidationError: If configuration validation fails.
        """
        self.logger.debug(f"Preparing task with profile: {profile_name}")
        
        # Save current workspace configuration before loading
        current_config = self.config_component.get_config()
        workspace_config = current_config.get("workspace", {})
        has_workspace_dir = "workspace_dir" in workspace_config
        
        if has_workspace_dir:
            self.logger.debug(f"Preserving workspace_dir: {workspace_config['workspace_dir']}")
        
        # Load configuration
        try:
            config = self.config_component.load_config(profile_name)
            self.logger.debug("Configuration loaded successfully")
            
            # Merge with CLI overrides if present
            if cli_overrides:
                self.logger.debug("Merging with CLI overrides")
                config = self.config_component.merge_config(cli_overrides)
                self.logger.debug("Configuration merged successfully")
            
            # Restore workspace configuration if it was present
            if has_workspace_dir:
                if "workspace" not in config:
                    config["workspace"] = {}
                config["workspace"].update(workspace_config)
                self.logger.debug(f"Restored workspace configuration with workspace_dir: {workspace_config['workspace_dir']}")
                
            # Validate configuration
            is_valid, errors = self.validation_component.validate(config)
            
            if not is_valid:
                error_msg = f"Configuration validation failed: {errors}"
                self.logger.error(error_msg)
                raise ValidationError(error_msg)
                
            self.logger.debug("Configuration validated successfully")
            
            return config
        except ConfigError as e:
            self.logger.error(f"Failed to load or merge configuration: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during task preparation: {str(e)}")
            raise
            
    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit a job script for execution.
        
        Args:
            script_path: Path to the script to submit.
            
        Returns:
            A tuple containing:
                - True if the job was submitted successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the job submission fails.
        """
        self.logger.debug(f"Submitting job script: {script_path}")
        
        try:
            # Get the workspace from the configuration if available
            config = self.config_component.get_config()
            workspace = config.get("workspace", None)
            
            # Submit the job with workspace if available
            success, job_id = self.execution_component.execute(script_path, workspace)
            
            if success:
                self.logger.info(f"Job submitted successfully with ID: {job_id}")
            else:
                self.logger.warning("Job submission failed")
                
            return success, job_id
        except Exception as e:
            self.logger.error(f"Error submitting job: {str(e)}")
            raise ExecutionError(f"Error submitting job: {str(e)}")
    
    def get_job_status(self, job_id: str) -> str:
        """
        Get the status of a submitted job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Job status as a string.
            
        Raises:
            ExecutionError: If retrieving the job status fails.
        """
        self.logger.debug(f"Getting status for job: {job_id}")
        
        try:
            status = self.execution_component.get_status(job_id)
            self.logger.debug(f"Job status: {status}")
            return status
        except Exception as e:
            self.logger.error(f"Error getting job status: {str(e)}")
            raise ExecutionError(f"Error getting job status: {str(e)}")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a submitted job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was canceled successfully, False otherwise.
            
        Raises:
            ExecutionError: If canceling the job fails.
        """
        self.logger.debug(f"Canceling job: {job_id}")
        
        try:
            success = self.execution_component.cancel_job(job_id)
            
            if success:
                self.logger.info(f"Job {job_id} canceled successfully")
            else:
                self.logger.warning(f"Failed to cancel job {job_id}")
                
            return success
        except Exception as e:
            self.logger.error(f"Error canceling job: {str(e)}")
            raise ExecutionError(f"Error canceling job: {str(e)}")


class Application(Task):
    """
    Application task implementation.
    
    This task type is responsible for building and installing applications.
    """
    
    def run(self, is_local_execution: bool = True, cleanup: bool = True):
        """
        Run the Task and set run results. For an Application, this involves building 
        the application, creating a module file, registering with the registry,
        and optionally submitting a test job.
        
        Args:
            is_local_execution: Flag indicating if execution is local.
            cleanup: Flag indicating if cleanup should be performed.
            
        Returns:
            A tuple containing:
                - True if the application was run successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
        """
        self.logger.info("Starting application run process")
        
        # Get the configuration
        config = self.config_component.get_config()
        
        # Get the application name and version
        app_name = config.get("name", "unknown")
        app_version = config.get("version", "1.0")
        
        # Get the workspace directory directly from configuration - it should be there
        # since the TaskOrchestrator already set it
        if "workspace" not in config or "workspace_dir" not in config["workspace"]:
            self.logger.error("No workspace directory defined in configuration")
            return False, None
            
        workspace_dir = config["workspace"]["workspace_dir"]
        # Ensure it's an absolute path
        if not os.path.isabs(workspace_dir):
            workspace_dir = os.path.abspath(workspace_dir)
            
        self.logger.info(f"Using workspace directory: {workspace_dir}")
        
        # First build the application using the parent class build method
        self.logger.info("Starting build process")
        build_result = super().run(is_local_execution, cleanup)
        if not build_result:
            self.logger.error("Application build failed")
            return False, None

        # Create the module file
        module_file = self._create_module_file(app_name, app_version, workspace_dir, config)
        if not module_file:
            self.logger.warning("Continuing despite module file creation failure")
            
        # Register the application with the registry
        app_id = self._register_application(app_name, app_version, workspace_dir, config)
        if not app_id:
            self.logger.error("Application registration failed")
            return False, None
        
        # Variable to store job ID if a job is submitted
        job_id = None
            
        # Submit a test job if specified
        if config.get("test_job", {}).get("submit", False):
            self.logger.info("Submitting test job")
            
            # Generate the test job script path
            test_script_path = self._generate_test_script(app_name, app_version, workspace_dir)
            if not test_script_path:
                self.logger.error("Failed to generate test script")
                return False, None
                
            # Submit the test job
            job_success, job_id = self.submit_job(test_script_path)
            if not job_success:
                self.logger.error("Test job submission failed")
                return False, None
            else:
                self.logger.info(f"Test job submitted successfully with ID: {job_id}")
        
        self.logger.info("Application run successfully")
        return True, job_id
        
    def _create_module_file(self, app_name: str, app_version: str, workspace_dir: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Create a module file for the application.
        
        Args:
            app_name: Application name.
            app_version: Application version.
            workspace_dir: Workspace directory path.
            config: Application configuration.
            
        Returns:
            Path to the created module file, or None if creation failed.
        """
        try:
            from benchpro.workspace.module_manager import ModuleManager
            module_manager = ModuleManager()
            
            # Create binary path
            binary_path = os.path.join(workspace_dir, app_name)
            
            # Extract module dependencies directly from config
            dependencies = module_manager.extract_dependencies_from_config(config)
            
            # Extract module paths from config
            module_paths = module_manager.extract_module_paths_from_config(config)
            
            # Create the module file with direct parameters
            module_file = module_manager.create_module_file(
                app_name,
                app_version,
                workspace_dir,
                dependencies,
                binary_path,
                module_paths
            )
            
            self.logger.info(f"Created module file: {module_file}")
            return module_file
            
        except Exception as e:
            self.logger.error(f"Failed to create module file: {str(e)}")
            return None
            
    def _register_application(self, app_name: str, app_version: str, workspace_dir: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Register the application with the registry.
        
        Args:
            app_name: Application name.
            app_version: Application version.
            workspace_dir: Workspace directory path.
            config: Application configuration.
            
        Returns:
            The application ID if registration was successful, None otherwise.
        """
        try:
            from benchpro.registry.registry_manager import RegistryManager
            registry_manager = RegistryManager()
            
            # Register the application with the simplified approach
            app_id = registry_manager.register_application(
                {
                    "name": app_name,
                    "version": app_version,
                    "workspace_dir": workspace_dir,
                    "binary_path": os.path.join(workspace_dir, app_name),
                    "environment": config.get("environment", {"modules": []})
                }
            )
            
            if app_id:
                self.logger.info(f"Registered application {app_name}/{app_version} with registry, ID: {app_id}")
                return app_id
            else:
                self.logger.error(f"Application registration failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to register application: {str(e)}")
            return None
            
    def _generate_test_script(self, app_name: str, app_version: str, workspace_dir: str) -> Optional[str]:
        """
        Generate a test script for the application.
        
        Args:
            app_name: Application name.
            app_version: Application version.
            workspace_dir: Workspace directory path.
            
        Returns:
            Path to the generated test script, or None if generation failed.
        """
        try:
            # Create a simple test script that loads the module and runs the application
            test_script_path = os.path.join(workspace_dir, f"{app_name}-{app_version}_test.sh")
            
            # Use the script generation component to generate a proper test script
            # For now, create a simple script with basic commands
            with open(test_script_path, 'w') as f:
                f.write("#!/bin/bash\n\n")
                f.write(f"# Test script for {app_name} {app_version}\n")
                f.write(f"# Generated by BenchPRO\n\n")
                f.write(f"# Load the module\n")
                f.write(f"module use {workspace_dir}/modulefiles\n")
                f.write(f"module load {app_name}/{app_version}\n\n")
                f.write(f"# Run the application\n")
                f.write(f"{app_name} --test\n")
                
            # Make the script executable
            os.chmod(test_script_path, 0o755)
            
            self.logger.info(f"Generated test script: {test_script_path}")
            return test_script_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate test script: {str(e)}")
            return None
    
    def _get_template_and_script_paths(self) -> Tuple[str, str]:
        """
        Get the template and script paths for the application task.
        
        Returns:
            A tuple containing the template path and script path.
        """
        # Get configuration
        config = self.config_component.get_config()
        
        # Extract template and script information
        name = config.get("name", "unknown")
        version = config.get("version", "unknown")
        
        template = config.get("build", {}).get("template", f"{name}.j2")
        script_name = f"{name}-{version}_build.sh"
        
        workspace_dir = config.get("workspace", {}).get("dir", ".")
        script_path = os.path.join(workspace_dir, script_name)
        
        # Find template path
        # This is a simplified example; in a real implementation, you would search for the template
        template_path = template
        
        self.logger.debug(f"Application template path: {template_path}")
        self.logger.debug(f"Application script path: {script_path}")
        
        return template_path, script_path

    def prepare(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the application task by loading, validating configuration, and verifying modules.
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            The prepared configuration dictionary.
            
        Raises:
            ConfigError: If configuration loading fails.
            ValidationError: If configuration validation fails.
            ModuleError: If module validation fails.
        """
        from benchpro.workspace.module_manager import ModuleManager, ModuleError
        
        # First, perform standard preparation from the parent class
        config = super().prepare(profile_name, cli_overrides)
        
        # Validate module dependencies if present
        if "environment" in config and "modules" in config["environment"] and config["environment"]["modules"]:
            self.logger.info("Validating module dependencies")
            
            # Create a ModuleManager instance
            module_manager = ModuleManager()
            
            # Extract modules and module paths
            modules = config["environment"]["modules"]
            module_paths = config["environment"].get("module_paths", [])
            
            # Validate modules
            valid, error = module_manager.validate_modules(modules, module_paths)
            if not valid:
                error_msg = f"Module validation failed: {error}"
                self.logger.error(error_msg)
                raise ModuleError(error_msg)
                
            self.logger.info("Module dependencies validated successfully")
            
        return config

    def submit_job(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Submit a job using the application.
        
        This method submits a job using the script path provided.
        
        Args:
            script_path: Path to the script to submit.
            
        Returns:
            A tuple containing:
                - True if the job was submitted successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
        """
        self.logger.info(f"Submitting job using script: {script_path}")
        
        # Verify the script exists
        if not os.path.exists(script_path):
            self.logger.error(f"Script does not exist: {script_path}")
            return False, None
            
        # Call the parent submit_job method to perform the actual submission
        try:
            return super().submit_job(script_path)
        except Exception as e:
            self.logger.error(f"Error submitting job: {str(e)}")
            return False, None


class Benchmark(Task):
    """
    Benchmark task implementation.
    
    This task type is responsible for running benchmarks.
    """
    
    def prepare(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the benchmark task by loading, validating configuration, and resolving application dependencies.
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            The prepared configuration dictionary.
            
        Raises:
            ConfigError: If configuration loading fails.
            ValidationError: If configuration validation fails.
            ApplicationNotFoundError: If the referenced application cannot be found in the registry.
        """
        # First, perform standard preparation from the parent class
        config = super().prepare(profile_name, cli_overrides)
        
        # Check if this benchmark has requirements for an application
        has_app_requirement = False
        if "requirements" in config and config["requirements"]:
            requirements = config["requirements"]
            if "application" in requirements and requirements["application"]:
                has_app_requirement = True
                app_name = requirements["application"]
                
                # Resolve application dependency from requirements
                app_info = self._resolve_application_requirements(config)
                
                # If the application was specified but not found, raise an error
                if not app_info:
                    error_msg = f"Required application '{app_name}' not found in registry"
                    self.logger.error(error_msg)
                    raise ApplicationNotFoundError(error_msg)
                
                # Store the application info in the config for later use
                if "dependencies" not in config:
                    config["dependencies"] = {}
                config["dependencies"]["application"] = app_info
                
                # Setup module environment for the application
                self._setup_application_module_environment(config, app_info)
        
        # If no application requirements, just log a debug message
        if not has_app_requirement:
            self.logger.debug("No application requirements specified for this benchmark")
        
        # Normalize module formats to simplify templates
        self._normalize_module_formats(config)
                
        return config
    
    def _normalize_module_formats(self, config: Dict[str, Any]) -> None:
        """
        Normalize module formats to simplify templates.
        
        This converts all modules to a standard format of "name/version",
        eliminating the need for complex conditionals in templates.
        
        Args:
            config: Configuration dictionary.
        """
        if "environment" not in config or "modules" not in config["environment"]:
            return
            
        normalized_modules = []
        
        for module in config["environment"]["modules"]:
            if isinstance(module, dict) and "name" in module:
                # Convert dict format to string format
                if "version" in module and module["version"]:
                    normalized_modules.append(f"{module['name']}/{module['version']}")
                else:
                    normalized_modules.append(module["name"])
            elif isinstance(module, str):
                # Already in string format
                normalized_modules.append(module)
            else:
                self.logger.warning(f"Skipping invalid module format: {module}")
                
        # Replace modules with normalized version
        config["environment"]["modules"] = normalized_modules
        self.logger.debug(f"Normalized {len(normalized_modules)} modules to standard string format")
    
    def _resolve_application_requirements(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Resolve application dependency based on requirements section.
        
        Args:
            config: Configuration dictionary.
            
        Returns:
            Application information dictionary if found, None otherwise.
        """
        # Check if requirements section exists
        if "requirements" not in config or not config["requirements"]:
            self.logger.debug("No requirements section found in benchmark config")
            return None
            
        requirements = config["requirements"]
        app_name = requirements.get("application")
        
        if not app_name:
            self.logger.debug("No application specified in requirements")
            return None
            
        self.logger.info(f"Resolving application dependency: {app_name}")
        
        try:
            # Build search criteria
            search_criteria = {"name": app_name}
            
            # Add optional version filter
            if "version" in requirements and requirements["version"]:
                search_criteria["version"] = requirements["version"]
                
            # Add optional label filter (simplified from metadata.label)
            if "label" in requirements and requirements["label"]:
                search_criteria["label"] = requirements["label"]
            
            # Search the registry
            registry_manager = RegistryManager()
            matching_apps = registry_manager.find_applications(search_criteria)
            
            # Handle search results
            if not matching_apps:
                self.logger.warning(f"No applications matching criteria: {search_criteria}")
                return None
            
            if len(matching_apps) > 1:
                self.logger.info(f"Multiple applications match criteria: {search_criteria}. Using the most recent.")
                # Sort by build timestamp, newest first
                matching_apps.sort(key=lambda app: app.get("build_timestamp", ""), reverse=True)
            
            app_info = matching_apps[0]
            self.logger.info(f"Found application: {app_info.get('name')} (ID: {app_info.get('id', 'unknown')})")
            return app_info
            
        except Exception as e:
            self.logger.error(f"Error resolving application dependency: {str(e)}")
            
        return None
    
    def _setup_application_module_environment(self, config: Dict[str, Any], app_info: Dict[str, Any]) -> None:
        """
        Setup module environment for the application.
        
        Args:
            config: Configuration dictionary.
            app_info: Application information dictionary.
        """
        # Ensure environment section exists
        if "environment" not in config:
            config["environment"] = {}
            
        # Ensure modules section exists
        if "modules" not in config["environment"]:
            config["environment"]["modules"] = []
            
        # Ensure module_paths section exists
        if "module_paths" not in config["environment"]:
            config["environment"]["module_paths"] = []
            
        # Get application name and version
        app_name = app_info.get("name")
        app_version = app_info.get("version", "1.0")
        
        # First, add any custom module paths from the application's environment
        app_environment = app_info.get("environment", {})
        app_module_paths = app_environment.get("module_paths", [])
        
        for module_path in app_module_paths:
            if module_path not in config["environment"]["module_paths"]:
                config["environment"]["module_paths"].append(module_path)
                self.logger.info(f"Added custom module path: {module_path}")
        
        # Handle the application's module file
        
        # Check if the application has a module file
        module_file = app_info.get("module_file")
        if module_file:
            self.logger.info(f"Using application module file: {module_file}")
            
            # Get the module directory (parent of the parent of the module file)
            # e.g., /path/to/modulefiles/app_name/version.lua -> /path/to/modulefiles
            module_dir = os.path.dirname(os.path.dirname(module_file))
            
            # Add the module directory to module_paths
            if module_dir not in config["environment"]["module_paths"]:
                config["environment"]["module_paths"].append(module_dir)
                self.logger.info(f"Added module directory: {module_dir}")
            
            # Create the app module string (app_name/version)
            app_module = f"{app_name}/{app_version}"
            
            # Add the application module to the list of modules to load
            if app_module not in config["environment"]["modules"]:
                config["environment"]["modules"].append(app_module)
                self.logger.info(f"Added application module: {app_module}")
        else:
            # If no module_file is specified directly, check for a modulefiles directory in the workspace
            workspace_dir = app_info.get("workspace_dir")
            if workspace_dir:
                modulefiles_dir = os.path.join(workspace_dir, "modulefiles")
                if os.path.isdir(modulefiles_dir):
                    self.logger.info(f"Using application modulefiles directory: {modulefiles_dir}")
                    
                    # Add the modulefiles directory to module_paths
                    if modulefiles_dir not in config["environment"]["module_paths"]:
                        config["environment"]["module_paths"].append(modulefiles_dir)
                        self.logger.info(f"Added modulefiles directory: {modulefiles_dir}")
                    
                    # Create the app module string (app_name/version)
                    app_module = f"{app_name}/{app_version}"
                    
                    # Add the application module to the list of modules to load
                    if app_module not in config["environment"]["modules"]:
                        config["environment"]["modules"].append(app_module)
                        self.logger.info(f"Added application module: {app_module}")
                else:
                    self.logger.warning(f"Application does not have a modulefiles directory: {modulefiles_dir}")
            else:
                self.logger.warning("Application does not have a module file or workspace directory")
                
        # We no longer merge the application's environment modules with the benchmark's environment
        # as the application module will load its dependencies automatically
        self.logger.info(f"Application module {app_name}/{app_version} will load its dependencies automatically")
    
    def _get_template_and_script_paths(self) -> Tuple[str, str]:
        """
        Get the template and script paths for the benchmark task.
        
        Returns:
            A tuple containing the template path and script path.
        """
        # Get configuration
        config = self.config_component.get_config()
        
        # Extract template and script information
        name = config.get("name", "unknown")
        version = config.get("version", "unknown")
        
        template = config.get("template", f"{name}.j2")
        script_name = f"{name}-{version}_run.sh"
        
        workspace_dir = config.get("workspace", {}).get("workspace_dir", ".")
        script_path = os.path.join(workspace_dir, script_name)
        
        # Find template path
        # This is a simplified example; in a real implementation, you would search for the template
        template_path = template
        
        self.logger.debug(f"Benchmark template path: {template_path}")
        self.logger.debug(f"Benchmark script path: {script_path}")
        
        return template_path, script_path


class ApplicationNotFoundError(Exception):
    """Exception raised when a required application cannot be found in the registry."""
    pass 