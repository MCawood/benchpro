"""
Tests for ConfigManager tracking integration.

This module tests the new tracking-enabled methods in ConfigManager,
specifically get_complete_config_report and its integration with the
tracking system.
"""

import pytest

from benchpro.config.config_manager import ConfigManager
from benchpro.config.metadata import ConfigReport, ConfigSource


# Remove our custom fixture - we'll use the existing config_test_env fixture


class TestConfigManagerTracking:
    """Test ConfigManager tracking functionality."""
    
    def test_get_complete_config_report_basic(self, config_test_env):
        """Test basic get_complete_config_report functionality."""
        # Initialize ConfigManager using the standardized test environment
        # The config_test_env fixture already sets up user_dir_manager properly
        config_manager = ConfigManager()
        
        # Get configuration report
        report = config_manager.get_complete_config_report("test_app")
        
        # Verify it's a ConfigReport instance
        assert isinstance(report, ConfigReport)
        assert report.profile_name == "test_app"
        
        # Check final configuration contains merged values
        assert report.final_config["task_type"] == "application"
        assert report.final_config["name"] == "test_app"
        assert report.final_config["job"]["nodes"] == 1  # From profile
        assert report.final_config["job"]["time_limit"] == "00:10:00"  # From profile/default
        assert "job" in report.final_config
        
        # Check metadata tracking
        assert "task_type" in report.config_metadata
        assert "name" in report.config_metadata
        assert "job.nodes" in report.config_metadata
        assert "job.time_limit" in report.config_metadata
        
        # Verify sources are tracked correctly
        assert report.config_metadata["task_type"].source == "profile:test_app"
        assert report.config_metadata["name"].source == "profile:test_app"
        assert report.config_metadata["job.nodes"].source == "profile:test_app"
        
        # Check merge history
        assert len(report.merge_history) >= 2  # At least default and profile, possibly system and smart_defaults
        source_names = [step.source for step in report.merge_history]
        assert "default" in source_names
        assert "profile:test_app" in source_names
        # System may or may not be present depending on configuration
    
    def test_get_complete_config_report_with_cli_overrides(self, config_test_env):
        """Test get_complete_config_report with CLI overrides."""
        config_manager = ConfigManager()
        
        # Add CLI overrides
        cli_overrides = {
            "job": {
                "nodes": 2,
                "queue": "cli_queue"
            },
            "version": "2.0"
        }
        
        report = config_manager.get_complete_config_report("test_app", cli_overrides)
        
        # Check that CLI overrides are applied
        assert report.final_config["job"]["nodes"] == 2  # CLI override
        assert report.final_config["job"]["queue"] == "cli_queue"  # CLI override
        assert report.final_config["version"] == "2.0"  # CLI override
        
        # Check CLI overrides are tracked
        assert report.config_metadata["job.nodes"].source == "cli"
        assert report.config_metadata["job.queue"].source == "cli"
        assert report.config_metadata["version"].source == "cli"
        
        # Check CLI overrides in history
        cli_steps = [step for step in report.merge_history if step.source == "cli"]
        assert len(cli_steps) == 1
        assert cli_steps[0].step_name == "Applying CLI overrides"
        
        # Verify CLI overrides are recorded in report
        assert report.cli_overrides == cli_overrides
    
    def test_get_complete_config_report_smart_defaults(self, config_test_env):
        """Test that smart defaults are tracked properly."""
        config_manager = ConfigManager()
        
        # Use a CLI override that triggers smart defaults
        cli_overrides = {
            "execution": {"type": "sched"}
        }
        
        report = config_manager.get_complete_config_report("test_app", cli_overrides)
        
        # Check that smart defaults were applied
        # The scheduler should default to slurm for sched execution type
        assert report.final_config["job"]["scheduler"] == "slurm"
        
        # Check if smart defaults are tracked (if any were applied)
        smart_default_steps = [step for step in report.merge_history if step.source == "smart_defaults"]
        if smart_default_steps:
            assert len(smart_default_steps) == 1
            assert smart_default_steps[0].step_name == "Applying smart defaults"
    
    def test_get_complete_config_source_summary(self, config_test_env):
        """Test the source summary functionality."""
        config_manager = ConfigManager()
        
        report = config_manager.get_complete_config_report("test_app")
        source_summary = report.get_source_summary()
        
        # Should have parameters from multiple sources
        assert "default" in source_summary
        assert "profile:test_app" in source_summary
        
        # Each source should have contributed some parameters
        assert source_summary["default"] > 0
        assert source_summary["profile:test_app"] > 0
    
    def test_get_complete_config_parameters_by_source(self, config_test_env):
        """Test getting parameters by source."""
        config_manager = ConfigManager()
        
        report = config_manager.get_complete_config_report("test_app")
        
        # Get parameters from each source
        default_params = report.get_parameters_by_source("default")
        profile_params = report.get_parameters_by_source("profile:test_app")
        
        # Check that parameters are correctly attributed
        assert "task_type" in profile_params
        assert "name" in profile_params
        # Default parameters will vary based on what's in the default config
    
    def test_backward_compatibility_get_complete_config(self, config_test_env):
        """Test that the old get_complete_config method still works."""
        config_manager = ConfigManager()
        
        # The old method should still return a dictionary
        config = config_manager.get_complete_config("test_app")
        
        assert isinstance(config, dict)
        assert config["task_type"] == "application"
        assert config["name"] == "test_app"
        assert config["job"]["nodes"] == 1  # From test_app profile
        
        # Test with CLI overrides
        cli_overrides = {"version": "3.0"}
        config_with_overrides = config_manager.get_complete_config("test_app", cli_overrides)
        
        assert config_with_overrides["version"] == "3.0"
    
    def test_load_configuration_sources(self, config_test_env):
        """Test the _load_configuration_sources helper method."""
        config_manager = ConfigManager()
        
        # Load sources
        sources = config_manager._load_configuration_sources("test_app")
        
        # Should have at least default and profile sources
        assert len(sources) >= 2
        
        # Check source types and precedence
        source_names = [source.source for source in sources]
        assert "default" in source_names
        assert "profile:test_app" in source_names
        
        # Check precedence order
        for i, source in enumerate(sources[:-1]):
            assert source.precedence <= sources[i + 1].precedence
        
        # Check that all sources are ConfigSource instances
        for source in sources:
            assert isinstance(source, ConfigSource)
            assert isinstance(source.config, dict)
            assert source.source
            assert isinstance(source.precedence, int) 