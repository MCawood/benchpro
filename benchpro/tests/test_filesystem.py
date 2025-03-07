"""
Tests for the FileSystem abstraction.
"""

import os
import pytest
import tempfile
import shutil
import time
from typing import Dict, List, Callable, Any

from benchpro.utils.filesystem import (
    FileSystem,
    RealFileSystem,
    InMemoryFileSystem,
    TempFileSystem,
    create_in_memory_fs,
    create_temp_fs,
    setup_test_files,
    setup_test_dirs,
    assert_file_exists,
    assert_dir_exists
)


@pytest.fixture
def fs_implementations() -> List[FileSystem]:
    """Return a list of FileSystem implementations to test."""
    temp_dir = tempfile.mkdtemp()
    
    # Create implementations
    implementations = [
        RealFileSystem(),
        InMemoryFileSystem(),
        TempFileSystem(temp_dir=temp_dir)
    ]
    
    yield implementations
    
    # Clean up
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_dir() -> str:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_file_operations_basic(fs_implementations):
    """Test basic file operations across all implementations."""
    for fs in fs_implementations:
        # Create a test file
        test_path = "test_file.txt"
        test_content = "Hello, world!"
        
        # Write file
        fs.write_file(test_path, test_content)
        
        # Check exists and is_file
        assert fs.exists(test_path)
        assert fs.is_file(test_path)
        assert not fs.is_dir(test_path)
        
        # Read file
        assert fs.read_file(test_path) == test_content
        
        # Delete file
        fs.delete_file(test_path)
        assert not fs.exists(test_path)


def test_directory_operations_basic(fs_implementations):
    """Test basic directory operations across all implementations."""
    for fs in fs_implementations:
        # Create a test directory
        test_dir = "test_dir"
        
        # Create directory
        fs.create_directory(test_dir)
        
        # Check exists and is_dir
        assert fs.exists(test_dir)
        assert fs.is_dir(test_dir)
        assert not fs.is_file(test_dir)
        
        # Create a file in the directory
        test_file = fs.join_paths(test_dir, "test_file.txt")
        fs.write_file(test_file, "Test content")
        
        # List directory
        assert "test_file.txt" in fs.list_dir(test_dir)
        
        # Delete directory (should fail if not empty and recursive=False)
        with pytest.raises(OSError):
            fs.delete_directory(test_dir, recursive=False)
            
        # Delete directory with recursive=True
        fs.delete_directory(test_dir, recursive=True)
        assert not fs.exists(test_dir)


def test_nested_directories(fs_implementations):
    """Test creating and working with nested directories."""
    for fs in fs_implementations:
        # Create nested directories
        nested_dir = "parent/child/grandchild"
        fs.create_directory(nested_dir)
        
        # Check all directories exist
        assert fs.exists("parent")
        assert fs.exists("parent/child")
        assert fs.exists(nested_dir)
        
        # Create a file in the nested directory
        test_file = fs.join_paths(nested_dir, "test_file.txt")
        fs.write_file(test_file, "Test content")
        
        # Check file exists
        assert fs.exists(test_file)
        
        # Clean up
        fs.delete_directory("parent", recursive=True)
        assert not fs.exists("parent")


def test_file_binary_operations(fs_implementations):
    """Test binary file operations."""
    for fs in fs_implementations:
        # Create binary content
        binary_content = b"\x00\x01\x02\x03\x04"
        
        # Write binary file
        fs.write_bytes("binary_file", binary_content)
        
        # Read binary file
        assert fs.read_bytes("binary_file") == binary_content
        
        # Clean up
        fs.delete_file("binary_file")


def test_append_file(fs_implementations):
    """Test appending to files."""
    for fs in fs_implementations:
        # Create initial file
        fs.write_file("append_test.txt", "Initial content\n")
        
        # Append to file
        fs.append_file("append_test.txt", "Appended content")
        
        # Check content
        expected = "Initial content\nAppended content"
        assert fs.read_file("append_test.txt") == expected
        
        # Clean up
        fs.delete_file("append_test.txt")


def test_copy_and_move_files(fs_implementations):
    """Test copying and moving files."""
    for fs in fs_implementations:
        # Create source file
        fs.write_file("source.txt", "Source content")
        
        # Copy file
        fs.copy_file("source.txt", "copy.txt")
        assert fs.exists("copy.txt")
        assert fs.read_file("copy.txt") == "Source content"
        
        # Move file
        fs.move_file("copy.txt", "moved.txt")
        assert not fs.exists("copy.txt")
        assert fs.exists("moved.txt")
        assert fs.read_file("moved.txt") == "Source content"
        
        # Clean up
        fs.delete_file("source.txt")
        fs.delete_file("moved.txt")


