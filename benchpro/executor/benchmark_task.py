"""
Benchmark Task Class for BenchPRO.

This module defines the Benchmark task class for running benchmarks in BenchPRO.
"""

import os
import json
from typing import Dict, Any, Optional, Tuple, List

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.results.result_extractor import ResultExtractor
from benchpro.results.result_capture import ResultCapture
from benchpro.executor.task_base import Task
from benchpro.utils.logger import get_logger
from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager


class Benchmark(Task):
    """Task for running benchmarks."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, 
                 template_engine: Optional[TemplateEngine] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None,
                 result_extractor: Optional[ResultExtractor] = None,
                 result_capture: Optional[ResultCapture] = None,
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None):
        """
        Initialize the Benchmark task.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            template_engine: Optional TemplateEngine instance. If None, a new one is created.
            workspace_manager: Optional WorkspaceManager instance. If None, a new one is created.
            registry_manager: Optional RegistryManager instance. If None, a new one is created.
            result_extractor: Optional ResultExtractor instance. If None, a new one is created.
            result_capture: Optional ResultCapture instance. If None, a new one is created.
            user_dir_manager: Optional UserDirectoryManager instance. If None, uses the default instance.
        """
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        # Create dependencies with the user_dir_manager if not provided
        if config_manager is None:
            config_manager = ConfigManager(user_dir_manager=self.user_dir_manager)
        if template_engine is None:
            template_engine = TemplateEngine(user_dir_manager=self.user_dir_manager)
        if workspace_manager is None:
            workspace_manager = WorkspaceManager(user_dir_manager=self.user_dir_manager)
        if registry_manager is None:
            registry_manager = RegistryManager(user_dir_manager=self.user_dir_manager)
            
        super().__init__(config_manager, template_engine, workspace_manager)
        self.registry_manager = registry_manager
        self.result_extractor = result_extractor or ResultExtractor()
        self.result_capture = result_capture or ResultCapture()
        self.logger.debug(f"Benchmark task initialized with RegistryManager: {self.registry_manager.__class__.__name__}")
        self.logger.debug(f"Benchmark task initialized with ResultExtractor: {self.result_extractor.__class__.__name__}")
        self.logger.debug(f"Benchmark task initialized with ResultCapture: {self.result_capture.__class__.__name__}")
    
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
        
        # Get the profile path and copy it to the workspace
        profile_path = self._get_profile_path(profile_name)
        if profile_path:
            workspace_profile_path = self.workspace_manager.copy_profile_file(profile_path, workspace)
            # Store the profile name in the config for later use
            self.config["profile_name"] = profile_name
            # Store the path to the workspace profile
            self.config["profile_path"] = workspace_profile_path
        
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
        
        # Get the template path and copy it to the workspace if it exists
        template_path = self._get_template_path(template_name)
        if template_path:
            self.workspace_manager.copy_profile_file(template_path, workspace)
        
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
            
            # Record job information for later use without extracting results
            if job_id:
                self.record_job_info(job_id)
        else:
            self.logger.info("Dry run: Job not submitted.")
        
        return True, job_id, script_path
    
    def _get_profile_path(self, profile_name: str) -> str:
        """
        Get the full path to a profile file.
        
        Args:
            profile_name: Name of the profile.
            
        Returns:
            Full path to the profile file, or empty string if not found.
        """
        # Check if profile_name is a path to a YAML file
        if os.path.isfile(profile_name) and profile_name.endswith('.yaml'):
            return profile_name
            
        # Try benchmark directory first
        benchmark_dir = self.user_dir_manager.get_path("inputs_benchmark")
        profile_path = os.path.join(benchmark_dir, f"{profile_name}")
        if not profile_path.endswith('.yaml'):
            profile_path += '.yaml'
            
        if os.path.isfile(profile_path):
            return profile_path
            
        self.logger.warning(f"Profile file not found: {profile_name}")
        return ""
    
    def _get_template_path(self, template_name: str) -> str:
        """
        Get the full path to a template file.
        
        Args:
            template_name: Name of the template.
            
        Returns:
            Full path to the template file, or empty string if not found.
        """
        # Try to find the template in the template directories
        template_dirs = self.template_engine.get_template_dirs()
        
        for template_dir in template_dirs:
            template_path = os.path.join(template_dir, template_name)
            if os.path.isfile(template_path):
                return template_path
                
        self.logger.warning(f"Template file not found: {template_name}")
        return ""
    
    def record_job_info(self, job_id: str) -> None:
        """
        Record job information for later reference.
        
        This method stores basic information about the job without extracting results.
        Results extraction should be done as a separate step after the job completes.
        
        Args:
            job_id: ID of the submitted job.
        """
        self.logger.info(f"Recording job information for job {job_id}")
        
        # Determine log file path
        log_file = os.path.join(
            self.config["workspace"]["workspace_dir"],
            f"{self.config['job']['name']}_run.log"
        )
        
        # Store basic job info in the workspace
        job_info = {
            "job_id": job_id,
            "job_name": self.config["job"]["name"],
            "benchmark_name": self.config["name"],
            "application": self.config["run"]["application"],
            "workspace_dir": self.config["workspace"]["workspace_dir"],
            "log_file": log_file,
            "profile_name": self.config.get("profile_name", ""),
            "profile_path": self.config.get("profile_path", "")
        }
        
        # Save job info to a file in the workspace for later retrieval
        job_info_file = os.path.join(self.config["workspace"]["workspace_dir"], f"{self.config['job']['name']}_job_info.json")
        try:
            with open(job_info_file, 'w') as f:
                json.dump(job_info, f, indent=2)
            self.logger.info(f"Job information saved to {job_info_file}")
        except Exception as e:
            self.logger.error(f"Failed to save job information: {str(e)}")
    
    def process_results(self, job_id: str) -> Dict[str, Any]:
        """
        Process results after job completion.
        
        This method is now deprecated. Results extraction should be done using the 'bp capture' command.
        
        Args:
            job_id: ID of the submitted job.
            
        Returns:
            Dictionary with job information.
        """
        self.logger.warning("The process_results method is deprecated. Use 'bp capture' command for result extraction.")
        return {"job_id": job_id, "warning": "process_results is deprecated"} 