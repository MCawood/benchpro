"""
Global pytest fixtures for BenchPRO tests.
"""

import os
import tempfile
import shutil
import pytest
from benchpro.registry.registry_manager import RegistryManager
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.utils.user_dir import user_dir_manager
import yaml


@pytest.fixture(scope="session")
def global_temp_dir():
    """Create a temporary directory for the entire test session."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_registry(global_temp_dir):
    """Create a temporary registry file that will be used for all tests."""
    registry_path = os.path.join(global_temp_dir, "registry.yaml")
    
    # Create a registry manager with the temporary path
    registry_manager = RegistryManager(registry_path)
    
    # Return the registry manager with the temporary path
    yield registry_manager


class TestWorkspaceManager(WorkspaceManager):
    """A workspace manager that tracks created workspaces for cleanup."""
    
    def __init__(self):
        """Initialize the TestWorkspaceManager."""
        super().__init__()
        self.created_workspaces = []
        
    def create_workspace(self, task_name, task_type=None):
        """
        Create a workspace and track it for cleanup.
        
        Args:
            task_name: Name of the task.
            task_type: Type of the task (application or benchmark).
            
        Returns:
            Dictionary with workspace paths.
        """
        workspace = super().create_workspace(task_name, task_type)
        self.created_workspaces.append(workspace["workspace_dir"])
        return workspace
        
    def cleanup(self):
        """Clean up all workspaces created by this manager."""
        for workspace_dir in self.created_workspaces:
            if os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir)
        self.created_workspaces = []


@pytest.fixture
def temp_workspace_manager():
    """Create a workspace manager that tracks and cleans up workspaces."""
    manager = TestWorkspaceManager()
    yield manager
    manager.cleanup()


@pytest.fixture(autouse=True)
def cleanup_test_workspaces():
    """Clean up any workspaces after each test."""
    # This is now handled by the test_environment fixture that resets and cleans up
    # the test directories. Tests that need specific workspaces should create them
    # in their own fixture or in the test itself.
    yield


@pytest.fixture
def setup_test_env():
    """
    Create a standardized test environment with necessary directories and example files.
    This is the single source of truth for test environment setup.
    """
    # Create a consistent temporary directory - use /tmp/benchpro_test if possible
    temp_dir = "/tmp/benchpro_test"
    if not os.access("/tmp", os.W_OK):
        # Fall back to a system-generated temp dir if /tmp isn't writable
        temp_dir = tempfile.mkdtemp(prefix="benchpro_test_")
    
    # Remove any existing test directory to start fresh
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    os.makedirs(temp_dir, exist_ok=True)
    
    # Configure user_dir_manager to use test directories
    # This will create the directory structure and copy example files
    user_dir_manager.set_test_environment(temp_dir)
    
    # Create a dictionary of paths to return to the test
    test_env = {
        "temp_dir": temp_dir,
        "config_dir": os.path.join(temp_dir, "config"),
        "inputs_dir": os.path.join(temp_dir, "inputs"),
        "inputs_app_dir": os.path.join(temp_dir, "inputs", "application"),
        "inputs_bench_dir": os.path.join(temp_dir, "inputs", "benchmark"),
        "inputs_source_dir": os.path.join(temp_dir, "inputs", "source"),
        "outputs_dir": os.path.join(temp_dir, "outputs"),
        "outputs_app_dir": os.path.join(temp_dir, "outputs", "application"),
        "outputs_bench_dir": os.path.join(temp_dir, "outputs", "benchmark"),
        "templates_dir": os.path.join(temp_dir, "inputs"),  # Templates are in inputs directory
        "registry_dir": os.path.join(temp_dir, "registry"),  # Add registry_dir
    }
    
    # Create config directory and add default config files
    os.makedirs(test_env["config_dir"], exist_ok=True)
    
    # Create a default config
    default_config = {
        "job": {
            "name": "default_job"
        },
        "scheduler": {
            "type": "slurm",
            "queue": "default",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "01:00:00"
        }
    }
    
    # Write default config to file
    with open(os.path.join(test_env["config_dir"], "default.yaml"), "w") as f:
        yaml.dump(default_config, f)
    
    # Add system default config
    system_config = {
        "system": {
            "name": "test_system",
            "scheduler": {
                "type": "slurm"
            }
        }
    }
    
    # Write system config to file
    with open(os.path.join(test_env["config_dir"], "system_default.yaml"), "w") as f:
        yaml.dump(system_config, f)
    
    # Create application and benchmark directories for templates if they don't exist
    os.makedirs(test_env["inputs_app_dir"], exist_ok=True)
    os.makedirs(test_env["inputs_bench_dir"], exist_ok=True)
    os.makedirs(test_env["inputs_source_dir"], exist_ok=True)
    os.makedirs(test_env["registry_dir"], exist_ok=True)  # Create registry directory
    
    # If hello_world templates don't exist, create them
    for template_dir, template_name in [(test_env["inputs_app_dir"], "hello_world.j2"), 
                                      (test_env["inputs_bench_dir"], "hello_world.j2")]:
        template_path = os.path.join(template_dir, template_name)
        if not os.path.exists(template_path):
            # Only create if copying from examples didn't work
            with open(template_path, "w") as f:
                if "app" in template_dir:
                    f.write("""#!/bin/bash
# Hello World application build script
echo "Job Name: {{ name }}"
echo "Building application"
{{ build.compiler }} {{ build.flags }} -o {{ build.output }} {{ build.source }}
""")
                else:
                    f.write("""#!/bin/bash
# Hello World benchmark run script
echo "Job Name: {{ name }}"
echo "Running application: {{ application }}"
echo "Starting benchmark run..."
{{ application_binary }} {{ run_parameters }}
echo "Benchmark completed."
""")
    
    # Create a sample source file if it doesn't exist
    source_file = os.path.join(test_env["inputs_source_dir"], "hello_world.c")
    if not os.path.exists(source_file):
        with open(source_file, "w") as f:
            f.write("""#include <stdio.h>
int main() {
    printf("Hello, world!\\n");
    return 0;
}
""")
    
    yield test_env
    
    # Reset the user_dir_manager to use original paths
    user_dir_manager.reset_test_environment()
    
    # Clean up temporary directory but leave it for debugging if needed
    # Comment this out if you want to examine the test files after running
    # shutil.rmtree(temp_dir) 