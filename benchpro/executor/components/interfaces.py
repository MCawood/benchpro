"""
Component interfaces for BenchPRO Task composition.

This module defines the abstract interfaces for components used in the
composition-based task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple


class ConfigComponent(ABC):
    """
    Interface for components that handle task configuration.
    
    ConfigComponent implementations are responsible for loading, validating, and
    providing access to task configuration.
    """
    
    @abstractmethod
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            Loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded or is invalid.
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Current configuration as a dictionary.
        """
        pass
    
    @abstractmethod
    def merge_config(self, override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge override configuration with the current configuration.
        
        Args:
            override_config: Configuration to merge with the current configuration.
            
        Returns:
            Merged configuration as a dictionary.
        """
        pass


class ValidationComponent(ABC):
    """
    Interface for components that validate task configuration.
    
    ValidationComponent implementations are responsible for ensuring that
    the task configuration meets the requirements for execution.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for this task type.
        
        Returns:
            List of required field names.
        """
        pass


class ScriptGenerationComponent(ABC):
    """
    Interface for components that generate execution scripts.
    
    ScriptGenerationComponent implementations are responsible for generating
    scripts from templates, with variables populated from the task configuration.
    """
    
    @abstractmethod
    def generate_script(self, template_path: str, variables: Dict[str, Any]) -> str:
        """
        Generate a script from a template.
        
        Args:
            template_path: Path to the template file.
            variables: Variables to use when rendering the template.
            
        Returns:
            Generated script content as a string.
            
        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        pass
    
    @abstractmethod
    def prepare_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare variables for template rendering.
        
        Args:
            config: Task configuration.
            
        Returns:
            Dictionary of variables for template rendering.
        """
        pass


class ExecutionComponent(ABC):
    """
    Interface for components that execute scripts.
    
    ExecutionComponent implementations are responsible for executing scripts,
    monitoring their execution, and retrieving results.
    """
    
    @abstractmethod
    def execute(self, script_path: str) -> Tuple[bool, Optional[str]]:
        """
        Execute a script.
        
        Args:
            script_path: Path to the script to execute.
            
        Returns:
            A tuple containing:
                - True if the script was successfully submitted, False otherwise.
                - Job ID or process ID (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the script cannot be executed.
        """
        pass
    
    @abstractmethod
    def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.
        
        Args:
            job_id: ID of the job to check.
            
        Returns:
            Status of the job as a string (e.g., "RUNNING", "COMPLETED", "FAILED").
            
        Raises:
            StatusCheckError: If the status cannot be retrieved.
        """
        pass
    
    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if the job was successfully cancelled, False otherwise.
            
        Raises:
            CancellationError: If the job cannot be cancelled.
        """
        pass


# Common exceptions for components

class ComponentError(Exception):
    """Base class for all component-related exceptions."""
    pass


class ConfigError(ComponentError):
    """Exception raised when a configuration error occurs."""
    pass


class ValidationError(ComponentError):
    """Exception raised when a validation error occurs."""
    pass


class TemplateError(ComponentError):
    """Exception raised when a template error occurs."""
    pass


class ExecutionError(ComponentError):
    """Exception raised when an execution error occurs."""
    pass


class StatusCheckError(ComponentError):
    """Exception raised when a status check error occurs."""
    pass


class CancellationError(ComponentError):
    """Exception raised when a job cancellation error occurs."""
    pass 