"""
File System abstraction for BenchPRO.

This module provides abstractions for file system operations to make testing easier
and reduce dependencies on the actual file system in tests.
"""

import os
import shutil
import yaml
import logging
from typing import Dict, Any, List, Optional, Union, Set

# Get logger
logger = logging.getLogger(__name__)


class FileSystem:
    """
    Abstract interface for file system operations.
    
    This abstraction allows for easy mocking in tests and decouples
    code from the actual file system implementation.
    """
    
    def exists(self, path: str) -> bool:
        """
        Check if a path exists.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path exists, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def is_file(self, path: str) -> bool:
        """
        Check if a path is a file.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path is a file, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def is_dir(self, path: str) -> bool:
        """
        Check if a path is a directory.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path is a directory, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def read_file(self, path: str) -> str:
        """
        Read the contents of a file.
        
        Args:
            path: The path to the file.
            
        Returns:
            The contents of the file as a string.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If the file cannot be read.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def read_yaml(self, path: str) -> Dict[str, Any]:
        """
        Read and parse a YAML file.
        
        Args:
            path: The path to the YAML file.
            
        Returns:
            The parsed YAML content as a dictionary.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML is invalid.
        """
        content = self.read_file(path)
        return yaml.safe_load(content) or {}
    
    def write_file(self, path: str, content: str) -> None:
        """
        Write content to a file.
        
        Args:
            path: The path to the file.
            content: The content to write.
            
        Raises:
            IOError: If the file cannot be written.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def write_yaml(self, path: str, data: Dict[str, Any]) -> None:
        """
        Write data to a YAML file.
        
        Args:
            path: The path to the YAML file.
            data: The data to write.
            
        Raises:
            IOError: If the file cannot be written.
        """
        content = yaml.dump(data)
        self.write_file(path, content)
    
    def create_directory(self, path: str) -> None:
        """
        Create a directory if it doesn't exist.
        
        Args:
            path: The path to the directory.
            
        Raises:
            IOError: If the directory cannot be created.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def list_dir(self, path: str) -> List[str]:
        """
        List the contents of a directory.
        
        Args:
            path: The path to the directory.
            
        Returns:
            A list of file and directory names in the directory.
            
        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def join_paths(self, *paths: str) -> str:
        """
        Join paths together.
        
        Args:
            *paths: The paths to join.
            
        Returns:
            The joined path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def copy_file(self, src: str, dst: str) -> None:
        """
        Copy a file from src to dst.
        
        Args:
            src: The source path.
            dst: The destination path.
            
        Raises:
            FileNotFoundError: If the source file does not exist.
            IOError: If the file cannot be copied.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def copy_directory(self, src: str, dst: str) -> None:
        """
        Copy a directory from src to dst.
        
        Args:
            src: The source path.
            dst: The destination path.
            
        Raises:
            FileNotFoundError: If the source directory does not exist.
            IOError: If the directory cannot be copied.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def expand_path(self, path: str) -> str:
        """
        Expand user and environment variables in a path.
        
        Args:
            path: The path to expand.
            
        Returns:
            The expanded path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_dirname(self, path: str) -> str:
        """
        Get the directory name of a path.
        
        Args:
            path: The path.
            
        Returns:
            The directory containing the path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_basename(self, path: str) -> str:
        """
        Get the base name of a path.
        
        Args:
            path: The path.
            
        Returns:
            The filename portion of the path.
        """
        raise NotImplementedError("Subclasses must implement this method")


