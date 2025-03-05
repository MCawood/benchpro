"""
Benchmark Task Class for BenchPRO.

This module defines the Benchmark task class for running benchmarks in BenchPRO.
"""

import os
from typing import Dict, Any, Optional, Tuple, List

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.task_base import Task
from benchpro.utils.logger import get_logger


class Benchmark(Task):
    """Task for running benchmarks."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None):
        """
        Initialize the Benchmark task.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
            registry_manager: Optional RegistryManager instance. If None, a new one is created.
        """
        super().__init__(config_manager, template_engine, workspace_manager)
        self.registry_manager = registry_manager or RegistryManager()
        self.logger.debug(f"Benchmark task initialized with RegistryManager: {self.registry_manager.__class__.__name__}")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the benchmark configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid.
        """
        self.logger.info("Validating benchmark configuration")
        
        # Check task_type
        if config.get("task_type") != "benchmark":
            raise ValueError("task_type must be 'benchmark'")
        
        # Use the parent class validate_config method
        return super().validate_config(config)
    
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

        # Create workspace with benchmark task type
        bench_name = self.config["name"]
        
        # Set job name to benchmark name
        if "job" not in self.config:
            self.config["job"] = {}
        # Always set job name to benchmark name
        self.config["job"]["name"] = bench_name
        
        workspace = self.workspace_manager.create_workspace(bench_name, "benchmark")
        
        # Update configuration with workspace paths
        self.config["workspace"] = workspace
        
        # Get application reference from run configuration
        run_config = self.config["run"]
        app_ref = run_config["application"]
        
        # Find application in registry
        app_info = self.registry_manager.find_application_by_name(app_ref)
        if not app_info:
            self.logger.error(f"Application not found: {app_ref}")
            return False, None, ""
        
        self.logger.info(f"Using application: {app_info['name']} {app_info['version']}")
        
        # Update configuration with application information
        run_config["application"] = app_info["binary_path"]
        
        # Determine template to use
        template_name = self.config.get("template")
        if not template_name:
            # Default to using the benchmark name as the template
            template_name = f"{bench_name}.j2"
            self.logger.info(f"No template specified, defaulting to {template_name}")
        
        self.logger.info(f"Using template: {template_name}")
        
        # Generate job script path
        script_path = os.path.join(self.config["workspace"]["workspace_dir"], f"{self.config['job']['name']}_run.sh")
        
        # Generate the job script
        self.generate_script(template_name, script_path)
        
        # Submit the job if not a dry run
        job_id = None
        if not dry_run:
            success, job_id = self.submit_job(script_path)
            if not success:
                self.logger.error("Failed to submit job")
                return False, None, script_path
        else:
            self.logger.info("Dry run: Job not submitted.")
        
        return True, job_id, script_path 