"""
Tests for the ConfigManager class.
"""

import os
import pytest
import tempfile
import yaml
import shutil
from benchpro.config.config_manager import ConfigManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, "config")
    
    # Create directories needed for tests
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
    
    # Return the temporary directories
    return {
        "temp_dir": temp_dir,
        "config_dir": config_dir
    }


def test_load_default_config(temp_dirs):
    """Test loading the default configuration."""
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"], 
        is_test_environment=True, 
        test_dir=temp_dirs["temp_dir"]
    )
    default_config = config_manager.load_default_config()
    
    # Check that we loaded default configuration properly
    assert "job" in default_config
    assert "scheduler" in default_config["job"]


def test_load_system_config(temp_dirs):
    """Test loading the system configuration."""
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"], 
        is_test_environment=True, 
        test_dir=temp_dirs["temp_dir"]
    )
    system_config = config_manager.load_system_config()
    
    assert "job" in system_config
    assert system_config["job"]["account"] == "system_account"
    assert system_config["job"]["tasks_per_node"] == 16


def test_load_profile_config(temp_dirs):
    """Test loading a profile configuration."""
    # Initialize config manager in test mode
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        is_test_environment=True,
        test_dir=temp_dirs["temp_dir"]
    )
    
    # Create a test profile in the test inputs directory
    test_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application"
    }
    
    # Save the profile to the test inputs directory
    inputs_app_dir = os.path.join(temp_dirs["temp_dir"], "inputs", "application")
    os.makedirs(inputs_app_dir, exist_ok=True)
    
    with open(os.path.join(inputs_app_dir, "test_profile.yaml"), 'w') as f:
        yaml.dump(test_profile, f)
    
    # Test loading the profile
    profile_config = config_manager.load_profile_config("test_profile", task_type="application")
    
    assert profile_config["task_type"] == "application"
    assert profile_config["name"] == "test_app"


def test_merge_configs(temp_dirs):
    """Test merging configurations with proper precedence."""
    # Initialize config manager in test mode
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        is_test_environment=True,
        test_dir=temp_dirs["temp_dir"]
    )
    
    # Create a test profile in the test inputs directory
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
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    
    # Save the profile to the test inputs directory
    inputs_app_dir = os.path.join(temp_dirs["temp_dir"], "inputs", "application")
    os.makedirs(inputs_app_dir, exist_ok=True)
    
    with open(os.path.join(inputs_app_dir, "test_profile.yaml"), 'w') as f:
        yaml.dump(test_profile, f)
    
    # Test merging configs
    merged_config = config_manager.merge_configs("test_profile")
    
    # Profile values should override defaults
    assert merged_config["name"] == "test_app"  # From profile
    
    # Check that job configuration is properly merged
    assert "job" in merged_config
    assert "account" in merged_config["job"]
    assert "nodes" in merged_config["job"]
    assert "tasks_per_node" in merged_config["job"]


def test_merge_configs_with_cli_overrides(temp_dirs):
    """Test merging configurations with CLI overrides."""
    # Initialize config manager in test mode
    config_manager = ConfigManager(
        config_dir=temp_dirs["config_dir"],
        is_test_environment=True,
        test_dir=temp_dirs["temp_dir"]
    )
    
    # Create a test profile in the test inputs directory
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
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    
    # Save the profile to the test inputs directory
    inputs_app_dir = os.path.join(temp_dirs["temp_dir"], "inputs", "application")
    os.makedirs(inputs_app_dir, exist_ok=True)
    
    with open(os.path.join(inputs_app_dir, "test_profile.yaml"), 'w') as f:
        yaml.dump(test_profile, f)
    
    # Define CLI overrides
    cli_overrides = {
        "name": "cli_app",
        "job": {
            "nodes": 4,
            "account": "cli_account"
        }
    }
    
    # Test merging configs with CLI overrides
    merged_config = config_manager.merge_configs("test_profile", cli_overrides)
    
    # CLI overrides should take precedence
    assert merged_config["name"] == "cli_app"  # From CLI
    assert merged_config["job"]["nodes"] == 4  # From CLI
    assert merged_config["job"]["account"] == "cli_account"  # From CLI
    assert merged_config["job"]["tasks_per_node"] == 16  # From profile


def test_validate_config_valid():
    """Test validating a valid configuration."""
    config_manager = ConfigManager()
    
    # Valid application config
    valid_app_config = {
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
            "account": "system_account",
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
        "template": "test_app.j2"
    }
    errors = config_manager.validate_config(valid_app_config)
    assert len(errors) == 0
    
    # Valid benchmark config
    valid_bench_config = {
        "task_type": "benchmark",
        "name": "test_bench",
        "version": "1.0",
        "description": "Test benchmark",
        "run": {
            "application": "test_app",
            "arguments": "-n 10",
            "input_files": [],
            "output_files": [],
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "system_account",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "input_dir": "test_input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "results": {
            "metrics": ["runtime"],
            "parser": "simple",
            "output_format": "json"
        },
        "template": "test_bench.j2"
    }
    errors = config_manager.validate_config(valid_bench_config)
    assert len(errors) == 0


def test_validate_config_missing_required():
    """Test validating a configuration with missing required fields."""
    config_manager = ConfigManager()
    
    # Missing required fields in application config
    invalid_app_config = {
        "task_type": "application",
        "name": "test_app"
    }
    errors = config_manager.validate_config(invalid_app_config)
    assert len(errors) > 0
    assert any("Field required" in error for error in errors)
    
    # Missing required fields in benchmark config
    invalid_bench_config = {
        "task_type": "benchmark",
        "name": "test_bench"
    }
    errors = config_manager.validate_config(invalid_bench_config)
    assert len(errors) > 0
    assert any("Field required" in error for error in errors)


def test_validate_config_invalid_types():
    """Test validating a configuration with invalid field types."""
    config_manager = ConfigManager()
    
    # Invalid types in application config
    invalid_app_config = {
        "task_type": "application",
        "name": "test_app",
        "version": 1.0,  # Should be a string
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": "1"  # Should be an integer
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "system_account",
            "nodes": "1",  # Should be an integer
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "/path/to/source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": "true",  # Should be a boolean
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    errors = config_manager.validate_config(invalid_app_config)
    assert len(errors) > 0
    
    # Invalid types in benchmark config
    invalid_bench_config = {
        "task_type": "benchmark",
        "name": "test_bench",
        "version": 1.0,  # Should be a string
        "run": {
            "application": "test_app",
            "arguments": "-n 10",
            "input_files": "file.txt",  # Should be a list
            "output_files": [],
            "threads": "1"  # Should be an integer
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "system_account",
            "nodes": "1",  # Should be an integer
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "input_dir": "test_input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": "true",  # Should be a boolean
            "keep_output": True
        },
        "results": {
            "metrics": "runtime",  # Should be a list
            "parser": "simple",
            "output_format": "json"
        },
        "template": "test_bench.j2"
    }
    errors = config_manager.validate_config(invalid_bench_config)
    assert len(errors) > 0 