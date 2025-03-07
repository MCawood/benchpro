"""
Tests for the configuration validator.
"""

import os
import pytest
import tempfile
import yaml
import json

from benchpro.config.validator import ConfigValidator


class TestConfigValidator:
    """Tests for the ConfigValidator."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.validator = ConfigValidator()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def teardown_method(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()
    
    def test_validate_application_config(self):
        """Test validating an application configuration."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "test_app"
            },
            "environment": {
                "modules": ["gcc/9.3.0"],
                "variables": {
                    "OMP_NUM_THREADS": "1"
                }
            },
            "job": {
                "scheduler": "slurm",
                "queue": "compute",
                "account": "test_account",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "00:10:00"
            },
            "workspace": {
                "source_dir": "/path/to/source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "application.j2"
        }
        
        # This should not raise an exception
        validated_config = self.validator.validate(config)
        
        # Check that the values are correctly set
        assert validated_config["task_type"] == "application"
        assert validated_config["name"] == "test_app"
        assert validated_config["version"] == "1.0"
        assert validated_config["build"]["compiler"] == "gcc"
    
    def test_validate_benchmark_config(self):
        """Test validating a benchmark configuration."""
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "run": {
                "application": "test_app"
            },
            "workspace": {
                "input_dir": "test_input"
            },
            "template": "test_bench.j2"
        }
        
        # This should not raise an exception
        validated_config = self.validator.validate(config)
        
        # Check that the values are correctly set
        assert validated_config["name"] == "test_bench"
        assert validated_config["version"] == "1.0"
        assert validated_config["run"]["application"] == "test_app"
    
    def test_validate_invalid_config(self):
        """Test validating an invalid configuration."""
        # Missing task_type
        config = {
            "name": "test_app",
            "version": "1.0"
        }
        
        with pytest.raises(ValueError, match="missing 'task_type' field"):
            self.validator.validate(config)
        
        # Unknown task_type
        config = {
            "task_type": "unknown",
            "name": "test_app",
            "version": "1.0"
        }
        
        with pytest.raises(ValueError, match="Unknown or invalid task type"):
            self.validator.validate(config)
        
        # Invalid application config (missing required fields)
        config = {
            "task_type": "application",
            "name": "test_app"
        }
        
        with pytest.raises(ValueError, match="validation failed"):
            self.validator.validate(config)
    
    def test_validate_file(self):
        """Test validating a configuration file."""
        # Create a temporary configuration file
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
            },
            "template": "test_app.j2"
        }
        
        config_file = os.path.join(self.temp_dir.name, "test_config.yaml")
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        # This should not raise an exception
        validated_config = self.validator.validate_file(config_file)
        
        # Check that the values are correctly set
        assert validated_config["name"] == "test_app"
        assert validated_config["version"] == "1.0"
        assert validated_config["build"]["compiler"] == "gcc"
    
    def test_validate_nonexistent_file(self):
        """Test validating a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            self.validator.validate_file("nonexistent_file.yaml")
    
    def test_validate_invalid_yaml_file(self):
        """Test validating an invalid YAML file."""
        # Create a temporary file with invalid YAML
        invalid_file = os.path.join(self.temp_dir.name, "invalid.yaml")
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content:")
        
        with pytest.raises(ValueError, match="Error parsing YAML file"):
            self.validator.validate_file(invalid_file)
    
    def test_get_schema_for_task_type(self):
        """Test getting the schema for a task type."""
        # Valid task types
        app_schema = self.validator.get_schema_for_task_type("application")
        assert app_schema.__name__ == "ApplicationSchema"
        
        bench_schema = self.validator.get_schema_for_task_type("benchmark")
        assert bench_schema.__name__ == "BenchmarkSchema"
        
        # Invalid task type
        with pytest.raises(ValueError, match="Unknown task type"):
            self.validator.get_schema_for_task_type("unknown")
    
    def test_get_schema_json(self):
        """Test getting a schema as JSON for a task type."""
        # Get the schema as JSON for an application
        schema_json = self.validator.get_schema_json("application")
        
        # Check that the schema is a valid JSON string
        schema = json.loads(schema_json)
        assert isinstance(schema, dict)
        assert "properties" in schema
        
        # Get the schema as JSON for a benchmark
        schema_json = self.validator.get_schema_json("benchmark")
        
        # Check that the schema is a valid JSON string
        schema = json.loads(schema_json)
        assert isinstance(schema, dict)
        assert "properties" in schema
    
    def test_get_example_config(self):
        """Test getting an example configuration for a task type."""
        # Valid task types
        app_example = self.validator.get_example_config("application")
        assert app_example["name"] == "hello_world"
        assert app_example["task_type"] == "application"
        
        bench_example = self.validator.get_example_config("benchmark")
        assert bench_example["name"] == "hello_world_bench"
        assert bench_example["task_type"] == "benchmark"
        
        # Invalid task type
        with pytest.raises(ValueError, match="Unknown task type"):
            self.validator.get_example_config("unknown")

    def test_validate_global_config(self):
        """Test validating global configuration."""
        # Global configuration with valid fields
        global_config = {
            "logging": {
                "level": "DEBUG",
                "file": "test.log"
            },
            "paths": {
                "modules": "/usr/local/modules",
                "scratch": "/tmp/scratch"
            },
            "workspace": {
                "base_input_dir": "test/input",
                "base_output_dir": "test/output",
                "keep_source_files": True,
                "keep_build_files": True,
                "keep_logs": True
            }
        }
        
        # Validate the global configuration
        validated = self.validator.validate_global(global_config)
        
        # Check that the validated config contains the expected fields
        assert validated["logging"]["level"] == "DEBUG"
        assert validated["logging"]["file"] == "test.log"
        assert validated["paths"]["modules"] == "/usr/local/modules"
        assert validated["paths"]["scratch"] == "/tmp/scratch"
        assert validated["workspace"]["base_input_dir"] == "test/input"
        assert validated["workspace"]["base_output_dir"] == "test/output"
        assert validated["workspace"]["keep_source_files"] is True
        assert validated["workspace"]["keep_build_files"] is True
        assert validated["workspace"]["keep_logs"] is True

    def test_validate_layered_config(self):
        """Test validating a complete configuration with both global and task-specific settings."""
        # Complete configuration with both global and task-specific settings
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "test",
                "threads": 4
            },
            "job": {
                "scheduler": "slurm",
                "queue": "test",
                "time_limit": "01:00:00"
            },
            "workspace": {
                "source_dir": "source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True,
                "base_input_dir": "test/input",
                "base_output_dir": "test/output",
                "keep_logs": True
            },
            "template": "test.j2",
            "logging": {
                "level": "DEBUG",
                "file": "test.log"
            },
            "paths": {
                "modules": "/usr/local/modules",
                "scratch": "/tmp/scratch"
            }
        }
        
        # Validate the complete configuration
        validated = self.validator.validate(config)
        
        # Check that the validated config contains both global and task-specific fields
        # Task-specific fields
        assert validated["task_type"] == "application"
        assert validated["name"] == "test_app"
        assert validated["build"]["source"] == "test.c"
        assert validated["job"]["scheduler"] == "slurm"
        assert validated["workspace"]["source_dir"] == "source"
        assert validated["template"] == "test.j2"
        
        # Global fields
        assert validated["logging"]["level"] == "DEBUG"
        assert validated["paths"]["modules"] == "/usr/local/modules"
        assert validated["workspace"]["base_input_dir"] == "test/input"

    def test_validate_handles_legacy_fields(self):
        """Test that the validator properly handles legacy fields like 'scheduler'."""
        # Configuration with legacy fields
        config = {
            "task_type": "application",
            "name": "test_app",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "output": "test"
            },
            "scheduler": {  # Legacy field
                "queue": "test",
                "time_limit": "01:00:00"
            },
            "workspace": {
                "source_dir": "source"
            },
            "template": "test.j2"
        }
        
        # Validate the configuration
        validated = self.validator.validate_task(config)
        
        # Check that the scheduler field was moved to job
        assert "scheduler" not in validated
        assert "job" in validated
        assert validated["job"]["queue"] == "test"
        assert validated["job"]["time_limit"] == "01:00:00" 