class RealFileSystem(FileSystem):
    """
    Implementation of FileSystem using the actual file system.
    
    This is the default implementation used in production code.
    """
    
    def exists(self, path: str) -> bool:
        return os.path.exists(path)
    
    def is_file(self, path: str) -> bool:
        return os.path.isfile(path)
    
    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)
    
    def read_file(self, path: str) -> str:
        with open(path, 'r') as f:
            return f.read()
    
    def write_file(self, path: str, content: str) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(path, 'w') as f:
            f.write(content)
    
    def create_directory(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
    
    def list_dir(self, path: str) -> List[str]:
        return os.listdir(path)
    
    def join_paths(self, *paths: str) -> str:
        return os.path.join(*paths)
    
    def copy_file(self, src: str, dst: str) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(dst)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        shutil.copy2(src, dst)
    
    def copy_directory(self, src: str, dst: str) -> None:
        # Create parent directories if they don't exist
        if not os.path.exists(dst):
            os.makedirs(dst, exist_ok=True)
            
        # Copy all files and subdirectories
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
    
    def expand_path(self, path: str) -> str:
        """Expand user and environment variables in path."""
        return os.path.expanduser(os.path.expandvars(path))
    
    def get_dirname(self, path: str) -> str:
        return os.path.dirname(path)
    
    def get_basename(self, path: str) -> str:
        return os.path.basename(path)


class TestFileSystem(FileSystem):
    """
    In-memory implementation of FileSystem for testing.
    
    This implementation stores files and directories in memory,
    making it perfect for unit tests that don't need real file system access.
    """
    
    def __init__(self, base_temp_dir: Optional[str] = None):
        """
        Initialize an empty file system.
        
        Args:
            base_temp_dir: Optional real directory path to use as a base.
                           If provided, this allows integration with the existing
                           UserDirectoryManager test conventions.
        """
        self.files: Dict[str, str] = {}
        self.directories: Set[str] = set()
        self.base_temp_dir = base_temp_dir
        
        # If using a real base temp directory, consider it to exist
        if base_temp_dir:
            self.directories.add(base_temp_dir)
        
    def exists(self, path: str) -> bool:
        # If we're using a real base temp directory and the path is within it,
        # check the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            return os.path.exists(path)
            
        return path in self.files or self._in_directory(path)
    
    def is_file(self, path: str) -> bool:
        # If we're using a real base temp directory and the path is within it,
        # check the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            return os.path.isfile(path)
            
        return path in self.files
    
    def is_dir(self, path: str) -> bool:
        # If we're using a real base temp directory and the path is within it,
        # check the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            return os.path.isdir(path)
            
        return self._in_directory(path)
    
    def read_file(self, path: str) -> str:
        # If we're using a real base temp directory and the path is within it,
        # read from the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            with open(path, 'r') as f:
                return f.read()
                
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]
    
    def write_file(self, path: str, content: str) -> None:
        # If we're using a real base temp directory and the path is within it,
        # write to the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            parent_dir = os.path.dirname(path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                
            with open(path, 'w') as f:
                f.write(content)
            return
                
        # Create parent directories
        parent_dir = self.get_dirname(path)
        if parent_dir:
            self.create_directory(parent_dir)
            
        self.files[path] = content
    
    def create_directory(self, path: str) -> None:
        # If we're using a real base temp directory and the path is within it,
        # create the directory in the real file system
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            os.makedirs(path, exist_ok=True)
            return
            
        # Add this directory and all parent directories
        self.directories.add(path)
        
        # Ensure all parent directories exist
        parent_dir = self.get_dirname(path)
        if parent_dir:
            self.create_directory(parent_dir)
    
    def list_dir(self, path: str) -> List[str]:
        # If we're using a real base temp directory and the path is within it,
        # list the real directory
        if self.base_temp_dir and path.startswith(self.base_temp_dir):
            return os.listdir(path)
            
        if not self._in_directory(path):
            raise FileNotFoundError(f"Directory not found: {path}")
            
        # Get all files and directories directly under this path
        result = []
        
        # Add files
        for file_path in self.files:
            if self.get_dirname(file_path) == path:
                result.append(self.get_basename(file_path))
        
        # Add directories
        for dir_path in self.directories:
            if self.get_dirname(dir_path) == path:
                result.append(self.get_basename(dir_path))
        
        return list(set(result))  # Remove duplicates
    
    def join_paths(self, *paths: str) -> str:
        return os.path.join(*paths)
    
    def copy_file(self, src: str, dst: str) -> None:
        # Handle real file system operations if using base_temp_dir
        if self.base_temp_dir:
            src_is_real = src.startswith(self.base_temp_dir)
            dst_is_real = dst.startswith(self.base_temp_dir)
            
            # Both are real paths
            if src_is_real and dst_is_real:
                parent_dir = os.path.dirname(dst)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                shutil.copy2(src, dst)
                return
                
            # Source is real, destination is in-memory
            if src_is_real:
                with open(src, 'r') as f:
                    content = f.read()
                self.write_file(dst, content)
                return
                
            # Source is in-memory, destination is real
            if dst_is_real:
                if src not in self.files:
                    raise FileNotFoundError(f"Source file not found: {src}")
                parent_dir = os.path.dirname(dst)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                with open(dst, 'w') as f:
                    f.write(self.files[src])
                return
        
        # Both are in-memory
        if src not in self.files:
            raise FileNotFoundError(f"Source file not found: {src}")
            
        # Create parent directories
        parent_dir = self.get_dirname(dst)
        if parent_dir:
            self.create_directory(parent_dir)
            
        self.files[dst] = self.files[src]
    
    def copy_directory(self, src: str, dst: str) -> None:
        # Handle real file system operations if using base_temp_dir
        if self.base_temp_dir:
            src_is_real = src.startswith(self.base_temp_dir)
            dst_is_real = dst.startswith(self.base_temp_dir)
            
            # Both are real paths
            if src_is_real and dst_is_real:
                if not os.path.exists(dst):
                    os.makedirs(dst, exist_ok=True)
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                return
            
            # Mixed real/in-memory operations not fully supported
            # Would need more complex handling
            logger.warning("Mixed real/in-memory directory copy not fully supported")
            
        # Both are in-memory
        if not self._in_directory(src):
            raise FileNotFoundError(f"Source directory not found: {src}")
            
        # Create destination directory
        self.create_directory(dst)
        
        # Copy all files in the directory
        for file_path in list(self.files.keys()):
            if file_path.startswith(f"{src}/"):
                rel_path = os.path.relpath(file_path, src)
                dst_path = os.path.join(dst, rel_path)
                self.files[dst_path] = self.files[file_path]
        
        # Copy all subdirectories
        for dir_path in list(self.directories):
            if dir_path.startswith(f"{src}/"):
                rel_path = os.path.relpath(dir_path, src)
                dst_path = os.path.join(dst, rel_path)
                self.directories.add(dst_path)
    
    def expand_path(self, path: str) -> str:
        """Expand user and environment variables in path."""
        return os.path.expanduser(os.path.expandvars(path))
    
    def get_dirname(self, path: str) -> str:
        return os.path.dirname(path)
    
    def get_basename(self, path: str) -> str:
        return os.path.basename(path)
    
    def _in_directory(self, path: str) -> bool:
        """Check if a path is a directory or within a directory."""
        # Exact directory match
        if path in self.directories:
            return True
            
        # Check if any directory is a parent of this path
        for dir_path in self.directories:
            if path.startswith(f"{dir_path}/"):
                return True
                
        # Check if any file is under this path (meaning it's a directory)
        path_with_sep = f"{path}/"
        for file_path in self.files:
            if file_path.startswith(path_with_sep):
                return True
                
        return False


# Create a singleton instance for convenience
real_file_system = RealFileSystem() 