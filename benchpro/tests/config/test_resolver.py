"""
Tests for the TemplateVariableResolver class.
"""

import os
import pytest
from copy import deepcopy

from benchpro.config.resolver import TemplateVariableResolver


@pytest.fixture
def variable_resolver():
    """Create a TemplateVariableResolver for testing."""
    return TemplateVariableResolver()


def test_resolve_simple(variable_resolver):
    """Test resolving simple variable references."""
    # Create a configuration with variable references
    config = {
        "name": "test",
        "reference": "${name}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check the result
    assert result["name"] == "test"
    assert result["reference"] == "test"
    
    # Check that the original configuration was not modified
    assert config["reference"] == "${name}"


def test_resolve_nested(variable_resolver):
    """Test resolving nested variable references."""
    # Create a configuration with nested variable references
    config = {
        "app": {
            "name": "test",
            "version": "1.0"
        },
        "reference": "${app.name}",
        "full_name": "${app.name}-${app.version}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check the result
    assert result["app"]["name"] == "test"
    assert result["app"]["version"] == "1.0"
    assert result["reference"] == "test"
    assert result["full_name"] == "test-1.0"


def test_resolve_recursive(variable_resolver):
    """Test resolving recursive variable references."""
    # Create a configuration with recursive variable references
    config = {
        "base": "test",
        "derived": "${base}",
        "recursive": "${derived}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check the result
    assert result["base"] == "test"
    assert result["derived"] == "test"
    assert result["recursive"] == "test"


def test_resolve_environment_variables(variable_resolver, monkeypatch):
    """Test resolving environment variables."""
    # Set environment variables
    monkeypatch.setenv("TEST_VAR", "test_value")
    monkeypatch.setenv("ANOTHER_VAR", "another_value")
    
    # Create a configuration with environment variable references
    config = {
        "env_var": "${ENV:TEST_VAR}",
        "combined": "${ENV:TEST_VAR}-${ENV:ANOTHER_VAR}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check the result
    assert result["env_var"] == "test_value"
    assert result["combined"] == "test_value-another_value"


def test_resolve_missing_variable(variable_resolver):
    """Test resolving a missing variable."""
    # Create a configuration with a missing variable reference
    config = {
        "reference": "${missing}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check that the reference is unchanged
    assert result["reference"] == "${missing}"


def test_resolve_missing_environment_variable(variable_resolver):
    """Test resolving a missing environment variable."""
    # Create a configuration with a missing environment variable reference
    config = {
        "env_var": "${ENV:MISSING_VAR}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check that the reference is unchanged
    assert result["env_var"] == "${ENV:MISSING_VAR}"


def test_resolve_circular_reference(variable_resolver):
    """Test resolving circular variable references."""
    # Create a configuration with circular variable references
    config = {
        "a": "${b}",
        "b": "${a}"
    }
    
    # Resolve the variables
    with pytest.raises(ValueError) as excinfo:
        variable_resolver.resolve(config)
    
    # Check the error message
    assert "Circular reference detected" in str(excinfo.value)


def test_resolve_complex(variable_resolver, monkeypatch):
    """Test resolving a complex configuration with various types of references."""
    # Set environment variables
    monkeypatch.setenv("HOME", "/home/user")
    
    # Create a complex configuration
    config = {
        "app": {
            "name": "test",
            "version": "1.0"
        },
        "paths": {
            "home": "${ENV:HOME}",
            "app_dir": "${ENV:HOME}/apps/${app.name}"
        },
        "full_name": "${app.name}-${app.version}",
        "install_path": "${paths.app_dir}/${full_name}"
    }
    
    # Resolve the variables
    result = variable_resolver.resolve(config)
    
    # Check the result
    assert result["app"]["name"] == "test"
    assert result["app"]["version"] == "1.0"
    assert result["paths"]["home"] == "/home/user"
    assert result["paths"]["app_dir"] == "/home/user/apps/test"
    assert result["full_name"] == "test-1.0"
    assert result["install_path"] == "/home/user/apps/test/test-1.0" 