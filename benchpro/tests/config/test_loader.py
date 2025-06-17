"""
Tests for the YamlConfigLoader class.
"""

import os
import pytest
import tempfile
import yaml
import shutil

from benchpro.config.loader import YamlConfigLoader
from benchpro.utils.filesystem import InMemoryFileSystem, create_in_memory_fs, RealFileSystem
from benchpro.utils.user_dir import UserDirectoryManager, user_dir_manager
from benchpro.tests.conftest import create_isolated_test_env


@pytest.fixture
def in_memory_fs(setup_test_env):
    """Create an in-memory file system for testing."""
    fs = create_in_memory_fs()
    
    # Test environment is already set up by setup_test_env
    test_base_dir = setup_test_env["temp_dir"]
    
    # Create default configuration
    default_config = {
        "task_type": "application",
        "name": "default_app",
        "version": "1.0",
        "description": "Default application"
    }
    
    # Create system configuration
    system_config = {
        "system": "test_system",
        "job": {
            "scheduler": "slurm",
            "queue": "test_queue"
        }
    }
    
    # Create directories in in-memory file system
    fs.create_directory("/benchpro/config")
    fs.create_directory("/benchpro/config/system")
    
    # Write files to in-memory fs
    fs.write_yaml("/benchpro/config/default.yaml", default_config)
    fs.write_yaml("/benchpro/config/system/default.yaml", system_config)
    
    # Make sure the system config exists in the real test directory
    system_config_dir = os.path.join(test_base_dir, "config", "system")
    os.makedirs(system_config_dir, exist_ok=True)
    with open(os.path.join(system_config_dir, "default.yaml"), "w") as f:
        yaml.dump(system_config, f)
    
    # Store test_base_dir to allow fixtures to access it
    fs.test_base_dir = test_base_dir
    
    # Create necessary test profiles in the test environment
    # The test profiles should already be created by setup_test_env fixture,
    # but we'll make sure they have what we need for our tests
    app_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application"
    }
    
    bench_profile = {
        "task_type": "benchmark",
        "name": "test_benchmark",
        "version": "1.0",
        "description": "Test benchmark"
    }
    
    app_profile_path = os.path.join(test_base_dir, "inputs", "application", "test_app.yaml")
    bench_profile_path = os.path.join(test_base_dir, "inputs", "benchmark", "test_benchmark.yaml")
    
    # Ensure the profiles exist
    with open(app_profile_path, "w") as f:
        yaml.dump(app_profile, f)
    
    with open(bench_profile_path, "w") as f:
        yaml.dump(bench_profile, f)
    
    return fs


@pytest.fixture
def user_dir_manager(in_memory_fs):
    """Create a UserDirectoryManager with an in-memory file system."""
    # The UserDirectoryManager is already initialized with test environment by setup_test_env
    # We just need to ensure it's using our in-memory filesystem
    manager = UserDirectoryManager(base_dir=in_memory_fs.test_base_dir, file_system=in_memory_fs)
    
    # Make double-sure the test environment is set correctly
    manager.set_test_environment(in_memory_fs.test_base_dir)
    
    return manager


@pytest.fixture
def config_loader(setup_test_env, user_dir_manager):
    """Create a YamlConfigLoader with a real file system that can access the test directories."""
    return YamlConfigLoader(
        config_dir=os.path.join(setup_test_env["temp_dir"], "config"),
        file_system=RealFileSystem(),
        user_dir_manager=user_dir_manager
    )


def test_load_file(config_loader, setup_test_env):
    """Test loading a YAML file."""
    # Create a test file in the real filesystem
    test_config = {"test": "value"}
    test_file = os.path.join(setup_test_env["temp_dir"], "test_config.yaml")
    
    # Write the file to disk
    with open(test_file, "w") as f:
        yaml.dump(test_config, f)
    
    # Load the file
    loaded_config = config_loader.load_file(test_file)
    
    # Check the result
    assert loaded_config == test_config


def test_load_file_not_found(config_loader):
    """Test loading a non-existent file."""
    with pytest.raises(FileNotFoundError):
        config_loader.load_file("/non/existent/file.yaml")


def test_load_default_config(config_loader, setup_test_env):
    """Test loading the default configuration."""
    # Create a default config file with the expected structure for the test
    default_config = {
        "job": {
            "name": "default_job",
            "scheduler": "slurm",
            "queue": "default"
        }
    }
    
    # Write it to the expected location in the test environment
    default_config_path = os.path.join(setup_test_env["config_dir"], "default.yaml")
    with open(default_config_path, "w") as f:
        yaml.dump(default_config, f)
    
    # Load the default configuration
    loaded_config = config_loader.load_default_config()
    
    # Check the result matches what we wrote
    assert loaded_config["job"]["name"] == "default_job"
    assert loaded_config["job"]["scheduler"] == "slurm"
    assert loaded_config["job"]["queue"] == "default"


def test_load_system_config(config_loader):
    """Test loading the system configuration."""
    # Load the system configuration
    system_config = config_loader.load_system_config()
    
    # Check the result
    assert system_config["system"] == "test_system"
    assert system_config["job"]["scheduler"] == "slurm"
    assert system_config["job"]["queue"] == "test_queue"


def test_load_system_config_not_found(config_loader):
    """Test loading a non-existent system configuration."""
    # Load a non-existent system configuration
    system_config = config_loader.load_system_config("non_existent")
    
    # The loader should fall back to the default system config
    # instead of returning an empty dict
    assert system_config["system"] == "test_system"
    assert system_config["job"]["scheduler"] == "slurm"
    assert system_config["job"]["queue"] == "test_queue"


def test_load_profile_config_application(config_loader):
    """Test loading an application profile."""
    # Load the existing hello_world application profile that is
    # copied by setup_test_env
    profile_config = config_loader.load_profile_config("hello_world", "application")
    
    # Check the result
    assert profile_config is not None
    assert profile_config["task_type"] == "application"
    assert "name" in profile_config  # Basic check that it's a valid profile


def test_load_profile_config_benchmark(config_loader):
    """Test loading a benchmark profile."""
    # Load the existing hello_world benchmark profile that is
    # copied by setup_test_env
    profile_config = config_loader.load_profile_config("hello_world", "benchmark")
    
    # Check the result
    assert profile_config is not None
    assert profile_config["task_type"] == "benchmark"
    assert "name" in profile_config  # Basic check that it's a valid profile


def test_load_profile_config_auto_detect(config_loader):
    """Test loading a profile with auto-detection of task type."""
    # Load the existing hello_world application profile without specifying task type
    profile_config = config_loader.load_profile_config("hello_world")
    
    # Check the result
    assert profile_config is not None
    assert "task_type" in profile_config
    assert "name" in profile_config  # Basic check that it's a valid profile


def test_load_profile_config_not_found(config_loader):
    """Test loading a non-existent profile."""
    with pytest.raises(FileNotFoundError):
        config_loader.load_profile_config("non_existent") 