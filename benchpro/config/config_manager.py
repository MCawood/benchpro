"""
Configuration Manager for BenchPRO.

This module handles loading, merging, and validating YAML configuration files.
"""

import os
from typing import Dict, Any, List, Optional
import yaml


class ConfigManager:
    """
    Manages configuration loading, merging, and validation for BenchPRO.
    
    This class handles:
    - Loading YAML configuration files (global defaults, system context, profiles)
    - Merging configurations with proper precedence
    - Validating configuration consistency
    """
    
    def __init__(self, config_dir: Optional[str] = None, profile_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing internal configuration files (default and system).
            profile_dir: Directory containing user-editable profile configuration files.
        """
        # Internal config files (default and system) should remain in benchpro/config
        if config_dir is None:
            self.config_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.config_dir = config_dir
            
        # User-editable profile configs should be in examples/input/config
        if profile_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.profile_dir = os.path.join(project_root, "examples", "input", "config")
        else:
            self.profile_dir = profile_dir
            
        self.default_config = {}
        self.system_config = {}
        self.profile_configs = {}
        
    def load_default_config(self) -> Dict[str, Any]:
        """
        Load the global default configuration.
        
        Returns:
            Dict containing the default configuration.
        """
        default_path = os.path.join(self.config_dir, "default.yaml")
        if os.path.exists(default_path):
            with open(default_path, 'r') as f:
                self.default_config = yaml.safe_load(f) or {}
        else:
            self.default_config = {}
        
        return self.default_config
    
    def load_system_config(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the system-specific configuration.
        
        Args:
            system_name: Name of the system to load. If None, attempts to detect the current system.
            
        Returns:
            Dict containing the system configuration.
        """
        if system_name is None:
            # TODO: Implement system detection logic
            system_name = "default"
            
        system_path = os.path.join(self.config_dir, f"system_{system_name}.yaml")
            
        if os.path.exists(system_path):
            with open(system_path, 'r') as f:
                self.system_config = yaml.safe_load(f) or {}
        else:
            self.system_config = {}
            
        return self.system_config
    
    def load_profile_config(self, profile_name: str) -> Dict[str, Any]:
        """
        Load a specific profile configuration.
        
        Args:
            profile_name: Name of the profile to load.
            
        Returns:
            Dict containing the profile configuration.
            
        Raises:
            FileNotFoundError: If the profile configuration file doesn't exist.
        """
        # First try with the profile_ prefix (for backward compatibility)
        profile_path = os.path.join(self.profile_dir, f"profile_{profile_name}.yaml")
        
        # If not found, try without the prefix
        if not os.path.exists(profile_path):
            profile_path = os.path.join(self.profile_dir, f"{profile_name}.yaml")
            
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile configuration not found: {profile_path}")
            
        with open(profile_path, 'r') as f:
            profile_config = yaml.safe_load(f) or {}
            
        self.profile_configs[profile_name] = profile_config
        return profile_config
    
    def merge_configs(self, profile_name: str, cli_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Merge configurations with proper precedence:
        CLI overrides > profile > system > defaults
        
        Args:
            profile_name: Name of the profile to use.
            cli_overrides: Optional dictionary of CLI parameter overrides.
            
        Returns:
            Dict containing the merged configuration.
        """
        # Ensure all configs are loaded
        if not self.default_config:
            self.load_default_config()
            
        if not self.system_config:
            self.load_system_config()
            
        if profile_name not in self.profile_configs:
            self.load_profile_config(profile_name)
            
        # Start with defaults
        merged_config = self.default_config.copy()
        
        # Apply system config
        self._deep_update(merged_config, self.system_config)
        
        # Apply profile config
        self._deep_update(merged_config, self.profile_configs[profile_name])
        
        # Apply CLI overrides
        if cli_overrides:
            self._deep_update(merged_config, cli_overrides)
            
        return merged_config
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate the configuration for consistency and required values.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            List of validation error messages. Empty list if validation passes.
        """
        errors = []
        
        # Check for required top-level keys
        required_keys = ["job", "scheduler"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required configuration section: {key}")
                
        # Check job section if it exists
        if "job" in config:
            job_config = config["job"]
            if not isinstance(job_config, dict):
                errors.append("'job' configuration must be a dictionary")
            else:
                # Check for required job keys
                job_required_keys = ["name"]
                for key in job_required_keys:
                    if key not in job_config:
                        errors.append(f"Missing required job configuration: {key}")
        
        # Check scheduler section if it exists
        if "scheduler" in config:
            scheduler_config = config["scheduler"]
            if not isinstance(scheduler_config, dict):
                errors.append("'scheduler' configuration must be a dictionary")
            else:
                # Check for required scheduler keys
                scheduler_required_keys = ["type"]
                for key in scheduler_required_keys:
                    if key not in scheduler_config:
                        errors.append(f"Missing required scheduler configuration: {key}")
                        
        return errors
    
    @staticmethod
    def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively update a nested dictionary.
        
        Args:
            target: The dictionary to update.
            source: The dictionary with values to apply.
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                ConfigManager._deep_update(target[key], value)
            else:
                # Replace or add values
                target[key] = value 