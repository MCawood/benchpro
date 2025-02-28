"""Tests for the executor factory."""

import pytest
from unittest.mock import MagicMock

from benchpro.core.executor.local.executor import LocalExecutor
from benchpro.core.executor.slurm import SlurmExecutor
from benchpro.core.services.executor_factory import create_executor
from benchpro.core.services.settings import Settings
from benchpro.core.domain.errors import ExecutorError


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    
    # Store the return value so we can access it in the side effect
    settings._return_value = {"type": "local"}
    
    def get_side_effect(key, default=None):
        if key == "executor":
            return settings._return_value
        elif key == "working_dir":
            return "/tmp/benchpro"
        return default
        
    settings.get.side_effect = get_side_effect
    return settings


def test_create_local_executor(mock_settings):
    """Test creating local executor."""
    mock_settings._return_value = {"type": "local"}
    executor = create_executor(mock_settings)
    assert isinstance(executor, LocalExecutor)
    mock_settings.get.assert_any_call("executor", {})


def test_create_slurm_executor_system(mock_settings):
    """Test creating Slurm executor for system installation."""
    mock_settings._return_value = {
        "type": "slurm",
        "slurm_simulator": {"enabled": False}
    }
    with pytest.raises(ExecutorError, match="Slurm executor not yet implemented"):
        create_executor(mock_settings)
    mock_settings.get.assert_any_call("executor", {})


def test_create_slurm_executor_simulator(mock_settings):
    """Test creating Slurm executor for simulator."""
    mock_settings._return_value = {
        "type": "slurm",
        "slurm_simulator": {
            "enabled": True,
            "connection_type": "lima",
            "instance": "test-slurm"
        }
    }
    with pytest.raises(ExecutorError, match="Slurm executor not yet implemented"):
        create_executor(mock_settings)
    mock_settings.get.assert_any_call("executor", {})


def test_create_executor_default(mock_settings):
    """Test creating executor with default type."""
    mock_settings._return_value = {}
    executor = create_executor(mock_settings)
    assert isinstance(executor, LocalExecutor)
    mock_settings.get.assert_any_call("executor", {})


def test_create_executor_invalid_type(mock_settings):
    """Test creating executor with invalid type."""
    mock_settings._return_value = {"type": "invalid"}
    with pytest.raises(ExecutorError, match="Invalid executor type: invalid"):
        create_executor(mock_settings) 