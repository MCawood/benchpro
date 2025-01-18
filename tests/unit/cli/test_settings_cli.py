"""Unit tests for the settings CLI commands."""

import pytest
from click.testing import CliRunner
from benchpro.cli import cli
from benchpro.core.services.settings import Settings

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()

@pytest.fixture
def mock_settings(monkeypatch, tmp_path):
    """Create a mock settings instance."""
    settings_file = tmp_path / 'settings.yaml'
    
    def mock_home():
        return tmp_path
    
    monkeypatch.setattr(Settings, '_instance', None)
    monkeypatch.setattr('pathlib.Path.home', mock_home)
    
    return Settings()

def test_list_settings(runner, mock_settings):
    """Test listing all settings."""
    result = runner.invoke(cli, ['settings', 'list'])
    assert result.exit_code == 0
    assert 'User-Editable Settings:' in result.output
    assert 'debug' in result.output  # Check for a known user-editable setting
    # Metadata should not be visible
    assert 'version:' not in result.output
    assert '_metadata:' not in result.output

def test_get_setting(runner, mock_settings):
    """Test getting a specific setting."""
    # Get existing setting
    result = runner.invoke(cli, ['settings', 'get', 'testing'])
    assert result.exit_code == 0
    assert 'Setting: testing' in result.output
    assert 'Value: false' in result.output
    
    # Get non-existent setting
    result = runner.invoke(cli, ['settings', 'get', 'nonexistent'])
    assert result.exit_code == 0
    assert "Setting 'nonexistent' not found" in result.output
    
    # Get immutable setting
    result = runner.invoke(cli, ['settings', 'get', 'version'])
    assert result.exit_code == 0
    assert 'Setting: version' in result.output
    assert 'Level: Immutable' in result.output
    assert 'Mutability: Cannot be modified' in result.output

def test_set_setting(runner, mock_settings):
    """Test setting values."""
    # Set boolean
    result = runner.invoke(cli, ['settings', 'set', 'debug', 'true'])
    assert result.exit_code == 0
    assert mock_settings.get('debug') is True
    
    # Set boolean back to false
    result = runner.invoke(cli, ['settings', 'set', 'debug', 'false'])
    assert result.exit_code == 0
    assert mock_settings.get('debug') is False
    
    # Try to set immutable setting (should fail)
    result = runner.invoke(cli, ['settings', 'set', 'version', '2.0'])
    assert result.exit_code == 0
    assert "Error: Setting 'version' cannot be modified" in result.output

def test_reset_settings(runner, mock_settings):
    """Test resetting settings to defaults."""
    # Change some settings
    mock_settings.set('debug', True)
    
    # Store metadata
    old_metadata = mock_settings._metadata.copy()
    
    # Reset with confirmation
    result = runner.invoke(cli, ['settings', 'reset'], input='y\n')
    assert result.exit_code == 0
    assert 'Settings reset to defaults' in result.output
    
    # Get a fresh instance to ensure we're getting the reset settings
    Settings.reset()  # Clear the singleton instance
    fresh_settings = Settings()  # Get a new instance
    assert fresh_settings.get('debug') is False  # Back to default
    
    # Metadata should be preserved
    assert fresh_settings._metadata == old_metadata
    
    # Reset without confirmation
    result = runner.invoke(cli, ['settings', 'reset'], input='n\n')
    assert result.exit_code == 0
    assert 'Settings reset to defaults' not in result.output 