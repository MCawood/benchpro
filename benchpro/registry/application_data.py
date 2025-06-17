"""
Application Data structures for BenchPRO.

This module provides data classes for structured handling of application data
in BenchPRO, with validation methods and type hints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ModuleConfig:
    """
    Configuration for a module dependency.
    
    Attributes:
        name: Module name
        version: Optional module version
    """
    name: str
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation"""
        result = {"name": self.name}
        if self.version:
            result["version"] = self.version
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ModuleConfig':
        """Create from dictionary representation"""
        return cls(
            name=data["name"],
            version=data.get("version")
        )


@dataclass
class EnvironmentConfig:
    """
    Environment configuration for an application.
    
    Attributes:
        modules: List of module dependencies
        module_paths: List of paths to search for modules
        variables: Dictionary of environment variables
    """
    modules: List[ModuleConfig] = field(default_factory=list)
    module_paths: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {
            "module_paths": self.module_paths,
            "variables": self.variables
        }
        
        if self.modules:
            # Ensure modules are properly converted to dictionaries
            modules_list = []
            for module in self.modules:
                if hasattr(module, "to_dict"):
                    modules_list.append(module.to_dict())
                else:
                    # Fallback for any non-object modules
                    modules_list.append({"name": module.name, "version": module.version if hasattr(module, "version") else None})
            
            result["modules"] = modules_list
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentConfig':
        """Create from dictionary representation"""
        modules = []
        if "modules" in data:
            for module_data in data["modules"]:
                if isinstance(module_data, dict):
                    modules.append(ModuleConfig(
                        name=module_data["name"],
                        version=module_data.get("version")
                    ))
                elif isinstance(module_data, str):
                    modules.append(ModuleConfig(name=module_data))
        
        return cls(
            modules=modules,
            module_paths=data.get("module_paths", []),
            variables=data.get("variables", {})
        )


@dataclass
class ApplicationData:
    """
    Structured data for an application.
    
    Attributes:
        name: Application name
        version: Application version
        workspace_dir: Path to the workspace directory
        binary_path: Path to the application binary
        build_parameters: Dictionary of build parameters
        environment: Optional environment configuration
        metadata: Optional metadata dictionary
    """
    name: str
    version: str
    workspace_dir: str
    binary_path: str
    build_parameters: Dict[str, Any] = field(default_factory=dict)
    environment: Optional[EnvironmentConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApplicationData':
        """
        Create an ApplicationData instance from a dictionary.
        
        Args:
            data: Dictionary containing application data
            
        Returns:
            An ApplicationData instance
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ["name", "workspace_dir", "binary_path"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
        # Extract fields with defaults
        name = data["name"]
        version = data.get("version", "1.0")
        workspace_dir = data["workspace_dir"]
        binary_path = data["binary_path"]
        build_parameters = data.get("build_parameters", {})
        metadata = data.get("metadata", {})
        
        # Process environment if present
        environment = None
        if "environment" in data:
            environment = EnvironmentConfig.from_dict(data["environment"])
            
        return cls(
            name=name,
            version=version,
            workspace_dir=workspace_dir,
            binary_path=binary_path,
            build_parameters=build_parameters,
            environment=environment,
            metadata=metadata
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ApplicationData instance to a dictionary.
        
        Returns:
            Dictionary representation of the ApplicationData
        """
        result = {
            "name": self.name,
            "version": self.version,
            "workspace_dir": self.workspace_dir,
            "binary_path": self.binary_path,
            "build_parameters": self.build_parameters,
            "metadata": self.metadata
        }
        
        # Convert environment to dictionary if present
        if self.environment:
            # Use a more direct approach to ensure environment is included
            env_dict = self.environment.to_dict() if hasattr(self.environment, "to_dict") else {}
            
            # Ensure we have a valid dictionary for the environment
            if isinstance(env_dict, dict):
                result["environment"] = env_dict
            else:
                # Fallback to create a basic environment dictionary
                result["environment"] = {
                    "module_paths": getattr(self.environment, "module_paths", []),
                    "variables": getattr(self.environment, "variables", {})
                }
                
                # Add modules if they exist
                if hasattr(self.environment, "modules") and self.environment.modules:
                    modules_list = []
                    for module in self.environment.modules:
                        if hasattr(module, "to_dict"):
                            modules_list.append(module.to_dict())
                        else:
                            modules_list.append({"name": getattr(module, "name", "unknown")})
                    
                    result["environment"]["modules"] = modules_list
            
        return result
        
    def validate(self) -> List[str]:
        """
        Validate the application data.
        
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check required fields
        if not self.name:
            errors.append("Application name is required")
        if not self.workspace_dir:
            errors.append("Workspace directory is required")
        if not self.binary_path:
            errors.append("Binary path is required")
            
        return errors 