"""
Tests for the ConfigManager class.
"""

import os
import pytest
import tempfile
import yaml
import shutil

from benchpro.config.config_manager import ConfigManager
from benchpro.utils.filesystem import TempFileSystem, InMemoryFileSystem, create_temp_fs, create_in_memory_fs


def test_load_default_config(config_test_env):
    """Test loading the default configuration."""
    # Create a TempFileSystem that points to our test directories
    test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
    
    # Initialize ConfigManager with the TempFileSystem
    config_manager = ConfigManager(
        config_dir=config_test_env["config_dir"], 
        file_system=test_fs
    )
    
    # Test loading the default config
    default_config = config_manager.load_default_config()
    
    # Check that we loaded default configuration properly
    # Note: scheduler field is now handled by smart defaults, not in raw default config
    assert "execution" in default_config
    assert default_config["execution"]["type"] == "local"


def test_load_system_config(config_test_env):
    """Test loading the system configuration."""
    # Create a TempFileSystem that points to our test directories
    test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
    
    # Initialize ConfigManager with the TempFileSystem
    config_manager = ConfigManager(
        config_dir=config_test_env["config_dir"], 
        file_system=test_fs
    )
    
    # Test loading the system config
    system_config = config_manager.load_system_config()
    
    # Check that we loaded system configuration properly
    assert "job" in system_config
    assert system_config["job"]["account"] == "system_account"
    
    # Test loading a non-existent system config should return empty dict, not fail
    empty_config = config_manager.load_system_config("nonexistent")
    # The implementation should gracefully handle missing configs
    assert isinstance(empty_config, dict)


def test_load_profile_config(config_test_env):
    """Test loading a profile configuration."""
    # Create a TempFileSystem that points to our test directories
    test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
    
    # Initialize ConfigManager with the TempFileSystem
    config_manager = ConfigManager(
        config_dir=config_test_env["config_dir"],
        profile_dir=config_test_env["temp_dir"],
        file_system=test_fs
    )
    
    # Test loading the test_profile that was created by config_test_env
    profile_config = config_manager.load_profile_config("test_profile", task_type="application")
    
    assert profile_config["task_type"] == "application"
    assert profile_config["name"] == "test_profile"


def test_merge_configs(config_test_env):
    """Test merging configurations with proper precedence."""
    # Create a TempFileSystem that points to our test directories
    test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
    
    # Initialize ConfigManager with the TempFileSystem
    config_manager = ConfigManager(
        config_dir=config_test_env["config_dir"],
        profile_dir=config_test_env["temp_dir"],
        file_system=test_fs
    )
    
    # Test merging configurations using the merge_test profile created by config_test_env
    merged_config = config_manager.merge_configs("merge_test")
    
    # Check that proper precedence was applied
    # Profile values should override default and system values
    assert merged_config["version"] == "2.0"  # From profile (overrides default)
    assert merged_config["job"]["nodes"] == 4  # From profile (overrides default)
    assert merged_config["job"]["queue"] == "test_queue"  # From profile (overrides system)
    assert merged_config["job"]["tasks_per_node"] == 8  # From profile (overrides system)
    
    # Values not in profile should come from system, then default
    assert merged_config["job"]["scheduler"] == "slurm"  # From system/default (not overridden)


def test_merge_configs_with_cli_overrides(config_test_env):
    """Test merging configurations with CLI overrides."""
    # Create a TempFileSystem that points to our test directories
    test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
    
    # Initialize ConfigManager with the TempFileSystem
    config_manager = ConfigManager(
        config_dir=config_test_env["config_dir"],
        profile_dir=config_test_env["temp_dir"],
        file_system=test_fs
    )
    
    # Define CLI overrides
    cli_overrides = {
        "job": {
            "nodes": 8,  # Override profile value
            "tasks_per_node": 32,  # Override profile value
            "time_limit": "02:00:00"  # Override profile value
        },
        "build": {
            "compiler": "icc",  # Override profile value
            "flags": "-O3"  # Override profile value
        }
    }
    
    # Test merging configurations with CLI overrides using cli_test profile
    merged_config = config_manager.merge_configs("cli_test", cli_overrides=cli_overrides)
    
    # Check that proper precedence was applied
    # CLI overrides should override profile values
    assert merged_config["job"]["nodes"] == 8  # From CLI (overrides profile)
    assert merged_config["job"]["tasks_per_node"] == 32  # From CLI (overrides profile)
    assert merged_config["job"]["time_limit"] == "02:00:00"  # From CLI (overrides profile)
    assert merged_config["build"]["compiler"] == "icc"  # From CLI (overrides profile)
    assert merged_config["build"]["flags"] == "-O3"  # From CLI (overrides profile)
    
    # Values not in CLI overrides should come from profile
    assert merged_config["version"] == "1.0"  # From profile (not overridden)
    assert merged_config["job"]["scheduler"] == "slurm"  # From profile (not overridden)
    assert merged_config["job"]["account"] == "project123"  # From profile (not overridden)


