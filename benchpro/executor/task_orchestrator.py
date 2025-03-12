"""
Task Orchestrator for BenchPRO.

This module orchestrates the execution of tasks by integrating configuration, templating, and job submission
using the composition-based task architecture.
"""

import os
from typing import Dict, Any, Optional, Tuple

from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.task_factory import TaskFactory
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import get_user_dir_manager
from benchpro.utils.logger import get_logger


class TaskOrchestrator:
    """
    Orchestrates the execution of tasks using the composition-based architecture.
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
        
        # Get the user directory manager
        self.user_dir_manager = get_user_dir_manager()
        
        self.config_manager = config_manager or ConfigManager(user_dir_manager=self.user_dir_manager)
        self.template_engine = template_engine or TemplateEngine(user_dir_manager=self.user_dir_manager)
        self.workspace_manager = workspace_manager or WorkspaceManager(user_dir_manager=self.user_dir_manager)
        self.registry_manager = registry_manager or RegistryManager(user_dir_manager=self.user_dir_manager)
        
        self.logger.debug("TaskOrchestrator initialized with components:")
        self.logger.debug(f"  - ConfigManager: {self.config_manager.__class__.__name__}")
        self.logger.debug(f"  - TemplateEngine: {self.template_engine.__class__.__name__}")
        self.logger.debug(f"  - WorkspaceManager: {self.workspace_manager.__class__.__name__}")
        self.logger.debug(f"  - RegistryManager: {self.registry_manager.__class__.__name__}")
        
        # Create the task factory
        self.task_factory = TaskFactory()
        
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
            
            # Create a workspace for the task using the WorkspaceManager
            self.logger.info(f"Creating workspace for task: {profile_name} of type: {task_type}")
            workspace = self.workspace_manager.create_workspace(profile_name, task_type)
            self.logger.debug(f"Workspace created: {workspace['workspace_dir']}")
            
            # If the profile is a file, copy it to the workspace
            if os.path.isfile(profile_name):
                profile_path = self.workspace_manager.copy_profile_file(profile_name, workspace)
                self.logger.debug(f"Profile copied to workspace: {profile_path}")
            
            # For application tasks, copy source files to the workspace
            if task_type == "application":
                # Get the source file(s) from the profile configuration
                source_files = []
                if "build" in profile_config and "source" in profile_config["build"]:
                    source_files.append(profile_config["build"]["source"])
                
                # Get the source directory from the user directory manager
                source_dir = self.user_dir_manager.get_source_directory()
                self.logger.info(f"Copying source files from {source_dir} to workspace root")
                
                # Copy the source files to the workspace
                copied_files = self.workspace_manager.copy_input_files(source_dir, workspace, source_files)
                
                if copied_files:
                    self.logger.info(f"Copied {len(copied_files)} source files to workspace root: {', '.join(os.path.basename(f) for f in copied_files)}")
                else:
                    self.logger.warning(f"No source files copied. Build will likely fail! Expected source file: {source_files}")
                    self.logger.warning(f"Check that files exist in source directory: {source_dir}")
            
            # Get execution type from CLI overrides or from profile config
            execution_type = None
            if cli_overrides and "execution" in cli_overrides:
                execution_type = cli_overrides["execution"].get("type")
                
            if not execution_type and "execution" in profile_config:
                execution_type = profile_config["execution"].get("type")
            
            # Map legacy executor names to new execution types
            if execution_type == "scheduler":
                execution_type = "slurm"
            
            self.logger.info(f"Execution type determined: {execution_type or 'default'}")
            
            # Update the configuration with workspace paths
            if "workspace" not in profile_config:
                profile_config["workspace"] = {}
                
            profile_config["workspace"].update({
                "workspace_dir": workspace["workspace_dir"],
                "source_dir": workspace["source_dir"],
                "build_dir": workspace["build_dir"],
                "logs_dir": workspace["logs_dir"],
                "results_dir": workspace["results_dir"],
                "task_id": workspace["task_id"]
            })
            
            self.logger.debug(f"Updated configuration with workspace paths")
            
            # Merge with CLI overrides if present
            merged_config = profile_config
            if cli_overrides:
                self.logger.debug("Merging workspace config with CLI overrides")
                merged_config = self.config_manager.merge_configs(profile_config, cli_overrides)
            
            # Create appropriate task instance using the composition-based factory
            self.logger.debug(f"Creating task of type: {task_type} with execution type: {execution_type or 'default'}")
            task = self.task_factory.create_task(task_type, execution_type, merged_config)
            self.logger.debug(f"Task created: {task.__class__.__name__}")
            
            # Prepare the task with the profile and CLI overrides
            self.logger.debug("Preparing task")
            config = task.prepare(profile_name, cli_overrides)
            
            # Generate the script
            self.logger.debug("Generating script")
            template_path = config.get("template")
            if not template_path:
                raise ValueError("No template specified in configuration")
                
            # Use workspace root directory for script output instead of logs directory
            workspace_dir = workspace["workspace_dir"]
            script_name = f"{task_type}_{profile_name}.sh"
            script_path = os.path.join(workspace_dir, script_name)
            self.logger.debug(f"Script will be generated at: {script_path}")
            
            # Generate the script
            script_path = task.generate_script(template_path, script_path)
            
            # Submit the job if not a dry run
            if not dry_run:
                self.logger.debug("Submitting job")
                success, job_id = task.submit_job(script_path)
            else:
                success = True
                job_id = None
                
            if success:
                if job_id:
                    self.logger.info(f"Task execution started. Job ID: {job_id}, Script: {script_path}")
                    
                    # For application tasks, provide registration information
                    if task_type == "application":
                        # Get application name from config
                        app_config = task.config_component.get_config()
                        app_name = app_config.get("name", profile_name)
                        binary_path = os.path.join(workspace["build_dir"], app_name)
                        
                        self.logger.info("Application build job submitted")
                        
                        # Registration instructions - currently manual
                        self.logger.info("NOTE: Applications must be registered manually after successful build:")
                        self.logger.info(f"  To register: bp apps register {app_name} {binary_path}")
                        self.logger.info("  Registration is required for applications to be available to benchmarks")
                        
                    # Only show the capture results message for benchmark tasks
                    if task_type == "benchmark":
                        self.logger.info("To capture results after completion, use 'bp capture --job-id %s'", job_id)
                else:
                    self.logger.info(f"Task script generated: {script_path}")
                    
                    # For application tasks in dry run mode, provide registration info
                    if task_type == "application" and dry_run:
                        # Get application name from config
                        app_config = task.config_component.get_config()
                        app_name = app_config.get("name", profile_name)
                        binary_path = os.path.join(workspace["build_dir"], app_name)
                        
                        self.logger.info("NOTE: After successful build, applications must be registered:")
                        self.logger.info(f"  bp apps register {app_name} {binary_path}")
            else:
                self.logger.error(f"Task execution failed. Script: {script_path}")
                
            return success, job_id, script_path
            
        except FileNotFoundError as e:
            self.logger.error(f"Profile not found: {str(e)}")
            raise
        except ValueError as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error during execution: {str(e)}")
            raise 