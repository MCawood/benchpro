"""Unit tests for Job domain model."""

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from benchpro.core.domain.job import Job, JobResources, JobState
from benchpro.core.domain.task import Task, TaskState


@pytest.fixture
def valid_task_data(tmp_path: Path) -> dict:
    """Create valid task data for testing."""
    working_dir = tmp_path / "work"
    working_dir.mkdir()
    template = tmp_path / "job.sh"
    template.touch()
    
    return {
        "name": "test_task",
        "working_dir": working_dir,
        "template_path": template,
        "variables": {"cores": 4, "memory": "8G"},
    }


@pytest.fixture
def valid_job_data(tmp_path: Path, valid_task_data: dict) -> dict:
    """Create valid job data for testing."""
    working_dir = tmp_path / "job"
    working_dir.mkdir()
    
    task = Task(**valid_task_data)
    resources = JobResources(cores=4, memory="8G")
    
    return {
        "name": "test_job",
        "working_dir": working_dir,
        "tasks": [task],
        "resources": resources,
    }


def test_job_creation(valid_job_data: dict):
    """Test job creation with valid data."""
    job = Job(**valid_job_data)
    
    assert isinstance(job.id, UUID)
    assert job.name == "test_job"
    assert job.working_dir == valid_job_data["working_dir"]
    assert len(job.tasks) == 1
    assert job.resources.cores == 4
    assert job.resources.memory == "8G"
    assert job.state == JobState.CREATED
    assert job.error is None
    assert isinstance(job.created_at, datetime)
    assert job.started_at is None
    assert job.completed_at is None


def test_job_invalid_working_dir(valid_job_data: dict, tmp_path: Path):
    """Test job creation with invalid working directory."""
    valid_job_data["working_dir"] = tmp_path / "nonexistent"
    with pytest.raises(ValidationError, match="Directory does not exist"):
        Job(**valid_job_data)


def test_job_invalid_resources(valid_job_data: dict):
    """Test job creation with invalid resources."""
    # Test invalid cores
    valid_job_data["resources"] = {"cores": 0, "memory": "8G"}
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        Job(**valid_job_data)
    
    # Test invalid memory format
    valid_job_data["resources"] = {"cores": 4, "memory": "invalid"}
    with pytest.raises(ValidationError, match="Invalid memory string format"):
        Job(**valid_job_data)


def test_job_empty_tasks(valid_job_data: dict):
    """Test job creation with no tasks."""
    valid_job_data["tasks"] = []
    with pytest.raises(ValidationError, match="Job must have at least one task"):
        Job(**valid_job_data)


def test_job_state_transitions(valid_job_data: dict):
    """Test job state transitions and timestamps."""
    job = Job(**valid_job_data)
    assert job.state == JobState.CREATED
    assert job.started_at is None
    assert job.completed_at is None
    
    # Transition to QUEUED
    job.transition_to(JobState.QUEUED)
    assert job.state == JobState.QUEUED
    assert job.started_at is None
    assert job.completed_at is None
    
    # Transition to RUNNING
    job.transition_to(JobState.RUNNING)
    assert job.state == JobState.RUNNING
    assert isinstance(job.started_at, datetime)
    assert job.completed_at is None
    
    # Transition to COMPLETED
    job.transition_to(JobState.COMPLETED)
    assert job.state == JobState.COMPLETED
    assert isinstance(job.completed_at, datetime)


def test_job_invalid_transitions(valid_job_data: dict):
    """Test invalid job state transitions."""
    job = Job(**valid_job_data)
    
    # Cannot go directly to RUNNING
    with pytest.raises(ValueError, match="Invalid state transition"):
        job.transition_to(JobState.RUNNING)
    
    # Cannot transition from COMPLETED
    job.transition_to(JobState.QUEUED)
    job.transition_to(JobState.RUNNING)
    job.transition_to(JobState.COMPLETED)
    with pytest.raises(ValueError, match="Invalid state transition"):
        job.transition_to(JobState.RUNNING)


def test_job_duration(valid_job_data: dict):
    """Test job duration calculation."""
    job = Job(**valid_job_data)
    assert job.duration is None
    
    job.transition_to(JobState.QUEUED)
    assert job.duration is None
    
    job.transition_to(JobState.RUNNING)
    assert job.duration is not None
    assert job.duration >= 0
    
    job.transition_to(JobState.COMPLETED)
    final_duration = job.duration
    assert final_duration > 0
    
    # Duration should be fixed after completion
    assert job.duration == final_duration


def test_job_task_states(valid_job_data: dict):
    """Test task state tracking."""
    job = Job(**valid_job_data)
    task = job.tasks[0]
    
    # Initially all tasks are CREATED
    assert len(job.task_states[TaskState.CREATED]) == 1
    assert not job.has_failed_tasks
    assert not job.all_tasks_completed
    
    # Transition task through states
    task.transition_to(TaskState.PENDING)
    assert len(job.task_states[TaskState.PENDING]) == 1
    
    task.transition_to(TaskState.RUNNING)
    assert len(job.task_states[TaskState.RUNNING]) == 1
    
    task.transition_to(TaskState.COMPLETED)
    assert len(job.task_states[TaskState.COMPLETED]) == 1
    assert job.all_tasks_completed


def test_job_failed_tasks(valid_job_data: dict):
    """Test failed task detection."""
    job = Job(**valid_job_data)
    task = job.tasks[0]
    
    task.transition_to(TaskState.PENDING)
    task.transition_to(TaskState.RUNNING)
    task.transition_to(TaskState.FAILED, error="Test error")
    
    assert job.has_failed_tasks
    assert not job.all_tasks_completed


def test_job_string_representation(valid_job_data: dict):
    """Test job string representation."""
    job = Job(**valid_job_data)
    assert str(job) == "test_job (created) - Tasks: 0/1 completed"
    
    job.transition_to(JobState.QUEUED)
    job.transition_to(JobState.RUNNING)
    assert "test_job (running) - Duration:" in str(job)
    assert "Tasks: 0/1 completed" in str(job)
    
    # Fail the task
    task = job.tasks[0]
    task.transition_to(TaskState.PENDING)
    task.transition_to(TaskState.RUNNING)
    task.transition_to(TaskState.FAILED, error="Test error")
    
    job.transition_to(JobState.FAILED, error="Job failed")
    assert str(job) == "test_job (failed) - Error: Job failed - Tasks: 0/1 completed, 1 failed" 