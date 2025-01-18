"""Tests for event subscribers."""

import pytest
from unittest.mock import patch, call

from benchpro.core.domain.events import TaskStateChangedEvent, JobStateChangedEvent
from benchpro.core.domain.states import TaskState, JobState
from benchpro.core.services.event_bus import EventBus
from benchpro.core.services.event_subscribers import StateChangeLogger

@pytest.fixture
def event_bus():
    """Create a clean event bus for each test."""
    bus = EventBus()
    # Clear any existing handlers
    bus._handlers = {}
    return bus

@pytest.fixture
def state_logger(event_bus):
    """Create a StateChangeLogger instance."""
    return StateChangeLogger()

def test_task_state_change_logging(state_logger):
    """Test logging of task state changes."""
    with patch('benchpro.core.services.event_subscribers.logger') as mock_logger:
        # Create and publish a normal state change event
        event = TaskStateChangedEvent(
            task_id="test-task",
            old_state=TaskState.CREATED,
            new_state=TaskState.STAGING
        )
        EventBus().publish(event)
        
        # Verify normal state change was logged at INFO level
        mock_logger.info.assert_called_once_with(
            "Task %s state changed: %s -> %s",
            "test-task",
            TaskState.CREATED,
            TaskState.STAGING
        )
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Create and publish an error state change event
        error_event = TaskStateChangedEvent(
            task_id="test-task",
            old_state=TaskState.STAGING,
            new_state=TaskState.FAILED,
            error="Test error"
        )
        EventBus().publish(error_event)
        
        # Verify error state change was logged at WARNING level
        mock_logger.warning.assert_called_once_with(
            "Task %s state changed: %s -> %s (Error: %s)",
            "test-task",
            TaskState.STAGING,
            TaskState.FAILED,
            "Test error"
        )

def test_job_state_change_logging(state_logger):
    """Test logging of job state changes."""
    with patch('benchpro.core.services.event_subscribers.logger') as mock_logger:
        # Create and publish a normal state change event
        event = JobStateChangedEvent(
            job_id="test-job",
            task_id="test-task",
            old_state=JobState.CREATED,
            new_state=JobState.RUNNING
        )
        EventBus().publish(event)
        
        # Verify normal state change was logged at INFO level
        mock_logger.info.assert_called_once_with(
            "Job %s (Task %s) state changed: %s -> %s",
            "test-job",
            "test-task",
            JobState.CREATED,
            JobState.RUNNING
        )
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Create and publish an error state change event
        error_event = JobStateChangedEvent(
            job_id="test-job",
            task_id="test-task",
            old_state=JobState.RUNNING,
            new_state=JobState.FAILED,
            error="Test error"
        )
        EventBus().publish(error_event)
        
        # Verify error state change was logged at WARNING level
        mock_logger.warning.assert_called_once_with(
            "Job %s (Task %s) state changed: %s -> %s (Error: %s)",
            "test-job",
            "test-task",
            JobState.RUNNING,
            JobState.FAILED,
            "Test error"
        ) 