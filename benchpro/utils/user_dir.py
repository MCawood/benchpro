"""
User Directory Manager for BenchPRO.

This module provides functionality for managing user-specific directories and files.
"""

import os
import logging
import stat
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Protocol, List

from benchpro.utils.filesystem import FileSystem, RealFileSystem

# Check if we're in completion mode
if "_BP_COMPLETE" in os.environ:
    # In completion mode, use a null logger
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
else:
    # Normal mode, use the regular logger
    logger = logging.getLogger(__name__)


class UserDirectoryManagerInterface:
    """
    Interface for managing user-specific directories for BenchPRO.
    
    This interface defines the contract that all UserDirectoryManager implementations must follow.
    """
    
    def get_path(self, dir_key: str, *paths: str) -> str:
        """
        Get the path for a specific directory key, optionally joined with additional paths.
        
        Args:
            dir_key: The directory key (e.g., 'root', 'inputs', 'outputs').
            *paths: Additional path components to join.
            
        Returns:
            The full path.
            
        Raises:
            KeyError: If the directory key is not recognized.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def ensure_file_directory(self, file_path: str) -> bool:
        """
        Ensure the directory for a file exists.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            True if the directory was created or already exists, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_application_directory(self) -> str:
        """
        Get the application directory path.
        
        Returns:
            The application directory path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_benchmark_directory(self) -> str:
        """
        Get the benchmark directory path.
        
        Returns:
            The benchmark directory path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_source_directory(self) -> str:
        """
        Get the source directory path.
        
        Returns:
            The source directory path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load user settings.
        
        Returns:
            The user settings as a dictionary.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save user settings.
        
        Args:
            settings: The settings to save.
            
        Returns:
            True if the settings were saved successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def copy_default_files(self, source_dir: str, dest_dir_key: str, files: List[str], force: bool = False) -> bool:
        """
        Copy default files to a user directory.
        
        Args:
            source_dir: The source directory.
            dest_dir_key: The destination directory key.
            files: List of files to copy.
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if all files were copied successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def copy_example_profiles(self, force: bool = False) -> bool:
        """
        Copy example profiles to user directories.
        
        Args:
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if the profiles were copied successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def copy_default_source_files(self, force: bool = False) -> bool:
        """
        Copy default source files to user directories.
        
        Args:
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if the files were copied successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")


