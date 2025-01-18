"""Tests for TaskStateManager service."""

import pytest
from unittest.mock import Mock, call
from pathlib import Path

from benchpro.core.domain.task import Task
from benchpro.core.domain.states import TaskState
from benchpro.core.domain.events import TaskStateChangedEvent
from benchpro.core.services.event_bus import EventBus
from benchpro.core.services.task_state_manager import (
    TaskStateManager,
    InvalidStateTransitionError
)

@pytest.fixture
def task():
    """Create a test task."""
    return Task(
        name="test_task",
        working_dir=Path("/tmp/test_task"),
        template_path=None
    )

@pytest.fixture
def state_manager():
    """Create a TaskStateManager instance."""
    return TaskStateManager()

def test_valid_state_transitions(state_manager, task):
    """Test valid state transitions."""
    # Test basic transitions
    state_manager.transition_to(task, TaskState.STAGING)
    assert task.state == TaskState.STAGING
    
    state_manager.transition_to(task, TaskState.PENDING)
    assert task.state == TaskState.PENDING
    
    state_manager.transition_to(task, TaskState.RUNNING)
    assert task.state == TaskState.RUNNING
    
    state_manager.transition_to(task, TaskState.COMPLETED)
    assert task.state == TaskState.COMPLETED

def test_invalid_state_transitions(state_manager, task):
    """Test invalid state transitions raise appropriate errors."""
    # Cannot go from CREATED to RUNNING directly
    with pytest.raises(InvalidStateTransitionError) as exc:
        state_manager.transition_to(task, TaskState.RUNNING)
    assert "Invalid state transition" in str(exc.value)
    
    # Cannot transition from COMPLETED state
    state_manager.transition_to(task, TaskState.STAGING)
    state_manager.transition_to(task, TaskState.PENDING)
    state_manager.transition_to(task, TaskState.RUNNING)
    state_manager.transition_to(task, TaskState.COMPLETED)
    
    with pytest.raises(InvalidStateTransitionError) as exc:
        state_manager.transition_to(task, TaskState.RUNNING)
    assert "Invalid state transition" in str(exc.value)

def test_failed_state_transitions(state_manager, task):
    """Test transitions to FAILED state."""
    # Can transition to FAILED from any state
    state_manager.transition_to(task, TaskState.FAILED, error="Test error")
    assert task.state == TaskState.FAILED
    assert task.error == "Test error"
    
    # Create new task since FAILED is terminal
    task = Task(name="test_task2", working_dir=Path("/tmp/test_task2"))
    
    # Test FAILED from different states
    state_manager.transition_to(task, TaskState.STAGING)
    state_manager.transition_to(task, TaskState.FAILED, error="Failed during staging")
    assert task.state == TaskState.FAILED
    assert task.error == "Failed during staging"

def test_cancelled_state_transitions(state_manager, task):
    """Test transitions to CANCELLED state."""
    # Can transition to CANCELLED from any state
    state_manager.transition_to(task, TaskState.CANCELLED)
    assert task.state == TaskState.CANCELLED
    
    # Create new task since CANCELLED is terminal
    task = Task(name="test_task2", working_dir=Path("/tmp/test_task2"))
    
    # Test CANCELLED from different states
    state_manager.transition_to(task, TaskState.STAGING)
    state_manager.transition_to(task, TaskState.PENDING)
    state_manager.transition_to(task, TaskState.CANCELLED)
    assert task.state == TaskState.CANCELLED

def test_transition_hooks(state_manager, task):
    """Test pre and post transition hooks."""
    def pre_hook(task, old_state, new_state): pass
    def post_hook(task, old_state, new_state): pass
    
    pre_mock = Mock(wraps=pre_hook)
    post_mock = Mock(wraps=post_hook)
    
    state_manager.add_pre_transition_hook(pre_mock)
    state_manager.add_post_transition_hook(post_mock)
    
    # Perform transition
    state_manager.transition_to(task, TaskState.STAGING)
    
    # Verify hooks were called
    pre_mock.assert_called_once_with(task, TaskState.CREATED, TaskState.STAGING)
    post_mock.assert_called_once_with(task, TaskState.CREATED, TaskState.STAGING)
    
    # Reset mocks
    pre_mock.reset_mock()
    post_mock.reset_mock()
    
    # Another transition
    state_manager.transition_to(task, TaskState.PENDING)
    
    # Verify hooks were called again
    pre_mock.assert_called_once_with(task, TaskState.STAGING, TaskState.PENDING)
    post_mock.assert_called_once_with(task, TaskState.STAGING, TaskState.PENDING)

