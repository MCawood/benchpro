"""
Configuration validator for BenchPRO.

This module provides functionality for validating configuration files against schemas.
"""

import os
import yaml
from typing import Dict, Any, List, Optional, Union, Type
from pydantic import ValidationError

from benchpro.config.schema import ApplicationSchema, BenchmarkSchema
from benchpro.utils.logger import get_logger


class ConfigValidator:
    """
    Validates configuration files against schemas.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ConfigValidator")
        
        # Map task types to schemas
        self.schema_map = {
            "application": ApplicationSchema,
            "benchmark": BenchmarkSchema
        }
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a configuration dictionary against the appropriate schema.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid or the task type is unknown.
        """
        self.logger.info("Validating configuration")
        
        # Check if config is None
        if config is None:
            self.logger.error("Configuration is None")
            raise ValueError("Configuration is None")
        
        # Check if task_type is present
        if "task_type" not in config:
            self.logger.error("Configuration missing 'task_type' field")
            raise ValueError("Configuration missing 'task_type' field")
        
        task_type = config["task_type"]
        self.logger.debug(f"Task type: {task_type}")
        
        # Get the appropriate schema
        if task_type not in self.schema_map:
            self.logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")
        
        schema_class = self.schema_map[task_type]
        self.logger.debug(f"Using schema: {schema_class.__name__}")
        
        # Validate the configuration
        try:
            validated_config = schema_class(**config)
            self.logger.info("Configuration validated successfully")
            return validated_config.dict()
        except ValidationError as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            raise ValueError(f"Configuration validation failed: {str(e)}")
    
    def validate_file(self, config_file: str) -> Dict[str, Any]:
        """
        Validate a configuration file against the appropriate schema.
        
        Args:
            config_file: Path to the configuration file.
            
        Returns:
            Validated configuration dictionary.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the configuration is invalid or the task type is unknown.
        """
        self.logger.info(f"Validating configuration file: {config_file}")
        
        # Check if the file exists
        if not os.path.exists(config_file):
            self.logger.error(f"Configuration file not found: {config_file}")
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Load the configuration
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            
            self.logger.debug(f"Loaded configuration from {config_file}")
            
            # Validate the configuration
            return self.validate(config)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML file {config_file}: {str(e)}")
            raise ValueError(f"Error parsing YAML file {config_file}: {str(e)}")
    
    def get_schema_for_task_type(self, task_type: str) -> Type:
        """
        Get the schema class for a task type.
        
        Args:
            task_type: Task type to get the schema for.
            
        Returns:
            Schema class for the task type.
            
        Raises:
            ValueError: If the task type is unknown.
        """
        if task_type not in self.schema_map:
            self.logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")
        
        return self.schema_map[task_type]
    
    def get_schema_json(self, task_type: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a task type.
        
        Args:
            task_type: Task type to get the schema for.
            
        Returns:
            JSON schema for the task type.
            
        Raises:
            ValueError: If the task type is unknown.
        """
        schema_class = self.get_schema_for_task_type(task_type)
        return schema_class.schema()
    
    def get_example_config(self, task_type: str) -> Dict[str, Any]:
        """
        Get an example configuration for the given task type.
        
        Args:
            task_type: Type of task (application, benchmark)
            
        Returns:
            Example configuration
            
        Raises:
            ValueError: If the task type is unknown.
        """
        schema_class = self.get_schema_for_task_type(task_type)
        # Try json_schema_extra first (Pydantic V2), fall back to schema_extra for backward compatibility
        if hasattr(schema_class.Config, "json_schema_extra"):
            return schema_class.Config.json_schema_extra["example"]
        else:
            return schema_class.Config.schema_extra["example"] 