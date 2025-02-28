"""
Task Classes for BenchPRO.

This module defines the Task base class and its subclasses (Application and Benchmark)
for handling different types of tasks in BenchPRO.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, List
import shutil

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.executor import Executor
from benchpro.workspace.workspace_manager import WorkspaceManager


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
        self.config_manager = config_manager or ConfigManager()
        self.template_engine = template_engine or TemplateEngine()
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.logger = logging.getLogger(__name__)
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
            ValueError: If the configuration validation fails.
        """
        # Load and merge configurations
        self.config = self.config_manager.merge_configs(profile_name, cli_overrides)
        
        # Validate the merged configuration
        errors = self.validate_config(self.config)
        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        return self.config
    
    def generate_script(self, template_name: str, output_path: str) -> str:
        """
        Generate a job script from a template.
        
        Args:
            template_name: Name of the template to use.
            output_path: Path where the generated script will be saved.
            
        Returns:
            The path to the generated script.
        """
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Render and write the job script
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
        try:
            # Get executor type from config (default to scheduler for backward compatibility)
            executor_type = self.config.get("execution", {}).get("type", "scheduler")
            
            # Create executor instance
            executor = Executor.get_executor(executor_type, self.config.get("scheduler", {}))
            
            # Submit the job
            success, job_id = executor.submit_job(script_path)
            
            if success:
                self.logger.info(f"Job submitted with ID: {job_id}")
            else:
                self.logger.error("Job submission failed")
                
            return success, job_id
            
        except Exception as e:
            self.logger.error(f"Job submission failed: {str(e)}")
            return False, None
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate task-specific configuration.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            List of validation error messages. Empty list if no errors.
        """
        # Base validation - subclasses should extend this
        errors = []
        
        # Check for required top-level keys
        required_keys = ["job"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required configuration section: {key}")
        
        # If using scheduler executor, require scheduler section
        executor_type = config.get("execution", {}).get("type", "scheduler")
        if executor_type.lower() == "scheduler" and "scheduler" not in config:
            errors.append("Missing required configuration section: scheduler")
        
        return errors
    
    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None, 
                dry_run: bool = False) -> Tuple[bool, Optional[str], str]:
        """
        Execute the task.
        
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
        # This method should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement execute()")


