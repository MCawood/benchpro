"""
Tests for the configuration validator.
"""

import os
import pytest
import tempfile
import yaml

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
        
        # This should not raise an exception
        validated_config = self.validator.validate(config)
        
        # Check that the values are correctly set
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
        
        with pytest.raises(ValueError, match="Unknown task type"):
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
        """Test getting the JSON schema for a task type."""
        # Valid task types
        app_schema_json = self.validator.get_schema_json("application")
        assert app_schema_json["title"] == "ApplicationSchema"
        assert "properties" in app_schema_json
        
        bench_schema_json = self.validator.get_schema_json("benchmark")
        assert bench_schema_json["title"] == "BenchmarkSchema"
        assert "properties" in bench_schema_json
        
        # Invalid task type
        with pytest.raises(ValueError, match="Unknown task type"):
            self.validator.get_schema_json("unknown")
    
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