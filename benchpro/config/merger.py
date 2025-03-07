"""
Configuration Merger for BenchPRO.

This module provides functionality for merging configurations with proper precedence.
"""

import copy
from typing import Dict, Any, List, Optional

from benchpro.utils.logger import get_logger
from benchpro.config.interfaces import ConfigMergerInterface


class HierarchicalConfigMerger(ConfigMergerInterface):
    """
    Merges configurations with proper precedence.
    
    Responsibilities:
    - Merge configurations from different sources
    - Handle precedence rules
    - Handle deep merging of nested dictionaries
    """
    
    def __init__(self):
        """Initialize the HierarchicalConfigMerger."""
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing HierarchicalConfigMerger")
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations.
        
        Args:
            base: Base configuration.
            override: Configuration to override the base.
            
        Returns:
            Merged configuration.
        """
        self.logger.debug("Merging two configurations")
        
        # Make a deep copy of the base to avoid modifying it
        result = copy.deepcopy(base)
        
        # Apply the override
        self._deep_update(result, override)
        
        return result
    
    def merge_all(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple configurations.
        
        Args:
            configs: List of configurations to merge, in order of precedence (lowest to highest).
            
        Returns:
            Merged configuration.
        """
        self.logger.debug(f"Merging {len(configs)} configurations")
        
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