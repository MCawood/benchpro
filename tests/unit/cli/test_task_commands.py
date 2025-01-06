"""Test cases for task CLI commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import shutil
import tempfile
from benchpro.cli.task import task

@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()

@pytest.fixture
def workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir)
        (workspace_dir / 'tasks').mkdir()
        (workspace_dir / 'templates').mkdir()
        yield workspace_dir

def test_task_create_basic(runner, workspace):
    """Test creating a basic task."""
    result = runner.invoke(task, ['create', 'test-task'], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "Task 'test-task' created successfully" in result.output
    assert "Working directory:" in result.output
    assert "Resources: 1 cores, 1G memory, 3600s walltime" in result.output

def test_task_create_with_resources(runner, workspace):
    """Test creating a task with specific resource requirements."""
    result = runner.invoke(task, [
        'create', 'resource-task',
        '--cores', '4',
        '--memory', '2G',
        '--walltime', '7200'
    ], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "Task 'resource-task' created successfully" in result.output
    assert "Working directory:" in result.output
    assert "Resources: 4 cores, 2G memory, 7200s walltime" in result.output

def test_task_create_invalid_memory(runner, workspace):
    """Test creating a task with invalid memory specification."""
    result = runner.invoke(task, [
        'create', 'invalid-memory',
        '--memory', 'invalid'
    ], obj={'cwd': str(workspace)})
    assert result.exit_code != 0
    assert "Invalid memory format" in result.output

def test_task_list_empty(runner, workspace):
    """Test listing tasks when none exist."""
    result = runner.invoke(task, ['list'], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "No tasks found" in result.output

def test_task_list_with_tasks(runner, workspace):
    """Test listing tasks when some exist."""
    # Create some task directories
    (workspace / 'tasks' / 'task1').mkdir()
    (workspace / 'tasks' / 'task2').mkdir()
    
    result = runner.invoke(task, ['list'], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "task1" in result.output
    assert "task2" in result.output

def test_task_create_no_workspace(runner):
    """Test creating a task without initializing the workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(task, ['create', 'test-task'], obj={'cwd': tmpdir})
        assert result.exit_code != 0
        assert "Not in a BenchPRO workspace" in result.output

def test_task_create_invalid_name(runner, workspace):
    """Test creating a task with invalid characters in name."""
    result = runner.invoke(task, ['create', 'test/task'], obj={'cwd': str(workspace)})
    assert result.exit_code != 0
    assert "Invalid task name" in result.output

def test_task_create_with_invalid_template(runner, workspace):
    """Test creating a task with an invalid template file."""
    # Create a non-shell script template
    invalid_template = workspace / 'templates' / 'invalid.txt'
    invalid_template.write_text('not a shell script')
    
    result = runner.invoke(task, [
        'create', 'template-task',
        '--template', str(invalid_template)
    ], obj={'cwd': str(workspace)})
    assert result.exit_code != 0
    assert "Invalid template file" in result.output

def test_task_create_existing_directory(runner, workspace):
    """Test creating a task when the directory already exists."""
    # Create the task directory first
    task_dir = workspace / 'tasks' / 'existing-task'
    task_dir.mkdir()

    result = runner.invoke(task, ['create', 'existing-task'], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "Task 'existing-task' created successfully" in result.output
    assert "Working directory:" in result.output
    assert "Resources: 1 cores, 1G memory, 3600s walltime" in result.output

def test_task_list_with_subdirectories(runner, workspace):
    """Test listing tasks with nested directories."""
    # Create task directories with subdirectories
    (workspace / 'tasks' / 'task1').mkdir()
    (workspace / 'tasks' / 'task1' / 'output').mkdir()
    (workspace / 'tasks' / 'task2').mkdir()
    (workspace / 'tasks' / 'task2' / 'data').mkdir()
    
    result = runner.invoke(task, ['list'], obj={'cwd': str(workspace)})
    assert result.exit_code == 0
    assert "task1" in result.output
    assert "task2" in result.output
    # Subdirectories should not be listed
    assert "output" not in result.output
    assert "data" not in result.output 