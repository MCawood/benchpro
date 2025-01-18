"""Unit tests for file staging service."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock

from benchpro.core.domain.staging import StagingMode, StagingFile
from benchpro.core.domain.task import Task, TaskState
from benchpro.core.services.staging import FileStager, StagingError

@pytest.fixture
def temp_source_file(tmp_path):
    """Create a temporary source file for testing."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("test content")
    return source_file

@pytest.fixture
def temp_dest_dir(tmp_path):
    """Create a temporary destination directory."""
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    return dest_dir

@pytest.fixture
def file_stager():
    """Create a FileStager instance."""
    return FileStager(max_concurrent=2)

@pytest.mark.asyncio
async def test_stage_single_file(file_stager, temp_source_file, temp_dest_dir):
    """Test staging a single file."""
    # Create task with one staging file
    task = Task(
        name="test-task",
        working_dir=temp_dest_dir
    )
    task.staging_files = [
        StagingFile(
            source=temp_source_file,
            destination=temp_dest_dir / "source.txt",
            mode=StagingMode.LOCAL_COPY
        )
    ]
    
    # Stage the file
    await file_stager.stage_files(task)
    
    # Check results
    assert (temp_dest_dir / "source.txt").exists()
    assert (temp_dest_dir / "source.txt").read_text() == "test content"

@pytest.mark.asyncio
async def test_stage_multiple_files(file_stager, tmp_path):
    """Test staging multiple files concurrently."""
    # Create source files
    source_files = []
    for i in range(3):
        source_file = tmp_path / f"source{i}.txt"
        source_file.write_text(f"content {i}")
        source_files.append(source_file)
        
    # Create task with multiple staging files
    task = Task(
        name="test-task",
        working_dir=tmp_path / "dest"
    )
    task.staging_files = [
        StagingFile(
            source=src,
            destination=task.working_dir / src.name,
            mode=StagingMode.LOCAL_COPY
        )
        for src in source_files
    ]
    
    # Stage files
    await file_stager.stage_files(task)
    
    # Check results
    for i in range(3):
        staged_file = task.working_dir / f"source{i}.txt"
        assert staged_file.exists()
        assert staged_file.read_text() == f"content {i}"

@pytest.mark.asyncio
async def test_staging_error_handling(file_stager, tmp_path):
    """Test error handling when staging fails."""
    # Create task with non-existent source file
    task = Task(
        name="test-task",
        working_dir=tmp_path / "dest"
    )
    task.staging_files = [
        StagingFile(
            source=tmp_path / "nonexistent.txt",
            destination=task.working_dir / "dest.txt",
            mode=StagingMode.LOCAL_COPY
        )
    ]
    
    # Attempt to stage files
    with pytest.raises(StagingError):
        await file_stager.stage_files(task)

@pytest.mark.asyncio
async def test_staging_concurrency(file_stager, tmp_path):
    """Test that staging respects concurrency limits."""
    # Create source files
    source_files = []
    for i in range(4):  # More files than concurrent limit
        source_file = tmp_path / f"source{i}.txt"
        source_file.write_text(f"content {i}")
        source_files.append(source_file)
        
    # Create task with multiple staging files
    task = Task(
        name="test-task",
        working_dir=tmp_path / "dest"
    )
    task.staging_files = [
        StagingFile(
            source=src,
            destination=task.working_dir / src.name,
            mode=StagingMode.LOCAL_COPY
        )
        for src in source_files
    ]
    
    # Track concurrent operations
    active_operations = 0
    max_active_operations = 0
    
    async def mock_copy_with_delay(src, dst):
        nonlocal active_operations, max_active_operations
        active_operations += 1
        max_active_operations = max(max_active_operations, active_operations)
        await asyncio.sleep(0.1)  # Simulate file copy
        active_operations -= 1
        dst.write_text(src.read_text())
        
    # Replace actual copy with mock
    file_stager._copy_file = mock_copy_with_delay
    
    # Stage files
    await file_stager.stage_files(task)
    
    # Check that concurrency limit was respected
    assert max_active_operations <= 2  # Our concurrency limit
    
    # Check all files were staged
    for i in range(4):
        staged_file = task.working_dir / f"source{i}.txt"
        assert staged_file.exists()
        assert staged_file.read_text() == f"content {i}" 