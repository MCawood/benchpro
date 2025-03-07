"""
Tests for the YamlConfigLoader class.
"""

import os
import pytest
import tempfile
import yaml
import shutil

from benchpro.config.loader import YamlConfigLoader
from benchpro.utils.filesystem import InMemoryFileSystem, create_in_memory_fs
from benchpro.utils.user_dir import UserDirectoryManager


@pytest.fixture
def in_memory_fs():
    """Create an in-memory file system for testing."""
    fs = create_in_memory_fs()
    
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
    
    # Create application profile
    app_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application"
    }
    
    # Create benchmark profile
    bench_profile = {
        "task_type": "benchmark",
        "name": "test_benchmark",
        "version": "1.0",
        "description": "Test benchmark"
    }
    
    # Create directories
    fs.create_directory("/benchpro/config")
    fs.create_directory("/benchpro/config/system")
    fs.create_directory("/home/user/.benchpro/inputs/application")
    fs.create_directory("/home/user/.benchpro/inputs/benchmark")
    
    # Write files
    fs.write_yaml("/benchpro/config/default.yaml", default_config)
    fs.write_yaml("/benchpro/config/system/default.yaml", system_config)
    fs.write_yaml("/home/user/.benchpro/inputs/application/test_app.yaml", app_profile)
    fs.write_yaml("/home/user/.benchpro/inputs/benchmark/test_benchmark.yaml", bench_profile)
    
    return fs


@pytest.fixture
def user_dir_manager(in_memory_fs):
    """Create a UserDirectoryManager with an in-memory file system."""
    return UserDirectoryManager(base_dir="/home/user/.benchpro", file_system=in_memory_fs)


@pytest.fixture
def config_loader(in_memory_fs, user_dir_manager):
    """Create a YamlConfigLoader with an in-memory file system."""
    return YamlConfigLoader(
        config_dir="/benchpro/config",
        file_system=in_memory_fs,
        user_dir_manager=user_dir_manager
    )


def test_load_file(config_loader, in_memory_fs):
    """Test loading a YAML file."""
    # Create a test file
    test_config = {"test": "value"}
    in_memory_fs.write_yaml("/test/config.yaml", test_config)
    
    # Load the file
    loaded_config = config_loader.load_file("/test/config.yaml")
    
    # Check the result
    assert loaded_config == test_config


def test_load_file_not_found(config_loader):
    """Test loading a non-existent file."""
    with pytest.raises(FileNotFoundError):
        config_loader.load_file("/non/existent/file.yaml")


def test_load_default_config(config_loader):
    """Test loading the default configuration."""
    # Load the default configuration
    default_config = config_loader.load_default_config()
    
    # Check the result
    assert default_config["task_type"] == "application"
    assert default_config["name"] == "default_app"
    assert default_config["version"] == "1.0"
    assert default_config["description"] == "Default application"


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
    
    # Check that an empty dict is returned
    assert system_config == {}


def test_load_profile_config_application(config_loader):
    """Test loading an application profile."""
    # Load the application profile
    profile_config = config_loader.load_profile_config("test_app", "application")
    
    # Check the result
    assert profile_config["task_type"] == "application"
    assert profile_config["name"] == "test_app"
    assert profile_config["version"] == "1.0"
    assert profile_config["description"] == "Test application"


def test_load_profile_config_benchmark(config_loader):
    """Test loading a benchmark profile."""
    # Load the benchmark profile
    profile_config = config_loader.load_profile_config("test_benchmark", "benchmark")
    
    # Check the result
    assert profile_config["task_type"] == "benchmark"
    assert profile_config["name"] == "test_benchmark"
    assert profile_config["version"] == "1.0"
    assert profile_config["description"] == "Test benchmark"


def test_load_profile_config_auto_detect(config_loader):
    """Test loading a profile with auto-detection of task type."""
    # Load the application profile without specifying task type
    profile_config = config_loader.load_profile_config("test_app")
    
    # Check the result
    assert profile_config["task_type"] == "application"
    assert profile_config["name"] == "test_app"
    
    # Load the benchmark profile without specifying task type
    profile_config = config_loader.load_profile_config("test_benchmark")
    
    # Check the result
    assert profile_config["task_type"] == "benchmark"
    assert profile_config["name"] == "test_benchmark"


def test_load_profile_config_not_found(config_loader):
    """Test loading a non-existent profile."""
    with pytest.raises(FileNotFoundError):
        config_loader.load_profile_config("non_existent") 