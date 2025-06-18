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
from benchpro.config.metadata import ConfigSource, ConfigReport


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
    
    def get_complete_config_report(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> ConfigReport:
        """
        Get a complete configuration report for a profile with full tracking.
        
        This is the primary method for configuration processing, providing comprehensive
        tracking of configuration origins and generating detailed reports.
        
        This method:
        1. Loads configuration sources (default, system, profile) with metadata
        2. Merges configurations with full tracking and precedence handling
        3. Applies smart defaults as a tracked source
        4. Resolves variables in the final configuration
        5. Validates the configuration against the appropriate schema
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            ConfigReport with complete tracking information and final configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the configuration is invalid.
        """
        self.logger.info(f"Getting complete configuration report for profile: {profile_name}")
        
        # Extract system name and task type from CLI overrides if provided
        system_name = None
        task_type = None
        if cli_overrides:
            system_name = cli_overrides.get("system")
            task_type = cli_overrides.get("task_type")
        
        # Create configuration sources with metadata
        sources = self._load_configuration_sources(profile_name, task_type, system_name)
        
        # Merge all sources with comprehensive tracking
        report = self.config_merger.merge_sources(sources, profile_name, cli_overrides)
        
        # Apply smart defaults as a tracked source
        report = self._apply_smart_defaults_with_tracking(report)
        
        # Resolve variables in the final configuration
        report.final_config = self.variable_resolver.resolve(report.final_config)
        
        # Validate the final configuration
        report.final_config = self.config_validator.validate(report.final_config)
        
        self.logger.info(f"Configuration report generated with {len(report.config_metadata)} tracked parameters")
        return report
    
    def _load_configuration_sources(self, profile_name: str, task_type: Optional[str] = None, 
                                   system_name: Optional[str] = None) -> List[ConfigSource]:
        """
        Load all configuration sources with metadata tracking.
        
        Args:
            profile_name: Name of the profile to load.
            task_type: Type of task (application or benchmark).
            system_name: Name of the system configuration to load.
            
        Returns:
            List of ConfigSource objects in precedence order (lowest to highest).
        """
        sources = []
        
        # Load default configuration (precedence 1)
        default_config = self.config_loader.load_default_config()
        sources.append(ConfigSource(
            config=default_config,
            source="default",
            source_file=self._get_default_config_path(),
            precedence=1
        ))
        
        # Load system configuration (precedence 2)
        system_config = self.config_loader.load_system_config(system_name)
        if system_config:  # Only add if not empty
            source_name = f"system:{system_name}" if system_name else "system:default"
            sources.append(ConfigSource(
                config=system_config,
                source=source_name,
                source_file=self._get_system_config_path(system_name),
                precedence=2
            ))
        
        # Load profile configuration (precedence 3)
        profile_config = self.config_loader.load_profile_config(profile_name, task_type)
        
        # Determine task_type from profile if not specified
        if not task_type:
            task_type = profile_config.get("task_type")
        if not task_type:
            self.logger.warning("No task_type specified in profile config, assuming 'application'")
            task_type = "application"
        
        sources.append(ConfigSource(
            config=profile_config,
            source=f"profile:{profile_name}",
            source_file=self._get_profile_config_path(profile_name, task_type),
            precedence=3
        ))
        
        return sources
    
    def _apply_smart_defaults_with_tracking(self, report: ConfigReport) -> ConfigReport:
        """
        Apply smart defaults to the configuration with tracking.
        
        Args:
            report: Current configuration report.
            
        Returns:
            Updated configuration report with smart defaults applied.
        """
        # Get the current configuration
        config = report.final_config.copy()
        
        # Apply smart defaults
        smart_defaults = self._get_smart_defaults(config)
        
        if smart_defaults:
            # Create a smart defaults source
            smart_source = ConfigSource(
                config=smart_defaults,
                source="smart_defaults",
                precedence=4
            )
            
            # Apply the smart defaults with tracking
            from benchpro.config.metadata import MergeStep, ConfigValue, flatten_config_for_tracking
            
            # Track changes
            flat_defaults = flatten_config_for_tracking(smart_defaults)
            changes = {}
            parameters_added = 0
            parameters_modified = 0
            
            for param_path, value in flat_defaults.items():
                changes[param_path] = value
                if param_path in report.config_metadata:
                    parameters_modified += 1
                else:
                    parameters_added += 1
                
                # Update metadata
                report.config_metadata[param_path] = ConfigValue(
                    value=value,
                    source="smart_defaults",
                    precedence=4
                )
            
            # Apply the merge
            self.config_merger._deep_update(report.final_config, smart_defaults)
            
            # Add to merge history
            merge_step = MergeStep(
                step_name="Applying smart defaults",
                source="smart_defaults",
                changes=changes,
                parameters_added=parameters_added,
                parameters_modified=parameters_modified
            )
            report.merge_history.append(merge_step)
        
        return report
    
    def _get_smart_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get smart defaults based on the current configuration.
        
        This extracts the logic from _apply_smart_defaults to return just the defaults.
        
        Args:
            config: Current configuration.
            
        Returns:
            Dictionary of smart defaults to apply.
        """
        smart_defaults = {}
        
        # Get execution type
        execution_type = config.get("execution", {}).get("type", "local")
        
        # Set smart defaults for job.scheduler based on execution.type
        if execution_type == "local":
            # For local execution, always set scheduler to local (will be ignored)
            smart_defaults.setdefault("job", {})["scheduler"] = "local"
        elif execution_type == "sched":
            # For scheduled execution, default to slurm unless explicitly set to something else
            current_scheduler = config.get("job", {}).get("scheduler")
            if not current_scheduler or current_scheduler == "local":
                smart_defaults.setdefault("job", {})["scheduler"] = "slurm"
            # If scheduler is explicitly set to something else (like "pbs"), preserve it
        
        self.logger.debug(f"Generated smart defaults: {smart_defaults}")
        return smart_defaults
    
    def _get_default_config_path(self) -> Optional[str]:
        """Get the path to the default configuration file."""
        try:
            return self.config_loader.file_system.join_paths(self.config_loader.config_dir, "default.yaml")
        except Exception:
            return None
    
    def _get_system_config_path(self, system_name: Optional[str]) -> Optional[str]:
        """Get the path to the system configuration file."""
        try:
            system_name = system_name or "default"
            
            # Check user directory first (matches ConfigLoader logic)
            user_config_dir = self.config_loader.user_dir_manager.get_path("root", "config")
            user_system_path = self.config_loader.file_system.join_paths(user_config_dir, "system", f"{system_name}.yaml")
            
            if self.config_loader.file_system.exists(user_system_path):
                return user_system_path
            
            # Fall back to application directory
            system_path = self.config_loader.file_system.join_paths(self.config_loader.config_dir, "system", f"{system_name}.yaml")
            if self.config_loader.file_system.exists(system_path):
                return system_path
                
            # Try alternative path format for backward compatibility
            alt_system_path = self.config_loader.file_system.join_paths(self.config_loader.config_dir, f"system_{system_name}.yaml")
            if self.config_loader.file_system.exists(alt_system_path):
                return alt_system_path
                
            return None
        except Exception:
            return None
    
    def _get_profile_config_path(self, profile_name: str, task_type: str) -> Optional[str]:
        """Get the path to the profile configuration file."""
        try:
            # Check if profile_name is already a file path
            if os.path.isfile(profile_name):
                return profile_name
            
            # Determine directory based on task type
            if task_type == "application":
                app_path = self.config_loader.user_dir_manager.get_path("inputs_application")
                yaml_path = os.path.join(app_path, profile_name)
                if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                    yaml_path += '.yaml'
                    
                if os.path.isfile(yaml_path):
                    return yaml_path
                    
            elif task_type == "benchmark":
                bench_path = self.config_loader.user_dir_manager.get_path("inputs_benchmark")
                yaml_path = os.path.join(bench_path, profile_name)
                if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                    yaml_path += '.yaml'
                    
                if os.path.isfile(yaml_path):
                    return yaml_path
            
            # If task_type is not specified or file not found, try both locations
            # Try application directory first
            app_path = self.config_loader.user_dir_manager.get_path("inputs_application")
            yaml_path = os.path.join(app_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                return yaml_path
                
            # Try benchmark directory
            bench_path = self.config_loader.user_dir_manager.get_path("inputs_benchmark")
            yaml_path = os.path.join(bench_path, profile_name)
            if not yaml_path.endswith('.yaml') and not yaml_path.endswith('.yml'):
                yaml_path += '.yaml'
                
            if os.path.isfile(yaml_path):
                return yaml_path
                
            return None
        except Exception:
            return None

    def get_complete_config(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a complete configuration for a profile (compatibility method).
        
        This method provides backward compatibility by using the new tracking system
        internally but only returning the final configuration dictionary.
        For new code, use get_complete_config_report() for full tracking information.
        
        Args:
            profile_name: Name of the profile to load.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            Complete configuration dictionary.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the configuration is invalid.
        """
        self.logger.debug(f"Getting complete configuration for profile: {profile_name} (compatibility mode)")
        
        # Use the new tracking method and extract just the final config
        report = self.get_complete_config_report(profile_name, cli_overrides)
        return report.final_config
    
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
        Load and merge configurations for a profile (compatibility method).
        
        This method provides backward compatibility by using the new tracking system
        internally but only returning the final configuration dictionary.
        For new code, use get_complete_config_report() for full tracking information.
        
        Args:
            profile_name: Name of the profile to load or a profile configuration dictionary.
            cli_overrides: CLI parameter overrides.
            
        Returns:
            The merged configuration.
            
        Raises:
            FileNotFoundError: If the profile file doesn't exist.
            ValueError: If the configuration validation fails.
        """
        self.logger.debug(f"Merging configurations for profile: {profile_name} (compatibility mode)")
        
        # Handle direct profile config dictionary case
        if isinstance(profile_name, dict):
            # For dictionary input, we can't use the full tracking system
            # Fall back to the old merge logic for this case
            profile_config = profile_name
            task_type = cli_overrides.get("task_type") if cli_overrides else profile_config.get("task_type", "benchmark")
            
            if cli_overrides:
                merged_config = self.config_merger.merge_configs(profile_config, cli_overrides)
            else:
                merged_config = profile_config
            
            merged_config = self._apply_smart_defaults(merged_config)
            return merged_config
        else:
            # For string profile names, use the new tracking system
            report = self.get_complete_config_report(profile_name, cli_overrides)
            return report.final_config 