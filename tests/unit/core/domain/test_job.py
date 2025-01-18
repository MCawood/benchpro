"""Tests for job domain model."""

import pytest
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, Any

from benchpro.core.domain.job import Job, JobState
from benchpro.core.domain.task import Task, TaskState

@pytest.fixture
def valid_task_data(tmp_path: Path) -> Dict[str, Any]:
    """Create valid task data for testing."""
    working_dir = tmp_path / "task"
    working_dir.mkdir()
    return {
        "name": "test_task",
        "working_dir": working_dir,
        "template_path": None,
        "variables": {}
    }

@pytest.fixture
def valid_job_data(tmp_path: Path, valid_task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create valid job data for testing."""
    working_dir = tmp_path / "job"
    working_dir.mkdir()
    task = Task(**valid_task_data)
    return {
        "name": "test_job",
        "working_dir": working_dir,
        "tasks": [task],
        "resources": {"cores": 4, "memory": "8G"}
    }

def test_job_creation(valid_job_data: Dict[str, Any]):
    """Test job creation with valid data."""
    job = Job(**valid_job_data)
    assert job.name == "test_job"
    assert job.state == JobState.CREATED
    assert len(job.tasks) == 1
    assert job.resources == {"cores": 4, "memory": "8G"}

def test_job_state_transitions(valid_job_data: Dict[str, Any]):
    """Test job state transitions."""
    job = Job(**valid_job_data)
    
    # Test valid transitions
    job.transition_to(JobState.QUEUED)
    assert job.state == JobState.QUEUED
    
    job.transition_to(JobState.RUNNING)
    assert job.state == JobState.RUNNING
    
    job.transition_to(JobState.COMPLETED)
    assert job.state == JobState.COMPLETED
    
    # Test invalid transitions
    with pytest.raises(ValueError):
        job.transition_to(JobState.QUEUED)

def test_job_failure(valid_job_data: Dict[str, Any]):
    """Test job failure handling."""
    job = Job(**valid_job_data)
    
    # Test transition to failed state with error message
    error_msg = "Test error"
    job.transition_to(JobState.FAILED, error_msg)
    assert job.state == JobState.FAILED
    assert job.error == error_msg

def test_job_cancellation(valid_job_data: Dict[str, Any]):
    """Test job cancellation."""
    job = Job(**valid_job_data)
    
    # Test transition to cancelled state
    job.transition_to(JobState.CANCELLED)
    assert job.state == JobState.CANCELLED

def test_job_duration(valid_job_data: Dict[str, Any]):
    """Test job duration calculation."""
    job = Job(**valid_job_data)
    
    # Duration should be None before starting
    assert job.duration is None
    
    # Start job
    job.transition_to(JobState.RUNNING)
    start_time = job.started_at
    assert start_time is not None
    
    # Complete job
    job.transition_to(JobState.COMPLETED)
    assert job.completed_at is not None
    assert job.duration is not None
    assert job.duration >= 0

def test_job_task_states(valid_job_data: Dict[str, Any]):
    """Test task state tracking."""
    job = Job(**valid_job_data)
    task = job.tasks[0]

    # Initial state
    assert not job.has_failed_tasks
    assert not job.all_tasks_completed

    # Complete task through proper sequence
    task.transition_to(TaskState.STAGING)
    task.transition_to(TaskState.PENDING)
    task.transition_to(TaskState.RUNNING)
    task.transition_to(TaskState.COMPLETED)
    assert not job.has_failed_tasks
    assert job.all_tasks_completed

    # Fail task (can transition to FAILED from any state)
    task.transition_to(TaskState.FAILED)
    assert job.has_failed_tasks
    assert not job.all_tasks_completed

def test_job_string_representation(valid_job_data: Dict[str, Any]):
    """Test job string representation."""
    job = Job(**valid_job_data)
    
    # Test initial state
    assert str(job) == "test_job (created) - Tasks: 0/1 completed"
    
    # Test with error
    job.transition_to(JobState.FAILED, "Test error")
    assert "Error: Test error" in str(job)
    
    # Test with duration
    job = Job(**valid_job_data)
    job.transition_to(JobState.RUNNING)
    job.transition_to(JobState.COMPLETED)
    assert "Duration:" in str(job) 