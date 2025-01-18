"""Unit tests for the SystemPaths service."""

import os
import pytest
from pathlib import Path
from benchpro.core.services.system_paths import SystemPaths

@pytest.fixture
def system_paths(tmp_path, monkeypatch):
    """Create SystemPaths instance with temporary directories."""
    # Set up temporary XDG directories
    xdg_config = tmp_path / 'config'
    xdg_cache = tmp_path / 'cache'
    xdg_data = tmp_path / 'data'
    xdg_state = tmp_path / 'state'
    
    # Set environment variables
    monkeypatch.setenv('XDG_CONFIG_HOME', str(xdg_config))
    monkeypatch.setenv('XDG_CACHE_HOME', str(xdg_cache))
    monkeypatch.setenv('XDG_DATA_HOME', str(xdg_data))
    monkeypatch.setenv('XDG_STATE_HOME', str(xdg_state))
    
    return SystemPaths()

def test_system_paths_initialization(system_paths, tmp_path):
    """Test that SystemPaths creates necessary directories."""
    # Check that base directories exist
    assert system_paths.config_dir.exists()
    assert system_paths.cache_dir.exists()
    assert system_paths.data_dir.exists()
    assert system_paths.state_dir.exists()
    
    # Check that directories are in the correct location
    assert system_paths.config_dir == Path(tmp_path) / 'config' / 'benchpro'
    assert system_paths.cache_dir == Path(tmp_path) / 'cache' / 'benchpro'
    assert system_paths.data_dir == Path(tmp_path) / 'data' / 'benchpro'
    assert system_paths.state_dir == Path(tmp_path) / 'state' / 'benchpro'

def test_get_config_file(system_paths, tmp_path):
    """Test getting configuration file paths."""
    config_file = system_paths.get_config_file('test.yaml')
    assert config_file == Path(tmp_path) / 'config' / 'benchpro' / 'test.yaml'

def test_get_cache_dir(system_paths, tmp_path):
    """Test getting cache directory paths."""
    # Test without subdirectory
    cache_dir = system_paths.get_cache_dir()
    assert cache_dir == Path(tmp_path) / 'cache' / 'benchpro'
    
    # Test with subdirectory
    subdir = system_paths.get_cache_dir('test')
    assert subdir == Path(tmp_path) / 'cache' / 'benchpro' / 'test'
    assert subdir.exists()

def test_get_data_file(system_paths, tmp_path):
    """Test getting data file paths."""
    data_file = system_paths.get_data_file('test.dat')
    assert data_file == Path(tmp_path) / 'data' / 'benchpro' / 'test.dat'

def test_get_state_file(system_paths, tmp_path):
    """Test getting state file paths."""
    state_file = system_paths.get_state_file('test.state')
    assert state_file == Path(tmp_path) / 'state' / 'benchpro' / 'test.state'

def test_get_log_file(system_paths, tmp_path):
    """Test getting log file paths."""
    # Test that log directory is created
    log_file = system_paths.get_log_file('test.log')
    assert log_file.parent.exists()
    assert log_file == Path(tmp_path) / 'state' / 'benchpro' / 'logs' / 'test.log'

def test_fallback_paths(monkeypatch):
    """Test fallback paths when XDG variables are not set."""
    # Clear XDG environment variables
    for var in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME'):
        monkeypatch.delenv(var, raising=False)
    
    paths = SystemPaths()
    home = Path.home()
    
    # Check fallback paths
    assert paths.config_dir == home / '.config' / 'benchpro'
    assert paths.cache_dir == home / '.cache' / 'benchpro'
    assert paths.data_dir == home / '.local' / 'share' / 'benchpro'
    assert paths.state_dir == home / '.local' / 'state' / 'benchpro' 