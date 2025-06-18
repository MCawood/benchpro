"""
Tests for the parameter tracking and reporting functionality.

This module tests the new tracking-first configuration system including
ConfigSource, ConfigReport, and the enhanced HierarchicalConfigMerger.
"""

import pytest
from datetime import datetime

from benchpro.config.metadata import ConfigSource, ConfigValue, ConfigReport, MergeStep
from benchpro.config.metadata import flatten_config_for_tracking, unflatten_config_from_tracking
from benchpro.config.merger import HierarchicalConfigMerger
from benchpro.config.report_generator import ConfigReportGenerator, ParameterReportDisplay


class TestConfigSource:
    """Test ConfigSource data structure."""
    
    def test_config_source_creation(self):
        """Test creating a ConfigSource instance."""
        config = {"job": {"nodes": 4}}
        source = ConfigSource(
            config=config,
            source="profile:test",
            source_file="/path/to/test.yaml",
            precedence=5
        )
        
        assert source.config == config
        assert source.source == "profile:test"
        assert source.source_file == "/path/to/test.yaml"
        assert source.precedence == 5
    
    def test_config_source_validation(self):
        """Test ConfigSource validation."""
        # Test invalid config type
        with pytest.raises(ValueError, match="Config must be a dictionary"):
            ConfigSource(config="not a dict", source="test")
        
        # Test missing source
        with pytest.raises(ValueError, match="Source must be specified"):
            ConfigSource(config={}, source="")


class TestConfigValue:
    """Test ConfigValue data structure."""
    
    def test_config_value_creation(self):
        """Test creating a ConfigValue instance."""
        value = ConfigValue(
            value=42,
            source="default",
            source_file="/path/to/default.yaml",
            line_number=15,
            precedence=1
        )
        
        assert value.value == 42
        assert value.source == "default"
        assert value.source_file == "/path/to/default.yaml"
        assert value.line_number == 15
        assert value.precedence == 1
        assert value.applied_at  # Should be auto-generated
    
    def test_config_value_validation(self):
        """Test ConfigValue validation."""
        with pytest.raises(ValueError, match="Source must be specified"):
            ConfigValue(value=42, source="")


class TestConfigReport:
    """Test ConfigReport data structure."""
    
    def test_config_report_creation(self):
        """Test creating a ConfigReport instance."""
        final_config = {"job": {"nodes": 4}}
        metadata = {
            "job.nodes": ConfigValue(value=4, source="profile:test")
        }
        history = [
            MergeStep(step_name="Loading profile", source="profile:test", changes={"job.nodes": 4})
        ]
        
        report = ConfigReport(
            final_config=final_config,
            config_metadata=metadata,
            merge_history=history,
            profile_name="test_profile"
        )
        
        assert report.final_config == final_config
        assert report.config_metadata == metadata
        assert report.merge_history == history
        assert report.profile_name == "test_profile"
        assert report.generation_time  # Should be auto-generated
    
    def test_get_source_summary(self):
        """Test getting source summary from report."""
        metadata = {
            "job.nodes": ConfigValue(value=4, source="profile:test"),
            "job.queue": ConfigValue(value="compute", source="profile:test"),
            "execution.type": ConfigValue(value="local", source="default")
        }
        
        report = ConfigReport(
            final_config={},
            config_metadata=metadata,
            merge_history=[],
            profile_name="test"
        )
        
        summary = report.get_source_summary()
        assert summary["profile:test"] == 2
        assert summary["default"] == 1
    
    def test_get_parameters_by_source(self):
        """Test getting parameters by source."""
        metadata = {
            "job.nodes": ConfigValue(value=4, source="profile:test"),
            "job.queue": ConfigValue(value="compute", source="profile:test"),
            "execution.type": ConfigValue(value="local", source="default")
        }
        
        report = ConfigReport(
            final_config={},
            config_metadata=metadata,
            merge_history=[],
            profile_name="test"
        )
        
        profile_params = report.get_parameters_by_source("profile:test")
        assert profile_params == {"job.nodes": 4, "job.queue": "compute"}
        
        default_params = report.get_parameters_by_source("default")
        assert default_params == {"execution.type": "local"}


