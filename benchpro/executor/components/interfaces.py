"""
Component interfaces for the BenchPRO execution system.

This module defines the interfaces for components used in the BenchPRO execution system.
Components are used to compose Task objects with different functionalities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Optional


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class ExecutionError(Exception):
    """Exception raised for execution errors."""
    pass


class ConfigComponent(ABC):
    """
    Interface for configuration components.
    
    Configuration components are responsible for loading, merging, and managing configuration data.
    """
    
    @abstractmethod
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
            
        Returns:
            The loaded configuration as a dictionary.
            
        Raises:
            ConfigError: If the configuration cannot be loaded.
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            The current configuration.
            
        Raises:
            ConfigError: If the configuration is not available.
        """
        pass
    
    @abstractmethod
    def get_environment_section(self) -> Optional[Dict[str, Any]]:
        """
        Get the environment section from the configuration.
        
        This method provides direct access to the environment section,
        which contains module dependencies and environment variables.
        
        Returns:
            The environment section as a dictionary, or None if not present.
        """
        pass
    
    @abstractmethod
    def get_module_dependencies(self) -> Optional[List[Dict[str, str]]]:
        """
        Get the module dependencies from the configuration.
        
        This method provides direct access to the module dependencies 
        specified in the environment section.
        
        Returns:
            List of module dictionaries, or None if not present.
            Each module dictionary typically contains 'name' and 'version' keys.
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class ValidationComponent(ABC):
    """
    Interface for validation components.
    
    Validation components are responsible for validating configuration data.
    """
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the configuration.
        
        Args:
            config: The configuration to validate.
            
        Returns:
            A tuple containing:
                - True if the configuration is valid, False otherwise.
                - A list of validation error messages (empty if no errors).
                
        Raises:
            ValidationError: If validation fails.
        """
        pass
        
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """
        Get the list of required fields for configuration validation.
        
        Returns:
            A list of required field names.
        """
        pass


# NOTE: The ScriptGenerationComponent has been moved to benchpro.templates.script_generators
# to avoid circular dependencies


class ExecutionComponent(ABC):
    """
    Interface for execution components.
    
    Execution components are responsible for executing scripts and managing job status.
    """
    
    @abstractmethod
    def execute(self, script_path: str, workspace: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Execute a script.
        
        Args:
            script_path: Path to the script to execute.
            workspace: Optional workspace dictionary with paths for logs and other directories.
            
        Returns:
            A tuple containing:
                - True if the script was executed successfully, False otherwise.
                - Job ID (if submitted, None otherwise).
                
        Raises:
            ExecutionError: If the script execution fails.
        """
        pass
    
    @abstractmethod
    def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.
        
        Args:
            job_id: The ID of the job to check.
            
        Returns:
            The status of the job.
            
        Raises:
            ExecutionError: If the status check fails.
        """
        pass
    
    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: The ID of the job to cancel.
            
        Returns:
            True if the job was cancelled successfully, False otherwise.
            
        Raises:
            ExecutionError: If the job cancellation fails.
        """
        pass 