"""
Tests for the ConfigManager.
"""

import os
import pytest
import tempfile
import yaml
import shutil

from benchpro.config.config_manager import ConfigManager


class TestConfigManager:
    """Tests for the ConfigManager."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        self.profile_dir = os.path.join(self.temp_dir, "profiles")
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.profile_dir, exist_ok=True)
        
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
        with open(os.path.join(self.config_dir, "default.yaml"), 'w') as f:
            yaml.dump(default_config, f)
            
        # Create system configuration
        system_config = {
            "job": {
                "scheduler": "slurm",
                "queue": "compute",
                "account": "system_account",
                "nodes": 1,
                "tasks_per_node": 16,
                "time_limit": "00:10:00"
            }
        }
        with open(os.path.join(self.config_dir, "system_default.yaml"), 'w') as f:
            yaml.dump(system_config, f)
            
        # Create test profile
        test_profile = {
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
                "queue": "compute",
                "account": "project123",
                "nodes": 2,
                "tasks_per_node": 16,
                "time_limit": "00:10:00"
            },
            "workspace": {
                "source_dir": "${job.account}/source",
                "build_dir": "build",
                "logs_dir": "logs",
                "keep_source": True,
                "keep_build": True
            },
            "template": "test_app.j2"
        }
        with open(os.path.join(self.profile_dir, "test_profile.yaml"), 'w') as f:
            yaml.dump(test_profile, f)
        
        # Initialize the ConfigManager
        self.config_manager = ConfigManager(config_dir=self.config_dir, profile_dir=self.profile_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
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
        substituted_config = self.config_manager.substitute_variables(config)
        
        # Check that variables were substituted correctly
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
        substituted_config = self.config_manager.substitute_variables(config)
        
        # Check that environment variables were substituted correctly
        assert substituted_config["environment"]["variables"]["TEST_VAR"] == "test_value"
        
        # Clean up
        del os.environ["TEST_VAR"]
    
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
                    "TEST_VAR": "${env:NONEXISTENT_VAR}"
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
        substituted_config = self.config_manager.substitute_variables(config)
        
        # Check that nonexistent variables are left unchanged
        assert substituted_config["environment"]["variables"]["TEST_VAR"] == "${env:NONEXISTENT_VAR}"
    
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
        substituted_config = self.config_manager.substitute_variables(config)
        
        # Check that nested variables were substituted correctly
        assert substituted_config["job"]["output_dir"] == "output/test_app"
        assert substituted_config["workspace"]["source_dir"] == "source/test_app"
        assert substituted_config["workspace"]["build_dir"] == "output/test_app/build"
    
    def test_merge_configs(self):
        """Test merging configurations."""
        # Create a profile configuration
        profile_config = {
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
                "queue": "compute",
                "account": "test_account",
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
        
        with open(os.path.join(self.profile_dir, "test_app.yaml"), 'w') as f:
            yaml.dump(profile_config, f)
        
        # Create CLI overrides
        cli_overrides = {
            "job": {
                "nodes": 4,
                "tasks_per_node": 32
            }
        }
        
        # Merge configurations
        merged_config = self.config_manager.merge_configs("test_app", cli_overrides)
        
        # Check that the configurations were merged correctly
        assert merged_config["name"] == "test_app"
        assert merged_config["job"]["nodes"] == 4  # From CLI overrides
        assert merged_config["job"]["tasks_per_node"] == 32  # From CLI overrides
        assert merged_config["job"]["account"] == "test_account"  # From profile config (profile overrides system)
        
        # Test with a profile that doesn't specify an account
        # Create a profile configuration without account
        profile_no_account = {
            "task_type": "application",
            "name": "test_app_no_account",
            "version": "1.0",
            "description": "Test application without account",
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
                "queue": "compute",
                "nodes": 1,
                "tasks_per_node": 1,
                "time_limit": "01:00:00"
                # No account specified here, should fall back to system account
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
            yaml.dump(profile_no_account, f)
        
        # Merge configurations for the profile without account
        merged_config_no_account = self.config_manager.merge_configs("test_app_no_account", {})
        
        # Now the system account should be used since the profile doesn't specify one
        assert merged_config_no_account["job"]["account"] == "system_account"  # From system config 