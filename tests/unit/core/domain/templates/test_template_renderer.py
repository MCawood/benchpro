"""Unit tests for template rendering functionality."""
import pytest
from pathlib import Path
from benchpro.core.domain.templates import (
    TemplateRenderer,
    TemplateConfig,
    TemplateVariableError,
    TemplateSyntaxError,
    TemplateRenderError
)

@pytest.fixture
def template_config():
    """Return a template configuration for testing."""
    return TemplateConfig({
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
            "files": ["test.c"]
        },
        "variables": {
            "TEST_VAR": "test_value"
        }
    })

@pytest.fixture
def build_template():
    """Return a build template for testing."""
    return """#!/bin/bash
cd {{ working_dir }}
export TEST_VAR="{{ variables.TEST_VAR }}"

# Compile
{{ build.compiler }} -o {{ build.binary.executable }} test.c

# Install
mkdir -p {{ install_dir }}/{{ build.binary.directory }}
cp {{ build.binary.executable }} {{ install_dir }}/{{ build.binary.directory }}/"""

def test_renderer_creation(template_config, build_template):
    """Test creating a template renderer."""
    renderer = TemplateRenderer(template_config, build_template)
    assert renderer.config == template_config
    assert renderer.template == build_template

def test_basic_rendering(template_config, build_template):
    """Test basic template rendering with standard variables."""
    renderer = TemplateRenderer(template_config, build_template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    result = renderer.render(context)
    assert "cd /tmp/test" in result
    assert 'export TEST_VAR="test_value"' in result
    assert "gcc -o test_app test.c" in result
    assert "mkdir -p /opt/test/bin" in result
    assert "cp test_app /opt/test/bin/" in result

def test_missing_context_variable(template_config, build_template):
    """Test rendering with missing context variable."""
    renderer = TemplateRenderer(template_config, build_template)
    context = {
        "working_dir": "/tmp/test"
        # Missing install_dir
    }
    
    with pytest.raises(TemplateVariableError, match="Missing required context variable: install_dir"):
        renderer.render(context)

def test_override_config_variable(template_config, build_template):
    """Test overriding config variables through context."""
    renderer = TemplateRenderer(template_config, build_template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test",
        "variables": {
            "TEST_VAR": "overridden_value"
        }
    }
    
    result = renderer.render(context)
    assert 'export TEST_VAR="overridden_value"' in result

def test_invalid_template_syntax(template_config):
    """Test handling of invalid template syntax."""
    invalid_template = """#!/bin/bash
    cd {{ working_dir }
    # Missing closing brace"""
    
    renderer = TemplateRenderer(template_config, invalid_template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateSyntaxError, match="Invalid template syntax"):
        renderer.render(context)

def test_undefined_variable_access(template_config, build_template):
    """Test accessing undefined variables in template."""
    template_with_undefined = build_template + """
echo {{ undefined_variable }}"""
    
    renderer = TemplateRenderer(template_config, template_with_undefined)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateVariableError, match="Undefined template variable: undefined_variable"):
        renderer.render(context)

def test_strict_undefined_handling(template_config):
    """Test strict handling of undefined variables."""
    template = """#!/bin/bash
{% if undefined_var %}
echo "This should fail"
{% endif %}"""
    
    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateVariableError, match="Undefined template variable"):
        renderer.render(context)

def test_template_whitespace_control(template_config):
    """Test template whitespace control."""
    template = """#!/bin/bash
{%- for file in source.files %}
compile {{ file }}
{%- endfor %}
"""

    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }

    result = renderer.render(context)
    # Just verify the content is present and in order
    assert result.startswith("#!/bin/bash")
    assert "compile test.c" in result
    assert not result.endswith("\n\n")  # No extra blank lines

def test_complex_template_logic(template_config):
    """Test more complex template logic."""
    template = """#!/bin/bash
{% if build.language == 'c' -%}
{{ build.compiler }} {% if build.optimization|default(false) %}-O2{% endif %} -o {{ build.binary.executable }} {{ source.files|join(' ') }}
{% elif build.language == 'c++' -%}
{{ build.compiler }} -std=c++11 -o {{ build.binary.executable }} {{ source.files|join(' ') }}
{% endif %}"""
    
    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    result = renderer.render(context)
    assert "gcc" in result
    assert "test.c" in result

def test_nested_variable_override(template_config):
    """Test overriding nested variables in context."""
    template = """#!/bin/bash
{{ build.compiler }} {{ build.optimization|default('-O0') }} -o {{ build.binary.executable }} {{ source.files|join(' ') }}
export CUSTOM_VAR="{{ variables.CUSTOM_VAR }}"
"""
    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test",
        "build": {
            "optimization": "-O3",  # Override build config
            "compiler": "clang"     # Override compiler
        },
        "variables": {
            "CUSTOM_VAR": "override"  # Add new variable
        }
    }
    
    result = renderer.render(context)
    assert "clang -O3" in result  # Uses overridden values
    assert 'CUSTOM_VAR="override"' in result

def test_error_undefined_nested_variable(template_config):
    """Test error handling for undefined nested variables."""
    template = """#!/bin/bash
{{ build.undefined.nested.variable }}"""

    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateVariableError, match="Undefined template variable: build.undefined"):
        renderer.render(context)

def test_error_invalid_filter(template_config):
    """Test error handling for invalid filter usage."""
    template = """#!/bin/bash
{{ build.compiler|undefined_filter }}"""

    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateSyntaxError, match="Invalid template syntax"):
        renderer.render(context)

def test_template_include_error(template_config):
    """Test error handling for unsupported include statement."""
    template = """#!/bin/bash
{% include 'other_template.j2' %}"""

    renderer = TemplateRenderer(template_config, template)
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    with pytest.raises(TemplateSyntaxError, match="Template includes are not supported"):
        renderer.render(context)
  