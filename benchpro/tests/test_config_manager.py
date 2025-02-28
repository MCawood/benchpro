"""
Tests for the ConfigManager class.
"""

import os
import pytest
import tempfile
import yaml
from benchpro.config.config_manager import ConfigManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories with test configuration files."""
    with tempfile.TemporaryDirectory() as config_temp_dir, tempfile.TemporaryDirectory() as profile_temp_dir:
        # Create default config in config_dir
        default_config = {
            "job": {
                "name": "default_job",
                "output_dir": "results/output"
            },
            "scheduler": {
                "type": "slurm",
                "queue": "default"
            }
        }
        with open(os.path.join(config_temp_dir, "default.yaml"), 'w') as f:
            yaml.dump(default_config, f)
            
        # Create system config in config_dir
        system_config = {
            "scheduler": {
                "queue": "compute",
                "account": "project123"
            }
        }
        with open(os.path.join(config_temp_dir, "system_default.yaml"), 'w') as f:
            yaml.dump(system_config, f)
            
        # Create profile config in profile_dir
        profile_config = {
            "job": {
                "name": "test_job"
            },
            "scheduler": {
                "nodes": 2,
                "tasks_per_node": 16
            }
        }
        with open(os.path.join(profile_temp_dir, "test_profile.yaml"), 'w') as f:
            yaml.dump(profile_config, f)
            
        yield {"config_dir": config_temp_dir, "profile_dir": profile_temp_dir}


def test_load_default_config(temp_dirs):
    """Test loading the default configuration."""
    config_manager = ConfigManager(config_dir=temp_dirs["config_dir"], profile_dir=temp_dirs["profile_dir"])
    default_config = config_manager.load_default_config()
    
    assert default_config["job"]["name"] == "default_job"
    assert default_config["scheduler"]["type"] == "slurm"
    assert default_config["scheduler"]["queue"] == "default"


def test_load_system_config(temp_dirs):
    """Test loading the system configuration."""
    config_manager = ConfigManager(config_dir=temp_dirs["config_dir"], profile_dir=temp_dirs["profile_dir"])
    system_config = config_manager.load_system_config("default")
    
    assert system_config["scheduler"]["queue"] == "compute"
    assert system_config["scheduler"]["account"] == "project123"


def test_load_profile_config(temp_dirs):
    """Test loading a profile configuration."""
    config_manager = ConfigManager(config_dir=temp_dirs["config_dir"], profile_dir=temp_dirs["profile_dir"])
    profile_config = config_manager.load_profile_config("test_profile")
    
    assert profile_config["job"]["name"] == "test_job"
    assert profile_config["scheduler"]["nodes"] == 2
    assert profile_config["scheduler"]["tasks_per_node"] == 16


def test_merge_configs(temp_dirs):
    """Test merging configurations with proper precedence."""
    config_manager = ConfigManager(config_dir=temp_dirs["config_dir"], profile_dir=temp_dirs["profile_dir"])
    merged_config = config_manager.merge_configs("test_profile")
    
    # Profile values should override defaults
    assert merged_config["job"]["name"] == "test_job"  # From profile
    assert merged_config["job"]["output_dir"] == "results/output"  # From default
    
    # System values should be applied
    assert merged_config["scheduler"]["queue"] == "compute"  # From system
    assert merged_config["scheduler"]["account"] == "project123"  # From system
    
    # Profile values should override system
    assert merged_config["scheduler"]["nodes"] == 2  # From profile
    assert merged_config["scheduler"]["tasks_per_node"] == 16  # From profile
    
    # Default values should be preserved if not overridden
    assert merged_config["scheduler"]["type"] == "slurm"  # From default


def test_merge_configs_with_cli_overrides(temp_dirs):
    """Test merging configurations with CLI overrides."""
    config_manager = ConfigManager(config_dir=temp_dirs["config_dir"], profile_dir=temp_dirs["profile_dir"])
    
    cli_overrides = {
        "job": {
            "name": "cli_job"
        },
        "scheduler": {
            "nodes": 4
        }
    }
    
    merged_config = config_manager.merge_configs("test_profile", cli_overrides)
    
    # CLI values should override profile, system, and defaults
    assert merged_config["job"]["name"] == "cli_job"  # From CLI
    assert merged_config["scheduler"]["nodes"] == 4  # From CLI
    
    # Other values should be preserved
    assert merged_config["job"]["output_dir"] == "results/output"  # From default
    assert merged_config["scheduler"]["queue"] == "compute"  # From system
    assert merged_config["scheduler"]["tasks_per_node"] == 16  # From profile


def test_validate_config_valid():
    """Test validating a valid configuration."""
    config_manager = ConfigManager()
    config = {
        "job": {
            "name": "test_job"
        },
        "scheduler": {
            "type": "slurm"
        }
    }
    errors = config_manager.validate_config(config)
    
    assert len(errors) == 0


def test_validate_config_missing_required():
    """Test validating a configuration with missing required sections."""
    config_manager = ConfigManager()
    config = {
        "job": {
            "description": "Missing name"
        }
    }
    errors = config_manager.validate_config(config)
    
    assert len(errors) > 0
    assert any("Missing required configuration section: scheduler" in error for error in errors)
    assert any("Missing required job configuration: name" in error for error in errors)


def test_validate_config_invalid_types():
    """Test validating a configuration with invalid types."""
    config_manager = ConfigManager()
    config = {
        "job": "not_a_dict",
        "scheduler": {
            "type": "slurm"
        }
    }
    errors = config_manager.validate_config(config)
    
    assert len(errors) > 0
    assert any("'job' configuration must be a dictionary" in error for error in errors) 