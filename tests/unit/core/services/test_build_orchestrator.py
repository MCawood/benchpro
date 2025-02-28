import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, call
from benchpro.core.services.build_orchestrator import BuildOrchestrator, BuildError
from benchpro.core.domain.templates.loader import TemplateLoader
from benchpro.core.domain.templates.config import TemplateConfig
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.executor.local import LocalExecutor
from benchpro.core.domain.task_registry import TaskRegistry
from benchpro.core.services.location_manager import LocationManager
from benchpro.core.services.settings import Settings

@pytest.fixture
def template_loader(tmp_path):
    loader = Mock(spec=TemplateLoader)
    loader.load_config.return_value = TemplateConfig({
        "name": "hello_world",
        "version": "1.0.0",
        "type": "application",
        "build": {
            "language": "C",
            "compiler": "gcc",
            "binary": {
                "directory": "bin",
                "executable": "hello_world"
            }
        },
        "source": {
            "files": ["hello_world.c"]
        }
    })
    loader.load_template.return_value = """#!/bin/bash
# Export build variables if provided
{% if CFLAGS is defined %}export CFLAGS="{{ CFLAGS }}"{% endif %}
{% if DEBUG is defined %}export DEBUG="{{ DEBUG }}"{% endif %}

# Create output directory
mkdir -p {{ build.binary.directory }}

# Build application
gcc {% if CFLAGS is defined %}$CFLAGS{% endif %} -o {{ build.binary.directory }}/{{ build.binary.executable }} hello_world.c"""
    
    # Create mock root directory with source files
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    app_dir = mock_root / "applications" / "hello_world"
    app_dir.mkdir(parents=True)
    
    # Create hello_world.c with a simple test program
    hello_world_c = app_dir / "hello_world.c"
    hello_world_c.write_text("""
#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
""")
    
    # Set root_dir attribute to the temporary directory
    loader.root_dir = mock_root
    
    return loader

@pytest.fixture
def executor():
    """Create a mock executor for testing."""
    executor = AsyncMock()
    executor.get_job_status = AsyncMock(return_value={"state": "completed"})
    executor.submit_job = AsyncMock()
    executor.cancel_job = AsyncMock()
    executor.cleanup_job = AsyncMock()
    executor.get_resource_usage = AsyncMock(return_value={
        "memory_mb": 1024.0,
        "virtual_memory_mb": 2048.0,
        "cpu_time": 60.0
    })
    return executor

@pytest.fixture
def root_dir(tmp_path):
    """Create a temporary root directory."""
    return tmp_path

@pytest.fixture
def task_registry(tmp_path):
    """Create a task registry for testing."""
    return TaskRegistry()

@pytest.fixture
def settings():
    """Create test settings."""
    settings = Settings()
    settings.set("task_locations", {
        "build": None,  # Will be set in orchestrator fixture
        "run": None
    })
    return settings

@pytest.fixture
def orchestrator(template_loader, executor, root_dir, task_registry, settings):
    """Create a build orchestrator for testing."""
    # Set up build location in settings
    build_location = root_dir / "applications"
    build_location.mkdir(parents=True, exist_ok=True)
    settings.set("task_locations", {
        "build": str(build_location),
        "run": str(root_dir / "runs")
    })
    
    return BuildOrchestrator(
        template_loader=template_loader,
        executor=executor,
        location_manager=LocationManager(settings),
        task_registry=task_registry,
        root_dir=root_dir
    )

@pytest.mark.asyncio
async def test_applications_directory_creation(orchestrator, root_dir):
    """Test that applications directory is created."""
    applications_dir = root_dir / "applications"
    assert applications_dir.exists()
    assert applications_dir.is_dir()

@pytest.mark.asyncio
async def test_build_application_directory_structure(orchestrator, root_dir):
    """Test that application directory structure is created correctly."""
    app_dir = await orchestrator.build_application("hello_world")
    
    # Verify directory structure
    assert app_dir.exists()
    assert app_dir.parent == root_dir / "applications"
    assert (app_dir / "source").is_dir()
    assert (app_dir / "build").is_dir()
    assert (app_dir / "install").is_dir()
    assert (app_dir / "logs").is_dir()
    
    # Verify build script is in source directory
    build_script = app_dir / "source" / "build.sh"
    assert build_script.exists()
    assert build_script.stat().st_mode & 0o111  # Executable

@pytest.mark.asyncio
async def test_unique_application_instances(orchestrator, root_dir):
    """Test that multiple builds of the same application get unique directories."""
    app_dir1 = await orchestrator.build_application("hello_world")
    app_dir2 = await orchestrator.build_application("hello_world")
    
    assert app_dir1 != app_dir2
    assert app_dir1.exists()
    assert app_dir2.exists()

@pytest.mark.asyncio
async def test_build_application_with_variables(orchestrator, template_loader, root_dir):
    """Test building application with custom variables."""
    variables = {"CFLAGS": "-O3", "DEBUG": "1"}
    app_dir = await orchestrator.build_application("hello_world", variables)
    
    # Verify variables were passed to template renderer
    template_loader.load_template.assert_called_once_with("hello_world", "build.j2")
    
    # Get the rendered script
    build_script = app_dir / "source" / "build.sh"
    script_content = build_script.read_text()
    
    # Check that variables are properly exported
    assert 'export CFLAGS="-O3"' in script_content
    assert 'export DEBUG="1"' in script_content

@pytest.mark.asyncio
async def test_build_application_failure_preservation(orchestrator, executor, root_dir):
    """Test that failed builds are preserved and marked."""
    # Make executor return failed state
    executor.get_job_status.return_value = {"state": "failed"}
    
    with pytest.raises(BuildError):
        app_dir = await orchestrator.build_application("hello_world")
        
        # Directory should still exist
        assert app_dir.exists()
        
        # Should be marked as failed
        assert (app_dir / "FAILED").exists()
        
        # Should preserve all directories
        assert (app_dir / "source").exists()
        assert (app_dir / "build").exists()
        assert (app_dir / "install").exists()
        assert (app_dir / "logs").exists()

@pytest.mark.asyncio
async def test_application_id_generation(orchestrator):
    """Test that application IDs are generated consistently."""
    # Same inputs should generate same ID
    variables = {"CFLAGS": "-O3"}
    id1 = orchestrator._generate_app_id("hello_world", variables)
    id2 = orchestrator._generate_app_id("hello_world", variables)
    
    assert len(id1) == 12  # Check length
    assert all(c in "0123456789abcdef" for c in id1)  # Check hex format
    
    # Different variables should generate different IDs
    id3 = orchestrator._generate_app_id("hello_world", {"CFLAGS": "-O2"})
    assert id1 != id3

@pytest.mark.asyncio
async def test_template_context(orchestrator, template_loader, root_dir):
    """Test that template context contains correct paths."""
    app_dir = await orchestrator.build_application("hello_world")
    
    # Get the rendered script
    build_script = app_dir / "source" / "build.sh"
    script_content = build_script.read_text()
    
    # Verify binary directory and name are in the rendered script
    assert "mkdir -p bin" in script_content
    assert "gcc  -o bin/hello_world hello_world.c" in script_content
    
    # Verify the script is executable
    assert build_script.stat().st_mode & 0o111 