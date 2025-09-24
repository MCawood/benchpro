import os
import sys
import time
from typing import Dict, Any, Optional, Tuple

from benchpro.config.config_manager import ConfigManager
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import get_user_dir_manager
from benchpro.executor.task_factory import TaskFactory
from benchpro.utils.logger import get_logger
from benchpro.config.report_generator import ParameterReportDisplay

class TaskOrchestrator:
    """
    Orchestrates task execution in BenchPRO.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 workspace_manager: Optional[WorkspaceManager] = None,
                 registry_manager: Optional[RegistryManager] = None):
        """
        Initialize the task orchestrator.
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing TaskOrchestrator")

        self.user_dir_manager = get_user_dir_manager()
        self.config_manager = config_manager or ConfigManager(user_dir_manager=self.user_dir_manager)
        self.workspace_manager = workspace_manager or WorkspaceManager(user_dir_manager=self.user_dir_manager)
        self.registry_manager = registry_manager or RegistryManager(workspace_manager=self.workspace_manager)

        # The TaskFactory is now created with the orchestrator's managers,
        # ensuring the entire dependency chain is consistent.
        self.task_factory = TaskFactory(
            config_manager=self.config_manager,
            registry_manager=self.registry_manager
        )

    def execute(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None,
                dry_run: bool = False, param_report: bool = False, 
                param_report_format: str = "table") -> Tuple[bool, Optional[str], str]:
        """
        Orchestrate the execution of a task for the specified profile.
        """
        self.logger.info(f"Orchestrating task execution for profile: {profile_name}")
        try:
            # Generate parameter report if requested
            if param_report:
                # Get complete configuration report with tracking
                config_report = self.config_manager.get_complete_config_report(profile_name, cli_overrides)
                
                # Display the report
                display = ParameterReportDisplay()
                display.display_report(config_report, param_report_format, dry_run)
                
                # If dry-run with param-report, exit after showing report
                if dry_run:
                    return True, None, "(param-report-only)"
                
                # For normal execution, continue with the final config
                config = config_report.final_config
            else:
                # Normal execution without parameter tracking
                config = self.config_manager.merge_configs(profile_name, cli_overrides)

            # Create a workspace for the task
            workspace = self.workspace_manager.create_workspace(
                config.get("name", profile_name),
                config.get("task_type")
            )
            
            # Update config with workspace information
            config["workspace"] = {**config.get("workspace", {}), **workspace}

            # Copy profile and template files to workspace inputs directory
            self._populate_workspace_files(profile_name, config, workspace)
            
            # Write workspace metadata for reproducibility
            self._write_workspace_metadata(config, workspace)
            
            # Generate workspace pattern and fingerprint for reproducibility
            self._generate_workspace_reproducibility_data(config, workspace)
            
            # Register task immediately with registry (paradigm shift!)
            task_id = self.registry_manager.register_task_submission(
                task_data=config,
                workspace_dir=workspace["workspace_dir"],
                system_snapshot=self._capture_system_environment()
            )
            
            self.logger.info(f"Task registered with registry: {task_id}")

            # Create the task using the fully merged config
            task = self.task_factory.create_task(config)

            # Generate the script
            template_path = config.get("template")
            if not template_path:
                raise ValueError("No template specified in configuration")

            script_name = f"{config['task_type']}_{config['name']}.sh"
            script_path = os.path.join(workspace["workspace_dir"], script_name)
            script_path = task.generate_script(template_path, script_path)

            # Submit the job if not a dry run
            if not dry_run:
                success, job_id = task.submit_job(script_path)
                
                # Update registry with job ID if job was submitted
                if job_id:
                    self.registry_manager.update_task_job_id(task_id, job_id)
                    
                # Register task-specific completion data if successful
                if success:
                    self._register_task_specific_data(task_id, config, task)
                    
                # Update task completion status in registry
                completion_status = 'COMPLETED' if success else 'FAILED'
                self.registry_manager.update_task_completion(task_id, {
                    'status': completion_status,
                    'completion_time': time.time()
                })
            else:
                success, job_id = True, None
                # For dry runs, mark as completed since script generation succeeded
                self.registry_manager.update_task_completion(task_id, {
                    'status': 'DRY_RUN_COMPLETED',
                    'completion_time': time.time()
                })

            if success:
                self.logger.info(f"Task '{config['name']}' completed. Task ID: {task_id}, Job ID: {job_id}, Script: {script_path}")
            else:
                self.logger.error(f"Task '{config['name']}' failed. Task ID: {task_id}, Script: {script_path}")

            return success, job_id, script_path

        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"Configuration or setup error for profile '{profile_name}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during task orchestration for profile '{profile_name}': {e}")
            raise
    
    def _register_task_specific_data(self, task_id: str, config: Dict[str, Any], task) -> None:
        """
        Register task-specific completion data with the registry.
        
        Args:
            task_id: The task ID in the registry
            config: The task configuration
            task: The task instance
        """
        task_type = config.get('task_type', '').lower()
        
        if task_type == 'application':
            # Register application build completion
            app_name = config.get('name', 'unknown')
            workspace_dir = config.get('workspace', {}).get('workspace_dir', '')
            
            build_data = {
                'binary_path': os.path.join(workspace_dir, app_name),
                'build_artifacts': [app_name],  # Simplified
                'module_file_path': None,  # Could be enhanced
                'build_success': True,
                'build_duration_seconds': 0  # Could be tracked
            }
            
            try:
                self.registry_manager.register_application_build(task_id, build_data)
                self.logger.info(f"Registered application build completion for task {task_id}")
            except Exception as e:
                self.logger.error(f"Failed to register application build: {e}")
                
        elif task_type == 'benchmark':
            # For benchmarks, we'd register results here if available
            # This would typically be done after result extraction
            try:
                # Placeholder for future result registration
                # self.registry_manager.register_benchmark_results(task_id, results_data, figures_of_merit)
                self.logger.debug(f"Benchmark task {task_id} completed - results registration would happen after extraction")
            except Exception as e:
                self.logger.error(f"Failed to register benchmark results: {e}")

    def _populate_workspace_files(self, profile_name: str, config: Dict[str, Any], workspace: Dict[str, str]) -> None:
        """
        Copy profile and template files to workspace inputs directory.
        
        Args:
            profile_name: Name of the profile being executed.
            config: Complete task configuration.
            workspace: Workspace directory structure.
        """
        self.logger.info("Populating workspace with input files")
        
        try:
            # Get the profile file path from metadata if available
            profile_path = None
            if "_metadata" in config and "source_path" in config["_metadata"]:
                profile_path = config["_metadata"]["source_path"]
            else:
                # Fallback: try to find profile file manually
                task_type = config.get("task_type", "benchmark")
                if task_type == "application":
                    profile_dir = self.user_dir_manager.get_path("inputs_application")
                else:
                    profile_dir = self.user_dir_manager.get_path("inputs_benchmark")
                
                potential_path = os.path.join(profile_dir, f"{profile_name}.yaml")
                if os.path.exists(potential_path):
                    profile_path = potential_path
            
            if profile_path and os.path.exists(profile_path):
                copied_profile = self.workspace_manager.copy_profile_file(profile_path, workspace)
                self.logger.info(f"Copied profile file: {copied_profile}")
            else:
                self.logger.warning(f"Profile file not found for {profile_name}")
            
            # Copy template file if specified
            template_name = config.get("template")
            if template_name:
                # Find template file in appropriate directory
                task_type = config.get("task_type", "benchmark")
                if task_type == "application":
                    template_dir = self.user_dir_manager.get_path("inputs_application")
                else:
                    template_dir = self.user_dir_manager.get_path("inputs_benchmark")
                
                template_path = os.path.join(template_dir, template_name)
                
                if os.path.exists(template_path):
                    copied_template = self.workspace_manager.copy_template_file(template_path, workspace)
                    self.logger.info(f"Copied template file: {copied_template}")
                else:
                    self.logger.warning(f"Template file not found: {template_name} in {template_dir}")
            
            # Copy source file if specified in build configuration
            build_config = config.get("build", {})
            source_filename = build_config.get("source")
            if source_filename:
                copied_source = self.workspace_manager.copy_source_file(source_filename, workspace)
                if copied_source:
                    self.logger.info(f"Copied source file: {copied_source}")
                else:
                    self.logger.warning(f"Source file not found: {source_filename}")
            
            # Copy debug log for troubleshooting
            self.workspace_manager.copy_debug_log(workspace)
            
        except Exception as e:
            self.logger.error(f"Error populating workspace files: {e}")
            # Don't fail the entire task for file copying issues
    
    def _write_workspace_metadata(self, config: Dict[str, Any], workspace: Dict[str, str]) -> None:
        """
        Write metadata files to workspace for reproducibility.
        
        Args:
            config: Complete task configuration.
            workspace: Workspace directory structure.
        """
        self.logger.info("Writing workspace metadata for reproducibility")
        
        try:
            # Write task metadata
            task_metadata = {
                "name": config.get("name"),
                "version": config.get("version", "1.0"),
                "task_type": config.get("task_type"),
                "description": config.get("description"),
                "tags": config.get("tags", [])
            }
            self.workspace_manager.write_task_metadata(workspace, task_metadata)
            
            # Write complete config snapshot
            self.workspace_manager.write_config_snapshot(workspace, config)
            
            # Write system environment
            system_env = self._capture_system_environment()
            self.workspace_manager.write_system_environment(workspace, system_env)
            
            # Write dependencies if present (will be populated later for benchmarks)
            dependencies = config.get("requirements", {})
            if dependencies:
                self.workspace_manager.write_dependencies_metadata(workspace, [dependencies])
                
        except Exception as e:
            self.logger.error(f"Error writing workspace metadata: {e}")
            # Don't fail the entire task for metadata writing issues
    
    def _generate_workspace_reproducibility_data(self, config: Dict[str, Any], workspace: Dict[str, str]) -> None:
        """
        Generate workspace pattern and fingerprint for reproducibility.
        
        Args:
            config: Complete task configuration.
            workspace: Workspace directory structure.
        """
        self.logger.info("Generating workspace pattern and fingerprint for reproducibility")
        
        try:
            # Generate workspace pattern
            pattern = self.workspace_manager.generate_workspace_pattern(
                task_name=config.get("name", "unknown"),
                task_type=config.get("task_type", "benchmark"),
                version=config.get("version", "1.0")
            )
            
            # Store pattern in config for registry
            config["workspace_pattern"] = pattern
            
            # Generate and write workspace fingerprint
            fingerprint_path = self.workspace_manager.write_workspace_fingerprint(workspace)
            self.logger.info(f"Generated workspace fingerprint: {fingerprint_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating workspace reproducibility data: {e}")
            # Don't fail the entire task for reproducibility data generation issues
    
    def _capture_system_environment(self) -> Dict[str, Any]:
        """
        Capture current system environment for reproducibility.
        
        Returns:
            Dictionary containing system environment information.
        """
        import platform
        import socket
        from datetime import datetime
        
        try:
            return {
                "hostname": socket.gethostname(),
                "os_info": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                },
                "python_version": platform.python_version(),
                "captured_at": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.warning(f"Error capturing system environment: {e}")
            return {"error": str(e), "captured_at": datetime.now().isoformat()}
