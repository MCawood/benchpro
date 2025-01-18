"""Unit tests for the Settings service."""

import pytest
from pathlib import Path
import yaml
import os
from benchpro.core.services.settings import Settings, ImmutableSettingError, InvalidValueError

@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings singleton before each test."""
    Settings.reset()
    yield

@pytest.fixture
def mock_settings_files(tmp_path, monkeypatch):
    """Create mock settings files for testing."""
    # Create package data directory
    pkg_dir = tmp_path / "benchpro" / "data" / "settings"
    pkg_dir.mkdir(parents=True)
    
    # Create defaults file
    defaults = {
        "metadata": {
            "file_version": "1.0",
            "last_updated": "2024-01-07T12:00:00"
        },
        "settings": {
            "immutable": {
                "version": {
                    "value": "1.0.0",
                    "type": "str",
                    "description": "BenchPro version"
                }
            },
            "site_mutable": {
                "testing": {
                    "value": False,
                    "type": "bool",
                    "description": "Testing mode"
                },
                "workspace_root": {
                    "value": "${HOME}/benchpro",
                    "type": "str",
                    "description": "Root directory for workspace"
                },
                "workspace_dirs": {
                    "value": {
                        "tasks": "${TASKS_DIR:-tasks}",
                        "jobs": "jobs",
                        "templates": "templates"
                    },
                    "type": "dict",
                    "description": "Directory structure"
                }
            },
            "user_mutable": {
                "debug": {
                    "value": False,
                    "type": "bool",
                    "description": "Debug mode"
                }
            }
        }
    }
    with open(pkg_dir / "defaults.yaml", "w") as f:
        yaml.safe_dump(defaults, f)
    
    # Create testing settings
    testing = {
        "metadata": {
            "file_version": "1.0",
            "description": "Testing configuration"
        },
        "settings": {
            "site_mutable": {
                "testing": {
                    "value": True,
                    "type": "bool",
                    "description": "Testing mode"
                },
                "workspace_root": {
                    "value": "${HOME}/.benchpro_testing",
                    "type": "str",
                    "description": "Testing workspace root"
                },
                "workspace_dirs": {
                    "value": {
                        "tasks": "${TASKS_DIR:-tasks}",
                        "jobs": "jobs",
                        "templates": "templates"
                    },
                    "type": "dict",
                    "description": "Directory structure"
                }
            }
        }
    }
    with open(pkg_dir / "testing.yaml", "w") as f:
        yaml.safe_dump(testing, f)
    
    # Create user settings directory
    user_dir = tmp_path / ".benchpro"
    user_dir.mkdir()
    
    # Mock paths and environment
    def mock_home():
        return tmp_path
    
    def mock_resources_files(package):
        return tmp_path / package
    
    monkeypatch.setattr(Path, "home", mock_home)
    monkeypatch.setattr("importlib.resources.files", mock_resources_files)
    monkeypatch.setenv("HOME", str(tmp_path))
    
    return tmp_path

def test_settings_loading(mock_settings_files):
    """Test loading settings from all sources."""
    settings = Settings()
    
    # Test metadata
    assert settings._metadata["file_version"] == "1.0"
    
    # Test immutable settings
    version = settings.get_setting_info("version")
    assert version.value == "1.0.0"
    assert version.level == "immutable"
    assert version.origin == "default"
    
    # Test site-mutable settings
    testing = settings.get_setting_info("testing")
    assert testing.value is False  # Default value
    assert testing.level == "site_mutable"
    assert testing.origin == "default"
    
    # Test user-mutable settings
    debug = settings.get_setting_info("debug")
    assert debug.value is False
    assert debug.level == "user_mutable"
    assert debug.origin == "default"

def test_type_validation(mock_settings_files):
    """Test type validation for settings."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Try to set a string value for a boolean setting
    with pytest.raises(InvalidValueError) as exc:
        settings.set("debug", "not a boolean")
    assert "type bool" in str(exc.value)

def test_reset_settings(mock_settings_files):
    """Test resetting settings to defaults."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Change a setting
    settings.set("debug", True)
    assert settings.get("debug") is True
    
    # Reset settings
    settings.reset()
    settings = Settings()  # Get new instance
    assert settings.get("debug") is False  # Back to default

def test_env_var_expansion(mock_settings_files, monkeypatch):
    """Test basic environment variable expansion in settings."""
    monkeypatch.setenv("TEST_VAR", "test_value")
    
    settings = Settings()
    settings.set("testing", True)
    
    settings.set("test_basic", "${TEST_VAR}")
    assert settings.get("test_basic") == "test_value"

def test_env_var_expansion_in_dict(mock_settings_files, monkeypatch):
    """Test environment variable expansion in dictionary values."""
    monkeypatch.setenv("ROOT", "/data")
    
    settings = Settings()
    settings.set("testing", True)
    
    test_dict = {
        "basic": "${ROOT}",
        "path": "${ROOT}/apps"
    }
    settings.set("test_dict", test_dict)
    
    result = settings.get("test_dict")
    assert result["basic"] == "/data"
    assert result["path"] == "/data/apps"

def test_env_var_expansion_missing_var(mock_settings_files):
    """Test handling of missing environment variables."""
    settings = Settings()
    settings.set("testing", True)
    
    settings.set("test_missing", "${NONEXISTENT}")
    assert settings.get("test_missing") == ""

def test_env_var_expansion_in_user_settings(mock_settings_files, monkeypatch):
    """Test environment variable expansion in user settings."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Set a custom environment variable
    monkeypatch.setenv("CUSTOM_PATH", "/custom/path")
    
    # Set a setting with an environment variable
    settings.set("workspace_root", "${CUSTOM_PATH}/benchpro")
    
    # Verify expansion
    assert settings.get("workspace_root") == "/custom/path/benchpro"

