"""
Configuration validator for BenchPRO.

This module provides functionality for validating configuration files against schemas.
"""

import os
import json
import yaml
import copy
from typing import Dict, Any, List, Optional, Union, Type
from pydantic import ValidationError

from benchpro.config.schema import ApplicationSchema, BenchmarkSchema
from benchpro.config.schema.global_config import GlobalConfigSchema
from benchpro.utils.logger import get_logger
from benchpro.config.interfaces import ConfigValidatorInterface


class ConfigValidator(ConfigValidatorInterface):
    """
    Validates configuration files against schemas.
    
    Responsibilities:
    - Validate configuration against schemas
    - Provide schema information
    - Generate example configurations
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing ConfigValidator")
        
        # Map task types to schemas
        self.schema_map = {
            "application": ApplicationSchema,
            "benchmark": BenchmarkSchema,
            "global": GlobalConfigSchema
        }
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a complete configuration dictionary against appropriate schemas.
        
        This method:
        1. Makes a copy of the configuration to avoid modifying the original
        2. Validates global settings
        3. Validates task-specific settings
        4. Merges the validated configurations
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated configuration dictionary.
            
        Raises:
            ValueError: If the configuration is invalid or the task type is unknown.
        """
        self.logger.info("Validating complete configuration")
        
        # Check if config is None
        if config is None:
            self.logger.error("Configuration is None")
            raise ValueError("Configuration is None")
        
        # Create a deep copy to avoid modifying the original
        config_copy = copy.deepcopy(config)
        
        # Validate global configuration
        self.logger.debug("Validating global configuration settings")
        validated_global = self.validate_global(config_copy)
        
        # Validate task-specific configuration
        self.logger.debug("Validating task-specific configuration settings")
        validated_task = self.validate_task(config_copy)
        
        # Merge validated configurations
        # Task-specific settings have higher precedence
        result = {**validated_global, **validated_task}
        
        self.logger.debug("Configuration validation completed successfully")
        return result
    
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
        self.logger.debug("Extracting global configuration fields")
        
        # Extract global fields from the configuration
        global_fields = {
            "logging": config.get("logging", {}),
            "paths": config.get("paths", {}),
            "workspace": {}
        }
        
        # Extract workspace global fields
        workspace = config.get("workspace", {})
        global_workspace = {}
        for field in ["base_input_dir", "base_output_dir", "keep_source_files", 
                     "keep_build_files", "keep_logs"]:
            if field in workspace:
                global_workspace[field] = workspace[field]
        
        global_fields["workspace"] = global_workspace
        
        # Validate global fields
        try:
            self.logger.debug("Validating global fields against GlobalConfigSchema")
            validated = GlobalConfigSchema(**global_fields)
            result = validated.model_dump()
            self.logger.debug("Global configuration validation successful")
            return result
        except ValidationError as e:
            # Format error messages with context
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(l) for l in error["loc"])
                msg = error["msg"]
                error_messages.append(f"Global config error at {loc}: {msg}")
            
            formatted_error = "\n".join(error_messages)
            self.logger.error(f"Global configuration validation failed:\n{formatted_error}")
            raise ValueError(f"Global configuration validation failed:\n{formatted_error}")
    
    def validate_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task-specific configuration settings.
        
        This method:
        1. Preprocesses the configuration to handle legacy fields
        2. Determines the task type
        3. Validates against the appropriate task schema
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated task configuration dictionary.
            
        Raises:
            ValueError: If the task configuration is invalid or the task type is unknown.
        """
        # Preprocess configuration to handle legacy fields and cleanup
        config_copy = self._preprocess_config(config)
        
        # Check if task_type is present
        if "task_type" not in config_copy:
            self.logger.error("Configuration missing 'task_type' field")
            raise ValueError("Configuration missing 'task_type' field")
        
        task_type = config_copy["task_type"]
        self.logger.debug(f"Task type identified: {task_type}")
        
        # Get the appropriate schema
        if task_type not in self.schema_map or task_type == "global":
            self.logger.error(f"Unknown or invalid task type: {task_type}")
            raise ValueError(f"Unknown or invalid task type: {task_type}")
        
        schema_class = self.schema_map[task_type]
        self.logger.debug(f"Using schema: {schema_class.__name__}")
        
        # Validate task-specific fields
        try:
            validated = schema_class(**config_copy)
            result = validated.model_dump()
            self.logger.debug(f"Task configuration validation successful for {task_type}")
            return result
        except ValidationError as e:
            # Format error messages with context
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(l) for l in error["loc"])
                msg = error["msg"]
                error_messages.append(f"Task config error at {loc}: {msg}")
            
            formatted_error = "\n".join(error_messages)
            self.logger.error(f"Task configuration validation failed for {task_type}:\n{formatted_error}")
            raise ValueError(f"Task configuration validation failed for {task_type}:\n{formatted_error}")
    
    def _preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess the configuration to handle legacy fields and cleanup.
        
        Args:
            config: Configuration dictionary to preprocess.
            
        Returns:
            Preprocessed configuration dictionary.
        """
        config_copy = copy.deepcopy(config)
        
        # Handle scheduler -> job conversion
        if "scheduler" in config_copy:
            self.logger.debug("Moving scheduler field to job field")
            if "job" not in config_copy:
                config_copy["job"] = {}
            config_copy["job"].update(config_copy.pop("scheduler"))
        
        # Remove fields that should not be part of task validation
        fields_to_remove = ["system"]
        for field in fields_to_remove:
            if field in config_copy:
                self.logger.debug(f"Removing {field} field from configuration")
                config_copy.pop(field)
        
        return config_copy
    
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
        self.logger.debug(f"Getting schema for task type: {task_type}")
        
        # Check if task_type is valid
        if task_type not in self.schema_map:
            self.logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")
        
        schema_class = self.schema_map[task_type]
        return schema_class.model_json_schema()
    
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
        self.logger.debug(f"Getting schema JSON for task type: {task_type}")
        
        schema = self.get_schema(task_type)
        return json.dumps(schema, indent=2)
    
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
        self.logger.debug(f"Generating example configuration for task type: {task_type}")
        
        # Check if task_type is valid
        if task_type not in self.schema_map:
            self.logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Create an example configuration based on the schema
        if task_type == "application":
            return self._generate_application_example()
        elif task_type == "benchmark":
            return self._generate_benchmark_example()
        else:
            self.logger.error(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")
    
    def _generate_application_example(self) -> Dict[str, Any]:
        """
        Generate an example application configuration.
        
        Returns:
            Example application configuration.
        """
        self.logger.debug("Generating example application configuration")
        
        return {
            "task_type": "application",
            "name": "example_app",
            "version": "1.0",
            "description": "Example application",
            "build": {
                "source": "example.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "example_app",
                "threads": 1
            },
            "environment": {
                "modules": ["gcc/9.3.0"],
                "variables": {
                    "OMP_NUM_THREADS": "1"
                }
            },
            "job": {
                "scheduler": "slurm",
                "queue": "compute",
                "account": "example_account",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "00:10:00"
            },
            "workspace": {
                "source_dir": "${ENV:HOME}/source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "application.j2"
        }
    
    def _generate_benchmark_example(self) -> Dict[str, Any]:
        """
        Generate an example benchmark configuration.
        
        Returns:
            Example benchmark configuration.
        """
        self.logger.debug("Generating example benchmark configuration")
        
        return {
            "task_type": "benchmark",
            "name": "example_benchmark",
            "version": "1.0",
            "description": "Example benchmark",
            "application": {
                "name": "example_app",
                "version": "1.0"
            },
            "parameters": {
                "input_file": "input.dat",
                "output_file": "output.dat",
                "iterations": 10
            },
            "environment": {
                "modules": ["gcc/9.3.0"],
                "variables": {
                    "OMP_NUM_THREADS": "1"
                }
            },
            "job": {
                "scheduler": "slurm",
                "queue": "compute",
                "account": "example_account",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "00:10:00"
            },
            "results": {
                "metrics": ["runtime", "throughput"],
                "files": ["output.dat", "stats.txt"]
            },
            "template": "benchmark.j2"
        }

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
        
        # In Pydantic v2, model_config replaces Config
        schema_dict = {}
        try:
            # Get the full schema
            schema_dict = schema_class.model_json_schema()
            
            # For application and benchmark schemas that have examples
            if "examples" in schema_dict:
                return schema_dict["examples"][0]
            elif "example" in schema_dict:
                return schema_dict["example"]
            
            # For schemas without examples, generate a basic example
            self.logger.debug(f"No example found in schema for {task_type}, generating a basic example")
            if task_type == "application":
                return self._generate_application_example()
            elif task_type == "benchmark":
                return self._generate_benchmark_example()
            else:
                return {}
        except Exception as e:
            self.logger.error(f"Error getting example for {task_type}: {e}")
            return {} 