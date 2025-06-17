"""
Workspace Manager for BenchPRO.

This module provides functionality for managing workspaces for BenchPRO tasks.
"""

import os
import time
import glob
import shutil
import logging
import random
import string
from typing import Dict, List, Optional

from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager


class WorkspaceManager:
    """
    Manages workspace directories and file operations for BenchPRO tasks.
    
    Responsibilities:
    - Create unique workspace directories for each task run
    - Copy input files to the workspace
    - Manage output file locations
    - Clean up temporary files when needed
    """
    
    def __init__(self, user_dir_manager: Optional[UserDirectoryManagerInterface] = None):
        """
        Initialize the WorkspaceManager.
        
        Args:
            user_dir_manager: UserDirectoryManager instance. If None, uses the default instance.
        """
        self.logger = logging.getLogger(__name__)
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
    def create_workspace(self, task_name: str, task_type: str = "benchmark") -> Dict[str, str]:
        """
        Create a unique workspace directory for a task.
        
        Args:
            task_name: Name of the task.
            task_type: Type of task ("application" or "benchmark").
            
        Returns:
            Dictionary containing paths to different workspace directories.
        """
        # Generate a unique task ID (timestamp + random string)
        task_id = f"{task_name}_{int(time.time())}_{self._generate_random_string(6)}"
        
        # Get the appropriate base directory based on task type
        if task_type.lower() == "application":
            base_output_dir = self.user_dir_manager.get_application_directory()
        else:  # Default to benchmark
            base_output_dir = self.user_dir_manager.get_benchmark_directory()
        
        # Create the main workspace directory
        workspace_dir = os.path.join(base_output_dir, task_id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Create only the necessary subdirectories
        logs_dir = os.path.join(workspace_dir, "logs")
        inputs_dir = os.path.join(workspace_dir, "inputs")
        
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(inputs_dir, exist_ok=True)
        
        self.logger.info(f"Created workspace directory: {workspace_dir}")
        
        # Return the workspace structure (maintaining the keys for compatibility)
        return {
            "workspace_dir": workspace_dir,
            "logs_dir": logs_dir,
            "inputs_dir": inputs_dir,
            "task_id": task_id,
            # Keep these keys for compatibility, but point to workspace_dir
            "source_dir": workspace_dir,
            "build_dir": workspace_dir,
            "results_dir": workspace_dir
        }
        
    def copy_input_files(self, input_dir: str, workspace: Dict[str, str], 
                         file_patterns: Optional[List[str]] = None) -> List[str]:
        """
        Copy input files to the workspace.
        
        Args:
            input_dir: Directory containing input files.
            workspace: Workspace dictionary from create_workspace().
            file_patterns: Optional list of file patterns to copy (e.g., ["*.c", "*.h"]).
                          If None, copy all files.
                          
        Returns:
            List of copied file paths.
        """
        # Use the workspace root directory instead of source directory
        workspace_dir = workspace["workspace_dir"]
        copied_files = []
        
        # If no patterns specified, copy all files
        if not file_patterns:
            file_patterns = ["*"]
            
        # Copy files matching patterns
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(input_dir, pattern)):
                if os.path.isfile(file_path):
                    dest_path = os.path.join(workspace_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    copied_files.append(dest_path)
                    self.logger.info(f"Copied {file_path} to {dest_path}")
                    
        return copied_files

    def copy_profile_file(self, profile_path: str, workspace: Dict[str, str]) -> str:
        """
        Copy a profile file to the workspace inputs directory.
        
        Args:
            profile_path: Path to the profile file.
            workspace: Workspace dictionary from create_workspace().
            
        Returns:
            Path to the copied profile file.
        """
        if not os.path.exists(profile_path):
            self.logger.error(f"Profile file not found: {profile_path}")
            return ""
            
        # Get the destination path in the inputs directory
        inputs_dir = workspace["inputs_dir"]
        dest_path = os.path.join(inputs_dir, os.path.basename(profile_path))
        
        # Copy the file
        shutil.copy2(profile_path, dest_path)
        self.logger.info(f"Copied profile file {profile_path} to {dest_path}")
        
        return dest_path
        
    def get_log_file_path(self, workspace: Dict[str, str], log_name: str) -> str:
        """
        Get the path to a log file in the workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            log_name: Name of the log file.
            
        Returns:
            Path to the log file.
        """
        return os.path.join(workspace["logs_dir"], f"{log_name}.log")
        
    def get_build_output_path(self, workspace: Dict[str, str], binary_name: str) -> str:
        """
        Get the path to a build output file in the workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            binary_name: Name of the binary file.
            
        Returns:
            Path to the build output file.
        """
        return os.path.join(workspace["build_dir"], binary_name)
        
    def get_result_file_path(self, workspace: Dict[str, str], result_name: str) -> str:
        """
        Get the path to a result file in the workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            result_name: Name of the result file.
            
        Returns:
            Path to the result file.
        """
        return os.path.join(workspace["results_dir"], result_name)
    
    def get_profile_file_path(self, workspace: Dict[str, str], profile_name: str) -> str:
        """
        Get the path to a profile file in the workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            profile_name: Name of the profile file.
            
        Returns:
            Path to the profile file.
        """
        # If profile_name doesn't end with .yaml, add it
        if not profile_name.endswith('.yaml'):
            profile_name += '.yaml'
            
        return os.path.join(workspace["workspace_dir"], profile_name)
        
    def clean_workspace(self, workspace: Dict[str, str], keep_logs: bool = True) -> None:
        """
        Clean up a workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            keep_logs: If True, don't delete log files.
        """
        # Check if workspace directory exists
        if not os.path.exists(workspace["workspace_dir"]):
            self.logger.warning(f"Workspace directory doesn't exist: {workspace['workspace_dir']}")
            return
            
        # Delete source directory
        if os.path.exists(workspace["source_dir"]):
            shutil.rmtree(workspace["source_dir"])
            self.logger.info(f"Deleted source directory: {workspace['source_dir']}")
            
        # Delete build directory
        if os.path.exists(workspace["build_dir"]):
            shutil.rmtree(workspace["build_dir"])
            self.logger.info(f"Deleted build directory: {workspace['build_dir']}")
            
        # Delete logs directory if keep_logs is False
        if not keep_logs and os.path.exists(workspace["logs_dir"]):
            shutil.rmtree(workspace["logs_dir"])
            self.logger.info(f"Deleted logs directory: {workspace['logs_dir']}")
            
    def _generate_random_string(self, length: int = 6) -> str:
        """
        Generate a random string.
        
        Args:
            length: Length of the string.
            
        Returns:
            Random string.
        """
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def copy_template_file(self, template_path: str, workspace: Dict[str, str]) -> str:
        """
        Copy a template file to the workspace inputs directory.
        
        Args:
            template_path: Path to the template file.
            workspace: Workspace dictionary from create_workspace().
            
        Returns:
            Path to the copied template file.
        """
        if not os.path.exists(template_path):
            self.logger.error(f"Template file not found: {template_path}")
            return ""
            
        # Get the destination path in the inputs directory
        inputs_dir = workspace["inputs_dir"]
        dest_path = os.path.join(inputs_dir, os.path.basename(template_path))
        
        # Copy the file
        shutil.copy2(template_path, dest_path)
        self.logger.info(f"Copied template file {template_path} to {dest_path}")
        
        return dest_path

    def copy_debug_log(self, workspace: Dict[str, str]) -> str:
        """
        Copy the benchpro debug log to the workspace logs directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            
        Returns:
            Path to the copied log file.
        """
        # Get the benchpro logs directory
        benchpro_logs_dir = self.user_dir_manager.get_logs_directory()
        
        if not os.path.exists(benchpro_logs_dir):
            self.logger.warning(f"Benchpro logs directory not found: {benchpro_logs_dir}")
            return ""
            
        # Find the most recent log file
        log_files = glob.glob(os.path.join(benchpro_logs_dir, "benchpro_*.log"))
        if not log_files:
            self.logger.warning(f"No benchpro log files found in: {benchpro_logs_dir}")
            return ""
            
        # Sort by modification time (most recent first)
        most_recent_log = max(log_files, key=os.path.getmtime)
        
        # Get the destination path in the logs directory
        logs_dir = workspace["logs_dir"]
        dest_path = os.path.join(logs_dir, "benchpro_debug.log")
        
        # Copy the file
        shutil.copy2(most_recent_log, dest_path)
        self.logger.info(f"Copied benchpro log file {most_recent_log} to {dest_path}")
        
        return dest_path

    def get_module_file_path(self, workspace_dir: str, app_name: str, app_version: str) -> str:
        """
        Get the path to a module file in the workspace.
        
        Args:
            workspace_dir: Path to the workspace directory
            app_name: Application name
            app_version: Application version
            
        Returns:
            Path to the module file
        """
        # Ensure the workspace_dir is an absolute path
        workspace_dir = os.path.abspath(workspace_dir)
        
        # Create the path as [workspace_dir]/modulefiles/[app_name]/[app_version].lua
        module_file_path = os.path.join(
            workspace_dir, 
            "modulefiles", 
            app_name, 
            f"{app_version}.lua"
        )
        
        # Create the modulefiles directory
        modulefiles_dir = os.path.dirname(module_file_path)
        os.makedirs(modulefiles_dir, exist_ok=True)
        self.logger.info(f"Created modulefiles directory: {modulefiles_dir}")
        
        self.logger.debug(f"Module file path: {module_file_path}")
        return module_file_path 