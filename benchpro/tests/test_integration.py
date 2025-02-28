"""
Integration tests for BenchPRO.

These tests simulate a complete flow from configuration to job script generation.
"""

import os
import pytest
import tempfile
import yaml
import time
import shutil
from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.executor.build_executor import BuildExecutor
from benchpro.executor.task import Application, Benchmark
from benchpro.workspace.workspace_manager import WorkspaceManager


@pytest.fixture
def test_environment():
    """Create a temporary test environment with configuration and template files."""
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
            
        # Create system config
        system_config = {
            "scheduler": {
                "queue": "system_queue",
                "account": "system_account"
            }
        }
        with open(os.path.join(config_dir, "system_default.yaml"), 'w') as f:
            yaml.dump(system_config, f)
            
        # Create application profile
        app_config = {
            "task_type": "application",
            "job": {
                "name": "hello_world_app"
            },
            "scheduler": {
                "time_limit": "00:05:00"
            },
            "template": {
                "base_template": "application_build"
            },
            "application": {
                "name": "hello_world",
                "source_dir": source_dir,
                "build_script": "gcc -o hello_world hello_world.c",
                "output_binary": "hello_world"
            }
        }
        with open(os.path.join(config_dir, "profile_hello_world_app.yaml"), 'w') as f:
            yaml.dump(app_config, f)
            
        # Create benchmark profile
        bench_config = {
            "task_type": "benchmark",
            "job": {
                "name": "hello_world_bench"
            },
            "scheduler": {
                "time_limit": "00:05:00"
            },
            "template": {
                "base_template": "benchmark_run"
            },
            "benchmark": {
                "name": "hello_world",
                "application": "hello_world",
                "input_params": ""
            }
        }
        with open(os.path.join(config_dir, "profile_hello_world_bench.yaml"), 'w') as f:
            yaml.dump(bench_config, f)
            
        # Create application template
        app_template = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --output={{ job.output_dir }}/{{ job.name }}_%j.out
#SBATCH --error={{ job.output_dir }}/{{ job.name }}_%j.err
#SBATCH --time={{ scheduler.time_limit }}
#SBATCH --nodes={{ scheduler.nodes }}
#SBATCH --ntasks-per-node={{ scheduler.tasks_per_node }}
{% if scheduler.queue is defined %}
#SBATCH --partition={{ scheduler.queue }}
{% endif %}
{% if scheduler.account is defined %}
#SBATCH --account={{ scheduler.account }}
{% endif %}

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: {{ job.name }}"
echo "Start Time: $(date)"

# Change to source directory
cd {{ application.source_dir }}

# Build the application
echo "Building application: {{ application.name }}"
{{ application.build_script }}

# Copy the binary to the output directory
cp {{ application.output_binary }} {{ job.output_dir }}/

