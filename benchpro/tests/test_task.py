"""
Tests for the Task classes.
"""

import os
import pytest
import tempfile
import yaml
from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.task import Task, Application, Benchmark, TaskFactory
from benchpro.registry.registry_manager import RegistryManager


def test_task_factory():
    """Test the TaskFactory."""
    factory = TaskFactory()
    
    # Test creating an application task
    app_task = factory.create_task("application")
    assert isinstance(app_task, Application)
    
    # Test creating a benchmark task
    bench_task = factory.create_task("benchmark")
    assert isinstance(bench_task, Benchmark)
    
    # Test invalid task type
    with pytest.raises(ValueError):
        factory.create_task("invalid")


def test_application_validate_config():
    """Test application config validation."""
    # Create a Task instance
    task = Task()
    
    # Valid application config
    valid_config = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "workspace": {
            "source_dir": "/tmp",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    }
    
    # Test valid config
    assert task.validate_config(valid_config) is not None
    
    # Invalid config (missing required field)
    invalid_config = valid_config.copy()
    del invalid_config["name"]
    
    with pytest.raises(ValueError):
        task.validate_config(invalid_config)
    
    # Invalid config (wrong task type)
    wrong_type_config = valid_config.copy()
    wrong_type_config["task_type"] = "benchmark"
    
    with pytest.raises(ValueError):
        task.validate_config(wrong_type_config)
    
    # Test handling of None config
    with pytest.raises(ValueError):
        task.validate_config(None)


def test_benchmark_validate_config():
    """Test benchmark config validation."""
    # Create a Task instance
    task = Task()
    
    # Valid benchmark config
    valid_config = {
        "task_type": "benchmark",
        "name": "test_bench",
        "version": "1.0",
        "run": {
            "application": "test_app",
            "arguments": "-n 10",
            "input_files": [],
            "output_files": [],
            "threads": 1
        },
        "workspace": {
            "input_dir": "input",
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        },
        "template": "hello_world.j2"
    }
    
    # Test valid config
    result = task.validate_config(valid_config)
    assert result is not None  # It should return a validated config dictionary
    
    # Invalid config (missing required field)
    invalid_config = valid_config.copy()
    del invalid_config["name"]
    
    with pytest.raises(ValueError):
        task.validate_config(invalid_config)
    
    # Invalid config (wrong task type)
    wrong_type_config = valid_config.copy()
    wrong_type_config["task_type"] = "application"
    
    with pytest.raises(ValueError):
        task.validate_config(wrong_type_config)
    
    # Test handling of None config
    with pytest.raises(ValueError):
        task.validate_config(None)


def test_application_execute(setup_test_env, monkeypatch, temp_registry):
    """Test application execution."""
    # Mock the executor submit_job method to avoid actual job submission
    def mock_submit_job(self, script_path):
        """Mock job submission."""
        return True, "test_job_id"
    
    # Apply the mock
    monkeypatch.setattr("benchpro.executor.executor.LocalExecutor.submit_job", mock_submit_job)
    
    config_manager = ConfigManager(
        config_dir=setup_test_env["config_dir"], 
        profile_dir=setup_test_env["config_dir"]
    )
    template_engine = TemplateEngine(setup_test_env["templates_dir"])
    
    # Create a test application profile
    app_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "build": {
            "source": "hello_world.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "nodes": 1,
            "time_limit": "01:00:00"
        },
        "workspace": {
            "source_dir": setup_test_env["inputs_source_dir"],
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "hello_world.j2"
    }
    
    # Write the app profile to a file
    app_profile_path = os.path.join(setup_test_env["config_dir"], "test_app.yaml")
    with open(app_profile_path, "w") as f:
        yaml.dump(app_profile, f)
    
    # Verify source file exists
    source_file = os.path.join(setup_test_env["inputs_source_dir"], "hello_world.c")
    if not os.path.exists(source_file):
        # Create a simple C file if it doesn't exist
        with open(source_file, "w") as f:
            f.write("""#include <stdio.h>
int main() {
    printf("Hello, World!\\n");
    return 0;
}
""")
    
    # Create application task
    app_task = Application(config_manager, template_engine)
    
    # Execute the application build with dry run
    success, job_id, script_path = app_task.execute("test_app", dry_run=True)
    
    # Check the results
    assert success is True
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Validate the generated script
    with open(script_path, "r") as f:
        script_content = f.read()
        
    assert "#!/bin/bash" in script_content
    assert "gcc -O2" in script_content
    assert "hello_world.c" in script_content


def test_benchmark_execute(setup_test_env, temp_registry):
    """Test benchmark execution."""
    config_manager = ConfigManager(
        config_dir=setup_test_env["config_dir"], 
        profile_dir=setup_test_env["config_dir"]
    )
    template_engine = TemplateEngine(setup_test_env["templates_dir"])
    
    # Create a test benchmark profile
    benchmark_profile = {
        "task_type": "benchmark",
        "name": "test_bench",
        "version": "1.0",
        "run": {
            "application": "test_app",
            "arguments": "-n 10",
            "input_files": [],
            "output_files": [],
            "threads": 1
        },
        "template": "hello_world.j2",
        "workspace": {
            "input_dir": setup_test_env["inputs_dir"],
            "output_dir": "output",
            "logs_dir": "logs",
            "keep_input": True,
            "keep_output": True
        }
    }
    
    # Write the benchmark profile to a file
    benchmark_profile_path = os.path.join(setup_test_env["config_dir"], "test_bench.yaml")
    with open(benchmark_profile_path, "w") as f:
        yaml.dump(benchmark_profile, f)
    
    # Register a test application using the temp_registry
    app_data = {
        "name": "test_app",
        "version": "1.0",
        "workspace_dir": setup_test_env["temp_dir"],
        "binary_path": os.path.join(setup_test_env["outputs_dir"], "test_app"),
        "build_parameters": {},
        "metadata": {
            "description": "Test application",
            "tags": ["test"]
        }
    }
    temp_registry.register_application(app_data)
    
    # Create benchmark task with the temp_registry
    bench_task = Benchmark(config_manager, template_engine, registry_manager=temp_registry)
    
    # Execute the benchmark run with dry run
    success, job_id, script_path = bench_task.execute("test_bench", dry_run=True)
    
    # Check that the run was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "Hello World benchmark run script" in content
    assert "Job Name: test_bench" in content
    assert "Running application:" in content
    assert "Starting benchmark run..." in content 