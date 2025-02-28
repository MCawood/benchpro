"""Integration tests for configurable task paths."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

from benchpro.core.services.settings import Settings
from benchpro.core.services.location_manager import LocationManager
from benchpro.core.domain.task_registry import TaskRegistry, TaskType
from benchpro.core.domain.templates.loader import TemplateLoader
from benchpro.core.executor.local.executor import LocalExecutor
from benchpro.core.services.build_orchestrator import BuildOrchestrator

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        
        # Create basic workspace structure
        (workspace / "templates").mkdir()
        (workspace / "templates" / "applications").mkdir()
        
        # Copy hello_world template to test workspace
        template_src = Path("templates/applications/hello_world")
        template_dst = workspace / "templates" / "applications" / "hello_world"
        shutil.copytree(template_src, template_dst)
        
        yield workspace

@pytest.fixture
def settings(temp_workspace):
    """Create test settings with temporary workspace."""
    settings = Settings()
    
    # Enable testing mode first
    settings.set("testing", True)
    
    # Override workspace settings for testing
    settings.set("workspace_root", str(temp_workspace))
    settings.set("task_locations", {
        "build": str(temp_workspace / "applications"),
        "benchmark": str(temp_workspace / "benchmarks"),
        "custom": None
    })
    
    return settings

@pytest.fixture
def location_manager(settings):
    """Create location manager with test settings."""
    return LocationManager(settings)

@pytest.fixture
def task_registry(temp_workspace):
    """Create task registry in test workspace."""
    return TaskRegistry(temp_workspace)

@pytest.fixture
def build_orchestrator(temp_workspace, settings, location_manager, task_registry):
    """Create build orchestrator with test components."""
    template_loader = TemplateLoader(temp_workspace / "templates")
    executor = LocalExecutor(working_dir=temp_workspace / "applications")
    return BuildOrchestrator(
        template_loader=template_loader,
        executor=executor,
        location_manager=location_manager,
        task_registry=task_registry,
        root_dir=temp_workspace
    )

@pytest.mark.asyncio
async def test_build_in_different_locations(build_orchestrator, settings, location_manager):
    """Test building applications in different locations."""
    
    # Create test directories
    test_dir1 = Path("/tmp/test1")
    test_dir2 = Path("/tmp/test2")
    
    try:
        # Test location 1
        settings.set("task_locations", {
            "build": str(test_dir1),
            "benchmark": str(settings.get("task_locations")["benchmark"]),
            "custom": None
        })
        location_manager._load_locations()  # Reload locations
        
        # Build in first location
        app_dir1 = await build_orchestrator.build_application("hello_world")
        assert app_dir1.parent.resolve() == test_dir1.resolve()
        
        # Test location 2
        settings.set("task_locations", {
            "build": str(test_dir2),
            "benchmark": str(settings.get("task_locations")["benchmark"]),
            "custom": None
        })
        location_manager._load_locations()  # Reload locations
        
        # Build in second location
        app_dir2 = await build_orchestrator.build_application("hello_world")
        assert app_dir2.parent.resolve() == test_dir2.resolve()
        
        # Verify both builds exist in their respective locations
        assert len(list(test_dir1.glob("hello_world-*"))) == 1
        assert len(list(test_dir2.glob("hello_world-*"))) == 1
        
    finally:
        # Cleanup
        if test_dir1.exists():
            shutil.rmtree(test_dir1)
        if test_dir2.exists():
            shutil.rmtree(test_dir2)

@pytest.mark.asyncio
async def test_build_with_cli_location_override(build_orchestrator):
    """Test building application with location override from CLI."""
    
    custom_dir = Path("/tmp/custom_test")
    
    try:
        # Build with custom location
        app_dir = await build_orchestrator.build_application(
            "hello_world",
            custom_location=custom_dir
        )
        
        # Verify build location
        assert app_dir.parent.resolve() == custom_dir.resolve()
        
        # Check task registry
        task_record = build_orchestrator.task_registry.list_tasks(
            task_type=TaskType.BUILD,
            limit=1
        )[0]
        assert task_record.location.parent.resolve() == custom_dir.resolve()
        
    finally:
        # Cleanup
        if custom_dir.exists():
            shutil.rmtree(custom_dir)

@pytest.mark.asyncio
async def test_location_persistence(build_orchestrator, settings, location_manager):
    """Test that location changes persist across builds."""
    
    test_dir = Path("/tmp/persist_test")
    
    try:
        # Update build location
        settings.set("task_locations", {
            "build": str(test_dir),
            "benchmark": str(settings.get("task_locations")["benchmark"]),
            "custom": None
        })
        location_manager._load_locations()
        
        # Do multiple builds
        app_dir1 = await build_orchestrator.build_application("hello_world")
        app_dir2 = await build_orchestrator.build_application("hello_world")
        
        # Verify all builds are in the new location
        assert app_dir1.parent.resolve() == test_dir.resolve()
        assert app_dir2.parent.resolve() == test_dir.resolve()
        assert len(list(test_dir.glob("hello_world-*"))) == 2
        
        # Verify task registry records
        tasks = build_orchestrator.task_registry.list_tasks(task_type=TaskType.BUILD)
        assert all(task.location.parent.resolve() == test_dir.resolve() for task in tasks)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

@pytest.mark.asyncio
async def test_invalid_location_handling(build_orchestrator, settings, location_manager):
    """Test handling of invalid build locations."""
    
    # Test non-existent parent directory
    with pytest.raises(Exception) as exc_info:
        invalid_dir = Path("/nonexistent/path/test")
        await build_orchestrator.build_application(
            "hello_world",
            custom_location=invalid_dir
        )
    assert "Failed to ensure location" in str(exc_info.value)
    
    # Test non-writable directory (if running as non-root)
    if os.geteuid() != 0:  # Skip if running as root
        with pytest.raises(Exception) as exc_info:
            invalid_dir = Path("/root/test")  # Typically non-writable for non-root
            await build_orchestrator.build_application(
                "hello_world",
                custom_location=invalid_dir
            )
        assert "Read-only file system" in str(exc_info.value) 