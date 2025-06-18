
import os
import sys
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
        self.registry_manager = registry_manager or RegistryManager(user_dir_manager=self.user_dir_manager)

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
            config["workspace"] = {**config.get("workspace", {}), **workspace}

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
            else:
                success, job_id = True, None

            if success:
                self.logger.info(f"Task '{config['name']}' completed. Job ID: {job_id}, Script: {script_path}")
            else:
                self.logger.error(f"Task '{config['name']}' failed. Script: {script_path}")

            return success, job_id, script_path

        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"Configuration or setup error for profile '{profile_name}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during task orchestration for profile '{profile_name}': {e}")
            raise
