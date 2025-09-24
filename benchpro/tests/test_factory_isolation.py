"""
Tests for TaskFactory isolation in different directory environments.

This module verifies that the TaskFactory can work properly when 
forced to use isolated directories through dependency injection.
"""

import pytest
import yaml
import os
from unittest.mock import MagicMock

from benchpro.executor.task_factory import TaskFactory
from benchpro.config.config_manager import ConfigManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import UserDirectoryManager
import benchpro.utils.user_dir as user_dir_module


@pytest.fixture
def isolated_user_dir(tmp_path):
    """Provides a UserDirectoryManager in a temporary directory."""
    return UserDirectoryManager(base_dir=str(tmp_path))


def test_factory_can_create_task_in_isolated_dir(isolated_user_dir, monkeypatch):
    """
    This test verifies that the TaskFactory can assemble a task
    when we force its sub-components to use our isolated directory.
    """
    # 1. THE CRITICAL WORKAROUND:
    # We patch the `get_user_dir_manager` function. Any component created
    # by the factory will now be forced to use our isolated directory.
    monkeypatch.setattr(
        user_dir_module,
        "get_user_dir_manager",
        lambda: isolated_user_dir
    )

    # 2. Create mock dependencies for the TaskFactory
    # Since we're testing isolation, we create real ConfigManager and RegistryManager
    # but they will use our isolated directory due to the monkeypatch
    config_manager = ConfigManager(user_dir_manager=isolated_user_dir)
    registry_manager = RegistryManager()
    
    # 3. Create the TaskFactory with proper dependency injection
    factory = TaskFactory(
        config_manager=config_manager,
        registry_manager=registry_manager
    )

    # 4. Create a dummy profile file for the factory to find.
    # This simulates the real workflow where profiles exist in the user directory
    profile_content = {
        "task_type": "benchmark", 
        "name": "factory_test_profile",
        "version": "1.0",
        "run": {"executable": "test_exec", "application": "test_app"},
        "template": "test.j2"
    }
    
    profile_path = isolated_user_dir.get_path("inputs_benchmark", "factory_test_profile.yaml")
    os.makedirs(os.path.dirname(profile_path), exist_ok=True)
    with open(profile_path, "w") as f:
        yaml.dump(profile_content, f)

    # 5. Test the factory's ability to create a task using the profile data
    try:
        # We now pass the configuration directly as the new API expects
        task = factory.create_task(profile_content)

        # 6. We assert that a task was created and its internal config is correct.
        assert task is not None
        task_config = task.config_component.get_config()
        assert task_config["name"] == "factory_test_profile"
        assert task_config["task_type"] == "benchmark"

    except Exception as e:
        pytest.fail(f"TaskFactory failed to create a task in isolated directory. Error: {e}")


def test_factory_isolation_with_application_task(isolated_user_dir, monkeypatch):
    """Test that application tasks can also be created in isolated environments."""
    # Patch user directory manager
    monkeypatch.setattr(
        user_dir_module,
        "get_user_dir_manager", 
        lambda: isolated_user_dir
    )
    
    # Create dependencies
    config_manager = ConfigManager(user_dir_manager=isolated_user_dir)
    registry_manager = RegistryManager()
    factory = TaskFactory(config_manager=config_manager, registry_manager=registry_manager)
    
    # Prepare application configuration
    config = {
        "task_type": "application",
        "name": "isolated_app",
        "version": "1.0",
        "build": {"source": "test.c"},
        "template": "app.j2",
        "job": {"scheduler": "local"}
    }
    
    # Create and verify task
    task = factory.create_task(config)
    assert task is not None
    assert task.__class__.__name__ == "Application"
    
    task_config = task.config_component.get_config()
    assert task_config["name"] == "isolated_app"


def test_factory_respects_injected_dependencies(isolated_user_dir):
    """Test that the factory properly uses injected dependencies."""
    # Create mock dependencies
    mock_config_manager = MagicMock(spec=ConfigManager)
    mock_registry_manager = MagicMock(spec=RegistryManager)
    
    # Create factory with mocked dependencies
    factory = TaskFactory(
        config_manager=mock_config_manager,
        registry_manager=mock_registry_manager
    )
    
    # Prepare configuration
    config = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "build": {"source": "test.c"},
        "template": "test.j2"
    }
    
    # Create task
    task = factory.create_task(config)
    
    # Verify that the task's config component uses the injected config manager
    assert task.config_component.config_manager is mock_config_manager

