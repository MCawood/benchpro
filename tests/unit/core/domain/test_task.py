"""Unit tests for the Task model."""
import pytest
from pathlib import Path
from benchpro.core.domain import Task, TaskState
from benchpro.core.validation.validators import validate_memory_string

def test_task_creation_basic(tmp_path):
    """Test creating a task with basic parameters."""
    task = Task(
        name="test_task",
        working_dir=tmp_path / "test_task",
        template_path=None
    )
    assert task.name == "test_task"
    assert task.working_dir == tmp_path / "test_task"
    assert task.template_path is None
    assert task.state == TaskState.CREATED
    assert task.error is None
    assert task.variables == {}

def test_task_creation_with_template(tmp_path):
    """Test creating a task with a template."""
    template_path = tmp_path / "template.sh"
    template_path.touch()
    task = Task(
        name="test_task",
        working_dir=tmp_path / "test_task",
        template_path=template_path
    )
    assert task.template_path == template_path

def test_task_creation_with_variables(tmp_path):
    """Test creating a task with resource variables."""
    task = Task(
        name="test_task",
        working_dir=tmp_path / "test_task",
        variables={
            "cores": 2,
            "memory": "2G",
            "walltime": 3600
        }
    )
    assert task.variables["cores"] == 2
    assert task.variables["memory"] == "2G"
    assert task.variables["walltime"] == 3600

def test_task_invalid_memory(tmp_path):
    """Test task creation with invalid memory specification."""
    with pytest.raises(ValueError, match="Invalid memory format"):
        Task(
            name="test_task",
            working_dir=tmp_path / "test_task",
            variables={"memory": "invalid"}
        )

def test_task_state_transitions(tmp_path):
    """Test task state transitions."""
    task = Task(
        name="test_task",
        working_dir=tmp_path / "test_task"
    )
    assert task.state == TaskState.CREATED

    # Test valid transitions
    task.transition_to(TaskState.PENDING)
    assert task.state == TaskState.PENDING

    task.transition_to(TaskState.RUNNING)
    assert task.state == TaskState.RUNNING

    task.transition_to(TaskState.COMPLETED)
    assert task.state == TaskState.COMPLETED

    # Test invalid transitions
    with pytest.raises(ValueError):
        task.transition_to(TaskState.PENDING)  # Can't go back to PENDING from COMPLETED

def test_task_error_handling(tmp_path):
    """Test task error handling."""
    task = Task(
        name="test_task",
        working_dir=tmp_path / "test_task"
    )
    assert task.error is None
    
    error_msg = "Test error message"
    task.error = error_msg
    task.state = TaskState.FAILED
    assert task.error == error_msg
    assert task.state == TaskState.FAILED 