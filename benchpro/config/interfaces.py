"""
Configuration System Interfaces for BenchPRO.

This module defines the interfaces for the configuration system components.
These interfaces allow for dependency injection and easier testing.
"""

from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class ConfigLoaderInterface(Protocol):
    """
    Interface for loading configuration from different sources.
    
    Responsibilities:
    - Load configuration from files
    - Handle different file formats
    - Handle file system operations
    """
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file.
            
        Returns:
            The loaded configuration.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file is invalid.
        """
        ...
    
    def load_default_config(self) -> Dict[str, Any]:
        """
        Load the default configuration.
        
        Returns:
            The default configuration.
            
        Raises:
            FileNotFoundError: If the default configuration file is not found.
            ValueError: If the default configuration file is invalid.
        """
        ...
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the system-specific configuration.
        
        Args:
            system_name: Name of the system to load configuration for.
                       If None, will use 'default' system.
                
        Returns:
            The system configuration.
            
        Raises:
            FileNotFoundError: If the system configuration file is not found.
            ValueError: If the system configuration file is invalid.
        """
        ...
    
    @abstractmethod
    def load_profile_config(self, profile_name: str, task_type: Optional[str] = None, 
                           system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a profile configuration.
        
        Args:
            profile_name: Name of the profile to load.
            task_type: Type of task (application or benchmark).
                     If None, will try to auto-detect, but this is not recommended.
            system_name: Name of the system configuration to load.
                       If None, will use 'default'.
            
        Returns:
            The profile configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the profile file is invalid.
        """
        pass


@runtime_checkable
class ConfigMergerInterface(Protocol):
    """
    Interface for merging configurations with proper precedence.
    
    Responsibilities:
    - Merge configurations from different sources
    - Handle precedence rules
    - Handle deep merging of nested dictionaries
    """
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations.
        
        Args:
            base: Base configuration.
            override: Configuration to override the base.
            
        Returns:
            Merged configuration.
        """
        ...
    
    def merge_all(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple configurations.
        
        Args:
            configs: List of configurations to merge, in order of precedence (lowest to highest).
            
        Returns:
            Merged configuration.
        """
        ...


@runtime_checkable
class VariableResolverInterface(Protocol):
    """
    Interface for substituting variables in configuration values.
    
    Responsibilities:
    - Substitute variables in configuration values
    - Handle environment variables
    - Handle recursive variable references
    """
    
    def resolve(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute variables in configuration values.
        
        Variables can be referenced using ${variable} syntax.
        Environment variables can be referenced using ${ENV:VARIABLE} syntax.
        
        Args:
            config: Configuration dictionary to substitute variables in.
            
        Returns:
            Configuration dictionary with variables substituted.
            
        Raises:
            ValueError: If there are unresolvable variables or circular references.
        """
        ...


@runtime_checkable
class ConfigValidatorInterface(Protocol):
    """
    Interface for validating configuration against schemas.
    
    Responsibilities:
    - Validate configuration against schemas
    - Provide schema information
    - Generate example configurations
    """
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a complete configuration dictionary against the appropriate schemas.
        
        Performs both global and task-specific validation.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid or the task type is unknown.
        """
        ...
    
    def validate_global(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the global configuration settings.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated global configuration dictionary.
            
        Raises:
            ValueError: If the global configuration is invalid.
        """
        ...
    
    def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task-specific configuration settings.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated task configuration dictionary.
            
        Raises:
            ValueError: If the task configuration is invalid or the task type is unknown.
        """
        ...
    
    def get_schema(self, task_type: str) -> Dict[str, Any]:
        """
        Get the schema for a task type.
        
        Args:
            task_type: Type of task (application or benchmark).
            
        Returns:
            Schema dictionary.
            
        Raises:
            ValueError: If the task type is unknown.
        """
        ...
    
    def get_schema_json(self, task_type: str) -> str:
        """
        Get the schema for a task type as JSON.
        
        Args:
            task_type: Type of task (application or benchmark).
            
        Returns:
            Schema as JSON string.
            
        Raises:
            ValueError: If the task type is unknown.
        """
        ...
    
    def generate_example(self, task_type: str) -> Dict[str, Any]:
        """
        Generate an example configuration for a task type.
        
        Args:
            task_type: Type of task (application or benchmark).
            
        Returns:
            Example configuration.
            
        Raises:
            ValueError: If the task type is unknown.
        """
        ... 