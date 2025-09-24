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
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager


class WorkspaceManager:
    """
    Manages workspace directories and file operations for BenchPRO tasks.
    
    Responsibilities:
    - Create unique workspace directories for each task run
    - Copy input files to the workspace
    - Manage output file locations
    - Create and manage metadata directories for reproducibility
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
        
        # Create the necessary subdirectories
        logs_dir = os.path.join(workspace_dir, "logs")
        inputs_dir = os.path.join(workspace_dir, "inputs")
        metadata_dir = os.path.join(workspace_dir, ".benchpro")
        scripts_dir = os.path.join(workspace_dir, "scripts")
        results_dir = os.path.join(workspace_dir, "results")
        build_dir = os.path.join(workspace_dir, "build")
        
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(inputs_dir, exist_ok=True)
        os.makedirs(metadata_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(build_dir, exist_ok=True)
        
        self.logger.info(f"Created workspace directory: {workspace_dir}")
        self.logger.debug(f"Created metadata directory: {metadata_dir}")
        
        # Return the workspace structure
        return {
            "workspace_dir": workspace_dir,
            "logs_dir": logs_dir,
            "inputs_dir": inputs_dir,
            "metadata_dir": metadata_dir,
            "scripts_dir": scripts_dir,
            "results_dir": results_dir,
            "build_dir": build_dir,
            "task_id": task_id,
            # Keep these keys for compatibility, but point to appropriate directories
            "source_dir": workspace_dir,  # For backwards compatibility
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

    def copy_source_file(self, source_filename: str, workspace: Dict[str, str]) -> str:
        """
        Copy a source file to the workspace root directory.
        
        Args:
            source_filename: Name of the source file to copy.
            workspace: Workspace dictionary from create_workspace().
            
        Returns:
            Path to the copied source file, or empty string if not found.
        """
        # Get the source directory from user_dir_manager
        source_dir = self.user_dir_manager.get_path("inputs_source")
        source_path = os.path.join(source_dir, source_filename)
        
        if not os.path.exists(source_path):
            self.logger.warning(f"Source file not found: {source_filename} in {source_dir}")
            return ""
            
        # Copy to workspace root directory instead of inputs subdirectory
        workspace_dir = workspace["workspace_dir"]
        dest_path = os.path.join(workspace_dir, source_filename)
        
        # Copy the file
        shutil.copy2(source_path, dest_path)
        self.logger.info(f"Copied source file {source_path} to {dest_path}")
        
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

    # ========================================================================
    # Metadata File Management for Registry Integration
    # ========================================================================

    def write_task_metadata(self, workspace: Dict[str, str], metadata: Dict[str, Any]) -> str:
        """
        Write task metadata to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            metadata: Task metadata dictionary.
            
        Returns:
            Path to the written metadata file.
        """
        metadata_dir = workspace["metadata_dir"]
        metadata_path = os.path.join(metadata_dir, "task_metadata.json")
        
        # Add timestamp to metadata
        metadata_with_timestamp = {
            **metadata,
            "created_at": datetime.now().isoformat(),
            "workspace_dir": workspace["workspace_dir"]
        }
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata_with_timestamp, f, indent=2, default=str)
            self.logger.info(f"Wrote task metadata to {metadata_path}")
            return metadata_path
        except Exception as e:
            self.logger.error(f"Failed to write task metadata: {e}")
            raise

    def write_config_snapshot(self, workspace: Dict[str, str], config: Dict[str, Any]) -> str:
        """
        Write configuration snapshot to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            config: Complete configuration dictionary.
            
        Returns:
            Path to the written config snapshot file.
        """
        metadata_dir = workspace["metadata_dir"]
        config_path = os.path.join(metadata_dir, "config_snapshot.json")
        
        # Add snapshot metadata
        config_snapshot = {
            "snapshot_time": datetime.now().isoformat(),
            "config": config
        }
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config_snapshot, f, indent=2, default=str)
            self.logger.info(f"Wrote config snapshot to {config_path}")
            return config_path
        except Exception as e:
            self.logger.error(f"Failed to write config snapshot: {e}")
            raise

    def write_dependencies_metadata(self, workspace: Dict[str, str], dependencies: List[Dict[str, Any]]) -> str:
        """
        Write dependency information to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            dependencies: List of dependency dictionaries.
            
        Returns:
            Path to the written dependencies file.
        """
        metadata_dir = workspace["metadata_dir"]
        deps_path = os.path.join(metadata_dir, "dependencies.json")
        
        dependencies_metadata = {
            "created_at": datetime.now().isoformat(),
            "dependencies": dependencies
        }
        
        try:
            with open(deps_path, 'w') as f:
                json.dump(dependencies_metadata, f, indent=2, default=str)
            self.logger.info(f"Wrote dependencies metadata to {deps_path}")
            return deps_path
        except Exception as e:
            self.logger.error(f"Failed to write dependencies metadata: {e}")
            raise

    def write_system_environment(self, workspace: Dict[str, str], system_env: Dict[str, Any]) -> str:
        """
        Write system environment information to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            system_env: System environment dictionary.
            
        Returns:
            Path to the written system environment file.
        """
        metadata_dir = workspace["metadata_dir"]
        env_path = os.path.join(metadata_dir, "system_environment.json")
        
        try:
            with open(env_path, 'w') as f:
                json.dump(system_env, f, indent=2, default=str)
            self.logger.info(f"Wrote system environment to {env_path}")
            return env_path
        except Exception as e:
            self.logger.error(f"Failed to write system environment: {e}")
            raise

    def write_execution_log(self, workspace: Dict[str, str], execution_data: Dict[str, Any]) -> str:
        """
        Write structured execution log to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            execution_data: Execution data and log information.
            
        Returns:
            Path to the written execution log file.
        """
        metadata_dir = workspace["metadata_dir"]
        log_path = os.path.join(metadata_dir, "execution_log.json")
        
        # Add timestamp if not present
        if "timestamp" not in execution_data:
            execution_data["timestamp"] = datetime.now().isoformat()
        
        try:
            with open(log_path, 'w') as f:
                json.dump(execution_data, f, indent=2, default=str)
            self.logger.info(f"Wrote execution log to {log_path}")
            return log_path
        except Exception as e:
            self.logger.error(f"Failed to write execution log: {e}")
            raise

    def write_results_manifest(self, workspace: Dict[str, str], results_info: Dict[str, Any]) -> str:
        """
        Write results manifest to the workspace metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            results_info: Results information and file locations.
            
        Returns:
            Path to the written results manifest file.
        """
        metadata_dir = workspace["metadata_dir"]
        manifest_path = os.path.join(metadata_dir, "results_manifest.json")
        
        results_manifest = {
            "created_at": datetime.now().isoformat(),
            "results": results_info
        }
        
        try:
            with open(manifest_path, 'w') as f:
                json.dump(results_manifest, f, indent=2, default=str)
            self.logger.info(f"Wrote results manifest to {manifest_path}")
            return manifest_path
        except Exception as e:
            self.logger.error(f"Failed to write results manifest: {e}")
            raise

    def read_workspace_metadata(self, workspace_dir: str) -> Dict[str, Any]:
        """
        Read all metadata files from a workspace for future ingest capability.
        
        Args:
            workspace_dir: Path to the workspace directory.
            
        Returns:
            Dictionary containing all workspace metadata.
        """
        metadata_dir = os.path.join(workspace_dir, ".benchpro")
        
        if not os.path.exists(metadata_dir):
            self.logger.warning(f"No metadata directory found in {workspace_dir}")
            return {}
        
        metadata = {}
        metadata_files = [
            "task_metadata.json",
            "config_snapshot.json", 
            "dependencies.json",
            "system_environment.json",
            "execution_log.json",
            "results_manifest.json"
        ]
        
        for filename in metadata_files:
            file_path = os.path.join(metadata_dir, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        key = filename.replace('.json', '')
                        metadata[key] = json.load(f)
                        self.logger.debug(f"Read metadata from {filename}")
                except Exception as e:
                    self.logger.warning(f"Failed to read {filename}: {e}")
            else:
                self.logger.debug(f"Metadata file not found: {filename}")
        
        return metadata

    # ========================================================================
    # Workspace Pattern Generation and Fingerprinting
    # ========================================================================

    def generate_workspace_pattern(self, task_name: str, task_type: str, version: str = "1.0") -> str:
        """
        Generate a reproducible workspace pattern for task recreation.
        
        This pattern can be used to recreate identical workspace structures
        for reproducibility purposes.
        
        Args:
            task_name: Name of the task.
            task_type: Type of task (application or benchmark).
            version: Task version.
            
        Returns:
            Workspace pattern string for reproducibility.
        """
        # Create a deterministic pattern based on task metadata
        pattern_components = [
            f"task_type={task_type}",
            f"name={task_name}",
            f"version={version}",
            "workspace_structure=standard_v1.0"
        ]
        
        # Generate pattern
        pattern = f"benchpro://{'/'.join(pattern_components)}"
        
        self.logger.debug(f"Generated workspace pattern: {pattern}")
        return pattern

    def create_workspace_fingerprint(self, workspace_dir: str) -> Dict[str, Any]:
        """
        Create a comprehensive fingerprint of the workspace for validation.
        
        Args:
            workspace_dir: Path to the workspace directory.
            
        Returns:
            Dictionary containing workspace fingerprint data.
        """
        self.logger.info(f"Creating workspace fingerprint for: {workspace_dir}")
        
        fingerprint = {
            "workspace_dir": workspace_dir,
            "created_at": datetime.now().isoformat(),
            "directory_structure": self._capture_directory_structure(workspace_dir),
            "file_hashes": self._calculate_file_hashes(workspace_dir),
            "metadata_files": self._capture_metadata_files(workspace_dir),
            "workspace_size": self._calculate_workspace_size(workspace_dir)
        }
        
        return fingerprint

    def write_workspace_fingerprint(self, workspace: Dict[str, str]) -> str:
        """
        Create and write workspace fingerprint to the metadata directory.
        
        Args:
            workspace: Workspace dictionary from create_workspace().
            
        Returns:
            Path to the written fingerprint file.
        """
        fingerprint = self.create_workspace_fingerprint(workspace["workspace_dir"])
        
        metadata_dir = workspace["metadata_dir"]
        fingerprint_path = os.path.join(metadata_dir, "workspace_fingerprint.json")
        
        try:
            with open(fingerprint_path, 'w') as f:
                json.dump(fingerprint, f, indent=2, default=str)
            self.logger.info(f"Wrote workspace fingerprint to {fingerprint_path}")
            return fingerprint_path
        except Exception as e:
            self.logger.error(f"Failed to write workspace fingerprint: {e}")
            raise

    def validate_workspace_integrity(self, workspace_dir: str, 
                                   expected_fingerprint: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """
        Validate workspace integrity against expected structure and files.
        
        Args:
            workspace_dir: Path to the workspace directory.
            expected_fingerprint: Expected fingerprint to validate against.
                                 If None, loads from workspace metadata.
            
        Returns:
            Tuple of (is_valid, list_of_issues).
        """
        self.logger.info(f"Validating workspace integrity: {workspace_dir}")
        issues = []
        
        try:
            # Load expected fingerprint if not provided
            if expected_fingerprint is None:
                fingerprint_path = os.path.join(workspace_dir, ".benchpro", "workspace_fingerprint.json")
                if os.path.exists(fingerprint_path):
                    with open(fingerprint_path, 'r') as f:
                        expected_fingerprint = json.load(f)
                else:
                    issues.append("No workspace fingerprint found for validation")
                    return False, issues
            
            # Check basic workspace structure
            if not os.path.exists(workspace_dir):
                issues.append(f"Workspace directory does not exist: {workspace_dir}")
                return False, issues
            
            # Validate directory structure
            expected_dirs = expected_fingerprint.get("directory_structure", {}).get("directories", [])
            for expected_dir in expected_dirs:
                full_path = os.path.join(workspace_dir, expected_dir)
                if not os.path.exists(full_path):
                    issues.append(f"Missing expected directory: {expected_dir}")
            
            # Validate critical files
            expected_hashes = expected_fingerprint.get("file_hashes", {})
            current_hashes = self._calculate_file_hashes(workspace_dir, critical_only=True)
            
            for file_path, expected_hash in expected_hashes.items():
                if file_path in current_hashes:
                    if current_hashes[file_path] != expected_hash:
                        issues.append(f"File hash mismatch: {file_path}")
                else:
                    # Only flag as issue if it's a critical file
                    if self._is_critical_file(file_path):
                        issues.append(f"Missing critical file: {file_path}")
            
            # Validate metadata files
            metadata_dir = os.path.join(workspace_dir, ".benchpro")
            if not os.path.exists(metadata_dir):
                issues.append("Missing .benchpro metadata directory")
            else:
                metadata_files = ["task_metadata.json", "config_snapshot.json"]
                for metadata_file in metadata_files:
                    metadata_path = os.path.join(metadata_dir, metadata_file)
                    if not os.path.exists(metadata_path):
                        issues.append(f"Missing metadata file: {metadata_file}")
            
        except Exception as e:
            issues.append(f"Workspace validation failed: {e}")
        
        is_valid = len(issues) == 0
        self.logger.info(f"Workspace validation result: {'VALID' if is_valid else 'INVALID'} ({len(issues)} issues)")
        
        return is_valid, issues

    def mark_workspace_cleaned(self, workspace_dir: str, cleanup_reason: str = None) -> str:
        """
        Mark workspace as cleaned and create cleanup record.
        
        Args:
            workspace_dir: Path to the workspace directory.
            cleanup_reason: Optional reason for cleanup.
            
        Returns:
            Path to the cleanup record file.
        """
        cleanup_record = {
            "workspace_dir": workspace_dir,
            "cleaned_at": datetime.now().isoformat(),
            "cleanup_reason": cleanup_reason or "Manual cleanup",
            "cleaned_by": "workspace_manager"
        }
        
        # Try to write cleanup record to metadata directory if it exists
        metadata_dir = os.path.join(workspace_dir, ".benchpro")
        if os.path.exists(metadata_dir):
            cleanup_path = os.path.join(metadata_dir, "cleanup_record.json")
            try:
                with open(cleanup_path, 'w') as f:
                    json.dump(cleanup_record, f, indent=2, default=str)
                self.logger.info(f"Marked workspace as cleaned: {workspace_dir}")
                return cleanup_path
            except Exception as e:
                self.logger.warning(f"Could not write cleanup record: {e}")
        
        # Fallback: write to user directory
        try:
            cleanup_dir = self.user_dir_manager.get_path("logs")
            cleanup_filename = f"workspace_cleanup_{int(time.time())}.json"
            cleanup_path = os.path.join(cleanup_dir, cleanup_filename)
            
            with open(cleanup_path, 'w') as f:
                json.dump(cleanup_record, f, indent=2, default=str)
            self.logger.info(f"Wrote cleanup record to: {cleanup_path}")
            return cleanup_path
        except Exception as e:
            self.logger.error(f"Failed to write cleanup record: {e}")
            raise

    def get_workspace_info(self, workspace_dir: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a workspace.
        
        Args:
            workspace_dir: Path to the workspace directory.
            
        Returns:
            Dictionary containing workspace information.
        """
        info = {
            "workspace_dir": workspace_dir,
            "exists": os.path.exists(workspace_dir),
            "created_at": None,
            "size_bytes": 0,
            "file_count": 0,
            "has_metadata": False,
            "has_fingerprint": False,
            "is_cleaned": False
        }
        
        if not info["exists"]:
            return info
        
        try:
            # Get basic filesystem info
            info["size_bytes"] = self._calculate_workspace_size(workspace_dir)
            info["file_count"] = self._count_files(workspace_dir)
            
            # Check for metadata directory
            metadata_dir = os.path.join(workspace_dir, ".benchpro")
            info["has_metadata"] = os.path.exists(metadata_dir)
            
            if info["has_metadata"]:
                # Check for specific metadata files
                fingerprint_path = os.path.join(metadata_dir, "workspace_fingerprint.json")
                info["has_fingerprint"] = os.path.exists(fingerprint_path)
                
                cleanup_path = os.path.join(metadata_dir, "cleanup_record.json")
                info["is_cleaned"] = os.path.exists(cleanup_path)
                
                # Get creation time from task metadata
                task_metadata_path = os.path.join(metadata_dir, "task_metadata.json")
                if os.path.exists(task_metadata_path):
                    try:
                        with open(task_metadata_path, 'r') as f:
                            task_metadata = json.load(f)
                            info["created_at"] = task_metadata.get("created_at")
                    except Exception:
                        pass
        
        except Exception as e:
            self.logger.warning(f"Error getting workspace info: {e}")
        
        return info

    # ========================================================================
    # Private Helper Methods for Fingerprinting
    # ========================================================================

    def _capture_directory_structure(self, workspace_dir: str) -> Dict[str, Any]:
        """Capture the directory structure of the workspace."""
        structure = {
            "directories": [],
            "files": [],
            "total_directories": 0,
            "total_files": 0
        }
        
        try:
            workspace_path = Path(workspace_dir)
            for item in workspace_path.rglob("*"):
                relative_path = str(item.relative_to(workspace_path))
                
                if item.is_dir():
                    structure["directories"].append(relative_path)
                    structure["total_directories"] += 1
                elif item.is_file():
                    structure["files"].append(relative_path)
                    structure["total_files"] += 1
        
        except Exception as e:
            self.logger.warning(f"Error capturing directory structure: {e}")
        
        return structure

    def _calculate_file_hashes(self, workspace_dir: str, critical_only: bool = False) -> Dict[str, str]:
        """Calculate SHA256 hashes for files in the workspace."""
        file_hashes = {}
        
        try:
            workspace_path = Path(workspace_dir)
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(workspace_path))
                    
                    # Skip non-critical files if critical_only is True
                    if critical_only and not self._is_critical_file(relative_path):
                        continue
                    
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                            file_hashes[relative_path] = file_hash
                    except Exception as e:
                        self.logger.debug(f"Could not hash file {relative_path}: {e}")
        
        except Exception as e:
            self.logger.warning(f"Error calculating file hashes: {e}")
        
        return file_hashes

    def _capture_metadata_files(self, workspace_dir: str) -> Dict[str, Any]:
        """Capture content of metadata files for fingerprinting."""
        metadata_content = {}
        metadata_dir = os.path.join(workspace_dir, ".benchpro")
        
        if not os.path.exists(metadata_dir):
            return metadata_content
        
        metadata_files = [
            "task_metadata.json",
            "config_snapshot.json",
            "system_environment.json"
        ]
        
        for metadata_file in metadata_files:
            file_path = os.path.join(metadata_dir, metadata_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        metadata_content[metadata_file] = json.load(f)
                except Exception as e:
                    self.logger.debug(f"Could not read metadata file {metadata_file}: {e}")
        
        return metadata_content

    def _calculate_workspace_size(self, workspace_dir: str) -> int:
        """Calculate total size of workspace in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(workspace_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass  # Skip files that can't be accessed
        except Exception:
            pass
        
        return total_size

    def _count_files(self, workspace_dir: str) -> int:
        """Count total number of files in workspace."""
        file_count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(workspace_dir):
                file_count += len(filenames)
        except Exception:
            pass
        
        return file_count

    def _is_critical_file(self, file_path: str) -> bool:
        """Determine if a file is critical for workspace validation."""
        critical_patterns = [
            ".benchpro/",  # All metadata files
            "inputs/",     # Original input files
            "scripts/",    # Generated scripts
            ".yaml",       # Configuration files
            ".j2"          # Template files
        ]
        
        return any(pattern in file_path for pattern in critical_patterns) 