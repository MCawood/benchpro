"""
Configuration Loader for BenchPRO.

This module provides functionality for loading configuration from different sources.
"""

import os
import platform
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
        
        # Set up user config directories
        self._setup_user_config_dirs()
    
    def _setup_user_config_dirs(self):
        """Set up user config directories and copy default system configs if needed."""
        # Create user config system directory if it doesn't exist
        user_config_dir = self.user_dir_manager.get_path("root", "config")
        user_system_dir = self.file_system.join_paths(user_config_dir, "system")
        
        # Create directories if they don't exist
        if not self.file_system.exists(user_config_dir):
            self.file_system.create_directory(user_config_dir)
            
        if not self.file_system.exists(user_system_dir):
            self.file_system.create_directory(user_system_dir)
        
        # Copy system configs to user directory if they don't exist
        self._copy_system_configs()
    
    def _copy_system_configs(self):
        """Copy system configuration files to user directory if they don't exist."""
        # Detect the current system
        current_system = platform.system().lower()
        if current_system == "darwin":
            system_name = "darwin"
        elif current_system == "linux":
            system_name = "linux"
        else:
            system_name = "default"
        
        # Source path in application directory
        source_path = self.file_system.join_paths(self.config_dir, "system", f"{system_name}.yaml")
        
        # Destination path in user directory
        user_config_dir = self.user_dir_manager.get_path("root", "config")
        user_system_dir = self.file_system.join_paths(user_config_dir, "system")
        dest_path = self.file_system.join_paths(user_system_dir, f"{system_name}.yaml")
        
        # Copy if source exists and destination doesn't
        if self.file_system.exists(source_path) and not self.file_system.exists(dest_path):
            self.logger.info(f"Copying system configuration for '{system_name}' to user directory")
            self.file_system.copy_file(source_path, dest_path)
            
        # Also copy default.yaml if it exists
        source_default_path = self.file_system.join_paths(self.config_dir, "system", "default.yaml")
        dest_default_path = self.file_system.join_paths(user_system_dir, "default.yaml")
        
        if self.file_system.exists(source_default_path) and not self.file_system.exists(dest_default_path):
            self.logger.info("Copying default system configuration to user directory")
            self.file_system.copy_file(source_default_path, dest_default_path)
            
        # If no system-specific config exists, create a symlink from the current system to default
        if not self.file_system.exists(dest_path) and self.file_system.exists(dest_default_path):
            self.logger.info(f"Creating symlink from default to {system_name} in user system configs")
            # Create symlink in file system-agnostic way
            try:
                os.symlink(dest_default_path, dest_path)
            except Exception as e:
                self.logger.warning(f"Failed to create symlink: {e}")
    
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
        
        # First try to load from user directory
        user_config_dir = self.user_dir_manager.get_path("root", "config")
        user_system_path = self.file_system.join_paths(user_config_dir, "system", f"{system_name}.yaml")
        
        if self.file_system.exists(user_system_path):
            try:
                config = self.load_file(user_system_path)
                self.logger.debug(f"Successfully loaded system configuration from user directory: {user_system_path}")
                return config
            except ValueError as e:
                self.logger.error(f"Error parsing system configuration file {user_system_path}: {e}")
                raise ValueError(f"Error parsing system configuration file {user_system_path}: {e}")
        
        # If not found in user directory, try the application directory
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
                # If system_name is not default, try to fall back to default
                if system_name != "default":
                    self.logger.warning(f"System configuration file for '{system_name}' not found, falling back to default")
                    return self.load_system_config("default")
                else:
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
        Load configuration from a profile.
        
        Args:
            profile_name: Name of the profile.
            task_type: Type of task (application or benchmark) to help with path resolution.
            
        Returns:
            The profile configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
        """
        # Check if profile_name is a file path
        if os.path.isfile(profile_name):
            self.logger.debug(f"Loading profile from file: {profile_name}")
            profile_config = self.load_file(profile_name)
            # Store the source file path in the configuration
            if "_metadata" not in profile_config:
                profile_config["_metadata"] = {}
            profile_config["_metadata"]["source_path"] = profile_name
            return profile_config
            
        # Determine where to look for this profile
        if task_type == "application":
            # Look in application directory
            app_path = self.user_dir_manager.get_path("inputs_application")
            yaml_path = os.path.join(app_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading application profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
                
        elif task_type == "benchmark":
            # Look in benchmark directory
            bench_path = self.user_dir_manager.get_path("inputs_benchmark")
            yaml_path = os.path.join(bench_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading benchmark profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
                
        # If task_type is not specified, try both locations
        if task_type is None:
            # First try application directory
            app_path = self.user_dir_manager.get_path("inputs_application")
            yaml_path = os.path.join(app_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading application profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
                
            # Then try benchmark directory
            bench_path = self.user_dir_manager.get_path("inputs_benchmark")
            yaml_path = os.path.join(bench_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading benchmark profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
                
        # If we still haven't found it, try with .yml extension
        if not profile_name.endswith('.yml'):
            profile_yml = profile_name if profile_name.endswith('.yaml') else profile_name + '.yml'
            
            # Try in application directory
            app_path = self.user_dir_manager.get_path("inputs_application")
            yaml_path = os.path.join(app_path, profile_yml)
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading application profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
                
            # Try in benchmark directory
            bench_path = self.user_dir_manager.get_path("inputs_benchmark")
            yaml_path = os.path.join(bench_path, profile_yml)
            if os.path.isfile(yaml_path):
                self.logger.debug(f"Loading benchmark profile from: {yaml_path}")
                profile_config = self.load_file(yaml_path)
                # Store the source file path in the configuration
                if "_metadata" not in profile_config:
                    profile_config["_metadata"] = {}
                profile_config["_metadata"]["source_path"] = yaml_path
                return profile_config
         
        # If we get here, the profile doesn't exist
        raise FileNotFoundError(f"Profile not found: {profile_name}") 