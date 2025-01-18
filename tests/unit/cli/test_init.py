"""Unit tests for the initialization command."""

import pytest
import shutil
from pathlib import Path
import os
from click.testing import CliRunner
from benchpro.cli import cli

@pytest.fixture
def cleanup_workspace():
    """Clean up the test workspace after tests."""
    # This runs before each test
    yield
    
    # This runs after each test
    test_dir = Path.cwd() / 'testing' / 'benchpro'
    if test_dir.exists():
        shutil.rmtree(test_dir)

@pytest.fixture(autouse=True)
def setup_testing_env():
    """Set up testing environment."""
    # Save original environment
    old_env = os.environ.get('BENCHPRO_TESTING')
    
    # Set testing environment
    os.environ['BENCHPRO_TESTING'] = '1'
    
    yield
    
    # Restore original environment
    if old_env is not None:
        os.environ['BENCHPRO_TESTING'] = old_env
    else:
        del os.environ['BENCHPRO_TESTING']

def test_init_basic(cleanup_workspace):
    """Test basic initialization."""
    runner = CliRunner()
    result = runner.invoke(cli, ['init', '--testing'])
    
    assert result.exit_code == 0
    
    # Check workspace directory structure
    workspace_dir = Path.cwd() / 'testing' / 'benchpro'
    assert workspace_dir.exists()
    
    # Check all directories exist
    expected_dirs = ['tasks', 'jobs', 'templates', 'applications', 'cache', 'logs']
    for dir_name in expected_dirs:
        assert (workspace_dir / dir_name).is_dir()
        
    # Check config file exists and is valid
    config_file = workspace_dir / 'config.yaml'
    assert config_file.exists()
    assert 'workspace:' in config_file.read_text()

def test_init_force(cleanup_workspace):
    """Test force reinitialization."""
    runner = CliRunner()
    
    # First initialization
    result = runner.invoke(cli, ['init', '--testing'])
    assert result.exit_code == 0
    
    # Create a test file in the workspace
    workspace_dir = Path.cwd() / 'testing' / 'benchpro'
    test_file = workspace_dir / 'test.txt'
    test_file.write_text('test content')
    
    # Try to initialize again without force
    result = runner.invoke(cli, ['init', '--testing'])
    assert result.exit_code == 0
    assert "already exists" in result.output
    assert test_file.exists()  # File should still exist
    
    # Initialize with force
    result = runner.invoke(cli, ['init', '--testing', '--force'])
    assert result.exit_code == 0
    assert not test_file.exists()  # File should be gone 