"""Unit tests for the TaskRegistry class."""

import json
import time
from pathlib import Path
import pytest
from benchpro.core.domain.task_registry import TaskRegistry, TaskType, TaskRecord

@pytest.fixture
def task_registry(tmp_path, monkeypatch):
    """Create a TaskRegistry instance with temporary directories."""
    # Set up temporary XDG directories
    xdg_state = tmp_path / 'state'
    monkeypatch.setenv('XDG_STATE_HOME', str(xdg_state))
    
    return TaskRegistry()

def test_task_registry_initialization(task_registry, tmp_path):
    """Test that TaskRegistry initializes correctly."""
    # Check that registry file is in the correct location
    assert task_registry.registry_file.parent.name == 'benchpro'
    assert task_registry.registry_file.name == 'tasks.json'
    assert task_registry._tasks == {}

def test_register_task(task_registry):
    """Test registering a new task."""
    task = task_registry.register_task(
        task_id="test-1",
        name="Test Task",
        task_type=TaskType.BUILD,
        location=Path("/tmp/test"),
        variables={"key": "value"},
        metadata={"meta": "data"}
    )
    
    assert task.id == "test-1"
    assert task.name == "Test Task"
    assert task.type == TaskType.BUILD
    assert task.location == Path("/tmp/test")
    assert task.variables == {"key": "value"}
    assert task.metadata == {"meta": "data"}
    
    # Check that task was saved to registry
    assert task_registry.get_task("test-1") == task

def test_list_tasks(task_registry):
    """Test listing tasks with various filters."""
    # Register multiple tasks
    task_registry.register_task(
        task_id="build-1",
        name="Build 1",
        task_type=TaskType.BUILD,
        location=Path("/tmp/build1")
    )
    time.sleep(0.1)  # Ensure different timestamps
    task_registry.register_task(
        task_id="bench-1",
        name="Benchmark 1",
        task_type=TaskType.BENCHMARK,
        location=Path("/tmp/bench1")
    )
    
    # Test listing all tasks
    all_tasks = task_registry.list_tasks()
    assert len(all_tasks) == 2
    
    # Test filtering by type
    build_tasks = task_registry.list_tasks(task_type=TaskType.BUILD)
    assert len(build_tasks) == 1
    assert build_tasks[0].id == "build-1"
    
    # Test limiting results
    limited_tasks = task_registry.list_tasks(limit=1)
    assert len(limited_tasks) == 1
    assert limited_tasks[0].id == "bench-1"  # Most recent task

def test_prune_history(task_registry):
    """Test pruning task history."""
    # Register multiple tasks
    for i in range(5):
        task_registry.register_task(
            task_id=f"task-{i}",
            name=f"Task {i}",
            task_type=TaskType.BUILD,
            location=Path(f"/tmp/task{i}")
        )
        time.sleep(0.1)  # Ensure different timestamps
    
    # Prune to 3 tasks
    task_registry.prune_history(3)
    
    # Check that only the 3 most recent tasks remain
    tasks = task_registry.list_tasks()
    assert len(tasks) == 3
    assert tasks[0].id == "task-4"
    assert tasks[1].id == "task-3"
    assert tasks[2].id == "task-2"

def test_persistence(task_registry):
    """Test that tasks persist across registry instances."""
    # Register a task
    task_registry.register_task(
        task_id="persist-1",
        name="Persistent Task",
        task_type=TaskType.BUILD,
        location=Path("/tmp/persist")
    )
    
    # Create new registry instance
    new_registry = TaskRegistry()
    
    # Check that task was loaded
    task = new_registry.get_task("persist-1")
    assert task is not None
    assert task.name == "Persistent Task"
    assert task.type == TaskType.BUILD
    assert task.location == Path("/tmp/persist")

def test_invalid_registry_file(task_registry):
    """Test handling of invalid registry file."""
    # Write invalid JSON to registry file
    task_registry.registry_file.write_text("invalid json")
    
    # Create new registry instance
    new_registry = TaskRegistry()
    
    # Check that registry is empty
    assert new_registry._tasks == {} 