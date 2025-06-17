"""
Tests for the configuration schema.
"""

import pytest
from pydantic import ValidationError

from benchpro.config.schema import ApplicationSchema, BenchmarkSchema


class TestApplicationSchema:
    """Tests for the ApplicationSchema."""
    
    def test_valid_application_config(self):
        """Test that a valid application configuration passes validation."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "test_app",
                "threads": 4
            },
            "environment": {
                "modules": ["gcc/11.2.0"],
                "variables": {
                    "OMP_NUM_THREADS": "4"
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
                "source_dir": "test_source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test_app.j2"
        }
        
        # This should not raise an exception
        app_schema = ApplicationSchema(**config)
        
        # Check that the values are correctly set
        assert app_schema.name == "test_app"
        assert app_schema.version == "1.0"
        assert app_schema.build.compiler == "gcc"
        assert app_schema.environment.modules == ["gcc/11.2.0"]
        assert app_schema.job.scheduler == "slurm"
        assert app_schema.workspace.source_dir == "test_source"
        assert app_schema.template == "test_app.j2"
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        # Missing name
        config = {
            "task_type": "application",
            "version": "1.0",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test_app"
            },
            "workspace": {
                "source_dir": "test_source"
            },
            "template": "test_app.j2"
        }
        
        with pytest.raises(ValidationError):
            ApplicationSchema(**config)
        
        # Missing build
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "workspace": {
                "source_dir": "test_source"
            },
            "template": "test_app.j2"
        }
        
        with pytest.raises(ValidationError):
            ApplicationSchema(**config)
        
        # Missing workspace
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test_app"
            },
            "template": "test_app.j2"
        }
        
        with pytest.raises(ValidationError):
            ApplicationSchema(**config)
        
        # Missing template
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test_app"
            },
            "workspace": {
                "source_dir": "test_source"
            }
        }
        
        with pytest.raises(ValidationError):
            ApplicationSchema(**config)
    
    def test_invalid_task_type(self):
        """Test that an invalid task_type raises a validation error."""
        config = {
            "task_type": "invalid",
            "name": "test_app",
            "version": "1.0",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test_app"
            },
            "workspace": {
                "source_dir": "test_source"
            },
            "template": "test_app.j2"
        }
        
        with pytest.raises(ValidationError):
            ApplicationSchema(**config)
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed and included in the validated model."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test_app",
                "extra_field": "value"  # Extra field in build
            },
            "workspace": {
                "source_dir": "test_source"
            },
            "template": "test_app.j2",
            "extra_field": "value"  # Extra field at top level
        }
        
        # Validate the config - should not raise an error
        validated = ApplicationSchema(**config)
        
        # Check that extra fields are included in the model
        assert validated.extra_field == "value"
        assert validated.build.extra_field == "value"


class TestBenchmarkSchema:
    """Tests for the BenchmarkSchema."""
    
    def test_valid_benchmark_config(self):
        """Test that a valid benchmark configuration passes validation."""
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "description": "Test benchmark",
            "run": {
                "executable": "test_app",
                "arguments": "--verbose",
                "input_files": ["input.dat"],
                "output_files": ["output.dat"],
                "threads": 4
            },
            "requirements": {
                "application": "test_app",
                "version": "1.0"
            },
            "environment": {
                "modules": ["gcc/11.2.0"],
                "variables": {
                    "OMP_NUM_THREADS": "4"
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
                "input_dir": "test_input",
                "output_dir": "output",
                "logs_dir": "logs",
                "keep_input": True,
                "keep_output": True
            },
            "results": {
                "metrics": ["runtime", "memory"],
                "parser": "simple",
                "output_format": "json"
            },
            "template": "test_bench.j2"
        }
        
        # This should not raise an exception
        bench_schema = BenchmarkSchema(**config)
        
        # Check that the values are correctly set
        assert bench_schema.name == "test_bench"
        assert bench_schema.version == "1.0"
        assert bench_schema.run.executable == "test_app"
        assert bench_schema.requirements.application == "test_app"
        assert bench_schema.environment.modules == ["gcc/11.2.0"]
        assert bench_schema.job.scheduler == "slurm"
        assert bench_schema.workspace.input_dir == "test_input"
        assert bench_schema.results.metrics == ["runtime", "memory"]
        assert bench_schema.template == "test_bench.j2"
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        # Missing name
        config = {
            "task_type": "benchmark",
            "version": "1.0",
            "run": {
                "executable": "test_app"
            },
            "workspace": {
                "input_dir": "test_input"
            },
            "template": "test_bench.j2"
        }
        
        with pytest.raises(ValidationError):
            BenchmarkSchema(**config)
        
        # Missing run
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "workspace": {
                "input_dir": "test_input"
            },
            "template": "test_bench.j2"
        }
        
        with pytest.raises(ValidationError):
            BenchmarkSchema(**config)
        
        # Missing workspace
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "run": {
                "executable": "test_app"
            },
            "template": "test_bench.j2"
        }
        
        with pytest.raises(ValidationError):
            BenchmarkSchema(**config)
        
        # Missing template
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "run": {
                "executable": "test_app"
            },
            "workspace": {
                "input_dir": "test_input"
            }
        }
        
        with pytest.raises(ValidationError):
            BenchmarkSchema(**config)
    
    def test_invalid_task_type(self):
        """Test that an invalid task_type raises a validation error."""
        config = {
            "task_type": "invalid",
            "name": "test_bench",
            "version": "1.0",
            "run": {
                "executable": "test_app"
            },
            "workspace": {
                "input_dir": "test_input"
            },
            "template": "test_bench.j2"
        }
        
        with pytest.raises(ValidationError):
            BenchmarkSchema(**config)
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed and included in the validated model."""
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "run": {
                "executable": "test_app",
                "extra_field": "value"  # Extra field in run
            },
            "workspace": {
                "input_dir": "test_input"  # Required field
            },
            "template": "test_bench.j2",
            "extra_field": "value"  # Extra field at top level
        }
        
        # Validate the config - should not raise an error
        validated = BenchmarkSchema(**config)
        
        # Check that extra fields are included in the model
        assert validated.extra_field == "value"
        assert validated.run.extra_field == "value" 