"""Unit tests for validation system."""

from pathlib import Path
from typing import Annotated, Any, Dict

import pytest
from pydantic import BaseModel, ValidationError, BeforeValidator

from benchpro.core.validation.validators import (
    DirectoryPath,
    FileValidator,
    MemoryString,
    Variables,
)


def test_directory_validator(tmp_path: Path):
    """Test directory validation."""
    class Model(BaseModel):
        directory: DirectoryPath
    
    # Test with existing directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    model = Model(directory=test_dir)
    assert model.directory == test_dir
    
    # Test with non-existent directory
    with pytest.raises(ValidationError, match="Directory does not exist"):
        Model(directory=tmp_path / "nonexistent")
    
    # Test with file instead of directory
    test_file = tmp_path / "test.txt"
    test_file.touch()
    with pytest.raises(ValidationError, match="Path is not a directory"):
        Model(directory=test_file)


def test_file_validator(tmp_path: Path):
    """Test file validation."""
    class Model(BaseModel):
        file: Annotated[Path, BeforeValidator(FileValidator(extensions=[".txt", ".sh"]))]
    
    # Test with valid file
    test_file = tmp_path / "test.txt"
    test_file.touch()
    model = Model(file=test_file)
    assert model.file == test_file
    
    # Test with non-existent file
    with pytest.raises(ValidationError, match="File does not exist"):
        Model(file=tmp_path / "nonexistent.txt")
    
    # Test with directory instead of file
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    with pytest.raises(ValidationError, match="Path exists but is not a file"):
        Model(file=test_dir)
    
    # Test with invalid extension
    invalid_file = tmp_path / "test.invalid"
    invalid_file.touch()
    with pytest.raises(ValidationError, match="File must have one of these extensions"):
        Model(file=invalid_file)


def test_memory_string_validator():
    """Test memory string validation."""
    class Model(BaseModel):
        memory: MemoryString
    
    # Test valid memory strings
    valid_strings = ["4G", "128M", "1T", "512MB", "2.5GB", "0.5TB"]
    for memory in valid_strings:
        model = Model(memory=memory)
        assert model.memory == memory
    
    # Test invalid memory strings
    invalid_strings = [
        "4X",  # Invalid unit
        "GB",  # Missing number
        "-1G",  # Negative number
        "1.2.3G",  # Invalid number format
        "very_large",  # Not a memory string
        "",  # Empty string
    ]
    for memory in invalid_strings:
        with pytest.raises(ValidationError, match="Invalid memory string format"):
            Model(memory=memory)


def test_variables_validator():
    """Test variables validation."""
    class Model(BaseModel):
        variables: Variables
    
    # Test valid variables
    valid_vars = {
        "cores": 4,
        "memory": "8G",
        "name": "test",
        "enabled": True,
        "priority": 1.5,
    }
    model = Model(variables=valid_vars)
    assert model.variables == valid_vars
    
    # Test invalid variable names
    invalid_names = {
        "": "empty",  # Empty key
        "invalid space": "value",  # Space in key
        "invalid.dot": "value",  # Dot in key
        "invalid$char": "value",  # Special char in key
    }
    for variables in [{"valid": "value", **{k: v}} for k, v in invalid_names.items()]:
        with pytest.raises(ValidationError, match="Invalid variable name"):
            Model(variables=variables)
    
    # Test invalid variable values
    invalid_values = {
        "var1": None,  # None not allowed
        "var2": {"nested": "dict"},  # Nested dict not allowed
        "var3": ["list", "not", "allowed"],  # List not allowed
    }
    for variables in [{"valid": "value", **{k: v}} for k, v in invalid_values.items()]:
        with pytest.raises(ValidationError, match="Invalid variable value"):
            Model(variables=variables) 