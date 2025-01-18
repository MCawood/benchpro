"""Unit tests for template loading functionality."""
import pytest
from pathlib import Path
from benchpro.core.domain.templates import (
    TemplateLoader,
    TemplateConfig,
    TemplateNotFoundError,
    TemplateConfigError,
    TemplateValidationError
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
    config_file = test_app_dir / "config.yaml"
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

def test_template_loader_creation(template_dir):
    """Test creating a template loader."""
    loader = TemplateLoader(template_dir)
    assert loader.root_dir == template_dir
    assert loader.applications_dir == template_dir / "applications"

def test_template_loader_list_applications(template_dir):
    """Test listing available applications."""
    # Create test application directory
    app_dir = template_dir / "applications" / "test_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Create build.yaml file
    config_file = app_dir / "build.yaml"
    config_file.write_text("""name: test_app
version: 1.0.0
type: application
build:
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: test_app""")
    
    loader = TemplateLoader(template_dir)
    apps = loader.list_applications()
    assert "test_app" in apps

def test_template_loader_list_applications_empty(template_dir):
    """Test listing applications when none exist."""
    # Remove all applications
    for app_dir in (template_dir / "applications").iterdir():
        for file in app_dir.iterdir():
            file.unlink()
        app_dir.rmdir()
    
    loader = TemplateLoader(template_dir)
    apps = loader.list_applications()
    assert len(apps) == 0

def test_template_loader_load_config(template_dir):
    """Test loading a template configuration."""
    # Create test application directory
    app_dir = template_dir / "applications" / "test_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Create build.yaml file
    config_file = app_dir / "build.yaml"
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
    - src/main.c""")
    
    loader = TemplateLoader(template_dir)
    config = loader.load_config("test_app")
    assert config.name == "test_app"
    assert config.version == "1.0.0"
    assert config.type == "application"

def test_template_loader_load_config_invalid_app(template_dir):
    """Test loading config for non-existent application."""
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateNotFoundError, match="Application template 'invalid_app' not found"):
        loader.load_config("invalid_app")

def test_template_loader_load_config_invalid_yaml(template_dir):
    """Test loading invalid YAML configuration."""
    # Create test application directory
    app_dir = template_dir / "applications" / "test_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Create invalid build.yaml file
    config_file = app_dir / "build.yaml"
    config_file.write_text("""name: test_app
version: 1.0.0
type: application
build: [this is not valid yaml
  language: c
  compiler: gcc
  binary:
    directory: bin
    executable: test_app""")
    
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateConfigError, match="Invalid YAML"):
        loader.load_config("test_app")

def test_template_loader_load_config_missing_required(template_dir):
    """Test loading config with missing required fields."""
    # Create test application directory
    app_dir = template_dir / "applications" / "test_app"
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Create build.yaml file with missing fields
    config_file = app_dir / "build.yaml"
    config_file.write_text("""name: test_app
# Missing version and type""")
    
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateValidationError, match="Missing required field"):
        loader.load_config("test_app")

def test_template_loader_load_template(template_dir):
    """Test loading a template file."""
    loader = TemplateLoader(template_dir)
    template = loader.load_template("test_app", "build.j2")
    assert "#!/bin/bash" in template
    assert "{{ working_dir }}" in template
    assert "{{ build.compiler }}" in template

def test_template_loader_load_template_invalid_app(template_dir):
    """Test loading template for non-existent application."""
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateNotFoundError, match="Application template 'invalid_app' not found"):
        loader.load_template("invalid_app", "build.j2")

def test_template_loader_load_template_invalid_file(template_dir):
    """Test loading non-existent template file."""
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateNotFoundError, match="Template file 'invalid.j2' not found"):
        loader.load_template("test_app", "invalid.j2")

def test_template_loader_load_template_empty(template_dir):
    """Test loading empty template file."""
    template_file = template_dir / "applications" / "test_app" / "empty.j2"
    template_file.write_text("")
    
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateValidationError, match="Empty template file"):
        loader.load_template("test_app", "empty.j2")

def test_template_loader_versioned_template(template_dir):
    """Test loading a versioned template."""
    # Create versioned template directory
    version_dir = template_dir / "applications" / "test_app" / "v1.0.0"
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Create versioned build.yaml file
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
    
    loader = TemplateLoader(template_dir)
    config = loader.load_config("test_app", version="1.0.0")
    assert config.name == "test_app"
    assert config.version == "1.0.0"
    assert config.type == "application"

def test_template_loader_invalid_version(template_dir):
    """Test loading template with invalid version."""
    loader = TemplateLoader(template_dir)
    with pytest.raises(TemplateNotFoundError, match="Version '2.0.0' not found"):
        loader.load_config("test_app", version="2.0.0") 