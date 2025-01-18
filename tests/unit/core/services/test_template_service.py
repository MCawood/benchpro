"""Unit tests for template service functionality."""
import pytest
from pathlib import Path
from benchpro.core.services.template_service import TemplateService
from benchpro.core.domain.templates import (
    TemplateConfig,
    TemplateNotFoundError,
    TemplateConfigError,
    TemplateValidationError,
    TemplateVersionError,
    TemplateVariableError
)

@pytest.fixture
def template_dir(tmp_path):
    """Create a temporary template directory structure."""
    apps_dir = tmp_path / "applications"
    apps_dir.mkdir()
    
    # Create test application directory
    test_app_dir = apps_dir / "test_app"
    test_app_dir.mkdir()
    
    # Create config file
    config_file = test_app_dir / "build.yaml"
    config_file.write_text("""name: test_app
version: 1.0.0
type: application
build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: test_app
source:
  files:
    - test.c
variables:
  TEST_VAR: test_value""")
    
    # Create template file
    template_file = test_app_dir / "build.j2"
    template_file.write_text("""#!/bin/bash
cd {{ working_dir }}
export TEST_VAR="{{ variables.TEST_VAR }}"

# Compile
{{ build.compiler }} -o {{ build.binary.executable }} test.c

# Install
mkdir -p {{ install_dir }}/{{ build.binary.directory }}
cp {{ build.binary.executable }} {{ install_dir }}/{{ build.binary.directory }}/""")
    
    return tmp_path

@pytest.fixture
def template_service(template_dir):
    """Create a template service instance."""
    return TemplateService(template_dir)

def test_service_creation(template_service):
    """Test creating a template service."""
    assert template_service is not None

def test_list_applications(template_service):
    """Test listing available applications."""
    apps = template_service.list_applications()
    assert "test_app" in apps

def test_load_template(template_service):
    """Test loading a template configuration and content."""
    config, template = template_service.load_template("test_app", "build.j2")
    assert isinstance(config, TemplateConfig)
    assert config.name == "test_app"
    assert str(config.version) == "1.0.0"
    assert "#!/bin/bash" in template

def test_load_template_invalid_app(template_service):
    """Test loading template for non-existent application."""
    with pytest.raises(TemplateNotFoundError, match="Application template 'invalid_app' not found"):
        template_service.load_template("invalid_app", "build.j2")

def test_load_template_invalid_file(template_service):
    """Test loading non-existent template file."""
    with pytest.raises(TemplateNotFoundError, match="Template file 'invalid.j2' not found"):
        template_service.load_template("test_app", "invalid.j2")

def test_render_template(template_service):
    """Test rendering a template with context."""
    context = {
        "working_dir": "/tmp/test",
        "install_dir": "/opt/test"
    }
    
    result = template_service.render_template("test_app", "build.j2", context)
    assert "cd /tmp/test" in result
    assert 'export TEST_VAR="test_value"' in result
    assert "gcc -o test_app test.c" in result
    assert "mkdir -p /opt/test/bin" in result
    assert "cp test_app /opt/test/bin/" in result

def test_render_template_missing_context(template_service):
    """Test rendering template with missing context variables."""
    context = {
        # Missing working_dir and install_dir
    }
    
    with pytest.raises(TemplateVariableError, match="Missing required context variable"):
        template_service.render_template("test_app", "build.j2", context)

def test_load_versioned_template(template_dir, template_service):
    """Test loading a versioned template."""
    # Create versioned template directory
    version_dir = template_dir / "applications" / "test_app" / "v1.0.0"
    version_dir.mkdir(parents=True)
    
    # Create versioned config file
    config_file = version_dir / "build.yaml"
    config_file.write_text("""name: test_app
version: 1.0.0
type: application
build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: test_app
source:
  files:
    - test.c
variables:
  TEST_VAR: test_value""")
    
    # Create versioned template file
    template_file = version_dir / "build.j2"
    template_file.write_text("""#!/bin/bash
cd {{ working_dir }}
export TEST_VAR="{{ variables.TEST_VAR }}"

# Compile
{{ build.compiler }} -o {{ build.binary.executable }} test.c

# Install
mkdir -p {{ install_dir }}/{{ build.binary.directory }}
cp {{ build.binary.executable }} {{ install_dir }}/{{ build.binary.directory }}/""")
    
    config, template = template_service.load_template("test_app", "build.j2", version="1.0.0")
    assert isinstance(config, TemplateConfig)
    assert config.name == "test_app"
    assert str(config.version) == "1.0.0"
    assert "#!/bin/bash" in template

def test_load_template_invalid_version(template_service):
    """Test loading template with invalid version."""
    with pytest.raises(TemplateNotFoundError, match="Version '2.0.0' not found"):
        template_service.load_template("test_app", "build.j2", version="2.0.0")

def test_validate_template_config(template_dir, template_service):
    """Test validating template configuration."""
    test_app_dir = template_dir / "applications" / "test_app"
    test_app_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = test_app_dir / "build.yaml"
    config_file.write_text("""name: test_app
# Missing required fields""")
    
    with pytest.raises(TemplateValidationError, match="Missing required field"):
        template_service.load_template("test_app", "build.j2")

def test_validate_template_version(template_dir, template_service):
    """Test validating template version format."""
    test_app_dir = template_dir / "applications" / "test_app"
    test_app_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = test_app_dir / "build.yaml"
    config_file.write_text("""name: test_app
version: invalid.version
type: application
build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: test_app""")
    
    with pytest.raises(TemplateVersionError, match="Invalid version format"):
        template_service.load_template("test_app", "build.j2") 