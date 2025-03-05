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

from benchpro.utils.user_dir import user_dir_manager


class WorkspaceManager:
    """
    Manages workspace directories and file operations for BenchPRO tasks.
    
    Responsibilities:
    - Create unique workspace directories for each task run
    - Copy input files to the workspace
    - Manage output file locations
    - Clean up temporary files when needed
    """
    
    def __init__(self):
        """
        Initialize the WorkspaceManager.
        """
        self.logger = logging.getLogger(__name__)
        
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
            base_output_dir = user_dir_manager.get_application_directory()
        else:  # Default to benchmark
            base_output_dir = user_dir_manager.get_benchmark_directory()
        
        # Create the main workspace directory
        workspace_dir = os.path.join(base_output_dir, task_id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Create subdirectories
        source_dir = os.path.join(workspace_dir, "source")
        build_dir = os.path.join(workspace_dir, "build")
        logs_dir = os.path.join(workspace_dir, "logs")
        results_dir = os.path.join(workspace_dir, "results")
        
        os.makedirs(source_dir, exist_ok=True)
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        
        self.logger.info(f"Created workspace directory: {workspace_dir}")
        
        # Return the workspace structure
        return {
            "workspace_dir": workspace_dir,
            "source_dir": source_dir,
            "build_dir": build_dir,
            "logs_dir": logs_dir,
            "results_dir": results_dir,
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
        
    def clean_workspace(self, workspace: Dict[str, str], keep_logs: bool = True) -> None:
        """
        Clean up temporary files in the workspace.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            keep_logs: If True, keep log files.
        """
        # Clean up source files
        for file_path in glob.glob(os.path.join(workspace["source_dir"], "*")):
            if os.path.isfile(file_path):
                os.remove(file_path)
                self.logger.info(f"Removed temporary file: {file_path}")
                
        # Clean up build files if needed
        # (This could be conditional based on configuration)
        
        # Keep logs if requested
        if not keep_logs:
            for file_path in glob.glob(os.path.join(workspace["logs_dir"], "*")):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    self.logger.info(f"Removed log file: {file_path}")
                    
    def _generate_random_string(self, length: int = 6) -> str:
        """
        Generate a random string of specified length.
        
        Args:
            length: Length of the random string.
            
        Returns:
            Random string.
        """
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) 