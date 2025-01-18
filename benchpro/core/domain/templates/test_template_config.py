import pytest
from benchpro.core.domain.templates.config import TemplateConfig
from benchpro.core.domain.templates.exceptions import TemplateValidationError

@pytest.fixture
def valid_config():
    """Provide a valid template configuration for testing."""
    return {
        "name": "test_app",
        "version": "1.0.0",
        "type": "application",
        "build": {
            "language": "c",
            "compiler": "gcc",
            "binary": {
                "directory": "bin",
                "executable": "test_app"
            }
        },
        "source": {
            "files": ["src/main.c"]
        },
        "variables": {
            "TEST_VAR": "test_value"
        }
    }

def test_valid_config_creation(valid_config):
    """Test creating a template config with valid data."""
    config = TemplateConfig(valid_config)
    assert config.name == "test_app"
    assert str(config.version) == "1.0.0"  # Compare string representation
    assert config.type == "application"
    assert config.build["language"] == "c"
    assert config.build["compiler"] == "gcc"

def test_config_to_dict(valid_config):
    """Test converting config back to dictionary."""
    config = TemplateConfig(valid_config)
    config_dict = config.to_dict()
    
    # Compare only the fields that should be present
    expected = {
        'name': valid_config['name'],
        'version': valid_config['version'],
        'type': valid_config['type'],
        'build': valid_config['build'],
        'source': valid_config['source'],
        'variables': valid_config['variables']
    }
    assert config_dict == expected

def test_config_variable_access(valid_config):
    """Test accessing config variables."""
    config = TemplateConfig(valid_config)
    assert config.get_variable("TEST_VAR") == "test_value"
    assert config.get_variable("NONEXISTENT", default="default") == "default"
    # Test accessing non-existent variable without default
    with pytest.raises(KeyError):
        config.variables["NONEXISTENT"]

def test_missing_required_fields():
    """Test validation of missing required fields."""
    invalid_configs = [
        {},  # Empty config
        {"name": "test"},  # Missing version and type
        {  # Missing build section
            "name": "test",
            "version": "1.0.0",
            "type": "application"
        }
    ]

    for config in invalid_configs:
        with pytest.raises(TemplateValidationError, match="Missing required field"):
            TemplateConfig(config)

def test_invalid_type():
    """Test validation of template type."""
    config = {
        "name": "test",
        "version": "1.0.0",
        "type": "invalid_type",  # Only 'application' or 'benchmark' allowed
        "build": {
            "language": "c",
            "compiler": "gcc",
            "binary": {
                "directory": "bin",
                "executable": "test"
            }
        }
    }

    with pytest.raises(TemplateValidationError, match="Invalid template type"):
        TemplateConfig(config)

def test_invalid_build_config():
    """Test validation of build configuration."""
    invalid_builds = [
        {},  # Empty build config
        {"language": "c"},  # Missing compiler and binary
        {  # Missing binary info
            "language": "c",
            "compiler": "gcc"
        },
        {  # Invalid binary config
            "language": "c",
            "compiler": "gcc",
            "binary": {}
        }
    ]

    for build in invalid_builds:
        config = {
            "name": "test",
            "version": "1.0.0",
            "type": "application",
            "build": build,
            "source": {
                "files": ["src/main.c"]
            }
        }
        with pytest.raises(TemplateValidationError, match="validation error[s]? for BuildConfig"):
            TemplateConfig(config)

def test_variable_validation():
    """Test validation of template variables."""
    config = {
        "name": "test",
        "version": "1.0.0",
        "type": "application",
        "build": {
            "language": "c",
            "compiler": "gcc",
            "binary": {
                "directory": "bin",
                "executable": "test"
            }
        },
        "source": {
            "files": ["src/main.c"]
        },
        "variables": {
            "INVALID NAME": "value",  # Space in variable name
            "123_invalid": "value"    # Starts with number
        }
    }

    with pytest.raises(TemplateValidationError, match="Invalid variable name"):
        TemplateConfig(config)

def test_source_files_validation():
    """Test validation of source files configuration."""
    config = {
        "name": "test",
        "version": "1.0.0",
        "type": "application",
        "build": {
            "language": "c",
            "compiler": "gcc",
            "binary": {
                "directory": "bin",
                "executable": "test"
            }
        },
        "source": {
            "files": []  # Empty source files list
        }
    }

    with pytest.raises(TemplateValidationError, match="No source files specified"):
        TemplateConfig(config) 