class TestFlattenUnflatten:
    """Test configuration flattening and unflattening utilities."""
    
    def test_flatten_config(self):
        """Test flattening nested configuration."""
        config = {
            "job": {
                "nodes": 4,
                "queue": "compute"
            },
            "execution": {
                "type": "local"
            },
            "simple": "value"
        }
        
        flattened = flatten_config_for_tracking(config)
        expected = {
            "job.nodes": 4,
            "job.queue": "compute",
            "execution.type": "local",
            "simple": "value"
        }
        
        assert flattened == expected
    
    def test_unflatten_config(self):
        """Test unflattening configuration back to nested structure."""
        flat_config = {
            "job.nodes": 4,
            "job.queue": "compute",
            "execution.type": "local",
            "simple": "value"
        }
        
        unflattened = unflatten_config_from_tracking(flat_config)
        expected = {
            "job": {
                "nodes": 4,
                "queue": "compute"
            },
            "execution": {
                "type": "local"
            },
            "simple": "value"
        }
        
        assert unflattened == expected
    
    def test_flatten_unflatten_roundtrip(self):
        """Test that flatten and unflatten are inverse operations."""
        original = {
            "deeply": {
                "nested": {
                    "config": {
                        "value": 42
                    }
                }
            },
            "simple": "test"
        }
        
        flattened = flatten_config_for_tracking(original)
        unflattened = unflatten_config_from_tracking(flattened)
        
        assert unflattened == original


class TestHierarchicalConfigMergerWithTracking:
    """Test the enhanced HierarchicalConfigMerger with tracking capabilities."""
    
    def test_merge_sources_basic(self):
        """Test basic merge_sources functionality."""
        merger = HierarchicalConfigMerger()
        
        # Create test sources
        default_source = ConfigSource(
            config={"job": {"nodes": 2, "time_limit": "01:00:00"}},
            source="default",
            source_file="/path/to/default.yaml",
            precedence=1
        )
        
        profile_source = ConfigSource(
            config={"job": {"nodes": 4}, "name": "test_app"},
            source="profile:test",
            source_file="/path/to/test.yaml",
            precedence=2
        )
        
        # Merge sources
        report = merger.merge_sources([default_source, profile_source], "test_profile")
        
        # Check final configuration
        assert report.final_config["job"]["nodes"] == 4  # Profile overrides default
        assert report.final_config["job"]["time_limit"] == "01:00:00"  # From default
        assert report.final_config["name"] == "test_app"  # From profile
        
        # Check metadata tracking
        assert "job.nodes" in report.config_metadata
        assert report.config_metadata["job.nodes"].source == "profile:test"
        assert report.config_metadata["job.nodes"].value == 4
        
        assert "job.time_limit" in report.config_metadata
        assert report.config_metadata["job.time_limit"].source == "default"
        
        # Check merge history
        assert len(report.merge_history) == 2
        assert report.merge_history[0].source == "default"
        assert report.merge_history[1].source == "profile:test"
    
    def test_merge_sources_with_cli_overrides(self):
        """Test merge_sources with CLI overrides."""
        merger = HierarchicalConfigMerger()
        
        profile_source = ConfigSource(
            config={"job": {"nodes": 4}},
            source="profile:test",
            precedence=2
        )
        
        cli_overrides = {"job": {"nodes": 8}}
        
        report = merger.merge_sources([profile_source], "test_profile", cli_overrides)
        
        # CLI should override profile
        assert report.final_config["job"]["nodes"] == 8
        assert report.config_metadata["job.nodes"].source == "cli"
        
        # Check that CLI override is recorded in history
        assert len(report.merge_history) == 2
        assert report.merge_history[1].source == "cli"
    
    def test_backward_compatibility_methods(self):
        """Test that existing merge methods still work."""
        merger = HierarchicalConfigMerger()
        
        base = {"job": {"nodes": 2}}
        override = {"job": {"queue": "compute"}}
        
        # Test merge method
        result = merger.merge(base, override)
        assert result["job"]["nodes"] == 2
        assert result["job"]["queue"] == "compute"
        
        # Test merge_all method
        configs = [
            {"job": {"nodes": 2}},
            {"job": {"queue": "compute"}},
            {"job": {"nodes": 4}}  # Should override the first nodes value
        ]
        
        result = merger.merge_all(configs)
        assert result["job"]["nodes"] == 4
        assert result["job"]["queue"] == "compute"


