"""Test the hello world template execution through CLI."""
import os
import pytest
import asyncio
from click.testing import CliRunner
from benchpro.cli.task import task

@pytest.fixture
def event_loop():
    """Create an event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()

@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # Create tasks directory
    (workspace / "tasks").mkdir()
    return workspace

def test_hello_world_execution(runner, workspace_dir):
    """Test executing the hello world template."""
    # Initialize workspace
    result = runner.invoke(task, ['init', str(workspace_dir)])
    assert result.exit_code == 0
    
    # Create task using hello world template
    task_name = "hello_test"
    result = runner.invoke(task, [
        'create',
        task_name,
        '--template', 'tests/data/templates/hello/hello_world.sh',
        '--working-dir', str(workspace_dir / 'tasks' / task_name)
    ], obj={'cwd': str(workspace_dir)})
    assert result.exit_code == 0
    assert f"Task '{task_name}' created successfully" in result.output
    
    # Run the task
    result = runner.invoke(task, ['run', task_name], obj={'cwd': str(workspace_dir)})
    assert result.exit_code == 0
    assert f"Started task '{task_name}'" in result.output
    
    # Check task status
    result = runner.invoke(task, ['status', task_name], obj={'cwd': str(workspace_dir)})
    assert result.exit_code == 0
    assert "COMPLETED" in result.output

def test_hello_world_nonexistent_workspace(runner):
    """Test executing hello world without initializing workspace."""
    result = runner.invoke(task, [
        'create',
        'hello_fail',
        '--template', 'tests/data/templates/hello/hello_world.sh',
        '--working-dir', '/nonexistent/path'
    ])
    assert result.exit_code != 0
    assert "read-only file system" in result.output.lower()

def test_hello_world_list_tasks(runner, workspace_dir):
    """Test listing tasks after creating hello world task."""
    # Initialize workspace
    runner.invoke(task, ['init', str(workspace_dir)])
    
    # Create hello world task
    task_name = "hello_list"
    runner.invoke(task, [
        'create',
        task_name,
        '--template', 'tests/data/templates/hello/hello_world.sh',
        '--working-dir', str(workspace_dir / 'tasks' / task_name)
    ], obj={'cwd': str(workspace_dir)})
    
    # List tasks
    result = runner.invoke(task, ['list'], obj={'cwd': str(workspace_dir)})
    assert result.exit_code == 0
    assert task_name in result.output 