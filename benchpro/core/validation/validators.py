"""Validation system for BenchPRO."""

import re
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    GetCoreSchemaHandler,
    ValidationError,
    field_validator,
)


def validate_directory(path: Path) -> Path:
    """Validate directory path."""
    if not path.exists():
        raise ValueError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path exists but is not a directory: {path}")
    return path


def validate_file(path: Path, extensions: Optional[List[str]] = None) -> Path:
    """Validate file path."""
    if not path.exists():
        raise ValueError(f"File does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Path exists but is not a file: {path}")
    if extensions and path.suffix not in extensions:
        raise ValueError(f"File must have one of these extensions: {', '.join(extensions)}")
    return path


def validate_memory_string(value: str) -> str:
    """Validate memory string."""
    pattern = re.compile(
        r"^(?P<number>\d+(\.\d+)?)\s*(?P<unit>[KMGT]B?|B)$",
        re.IGNORECASE,
    )
    if not pattern.match(value):
        raise ValueError(
            "Invalid memory string format. Must be number followed by unit (e.g., '4G', '128MB')"
        )
    return value


def validate_variables(value: Dict[str, Any]) -> Dict[str, Any]:
    """Validate variables dictionary."""
    name_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
    valid_types = (str, int, float, bool)
    
    for key, val in value.items():
        # Validate key
        if not name_pattern.match(key):
            raise ValueError(
                f"Invalid variable name: {key}. Must start with letter and contain only letters, numbers, and underscores"
            )
        
        # Validate value
        if not isinstance(val, valid_types):
            raise ValueError(
                f"Invalid variable value: {val}. Must be string, number, or boolean"
            )
    
    return value


# Type aliases with validation
DirectoryPath = Annotated[Path, BeforeValidator(validate_directory)]


class FileValidator:
    """File validator with configurable extensions."""
    
    def __init__(self, extensions: Optional[List[str]] = None):
        """Initialize validator.
        
        Args:
            extensions: List of allowed file extensions (e.g., [".txt", ".sh"])
        """
        self.extensions = extensions

    def __call__(self, path: Path) -> Path:
        """Validate file path."""
        return validate_file(path, self.extensions)


MemoryString = Annotated[str, BeforeValidator(validate_memory_string)]
Variables = Annotated[Dict[str, Any], BeforeValidator(validate_variables)]


# Example usage in models:
class TaskModel(BaseModel):
    """Example model showing how to use the validators."""
    
    working_dir: DirectoryPath
    template_file: Annotated[Path, BeforeValidator(FileValidator(extensions=[".sh", ".txt"]))]
    memory: MemoryString
    variables: Variables 