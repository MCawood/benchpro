"""Template configuration functionality."""
from typing import Dict, Any, List, Optional, ClassVar, Set, Union
from dataclasses import dataclass
from pydantic import BaseModel, Field, model_validator, ValidationError
from .exceptions import TemplateValidationError, TemplateVersionError
from .version import Version

class DynamicModel(BaseModel):
    """Base model that supports dynamic field access."""
    _dynamic_fields: Dict[str, Any] = {}

    def __init__(self, **data):
        """Initialize model with dynamic fields."""
        super().__init__(**data)
        self._dynamic_fields = {}

    def __getattr__(self, name: str) -> Any:
        """Get attribute value."""
        try:
            return super().__getattr__(name)
        except AttributeError:
            if name in self._dynamic_fields:
                return self._dynamic_fields[name]
            raise

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute value."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            try:
                super().__setattr__(name, value)
            except ValueError:
                self._dynamic_fields[name] = value

    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access."""
        try:
            return getattr(self, key)
        except AttributeError:
            if key in self._dynamic_fields:
                return self._dynamic_fields[key]
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Support dictionary-style assignment."""
        try:
            setattr(self, key, value)
        except ValueError:
            self._dynamic_fields[key] = value

class BinaryConfig(DynamicModel):
    """Binary configuration."""
    directory: str = Field(..., description="Directory containing the binary")
    executable: str = Field(..., description="Name of the executable")

class BuildConfig(DynamicModel):
    """Build configuration."""
    language: str = Field(..., description="Programming language")
    compiler: str = Field(..., description="Compiler to use")
    binary: BinaryConfig = Field(..., description="Binary configuration")
    cmake_options: Optional[List[str]] = Field(default_factory=list, description="CMake build options")

class GitSource(BaseModel):
    """Git source configuration."""
    url: str = Field(..., description="Git repository URL")
    tag: str = Field(..., description="Git tag or branch")

class SourceConfig(BaseModel):
    """Source configuration supporting both files and git sources."""
    files: Optional[List[str]] = Field(None, description="List of source files")
    git: Optional[GitSource] = Field(None, description="Git repository configuration")

class TemplateConfig(BaseModel):
    """Template configuration."""

    VALID_TYPES: ClassVar[Set[str]] = {'application', 'benchmark'}

    name: str = Field(..., description="Template name")
    version: Version = Field(..., description="Template version")
    type: str = Field(..., description="Template type")
    build: BuildConfig = Field(..., description="Build configuration")
    source: Optional[SourceConfig] = Field(None, description="Source configuration")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    description: Optional[str] = Field(None, description="Template description")

    def __init__(self, config: Dict[str, Any]):
        """Initialize template configuration."""
        try:
            # Convert version string to Version object
            if isinstance(config.get('version'), str):
                try:
                    config['version'] = Version.parse(config['version'])
                except ValueError as e:
                    raise TemplateVersionError(str(e))
            
            # Validate type first if present
            if 'type' in config:
                self._validate_type(config['type'])
            
            # Convert build config to BuildConfig object
            if isinstance(config.get('build'), dict):
                try:
                    config['build'] = BuildConfig(**config['build'])
                except ValidationError as e:
                    raise TemplateValidationError(str(e))

            # Convert source config to SourceConfig object if present
            if isinstance(config.get('source'), dict):
                try:
                    config['source'] = SourceConfig(**config['source'])
                except ValidationError as e:
                    raise TemplateValidationError(str(e))

            # Validate required fields
            missing_fields = {'name', 'version', 'type', 'build'} - set(config.keys())
            if missing_fields:
                raise TemplateValidationError(f"Missing required field: {missing_fields.pop()}")

            super().__init__(**config)
            self._validate_variables(self.variables)
            if self.source:
                self._validate_source(self.source)
        except ValueError as e:
            raise TemplateValidationError(str(e))

    def _validate_type(self, type_str: str) -> None:
        """Validate template type."""
        if type_str not in self.VALID_TYPES:
            raise TemplateValidationError(f"Invalid template type: {type_str}")

    def _validate_variables(self, variables: Dict[str, Any]) -> None:
        """Validate template variables."""
        import re
        valid_name_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        
        for name in variables:
            if not valid_name_pattern.match(name):
                raise TemplateValidationError(f"Invalid variable name: {name}")

    def _validate_source(self, source: SourceConfig) -> None:
        """Validate source configuration."""
        # If source is provided, either files or git must be specified
        if source.files is None and source.git is None:
            raise TemplateValidationError("When source is provided, either source files or git repository must be specified")
        # If files list is provided, it cannot be empty
        if source.files is not None and not source.files:
            raise TemplateValidationError("No source files specified")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config = {
            'name': self.name,
            'version': str(self.version),
            'type': self.type,
            'build': self.build,
            'variables': self.variables
        }
        
        if self.source:
            config['source'] = self.source
            
        if self.description:
            config['description'] = self.description
            
        return config

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a template variable value."""
        if name not in self.variables and default is None:
            raise KeyError(f"Variable '{name}' not found")
        return self.variables.get(name, default)

    @model_validator(mode='before')
    @classmethod
    def validate_required_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all required fields are present."""
        required_fields = {'name', 'version', 'type', 'build', 'source'}
        missing = required_fields - set(values.keys())
        if missing:
            raise ValueError(f"Missing required field: {', '.join(missing)}")
        return values 