class Application(Task):
    """Task for building applications."""
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate application-specific configuration.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            List of validation error messages. Empty list if no errors.
        """
        errors = super().validate_config(config)
        
        # Check for application-specific requirements
        if "application" not in config:
            errors.append("Missing required configuration section: application")
        else:
            app_config = config["application"]
            if "source_dir" not in app_config:
                errors.append("Missing required application configuration: source_dir")
            if "build_script" not in app_config:
                errors.append("Missing required application configuration: build_script")
            if "output_binary" not in app_config:
                errors.append("Missing required application configuration: output_binary")
        
        return errors
    
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
        
        # Create workspace
        job_name = self.config.get("job", {}).get("name", "app_build")
        self.workspace = self.workspace_manager.create_workspace(job_name)
        
        # Update config with workspace paths
        self.config["workspace"] = self.workspace
        
        # Copy input files
        app_config = self.config.get("application", {})
        input_dir = app_config.get("source_dir", "examples/input/hello_world")
        
        # If the source_dir is not in the examples/input directory, assume it's an input directory
        if not input_dir.startswith("examples/input"):
            # Use the original source_dir as the input directory
            self.logger.info(f"Using {input_dir} as input directory")
        else:
            # Use the configured input directory
            self.logger.info(f"Using {input_dir} as input directory")
            
        # Copy files from input directory to workspace
        self.workspace_manager.copy_input_files(input_dir, self.workspace)
        
        # Update paths in config to use workspace
        app_config["source_dir"] = self.workspace["source_dir"]
        
        # Get the binary name from the output_binary path
        binary_name = os.path.basename(app_config.get("output_binary", "app"))
        
        # Set the output binary path to be relative to the source directory
        app_config["output_binary"] = binary_name
        
        # Get executor type
        executor_type = self.config.get("execution", {}).get("type", "scheduler")
        self.logger.info(f"Using executor type: {executor_type}")
        
        # Get template name from config
        template_base = self.config.get("template", {}).get("base_template", "application_build")
        
        # Remove .j2 extension if present
        if template_base.endswith(".j2"):
            template_base = template_base[:-3]
        
        # Adjust template name based on executor type
        if executor_type.lower() == "local":
            template_name = f"{template_base}_local.j2"
        else:
            template_name = f"{template_base}.j2"
            
        self.logger.info(f"Using template: {template_name}")
        
        # Generate job script path in the workspace logs directory
        script_path = os.path.join(self.workspace["logs_dir"], f"{job_name}_build.sh")
        
        # Generate the build script
        self.generate_script(template_name, script_path)
        
        # If dry run, don't submit the job
        if dry_run:
            self.logger.info("Dry run: Job not submitted.")
            return True, None, script_path
        
        # Submit the job
        success, job_id = self.submit_job(script_path)
        return success, job_id, script_path


class Benchmark(Task):
    """Task for running benchmarks using built applications."""
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate benchmark-specific configuration.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            List of validation error messages. Empty list if no errors.
        """
        errors = super().validate_config(config)
        
        # Check for benchmark-specific requirements
        if "benchmark" not in config:
            errors.append("Missing required configuration section: benchmark")
        else:
            bench_config = config["benchmark"]
            if "application" not in bench_config:
                errors.append("Missing required benchmark configuration: application")
            if "input_params" not in bench_config:
                # Input params can be empty but should be defined
                bench_config["input_params"] = ""
        
        return errors
    
    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None, 
                dry_run: bool = False) -> Tuple[bool, Optional[str], str]:
        """
        Execute the benchmark run.
        
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
        
        # Create workspace
        job_name = self.config.get("job", {}).get("name", "benchmark_run")
        self.workspace = self.workspace_manager.create_workspace(job_name)
        
        # Update config with workspace paths
        self.config["workspace"] = self.workspace
        
        # Update benchmark paths
        bench_config = self.config.get("benchmark", {})
        bench_config["output_dir"] = self.workspace["results_dir"]
        
        # If the benchmark uses an application, copy it to the workspace
        if "application" in bench_config:
            app_binary = bench_config["application"]
            # If the application is a path, copy it to the workspace
            if os.path.exists(app_binary):
                dest_path = os.path.join(self.workspace["build_dir"], os.path.basename(app_binary))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(app_binary, dest_path)
                self.logger.info(f"Copied application binary from {app_binary} to {dest_path}")
                # Update the application path to just the binary name
                bench_config["application"] = os.path.basename(app_binary)
        
        # Get executor type
        executor_type = self.config.get("execution", {}).get("type", "scheduler")
        self.logger.info(f"Using executor type: {executor_type}")
        
        # Get template name from config
        template_base = self.config.get("template", {}).get("base_template", "benchmark_run")
        
        # Remove .j2 extension if present
        if template_base.endswith(".j2"):
            template_base = template_base[:-3]
        
        # Adjust template name based on executor type
        if executor_type.lower() == "local":
            template_name = f"{template_base}_local.j2"
        else:
            template_name = f"{template_base}.j2"
            
        self.logger.info(f"Using template: {template_name}")
        
        # Generate job script path in the workspace logs directory
        script_path = os.path.join(self.workspace["logs_dir"], f"{job_name}_run.sh")
        
        # Generate the run script
        self.generate_script(template_name, script_path)
        
        # If dry run, don't submit the job
        if dry_run:
            self.logger.info("Dry run: Job not submitted.")
            return True, None, script_path
        
        # Submit the job
        success, job_id = self.submit_job(script_path)
        return success, job_id, script_path


class TaskFactory:
    """Factory for creating appropriate task instances."""
    
    @staticmethod
    def create_task(task_type: str, config_manager: Optional[ConfigManager] = None, 
                    template_engine: Optional[TemplateEngine] = None,
                    workspace_manager: Optional[WorkspaceManager] = None) -> Task:
        """
        Create a task instance based on the task type.
        
        Args:
            task_type: Type of task to create ("application" or "benchmark").
            config_manager: Optional ConfigManager instance.
            template_engine: Optional TemplateEngine instance.
            workspace_manager: Optional WorkspaceManager instance.
            
        Returns:
            Task instance of the appropriate type.
            
        Raises:
            ValueError: If the task type is not supported.
        """
        if task_type.lower() == "application":
            return Application(config_manager, template_engine, workspace_manager)
        elif task_type.lower() == "benchmark":
            return Benchmark(config_manager, template_engine, workspace_manager)
        else:
            raise ValueError(f"Unsupported task type: {task_type}") 