echo "End Time: $(date)"
echo "Application build completed successfully"
"""
        with open(os.path.join(templates_dir, "application_build.j2"), 'w') as f:
            f.write(app_template)
            
        # Create benchmark template
        bench_template = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --output={{ job.output_dir }}/{{ job.name }}_%j.out
#SBATCH --error={{ job.output_dir }}/{{ job.name }}_%j.err
#SBATCH --time={{ scheduler.time_limit }}
#SBATCH --nodes={{ scheduler.nodes }}
#SBATCH --ntasks-per-node={{ scheduler.tasks_per_node }}
{% if scheduler.queue is defined %}
#SBATCH --partition={{ scheduler.queue }}
{% endif %}
{% if scheduler.account is defined %}
#SBATCH --account={{ scheduler.account }}
{% endif %}

# Job Information
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: {{ job.name }}"
echo "Start Time: $(date)"

# Run the benchmark
echo "Running benchmark: {{ benchmark.name }}"
{{ job.output_dir }}/{{ benchmark.application }} {{ benchmark.input_params }}

echo "End Time: $(date)"
echo "Benchmark run completed successfully"
"""
        with open(os.path.join(templates_dir, "benchmark_run.j2"), 'w') as f:
            f.write(bench_template)
            
        # Create local application template
        local_app_template = """#!/bin/bash
# Local application build script for {{ job.name }}

# Job Information
echo "Job Name: {{ job.name }}"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p {{ job.output_dir }}

# Change to source directory
cd {{ application.source_dir }}

# Build the application
echo "Building application: {{ application.name }}"
{{ application.build_script }}

# Copy the binary to the output directory
cp {{ application.output_binary }} {{ job.output_dir }}/

echo "End Time: $(date)"
echo "Application build completed successfully"
"""
        with open(os.path.join(templates_dir, "application_build_local.j2"), 'w') as f:
            f.write(local_app_template)
            
        # Create local benchmark template
        local_bench_template = """#!/bin/bash
# Local benchmark run script for {{ job.name }}

# Job Information
echo "Job Name: {{ job.name }}"
echo "Start Time: $(date)"

# Create output directory if it doesn't exist
mkdir -p {{ job.output_dir }}

# Run the benchmark
echo "Running benchmark: {{ benchmark.name }}"
{{ job.output_dir }}/{{ benchmark.application }} {{ benchmark.input_params }}

echo "End Time: $(date)"
echo "Benchmark run completed successfully"
"""
        with open(os.path.join(templates_dir, "benchmark_run_local.j2"), 'w') as f:
            f.write(local_bench_template)
            
        # Create a simple C file
        c_file = """#include <stdio.h>
int main() {
    printf("Hello, World!\\n");
    return 0;
}
"""
        with open(os.path.join(source_dir, "hello_world.c"), 'w') as f:
            f.write(c_file)
            
        yield {
            "temp_dir": temp_dir,
            "config_dir": config_dir,
            "templates_dir": templates_dir,
            "output_dir": output_dir,
            "source_dir": source_dir
        }


def test_application_build(test_environment):
    """Test building an application."""
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"], 
        profile_dir=test_environment["config_dir"]
    )
    template_engine = TemplateEngine(test_environment["templates_dir"])
    build_executor = BuildExecutor(config_manager, template_engine)
    
    # Execute the application build with dry run
    success, job_id, script_path = build_executor.execute("hello_world_app", dry_run=True)
    
    # Check that the build was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "#SBATCH --job-name=hello_world_app" in content
    assert "#SBATCH --time=00:05:00" in content
    assert "#SBATCH --partition=system_queue" in content
    assert "#SBATCH --account=system_account" in content
    assert "Building application: hello_world" in content
    assert "gcc -o hello_world hello_world.c" in content


def test_benchmark_run(test_environment):
    """Test running a benchmark."""
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"], 
        profile_dir=test_environment["config_dir"]
    )
    template_engine = TemplateEngine(test_environment["templates_dir"])
    benchmark_executor = BuildExecutor(config_manager, template_engine)
    
    # Execute the benchmark run with dry run
    success, job_id, script_path = benchmark_executor.execute("hello_world_bench", dry_run=True)
    
    # Check that the run was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "#SBATCH --job-name=hello_world_bench" in content
    assert "#SBATCH --time=00:05:00" in content
    assert "#SBATCH --partition=system_queue" in content
    assert "#SBATCH --account=system_account" in content
    assert "Running benchmark: hello_world" in content
    assert "hello_world" in content


def test_local_application_build(test_environment):
    """Test building an application with the local executor."""
    # Initialize components
    config_manager = ConfigManager(test_environment["config_dir"])
    template_engine = TemplateEngine(test_environment["templates_dir"])
    build_executor = BuildExecutor(config_manager, template_engine)
    
    # Create CLI overrides for local execution
    cli_overrides = {
        "execution": {
            "type": "local"
        }
    }
    
    # Execute the application build with dry run
    success, job_id, script_path = build_executor.execute("hello_world_app", cli_overrides, dry_run=True)
    
    # Check that the build was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "# Local application build script for hello_world_app" in content
    assert "#SBATCH" not in content  # No SLURM directives
    assert "Building application: hello_world" in content
    assert "gcc -o hello_world hello_world.c" in content


