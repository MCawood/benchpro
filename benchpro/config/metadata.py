"""
Configuration Metadata and Tracking Data Structures for BenchPRO.

This module defines the core data structures used for tracking configuration
origins, merge history, and generating comprehensive parameter reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import json
import yaml


@dataclass
class ConfigSource:
    """
    Represents a configuration source with metadata.
    
    This class wraps configuration data with information about where it came from,
    enabling tracking throughout the merge process.
    """
    config: Dict[str, Any]
    source: str  # e.g., "default", "system:slurm", "profile:hello_world", "cli", "smart_defaults"
    source_file: Optional[str] = None  # File path for file-based sources
    precedence: int = 0  # Numeric precedence for sorting (higher = more important)
    
    def __post_init__(self):
        """Validate and normalize the source data."""
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dictionary")
        if not self.source:
            raise ValueError("Source must be specified")


@dataclass  
class ConfigValue:
    """
    Represents a single configuration value with origin metadata.
    
    This tracks exactly where each final configuration parameter came from,
    including file paths and line numbers when available.
    """
    value: Any
    source: str  # Source identifier
    source_file: Optional[str] = None  # File path for file-based sources
    line_number: Optional[int] = None  # Line number for YAML sources
    precedence: int = 0  # Numeric precedence
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate the metadata."""
        if not self.source:
            raise ValueError("Source must be specified")


@dataclass
class MergeStep:
    """
    Represents a single step in the configuration merge process.
    
    This provides a detailed audit trail of how the final configuration
    was assembled from multiple sources.
    """
    step_name: str  # e.g., "Loading default config", "Applying CLI overrides"
    source: str  # Source identifier
    changes: Dict[str, Any]  # Configuration changes in this step
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parameters_added: int = 0  # Number of new parameters
    parameters_modified: int = 0  # Number of existing parameters changed
    
    def __post_init__(self):
        """Calculate parameter statistics if not provided."""
        if not self.step_name:
            raise ValueError("Step name must be specified")
        if not self.source:
            raise ValueError("Source must be specified")


@dataclass
class ConfigReport:
    """
    Complete configuration report with metadata and audit trail.
    
    This is the main data structure returned by the configuration system,
    containing both the final merged configuration and complete tracking
    information about how it was assembled.
    """
    final_config: Dict[str, Any]  # Final merged configuration
    config_metadata: Dict[str, ConfigValue]  # Metadata for each config path
    merge_history: List[MergeStep]  # Step-by-step merge history
    profile_name: str
    cli_overrides: Dict[str, Any] = field(default_factory=dict)
    generation_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate the report structure."""
        if not isinstance(self.final_config, dict):
            raise ValueError("Final config must be a dictionary")
        if not isinstance(self.config_metadata, dict):
            raise ValueError("Config metadata must be a dictionary")
        if not isinstance(self.merge_history, list):
            raise ValueError("Merge history must be a list")
        if not self.profile_name:
            raise ValueError("Profile name must be specified")
    
    def get_source_summary(self) -> Dict[str, int]:
        """
        Get a summary of configuration sources.
        
        Returns:
            Dictionary mapping source names to parameter counts.
        """
        source_counts = {}
        for config_value in self.config_metadata.values():
            source = config_value.source
            source_counts[source] = source_counts.get(source, 0) + 1
        return source_counts
    
    def get_parameters_by_source(self, source: str) -> Dict[str, Any]:
        """
        Get all parameters that came from a specific source.
        
        Args:
            source: Source identifier to filter by.
            
        Returns:
            Dictionary of parameters from the specified source.
        """
        result = {}
        for param_path, config_value in self.config_metadata.items():
            if config_value.source == source:
                result[param_path] = config_value.value
        return result
    
    def get_overridden_parameters(self) -> Dict[str, List[str]]:
        """
        Get parameters that were overridden by higher precedence sources.
        
        Returns:
            Dictionary mapping parameter paths to lists of sources that provided values.
        """
        # This would require tracking all intermediate values, not just final ones
        # For now, return empty dict - can be enhanced later
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the report to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the report.
        """
        return {
            "profile_name": self.profile_name,
            "generation_time": self.generation_time,
            "final_config": self.final_config,
            "cli_overrides": self.cli_overrides,
            "parameter_metadata": {
                path: {
                    "value": cv.value,
                    "source": cv.source,
                    "source_file": cv.source_file,
                    "line_number": cv.line_number,
                    "precedence": cv.precedence,
                    "applied_at": cv.applied_at
                }
                for path, cv in self.config_metadata.items()
            },
            "merge_history": [
                {
                    "step_name": step.step_name,
                    "source": step.source,
                    "timestamp": step.timestamp,
                    "parameters_added": step.parameters_added,
                    "parameters_modified": step.parameters_modified,
                    "changes": step.changes
                }
                for step in self.merge_history
            ],
            "source_summary": self.get_source_summary()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert the report to JSON format.
        
        Args:
            indent: Number of spaces for indentation.
            
        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def to_yaml(self) -> str:
        """
        Convert the report to YAML format.
        
        Returns:
            YAML string representation.
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


def flatten_config_for_tracking(config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    Flatten a nested configuration dictionary for tracking purposes.
    
    Converts nested dictionaries to dot-notation paths for easier tracking.
    
    Args:
        config: Configuration dictionary to flatten.
        prefix: Prefix for the current level (used in recursion).
        
    Returns:
        Flattened dictionary with dot-notation keys.
        
    Example:
        {"job": {"nodes": 4}} -> {"job.nodes": 4}
    """
    result = {}
    
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            result.update(flatten_config_for_tracking(value, full_key))
        else:
            # Store the value with its full path
            result[full_key] = value
    
    return result


def unflatten_config_from_tracking(flat_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unflatten a configuration dictionary from dot-notation back to nested structure.
    
    Args:
        flat_config: Flattened configuration with dot-notation keys.
        
    Returns:
        Nested dictionary structure.
        
    Example:
        {"job.nodes": 4} -> {"job": {"nodes": 4}}
    """
    result = {}
    
    for key, value in flat_config.items():
        # Split the key by dots
        parts = key.split('.')
        current = result
        
        # Navigate/create the nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
    
    return result 