"""
Configuration Merger for BenchPRO.

This module provides functionality for merging configurations with proper precedence
and comprehensive tracking of configuration origins and merge history.
"""

import copy
from typing import Dict, Any, List, Optional

from benchpro.utils.logger import get_logger
from benchpro.config.interfaces import ConfigMergerInterface
from benchpro.config.metadata import ConfigSource, ConfigReport, ConfigValue, MergeStep, flatten_config_for_tracking


class HierarchicalConfigMerger(ConfigMergerInterface):
    """
    Merges configurations with proper precedence and comprehensive tracking.
    
    This is the primary configuration merger that always tracks origins and
    generates detailed reports about the merge process.
    
    Responsibilities:
    - Merge configurations from different sources with metadata tracking
    - Handle precedence rules and maintain audit trail
    - Handle deep merging of nested dictionaries
    - Generate comprehensive configuration reports
    """
    
    def __init__(self):
        """Initialize the HierarchicalConfigMerger."""
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing HierarchicalConfigMerger with tracking support")
    
    def merge_sources(self, sources: List[ConfigSource], profile_name: str, 
                     cli_overrides: Optional[Dict[str, Any]] = None) -> ConfigReport:
        """
        Merge configuration sources with comprehensive tracking.
        
        This is the primary method for configuration merging, providing full
        tracking of origins and generating a complete configuration report.
        
        Args:
            sources: List of ConfigSource objects to merge, in precedence order.
            profile_name: Name of the profile being processed.
            cli_overrides: Optional CLI overrides to apply.
            
        Returns:
            ConfigReport with complete tracking information.
        """
        self.logger.debug(f"Merging {len(sources)} configuration sources with tracking")
        
        # Initialize tracking structures
        merge_history = []
        config_metadata = {}
        final_config = {}
        
        # Process each source in precedence order
        for source in sources:
            self._merge_source_with_tracking(
                source, final_config, config_metadata, merge_history
            )
        
        # Apply CLI overrides if provided
        if cli_overrides:
            cli_source = ConfigSource(
                config=cli_overrides,
                source="cli",
                precedence=1000  # Highest precedence
            )
            self._merge_source_with_tracking(
                cli_source, final_config, config_metadata, merge_history
            )
        
        # Create and return the configuration report
        return ConfigReport(
            final_config=final_config,
            config_metadata=config_metadata,
            merge_history=merge_history,
            profile_name=profile_name,
            cli_overrides=cli_overrides or {}
        )
    
    def _merge_source_with_tracking(self, source: ConfigSource, final_config: Dict[str, Any],
                                   config_metadata: Dict[str, ConfigValue], 
                                   merge_history: List[MergeStep]) -> None:
        """
        Merge a single configuration source while tracking changes.
        
        Args:
            source: ConfigSource to merge.
            final_config: Current final configuration (modified in-place).
            config_metadata: Current metadata tracking (modified in-place).
            merge_history: Current merge history (modified in-place).
        """
        # Flatten the source config for tracking
        flat_source = flatten_config_for_tracking(source.config)
        
        # Track what existed before this merge
        existing_params = set(flatten_config_for_tracking(final_config).keys())
        
        # Apply the merge
        changes = {}
        parameters_added = 0
        parameters_modified = 0
        
        for param_path, value in flat_source.items():
            # Store the change for history
            changes[param_path] = value
            
            # Track whether this is new or modified
            if param_path in existing_params:
                parameters_modified += 1
            else:
                parameters_added += 1
            
            # Update metadata tracking
            config_metadata[param_path] = ConfigValue(
                value=value,
                source=source.source,
                source_file=source.source_file,
                precedence=source.precedence
            )
        
        # Perform the actual deep merge on the nested structure
        self._deep_update(final_config, source.config)
        
        # Record this merge step
        step_name = self._get_step_name(source.source)
        merge_step = MergeStep(
            step_name=step_name,
            source=source.source,
            changes=changes,
            parameters_added=parameters_added,
            parameters_modified=parameters_modified
        )
        merge_history.append(merge_step)
    
    def _get_step_name(self, source: str) -> str:
        """
        Generate a human-readable step name for a source.
        
        Args:
            source: Source identifier.
            
        Returns:
            Human-readable step name.
        """
        if source == "default":
            return "Loading default configuration"
        elif source.startswith("system:"):
            system_name = source.split(":", 1)[1]
            return f"Loading system configuration: {system_name}"
        elif source.startswith("profile:"):
            profile_name = source.split(":", 1)[1]
            return f"Loading profile configuration: {profile_name}"
        elif source == "cli":
            return "Applying CLI overrides"
        elif source == "smart_defaults":
            return "Applying smart defaults"
        else:
            return f"Loading configuration from: {source}"
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations (compatibility method).
        
        This method provides backward compatibility but does not include tracking.
        For new code, use merge_sources() for full tracking capabilities.
        
        Args:
            base: Base configuration.
            override: Configuration to override the base.
            
        Returns:
            Merged configuration.
        """
        self.logger.debug("Merging two configurations (compatibility mode)")
        
        # Make a deep copy of the base to avoid modifying it
        result = copy.deepcopy(base)
        
        # Apply the override
        self._deep_update(result, override)
        
        return result
    
    def merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge a profile configuration with CLI overrides (compatibility method).
        
        This is a convenience method that calls merge().
        For new code, use merge_sources() for full tracking capabilities.
        
        Args:
            base: Base configuration (profile).
            override: Configuration to override the base (CLI overrides).
            
        Returns:
            Merged configuration.
        """
        return self.merge(base, override)
    
    def merge_all(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple configurations (compatibility method).
        
        This method provides backward compatibility but does not include tracking.
        For new code, use merge_sources() for full tracking capabilities.
        
        Args:
            configs: List of configurations to merge, in order of precedence (lowest to highest).
            
        Returns:
            Merged configuration.
        """
        self.logger.debug(f"Merging {len(configs)} configurations (compatibility mode)")
        
        if not configs:
            self.logger.warning("No configurations to merge, returning empty dict")
            return {}
        
        # Start with the first configuration
        result = copy.deepcopy(configs[0])
        
        # Apply each override in order
        for config in configs[1:]:
            self._deep_update(result, config)
        
        return result
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Update a nested dictionary with another nested dictionary.
        
        Args:
            target: Target dictionary to update.
            source: Source dictionary to update from.
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # If both values are dictionaries, recursively update
                self._deep_update(target[key], value)
            else:
                # Otherwise, just override the value
                target[key] = copy.deepcopy(value) 