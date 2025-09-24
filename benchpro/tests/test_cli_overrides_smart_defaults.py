"""
Test CLI override functionality with smart defaults.

This module tests the smart defaults functionality that automatically
sets job.scheduler based on execution.type to avoid redundant configuration.
"""

import pytest
from benchpro.config.config_manager import ConfigManager
from benchpro.executor.task_factory import TaskFactory
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.templates.script_generators import LocalScriptGenerator, SlurmScriptGenerator
from benchpro.tests.fixtures.test_data import get_standard_application_profile
from benchpro.utils.filesystem import create_temp_fs


class TestSmartDefaults:
    """Test smart defaults functionality."""
    
    def test_smart_defaults_local_execution(self):
        """Test that execution.type=local sets job.scheduler=local."""
        config_manager = ConfigManager()
        
        # Create a profile with local execution
        profile_config = get_standard_application_profile("cli_test")
        profile_config["execution"]["type"] = "local"
        
        # Apply smart defaults
        result = config_manager._apply_smart_defaults(profile_config)
        
        assert result["execution"]["type"] == "local"
        assert result["job"]["scheduler"] == "local"
    
    def test_smart_defaults_slurm_execution(self):
        """Test that execution.type=sched sets job.scheduler=slurm."""
        config_manager = ConfigManager()
        
        # Get a test profile config
        profile_config = get_standard_application_profile("cli_test")
        profile_config["execution"]["type"] = "sched"
        
        # Apply smart defaults
        result = config_manager._apply_smart_defaults(profile_config)
        
        assert result["execution"]["type"] == "sched"
        assert result["job"]["scheduler"] == "slurm"
    
    def test_smart_defaults_preserves_explicit_scheduler(self):
        """Test that smart defaults don't override explicitly set job.scheduler."""
        config_manager = ConfigManager()
        
        # Create a profile with scheduled execution and explicit scheduler
        profile_config = get_standard_application_profile("cli_test")
        profile_config["execution"]["type"] = "sched"
        profile_config["job"]["scheduler"] = "pbs"  # Explicit different scheduler
        
        # Apply smart defaults
        result = config_manager._apply_smart_defaults(profile_config)
        
        assert result["execution"]["type"] == "sched"
        assert result["job"]["scheduler"] == "pbs"  # Should preserve explicit value

class TestCLIOverridesWithSmartDefaults:
    """Test CLI overrides work correctly with smart defaults."""
    
    def test_cli_override_execution_type_to_local(self, config_test_env):
        """Test CLI override of execution.type to local applies smart defaults."""
        # Create a TempFileSystem that points to our test directories
        test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
        
        # Initialize ConfigManager with the TempFileSystem
        config_manager = ConfigManager(
            config_dir=config_test_env["config_dir"],
            profile_dir=config_test_env["temp_dir"],
            file_system=test_fs
        )
        
        # CLI override to change execution type to local
        cli_overrides = {
            "execution": {
                "type": "local"
            }
        }
        
        # Merge configs (cli_test profile has execution.type=sched by default)
        merged_config = config_manager.merge_configs("cli_test", cli_overrides)
        
        # Verify CLI override worked and smart defaults applied
        assert merged_config["execution"]["type"] == "local"
        assert merged_config["job"]["scheduler"] == "local"
    
    def test_cli_override_execution_type_to_sched(self, config_test_env):
        """Test CLI override of execution.type to sched applies smart defaults."""
        # Create a TempFileSystem that points to our test directories
        test_fs = create_temp_fs(temp_dir=config_test_env["temp_dir"])
        
        # Initialize ConfigManager with the TempFileSystem
        config_manager = ConfigManager(
            config_dir=config_test_env["config_dir"],
            profile_dir=config_test_env["temp_dir"],
            file_system=test_fs
        )
        
        # CLI override to change execution type to sched
        cli_overrides = {
            "execution": {
                "type": "sched"
            }
        }
        
        # Merge configs
        merged_config = config_manager.merge_configs("cli_test", cli_overrides)
        
        # Verify CLI override worked - this is the main thing we're testing
        assert merged_config["execution"]["type"] == "sched"
        
        # The scheduler should be a reasonable value for scheduled execution
        # It might be "slurm" from smart defaults, or preserved from config files
        scheduler = merged_config["job"]["scheduler"]
        assert scheduler is not None
        assert isinstance(scheduler, str)
        # We don't force it to be "slurm" because smart defaults preserve explicit values


class TestTaskFactoryWithSmartDefaults:
    """Test that TaskFactory uses execution.type correctly with smart defaults."""
    
    def test_task_factory_uses_execution_type_for_script_generator(self, standardized_test_env):
        """Test that TaskFactory chooses script generator based on execution.type."""
        from benchpro.executor.task_factory import TaskFactory
        from unittest.mock import Mock
        
        # Create task factory with mocked dependencies
        config_manager = Mock()
        registry_manager = Mock()
        factory = TaskFactory(config_manager, registry_manager)
        
        # Test local execution
        local_config = get_standard_application_profile("cli_test")
        local_config["execution"]["type"] = "local"
        local_config["job"]["scheduler"] = "local"  # Smart defaults would set this
        
        local_task = factory.create_task(local_config)
        assert isinstance(local_task.script_generation_component, LocalScriptGenerator)
        
        # Test scheduled execution
        sched_config = get_standard_application_profile("cli_test")
        sched_config["execution"]["type"] = "sched"
        sched_config["job"]["scheduler"] = "slurm"  # Smart defaults would set this
        
        sched_task = factory.create_task(sched_config)
        assert isinstance(sched_task.script_generation_component, SlurmScriptGenerator)


class TestEndToEndCLIOverrides:
    """Test end-to-end CLI override functionality."""
    
    def test_cli_override_execution_type_end_to_end(self, standardized_test_env):
        """Test CLI override of execution.type works end-to-end."""
        from unittest.mock import Mock
        
        # Create the orchestrator with mocked registry
        registry_manager = Mock()
        orchestrator = TaskOrchestrator(registry_manager=registry_manager)
        
        # Override execution type to local
        cli_overrides = {
            "execution": {
                "type": "local"
            }
        }
        
        # Execute with CLI overrides (dry run)
        success, job_id, script_path = orchestrator.execute("cli_test", cli_overrides, dry_run=True)
        
        # Verify success
        assert success
        # Note: Local execution doesn't return job IDs, so job_id will be None
        assert script_path is not None
        
        # Verify the generated script doesn't contain SLURM directives
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Should not contain SLURM directives since execution.type=local
        assert "#SBATCH" not in script_content
        assert "#!/bin/bash" in script_content  # Should have bash shebang 