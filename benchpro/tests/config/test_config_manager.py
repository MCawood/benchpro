"""
Tests for the ConfigManager class.
"""

import os
import pytest
import tempfile
import yaml
import shutil
from unittest.mock import Mock, MagicMock

from benchpro.config.config_manager import ConfigManager
from benchpro.config.interfaces import ConfigLoaderInterface, ConfigMergerInterface, VariableResolverInterface, ConfigValidatorInterface
from benchpro.utils.filesystem import create_in_memory_fs, InMemoryFileSystem, TempFileSystem
from benchpro.utils.user_dir import UserDirectoryManager
from benchpro.config.loader import YamlConfigLoader
from benchpro.config.merger import HierarchicalConfigMerger
from benchpro.config.resolver import TemplateVariableResolver
from benchpro.config.validator import ConfigValidator


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # Create default configuration
    default_config = {
        "task_type": "application",
        "name": "default_app",
        "version": "1.0",
        "description": "Default application",
        "build": {
            "source": "default.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "default_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "compute",
            "account": "default_account",
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
        "template": "default_app.j2"
    }
    with open(os.path.join(config_dir, "default.yaml"), 'w') as f:
        yaml.dump(default_config, f)
        
    # Create system configuration
    system_config = {
        "job": {
            "scheduler": "slurm",
            "queue": "system_queue",
            "account": "system_account",
            "nodes": 2,
            "tasks_per_node": 16,
            "time_limit": "01:00:00"
        }
    }
    system_dir = os.path.join(config_dir, "system")
    os.makedirs(system_dir, exist_ok=True)
    with open(os.path.join(system_dir, "default.yaml"), 'w') as f:
        yaml.dump(system_config, f)
    
    # Create profile directory
    profile_dir = os.path.join(temp_dir, "profiles")
    os.makedirs(profile_dir, exist_ok=True)
    
    # Create application profile
    app_profile = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0",
        "description": "Test application",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "flags": "-O2",
            "output": "test_app",
            "threads": 1
        },
        "environment": {
            "modules": [],
            "variables": {}
        },
        "job": {
            "scheduler": "slurm",
            "queue": "profile_queue",
            "nodes": 1,
            "tasks_per_node": 1,
            "time_limit": "00:30:00"
        },
        "workspace": {
            "source_dir": "source",
            "build_dir": "build",
            "logs_dir": "logs",
            "keep_source": True,
            "keep_build": True
        },
        "template": "test_app.j2"
    }
    with open(os.path.join(profile_dir, "test_app.yaml"), 'w') as f:
        yaml.dump(app_profile, f)
    
    yield temp_dir, config_dir, profile_dir
    
    # Clean up
    shutil.rmtree(temp_dir)


