"""
Configuration Components for BenchPRO Task composition.

This module defines components for loading and managing task configuration.
"""

import os
import yaml
from typing import Dict, Any, Optional, List

from benchpro.executor.components.interfaces import ConfigComponent, ConfigError
from benchpro.config.config_manager import ConfigManager
from benchpro.utils.logger import get_logger
from benchpro.utils.user_dir import UserDirectoryManagerInterface, get_user_dir_manager


class BaseConfigComponent(ConfigComponent):
    """Base implementation of the ConfigComponent interface with common functionality."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None,
                 task_type: Optional[str] = None):
        """
        Initialize the configuration component.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            user_dir_manager: Optional UserDirectoryManager instance. If None, the default is used.
            task_type: Type of task ("application" or "benchmark"). Used to ensure correct profile loading.
        """
        self.logger = get_logger(__name__)
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        self.config_manager = config_manager or ConfigManager(user_dir_manager=self.user_dir_manager)
        self.config = {}
        self.task_type = task_type
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            Loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded or is invalid.
        """
        self.logger.info(f"Loading configuration from: {config_path}")
        
        try:
            # Use the config manager to load the profile configuration,
            # explicitly passing the task type to ensure correct directory
            config = self.config_manager.load_profile_config(config_path, self.task_type)
            self.config = config
            self.logger.debug(f"Configuration loaded successfully: {config}")
            
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ConfigError(f"Failed to load configuration from {config_path}: {str(e)}")
    
    def set_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set the configuration directly.
        
        Args:
            config: Configuration dictionary to set.
            
        Returns:
            The configuration that was set.
        """
        self.logger.debug(f"Setting configuration directly")
        self.config = config
        return self.config
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Current configuration as a dictionary.
        """
        return self.config
    
    def merge_config(self, override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge override configuration with the current configuration.
        
        Args:
            override_config: Configuration to merge with the current configuration.
            
        Returns:
            Merged configuration as a dictionary.
        """
        self.logger.debug(f"Merging configuration: {override_config}")
        
        try:
            # Use the config manager to merge configurations
            merged_config = self.config_manager.merge_configs(self.config, override_config)
            self.config = merged_config
            self.logger.debug(f"Merged configuration: {merged_config}")
            
            return merged_config
        except Exception as e:
            self.logger.error(f"Failed to merge configuration: {str(e)}")
            raise ConfigError(f"Failed to merge configuration: {str(e)}")


class ApplicationConfigComponent(BaseConfigComponent):
    """Component that manages application-specific configuration."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None,
                 task_type: Optional[str] = None):
        """
        Initialize the application configuration component.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            user_dir_manager: Optional UserDirectoryManager instance. If None, the default is used.
            task_type: Type of task. Should be "application" for this component.
        """
        super().__init__(config_manager, user_dir_manager, task_type or "application")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load application configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
        
        Returns:
            Loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded or is invalid.
        """
        config = super().load_config(config_path)
        
        # Validate that this is an application configuration
        if config.get("task_type") != "application":
            error_msg = f"Invalid task type: expected 'application', got '{config.get('task_type')}'"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
        
        return config
    
    def prepare_application_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare application-specific default values.
        
        Args:
            config: Current configuration.
            
        Returns:
            Configuration with defaults applied.
        """
        # Start with a copy of the config
        config = dict(config)
        
        # Set default values if not present
        if "build" not in config:
            config["build"] = {}
        
        build_config = config["build"]
        
        # Set default build values
        if "threads" not in build_config:
            build_config["threads"] = 1
        
        return config


class BenchmarkConfigComponent(BaseConfigComponent):
    """Component that manages benchmark-specific configuration."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None,
                 task_type: Optional[str] = None):
        """
        Initialize the benchmark configuration component.
        
        Args:
            config_manager: Optional ConfigManager instance. If None, a new one is created.
            user_dir_manager: Optional UserDirectoryManager instance. If None, the default is used.
            task_type: Type of task. Should be "benchmark" for this component.
        """
        super().__init__(config_manager, user_dir_manager, task_type or "benchmark")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load benchmark configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
        
        Returns:
            Loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded or is invalid.
        """
        config = super().load_config(config_path)
        
        # Validate that this is a benchmark configuration
        if config.get("task_type") != "benchmark":
            error_msg = f"Invalid task type: expected 'benchmark', got '{config.get('task_type')}'"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
        
        return config
    
    def prepare_benchmark_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare benchmark-specific default values.
        
        Args:
            config: Current configuration.
            
        Returns:
            Configuration with defaults applied.
        """
        # Start with a copy of the config
        config = dict(config)
        
        # Set default values if not present
        if "run" not in config:
            config["run"] = {}
        
        run_config = config["run"]
        
        # Set default run values
        if "threads" not in run_config:
            run_config["threads"] = 1
        
        return config 