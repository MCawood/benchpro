"""Unit tests for file staging domain model."""

import pytest
from pathlib import Path
from benchpro.core.domain.staging import StagingMode, StagingFile

def test_staging_mode_values():
    """Test that staging modes are correctly defined."""
    assert StagingMode.LOCAL_COPY == "local_copy"
    assert StagingMode.SYMLINK == "symlink"
    assert StagingMode.NONE == "none"

def test_staging_file_creation():
    """Test creation of staging file with basic attributes."""
    staging_file = StagingFile(
        source=Path("/source/file.txt"),
        destination=Path("/dest/file.txt"),
        mode=StagingMode.LOCAL_COPY
    )
    assert staging_file.source == Path("/source/file.txt")
    assert staging_file.destination == Path("/dest/file.txt")
    assert staging_file.mode == StagingMode.LOCAL_COPY
    assert staging_file.size is None
    assert staging_file.checksum is None
    assert staging_file.last_modified is None

def test_staging_file_with_metadata():
    """Test creation of staging file with metadata."""
    staging_file = StagingFile(
        source=Path("/source/file.txt"),
        destination=Path("/dest/file.txt"),
        mode=StagingMode.LOCAL_COPY,
        size=1024,
        checksum="abc123",
        last_modified=1234567890.0
    )
    assert staging_file.size == 1024
    assert staging_file.checksum == "abc123"
    assert staging_file.last_modified == 1234567890.0

def test_staging_file_needs_staging():
    """Test needs_staging logic for different modes."""
    # LOCAL_COPY should always need staging initially
    copy_file = StagingFile(
        source=Path("/source/file.txt"),
        destination=Path("/dest/file.txt"),
        mode=StagingMode.LOCAL_COPY
    )
    assert copy_file.needs_staging() is True

    # NONE should never need staging
    none_file = StagingFile(
        source=Path("/source/file.txt"),
        destination=Path("/dest/file.txt"),
        mode=StagingMode.NONE
    )
    assert none_file.needs_staging() is False

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

def test_staging_file_with_real_paths(temp_source_file, temp_dest_dir):
    """Test staging file with real filesystem paths."""
    staging_file = StagingFile(
        source=temp_source_file,
        destination=temp_dest_dir / "source.txt",
        mode=StagingMode.LOCAL_COPY,
        size=temp_source_file.stat().st_size,
        last_modified=temp_source_file.stat().st_mtime
    )
    assert staging_file.source.exists()
    assert staging_file.needs_staging() is True 