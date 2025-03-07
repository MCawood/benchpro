"""
Tests for the ConfigManager class.
"""

import os
import pytest
import tempfile
import yaml
import shutil

from benchpro.config.config_manager import ConfigManager
from benchpro.utils.filesystem import TestFileSystem


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # Create default configuration
    default_config = {
        "task_type": "application",
        "name": "default_app",
        "version": "1.0",
        "description": "Default application",
        "build": {
            "source": "default.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "default_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "default_account",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "default_app.j2"
    }
    with open(os.path.join(config_dir, "default.yaml"), 'w') as f:
        yaml.dump(default_config, f)
        
    # Create system configuration
    system_config = {
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "system_account",
            "nodes": 1,
            "tasks_per_node": 16,
            "time_limit": "00:10:00"
        }
    }
    with open(os.path.join(config_dir, "system_default.yaml"), 'w') as f:
        yaml.dump(system_config, f)
    
    # Create required directories for tests
    inputs_app_dir = os.path.join(temp_dir, "inputs", "application")
    inputs_bench_dir = os.path.join(temp_dir, "inputs", "benchmark")
    os.makedirs(inputs_app_dir, exist_ok=True)
    os.makedirs(inputs_bench_dir, exist_ok=True)
    
    # Return the temporary directories
    yield {"temp_dir": temp_dir, "config_dir": config_dir}
    
    # Clean up
    shutil.rmtree(temp_dir)


def test_load_default_config(temp_dirs):
    """Test loading the default configuration."""
    # Create a TestFileSystem that points to our test directories
    test_fs = TestFileSystem(base_temp_dir=temp_dirs["temp_dir"])
    
    # Initialize ConfigManager with the TestFileSystem
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"], 
        file_system=test_fs
    )
    
    # Test loading the default config
    default_config = config_manager.load_default_config()
    
    # Check that we loaded default configuration properly
    assert "job" in default_config
    assert "scheduler" in default_config["job"]


def test_load_system_config(temp_dirs):
    """Test loading the system configuration."""
    # Create a TestFileSystem that points to our test directories
    test_fs = TestFileSystem(base_temp_dir=temp_dirs["temp_dir"])
    
    # Initialize ConfigManager with the TestFileSystem
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"], 
        file_system=test_fs
    )
    
    # Test loading the system config
    system_config = config_manager.load_system_config()
    
    # Check that we loaded system configuration properly
    assert "job" in system_config
    assert system_config["job"]["account"] == "system_account"
    
    # Test loading a non-existent system config
    empty_config = config_manager.load_system_config("nonexistent")
    assert empty_config == {}


def test_load_profile_config(temp_dirs):
    """Test loading a profile configuration."""
    # Create a TestFileSystem that points to our test directories
    test_fs = TestFileSystem(base_temp_dir=temp_dirs["temp_dir"])
    
    # Create required input directories
    inputs_app_dir = test_fs.join_paths(temp_dirs["temp_dir"], "inputs", "application")
    test_fs.create_directory(inputs_app_dir)
    
    # Create a test profile
    test_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
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
            "source_dir": "${job.account}/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    
    # Save the profile to a file using the TestFileSystem
    profile_path = test_fs.join_paths(inputs_app_dir, "test_profile.yaml")
    test_fs.write_yaml(profile_path, test_profile)
    
    # Log some debug information
    print(f"Created profile at: {profile_path}")
    print(f"Directory exists: {test_fs.exists(inputs_app_dir)}")
    print(f"Profile exists: {test_fs.exists(profile_path)}")
    
    # Initialize ConfigManager with the TestFileSystem
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        profile_dir=temp_dirs["temp_dir"],
        file_system=test_fs
    )
    
    # Test loading the profile
    profile_config = config_manager.load_profile_config("test_profile", task_type="application")
    
    assert profile_config["task_type"] == "application"
    assert profile_config["name"] == "test_app"


def test_merge_configs(temp_dirs):
    """Test merging configurations with proper precedence."""
    # Create a TestFileSystem that points to our test directories
    test_fs = TestFileSystem(base_temp_dir=temp_dirs["temp_dir"])
    
    # Initialize ConfigManager with the TestFileSystem
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        profile_dir=temp_dirs["temp_dir"],
        file_system=test_fs
    )
    
    # Create a test profile in the test inputs directory
    inputs_app_dir = test_fs.join_paths(temp_dirs["temp_dir"], "inputs", "application")
    test_fs.create_directory(inputs_app_dir)
    
    test_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "2.0",  # Different from default config
        "description": "Test application",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "test_queue",  # Different from system config
            "account": "test_account",
            "nodes": 4,  # Different from default config
            "tasks_per_node": 8,  # Different from system config
            "time_limit": "01:00:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    
    # Save the profile using the TestFileSystem
    profile_path = test_fs.join_paths(inputs_app_dir, "merge_test.yaml")
    test_fs.write_yaml(profile_path, test_profile)
    
    # Test merging configurations
    merged_config = config_manager.merge_configs("merge_test")
    
    # Check that proper precedence was applied
    # Profile values should override default and system values
    assert merged_config["version"] == "2.0"  # From profile (overrides default)
    assert merged_config["job"]["nodes"] == 4  # From profile (overrides default)
    assert merged_config["job"]["queue"] == "test_queue"  # From profile (overrides system)
    assert merged_config["job"]["tasks_per_node"] == 8  # From profile (overrides system)
    
    # Values not in profile should come from system, then default
    assert merged_config["job"]["scheduler"] == "slurm"  # From system/default (not overridden)


def test_merge_configs_with_cli_overrides(temp_dirs):
    """Test merging configurations with CLI overrides."""
    # Create a TestFileSystem that points to our test directories
    test_fs = TestFileSystem(base_temp_dir=temp_dirs["temp_dir"])
    
    # Initialize ConfigManager with the TestFileSystem
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        profile_dir=temp_dirs["temp_dir"],
        file_system=test_fs
    )
    
    # Create a test profile in the test inputs directory
    inputs_app_dir = test_fs.join_paths(temp_dirs["temp_dir"], "inputs", "application")
    test_fs.create_directory(inputs_app_dir)
    
    test_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application",
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "project123",
            "nodes": 2,
            "tasks_per_node": 16,
            "time_limit": "00:10:00"
        },
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    
    # Save the profile using the TestFileSystem
    profile_path = test_fs.join_paths(inputs_app_dir, "cli_test.yaml")
    test_fs.write_yaml(profile_path, test_profile)
    
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
    
    # Test merging configurations with CLI overrides
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
    # Create mock files
    mock_fs = TestFileSystem()
    
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
    # Create mock files
    mock_fs = TestFileSystem()
    
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
    # Create mock files
    mock_fs = TestFileSystem()
    
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