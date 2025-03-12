"""
Configuration Loader for BenchPRO.

This module provides functionality for loading configuration from different sources.
"""

import os
from typing import Dict, Any, Optional, List

import yaml

from benchpro.utils.logger import get_logger
from benchpro.utils.filesystem import FileSystem, RealFileSystem
from benchpro.utils.user_dir import UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.config.interfaces import ConfigLoaderInterface


class YamlConfigLoader(ConfigLoaderInterface):
    """
    Loads configuration from YAML files.
    
    Responsibilities:
    - Load configuration from YAML files
    - Handle file system operations
    - Provide access to default, system, and profile configurations
    """
    
    def __init__(self, config_dir: Optional[str] = None, profile_dir: Optional[str] = None,
                 file_system: Optional[FileSystem] = None,
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None):
        """
        Initialize the YamlConfigLoader.
        
        Args:
            config_dir: Directory containing internal configuration files (default and system).
            profile_dir: Directory containing user-editable profile configuration files.
            file_system: FileSystem implementation to use. If None, RealFileSystem is used.
            user_dir_manager: UserDirectoryManager instance. If None, uses the default instance.
        """
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing YamlConfigLoader")
        
        # Set file system implementation
        self.file_system = file_system or RealFileSystem()
        
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        # Set internal config directory for default configurations
        if config_dir is None:
            # Use the directory where this module is located
            self.config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_dir = os.path.join(self.config_dir, "config")
        else:
            self.config_dir = config_dir
            
        self.logger.debug(f"Using config directory: {self.config_dir}")
            
        # Set user profile directory
        self.profile_dir = profile_dir
        
        if self.profile_dir:
            self.logger.debug(f"Using custom profile directory: {self.profile_dir}")
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            file_path: Path to the YAML file.
            
        Returns:
            The loaded configuration.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file is invalid YAML.
        """
        self.logger.debug(f"Loading configuration from file: {file_path}")
        
        try:
            return self.file_system.read_yaml(file_path)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {file_path}")
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML file: {e}")
            raise ValueError(f"Error parsing YAML file: {e}")
    
    def load_default_config(self) -> Dict[str, Any]:
        """
        Load the default configuration.
        
        Returns:
            The default configuration.
            
        Raises:
            FileNotFoundError: If the default configuration file is not found.
            ValueError: If the default configuration file is invalid.
        """
        default_config_path = self.file_system.join_paths(self.config_dir, "default.yaml")
        self.logger.debug(f"Loading default configuration from {default_config_path}")
        
        return self.load_file(default_config_path)
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the system configuration.
        
        Args:
            system_name: Name of the system configuration to load. If None, uses 'default'.
            
        Returns:
            The system configuration.
            
        Raises:
            FileNotFoundError: If the system configuration file doesn't exist.
            ValueError: If the system configuration file is invalid.
        """
        system_name = system_name or "default"
        self.logger.debug(f"Loading system configuration: {system_name}")
        
        # Try to load from the system directory first
        system_path = self.file_system.join_paths(self.config_dir, "system", f"{system_name}.yaml")
        try:
            config = self.load_file(system_path)
            self.logger.debug(f"Successfully loaded system configuration from: {system_path}")
            return config
        except FileNotFoundError:
            self.logger.debug(f"System configuration not found at: {system_path}")
            
            # For backward compatibility and tests, try loading from config_dir/system_default.yaml
            alt_system_path = self.file_system.join_paths(self.config_dir, f"system_{system_name}.yaml")
            try:
                config = self.load_file(alt_system_path)
                self.logger.debug(f"Successfully loaded system configuration from: {alt_system_path}")
                return config
            except FileNotFoundError:
                self.logger.warning(f"System configuration file not found: {system_path}")
                self.logger.warning("Using empty system configuration")
                return {}
            except ValueError as e:
                self.logger.error(f"Error parsing system configuration file {alt_system_path}: {e}")
                raise ValueError(f"Error parsing system configuration file {alt_system_path}: {e}")
        except ValueError as e:
            self.logger.error(f"Error parsing system configuration file {system_path}: {e}")
            raise ValueError(f"Error parsing system configuration file {system_path}: {e}")
    
    def load_profile_config(self, profile_name: str, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a profile configuration.
        
        Args:
            profile_name: Name of the profile to load.
            task_type: Type of task (application or benchmark).
                     If None, will try to auto-detect, but this is not recommended.
        
        Returns:
            The profile configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the profile file is invalid.
        """
        self.logger.debug(f"Loading profile configuration for profile: {profile_name}, task_type: {task_type}")
        
        # If profile_name already has a .yaml extension, use it as is
        if profile_name.endswith(".yaml"):
            profile_name = profile_name[:-5]
            
        # List of potential profile paths to try
        potential_paths = []
        
        # If a custom profile directory is provided
        if self.profile_dir:
            self.logger.debug(f"Looking for profile in custom directory: {self.profile_dir}")
            
            # When task_type is explicitly specified, ONLY look in that directory
            if task_type == "application":
                app_dir = self.file_system.join_paths(self.profile_dir, "inputs", "application")
                potential_paths.append(self.file_system.join_paths(app_dir, f"{profile_name}.yaml"))
                self.logger.debug(f"Looking for application profile at: {potential_paths[-1]}")
                
            elif task_type == "benchmark":
                bench_dir = self.file_system.join_paths(self.profile_dir, "inputs", "benchmark")
                potential_paths.append(self.file_system.join_paths(bench_dir, f"{profile_name}.yaml"))
                self.logger.debug(f"Looking for benchmark profile at: {potential_paths[-1]}")
                
            # If no task_type specified, use old behavior but warn
            else:
                # Only as a fallback, allow looking in the root directory
                potential_paths.append(self.file_system.join_paths(self.profile_dir, f"{profile_name}.yaml"))
                self.logger.warning(f"No task_type specified - looking in profile root dir: {potential_paths[-1]}")
                
                # Then also look in application and benchmark subdirectories
                app_dir = self.file_system.join_paths(self.profile_dir, "inputs", "application")
                potential_paths.append(self.file_system.join_paths(app_dir, f"{profile_name}.yaml"))
                self.logger.warning(f"No task_type specified - also looking in application dir: {potential_paths[-1]}")
                
                bench_dir = self.file_system.join_paths(self.profile_dir, "inputs", "benchmark")
                potential_paths.append(self.file_system.join_paths(bench_dir, f"{profile_name}.yaml"))
                self.logger.warning(f"No task_type specified - also looking in benchmark dir: {potential_paths[-1]}")
        
        # Otherwise, look in the user directories
        else:
            # When task_type is explicitly specified, ONLY look in that directory
            if task_type == "application":
                app_path = self.user_dir_manager.get_path("inputs_application")
                potential_paths.append(self.file_system.join_paths(app_path, f"{profile_name}.yaml"))
                self.logger.debug(f"Looking for application profile at: {potential_paths[-1]}")
                
            elif task_type == "benchmark":
                bench_path = self.user_dir_manager.get_path("inputs_benchmark")
                potential_paths.append(self.file_system.join_paths(bench_path, f"{profile_name}.yaml"))
                self.logger.debug(f"Looking for benchmark profile at: {potential_paths[-1]}")
                
            # If no task_type specified, use old behavior but warn
            else:
                self.logger.warning("No task_type specified when loading profile - behavior may be unpredictable")
                
                # Look in application directory first, then benchmark
                app_path = self.user_dir_manager.get_path("inputs_application")
                potential_paths.append(self.file_system.join_paths(app_path, f"{profile_name}.yaml"))
                self.logger.warning(f"No task_type specified - looking in application dir: {potential_paths[-1]}")
                
                bench_path = self.user_dir_manager.get_path("inputs_benchmark")
                potential_paths.append(self.file_system.join_paths(bench_path, f"{profile_name}.yaml"))
                self.logger.warning(f"No task_type specified - also looking in benchmark dir: {potential_paths[-1]}")
        
        # Try each potential path
        for path in potential_paths:
            try:
                config = self.load_file(path)
                self.logger.debug(f"Successfully loaded profile from: {path}")
                
                # If task_type was explicitly provided, validate that the loaded config matches
                if task_type and config.get("task_type") != task_type:
                    self.logger.warning(
                        f"Profile loaded from {path} has task_type '{config.get('task_type')}', "
                        f"but '{task_type}' was requested. This may cause issues."
                    )
                    
                return config
            except FileNotFoundError:
                self.logger.debug(f"Profile not found at: {path}")
                continue
            except ValueError as e:
                self.logger.error(f"Error parsing profile file {path}: {e}")
                raise ValueError(f"Error parsing profile file {path}: {e}")
        
        # If we get here, the profile wasn't found
        self.logger.error(f"Profile not found: {profile_name}")
        raise FileNotFoundError(f"Profile not found: {profile_name}. Searched in: {', '.join(potential_paths)}") 