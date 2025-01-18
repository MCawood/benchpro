"""Test task execution commands."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from click.testing import CliRunner
from pathlib import Path
from benchpro.cli.task import task
from benchpro.core.domain import Task, TaskState

@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()

@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    workspace = tmp_path
    (workspace / "tasks").mkdir()
    return workspace

@pytest.fixture
def mock_task(workspace):
    """Create a mock task."""
    # Create a temporary template file
    template_path = workspace / "test.sh"
    template_path.write_text("#!/bin/bash\necho 'test'")
    
    # Create task working directory
    task_dir = workspace / "tasks" / "test-task"
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy template to run.sh in task directory
    import shutil
    run_script = task_dir / "run.sh"
    shutil.copy2(template_path, run_script)
    
    return Task(
        name="test-task",
        working_dir=task_dir,
        template_path=run_script,
        variables={
            "cores": 1,
            "memory": "1G",
            "walltime": 3600
        }
    )

@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.run = AsyncMock()
    executor.status = AsyncMock(return_value=TaskState.COMPLETED)
    executor.stop = AsyncMock()
    executor.cleanup = AsyncMock()
    return executor

def test_task_run_basic(runner, workspace, mock_task, mock_executor):
    """Test running a task with basic configuration."""
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['run', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 0
        assert f"Starting task '{mock_task.name}'" in result.output

def test_task_run_with_env(runner, workspace, mock_task, mock_executor):
    """Test running a task with environment variables."""
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, [
            'run', 'test-task',
            '--env', 'VAR1=value1',
            '--env', 'VAR2=value2'
        ], obj={'cwd': str(workspace)})
        assert result.exit_code == 0
        assert f"Starting task '{mock_task.name}'" in result.output

def test_task_status_running(runner, workspace, mock_task, mock_executor):
    """Test checking status of a running task."""
    mock_executor.status.return_value = TaskState.RUNNING
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['status', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 0
        assert "RUNNING" in result.output

def test_task_status_completed(runner, workspace, mock_task, mock_executor):
    """Test checking status of a completed task."""
    mock_executor.status.return_value = TaskState.COMPLETED
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['status', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 0
        assert "COMPLETED" in result.output

def test_task_status_failed(runner, workspace, mock_task, mock_executor):
    """Test checking status of a failed task."""
    mock_executor.status.return_value = TaskState.FAILED
    
    # Set up task state file
    task_dir = workspace / "tasks" / "test-task"
    task_dir.mkdir(parents=True, exist_ok=True)
    state_file = task_dir / "task_state.json"
    import json
    state_file.write_text(json.dumps({
        "state": TaskState.FAILED.value,
        "error": "Test failure message"
    }))
    
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['status', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "Error: Test failure message" in result.output

def test_task_stop_running(runner, workspace, mock_task, mock_executor):
    """Test stopping a running task."""
    mock_executor.status.return_value = TaskState.RUNNING
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['stop', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 0
        assert f"Stopped task '{mock_task.name}'" in result.output

def test_task_stop_not_running(runner, workspace, mock_task, mock_executor):
    """Test stopping a task that is not running."""
    mock_executor.status.return_value = TaskState.COMPLETED
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['stop', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 1
        assert "not running" in result.output.lower()

def test_task_run_cleanup_on_failure(runner, workspace, mock_task, mock_executor):
    """Test cleanup is called when task run fails."""
    mock_executor.run.side_effect = Exception("Test error")
    with patch('benchpro.cli.task.LocalExecutor', return_value=mock_executor):
        result = runner.invoke(task, ['run', 'test-task'], obj={'cwd': str(workspace)})
        assert result.exit_code == 1
        assert "Failed to run task" in result.output 