import pytest
import os
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from benchpro.cli.cli import build, bench
from benchpro.config.metadata import ConfigReport, ConfigValue
from benchpro.executor.task_orchestrator import TaskOrchestrator


class TestCLIParameterReport:
    """Test CLI integration for parameter report feature."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        
        # Create a sample config report for testing
        self.sample_config_report = ConfigReport(
            final_config={
                "task_type": "application",
                "name": "test_app",
                "build": {"compiler": "gcc", "flags": "-O2"},
                "job": {"scheduler": "local", "time_limit": "10:00"}
            },
            config_metadata={
                "task_type": ConfigValue("application", "cli", None, None, 4, "2024-01-15T10:00:00Z"),
                "name": ConfigValue("test_app", "profile:hello_world", "hello_world.yaml", 5, 3, "2024-01-15T10:00:01Z"),
                "build.compiler": ConfigValue("gcc", "profile:hello_world", "hello_world.yaml", 8, 3, "2024-01-15T10:00:01Z"),
                "build.flags": ConfigValue("-O2", "system:slurm", "slurm.yaml", 12, 2, "2024-01-15T10:00:02Z"),
                "job.scheduler": ConfigValue("local", "smart_defaults", None, None, 5, "2024-01-15T10:00:03Z"),
                "job.time_limit": ConfigValue("10:00", "default", "default.yaml", 23, 1, "2024-01-15T10:00:00Z")
            },
            merge_history=[],
            profile_name="hello_world",
            cli_overrides={"task_type": "application"},
            generation_time="2024-01-15T10:00:00Z"
        )

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_param_report_flag(self, mock_execute):
        """Test build command with --param-report flag."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert len(args) == 5  # profile, cli_overrides, dry_run, param_report, param_report_format
        assert args[3] is True  # param_report
        assert args[4] == "table"  # param_report_format default

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_param_report_format_json(self, mock_execute):
        """Test build command with --param-report-format json."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report",
            "--param-report-format", "json"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[3] is True  # param_report
        assert args[4] == "json"  # param_report_format

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_param_report_format_yaml(self, mock_execute):
        """Test build command with --param-report-format yaml."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report",
            "--param-report-format", "yaml"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[3] is True  # param_report
        assert args[4] == "yaml"  # param_report_format

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_param_report_dry_run(self, mock_execute):
        """Test build command with --param-report --dry-run combination."""
        mock_execute.return_value = (True, None, "(param-report-only)")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[2] is True  # dry_run
        assert args[3] is True  # param_report

    @patch.object(TaskOrchestrator, 'execute')
    def test_bench_param_report_flag(self, mock_execute):
        """Test bench command with --param-report flag."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(bench, [
            "hello_world",
            "--param-report"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[3] is True  # param_report
        assert args[4] == "table"  # param_report_format default

    @patch.object(TaskOrchestrator, 'execute')
    def test_bench_param_report_format_json(self, mock_execute):
        """Test bench command with --param-report-format json."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(bench, [
            "hello_world",
            "--param-report",
            "--param-report-format", "json"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[3] is True  # param_report
        assert args[4] == "json"  # param_report_format

    @patch.object(TaskOrchestrator, 'execute')
    def test_bench_param_report_dry_run(self, mock_execute):
        """Test bench command with --param-report --dry-run combination."""
        mock_execute.return_value = (True, None, "(param-report-only)")
        
        result = self.runner.invoke(bench, [
            "hello_world",
            "--param-report",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[2] is True  # dry_run
        assert args[3] is True  # param_report

    @patch.object(TaskOrchestrator, 'execute')
    def test_param_report_format_without_flag(self, mock_execute):
        """Test that --param-report-format requires --param-report flag."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report-format", "json"
        ])
        
        # Should still work, but param_report will be False
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        assert args[3] is False  # param_report should be False
        assert args[4] == "json"  # param_report_format still passed

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_with_all_options(self, mock_execute):
        """Test build command with all options including param-report."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--output-dir", "/custom/output",
            "--system", "slurm", 
            "--executor", "scheduler",
            "--force",
            "--version", "1.2.3",
            "--param-report",
            "--param-report-format", "yaml"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        
        # Check profile name
        assert args[0] == "hello_world"
        
        # Check CLI overrides dictionary
        cli_overrides = args[1]
        assert cli_overrides["task_type"] == "application"
        assert cli_overrides["workspace"]["output_dir"] == "/custom/output"
        assert cli_overrides["system"] == "slurm"
        assert cli_overrides["execution"]["type"] == "sched"
        assert cli_overrides["force"] is True
        assert cli_overrides["version"] == "1.2.3"
        
        # Check other parameters
        assert args[2] is False  # dry_run
        assert args[3] is True   # param_report
        assert args[4] == "yaml" # param_report_format

    @patch.object(TaskOrchestrator, 'execute')
    def test_bench_with_all_options(self, mock_execute):
        """Test bench command with all options including param-report."""
        mock_execute.return_value = (True, "job123", "/path/to/script.sh")
        
        result = self.runner.invoke(bench, [
            "hello_world",
            "--output-dir", "/custom/output",
            "--system", "slurm",
            "--execution-type", "local",
            "--version", "1.2.3",
            "--param-report",
            "--param-report-format", "json",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        args, kwargs = mock_execute.call_args
        
        # Check CLI overrides
        cli_overrides = args[1]
        assert cli_overrides["task_type"] == "benchmark"
        assert cli_overrides["workspace"]["output_dir"] == "/custom/output"
        assert cli_overrides["system"] == "slurm"
        assert cli_overrides["execution"]["type"] == "local"
        assert cli_overrides["version"] == "1.2.3"
        
        # Check flags
        assert args[2] is True   # dry_run
        assert args[3] is True   # param_report
        assert args[4] == "json" # param_report_format

    def test_invalid_param_report_format(self):
        """Test that invalid --param-report-format values are rejected."""
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report",
            "--param-report-format", "invalid"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value for '--param-report-format'" in result.output

    @patch.object(TaskOrchestrator, 'execute')
    def test_orchestrator_exception_handling(self, mock_execute):
        """Test that TaskOrchestrator exceptions are handled properly."""
        mock_execute.side_effect = ValueError("Configuration error")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report"
        ])
        
        assert result.exit_code == 1
        # Error messages go to stderr in Click, so we check the exception was raised
        assert result.exception is not None

    @patch.object(TaskOrchestrator, 'execute')
    def test_build_task_failure(self, mock_execute):
        """Test build command when task execution fails."""
        mock_execute.return_value = (False, None, "/path/to/script.sh")
        
        result = self.runner.invoke(build, [
            "hello_world",
            "--param-report"
        ])
        
        assert result.exit_code == 1
        # Check that execute was called properly, exit code indicates failure
        mock_execute.assert_called_once()

    @patch.object(TaskOrchestrator, 'execute')
    def test_bench_task_failure(self, mock_execute):
        """Test bench command when task execution fails."""
        mock_execute.return_value = (False, None, "/path/to/script.sh")
        
        result = self.runner.invoke(bench, [
            "hello_world",
            "--param-report"
        ])
        
        assert result.exit_code == 1
        # Check that execute was called properly, exit code indicates failure
        mock_execute.assert_called_once()


class TestTaskOrchestratorParameterReport:
    """Test TaskOrchestrator parameter report integration."""

    def setup_method(self):
        """Set up test environment."""
        self.sample_config_report = ConfigReport(
            final_config={
                "task_type": "application",
                "name": "test_app",
                "template": "/path/to/template.sh"
            },
            config_metadata={
                "task_type": ConfigValue("application", "cli", None, None, 4, "2024-01-15T10:00:00Z"),
                "name": ConfigValue("test_app", "profile:hello_world", "hello_world.yaml", 5, 3, "2024-01-15T10:00:01Z")
            },
            merge_history=[],
            profile_name="hello_world",
            cli_overrides={"task_type": "application"},
            generation_time="2024-01-15T10:00:00Z"
        )

    @patch('benchpro.executor.task_orchestrator.ParameterReportDisplay')
    def test_param_report_dry_run_exit(self, mock_display_class):
        """Test that param-report with dry-run exits after showing report."""
        # Mock the display
        mock_display = MagicMock()
        mock_display_class.return_value = mock_display
        
        # Mock config manager 
        mock_config_manager = MagicMock()
        mock_config_manager.get_complete_config_report.return_value = self.sample_config_report
        
        # Create orchestrator with mocked config manager
        orchestrator = TaskOrchestrator(config_manager=mock_config_manager)
        
        # Test param_report with dry_run
        result = orchestrator.execute("hello_world", {}, dry_run=True, param_report=True, param_report_format="table")
        
        # Should return early with special script path
        assert result == (True, None, "(param-report-only)")
        
        # Should have called display
        mock_display.display_report.assert_called_once_with(self.sample_config_report, "table", True)
        
        # Should have called get_complete_config_report
        mock_config_manager.get_complete_config_report.assert_called_once_with("hello_world", {})

    @patch('benchpro.executor.task_orchestrator.ParameterReportDisplay')
    def test_param_report_normal_execution_continues(self, mock_display_class):
        """Test that param-report without dry-run shows report then continues."""
        # Mock the display
        mock_display = MagicMock()
        mock_display_class.return_value = mock_display
        
        # Mock config manager
        mock_config_manager = MagicMock()
        mock_config_manager.get_complete_config_report.return_value = self.sample_config_report
        
        # Mock workspace manager to return workspace config
        mock_workspace_manager = MagicMock()
        mock_workspace_manager.create_workspace.return_value = {"workspace_dir": "/tmp/test"}
        
        # Mock task factory and task
        mock_task_factory = MagicMock()
        mock_task = MagicMock()
        mock_task.generate_script.return_value = "/path/to/script.sh"
        mock_task.submit_job.return_value = (True, "job123")
        mock_task_factory.create_task.return_value = mock_task
        
        # Create orchestrator with mocked dependencies
        orchestrator = TaskOrchestrator(
            config_manager=mock_config_manager,
            workspace_manager=mock_workspace_manager
        )
        orchestrator.task_factory = mock_task_factory
        
        # Test param_report without dry_run
        result = orchestrator.execute("hello_world", {}, dry_run=False, param_report=True, param_report_format="json")
        
        # Should continue with normal execution
        assert result[0] is True  # success
        assert result[1] == "job123"  # job_id
        
        # Should have displayed report first
        mock_display.display_report.assert_called_once_with(self.sample_config_report, "json", False)
        
        # Should have called get_complete_config_report
        mock_config_manager.get_complete_config_report.assert_called_once_with("hello_world", {}) 