"""Tests for TaskManager service."""

import pytest
from pathlib import Path
from benchpro.core.services.task_manager import TaskManager
from benchpro.core.domain.task import Task
from benchpro.core.domain.states import TaskState

@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace."""
    workspace = tmp_path
    (workspace / "tasks").mkdir()
    return workspace

@pytest.fixture
def task_manager(workspace):
    """Create a TaskManager instance."""
    return TaskManager(workspace)

def test_validate_task_name(task_manager):
    """Test task name validation."""
    # Valid names
    assert task_manager.validate_task_name("task1") == "task1"
    assert task_manager.validate_task_name("my-task") == "my-task"
    assert task_manager.validate_task_name("task_123") == "task_123"
    
    # Invalid names
    with pytest.raises(ValueError):
        task_manager.validate_task_name("-task")  # Can't start with hyphen
    with pytest.raises(ValueError):
        task_manager.validate_task_name("task@123")  # Invalid character
    with pytest.raises(ValueError):
        task_manager.validate_task_name("task space")  # No spaces

def test_get_task_dir(task_manager, workspace):
    """Test getting task directory."""
    task_dir = task_manager.get_task_dir("test-task")
    assert task_dir == workspace / "tasks" / "test-task"

def test_create_task_basic(task_manager):
    """Test creating a basic task."""
    task = task_manager.create_task("test-task")
    assert task.name == "test-task"
    assert task.working_dir == task_manager.get_task_dir("test-task")
    assert task.template_path is None
    assert task.variables == {}
    assert task.working_dir.exists()

def test_create_task_with_template(task_manager, workspace):
    """Test creating a task with a template."""
    # Create a test template
    template_dir = workspace / "templates"
    template_dir.mkdir()
    template_path = template_dir / "test.sh"
    template_path.write_text("#!/bin/bash\necho 'test'")
    template_path.chmod(0o755)
    
    task = task_manager.create_task("test-task", template_path=template_path)
    assert task.name == "test-task"
    assert task.template_path == task.working_dir / "run.sh"
    assert task.template_path.exists()
    assert task.template_path.stat().st_mode & 0o755  # Check permissions

def test_create_task_with_variables(task_manager):
    """Test creating a task with variables."""
    variables = {
        "cores": 4,
        "memory": "8G",
        "walltime": 3600
    }
    task = task_manager.create_task("test-task", variables=variables)
    assert task.variables == variables

def test_create_task_with_custom_working_dir(task_manager, workspace):
    """Test creating a task with custom working directory."""
    custom_dir = workspace / "custom" / "path"
    task = task_manager.create_task("test-task", working_dir=custom_dir)
    assert task.working_dir == custom_dir
    assert task.working_dir.exists()

def test_get_task(task_manager):
    """Test getting an existing task."""
    # First create a task
    original_task = task_manager.create_task("test-task")
    
    # Create a dummy run.sh file
    run_script = original_task.working_dir / "run.sh"
    run_script.write_text("#!/bin/bash\necho 'test'")
    run_script.chmod(0o755)
    
    # Follow valid state transitions
    original_task.transition_to(TaskState.STAGING)
    original_task.transition_to(TaskState.PENDING)
    original_task.transition_to(TaskState.RUNNING)
    original_task.transition_to(TaskState.COMPLETED)
    original_task.save_state()
    
    # Now try to get it
    loaded_task = task_manager.get_task("test-task")
    assert loaded_task.name == original_task.name
    assert loaded_task.working_dir == original_task.working_dir
    assert loaded_task.state == TaskState.COMPLETED
    assert loaded_task.template_path == run_script

def test_get_nonexistent_task(task_manager):
    """Test getting a task that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        task_manager.get_task("nonexistent-task") 