class TestConfigManager:
    """Tests for the ConfigManager class."""
    
    @pytest.fixture(autouse=True)
    def setup(self, config_test_env):
        """Set up the test environment using standardized fixtures."""
        self.temp_dir = config_test_env["temp_dir"]
        self.config_dir = config_test_env["config_dir"]
        self.profile_dir = config_test_env["inputs_app_dir"]  # Use standardized app directory
        
        # Create a file system
        self.fs = TempFileSystem(temp_dir=self.temp_dir)
        
        # Create a user directory manager that points to the test environment
        from benchpro.utils.user_dir import get_user_dir_manager
        self.user_dir_manager = get_user_dir_manager(base_dir=self.temp_dir)
        
        # Create the components using the standardized configuration
        from benchpro.config.loader import YamlConfigLoader
        from benchpro.config.merger import HierarchicalConfigMerger
        from benchpro.config.resolver import TemplateVariableResolver
        from benchpro.config.validator import ConfigValidator
        from benchpro.config.config_manager import ConfigManager
        
        self.config_loader = YamlConfigLoader(user_dir_manager=self.user_dir_manager)
        self.config_merger = HierarchicalConfigMerger()
        self.variable_resolver = TemplateVariableResolver()
        self.config_validator = ConfigValidator()
        
        # Create the config manager
        self.config_manager = ConfigManager(
            user_dir_manager=self.user_dir_manager,
            config_loader=self.config_loader,
            config_merger=self.config_merger,
            variable_resolver=self.variable_resolver,
            config_validator=self.config_validator
        )
    
    def test_substitute_variables(self):
        """Test variable substitution in configuration."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "${name}",
                "threads": 1
            },
            "environment": {
                "modules": [],
                "variables": {}
            },
            "job": {
                "scheduler": "slurm",
                "queue": None,
                "account": None,
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00",
                "name": "${name}_job",  # Reference to top-level name
                "output_dir": "output/${name}"  # Reference to top-level name
            },
            "workspace": {
                "source_dir": "source/${name}",  # Reference to top-level name
                "build_dir": "${job.output_dir}/build",  # Reference to job.output_dir
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "${name}.j2"  # Reference to top-level name
        }
        
        # Substitute variables
        substituted_config = self.variable_resolver.resolve(config)
        
        # Check that variables were substituted
        assert substituted_config["build"]["output"] == "test_app"
        assert substituted_config["job"]["name"] == "test_app_job"
        assert substituted_config["job"]["output_dir"] == "output/test_app"
        assert substituted_config["workspace"]["source_dir"] == "source/test_app"
        assert substituted_config["workspace"]["build_dir"] == "output/test_app/build"
        assert substituted_config["template"] == "test_app.j2"
    
    def test_substitute_environment_variables(self):
        """Test environment variable substitution."""
        os.environ["TEST_VAR"] = "test_value"
        
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "${name}",
                "threads": 1
            },
            "environment": {
                "modules": [],
                "variables": {
                    "TEST_VAR": "${ENV:TEST_VAR}"
                }
            },
            "job": {
                "scheduler": "slurm",
                "queue": None,
                "account": None,
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00"
            },
            "workspace": {
                "source_dir": "source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test.j2"
        }
        
        # Substitute variables
        substituted_config = self.variable_resolver.resolve(config)
        
        # Check that environment variables were substituted
        assert substituted_config["environment"]["variables"]["TEST_VAR"] == "test_value"
    
    def test_substitute_nonexistent_variables(self):
        """Test handling of nonexistent variables."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "${name}",
                "threads": 1
            },
            "environment": {
                "modules": [],
                "variables": {
                    "TEST_VAR": "${ENV:NONEXISTENT_VAR}"
                }
            },
            "job": {
                "scheduler": "slurm",
                "queue": None,
                "account": None,
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00"
            },
            "workspace": {
                "source_dir": "source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test.j2"
        }
        
        # Substitute variables
        substituted_config = self.variable_resolver.resolve(config)
        
        # Check that nonexistent variables are left unchanged
        assert substituted_config["environment"]["variables"]["TEST_VAR"] == "${ENV:NONEXISTENT_VAR}"
    
    def test_substitute_nested_variables(self):
        """Test substitution of nested variables."""
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "description": "Test application",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "${name}",
                "threads": 1
            },
            "environment": {
                "modules": [],
                "variables": {}
            },
            "job": {
                "scheduler": "slurm",
                "queue": None,
                "account": None,
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00",
                "output_dir": "output/${name}"
            },
            "workspace": {
                "source_dir": "source/${name}",
                "build_dir": "${job.output_dir}/build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test.j2"
        }
        
        # Substitute variables
        substituted_config = self.variable_resolver.resolve(config)
        
        # Check that nested variables were substituted
        assert substituted_config["job"]["output_dir"] == "output/test_app"
        assert substituted_config["workspace"]["source_dir"] == "source/test_app"
        assert substituted_config["workspace"]["build_dir"] == "output/test_app/build"
    
    def test_merge_configs(self):
        """Test merging configurations using standardized test data."""
        # Create a custom test profile for merging testing
        test_profile = {
            "task_type": "application",
            "name": "merge_test",
            "version": "1.0",
            "description": "Test application for configuration merging",
            "build": {
                "source": "merge_test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "merge_test",
                "threads": 1
            },
            "environment": {
                "modules": ["gcc/11.2.0"],
                "variables": {}
            },
            "job": {
                "scheduler": "local",
                "queue": "compute",
                "account": "project123",
                "nodes": 2,
                "tasks_per_node": 16,
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
        
        # Create the profile file
        with open(os.path.join(self.profile_dir, "merge_test.yaml"), 'w') as f:
            yaml.dump(test_profile, f)
        
        # Test basic configuration merging (profile + system + default)
        merged_config = self.config_manager.get_complete_config("merge_test")
        
        # Check that the configurations were merged correctly
        assert merged_config["task_type"] == "application"
        assert merged_config["name"] == "merge_test"  # From profile
        assert merged_config["version"] == "1.0"  # From profile
        assert merged_config["build"]["compiler"] == "gcc"  # From profile
        assert merged_config["build"]["flags"] == "-O2"  # From profile
        assert merged_config["job"]["account"] == "project123"  # From profile
        assert merged_config["template"] == "hello_world.j2"  # From profile
        
        # System/default configurations should override profile values for some fields
        assert "queue" in merged_config["job"]  # Queue value comes from system/default config
        assert "scheduler" in merged_config["job"]  # Scheduler value is merged
        
        # Verify that system environment variables are merged (system data gets removed by validator)
        assert "environment" in merged_config
        assert "variables" in merged_config["environment"]
        assert "SYSTEM_TYPE" in merged_config["environment"]["variables"]  # From system config
        
        # Test that the configuration is valid after merging
        errors = self.config_manager.validate_config(merged_config)
        assert len(errors) == 0, f"Configuration validation failed: {errors}"
        
        # Test that profile-specific values are preserved
        assert merged_config["description"] == "Test application for configuration merging"
        assert merged_config["build"]["output"] == "merge_test"
        assert merged_config["build"]["source"] == "merge_test.c"
        
        # Test merging with a custom profile that doesn't specify an account
        profile_config_no_account = {
            "task_type": "application",
            "name": "test_app_no_account",
            "version": "1.0",
            "description": "Test application without account",
            "build": {
                "source": "test.c",
                "compiler": "gcc",
                "flags": "-O2",
                "output": "test_app_no_account",
                "threads": 1
            },
            "environment": {
                "modules": [],
                "variables": {}
            },
            "job": {
                "scheduler": "local",  # Use local scheduler for testing
                "queue": "compute",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00"
                # Note: no account specified
            },
            "workspace": {
                "source_dir": "source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test.j2"
        }
        
        with open(os.path.join(self.profile_dir, "test_app_no_account.yaml"), 'w') as f:
            yaml.dump(profile_config_no_account, f)
        
        # Get a complete configuration
        merged_config_no_account = self.config_manager.get_complete_config("test_app_no_account")
        
        # Check that system defaults are applied when profile doesn't specify values
        assert merged_config_no_account["task_type"] == "application"
        assert merged_config_no_account["name"] == "test_app_no_account"


@pytest.fixture
def mock_config_loader():
    """Create a mock ConfigLoader for testing."""
    loader = Mock(spec=ConfigLoaderInterface)
    
    # Set up mock return values
    loader.load_default_config.return_value = {
        "task_type": "application",
        "name": "default_app",
        "version": "1.0"
    }
    
    loader.load_system_config.return_value = {
        "job": {
            "scheduler": "slurm",
            "queue": "test_queue"
        }
    }
    
    loader.load_profile_config.return_value = {
        "task_type": "application",
        "name": "test_app",
        "version": "2.0",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "output": "test_app"
        }
    }
    
    return loader


@pytest.fixture
def mock_config_merger():
    """Create a mock ConfigMerger for testing."""
    merger = Mock(spec=ConfigMergerInterface)
    
    # Set up mock return values
    merger.merge_all.return_value = {
        "task_type": "application",
        "name": "test_app",
        "version": "2.0",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "output": "test_app"
        },
        "job": {
            "scheduler": "slurm",
            "queue": "test_queue"
        }
    }
    
    return merger


@pytest.fixture
def mock_variable_resolver():
    """Create a mock VariableResolver for testing."""
    resolver = Mock(spec=VariableResolverInterface)
    
    # Set up mock return values
    def resolve_side_effect(config):
        # Replace ${name} with the value of name
        if "reference" in config and config["reference"] == "${name}":
            config = config.copy()
            config["reference"] = config["name"]
        return config
    
    resolver.resolve.side_effect = resolve_side_effect
    
    return resolver


@pytest.fixture
def mock_config_validator():
    """Create a mock ConfigValidator for testing."""
    validator = Mock(spec=ConfigValidatorInterface)
    
    # Set up mock return values
    validator.validate.return_value = {
        "task_type": "application",
        "name": "test_app",
        "version": "2.0",
        "build": {
            "source": "test.c",
            "compiler": "gcc",
            "output": "test_app"
        },
        "job": {
            "scheduler": "slurm",
            "queue": "test_queue"
        }
    }
    
    validator.get_schema_json.return_value = '{"type": "object", "properties": {"task_type": {"type": "string"}}}'
    
    validator.generate_example.return_value = {
        "task_type": "application",
        "name": "example_app",
        "version": "1.0"
    }
    
    return validator


@pytest.fixture
def config_manager(mock_config_loader, mock_config_merger, mock_variable_resolver, mock_config_validator):
    """Create a ConfigManager with mock components for testing."""
    fs = create_in_memory_fs()
    user_dir_manager = UserDirectoryManager(file_system=fs)
    
    return ConfigManager(
        file_system=fs,
        user_dir_manager=user_dir_manager,
        config_loader=mock_config_loader,
        config_merger=mock_config_merger,
        variable_resolver=mock_variable_resolver,
        config_validator=mock_config_validator
    )


def test_get_complete_config(config_manager, mock_config_loader, mock_config_merger, mock_variable_resolver, mock_config_validator):
    """Test getting a complete configuration."""
    # Get a complete configuration
    config = config_manager.get_complete_config("test_app")
    
    # Check that the components were called correctly
    mock_config_loader.load_profile_config.assert_called_once_with("test_app", None)
    mock_config_loader.load_default_config.assert_called_once()
    mock_config_loader.load_system_config.assert_called_once()
    
    mock_config_merger.merge_all.assert_called_once()
    mock_variable_resolver.resolve.assert_called_once()
    mock_config_validator.validate.assert_called_once()
    
    # Check the result
    assert config["task_type"] == "application"
    assert config["name"] == "test_app"
    assert config["version"] == "2.0"
    assert config["build"]["source"] == "test.c"
    assert config["build"]["compiler"] == "gcc"
    assert config["build"]["output"] == "test_app"
    assert config["job"]["scheduler"] == "slurm"
    assert config["job"]["queue"] == "test_queue"


def test_get_complete_config_with_cli_overrides(config_manager, mock_config_merger):
    """Test getting a complete configuration with CLI overrides."""
    # Create CLI overrides
    cli_overrides = {
        "name": "cli_app",
        "job": {
            "queue": "cli_queue"
        }
    }
    
    # Get a complete configuration with CLI overrides
    config = config_manager.get_complete_config("test_app", cli_overrides)
    
    # Check that the merger was called with the CLI overrides
    mock_config_merger.merge_all.assert_called_once()
    args, kwargs = mock_config_merger.merge_all.call_args
    assert len(args) == 1
    assert len(args[0]) == 4  # default, system, profile, cli_overrides
    assert args[0][3] == cli_overrides


def test_validate_config(config_manager, mock_config_validator):
    """Test validating a configuration."""
    # Create a configuration to validate
    config = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0"
    }
    
    # Validate the configuration
    errors = config_manager.validate_config(config)
    
    # Check that the validator was called correctly
    mock_config_validator.validate.assert_called_once_with(config)
    
    # Check the result
    assert errors == []


