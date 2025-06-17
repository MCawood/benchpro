"""
Validation Components for BenchPRO Task composition.

This module defines components for validating task configuration.
"""

from typing import Dict, Any, Optional, List, Tuple
import jsonschema

from benchpro.executor.components.interfaces import ValidationComponent, ValidationError
from benchpro.config.validator import ConfigValidator
from benchpro.utils.logger import get_logger


class BaseValidationComponent(ValidationComponent):
    """Base implementation of ValidationComponent with common functionality."""
    
    def __init__(self, config_validator: Optional[ConfigValidator] = None):
        """
        Initialize the validation component.
        
        Args:
            config_validator: Optional ConfigValidator instance. If None, a new one is created.
        """
        self.logger = get_logger(__name__)
        self.config_validator = config_validator or ConfigValidator()
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - List of validation error messages (if any).
        """
        self.logger.debug("Validating configuration")
        
        # Check for required fields
        required_fields = self.get_required_fields()
        missing_fields = []
        
        for field in required_fields:
            if field not in config:
                missing_fields.append(field)
        
        if missing_fields:
            error_messages = [f"Missing required field: {field}" for field in missing_fields]
            self.logger.error(f"Validation failed: {', '.join(error_messages)}")
            return False, error_messages
        
        # Validate specific fields
        return self._validate_fields(config)
    
    def _validate_fields(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate specific fields in the configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - List of validation error messages (if any).
        """
        # Base implementation just returns valid
        return True, None
    
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for this task type.
        
        Returns:
            List of required field names.
        """
        # Common required fields for all task types
        return ["name", "version", "task_type"]


class ApplicationValidationComponent(BaseValidationComponent):
    """Validation component for application tasks."""
    
    def __init__(self, config_validator: Optional[ConfigValidator] = None):
        """Initialize the application validation component."""
        super().__init__(config_validator)
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing ApplicationValidationComponent")
    
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for application tasks.
        
        Returns:
            List of required field names.
        """
        # Start with common required fields
        fields = super().get_required_fields()
        
        # Add application-specific required fields
        application_fields = ["build"]
        
        return fields + application_fields
    
    def _validate_fields(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate application-specific fields in the configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - List of validation error messages (if any).
        """
        errors = []
        
        # Validate task_type
        if config.get("task_type") != "application":
            errors.append(f"Invalid task_type: expected 'application', got '{config.get('task_type')}'")
        
        # Validate build section
        build_config = config.get("build", {})
        
        # Validate required build fields
        required_build_fields = ["source"]
        for field in required_build_fields:
            if field not in build_config:
                errors.append(f"Missing required build field: {field}")
        
        # Check if there are any errors
        if errors:
            self.logger.error(f"Application validation failed: {', '.join(errors)}")
            return False, errors
        
        return True, None


class BenchmarkValidationComponent(BaseValidationComponent):
    """Validation component for benchmark tasks."""
    
    def __init__(self, config_validator: Optional[ConfigValidator] = None):
        """Initialize the benchmark validation component."""
        super().__init__(config_validator)
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing BenchmarkValidationComponent")
    
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for benchmark tasks.
        
        Returns:
            List of required field names.
        """
        # Start with common required fields
        fields = super().get_required_fields()
        
        # Add benchmark-specific required fields
        benchmark_fields = ["run"]
        
        return fields + benchmark_fields
    
    def _validate_fields(self, config: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate benchmark-specific fields in the configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - List of validation error messages (if any).
        """
        errors = []
        
        # Validate task_type
        if config.get("task_type") != "benchmark":
            errors.append(f"Invalid task_type: expected 'benchmark', got '{config.get('task_type')}'")
        
        # Validate run section
        run_config = config.get("run", {})
        
        # Validate required run fields
        required_run_fields = ["executable"]
        for field in required_run_fields:
            if field not in run_config:
                errors.append(f"Missing required run field: {field}")
        
        # Check if there are any errors
        if errors:
            self.logger.error(f"Benchmark validation failed: {', '.join(errors)}")
            return False, errors
        
        return True, None


class SchemaValidationComponent(ValidationComponent):
    """
    Implementation of the ValidationComponent using JSON Schema validation.
    
    This component validates configuration data against a JSON schema.
    """
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize the SchemaValidationComponent.
        
        Args:
            schema: JSON schema to validate against.
        """
        self.logger = get_logger(__name__)
        self.schema = schema
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the configuration against the schema.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - A list of validation error messages (empty if no errors).
                
        Raises:
            ValidationError: If validation fails unexpectedly.
        """
        self.logger.debug("Validating configuration against schema")
        
        # If we don't have a schema, assume valid
        if not self.schema:
            self.logger.warning("No schema provided for validation, assuming valid")
            return True, []
        
        try:
            # Use jsonschema to validate
            jsonschema.validate(instance=config, schema=self.schema)
            
            self.logger.debug("Configuration validation successful")
            
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            # Construct a user-friendly error message
            error_path = ".".join(str(p) for p in e.path) if e.path else "root"
            error_message = f"Validation error at {error_path}: {e.message}"
            
            self.logger.error(error_message)
            
            return False, [error_message]
        except Exception as e:
            error_msg = f"Unexpected error during validation: {str(e)}"
            self.logger.error(error_msg)
            raise ValidationError(error_msg)
            
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields from the JSON schema.
        
        This method extracts required fields from the JSON schema definition.
        
        Returns:
            A list of required field names at the root level.
        """
        if not self.schema:
            self.logger.warning("No schema available for extracting required fields")
            return []
            
        required_fields = []
        
        # Get required fields from the schema's "required" property at root level
        if "required" in self.schema and isinstance(self.schema["required"], list):
            required_fields.extend(self.schema["required"])
            
        # Properties can also be marked as required individually
        if "properties" in self.schema and isinstance(self.schema["properties"], dict):
            for prop_name, prop_schema in self.schema["properties"].items():
                if isinstance(prop_schema, dict) and prop_schema.get("required") is True:
                    required_fields.append(prop_name)
                    
        self.logger.debug(f"Extracted {len(required_fields)} required fields from schema")
        return required_fields 