class UserDirectoryManager(UserDirectoryManagerInterface):
    """
    Manages user-specific directories for BenchPRO.
    
    Responsibilities:
    - Create and manage user-specific directories
    - Ensure proper permissions for user directories
    - Provide paths to user-specific files
    """
    
    # Default directory structure
    DEFAULT_DIRS = {
        "root": "~/.benchpro",
        "inputs": "inputs",
        "inputs_application": "inputs/application",
        "inputs_benchmark": "inputs/benchmark",
        "inputs_source": "inputs/source",
        "outputs": "outputs",
        "outputs_application": "outputs/application",
        "outputs_benchmark": "outputs/benchmark",
        "registry": "registry",
        "logs": "logs",
        "cache": "cache"
    }
    
    # Default settings
    DEFAULT_SETTINGS = {
        "application_directory": "~/.benchpro/outputs/application",
        "benchmark_directory": "~/.benchpro/outputs/benchmark",
        "inputs_directory": "~/.benchpro/inputs",
        "source_directory": "~/.benchpro/inputs/source",
        "logging_level": "INFO"
    }
    
    def __init__(self, base_dir: Optional[str] = None, file_system: Optional[FileSystem] = None):
        """
        Initialize the UserDirectoryManager.
        
        Args:
            base_dir: Base directory for user-specific files. If None, uses ~/.benchpro
            file_system: FileSystem implementation to use. If None, uses RealFileSystem.
        """
        self.file_system = file_system or RealFileSystem()
        self.base_dir = base_dir or self.DEFAULT_DIRS["root"]
        self.base_dir = self.file_system.expand_path(self.base_dir)
        
        # Create subdirectory paths
        self.dirs = {
            "root": self.base_dir,
            "inputs": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["inputs"]),
            "inputs_application": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["inputs_application"]),
            "inputs_benchmark": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["inputs_benchmark"]),
            "inputs_source": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["inputs_source"]),
            "outputs": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["outputs"]),
            "outputs_application": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["outputs_application"]),
            "outputs_benchmark": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["outputs_benchmark"]),
            "registry": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["registry"]),
            "logs": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["logs"]),
            "cache": self.file_system.join_paths(self.base_dir, self.DEFAULT_DIRS["cache"])
        }
        
        # Settings file path
        self.settings_file = self.file_system.join_paths(self.base_dir, "settings.yaml")
        
        self._is_test_environment = False
        self._test_dirs = {}
        self._original_dirs = None
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Ensure settings file exists
        self._ensure_settings_file()
        
        # Copy default source files
        self.copy_default_source_files(force=False)
        
        # Copy example profiles (benchmark and application)
        # Only do this if this is not a test environment
        if not self._is_test_environment:
            self.copy_example_profiles(force=False)
        
        # Load settings
        self.settings = self.load_settings()
    
    def get_path(self, dir_key: str, *paths: str) -> str:
        """
        Get the path for a specific directory key, optionally joined with additional paths.
        
        Args:
            dir_key: The directory key (e.g., 'root', 'inputs', 'outputs').
            *paths: Additional path components to join.
            
        Returns:
            The full path.
            
        Raises:
            KeyError: If the directory key is not recognized.
        """
        if dir_key not in self.dirs:
            raise KeyError(f"Unknown directory key: {dir_key}")
            
        if not paths:
            return self.dirs[dir_key]
            
        return self.file_system.join_paths(self.dirs[dir_key], *paths)
    
    def ensure_file_directory(self, file_path: str) -> bool:
        """
        Ensure the directory for a file exists.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            True if the directory was created or already exists, False otherwise.
        """
        dir_path = self.file_system.get_dirname(file_path)
        if not dir_path:
            return True  # No directory component
            
        try:
            self.file_system.create_directory(dir_path)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            return False
    
    def get_application_directory(self) -> str:
        """
        Get the application directory path.
        
        Returns:
            The application directory path.
        """
        return self.settings.get("application_directory", self.dirs["outputs_application"])
    
    def get_benchmark_directory(self) -> str:
        """
        Get the benchmark directory path.
        
        Returns:
            The benchmark directory path.
        """
        return self.settings.get("benchmark_directory", self.dirs["outputs_benchmark"])
    
    def get_source_directory(self) -> str:
        """
        Get the source directory path.
        
        Returns:
            The source directory path.
        """
        return self.settings.get("source_directory", self.dirs["inputs_source"])
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load user settings.
        
        Returns:
            The user settings as a dictionary.
        """
        if not self.file_system.exists(self.settings_file):
            return self.DEFAULT_SETTINGS.copy()
            
        try:
            settings = self.file_system.read_yaml(self.settings_file)
            # Merge with defaults to ensure all settings are present
            merged_settings = self.DEFAULT_SETTINGS.copy()
            merged_settings.update(settings)
            return merged_settings
        except Exception as e:
            logger.error(f"Error loading settings from {self.settings_file}: {e}")
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save user settings.
        
        Args:
            settings: The settings to save.
            
        Returns:
            True if the settings were saved successfully, False otherwise.
        """
        try:
            self.file_system.write_yaml(self.settings_file, settings)
            logger.info(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings to {self.settings_file}: {e}")
            return False
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for dir_path in self.dirs.values():
            try:
                self.file_system.create_directory(dir_path)
            except Exception as e:
                logger.error(f"Error creating directory {dir_path}: {e}")
    
    def _ensure_settings_file(self) -> None:
        """Ensure the settings file exists."""
        if not self.file_system.exists(self.settings_file):
            self.save_settings(self.DEFAULT_SETTINGS)
    
    def set_test_environment(self, temp_dir: str, test_dirs: Optional[Dict[str, str]] = None) -> None:
        """
        Configure the UserDirectoryManager for testing.
        
        Args:
            temp_dir: Temporary directory to use as the base for all test paths
            test_dirs: Optional dictionary of test-specific directory paths
        """
        self._is_test_environment = True
        
        # Store the original dirs to restore after testing if needed
        self._original_dirs = self.dirs.copy()
        
        # Set up test directories
        if test_dirs:
            self._test_dirs = test_dirs
        else:
            # Set up default test directory structure
            self._test_dirs = {
                "root": temp_dir,
                "inputs": self.file_system.join_paths(temp_dir, "inputs"),
                "inputs_application": self.file_system.join_paths(temp_dir, "inputs", "application"),
                "inputs_benchmark": self.file_system.join_paths(temp_dir, "inputs", "benchmark"), 
                "inputs_source": self.file_system.join_paths(temp_dir, "inputs", "source"),
                "outputs": self.file_system.join_paths(temp_dir, "outputs"),
                "outputs_application": self.file_system.join_paths(temp_dir, "outputs", "application"),
                "outputs_benchmark": self.file_system.join_paths(temp_dir, "outputs", "benchmark"),
                "registry": self.file_system.join_paths(temp_dir, "registry"),
                "logs": self.file_system.join_paths(temp_dir, "logs"),
                "cache": self.file_system.join_paths(temp_dir, "cache")
            }
            
            # Create all the test directories
            for dir_path in self._test_dirs.values():
                self.file_system.create_directory(dir_path)
        
        # Switch to using test directories
        self.dirs = self._test_dirs
        logger.info(f"UserDirectoryManager configured for testing with base path: {temp_dir}")
        
        # Copy reference files from examples to test environment
        self._copy_example_files_to_test_env()
    
    def reset_test_environment(self) -> None:
        """Reset the UserDirectoryManager to use the original directories."""
        if not self._is_test_environment or not self._original_dirs:
            return
            
        self.dirs = self._original_dirs
        self._is_test_environment = False
        logger.info("UserDirectoryManager reset to original directories")
    
    def _copy_example_files_to_test_env(self) -> None:
        """Copy example files from examples/inputs to the test environment."""
        if not self._is_test_environment:
            return
            
        example_dir = self._get_examples_directory()
        logger.info(f"Examples directory found at: {example_dir}")
        
        if not example_dir:
            logger.warning("Could not locate examples directory for test setup")
            return
            
        # Copy application profiles and templates
        example_app_dir = self.file_system.join_paths(example_dir, "inputs", "application")
        test_app_dir = self.get_path("inputs_application")
        
        logger.info(f"App templates - Source: {example_app_dir} (exists: {self.file_system.exists(example_app_dir)})")
        logger.info(f"App templates - Target: {test_app_dir} (exists: {self.file_system.exists(test_app_dir)})")
        
        if self.file_system.exists(example_app_dir):
            logger.info(f"Copying application examples from {example_app_dir} to {test_app_dir}")
            files_found = self.file_system.list_dir(example_app_dir)
            logger.info(f"Files found in {example_app_dir}: {files_found}")
            
            for filename in files_found:
                src_file = self.file_system.join_paths(example_app_dir, filename)
                dst_file = self.file_system.join_paths(test_app_dir, filename)
                try:
                    if self.file_system.is_file(src_file):
                        self.file_system.copy_file(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example application directory not found: {example_app_dir}")
        
        # Copy benchmark profiles and templates
        example_bench_dir = self.file_system.join_paths(example_dir, "inputs", "benchmark")
        test_bench_dir = self.get_path("inputs_benchmark")
        
        logger.info(f"Benchmark templates - Source: {example_bench_dir} (exists: {self.file_system.exists(example_bench_dir)})")
        logger.info(f"Benchmark templates - Target: {test_bench_dir} (exists: {self.file_system.exists(test_bench_dir)})")
        
        if self.file_system.exists(example_bench_dir):
            logger.info(f"Copying benchmark examples from {example_bench_dir} to {test_bench_dir}")
            files_found = self.file_system.list_dir(example_bench_dir)
            logger.info(f"Files found in {example_bench_dir}: {files_found}")
            
            for filename in files_found:
                src_file = self.file_system.join_paths(example_bench_dir, filename)
                dst_file = self.file_system.join_paths(test_bench_dir, filename)
                try:
                    if self.file_system.is_file(src_file):
                        self.file_system.copy_file(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example benchmark directory not found: {example_bench_dir}")
        
        # Copy source files
        example_source_dir = self.file_system.join_paths(example_dir, "inputs", "source")
        test_source_dir = self.get_path("inputs_source")
        
        logger.info(f"Source files - Source: {example_source_dir} (exists: {self.file_system.exists(example_source_dir)})")
        logger.info(f"Source files - Target: {test_source_dir} (exists: {self.file_system.exists(test_source_dir)})")
        
        if self.file_system.exists(example_source_dir):
            logger.info(f"Copying source examples from {example_source_dir} to {test_source_dir}")
            files_found = self.file_system.list_dir(example_source_dir)
            logger.info(f"Files found in {example_source_dir}: {files_found}")
            
            for filename in files_found:
                src_file = self.file_system.join_paths(example_source_dir, filename)
                dst_file = self.file_system.join_paths(test_source_dir, filename)
                try:
                    if self.file_system.is_file(src_file):
                        self.file_system.copy_file(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example source directory not found: {example_source_dir}")
    
    def _get_examples_directory(self) -> Optional[str]:
        """Get the path to the examples directory."""
        # Start with the current file's directory and traverse up to find the project root
        current_dir = self.file_system.get_dirname(self.file_system.get_dirname(self.file_system.get_dirname(os.path.abspath(__file__))))
        logger.info(f"Starting examples directory search from: {current_dir}")
        
        # Check if examples directory exists directly
        examples_dir = self.file_system.join_paths(current_dir, "examples")
        if self.file_system.exists(examples_dir):
            logger.info(f"Found examples directory at: {examples_dir}")
            return examples_dir
        
        # Look in the parent directory
        parent_dir = self.file_system.get_dirname(current_dir)
        examples_dir = self.file_system.join_paths(parent_dir, "examples")
        if self.file_system.exists(examples_dir):
            logger.info(f"Found examples directory at parent level: {examples_dir}")
            return examples_dir
            
        # Look in sibling directories
        for sibling in ["examples", "benchpro-examples"]:
            sibling_dir = self.file_system.join_paths(parent_dir, sibling)
            if self.file_system.exists(sibling_dir):
                logger.info(f"Found examples directory as sibling: {sibling_dir}")
                return sibling_dir
                
        return None
    
    def copy_default_files(self, source_dir: str, dest_dir_key: str, files: List[str], force: bool = False) -> bool:
        """
        Copy default files to a user directory.
        
        Args:
            source_dir: The source directory.
            dest_dir_key: The destination directory key.
            files: List of files to copy.
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if all files were copied successfully, False otherwise.
        """
        if not self.file_system.exists(source_dir):
            logger.warning(f"Source directory does not exist: {source_dir}")
            return False
            
        dest_dir = self.get_path(dest_dir_key)
        
        success = True
        for filename in files:
            src_file = self.file_system.join_paths(source_dir, filename)
            dst_file = self.file_system.join_paths(dest_dir, filename)
            
            # Skip if source file doesn't exist
            if not self.file_system.exists(src_file):
                logger.warning(f"Source file does not exist: {src_file}")
                success = False
                continue
            
            # Check if destination file exists
            if self.file_system.exists(dst_file) and not force:
                # Check which file is newer (only copy if source is newer)
                try:
                    src_mtime = self.file_system.get_mtime(src_file)
                    dst_mtime = self.file_system.get_mtime(dst_file)
                    
                    if dst_mtime >= src_mtime:
                        logger.debug(f"Skipping {dst_file} - destination file is newer or same age")
                        continue
                    else:
                        logger.info(f"Updating {dst_file} - source file is newer")
                except Exception as e:
                    logger.warning(f"Error comparing timestamps for {src_file} and {dst_file}: {e}")
                    # Skip if we can't compare timestamps
                    continue
            elif self.file_system.exists(dst_file) and force:
                logger.info(f"Force overwriting {dst_file}")
            else:
                logger.debug(f"Copying new file {dst_file}")
                
            try:
                self.file_system.copy_file(src_file, dst_file)
                logger.info(f"Copied {src_file} to {dst_file}")
            except Exception as e:
                logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
                success = False
                
        return success
    
    def copy_example_profiles(self, force: bool = False) -> bool:
        """
        Copy example profiles to user directories.
        
        Args:
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if the profiles were copied successfully, False otherwise.
        """
        example_dir = self._get_examples_directory()
        if not example_dir:
            logger.warning("Could not locate examples directory")
            return False
            
        app_source_dir = self.file_system.join_paths(example_dir, "inputs", "application")
        bench_source_dir = self.file_system.join_paths(example_dir, "inputs", "benchmark")
        
        app_success = True
        bench_success = True
        
        # Copy all YAML files from application directory
        if self.file_system.exists(app_source_dir):
            app_files = [f for f in self.file_system.list_dir(app_source_dir) 
                        if f.endswith('.yaml') or f.endswith('.yml')]
            if app_files:
                app_success = self.copy_default_files(app_source_dir, "inputs_application", app_files, force=force)
            else:
                logger.debug(f"No YAML files found in {app_source_dir}")
        else:
            logger.warning(f"Application examples directory not found: {app_source_dir}")
            app_success = False
        
        # Copy all YAML files from benchmark directory
        if self.file_system.exists(bench_source_dir):
            bench_files = [f for f in self.file_system.list_dir(bench_source_dir) 
                          if f.endswith('.yaml') or f.endswith('.yml')]
            if bench_files:
                bench_success = self.copy_default_files(bench_source_dir, "inputs_benchmark", bench_files, force=force)
            else:
                logger.debug(f"No YAML files found in {bench_source_dir}")
        else:
            logger.warning(f"Benchmark examples directory not found: {bench_source_dir}")
            bench_success = False
        
        return app_success and bench_success
    
    def copy_default_source_files(self, force: bool = False) -> bool:
        """
        Copy default source files to user directories.
        
        Args:
            force: If True, overwrite existing files even if they are newer.
            
        Returns:
            True if the files were copied successfully, False otherwise.
        """
        example_dir = self._get_examples_directory()
        if not example_dir:
            logger.warning("Could not locate examples directory")
            return False
        
        source_dir = self.file_system.join_paths(example_dir, "inputs", "source")
        
        if not self.file_system.exists(source_dir):
            logger.warning(f"Source examples directory not found: {source_dir}")
            return False
        
        # Find all source files with common source file extensions
        source_files = [f for f in self.file_system.list_dir(source_dir) 
                       if f.endswith(('.c', '.cpp', '.f90', '.f', '.py', '.h', '.hpp'))]
        
        if not source_files:
            logger.debug(f"No source files found in {source_dir}")
            return True  # Not a failure, just no files to copy
        
        return self.copy_default_files(source_dir, "inputs_source", source_files, force=force)


# Factory function to get or create a UserDirectoryManager instance
_default_instance = None

def get_user_dir_manager(base_dir: Optional[str] = None, file_system: Optional[FileSystem] = None) -> UserDirectoryManagerInterface:
    """
    Get or create a UserDirectoryManager instance.
    
    Args:
        base_dir: Base directory for user-specific files. If None, uses ~/.benchpro
        file_system: FileSystem implementation to use. If None, uses RealFileSystem.
        
    Returns:
        A UserDirectoryManager instance.
    """
    global _default_instance
    
    # If specific parameters are provided, create a new instance
    if base_dir is not None or file_system is not None:
        return UserDirectoryManager(base_dir=base_dir, file_system=file_system)
    
    # Otherwise, use or create the default instance
    if _default_instance is None:
        _default_instance = UserDirectoryManager()
    
    return _default_instance

# Create a default instance for backward compatibility
# This will be deprecated in favor of dependency injection
user_dir_manager = get_user_dir_manager() 