"""
Tests for the TaskOrchestrator class.

This module contains tests for the composition-based TaskOrchestrator using
standardized test data and fixtures for consistency.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import pytest

from benchpro.executor.task import Task, Application, Benchmark
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.config.config_manager import ConfigManager
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager


@pytest.fixture
def mock_orchestrator_setup(standardized_test_env):
    """Set up a TaskOrchestrator with mocked dependencies for testing."""
    # Create mock dependencies
    mock_config_manager = MagicMock()
    mock_workspace_manager = MagicMock()
    mock_registry_manager = MagicMock()
    
    # Create a mock task
    mock_task = MagicMock()
    mock_task.run.return_value = (True, "12345")
    mock_task.generate_script.return_value = os.path.join(standardized_test_env["temp_dir"], "script.sh")
    mock_task.submit_job.return_value = (True, "12345")
    
    # Create a mock config component
    mock_config_component = MagicMock()
    mock_config_component.get_config.return_value = {
        "workspace": {"logs_dir": os.path.join(standardized_test_env["temp_dir"], "logs")}
    }
    
    # Attach the mock config component to the mock task
    mock_task.config_component = mock_config_component
    
    # Create the orchestrator
    orchestrator = TaskOrchestrator(
        config_manager=mock_config_manager,
        workspace_manager=mock_workspace_manager,
        registry_manager=mock_registry_manager
    )
    
    # Mock the task factory
    orchestrator.task_factory = MagicMock()
    orchestrator.task_factory.create_task.return_value = mock_task
    
    return {
        "orchestrator": orchestrator,
        "mock_config_manager": mock_config_manager,
        "mock_workspace_manager": mock_workspace_manager,
        "mock_registry_manager": mock_registry_manager,
        "mock_task": mock_task,
        "test_env": standardized_test_env
    }


def test_execute_with_default_config(mock_orchestrator_setup):
    """Test execute with default configuration using standardized test data."""
    setup = mock_orchestrator_setup
    orchestrator = setup["orchestrator"]
    mock_config_manager = setup["mock_config_manager"]
    mock_workspace_manager = setup["mock_workspace_manager"]
    test_env = setup["test_env"]
    
    # Set up mock config manager using standardized test structure
    merged_config = {
        "execution": {"type": "local"},
        "task_type": "application",
        "name": "test_profile",
        "template": "hello_world.j2"
    }
    mock_config_manager.merge_configs.return_value = merged_config
    
    # Set up workspace mock
    workspace_mock = {
        "workspace_dir": os.path.join(test_env["temp_dir"], "workspace"),
        "logs_dir": os.path.join(test_env["temp_dir"], "workspace", "logs"),
        "inputs_dir": os.path.join(test_env["temp_dir"], "workspace", "inputs"),
        "metadata_dir": os.path.join(test_env["temp_dir"], "workspace", ".benchpro"),
        "scripts_dir": os.path.join(test_env["temp_dir"], "workspace", "scripts"),
        "results_dir": os.path.join(test_env["temp_dir"], "workspace", "results"),
        "build_dir": os.path.join(test_env["temp_dir"], "workspace", "build"),
        "source_dir": os.path.join(test_env["temp_dir"], "workspace", "source"),
        "task_id": "123"
    }
    mock_workspace_manager.create_workspace.return_value = workspace_mock
    
    # Run the test
    success, job_id, _ = orchestrator.execute("test_profile")
    
    # Verify results
    assert success is True
    assert job_id == "12345"
    mock_config_manager.merge_configs.assert_called_with("test_profile", None)
    
    # Check that task_factory.create_task was called
    orchestrator.task_factory.create_task.assert_called_once()


def test_execute_with_cli_overrides(mock_orchestrator_setup):
    """Test execute with CLI overrides using standardized test data."""
    setup = mock_orchestrator_setup
    orchestrator = setup["orchestrator"]
    mock_config_manager = setup["mock_config_manager"]
    mock_workspace_manager = setup["mock_workspace_manager"]
    test_env = setup["test_env"]
    
    # Set up mock config manager using standardized test structure
    merged_config = {
        "execution": {"type": "local"},
        "task_type": "application",
        "name": "test_profile",
        "template": "hello_world.j2",
        "cli_param": "test_value"
    }
    mock_config_manager.merge_configs.return_value = merged_config
    
    # Set up workspace mock
    workspace_mock = {
        "workspace_dir": os.path.join(test_env["temp_dir"], "workspace"),
        "logs_dir": os.path.join(test_env["temp_dir"], "workspace", "logs"),
        "inputs_dir": os.path.join(test_env["temp_dir"], "workspace", "inputs"),
        "metadata_dir": os.path.join(test_env["temp_dir"], "workspace", ".benchpro"),
        "scripts_dir": os.path.join(test_env["temp_dir"], "workspace", "scripts"),
        "results_dir": os.path.join(test_env["temp_dir"], "workspace", "results"),
        "build_dir": os.path.join(test_env["temp_dir"], "workspace", "build"),
        "source_dir": os.path.join(test_env["temp_dir"], "workspace", "source"),
        "task_id": "123"
    }
    mock_workspace_manager.create_workspace.return_value = workspace_mock
    
    # Run the test
    cli_overrides = {"cli_param": "test_value"}
    success, job_id, _ = orchestrator.execute("test_profile", cli_overrides=cli_overrides)
    
    # Verify results
    assert success is True
    assert job_id == "12345"
    mock_config_manager.merge_configs.assert_called_with("test_profile", cli_overrides)
    
    # Check that task_factory.create_task was called
    orchestrator.task_factory.create_task.assert_called_once()


def test_execute_with_dry_run(mock_orchestrator_setup):
    """Test execute with dry run using standardized test data."""
    setup = mock_orchestrator_setup
    orchestrator = setup["orchestrator"]
    mock_config_manager = setup["mock_config_manager"]
    mock_task = setup["mock_task"]
    
    # Set up mock config manager
    default_config = {
        "execution": {"type": "local"},
        "task_type": "application",
        "template": "hello_world.j2"
    }
    mock_config_manager.get_merged_config.return_value = default_config
    
    # Run the test
    success, job_id, _ = orchestrator.execute("test_profile", dry_run=True)
    
    # Verify results
    assert success is True
    assert job_id is None
    mock_task.run.assert_not_called()


def test_execute_with_scheduler_to_slurm_mapping(mock_orchestrator_setup):
    """Test execute with scheduler configured to use Slurm using standardized test data."""
    setup = mock_orchestrator_setup
    orchestrator = setup["orchestrator"]
    mock_config_manager = setup["mock_config_manager"]
    mock_workspace_manager = setup["mock_workspace_manager"]
    test_env = setup["test_env"]
    
    # Set up mock config manager using standardized test structure
    merged_config = {
        "execution": {"type": "sched"},
        "task_type": "benchmark",
        "name": "test_profile",
        "template": "hello_world.j2"
    }
    mock_config_manager.merge_configs.return_value = merged_config
    
    # Set up workspace mock
    workspace_mock = {
        "workspace_dir": os.path.join(test_env["temp_dir"], "workspace"),
        "logs_dir": os.path.join(test_env["temp_dir"], "workspace", "logs"),
        "inputs_dir": os.path.join(test_env["temp_dir"], "workspace", "inputs"),
        "metadata_dir": os.path.join(test_env["temp_dir"], "workspace", ".benchpro"),
        "scripts_dir": os.path.join(test_env["temp_dir"], "workspace", "scripts"),
        "results_dir": os.path.join(test_env["temp_dir"], "workspace", "results"),
        "build_dir": os.path.join(test_env["temp_dir"], "workspace", "build"),
        "source_dir": os.path.join(test_env["temp_dir"], "workspace", "source"),
        "task_id": "123"
    }
    mock_workspace_manager.create_workspace.return_value = workspace_mock
    
    # Run the test
    success, job_id, _ = orchestrator.execute("test_profile")
    
    # Verify results
    assert success is True
    assert job_id == "12345"
    mock_config_manager.merge_configs.assert_called_with("test_profile", None)
    
    # Check that task_factory.create_task was called
    orchestrator.task_factory.create_task.assert_called_once()


# For backward compatibility with unittest discovery
class TestTaskOrchestrator(unittest.TestCase):
    """Wrapper class for unittest compatibility."""
    
    def test_placeholder(self):
        """Placeholder test for unittest discovery."""
        # All real tests are now pytest functions above
        pass


if __name__ == '__main__':
    unittest.main() 