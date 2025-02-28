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


@pytest.fixture
def temp_task_env():
    """Create a temporary environment with test configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create config directory
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create templates directory
        templates_dir = os.path.join(temp_dir, "templates")
        os.makedirs(templates_dir, exist_ok=True)
        
        # Create output directory
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create source directory
        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir, exist_ok=True)
        
        # Create default config
        default_config = {
            "job": {
                "name": "default_job",
                "output_dir": output_dir
            },
            "scheduler": {
                "type": "slurm",
                "queue": "default",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00"
            }
        }
        with open(os.path.join(config_dir, "default.yaml"), 'w') as f:
            yaml.dump(default_config, f)
            
        # Create application profile
        app_config = {
            "task_type": "application",
            "job": {
                "name": "test_app"
            },
            "application": {
                "name": "test_app",
                "source_dir": source_dir,
                "build_script": "gcc -o test_app test_app.c",
                "output_binary": "test_app"
            }
        }
        with open(os.path.join(config_dir, "profile_test_app.yaml"), 'w') as f:
            yaml.dump(app_config, f)
            
        # Create benchmark profile
        bench_config = {
            "task_type": "benchmark",
            "job": {
                "name": "test_bench"
            },
            "benchmark": {
                "name": "test_bench",
                "application": "test_app",
                "input_params": "-n 10"
            }
        }
        with open(os.path.join(config_dir, "profile_test_bench.yaml"), 'w') as f:
            yaml.dump(bench_config, f)
            
        # Create application template
        app_template = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
echo "Building {{ application.name }}"
{{ application.build_script }}
"""
        with open(os.path.join(templates_dir, "application_build.j2"), 'w') as f:
            f.write(app_template)
            
        # Create benchmark template
        bench_template = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
echo "Running {{ benchmark.name }}"
{{ job.output_dir }}/{{ benchmark.application }} {{ benchmark.input_params }}
"""
        with open(os.path.join(templates_dir, "benchmark_run.j2"), 'w') as f:
            f.write(bench_template)
            
        # Create a simple C file
        c_file = """#include <stdio.h>
int main() {
    printf("Hello, World!\\n");
    return 0;
}
"""
        with open(os.path.join(source_dir, "test_app.c"), 'w') as f:
            f.write(c_file)
            
        yield {
            "temp_dir": temp_dir,
            "config_dir": config_dir,
            "templates_dir": templates_dir,
            "output_dir": output_dir,
            "source_dir": source_dir
        }


def test_task_factory():
    """Test the TaskFactory."""
    app_task = TaskFactory.create_task("application")
    assert isinstance(app_task, Application)
    
    bench_task = TaskFactory.create_task("benchmark")
    assert isinstance(bench_task, Benchmark)
    
    with pytest.raises(ValueError):
        TaskFactory.create_task("invalid_type")


def test_application_validate_config():
    """Test validating an application configuration."""
    app_task = Application()
    
    # Valid config
    valid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"},
        "application": {
            "source_dir": "/path/to/source",
            "build_script": "make",
            "output_binary": "app"
        }
    }
    errors = app_task.validate_config(valid_config)
    assert len(errors) == 0
    
    # Invalid config - missing application section
    invalid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"}
    }
    errors = app_task.validate_config(invalid_config)
    assert len(errors) > 0
    assert any("Missing required configuration section: application" in error for error in errors)
    
    # Invalid config - missing required application fields
    invalid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"},
        "application": {}
    }
    errors = app_task.validate_config(invalid_config)
    assert len(errors) > 0
    assert any("Missing required application configuration: source_dir" in error for error in errors)
    assert any("Missing required application configuration: build_script" in error for error in errors)
    assert any("Missing required application configuration: output_binary" in error for error in errors)


def test_benchmark_validate_config():
    """Test validating a benchmark configuration."""
    bench_task = Benchmark()
    
    # Valid config
    valid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"},
        "benchmark": {
            "application": "test_app",
            "input_params": "-n 10"
        }
    }
    errors = bench_task.validate_config(valid_config)
    assert len(errors) == 0
    
    # Invalid config - missing benchmark section
    invalid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"}
    }
    errors = bench_task.validate_config(invalid_config)
    assert len(errors) > 0
    assert any("Missing required configuration section: benchmark" in error for error in errors)
    
    # Invalid config - missing required benchmark fields
    invalid_config = {
        "job": {"name": "test"},
        "scheduler": {"type": "slurm"},
        "benchmark": {}
    }
    errors = bench_task.validate_config(invalid_config)
    assert len(errors) > 0
    assert any("Missing required benchmark configuration: application" in error for error in errors)


def test_application_execute(temp_task_env, monkeypatch):
    """Test executing an application build."""
    # Mock the submit_job method to avoid actual job submission
    def mock_submit_job(self, script_path):
        return True, "12345"
    
    monkeypatch.setattr(Task, "submit_job", mock_submit_job)
    
    # Initialize components
    config_manager = ConfigManager(
        config_dir=temp_task_env["config_dir"], 
        profile_dir=temp_task_env["config_dir"]
    )
    template_engine = TemplateEngine(temp_task_env["templates_dir"])
    app_task = Application(config_manager, template_engine)
    
    # Execute the application build with dry run
    success, job_id, script_path = app_task.execute("test_app", dry_run=True)
    
    # Check that the build was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "#SBATCH --job-name=test_app" in content
    assert "Building test_app" in content
    assert "gcc -o test_app test_app.c" in content


def test_benchmark_execute(temp_task_env, monkeypatch):
    """Test executing a benchmark run."""
    # Mock the submit_job method to avoid actual job submission
    def mock_submit_job(self, script_path):
        return True, "67890"
    
    monkeypatch.setattr(Task, "submit_job", mock_submit_job)
    
    # Initialize components
    config_manager = ConfigManager(
        config_dir=temp_task_env["config_dir"], 
        profile_dir=temp_task_env["config_dir"]
    )
    template_engine = TemplateEngine(temp_task_env["templates_dir"])
    bench_task = Benchmark(config_manager, template_engine)
    
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
    assert "#SBATCH --job-name=test_bench" in content
    assert "Running test_bench" in content
    assert "test_app -n 10" in content 