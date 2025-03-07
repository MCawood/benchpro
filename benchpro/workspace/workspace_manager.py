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
        
        # Create subdirectories
        source_dir = os.path.join(workspace_dir, "source")
        build_dir = os.path.join(workspace_dir, "build")
        logs_dir = os.path.join(workspace_dir, "logs")
        results_dir = os.path.join(workspace_dir, "results")
        inputs_dir = os.path.join(workspace_dir, "inputs")
        
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(inputs_dir, exist_ok=True)
        
        self.logger.info(f"Created workspace directory: {workspace_dir}")
        
        # Return the workspace structure
        return {
            "workspace_dir": workspace_dir,
            "source_dir": source_dir,
            "build_dir": build_dir,
            "logs_dir": logs_dir,
            "results_dir": results_dir,
            "inputs_dir": inputs_dir,
            "task_id": task_id
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
        source_dir = workspace["source_dir"]
        copied_files = []
        
        # If no patterns specified, copy all files
        if not file_patterns:
            file_patterns = ["*"]
            
        # Copy files matching patterns
        for pattern in file_patterns:
            for file_path in glob.glob(os.path.join(input_dir, pattern)):
                if os.path.isfile(file_path):
                    dest_path = os.path.join(source_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    copied_files.append(dest_path)
                    self.logger.info(f"Copied {file_path} to {dest_path}")
                    
        return copied_files

    def copy_profile_file(self, profile_path: str, workspace: Dict[str, str]) -> str:
        """
        Copy a profile file to the inputs directory in the workspace.
        
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
            
        return os.path.join(workspace["inputs_dir"], profile_name)
        
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