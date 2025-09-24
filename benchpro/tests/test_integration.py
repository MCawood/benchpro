"""
Integration tests for BenchPRO using standardized test data.

This module tests the integration between different components using
the centralized test data management system for consistency.
"""

import os
import pytest
from benchpro.config.config_manager import ConfigManager
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.registry.registry_manager import RegistryManager
from benchpro.utils.user_dir import get_user_dir_manager


def test_application_build(standardized_test_env, monkeypatch):
    """Test application build workflow using standardized test data."""
    def mock_execute(self, script_path, workspace=None):
        return True, "test_job_id"
    monkeypatch.setattr("benchpro.executor.components.execution.LocalExecutionComponent.execute", mock_execute)

    user_dir_manager = get_user_dir_manager(base_dir=standardized_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    
    # Mock registry manager to avoid database dependency
    from unittest.mock import MagicMock
    mock_registry_manager = MagicMock()
    mock_registry_manager.register_task_submission.return_value = "mock_task_id"
    
    from benchpro.workspace.workspace_manager import WorkspaceManager
    workspace_manager = WorkspaceManager(user_dir_manager=user_dir_manager)

    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=mock_registry_manager,
        workspace_manager=workspace_manager
    )
    success, job_id, script_path = orchestrator.execute("test_app", {}, dry_run=False)

    assert success is True
    assert job_id == "test_job_id"
    assert os.path.exists(script_path)
    assert script_path.endswith(".sh")


def test_benchmark_run(standardized_test_env, monkeypatch):
    """Test benchmark run workflow using standardized test data."""
    def mock_execute(self, script_path, workspace=None):
        return True, "test_job_id"
    monkeypatch.setattr("benchpro.executor.components.execution.LocalExecutionComponent.execute", mock_execute)

    user_dir_manager = get_user_dir_manager(base_dir=standardized_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    
    # Mock registry manager to avoid database dependency
    from unittest.mock import MagicMock
    mock_registry_manager = MagicMock()
    mock_registry_manager.register_task_submission.return_value = "mock_task_id"
    mock_registry_manager.list_applications.return_value = [
        {"name": "test_app", "version": "1.0", "binary_path": "/path/to/test_app"}
    ]
    
    from benchpro.workspace.workspace_manager import WorkspaceManager
    workspace_manager = WorkspaceManager(user_dir_manager=user_dir_manager)

    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=mock_registry_manager,
        workspace_manager=workspace_manager
    )
    success, job_id, script_path = orchestrator.execute("test_benchmark", {"task_type": "benchmark"}, dry_run=False)

    assert success is True
    assert job_id == "test_job_id"
    assert os.path.exists(script_path)
    assert script_path.endswith(".sh")


def test_cli_overrides(standardized_test_env, monkeypatch):
    """Test command-line overrides for job configuration using standardized test data."""
    def mock_execute(self, script_path, workspace=None):
        return True, "test_job_id"
    monkeypatch.setattr("benchpro.executor.components.execution.LocalExecutionComponent.execute", mock_execute)

    user_dir_manager = get_user_dir_manager(base_dir=standardized_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)

    cli_overrides = {
        "build": {"flags": "-O3 -march=native"},
        "execution": {"type": "local"}  # Force local execution to avoid slurm dependency
    }

    # Mock registry manager to avoid database dependency
    from unittest.mock import MagicMock
    mock_registry_manager = MagicMock()
    mock_registry_manager.register_task_submission.return_value = "mock_task_id"
    
    from benchpro.workspace.workspace_manager import WorkspaceManager
    workspace_manager = WorkspaceManager(user_dir_manager=user_dir_manager)

    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=mock_registry_manager,
        workspace_manager=workspace_manager
    )
    success, job_id, script_path = orchestrator.execute("cli_test", cli_overrides, dry_run=False)

    assert success is True
    assert job_id == "test_job_id"
    assert os.path.exists(script_path)
    with open(script_path, 'r') as f:
        content = f.read()
        # Check that the build flags were overridden (this actually works for local execution)
        assert "-O3 -march=native" in content
        # Verify the original flags are not present
        assert "-O2" not in content


def test_full_workflow(standardized_test_env, monkeypatch):
    """Test a complete workflow with all components using standardized test data."""
    def mock_execute(self, script_path, workspace=None):
        return True, "test_job_id"
    monkeypatch.setattr("benchpro.executor.components.execution.LocalExecutionComponent.execute", mock_execute)

    user_dir_manager = get_user_dir_manager(base_dir=standardized_test_env["temp_dir"])
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    
    # Mock registry manager to avoid database dependency
    from unittest.mock import MagicMock
    mock_registry_manager = MagicMock()
    mock_registry_manager.register_task_submission.return_value = "mock_task_id"
    mock_registry_manager.list_applications.return_value = [
        {"name": "test_app", "version": "1.0", "binary_path": "/path/to/test_app"}
    ]
    
    from benchpro.workspace.workspace_manager import WorkspaceManager
    workspace_manager = WorkspaceManager(user_dir_manager=user_dir_manager)

    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=mock_registry_manager,
        workspace_manager=workspace_manager
    )

    # Test application build
    app_success, app_job_id, _ = orchestrator.execute("test_app", {}, dry_run=False)
    assert app_success is True
    assert app_job_id == "test_job_id"

    # Register the application for the benchmark
    mock_registry_manager.register_task_submission({
        "name": "test_app",
        "version": "1.0",
        "binary_path": os.path.join(standardized_test_env["outputs_dir"], "test_app"),
        "build_parameters": {},
        "metadata": {}
    }, standardized_test_env["temp_dir"])

    # Test benchmark run
    bench_success, bench_job_id, bench_script_path = orchestrator.execute(
        "test_benchmark", {"task_type": "benchmark"}, dry_run=False
    )
    assert bench_success is True
    assert bench_job_id == "test_job_id"
    assert os.path.exists(bench_script_path)
    assert bench_script_path.endswith(".sh")
 