def test_failed_pre_hook(state_manager, task):
    """Test that failed pre-hook prevents transition."""
    def pre_hook(task, old_state, new_state): 
        raise ValueError("Pre-hook failed")
    
    pre_mock = Mock(wraps=pre_hook)
    state_manager.add_pre_transition_hook(pre_mock)
    
    # Transition should fail
    with pytest.raises(ValueError) as exc:
        state_manager.transition_to(task, TaskState.STAGING)
    assert "Pre-hook failed" in str(exc.value)
    
    # State should not have changed
    assert task.state == TaskState.CREATED

def test_failed_post_hook(state_manager, task):
    """Test that failed post-hook doesn't revert transition."""
    def post_hook(task, old_state, new_state):
        raise ValueError("Post-hook failed")
    
    post_mock = Mock(wraps=post_hook)
    state_manager.add_post_transition_hook(post_mock)
    
    # Transition should succeed despite post-hook failure
    state_manager.transition_to(task, TaskState.STAGING)
    
    # State should have changed
    assert task.state == TaskState.STAGING
    
    # Post-hook should have been called
    post_mock.assert_called_once_with(task, TaskState.CREATED, TaskState.STAGING)

def test_multiple_hooks(state_manager, task):
    """Test multiple pre and post hooks."""
    def make_hook(name):
        def hook(task, old_state, new_state): pass
        hook.__name__ = name
        return Mock(wraps=hook)
    
    pre_hooks = [make_hook(f"pre_hook_{i}") for i in range(3)]
    post_hooks = [make_hook(f"post_hook_{i}") for i in range(3)]
    
    for hook in pre_hooks:
        state_manager.add_pre_transition_hook(hook)
    for hook in post_hooks:
        state_manager.add_post_transition_hook(hook)
        
    # Perform transition
    state_manager.transition_to(task, TaskState.STAGING)
    
    # Verify all hooks were called in order
    for hook in pre_hooks:
        hook.assert_called_once_with(task, TaskState.CREATED, TaskState.STAGING)
    for hook in post_hooks:
        hook.assert_called_once_with(task, TaskState.CREATED, TaskState.STAGING) 

def test_state_changed_event(state_manager, task):
    """Test that state changes emit events."""
    # Create event handler mock
    handler = Mock()
    event_bus = EventBus()
    event_bus.subscribe(TaskStateChangedEvent, handler)
    
    # Perform transition
    state_manager.transition_to(task, TaskState.STAGING)
    
    # Verify event was published
    handler.assert_called_once()
    event = handler.call_args[0][0]
    assert isinstance(event, TaskStateChangedEvent)
    assert event.task_id == task.id
    assert event.old_state == TaskState.CREATED
    assert event.new_state == TaskState.STAGING
    assert event.error is None
    
    # Reset mock
    handler.reset_mock()
    
    # Test transition with error
    error_msg = "Test error"
    state_manager.transition_to(task, TaskState.FAILED, error=error_msg)
    
    # Verify error event
    handler.assert_called_once()
    event = handler.call_args[0][0]
    assert event.old_state == TaskState.STAGING
    assert event.new_state == TaskState.FAILED
    assert event.error == error_msg

def test_event_handler_failure(state_manager, task):
    """Test that failed event handlers don't affect state transition."""
    def failing_handler(event):
        raise ValueError("Handler failed")
    
    # Add failing handler
    event_bus = EventBus()
    event_bus.subscribe(TaskStateChangedEvent, failing_handler)
    
    # Transition should still succeed
    state_manager.transition_to(task, TaskState.STAGING)
    assert task.state == TaskState.STAGING 