class TestConfigReportGenerator:
    """Test the ConfigReportGenerator functionality."""
    
    def test_generate_table_report(self):
        """Test generating table format report."""
        generator = ConfigReportGenerator()
        
        # Create a test report
        metadata = {
            "job.nodes": ConfigValue(
                value=4,
                source="profile:test",
                source_file="/path/to/test.yaml",
                line_number=10
            ),
            "execution.type": ConfigValue(
                value="local",
                source="default",
                source_file="/path/to/default.yaml"
            )
        }
        
        history = [
            MergeStep(
                step_name="Loading default configuration",
                source="default",
                changes={"execution.type": "local"},
                parameters_added=1,
                parameters_modified=0
            ),
            MergeStep(
                step_name="Loading profile configuration: test",
                source="profile:test",
                changes={"job.nodes": 4},
                parameters_added=1,
                parameters_modified=0
            )
        ]
        
        report = ConfigReport(
            final_config={"job": {"nodes": 4}, "execution": {"type": "local"}},
            config_metadata=metadata,
            merge_history=history,
            profile_name="test_profile"
        )
        
        # Generate table report
        table_report = generator.generate_table_report(report)
        
        # Check that the report contains expected elements
        assert "BenchPRO Parameter Report" in table_report
        assert "Profile: test_profile" in table_report
        assert "execution.type" in table_report
        assert "job.nodes" in table_report
        assert "default" in table_report
        assert "profile:test" in table_report
        assert "Loading default configuration" in table_report
        assert "Loading profile configuration: test" in table_report
    
    def test_generate_json_report(self):
        """Test generating JSON format report."""
        generator = ConfigReportGenerator()
        
        metadata = {
            "test.param": ConfigValue(value="test_value", source="test_source")
        }
        
        report = ConfigReport(
            final_config={"test": {"param": "test_value"}},
            config_metadata=metadata,
            merge_history=[],
            profile_name="test_profile"
        )
        
        json_report = generator.generate_json_report(report)
        
        # Should be valid JSON containing our data
        import json
        parsed = json.loads(json_report)
        assert parsed["profile_name"] == "test_profile"
        assert "parameter_metadata" in parsed
        assert "test.param" in parsed["parameter_metadata"]
    
    def test_unsupported_format(self):
        """Test error handling for unsupported formats."""
        generator = ConfigReportGenerator()
        
        report = ConfigReport(
            final_config={},
            config_metadata={},
            merge_history=[],
            profile_name="test"
        )
        
        with pytest.raises(ValueError, match="Unsupported format type: invalid"):
            generator.generate_report(report, "invalid")


class TestParameterReportDisplay:
    """Test the ParameterReportDisplay helper."""
    
    def test_should_display_report(self):
        """Test logic for when to display reports."""
        display = ParameterReportDisplay()
        
        # Should display when param-report flag is set
        assert display.should_display_report(True, False) is True
        assert display.should_display_report(True, True) is True
        
        # Should not display when param-report flag is not set
        assert display.should_display_report(False, False) is False
        assert display.should_display_report(False, True) is False
    
    def test_should_continue_execution(self):
        """Test logic for when to continue execution."""
        display = ParameterReportDisplay()
        
        # Should continue when only param-report is set
        assert display.should_continue_execution(True, False) is True
        
        # Should continue when neither flag is set
        assert display.should_continue_execution(False, False) is True
        
        # Should continue when only dry-run is set
        assert display.should_continue_execution(False, True) is True
        
        # Should NOT continue when both flags are set
        assert display.should_continue_execution(True, True) is False 