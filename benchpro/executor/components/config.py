"""
Configuration components for BenchPRO.

This module provides implementation of configuration components that are responsible
for loading and managing configuration data from YAML files.
"""

import os
import yaml
from typing import Dict, Any, Optional, List, Union

from benchpro.executor.components.interfaces import ConfigComponent, ConfigError
from benchpro.utils.logger import get_logger


class YamlConfigComponent(ConfigComponent):
    """
    Implementation of the ConfigComponent for YAML configuration files.
    
    This component loads, merges, and manages configuration data from YAML files.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the YamlConfigComponent.
        
        Args:
            config_path: Optional path to the configuration file.
        """
        self.logger = get_logger(__name__)
        self.config = {}
        self.config_path = config_path
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            The loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded.
        """
        self.logger.info(f"Loading configuration from: {config_path}")
        
        try:
            if not os.path.exists(config_path):
                raise ConfigError(f"Configuration file not found: {config_path}")
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                raise ConfigError(f"Configuration file does not contain a valid YAML dictionary: {config_path}")
            
            self.config = config
            self.config_path = config_path
            
            self.logger.debug(f"Configuration loaded successfully")
            
            return self.config
        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
    
    def merge_config(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge configuration overrides with the current configuration.
        
        Args:
            overrides: Dictionary of configuration overrides.
            
        Returns:
            The merged configuration.
            
        Raises:
            ConfigError: If the configuration cannot be merged.
        """
        self.logger.debug(f"Merging configuration with overrides")
        
        try:
            # Simple recursive merge function
            def merge_dicts(base, override):
                result = base.copy()
                for key, value in override.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = merge_dicts(result[key], value)
                    else:
                        result[key] = value
                return result
            
            self.config = merge_dicts(self.config, overrides)
            
            self.logger.debug("Configuration merged successfully")
            
            return self.config
        except Exception as e:
            error_msg = f"Failed to merge configuration: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            The current configuration.
            
        Raises:
            ConfigError: If the configuration is not available.
        """
        if not self.config:
            error_msg = "No configuration loaded"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
        
        return self.config
    
    def get_environment_section(self) -> Optional[Dict[str, Any]]:
        """
        Get the environment section from the configuration.
        
        This method provides direct access to the environment section,
        which contains module dependencies and environment variables.
        
        Returns:
            The environment section as a dictionary, or None if not present.
        """
        self.logger.debug("Retrieving environment section from configuration")
        
        if not self.config:
            self.logger.warning("No configuration loaded, cannot retrieve environment section")
            return None
            
        env_section = self.config.get("environment")
        
        if env_section is None:
            self.logger.debug("No environment section found in configuration")
        else:
            self.logger.debug(f"Found environment section: {env_section}")
            
        return env_section
    
    def get_module_dependencies(self) -> Optional[List[Dict[str, str]]]:
        """
        Get the module dependencies from the configuration.
        
        This method provides direct access to the module dependencies 
        specified in the environment section.
        
        Returns:
            List of module dictionaries, or None if not present.
            Each module dictionary typically contains 'name' and 'version' keys.
        """
        self.logger.debug("Retrieving module dependencies from configuration")
        
        env_section = self.get_environment_section()
        
        if not env_section:
            return None
            
        modules = env_section.get("modules")
        
        if modules is None:
            self.logger.debug("No modules found in environment section")
        else:
            self.logger.debug(f"Found {len(modules)} module dependencies: {modules}")
            
        return modules
    
    def validate_required_sections(self, required_sections: List[str], 
                                  optional_sections: Optional[List[str]] = None) -> bool:
        """
        Validate that the configuration contains all required sections.
        
        Args:
            required_sections: List of required section names.
            optional_sections: Optional list of optional section names.
            
        Returns:
            True if all required sections are present.
            
        Raises:
            ConfigError: If any required section is missing.
        """
        self.logger.debug(f"Validating required sections: {required_sections}")
        
        if not self.config:
            raise ConfigError("No configuration loaded, cannot validate sections")
            
        missing_sections = [section for section in required_sections if section not in self.config]
        
        if missing_sections:
            error_msg = f"Missing required configuration sections: {', '.join(missing_sections)}"
            self.logger.error(error_msg)
            raise ConfigError(error_msg)
            
        # Check for optional sections and log warnings for missing ones
        if optional_sections:
            missing_optional = [section for section in optional_sections if section not in self.config]
            if missing_optional:
                self.logger.warning(f"Missing optional configuration sections: {', '.join(missing_optional)}")
                
        self.logger.debug("All required sections are present")
        return True
    
    def get_section(self, section_name: str, default: Any = None) -> Any:
        """
        Get a specific section from the configuration.
        
        This is a generic method to access any top-level section by name.
        
        Args:
            section_name: Name of the section to retrieve.
            default: Default value to return if the section is not found.
            
        Returns:
            The requested section, or the default value if not found.
        """
        self.logger.debug(f"Retrieving section '{section_name}' from configuration")
        
        if not self.config:
            self.logger.warning(f"No configuration loaded, cannot retrieve section '{section_name}'")
            return default
            
        section = self.config.get(section_name, default)
        
        if section is default:
            self.logger.debug(f"Section '{section_name}' not found in configuration")
        
        return section 