def test_local_benchmark_run(test_environment):
    """Test running a benchmark with the local executor."""
    # Initialize components
    config_manager = ConfigManager(test_environment["config_dir"])
    template_engine = TemplateEngine(test_environment["templates_dir"])
    build_executor = BuildExecutor(config_manager, template_engine)
    
    # Create CLI overrides for local execution
    cli_overrides = {
        "execution": {
            "type": "local"
        }
    }
    
    # Execute the benchmark run with dry run
    success, job_id, script_path = build_executor.execute("hello_world_bench", cli_overrides, dry_run=True)
    
    # Check that the run was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify key elements in the script
    assert "#!/bin/bash" in content
    assert "# Local benchmark run script for hello_world_bench" in content
    assert "#SBATCH" not in content  # No SLURM directives
    assert "Running benchmark: hello_world" in content
    assert "hello_world" in content


def test_cli_overrides(test_environment):
    """Test that CLI overrides are properly applied."""
    # Initialize components
    config_manager = ConfigManager(test_environment["config_dir"])
    template_engine = TemplateEngine(test_environment["templates_dir"])
    build_executor = BuildExecutor(config_manager, template_engine)
    
    # Create CLI overrides
    cli_overrides = {
        "job": {
            "name": "cli_job"
        },
        "scheduler": {
            "queue": "cli_queue"
        }
    }
    
    # Execute the build with dry run and CLI overrides
    success, job_id, script_path = build_executor.execute("hello_world_app", cli_overrides, dry_run=True)
    
    # Check that the build was successful
    assert success
    assert job_id is None  # No job ID in dry run
    assert os.path.exists(script_path)
    
    # Check the content of the generated script
    with open(script_path, 'r') as f:
        content = f.read()
        
    # Verify that CLI overrides were applied
    assert "#SBATCH --job-name=cli_job" in content
    assert "#SBATCH --partition=cli_queue" in content


def test_end_to_end_local_execution(test_environment):
    """Test end-to-end local execution of application build and benchmark run."""
    # Skip this test if we're in a CI environment
    if os.environ.get("CI") == "true":
        pytest.skip("Skipping end-to-end test in CI environment")
    
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"],
        profile_dir=test_environment["config_dir"]
    )
    template_engine = TemplateEngine(test_environment["templates_dir"])
    build_executor = BuildExecutor(config_manager, template_engine)
    
    # Create CLI overrides for local execution
    cli_overrides = {
        "execution": {
            "type": "local"
        }
    }
    
    # Execute the application build
    success, app_job_id, app_script_path = build_executor.execute("hello_world_app", cli_overrides)
    
    # Check that the build was successful
    assert success
    assert app_job_id is not None
    assert os.path.exists(app_script_path)
    
    # Wait for the build to complete
    time.sleep(2)
    
    # Check that the binary was created
    binary_path = os.path.join(test_environment["output_dir"], "hello_world")
    assert os.path.exists(binary_path)
    
    # Execute the benchmark run
    success, bench_job_id, bench_script_path = build_executor.execute("hello_world_bench", cli_overrides)
    
    # Check that the run was successful
    assert success
    assert bench_job_id is not None
    assert os.path.exists(bench_script_path)
    
    # Wait for the benchmark to complete
    time.sleep(2)


def test_application_class(test_environment):
    """Test the Application class."""
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"], 
        profile_dir=test_environment["config_dir"]
    )
    
    # Create an Application instance
    app = Application(config_manager, "hello_world_app")


def test_benchmark_class(test_environment):
    """Test the Benchmark class."""
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"], 
        profile_dir=test_environment["config_dir"]
    )
    
    # Create a Benchmark instance
    bench = Benchmark(config_manager, "hello_world_bench")


def test_workspace_manager(test_environment):
    """Test the WorkspaceManager class."""
    # Initialize components
    workspace_manager = WorkspaceManager(test_environment["output_dir"])
    
    # Create a workspace
    workspace = workspace_manager.create_workspace("hello_world_app")
    
    # Check that the workspace was created
    assert os.path.exists(workspace["workspace_dir"])
    assert os.path.exists(workspace["source_dir"])
    assert os.path.exists(workspace["build_dir"])
    assert os.path.exists(workspace["logs_dir"])
    assert os.path.exists(workspace["results_dir"])


def test_task_class(test_environment):
    """Test the Task class."""
    # Initialize components
    config_manager = ConfigManager(
        config_dir=test_environment["config_dir"], 
        profile_dir=test_environment["config_dir"]
    )
    template_engine = TemplateEngine(test_environment["templates_dir"]) 