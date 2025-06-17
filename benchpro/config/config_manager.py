"""
Configuration Manager for BenchPRO.

This module handles loading, merging, and validating YAML configuration files.
"""

import os
from typing import Dict, Any, List, Optional, Union

from benchpro.utils.logger import get_logger
from benchpro.utils.filesystem import FileSystem, RealFileSystem
from benchpro.utils.user_dir import UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.config.interfaces import ConfigLoaderInterface, ConfigMergerInterface, VariableResolverInterface, ConfigValidatorInterface
from benchpro.config.loader import YamlConfigLoader
from benchpro.config.merger import HierarchicalConfigMerger
from benchpro.config.resolver import TemplateVariableResolver
from benchpro.config.validator import ConfigValidator


class ConfigManager:
    """
    Manages configuration for BenchPRO.
    
    This class is responsible for:
    - Coordinating the loading, merging, and validation of configurations
    - Providing a simple interface for getting complete configurations
    """
    
    def __init__(self, config_dir: Optional[str] = None, profile_dir: Optional[str] = None, 
                 file_system: Optional[FileSystem] = None, 
                 user_dir_manager: Optional[UserDirectoryManagerInterface] = None,
                 config_loader: Optional[ConfigLoaderInterface] = None,
                 config_merger: Optional[ConfigMergerInterface] = None,
                 variable_resolver: Optional[VariableResolverInterface] = None,
                 config_validator: Optional[ConfigValidatorInterface] = None):
        """
        Initialize the ConfigManager.
        
        Args:
            config_dir: Directory containing internal configuration files (default and system).
            profile_dir: Directory containing user-editable profile configuration files.
            file_system: FileSystem implementation to use. If None, RealFileSystem is used.
            user_dir_manager: UserDirectoryManager instance. If None, uses the default instance.
            config_loader: ConfigLoader instance. If None, creates a new YamlConfigLoader.
            config_merger: ConfigMerger instance. If None, creates a new HierarchicalConfigMerger.
            variable_resolver: VariableResolver instance. If None, creates a new TemplateVariableResolver.
            config_validator: ConfigValidator instance. If None, creates a new ConfigValidator.
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ConfigManager")
        
        # Set file system implementation
        self.file_system = file_system or RealFileSystem()
        
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        # Create or use the provided components
        self.config_loader = config_loader or YamlConfigLoader(
            config_dir=config_dir,
            profile_dir=profile_dir,
            file_system=self.file_system,
            user_dir_manager=self.user_dir_manager
        )
        
        self.config_merger = config_merger or HierarchicalConfigMerger()
        self.variable_resolver = variable_resolver or TemplateVariableResolver()
        self.config_validator = config_validator or ConfigValidator()
        
        self.logger.debug("ConfigManager initialized with components:")
        self.logger.debug(f"  - ConfigLoader: {self.config_loader.__class__.__name__}")
        self.logger.debug(f"  - ConfigMerger: {self.config_merger.__class__.__name__}")
        self.logger.debug(f"  - VariableResolver: {self.variable_resolver.__class__.__name__}")
        self.logger.debug(f"  - ConfigValidator: {self.config_validator.__class__.__name__}")
    
    def get_complete_config(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a complete configuration for a profile.
        
        This method:
        1. Loads the profile configuration
        2. Loads the default and system configurations
        3. Merges the configurations with proper precedence
        4. Substitutes variables in the configuration
        5. Validates the configuration against the appropriate schema
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            Complete configuration dictionary.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the configuration is invalid.
        """
        self.logger.info(f"Getting complete configuration for profile: {profile_name}")
        
        # Check if task_type is specified in CLI overrides
        task_type = None
        system_name = None
        if cli_overrides:
            if "task_type" in cli_overrides:
                task_type = cli_overrides["task_type"]
            if "system" in cli_overrides:
                system_name = cli_overrides["system"]
        
        # Load profile configuration first to determine task_type
        profile_config = self.config_loader.load_profile_config(profile_name, task_type)
        
        # Determine task_type from profile
        if not task_type:
            task_type = profile_config.get("task_type")
        if not task_type:
            self.logger.warning("No task_type specified in profile config, assuming 'application'")
            task_type = "application"
        
        # Load default and system configurations
        default_config = self.config_loader.load_default_config()
        system_config = self.config_loader.load_system_config(system_name)
        
        # Merge configurations in order of precedence
        configs = [default_config, system_config, profile_config]
        
        # Add CLI overrides if provided
        if cli_overrides:
            configs.append(cli_overrides)
        
        # Merge configurations
        merged_config = self.config_merger.merge_all(configs)
        
        # Apply smart defaults to avoid redundant configuration
        resolved_config = self._apply_smart_defaults(merged_config)
        
        # Substitute variables
        resolved_config = self.variable_resolver.resolve(resolved_config)
        
        # Validate configuration
        validated_config = self.config_validator.validate(resolved_config)
        
        return validated_config
    
    def _apply_smart_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply smart defaults to avoid redundant configuration.
        
        This method implements the logic to automatically set related configuration
        fields based on primary settings, reducing the need for users to specify
        redundant or confusing parameter combinations.
        
        Args:
            config: The merged configuration dictionary.
            
        Returns:
            Configuration with smart defaults applied.
        """
        # Make a copy to avoid modifying the input
        result = config.copy()
        
        # Get execution type
        execution_type = result.get("execution", {}).get("type", "local")
        
        # Apply scheduler defaults based on execution type
        if "job" not in result:
            result["job"] = {}
            
        # Set smart defaults for job.scheduler based on execution.type
        if execution_type == "local":
            # For local execution, always set scheduler to local (will be ignored)
            result.setdefault("job", {})["scheduler"] = "local"
        elif execution_type == "sched":
            # For scheduled execution, default to slurm unless explicitly set to something else
            current_scheduler = result.get("job", {}).get("scheduler")
            if not current_scheduler or current_scheduler == "local":
                result.setdefault("job", {})["scheduler"] = "slurm"
            # If scheduler is explicitly set to something else (like "pbs"), preserve it
        
        self.logger.debug(f"Applied smart defaults: execution.type={execution_type}, job.scheduler={result['job']['scheduler']}")
        
        return result
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration against its schema.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            List of validation errors, or empty list if validation passed.
        """
        try:
            self.config_validator.validate(config)
            return []  # No errors if validation passes
        except ValueError as e:
            # Extract error message
            error_message = str(e)
            if "Configuration validation failed:" in error_message:
                # Extract the detailed validation errors
                errors_part = error_message.split("Configuration validation failed:", 1)[1].strip()
                # Split by commas and filter out empty lines
                error_lines = []
                for line in errors_part.split(','):
                    line = line.strip()
                    if line:
                        error_lines.append(line)
                return error_lines
            else:
                # If it's a different kind of error, just return the message
                return [error_message]
    
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
        return self.config_validator.get_schema_json(task_type)
    
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
        return self.config_validator.generate_example(task_type)
    
    # Backward compatibility methods
    
    def load_default_config(self) -> Dict[str, Any]:
        """
        Load the default configuration.
        
        Returns:
            Default configuration dictionary.
            
        Raises:
            FileNotFoundError: If the default configuration file doesn't exist.
        """
        self.logger.info("Loading default configuration")
        return self.config_loader.load_default_config()
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the system configuration.
        
        Args:
            system_name: Name of the system configuration to load. If None, uses 'default'.
            
        Returns:
            System configuration dictionary.
            
        Raises:
            FileNotFoundError: If the system configuration file doesn't exist.
        """
        self.logger.info(f"Loading system configuration: {system_name or 'default'}")
        return self.config_loader.load_system_config(system_name)
    
    def load_profile_config(self, profile_name: str, task_type: Optional[str] = None, 
                         system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from a profile.
        
        Args:
            profile_name: Name of the profile to load.
            task_type: Type of task (application or benchmark).
                       If None, will be determined from the profile configuration.
            system_name: Name of the system configuration to load.
                       If None, will use 'default'.
            
        Returns:
            The profile configuration with defaults merged.
            
        Raises:
            FileNotFoundError: If the profile doesn't exist.
            ValueError: If the configuration validation fails.
        """
        self.logger.info(f"Loading profile configuration: {profile_name}")
        
        # Load profile configuration
        profile_config = self.config_loader.load_profile_config(profile_name, task_type)
        
        # Determine task_type from profile
        if not task_type:
            task_type = profile_config.get("task_type")
        if not task_type:
            self.logger.warning("No task_type specified in profile config, assuming 'application'")
            task_type = "application"
        
        # Load default and system configurations
        default_config = self.load_default_config()
        system_config = self.load_system_config(system_name)
        
        # Merge configurations in order of precedence
        configs = [default_config, system_config, profile_config]
        
        # Merge configurations
        merged_config = self.config_merger.merge_all(configs)
        
        # Substitute variables
        resolved_config = self.variable_resolver.resolve(merged_config)
        
        return resolved_config
    
    def merge_configs(self, profile_name: Union[str, Dict[str, Any]], cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load and merge configurations for a profile.
        
        Args:
            profile_name: Name of the profile to load or a profile configuration dictionary.
            cli_overrides: CLI parameter overrides.
            
        Returns:
            The merged configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the configuration validation fails.
        """
        # Get task type from CLI overrides if specified
        task_type = cli_overrides.get("task_type") if cli_overrides else None
        system_name = cli_overrides.get("system") if cli_overrides else None
        
        # Load profile configuration
        if isinstance(profile_name, dict):
            profile_config = profile_name
        else:
            profile_config = self.load_profile_config(profile_name, task_type, system_name)
        
        # If task_type not specified in CLI overrides, get it from the profile
        if not task_type and isinstance(profile_name, str):
            task_type = profile_config.get("task_type", "benchmark")  # Default to benchmark for backward compatibility
        
        # Merge CLI overrides if provided
        if cli_overrides:
            self.logger.debug("Merging configurations")
            merged_config = self.config_merger.merge_configs(profile_config, cli_overrides)
        else:
            merged_config = profile_config
        
        # Apply smart defaults to avoid redundant configuration
        merged_config = self._apply_smart_defaults(merged_config)
        
        return merged_config 