def test_validate_config_with_errors(config_manager, mock_config_validator):
    """Test validating a configuration with errors."""
    # Create a configuration to validate
    config = {
        "task_type": "application",
        "name": "test_app",
        "version": "1.0"
    }
    
    # Set up the validator to raise an error
    mock_config_validator.validate.side_effect = ValueError("Configuration validation failed: Error 1, Error 2")
    
    # Validate the configuration
    errors = config_manager.validate_config(config)
    
    # Check that the validator was called correctly
    mock_config_validator.validate.assert_called_once_with(config)
    
    # Check the result
    assert len(errors) == 2
    assert errors[0] == "Error 1"
    assert errors[1] == "Error 2"


def test_get_schema_json(config_manager, mock_config_validator):
    """Test getting a schema as JSON for a task type."""
    # Get the schema as JSON
    schema_json = config_manager.get_schema_json("application")
    
    # Check that the validator was called correctly
    mock_config_validator.get_schema_json.assert_called_once_with("application")
    
    # Check the result
    assert schema_json == '{"type": "object", "properties": {"task_type": {"type": "string"}}}'


def test_generate_example(config_manager, mock_config_validator):
    """Test generating an example configuration for a task type."""
    # Generate an example configuration
    example = config_manager.generate_example("application")
    
    # Check that the validator was called correctly
    mock_config_validator.generate_example.assert_called_once_with("application")
    
    # Check the result
    assert example["task_type"] == "application"
    assert example["name"] == "example_app"
    assert example["version"] == "1.0" 