def test_env_var_expansion_in_reload(mock_settings_files, monkeypatch):
    """Test environment variable expansion after reload with changed env vars."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Initial state
    monkeypatch.setenv("CUSTOM_DIR", "dir1")
    settings.set("workspace_root", "${CUSTOM_DIR}/benchpro")
    assert settings.get("workspace_root") == "dir1/benchpro"
    
    # Change environment variable
    monkeypatch.setenv("CUSTOM_DIR", "dir2")
    settings.reset()
    settings = Settings()  # Get new instance
    assert settings.get("workspace_root") == str(mock_settings_files / "benchpro")  # Back to default

def test_no_expansion_for_non_string_values(mock_settings_files):
    """Test that non-string values are not processed for expansion."""
    settings = Settings()
    
    # Boolean setting
    assert settings.get("debug") is False
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Set and verify boolean remains boolean
    settings.set("debug", True)
    assert settings.get("debug") is True

def test_env_var_expansion_malformed(mock_settings_files, monkeypatch):
    """Test handling of malformed environment variable syntax."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Test unclosed variable
    settings.set("workspace_root", "${HOME/unclosed")
    assert settings.get("workspace_root") == "${HOME/unclosed"  # Left unchanged

def test_env_var_expansion_with_special_chars(mock_settings_files, monkeypatch):
    """Test environment variable expansion with special characters."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Test path with spaces
    monkeypatch.setenv("SPACE_PATH", "/path with spaces")
    settings.set("workspace_root", "${SPACE_PATH}/benchpro")
    assert settings.get("workspace_root") == "/path with spaces/benchpro"

def test_env_var_expansion_multiple_vars(mock_settings_files, monkeypatch):
    """Test expansion of multiple environment variables in one value."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Set multiple environment variables
    monkeypatch.setenv("PREFIX", "/prefix")
    monkeypatch.setenv("SUFFIX", "suffix")
    
    # Test multiple variables in one string
    settings.set("workspace_root", "${PREFIX}/middle/${SUFFIX}")
    assert settings.get("workspace_root") == "/prefix/middle/suffix"

def test_env_var_expansion_in_dict_errors(mock_settings_files, monkeypatch):
    """Test error cases for environment variable expansion in dictionaries."""
    settings = Settings()
    settings._settings["testing"].value = True

    # Test dictionary with malformed variables
    dirs = {
        "malformed": "${HOME/unclosed",
        "empty": "${}/path",
    }
    settings.set("workspace_dirs", dirs)
    result = settings.get("workspace_dirs")

    # Variables should be left unchanged if malformed
    assert result["malformed"] == "${HOME/unclosed"
    assert result["empty"] == "${}/path"

def test_env_var_expansion_type_conversion(mock_settings_files, monkeypatch):
    """Test type conversion after environment variable expansion."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Test with valid path characters
    monkeypatch.setenv("VALID_PATH", "/valid/path")
    settings.set("workspace_root", "${VALID_PATH}")
    assert settings.get("workspace_root") == "/valid/path"

def test_env_var_expansion_unicode(mock_settings_files, monkeypatch):
    """Test environment variable expansion with Unicode characters."""
    settings = Settings()
    
    # Enable testing mode to allow setting site_mutable settings
    settings._settings["testing"].value = True
    
    # Test Unicode in environment variables
    monkeypatch.setenv("UNICODE_PATH", "/path/测试/目录")
    settings.set("workspace_root", "${UNICODE_PATH}/benchpro")
    assert settings.get("workspace_root") == "/path/测试/目录/benchpro" 

def test_env_var_expansion_in_dict_nested(mock_settings_files, monkeypatch):
    """Test environment variable expansion in nested dictionary values."""
    settings = Settings()
    settings._settings["testing"].value = True
    
    # Set up environment variables
    monkeypatch.setenv("ROOT", "/root")
    monkeypatch.setenv("SUB", "sub")
    
    # Create a nested dictionary with environment variables
    workspace_dirs = {
        "base": "${ROOT}",
        "sub": {
            "path": "${ROOT}/${SUB}",
            "nested": {
                "deep": "${ROOT}/${SUB}/deep"
            }
        }
    }
    
    settings.set("workspace_dirs", workspace_dirs)
    result = settings.get("workspace_dirs")
    
    # Verify expansion at all levels
    assert result["base"] == "/root"
    assert result["sub"]["path"] == "/root/sub"
    assert result["sub"]["nested"]["deep"] == "/root/sub/deep"

def test_env_var_expansion_with_special_chars(mock_settings_files, monkeypatch):
    """Test environment variable expansion with special characters."""
    settings = Settings()
    settings._settings["testing"].value = True
    
    # Set up environment variables with special characters
    monkeypatch.setenv("PATH_WITH_SPACES", "/path with spaces")
    monkeypatch.setenv("PATH_WITH_SPECIAL", "!@#$%^&*()")
    
    # Test expansion with special characters
    settings.set("workspace_root", "${PATH_WITH_SPACES}/benchpro")
    assert settings.get("workspace_root") == "/path with spaces/benchpro"
    
    settings.set("workspace_root", "${PATH_WITH_SPECIAL}/benchpro")
    assert settings.get("workspace_root") == "!@#$%^&*()/benchpro" 