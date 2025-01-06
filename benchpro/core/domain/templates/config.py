"""Template configuration functionality."""
from typing import Dict, Any, List, Optional, ClassVar, Set
from dataclasses import dataclass
from pydantic import BaseModel, Field, model_validator, ValidationError
from .exceptions import TemplateValidationError, TemplateVersionError

@dataclass
class Version:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    prerelease: str = None
    build: str = None

    def __str__(self) -> str:
        """Convert version to string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __eq__(self, other: Any) -> bool:
        """Compare version with another version or string."""
        if isinstance(other, str):
            try:
                other = Version.parse(other)
            except TemplateVersionError:
                return False
        if not isinstance(other, Version):
            return False
        return (self.major == other.major and 
                self.minor == other.minor and 
                self.patch == other.patch and 
                self.prerelease == other.prerelease and 
                self.build == other.build)

    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse version string into Version object."""
        try:
            # Split version into parts
            version_parts = version_str.split('-', 1)
            version_nums = version_parts[0].split('.')
            
            if len(version_nums) != 3:
                raise TemplateVersionError(f"Invalid version format: {version_str}")
            
            major = int(version_nums[0])
            minor = int(version_nums[1])
            patch = int(version_nums[2])
            
            # Handle prerelease and build metadata
            prerelease = None
            build = None
            if len(version_parts) > 1:
                prerelease_build = version_parts[1].split('+', 1)
                prerelease = prerelease_build[0] if prerelease_build[0] else None
                if len(prerelease_build) > 1:
                    build = prerelease_build[1] if prerelease_build[1] else None
            
            return cls(major, minor, patch, prerelease, build)
        except (ValueError, IndexError) as e:
            raise TemplateVersionError(f"Invalid version format: {version_str}") from e

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

class TemplateConfig(BaseModel):
    """Template configuration."""

    VALID_TYPES: ClassVar[Set[str]] = {'application', 'benchmark'}

    name: str = Field(..., description="Template name")
    version: Version = Field(..., description="Template version")
    type: str = Field(..., description="Template type")
    build: BuildConfig = Field(..., description="Build configuration")
    source: Dict[str, List[str]] = Field(default_factory=dict, description="Source files")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    description: Optional[str] = Field(None, description="Template description")

    def __init__(self, config: Dict[str, Any]):
        """Initialize template configuration."""
        try:
            # Convert version string to Version object
            if isinstance(config.get('version'), str):
                config['version'] = Version.parse(config['version'])
            
            # Convert build config to BuildConfig object
            if isinstance(config.get('build'), dict):
                try:
                    config['build'] = BuildConfig(**config['build'])
                except ValidationError as e:
                    raise TemplateValidationError(str(e))

            # Validate required fields first
            missing_fields = {'name', 'version', 'type', 'build'} - set(config.keys())
            if missing_fields:
                raise TemplateValidationError(f"Missing required field: {missing_fields.pop()}")

            super().__init__(**config)
            self._validate_type(self.type)
            self._validate_variables(self.variables)
            self._validate_source_files(self.source)
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

    def _validate_source_files(self, source: Dict[str, Any]) -> None:
        """Validate source files configuration."""
        if 'files' in source and not source['files']:
            raise TemplateValidationError("No source files specified")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config = {
            'name': self.name,
            'version': str(self.version),
            'type': self.type,
            'build': self.build,
            'source': self.source,
            'variables': self.variables
        }
        
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
        required_fields = {'name', 'version', 'type', 'build'}
        missing = required_fields - set(values.keys())
        if missing:
            raise ValueError(f"Missing required field: {', '.join(missing)}")
        return values 