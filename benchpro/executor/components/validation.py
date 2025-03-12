"""
Validation Components for BenchPRO Task composition.

This module defines components for validating task configuration.
"""

from typing import Dict, Any, Optional, List, Tuple

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
        required_run_fields = ["application"]
        for field in required_run_fields:
            if field not in run_config:
                errors.append(f"Missing required run field: {field}")
        
        # Check if there are any errors
        if errors:
            self.logger.error(f"Benchmark validation failed: {', '.join(errors)}")
            return False, errors
        
        return True, None 