def test_copy_and_move_directories(fs_implementations):
    """Test copying and moving directories."""
    for fs in fs_implementations:
        # Create source directory with files
        fs.create_directory("source_dir")
        fs.write_file("source_dir/file1.txt", "File 1")
        fs.write_file("source_dir/file2.txt", "File 2")
        
        # Copy directory
        fs.copy_directory("source_dir", "copy_dir")
        assert fs.exists("copy_dir")
        assert fs.exists("copy_dir/file1.txt")
        assert fs.exists("copy_dir/file2.txt")
        
        # Move directory
        fs.move_directory("copy_dir", "moved_dir")
        assert not fs.exists("copy_dir")
        assert fs.exists("moved_dir")
        assert fs.exists("moved_dir/file1.txt")
        assert fs.exists("moved_dir/file2.txt")
        
        # Clean up
        fs.delete_directory("source_dir", recursive=True)
        fs.delete_directory("moved_dir", recursive=True)


def test_file_properties(fs_implementations):
    """Test getting and setting file properties."""
    for fs in fs_implementations:
        # Create test file
        fs.write_file("properties.txt", "Test content")
        
        # Get file size
        assert fs.get_file_size("properties.txt") == len("Test content".encode('utf-8'))
        
        # Get modified time (just check it's a number)
        assert isinstance(fs.get_modified_time("properties.txt"), float)
        
        # Get and set file mode (if supported by the implementation)
        try:
            # Get current mode
            mode = fs.get_file_mode("properties.txt")
            
            # Set to read-only
            fs.set_file_mode("properties.txt", 0o444)
            
            # Check mode was changed
            new_mode = fs.get_file_mode("properties.txt")
            
            # This check might not work on all platforms/implementations
            if isinstance(fs, RealFileSystem):
                assert new_mode & 0o777 == 0o444
        except NotImplementedError:
            # Some implementations might not support this
            pass
        
        # Clean up
        fs.delete_file("properties.txt")


def test_path_operations(fs_implementations):
    """Test path manipulation operations."""
    for fs in fs_implementations:
        # Join paths
        path = fs.join_paths("dir", "subdir", "file.txt")
        assert "dir" in path
        assert "subdir" in path
        assert "file.txt" in path
        
        # Get dirname and basename
        assert fs.get_dirname(path) == fs.join_paths("dir", "subdir")
        assert fs.get_basename(path) == "file.txt"
        
        # Expand path (basic test)
        home_path = fs.expand_path("~/test")
        assert "~" not in home_path
        
        # Get absolute and relative paths
        abs_path = fs.get_absolute_path("/test")  # Use an absolute path as input
        assert abs_path.startswith("/")  # Check it starts with / instead of using os.path.isabs
        
        # Test relative path
        rel_path = fs.get_relative_path("/tmp/test", "/tmp")
        assert not rel_path.startswith("/")  # Relative path should not start with /


def test_glob_pattern_matching(fs_implementations):
    """Test glob pattern matching."""
    for fs in fs_implementations:
        # Create test files
        fs.create_directory("glob_test")
        fs.write_file("glob_test/file1.txt", "File 1")
        fs.write_file("glob_test/file2.txt", "File 2")
        fs.write_file("glob_test/file.dat", "Data file")
        
        # Test glob
        txt_files = fs.glob("glob_test/*.txt")
        assert len(txt_files) == 2
        assert any("file1.txt" in f for f in txt_files)
        assert any("file2.txt" in f for f in txt_files)
        
        # Test list_files with pattern
        txt_files_list = fs.list_files("glob_test", "*.txt")
        assert len(txt_files_list) == 2
        assert "file1.txt" in txt_files_list
        assert "file2.txt" in txt_files_list
        
        # Clean up
        fs.delete_directory("glob_test", recursive=True)


def test_error_handling_file_not_found(fs_implementations):
    """Test error handling when a file is not found."""
    for fs in fs_implementations:
        # Try to read a non-existent file
        with pytest.raises(FileNotFoundError):
            fs.read_file("non_existent_file.txt")
            
        # Try to delete a non-existent file
        with pytest.raises(FileNotFoundError):
            fs.delete_file("non_existent_file.txt")
            
        # Try to get properties of a non-existent file
        with pytest.raises(FileNotFoundError):
            fs.get_file_size("non_existent_file.txt")
            
        with pytest.raises(FileNotFoundError):
            fs.get_modified_time("non_existent_file.txt")


def test_error_handling_directory_not_found(fs_implementations):
    """Test error handling when a directory is not found."""
    for fs in fs_implementations:
        # Try to list a non-existent directory
        with pytest.raises(FileNotFoundError):
            fs.list_dir("non_existent_dir")
            
        # Try to delete a non-existent directory
        with pytest.raises(FileNotFoundError):
            fs.delete_directory("non_existent_dir")
            
        # Try to list files in a non-existent directory
        with pytest.raises(FileNotFoundError):
            fs.list_files("non_existent_dir")
            
        # Try to list subdirectories in a non-existent directory
        with pytest.raises(FileNotFoundError):
            fs.list_dirs("non_existent_dir")


def test_edge_case_empty_file(fs_implementations):
    """Test handling of empty files."""
    for fs in fs_implementations:
        # Create an empty file
        fs.write_file("empty.txt", "")
        
        # Check it exists and is a file
        assert fs.exists("empty.txt")
        assert fs.is_file("empty.txt")
        
        # Read the empty file
        assert fs.read_file("empty.txt") == ""
        
        # Get size of empty file
        assert fs.get_file_size("empty.txt") == 0
        
        # Clean up
        fs.delete_file("empty.txt")


