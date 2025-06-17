"""
Integration tests for the template system with the task composition architecture.

This module tests the template system integration using standardized test data
and fixtures for consistency and maintainability.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import pytest

from benchpro.executor.task_factory import TaskFactory
from benchpro.config.config_manager import ConfigManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.templates.script_generators import (
    LocalScriptGenerator, SlurmScriptGenerator
)
from benchpro.tests.fixtures.test_data import get_standard_application_profile, get_standard_benchmark_profile, get_standard_system_data


@pytest.fixture
def task_factory_with_mocks():
    """Create a TaskFactory with mocked dependencies for testing."""
    # Create mock dependencies with proper specs
    mock_config_manager = MagicMock(spec=ConfigManager)
    mock_registry_manager = MagicMock(spec=RegistryManager)
    
    # Initialize the TaskFactory with proper dependency injection
    factory = TaskFactory(
        config_manager=mock_config_manager,
        registry_manager=mock_registry_manager
    )
    
    return factory, mock_config_manager, mock_registry_manager


def test_create_task_with_local_execution(task_factory_with_mocks):
    """Test creating a task with local execution using standardized data."""
    factory, mock_config_manager, mock_registry_manager = task_factory_with_mocks
    
    # Use standardized test profile with local execution
    config = get_standard_application_profile("test_app")
    config.setdefault("execution", {})["type"] = "local"  # Set execution type for TaskFactory
    config.setdefault("job", {})["scheduler"] = "local"   # Set scheduler for script directives
    
    # Create the task
    task = factory.create_task(config)
    
    # Check task type and components
    assert task.__class__.__name__ == "Application"
    assert isinstance(task.script_generation_component, LocalScriptGenerator)


def test_create_task_with_slurm_execution(task_factory_with_mocks):
    """Test creating a task with SLURM execution using standardized data."""
    factory, mock_config_manager, mock_registry_manager = task_factory_with_mocks
    
    # Use standardized test profile with SLURM execution
    config = get_standard_application_profile("test_app")
    config.setdefault("execution", {})["type"] = "sched"  # Set execution type for TaskFactory
    config.setdefault("job", {})["scheduler"] = "slurm"   # Set scheduler for script directives
    
    # Create the task
    task = factory.create_task(config)
    
    # Check task type and components
    assert task.__class__.__name__ == "Application"
    assert isinstance(task.script_generation_component, SlurmScriptGenerator)


def test_end_to_end_script_generation(standardized_test_env, task_factory_with_mocks):
    """Test end-to-end script generation with different execution contexts."""
    factory, mock_config_manager, mock_registry_manager = task_factory_with_mocks
    
    # Create workspace directories
    workspace_dir = os.path.join(standardized_test_env["temp_dir"], "workspace")
    logs_dir = os.path.join(workspace_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Prepare configurations using standardized profiles
    local_config = get_standard_application_profile("test_app")
    local_config.update({
        "execution": {"type": "local"},  # Set execution type for TaskFactory
        "job": {"scheduler": "local"},   # Set scheduler for script directives
        "system": get_standard_system_data(),
        "workspace": {
            "workspace_dir": workspace_dir,
            "logs_dir": logs_dir
        }
    })
    
    slurm_config = get_standard_application_profile("test_app")
    slurm_config.update({
        "execution": {"type": "sched"},  # Set execution type for TaskFactory
        "job": {
            "scheduler": "slurm",        # Set scheduler for script directives
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "01:00:00",
            "queue": "test_queue"
        },
        "system": get_standard_system_data(),
        "workspace": {
            "workspace_dir": workspace_dir,
            "logs_dir": logs_dir
        }
    })
    
    # Create tasks
    local_task = factory.create_task(local_config)
    slurm_task = factory.create_task(slurm_config)
    
    # Generate script paths
    local_script_path = os.path.join(workspace_dir, "local_app_build.sh")
    slurm_script_path = os.path.join(workspace_dir, "slurm_app_build.sh")
    
    # Use standardized templates that are already created by the fixture
    local_template_path = os.path.join(standardized_test_env["inputs_app_dir"], "hello_world.j2")
    slurm_template_path = os.path.join(standardized_test_env["inputs_app_dir"], "hello_world.j2")
    
    # Mock file operations to avoid permission issues
    with patch('os.chmod'), patch('os.makedirs'):
        # Generate scripts
        local_task.generate_script(local_template_path, local_script_path)
        slurm_task.generate_script(slurm_template_path, slurm_script_path)
        
    # Read the generated scripts
    with open(local_script_path, "r") as f:
        local_script_content = f.read()
    
    with open(slurm_script_path, "r") as f:
        slurm_script_content = f.read()
        
    # Check that the scripts contain the expected content
    assert "Building application" in local_script_content
    assert "Building application" in slurm_script_content
    assert "#SBATCH" in slurm_script_content
    assert "#SBATCH" not in local_script_content
        

def test_task_factory_handles_missing_scheduler_gracefully(task_factory_with_mocks):
    """Test that TaskFactory defaults to local execution when scheduler is missing."""
    factory, mock_config_manager, mock_registry_manager = task_factory_with_mocks
    
    # Use standardized profile without explicit scheduler
    config = get_standard_application_profile("test_app")
    if "scheduler" in config.get("job", {}):
        del config["job"]["scheduler"]
    
    # Create the task
    task = factory.create_task(config)
    
    # Should default to local execution
    assert isinstance(task.script_generation_component, LocalScriptGenerator)
    

def test_benchmark_task_creation_with_template_system(task_factory_with_mocks):
    """Test creating benchmark tasks with the template system."""
    factory, mock_config_manager, mock_registry_manager = task_factory_with_mocks
    
    # Use standardized benchmark profile
    config = get_standard_benchmark_profile("test_benchmark")
    config.setdefault("execution", {})["type"] = "sched"  # Set execution type for TaskFactory
    config.setdefault("job", {})["scheduler"] = "slurm"   # Set scheduler for script directives
    
    # Create the task
    task = factory.create_task(config)
    
    # Verify benchmark task and slurm components
    assert task.__class__.__name__ == "Benchmark"
    assert isinstance(task.script_generation_component, SlurmScriptGenerator)


# For backward compatibility with unittest discovery
class TestTaskFactoryIntegration(unittest.TestCase):
    """Wrapper class for unittest compatibility."""
    
    def test_placeholder(self):
        """Placeholder test for unittest discovery."""
        # All real tests are now pytest functions above
        pass


if __name__ == '__main__':
    unittest.main() 