"""
Tests for the Registry Manager.
"""

import os
import tempfile
import shutil
import pytest
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.task import Application
from benchpro.config.config_manager import ConfigManager


@pytest.fixture
def temp_registry():
    """Create a temporary registry file."""
    temp_dir = tempfile.mkdtemp()
    registry_path = os.path.join(temp_dir, "registry.yaml")
    
    # Create a registry manager with the temporary path
    registry_manager = RegistryManager(registry_path)
    
    yield registry_manager
    
    # Clean up
    shutil.rmtree(temp_dir)


def test_registry_init():
    """Test registry initialization."""
    registry_manager = RegistryManager()
    assert registry_manager.registry["version"] == "1.0"
    assert registry_manager.registry["applications"] == []


def test_registry_save_load(temp_registry):
    """Test saving and loading the registry."""
    # Add an application
    app_data = {
        "name": "test_app",
        "version": "1.0",
        "workspace_dir": "/tmp/test",
        "binary_path": "/tmp/test/bin/test_app"
    }
    
    # Register the application
    app_id = temp_registry.register_application(app_data)
    assert app_id != ""
    
    # Create a new registry manager with the same path
    new_registry = RegistryManager(temp_registry.registry_path)
    new_registry.load()
    
    # Check that the application was loaded
    assert len(new_registry.registry["applications"]) == 1
    assert new_registry.registry["applications"][0]["name"] == "test_app"


def test_find_application(temp_registry):
    """Test finding applications."""
    # Add applications
    app1_data = {
        "name": "app1",
        "version": "1.0",
        "workspace_dir": "/tmp/app1",
        "binary_path": "/tmp/app1/bin/app1",
        "build_parameters": {
            "compiler": "gcc",
            "flags": "-O2"
        }
    }
    
    app2_data = {
        "name": "app2",
        "version": "2.0",
        "workspace_dir": "/tmp/app2",
        "binary_path": "/tmp/app2/bin/app2",
        "build_parameters": {
            "compiler": "icc",
            "flags": "-O3"
        }
    }
    
    # Register the applications
    app1_id = temp_registry.register_application(app1_data)
    app2_id = temp_registry.register_application(app2_data)
    
    # Find by ID
    app1 = temp_registry.find_application(app1_id)
    assert app1["name"] == "app1"
    
    # Find by criteria
    apps = temp_registry.find_applications({"name": "app2"})
    assert len(apps) == 1
    assert apps[0]["version"] == "2.0"
    
    # Find by nested criteria
    apps = temp_registry.find_applications({"build_parameters.compiler": "gcc"})
    assert len(apps) == 1
    assert apps[0]["name"] == "app1"


def test_update_remove_application(temp_registry):
    """Test updating and removing applications."""
    # Add an application
    app_data = {
        "name": "test_app",
        "version": "1.0",
        "workspace_dir": "/tmp/test",
        "binary_path": "/tmp/test/bin/test_app"
    }
    
    # Register the application
    app_id = temp_registry.register_application(app_data)
    
    # Update the application
    update_data = {
        "version": "1.1",
        "build_parameters": {
            "compiler": "gcc",
            "flags": "-O3"
        }
    }
    
    success = temp_registry.update_application(app_id, update_data)
    assert success
    
    # Check that the application was updated
    app = temp_registry.find_application(app_id)
    assert app["version"] == "1.1"
    assert app["build_parameters"]["flags"] == "-O3"
    
    # Remove the application
    success = temp_registry.remove_application(app_id)
    assert success
    
    # Check that the application was removed
    app = temp_registry.find_application(app_id)
    assert app is None


def test_clean_registry(temp_registry):
    """Test cleaning the registry."""
    # Add applications with non-existent binary paths
    app1_data = {
        "name": "app1",
        "version": "1.0",
        "workspace_dir": "/tmp/app1",
        "binary_path": "/tmp/app1/bin/app1"
    }
    
    app2_data = {
        "name": "app2",
        "version": "2.0",
        "workspace_dir": "/tmp/app2",
        "binary_path": "/tmp/app2/bin/app2"
    }
    
    # Register the applications
    temp_registry.register_application(app1_data)
    temp_registry.register_application(app2_data)
    
    # Clean the registry
    removed_count = temp_registry.clean_registry(verify_paths=True)
    
    # Both applications should be removed since their binary paths don't exist
    assert removed_count == 2
    assert len(temp_registry.list_applications()) == 0


def test_application_uniqueness():
    """Test that applications with the same name, version, and build parameters are detected as duplicates."""
    # Create a temporary registry
    temp_dir = tempfile.mkdtemp()
    registry_path = os.path.join(temp_dir, "registry.yaml")
    
    try:
        # Create a registry manager with the temporary path
        registry_manager = RegistryManager(registry_path)
        
        # Register an application
        app_data = {
            "name": "test_app",
            "version": "1.0",
            "workspace_dir": "/tmp/test",
            "binary_path": "/tmp/test/bin/test_app",
            "build_parameters": {
                "compiler": "gcc",
                "flags": "-O2"
            }
        }
        
        app_id = registry_manager.register_application(app_data)
        assert app_id != ""
        
        # Create an Application instance
        app = Application(registry_manager=registry_manager)
        
        # Check if the application exists
        with pytest.raises(ValueError) as excinfo:
            app.check_application_exists(
                app_name="test_app",
                app_version="1.0",
                build_params={"compiler": "gcc", "flags": "-O2"},
                force=False
            )
        
        # Check that the error message contains the expected text
        assert "already exists in the registry" in str(excinfo.value)
        
        # Check that force=True allows the application to be built
        result = app.check_application_exists(
            app_name="test_app",
            app_version="1.0",
            build_params={"compiler": "gcc", "flags": "-O2"},
            force=True
        )
        assert result is None
        
        # Check that different build parameters are considered unique
        result = app.check_application_exists(
            app_name="test_app",
            app_version="1.0",
            build_params={"compiler": "gcc", "flags": "-O3"},
            force=False
        )
        assert result is None
        
        # Check that different versions are considered unique
        result = app.check_application_exists(
            app_name="test_app",
            app_version="1.1",
            build_params={"compiler": "gcc", "flags": "-O2"},
            force=False
        )
        assert result is None
        
        # Check that different names are considered unique
        result = app.check_application_exists(
            app_name="other_app",
            app_version="1.0",
            build_params={"compiler": "gcc", "flags": "-O2"},
            force=False
        )
        assert result is None
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir) 