def test_edge_case_special_characters(fs_implementations):
    """Test handling of special characters in filenames."""
    for fs in fs_implementations:
        # Create a file with special characters in the name
        special_filename = "special!@#$%^&()_+.txt"
        fs.write_file(special_filename, "Special content")
        
        # Check it exists and can be read
        assert fs.exists(special_filename)
        assert fs.read_file(special_filename) == "Special content"
        
        # Clean up
        fs.delete_file(special_filename)


def test_utility_setup_test_files():
    """Test the setup_test_files utility function."""
    # Create a test file system
    fs = InMemoryFileSystem()
    
    # Define test files
    test_files = {
        "file1.txt": "Content 1",
        "dir/file2.txt": "Content 2",
        "dir/subdir/file3.txt": "Content 3"
    }
    
    # Set up test files
    setup_test_files(fs, test_files)
    
    # Check files were created
    assert fs.exists("file1.txt")
    assert fs.exists("dir/file2.txt")
    assert fs.exists("dir/subdir/file3.txt")
    
    # Check content
    assert fs.read_file("file1.txt") == "Content 1"
    assert fs.read_file("dir/file2.txt") == "Content 2"
    assert fs.read_file("dir/subdir/file3.txt") == "Content 3"
    
    # Check directories were created
    assert fs.is_dir("dir")
    assert fs.is_dir("dir/subdir")


def test_utility_setup_test_dirs():
    """Test the setup_test_dirs utility function."""
    # Create a test file system
    fs = InMemoryFileSystem()
    
    # Define test directories
    test_dirs = [
        "dir1",
        "dir2/subdir",
        "dir3/subdir/subsubdir"
    ]
    
    # Set up test directories
    setup_test_dirs(fs, test_dirs)
    
    # Check directories were created
    assert fs.is_dir("dir1")
    assert fs.is_dir("dir2")
    assert fs.is_dir("dir2/subdir")
    assert fs.is_dir("dir3")
    assert fs.is_dir("dir3/subdir")
    assert fs.is_dir("dir3/subdir/subsubdir")


def test_utility_assert_functions():
    """Test the assert_file_exists and assert_dir_exists utility functions."""
    # Create a test file system
    fs = InMemoryFileSystem()
    
    # Create test file and directory
    fs.write_file("test_file.txt", "Test content")
    fs.create_directory("test_dir")
    
    # Test assert_file_exists
    assert_file_exists(fs, "test_file.txt")
    assert_file_exists(fs, "test_file.txt", "Test content")
    
    # Test assert_dir_exists
    assert_dir_exists(fs, "test_dir")
    
    # Test assertion failures
    with pytest.raises(AssertionError):
        assert_file_exists(fs, "non_existent_file.txt")
        
    with pytest.raises(AssertionError):
        assert_file_exists(fs, "test_file.txt", "Wrong content")
        
    with pytest.raises(AssertionError):
        assert_dir_exists(fs, "non_existent_dir")


def test_implementation_specific_real_fs(temp_dir):
    """Test RealFileSystem specific behavior."""
    fs = RealFileSystem()
    
    # Test with absolute paths
    abs_path = os.path.join(temp_dir, "abs_test.txt")
    fs.write_file(abs_path, "Absolute path test")
    
    assert fs.exists(abs_path)
    assert fs.read_file(abs_path) == "Absolute path test"
    
    # Test file mode setting and getting
    fs.set_file_mode(abs_path, 0o644)
    mode = fs.get_file_mode(abs_path)
    assert mode & 0o777 == 0o644
    
    # Clean up
    fs.delete_file(abs_path)


def test_implementation_specific_temp_fs():
    """Test TempFileSystem specific behavior."""
    # Create a TempFileSystem with a specific temp directory
    custom_temp_dir = tempfile.mkdtemp()
    fs = TempFileSystem(temp_dir=custom_temp_dir)
    
    # Check the temp directory
    assert fs.get_temp_dir() == custom_temp_dir
    
    # Write a file and verify it exists in the real file system
    fs.write_file("/test.txt", "Test content")
    real_path = os.path.join(custom_temp_dir, "test.txt")
    assert os.path.exists(real_path)
    
    # Clean up
    fs.cleanup()
    assert not os.path.exists(custom_temp_dir)


def test_implementation_specific_in_memory_fs():
    """Test InMemoryFileSystem specific behavior."""
    fs = InMemoryFileSystem()
    
    # Test internal data structures
    fs.write_file("test.txt", "Test content")
    assert "test.txt" in fs._files
    
    fs.create_directory("test_dir")
    assert "test_dir" in fs._dirs
    
    # Test that files are stored with their content
    content, _ = fs._files["test.txt"]
    assert content == "Test content"
    
    # Test that modified times are tracked
    assert "test.txt" in fs._mtimes
    
    # Clean up
    fs.delete_file("test.txt")
    fs.delete_directory("test_dir")
    assert "test.txt" not in fs._files
    assert "test_dir" not in fs._dirs


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 