def test_validate_config_valid():
    """Test validating a valid configuration."""
    mock_fs = create_in_memory_fs()
    
    # Initialize config manager with mock file system
    config_manager = ConfigManager(file_system=mock_fs)
    
    # Create a valid configuration
    valid_config = {
        "task_type": "application",
        "name": "valid_app",
        "version": "1.0",
        "description": "A valid application configuration",
        "build": {
            "source": "main.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "valid_app"
        },
        "environment": {
            "modules": ["gcc", "mpi"],
            "variables": {"OMP_NUM_THREADS": "4"}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "project123",
            "nodes": 2,
            "tasks_per_node": 16,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "app.j2"
    }
    
    # Validate the config
    validation_errors = config_manager.validate_config(valid_config)
    
    # Check that there are no errors
    assert len(validation_errors) == 0


def test_validate_config_missing_required():
    """Test validating a configuration with missing required fields."""
    mock_fs = create_in_memory_fs()
    
    # Initialize config manager with mock file system
    config_manager = ConfigManager(file_system=mock_fs)
    
    # Create a configuration with missing required fields
    invalid_config = {
        "task_type": "application",
        # Missing "name" field
        "version": "1.0",
        "description": "An invalid application configuration",
        # Missing "build" section
        "environment": {
            "modules": ["gcc", "mpi"],
            "variables": {"OMP_NUM_THREADS": "4"}
        },
        # Missing "job" section
        # Missing "workspace" section
        # Missing "template" field
    }
    
    # Validate the config
    validation_errors = config_manager.validate_config(invalid_config)
    
    # Check that the validation caught the missing required fields
    assert len(validation_errors) > 0
    
    # Check for specific error messages
    missing_fields = ['name', 'build', 'workspace', 'template']
    for field in missing_fields:
        assert any(field in error for error in validation_errors)


def test_validate_config_invalid_types():
    """Test validating a configuration with invalid field types."""
    mock_fs = create_in_memory_fs()
    
    # Initialize config manager with mock file system
    config_manager = ConfigManager(file_system=mock_fs)
    
    # Create a configuration with invalid field types
    invalid_config = {
        "task_type": "application",
        "name": 123,  # Should be a string
        "version": [1, 0],  # Should be a string
        "description": "A configuration with invalid types",
        "build": {
            "source": "main.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": "invalid"  # Should be an integer
        },
        "environment": {
            "modules": "gcc, mpi",  # Should be a list
            "variables": ["OMP_NUM_THREADS=4"]  # Should be a dictionary
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "project123",
            "nodes": "2",  # Should be an integer
            "tasks_per_node": 16,
            "time_limit": 600  # Should be a string
        },
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": "true",  # Should be a boolean
            "keep_build": 1  # Should be a boolean
        },
        "template": 123  # Should be a string
    }
    
    # Validate the config
    validation_errors = config_manager.validate_config(invalid_config)
    
    # Check that the validation caught the invalid field types
    assert len(validation_errors) > 0
    
    # Print the validation errors for debugging
    print("Validation errors:")
    for error in validation_errors:
        print(f"  {error}")
    
    # Check that we have errors for the basic fields with type issues
    assert any("name" in error.lower() for error in validation_errors)
    assert any("version" in error.lower() for error in validation_errors)
    assert any("template" in error.lower() for error in validation_errors) 