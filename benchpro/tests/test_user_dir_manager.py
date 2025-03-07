"""
Tests for the UserDirectoryManager.
"""

import os
import pytest
import tempfile
import shutil
from typing import Dict, Any

from benchpro.utils.user_dir import UserDirectoryManager, UserDirectoryManagerInterface
from benchpro.utils.filesystem import InMemoryFileSystem, TempFileSystem, create_in_memory_fs


@pytest.fixture
def in_memory_fs():
    """Create an in-memory file system for testing."""
    return create_in_memory_fs()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def in_memory_user_dir_manager(in_memory_fs):
    """Create a UserDirectoryManager with an in-memory file system."""
    return UserDirectoryManager(base_dir="/home/user/.benchpro", file_system=in_memory_fs)


@pytest.fixture
def temp_user_dir_manager(temp_dir):
    """Create a UserDirectoryManager with a temporary directory."""
    fs = TempFileSystem(temp_dir=temp_dir)
    return UserDirectoryManager(base_dir="/home/user/.benchpro", file_system=fs)


def test_user_dir_manager_interface():
    """Test that UserDirectoryManager implements the UserDirectoryManagerInterface."""
    assert issubclass(UserDirectoryManager, UserDirectoryManagerInterface)


def test_initialization(in_memory_user_dir_manager):
    """Test that UserDirectoryManager initializes correctly."""
    udm = in_memory_user_dir_manager
    
    # Check that directories are created
    for dir_key in udm.dirs:
        assert udm.file_system.exists(udm.dirs[dir_key])
        assert udm.file_system.is_dir(udm.dirs[dir_key])
    
    # Check that settings file is created
    assert udm.file_system.exists(udm.settings_file)


def test_get_path(in_memory_user_dir_manager):
    """Test the get_path method."""
    udm = in_memory_user_dir_manager
    
    # Test getting a directory path
    root_path = udm.get_path("root")
    assert root_path == "/home/user/.benchpro"
    
    # Test getting a file path
    file_path = udm.get_path("root", "settings.yaml")
    assert file_path == "/home/user/.benchpro/settings.yaml"
    
    # Test getting a nested path
    nested_path = udm.get_path("inputs", "application", "test.yaml")
    assert nested_path == "/home/user/.benchpro/inputs/application/test.yaml"
    
    # Test invalid directory key
    with pytest.raises(KeyError):
        udm.get_path("invalid_key")


def test_ensure_file_directory(in_memory_user_dir_manager):
    """Test the ensure_file_directory method."""
    udm = in_memory_user_dir_manager
    
    # Test creating a directory for a file
    file_path = "/home/user/.benchpro/new_dir/file.txt"
    assert udm.ensure_file_directory(file_path)
    assert udm.file_system.exists("/home/user/.benchpro/new_dir")
    
    # Test with a file in the root directory (no directory to create)
    file_path = "/home/user/.benchpro/file.txt"
    assert udm.ensure_file_directory(file_path)


def test_load_and_save_settings(in_memory_user_dir_manager):
    """Test loading and saving settings."""
    udm = in_memory_user_dir_manager
    
    # Load default settings
    settings = udm.load_settings()
    assert settings == udm.DEFAULT_SETTINGS
    
    # Modify settings
    settings["logging_level"] = "DEBUG"
    
    # Save settings
    assert udm.save_settings(settings)
    
    # Load settings again
    new_settings = udm.load_settings()
    assert new_settings["logging_level"] == "DEBUG"


def test_get_directories(in_memory_user_dir_manager):
    """Test getting application, benchmark, and source directories."""
    udm = in_memory_user_dir_manager
    
    # Test default directories
    # We need to check that the paths match the expected format from the settings
    # rather than comparing with the dirs dictionary
    assert udm.get_application_directory() == udm.settings["application_directory"]
    assert udm.get_benchmark_directory() == udm.settings["benchmark_directory"]
    assert udm.get_source_directory() == udm.settings["source_directory"]
    
    # Test custom directories in settings
    settings = udm.load_settings()
    settings["application_directory"] = "/custom/app/dir"
    settings["benchmark_directory"] = "/custom/bench/dir"
    settings["source_directory"] = "/custom/source/dir"
    udm.save_settings(settings)
    
    # Reload settings
    udm.settings = udm.load_settings()
    
    assert udm.get_application_directory() == "/custom/app/dir"
    assert udm.get_benchmark_directory() == "/custom/bench/dir"
    assert udm.get_source_directory() == "/custom/source/dir"


def test_copy_default_files(in_memory_user_dir_manager):
    """Test copying default files."""
    udm = in_memory_user_dir_manager
    fs = udm.file_system
    
    # Create source directory and files
    source_dir = "/source"
    fs.create_directory(source_dir)
    fs.write_file("/source/file1.txt", "Content 1")
    fs.write_file("/source/file2.txt", "Content 2")
    
    # Copy files
    assert udm.copy_default_files(source_dir, "inputs", ["file1.txt", "file2.txt"])
    
    # Check files were copied
    assert fs.exists(udm.get_path("inputs", "file1.txt"))
    assert fs.exists(udm.get_path("inputs", "file2.txt"))
    assert fs.read_file(udm.get_path("inputs", "file1.txt")) == "Content 1"
    
    # Test with non-existent source directory
    assert not udm.copy_default_files("/nonexistent", "inputs", ["file.txt"])
    
    # Test with non-existent source file
    assert not udm.copy_default_files(source_dir, "inputs", ["nonexistent.txt"])


def test_set_test_environment(temp_user_dir_manager, temp_dir):
    """Test setting up a test environment."""
    udm = temp_user_dir_manager
    
    # Save original directories
    original_dirs = udm.dirs.copy()
    
    # Set up test environment
    test_temp_dir = os.path.join(temp_dir, "test_env")
    udm.set_test_environment(test_temp_dir)
    
    # Check that directories were changed
    assert udm._is_test_environment
    assert udm.dirs["root"] == test_temp_dir
    assert udm.dirs != original_dirs
    
    # Check that test directories were created
    for dir_key in udm.dirs:
        assert udm.file_system.exists(udm.dirs[dir_key])
    
    # Reset test environment
    udm.reset_test_environment()
    
    # Check that directories were restored
    assert not udm._is_test_environment
    assert udm.dirs == original_dirs


def test_dependency_injection():
    """Test that UserDirectoryManager can be injected into other components."""
    # Create a component that uses UserDirectoryManager
    class TestComponent:
        def __init__(self, user_dir_manager: UserDirectoryManagerInterface):
            self.user_dir_manager = user_dir_manager
            
        def get_app_dir(self):
            return self.user_dir_manager.get_application_directory()
    
    # Create a UserDirectoryManager with an in-memory file system
    fs = create_in_memory_fs()
    udm = UserDirectoryManager(file_system=fs)
    
    # Create the component with the injected UserDirectoryManager
    component = TestComponent(udm)
    
    # Test that the component uses the injected UserDirectoryManager
    assert component.get_app_dir() == udm.get_application_directory() 