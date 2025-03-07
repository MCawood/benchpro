"""
User Directory Manager for BenchPRO.

This module provides functionality for managing user-specific directories and files.
"""

import os
import logging
import stat
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Check if we're in completion mode
if "_BP_COMPLETE" in os.environ:
    # In completion mode, use a null logger
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
else:
    # Normal mode, use the regular logger
    logger = logging.getLogger(__name__)

class UserDirectoryManager:
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
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the UserDirectoryManager.
        
        Args:
            base_dir: Base directory for user-specific files. If None, uses ~/.benchpro
        """
        self.base_dir = base_dir or self.DEFAULT_DIRS["root"]
        self.base_dir = os.path.expanduser(self.base_dir)
        
        # Create subdirectory paths
        self.dirs = {
            "root": self.base_dir,
            "inputs": os.path.join(self.base_dir, self.DEFAULT_DIRS["inputs"]),
            "inputs_application": os.path.join(self.base_dir, self.DEFAULT_DIRS["inputs_application"]),
            "inputs_benchmark": os.path.join(self.base_dir, self.DEFAULT_DIRS["inputs_benchmark"]),
            "inputs_source": os.path.join(self.base_dir, self.DEFAULT_DIRS["inputs_source"]),
            "outputs": os.path.join(self.base_dir, self.DEFAULT_DIRS["outputs"]),
            "outputs_application": os.path.join(self.base_dir, self.DEFAULT_DIRS["outputs_application"]),
            "outputs_benchmark": os.path.join(self.base_dir, self.DEFAULT_DIRS["outputs_benchmark"]),
            "registry": os.path.join(self.base_dir, self.DEFAULT_DIRS["registry"]),
            "logs": os.path.join(self.base_dir, self.DEFAULT_DIRS["logs"]),
            "cache": os.path.join(self.base_dir, self.DEFAULT_DIRS["cache"])
        }
        
        # Settings file path
        self.settings_file = os.path.join(self.base_dir, "settings.yaml")
        
        self._is_test_environment = False
        self._test_dirs = {}
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Ensure settings file exists
        self._ensure_settings_file()
        
        # Copy default source files
        self.copy_default_source_files()
        
        # Copy example profiles (benchmark and application)
        # Only do this if this is not a test environment
        if not self._is_test_environment:
            self.copy_example_profiles()
        
        # Load settings
        self.settings = self.load_settings()
    
    def set_test_environment(self, temp_dir: str, test_dirs: Optional[Dict[str, str]] = None):
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
                "inputs": os.path.join(temp_dir, "inputs"),
                "inputs_application": os.path.join(temp_dir, "inputs", "application"),
                "inputs_benchmark": os.path.join(temp_dir, "inputs", "benchmark"), 
                "inputs_source": os.path.join(temp_dir, "inputs", "source"),
                "outputs": os.path.join(temp_dir, "outputs"),
                "outputs_application": os.path.join(temp_dir, "outputs", "application"),
                "outputs_benchmark": os.path.join(temp_dir, "outputs", "benchmark"),
                "registry": os.path.join(temp_dir, "registry"),
                "logs": os.path.join(temp_dir, "logs"),
                "cache": os.path.join(temp_dir, "cache")
            }
            
            # Create all the test directories
            for dir_path in self._test_dirs.values():
                os.makedirs(dir_path, exist_ok=True)
        
        # Switch to using test directories
        self.dirs = self._test_dirs
        logger.info(f"UserDirectoryManager configured for testing with base path: {temp_dir}")
        
        # Copy reference files from examples to test environment
        self._copy_example_files_to_test_env()
    
    def _copy_example_files_to_test_env(self):
        """Copy example files from examples/inputs to the test environment."""
        if not self._is_test_environment:
            return
            
        import shutil
        
        example_dir = self._get_examples_directory()
        logger.info(f"Examples directory found at: {example_dir}")
        
        if not example_dir:
            logger.warning("Could not locate examples directory for test setup")
            return
            
        # Copy application profiles and templates
        example_app_dir = os.path.join(example_dir, "inputs", "application")
        test_app_dir = self.get_path("inputs_application")
        
        logger.info(f"App templates - Source: {example_app_dir} (exists: {os.path.exists(example_app_dir)})")
        logger.info(f"App templates - Target: {test_app_dir} (exists: {os.path.exists(test_app_dir)})")
        
        if os.path.exists(example_app_dir):
            logger.info(f"Copying application examples from {example_app_dir} to {test_app_dir}")
            files_found = os.listdir(example_app_dir)
            logger.info(f"Files found in {example_app_dir}: {files_found}")
            
            for filename in files_found:
                src_file = os.path.join(example_app_dir, filename)
                dst_file = os.path.join(test_app_dir, filename)
                try:
                    if os.path.isfile(src_file):
                        shutil.copy(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example application directory not found: {example_app_dir}")
        
        # Copy benchmark profiles and templates
        example_bench_dir = os.path.join(example_dir, "inputs", "benchmark")
        test_bench_dir = self.get_path("inputs_benchmark")
        
        logger.info(f"Benchmark templates - Source: {example_bench_dir} (exists: {os.path.exists(example_bench_dir)})")
        logger.info(f"Benchmark templates - Target: {test_bench_dir} (exists: {os.path.exists(test_bench_dir)})")
        
        if os.path.exists(example_bench_dir):
            logger.info(f"Copying benchmark examples from {example_bench_dir} to {test_bench_dir}")
            files_found = os.listdir(example_bench_dir)
            logger.info(f"Files found in {example_bench_dir}: {files_found}")
            
            for filename in files_found:
                src_file = os.path.join(example_bench_dir, filename)
                dst_file = os.path.join(test_bench_dir, filename)
                try:
                    if os.path.isfile(src_file):
                        shutil.copy(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example benchmark directory not found: {example_bench_dir}")
        
        # Copy source files
        example_source_dir = os.path.join(example_dir, "inputs", "source")
        test_source_dir = self.get_path("inputs_source")
        
        logger.info(f"Source files - Source: {example_source_dir} (exists: {os.path.exists(example_source_dir)})")
        logger.info(f"Source files - Target: {test_source_dir} (exists: {os.path.exists(test_source_dir)})")
        
        if os.path.exists(example_source_dir):
            logger.info(f"Copying source examples from {example_source_dir} to {test_source_dir}")
            files_found = os.listdir(example_source_dir)
            logger.info(f"Files found in {example_source_dir}: {files_found}")
            
            for filename in files_found:
                src_file = os.path.join(example_source_dir, filename)
                dst_file = os.path.join(test_source_dir, filename)
                try:
                    if os.path.isfile(src_file):
                        shutil.copy(src_file, dst_file)
                        logger.info(f"Successfully copied {filename} to test environment")
                except Exception as e:
                    logger.error(f"Error copying {src_file} to {dst_file}: {str(e)}")
        else:
            logger.warning(f"Example source directory not found: {example_source_dir}")
    
    def _get_examples_directory(self):
        """Get the path to the examples directory."""
        # Start with the current file's directory and traverse up to find the project root
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logger.info(f"Starting examples directory search from: {current_dir}")
        
        # Check if examples directory exists directly
        examples_dir = os.path.join(current_dir, "examples")
        if os.path.exists(examples_dir):
            logger.info(f"Found examples directory at: {examples_dir}")
            return examples_dir
        
        # Look in the parent directory
        parent_dir = os.path.dirname(current_dir)
        examples_dir = os.path.join(parent_dir, "examples")
        if os.path.exists(examples_dir):
            logger.info(f"Found examples directory at parent level: {examples_dir}")
            return examples_dir
        
        # Check if we're in a development environment with a different structure
        # Try common locations for the examples directory
        possible_paths = [
            # Current working directory
            os.path.join(os.getcwd(), "examples"),
            # Project root (from cwd)
            os.path.join(os.path.dirname(os.getcwd()), "examples"),
            # Explicit project path if in a known location
            "/Users/mcawood/dev/benchpro_2.0/examples",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found examples directory at alternative location: {path}")
                return path
        
        # If we still can't find it, log and return None
        logger.warning(f"Could not find examples directory. Searched in:")
        logger.warning(f"  - {current_dir}/examples")
        logger.warning(f"  - {parent_dir}/examples")
        for path in possible_paths:
            logger.warning(f"  - {path}")
        
        return None
    
    def reset_test_environment(self):
        """Reset the UserDirectoryManager to use the original user paths."""
        if self._is_test_environment:
            self.dirs = self._original_dirs
            self._is_test_environment = False
            logger.info("UserDirectoryManager reset to use original paths")
        
    def _ensure_directories(self):
        """
        Ensure all required directories exist with proper permissions.
        """
        for dir_name, dir_path in self.dirs.items():
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")
                    
                    # Set permissions to user read/write/execute
                    os.chmod(dir_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                except Exception as e:
                    logger.error(f"Error creating directory {dir_path}: {str(e)}")
            else:
                # Verify permissions
                if not os.access(dir_path, os.R_OK | os.W_OK):
                    logger.warning(f"Insufficient permissions for directory: {dir_path}")
    
    def _ensure_settings_file(self):
        """
        Ensure the settings file exists with default values.
        """
        if not os.path.exists(self.settings_file):
            try:
                # Create default settings
                settings = self.DEFAULT_SETTINGS.copy()
                
                # Write settings to file
                with open(self.settings_file, 'w') as f:
                    yaml.dump(settings, f, default_flow_style=False)
                    
                logger.info(f"Created settings file: {self.settings_file}")
            except Exception as e:
                logger.error(f"Error creating settings file {self.settings_file}: {str(e)}")
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from the settings file.
        
        Returns:
            Dictionary containing settings.
        """
        if not os.path.exists(self.settings_file):
            self._ensure_settings_file()
            return self.DEFAULT_SETTINGS.copy()
            
        try:
            with open(self.settings_file, 'r') as f:
                settings = yaml.safe_load(f) or {}
                
            # Ensure all required settings exist
            for key, default_value in self.DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = default_value
                    
            # Expand user paths
            for key in ['application_directory', 'benchmark_directory', 'inputs_directory', 'source_directory']:
                if key in settings:
                    settings[key] = os.path.expanduser(settings[key])
                    
            return settings
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to the settings file.
        
        Args:
            settings: Dictionary containing settings.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Ensure the directory exists
            self.ensure_file_directory(self.settings_file)
            
            # Write settings to file
            with open(self.settings_file, 'w') as f:
                yaml.dump(settings, f, default_flow_style=False)
                
            # Update internal settings
            self.settings = settings
            
            logger.info(f"Saved settings to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False
    
    def get_application_directory(self) -> str:
        """
        Get the application output directory.
        
        Returns:
            Path to the application output directory.
        """
        app_dir = self.settings.get('application_directory', self.dirs['outputs_application'])
        
        # Ensure the directory exists
        if not os.path.exists(app_dir):
            try:
                os.makedirs(app_dir, exist_ok=True)
                logger.info(f"Created application directory: {app_dir}")
            except Exception as e:
                logger.error(f"Error creating application directory {app_dir}: {str(e)}")
                # Fall back to default
                app_dir = self.dirs['outputs_application']
                
        return app_dir
    
    def get_benchmark_directory(self) -> str:
        """
        Get the benchmark output directory.
        
        Returns:
            Path to the benchmark output directory.
        """
        bench_dir = self.settings.get('benchmark_directory', self.dirs['outputs_benchmark'])
        
        # Ensure the directory exists
        if not os.path.exists(bench_dir):
            try:
                os.makedirs(bench_dir, exist_ok=True)
                logger.info(f"Created benchmark directory: {bench_dir}")
            except Exception as e:
                logger.error(f"Error creating benchmark directory {bench_dir}: {str(e)}")
                # Fall back to default
                bench_dir = self.dirs['outputs_benchmark']
                
        return bench_dir
    
    def get_source_directory(self) -> str:
        """
        Get the source files directory.
        
        Returns:
            Path to the source files directory.
        """
        source_dir = self.settings.get('source_directory', self.dirs['inputs_source'])
        
        # Ensure the directory exists
        if not os.path.exists(source_dir):
            try:
                os.makedirs(source_dir, exist_ok=True)
                logger.info(f"Created source directory: {source_dir}")
            except Exception as e:
                logger.error(f"Error creating source directory {source_dir}: {str(e)}")
                # Fall back to default
                source_dir = self.dirs['inputs_source']
                
        return source_dir
    
    def get_path(self, dir_type: str, filename: Optional[str] = None) -> str:
        """
        Get the path to a user-specific directory or file.
        
        Args:
            dir_type: Type of directory (root, config, registry, templates, logs, cache)
            filename: Optional filename to append to the directory path
            
        Returns:
            Path to the directory or file
            
        Raises:
            ValueError: If the directory type is invalid
        """
        if dir_type not in self.dirs:
            raise ValueError(f"Invalid directory type: {dir_type}")
            
        dir_path = self.dirs[dir_type]
        
        if filename:
            return os.path.join(dir_path, filename)
        return dir_path
    
    def ensure_file_directory(self, filepath: str) -> bool:
        """
        Ensure the directory for a file exists.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory for {filepath}: {str(e)}")
            return False
            
    def copy_default_files(self, source_dir: str, target_dir_type: str, files: list) -> bool:
        """
        Copy default files to user directory if they don't exist.
        
        Args:
            source_dir: Source directory containing default files
            target_dir_type: Target directory type (config, registry, templates)
            files: List of filenames to copy
            
        Returns:
            True if successful, False otherwise
        """
        import shutil
        
        target_dir = self.get_path(target_dir_type)
        
        try:
            for filename in files:
                source_path = os.path.join(source_dir, filename)
                target_path = os.path.join(target_dir, filename)
                
                if not os.path.exists(target_path) and os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Copied default file: {filename} to {target_dir}")
            return True
        except Exception as e:
            logger.error(f"Error copying default files: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """
        Check if BenchPRO user directories are initialized.
        
        Returns:
            True if initialized, False otherwise.
        """
        # Check for required directories
        return os.path.isdir(self.get_path("root"))
            
    def copy_default_source_files(self):
        """
        Copy default source files to the source directory.
        """
        source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "sources")
        target_dir_type = "inputs_source"
        
        # Look for source files
        if os.path.isdir(source_dir):
            files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
            self.copy_default_files(source_dir, target_dir_type, files)
            
    def copy_example_profiles(self):
        """
        Copy example profile files to the user's inputs directories.
        This ensures that example profiles are available for users immediately after installation.
        """
        # Define paths relative to the package
        examples_dir = self._get_examples_directory()
        if not examples_dir:
            logger.warning("Could not locate examples directory for initialization")
            return False
            
        # Copy application profiles
        app_examples_dir = os.path.join(examples_dir, "inputs", "application")
        if os.path.isdir(app_examples_dir):
            files = [f for f in os.listdir(app_examples_dir) if os.path.isfile(os.path.join(app_examples_dir, f))]
            self.copy_default_files(app_examples_dir, "inputs_application", files)
            logger.info(f"Copied {len(files)} application profiles to user directory")
            
        # Copy benchmark profiles
        bench_examples_dir = os.path.join(examples_dir, "inputs", "benchmark")
        if os.path.isdir(bench_examples_dir):
            files = [f for f in os.listdir(bench_examples_dir) if os.path.isfile(os.path.join(bench_examples_dir, f))]
            self.copy_default_files(bench_examples_dir, "inputs_benchmark", files)
            logger.info(f"Copied {len(files)} benchmark profiles to user directory")
            
        # Copy templates
        templates_dir = os.path.join(examples_dir, "templates")
        if os.path.isdir(templates_dir):
            files = [f for f in os.listdir(templates_dir) if os.path.isfile(os.path.join(templates_dir, f))]
            self.copy_default_files(templates_dir, "templates", files)
            logger.info(f"Copied {len(files)} templates to user directory")
            
        return True

# Create a singleton instance
user_dir_manager = UserDirectoryManager() 