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
from typing import Dict


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


def create_isolated_test_env(base_name="benchpro_test"):
    """
    Create an isolated test environment with a unique directory.
    
    Args:
        base_name: Base name for the test directory
        
    Returns:
        Path to the created test directory
    """
    # Create a consistent temporary directory with the provided base name
    temp_dir = f"/tmp/{base_name}"
    if not os.access("/tmp", os.W_OK):
        # Fall back to a system-generated temp dir if /tmp isn't writable
        temp_dir = tempfile.mkdtemp(prefix=f"{base_name}_")
    
    # Remove any existing test directory to start fresh
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    os.makedirs(temp_dir, exist_ok=True)
    
    # Return the created directory
    return temp_dir


@pytest.fixture
def setup_test_env():
    """
    Create a standardized test environment with necessary directories and example files.
    
    IMPORTANT: This fixture ensures tests are completely isolated from the user's actual
    ~/.benchpro directory to avoid any interference with user files. All tests should use
    this fixture or create similarly isolated environments to prevent:
      1. Modification of user's real configuration files
      2. Loss of user changes when tests run
      3. Non-isolated test environments affecting each other
      4. Tests behaving differently based on existing user configuration
    """
    # Create an isolated test environment
    temp_dir = create_isolated_test_env("benchpro_test")
    
    # Configure user_dir_manager to use test directories
    # This will create the directory structure and copy example files
    user_dir_manager.set_test_environment(temp_dir)
    
    # Check that we're actually using an isolated environment, not user's real ~/.benchpro
    real_benchpro_path = os.path.expanduser("~/.benchpro")
    if user_dir_manager.get_path("root") == real_benchpro_path:
        print(f"WARNING: Test may be using real user directory {real_benchpro_path} instead of isolated test environment!")
        print(f"Tests should NEVER modify the user's real ~/.benchpro directory.")
        # We use print as a fallback in case the logger isn't set up at this point
    
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
            "name": "default_job",
            "scheduler": "slurm",
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
            "job": {
                "scheduler": "slurm"
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
    
    # Create test_app profile in application directory - needed by many tests
    test_app_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application",
        "build": {
            "source": "test_app.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": ["gcc/11.2.0"],
            "variables": {
                "OMP_NUM_THREADS": "1"
            }
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    }

    with open(os.path.join(test_env["inputs_app_dir"], "test_app.yaml"), "w") as f:
        yaml.dump(test_app_profile, f)
    
    # Create test_benchmark profile in benchmark directory - needed by many tests
    test_benchmark_profile = {
        "task_type": "benchmark",
        "name": "test_benchmark",
        "version": "1.0",
        "description": "Test benchmark",
        "run": {
            "executable": "test_app",
            "arguments": "--test",
            "input_files": ["input.dat"],
            "output_files": ["output.dat"],
            "threads": 1
        },
        "requirements": {
            "application": "test_app",
            "version": "1.0"
        },
        "environment": {
            "modules": ["gcc/11.2.0"],
            "variables": {
                "OMP_NUM_THREADS": "1"
            }
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:10:00"
        },
        "workspace": {
            "input_dir": "input",
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
        "template": "hello_world.j2"
    }

    with open(os.path.join(test_env["inputs_bench_dir"], "test_benchmark.yaml"), "w") as f:
        yaml.dump(test_benchmark_profile, f)
    
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


# ==========================================
# NEW STANDARDIZED FIXTURES
# ==========================================

@pytest.fixture(scope="session")
def isolated_user_dir():
    """
    Create an isolated UserDirectoryManager for testing.
    
    This fixture ensures tests don't interfere with the user's actual
    BenchPRO directory.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a UserDirectoryManager that points to the temp directory
        from benchpro.utils.user_dir import UserDirectoryManager
        isolated_manager = UserDirectoryManager(base_dir=temp_dir)
        
        # Ensure the required directory structure exists
        isolated_manager.initialize_user_directories()
        
        yield isolated_manager
        
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def standardized_test_env():
    """
    Set up a complete test environment with standardized test data.
    
    This fixture creates a temporary directory structure with all the
    standard profiles, templates, and configurations needed for testing.
    
    Use this fixture for new tests that want consistent, comprehensive test data.
    """
    from benchpro.tests.fixtures.setup import setup_complete_test_environment
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Configure user_dir_manager for testing
        user_dir_manager.set_test_environment(temp_dir)
        
        # Create directory structure
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
            "templates_dir": os.path.join(temp_dir, "inputs"),
            "registry_dir": os.path.join(temp_dir, "registry"),
        }
        
        # Create all directories
        for dir_path in test_env.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Set up complete test environment with standardized data
        setup_complete_test_environment(test_env)
        
        # Copy examples from the main examples directory if available
        # This preserves backward compatibility with existing tests
        _copy_examples_if_available(test_env)
        
        yield test_env
        
    finally:
        # Reset the user_dir_manager
        user_dir_manager.reset_test_environment()
        
        # Clean up temporary directory
        # Uncomment this line if you want to examine test files after running
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def minimal_test_env():
    """
    Set up a minimal test environment with only essential test data.
    
    This fixture is useful for tests that don't need the full set of
    test data and want faster setup.
    """
    from benchpro.tests.fixtures.setup import setup_minimal_test_environment
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Configure user_dir_manager for testing
        user_dir_manager.set_test_environment(temp_dir)
        
        # Create directory structure
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
            "templates_dir": os.path.join(temp_dir, "inputs"),
            "registry_dir": os.path.join(temp_dir, "registry"),
        }
        
        # Create all directories
        for dir_path in test_env.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Set up minimal test environment
        setup_minimal_test_environment(test_env)
        
        yield test_env
        
    finally:
        # Reset the user_dir_manager
        user_dir_manager.reset_test_environment()
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config_test_env():
    """
    Set up a test environment specifically for configuration tests.
    
    This fixture creates all the profiles and templates needed for
    configuration-related tests.
    """
    from benchpro.tests.fixtures.setup import setup_config_test_environment
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Configure user_dir_manager for testing
        user_dir_manager.set_test_environment(temp_dir)
        
        # Create directory structure
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
            "templates_dir": os.path.join(temp_dir, "inputs"),
            "registry_dir": os.path.join(temp_dir, "registry"),
        }
        
        # Create all directories
        for dir_path in test_env.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Set up config test environment
        setup_config_test_environment(test_env)
        
        yield test_env
        
    finally:
        # Reset the user_dir_manager
        user_dir_manager.reset_test_environment()
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def orchestrator_test_env():
    """
    Set up a test environment specifically for orchestrator tests.
    
    This fixture creates all the profiles and templates needed for
    orchestrator-related tests.
    """
    from benchpro.tests.fixtures.setup import setup_orchestrator_test_environment
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Configure user_dir_manager for testing
        user_dir_manager.set_test_environment(temp_dir)
        
        # Create directory structure
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
            "templates_dir": os.path.join(temp_dir, "inputs"),
            "registry_dir": os.path.join(temp_dir, "registry"),
        }
        
        # Create all directories
        for dir_path in test_env.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Set up orchestrator test environment
        setup_orchestrator_test_environment(test_env)
        
        yield test_env
        
    finally:
        # Reset the user_dir_manager
        user_dir_manager.reset_test_environment()
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def _copy_examples_if_available(test_env: Dict[str, str]) -> None:
    """
    Copy examples from the main examples directory if available.
    
    This preserves backward compatibility with existing tests that
    might expect certain example files to be present.
    
    Args:
        test_env: Test environment dictionary with directory paths.
    """
    try:
        # Try to find the examples directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        examples_dir = os.path.join(project_root, "examples")
        
        if os.path.exists(examples_dir):
            # Copy application examples
            app_examples_dir = os.path.join(examples_dir, "inputs", "application")
            if os.path.exists(app_examples_dir):
                for item in os.listdir(app_examples_dir):
                    src_path = os.path.join(app_examples_dir, item)
                    dst_path = os.path.join(test_env["inputs_app_dir"], item)
                    if os.path.isfile(src_path) and not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
            
            # Copy benchmark examples
            bench_examples_dir = os.path.join(examples_dir, "inputs", "benchmark")
            if os.path.exists(bench_examples_dir):
                for item in os.listdir(bench_examples_dir):
                    src_path = os.path.join(bench_examples_dir, item)
                    dst_path = os.path.join(test_env["inputs_bench_dir"], item)
                    if os.path.isfile(src_path) and not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
            
            # Copy source examples
            source_examples_dir = os.path.join(examples_dir, "inputs", "source")
            if os.path.exists(source_examples_dir):
                for item in os.listdir(source_examples_dir):
                    src_path = os.path.join(source_examples_dir, item)
                    dst_path = os.path.join(test_env["inputs_source_dir"], item)
                    if os.path.isfile(src_path) and not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
    
    except Exception:
        # If copying examples fails, that's OK - we have our standardized data
        pass


# ==========================================
# SLURM TESTING FIXTURES
# ==========================================

@pytest.fixture
def mock_slurm_basic():
    """
    Basic mock SLURM system for simple tests.
    
    This fixture provides a lightweight mock SLURM system for tests that don't
    need the full integration environment.
    """
    from benchpro.tests.fixtures.mock_slurm import create_mock_slurm_system
    system = create_mock_slurm_system(auto_progress_jobs=True, job_run_time=0.05)
    yield system
    system.stop()


@pytest.fixture  
def slurm_patched(mock_slurm_basic):
    """
    Automatically patch subprocess calls for SLURM commands.
    
    This fixture makes it easy to test SLURM functionality without manual patching.
    """
    from benchpro.tests.fixtures.mock_slurm import patch_slurm_commands
    with patch_slurm_commands(mock_slurm_basic):
        yield mock_slurm_basic


@pytest.fixture
def slurm_with_standardized_env(standardized_test_env, mock_slurm_basic):
    """
    Combine standardized test environment with mock SLURM system.
    
    This fixture provides both the full standardized test data and 
    a mock SLURM system for comprehensive testing.
    """
    from benchpro.tests.fixtures.mock_slurm import patch_slurm_commands
    
    test_env = standardized_test_env.copy()
    test_env["mock_slurm"] = mock_slurm_basic
    
    with patch_slurm_commands(mock_slurm_basic):
        yield test_env 