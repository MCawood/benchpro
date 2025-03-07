"""
File System abstraction for BenchPRO.

This module provides abstractions for file system operations to make testing easier
and reduce dependencies on the actual file system in tests.
"""

import os
import shutil
import tempfile
import yaml
import logging
import time
from typing import Dict, Any, List, Optional, Union, Set, Pattern

# Get logger
logger = logging.getLogger(__name__)


class FileSystem:
    """
    Abstract interface for file system operations.
    
    This abstraction allows for easy mocking in tests and decouples
    code from the actual file system implementation.
    """
    
    # Basic file operations
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
    
    def read_bytes(self, path: str) -> bytes:
        """
        Read the contents of a file as bytes.
        
        Args:
            path: The path to the file.
            
        Returns:
            The contents of the file as bytes.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If the file cannot be read.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def write_file(self, path: str, content: str, mode: int = None) -> None:
        """
        Write content to a file.
        
        Args:
            path: The path to the file.
            content: The content to write.
            mode: Optional file permission mode.
            
        Raises:
            IOError: If the file cannot be written.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def write_bytes(self, path: str, content: bytes, mode: int = None) -> None:
        """
        Write binary content to a file.
        
        Args:
            path: The path to the file.
            content: The binary content to write.
            mode: Optional file permission mode.
            
        Raises:
            IOError: If the file cannot be written.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def append_file(self, path: str, content: str) -> None:
        """
        Append content to a file.
        
        Args:
            path: The path to the file.
            content: The content to append.
            
        Raises:
            IOError: If the file cannot be written.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def delete_file(self, path: str) -> None:
        """
        Delete a file.
        
        Args:
            path: The path to the file.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If the file cannot be deleted.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    # Directory operations
    def create_directory(self, path: str, mode: int = None) -> None:
        """
        Create a directory if it doesn't exist.
        
        Args:
            path: The path to the directory.
            mode: Optional directory permission mode.
            
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
    
    def list_files(self, path: str, pattern: str = None) -> List[str]:
        """
        List files in a directory, optionally matching a pattern.
        
        Args:
            path: The path to the directory.
            pattern: Optional glob pattern to match files against.
            
        Returns:
            A list of file names in the directory.
            
        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def list_dirs(self, path: str) -> List[str]:
        """
        List subdirectories in a directory.
        
        Args:
            path: The path to the directory.
            
        Returns:
            A list of directory names in the directory.
            
        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def delete_directory(self, path: str, recursive: bool = False) -> None:
        """
        Delete a directory.
        
        Args:
            path: The path to the directory.
            recursive: Whether to delete the directory recursively.
            
        Raises:
            FileNotFoundError: If the directory does not exist.
            IOError: If the directory cannot be deleted.
            OSError: If the directory is not empty and recursive is False.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    # Path operations
    def join_paths(self, *paths: str) -> str:
        """
        Join paths together.
        
        Args:
            *paths: The paths to join.
            
        Returns:
            The joined path.
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
    
    def get_absolute_path(self, path: str) -> str:
        """
        Get the absolute path.
        
        Args:
            path: The path to convert.
            
        Returns:
            The absolute path.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_relative_path(self, path: str, start: str = None) -> str:
        """
        Get a path relative to another path.
        
        Args:
            path: The path to convert.
            start: The starting path. If None, uses the current working directory.
            
        Returns:
            The relative path.
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
    
    # Copy/move operations
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
    
    def move_file(self, src: str, dst: str) -> None:
        """
        Move a file from src to dst.
        
        Args:
            src: The source path.
            dst: The destination path.
            
        Raises:
            FileNotFoundError: If the source file does not exist.
            IOError: If the file cannot be moved.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def move_directory(self, src: str, dst: str) -> None:
        """
        Move a directory from src to dst.
        
        Args:
            src: The source path.
            dst: The destination path.
            
        Raises:
            FileNotFoundError: If the source directory does not exist.
            IOError: If the directory cannot be moved.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    # File properties
    def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            path: The path to the file.
            
        Returns:
            The size of the file in bytes.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_modified_time(self, path: str) -> float:
        """
        Get the last modified time of a file.
        
        Args:
            path: The path to the file.
            
        Returns:
            The last modified time as a timestamp.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_file_mode(self, path: str) -> int:
        """
        Get the permission mode of a file.
        
        Args:
            path: The path to the file.
            
        Returns:
            The permission mode of the file.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def set_file_mode(self, path: str, mode: int) -> None:
        """
        Set the permission mode of a file.
        
        Args:
            path: The path to the file.
            mode: The permission mode to set.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            IOError: If the mode cannot be set.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    # Specialized operations
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
    
    def glob(self, pattern: str) -> List[str]:
        """
        Find paths matching a glob pattern.
        
        Args:
            pattern: The glob pattern to match.
            
        Returns:
            A list of paths matching the pattern.
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
    
    def read_bytes(self, path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()
    
    def write_file(self, path: str, content: str, mode: int = None) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(path, 'w') as f:
            f.write(content)
            
        if mode is not None:
            os.chmod(path, mode)
    
    def write_bytes(self, path: str, content: bytes, mode: int = None) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(path, 'wb') as f:
            f.write(content)
            
        if mode is not None:
            os.chmod(path, mode)
    
    def append_file(self, path: str, content: str) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(path, 'a') as f:
            f.write(content)
    
    def delete_file(self, path: str) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        if not os.path.isfile(path):
            raise IOError(f"Not a file: {path}")
        os.remove(path)
    
    def create_directory(self, path: str, mode: int = None) -> None:
        os.makedirs(path, exist_ok=True)
        if mode is not None:
            os.chmod(path, mode)
    
    def list_dir(self, path: str) -> List[str]:
        return os.listdir(path)
    
    def list_files(self, path: str, pattern: str = None) -> List[str]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        
        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]
            
        return files
    
    def list_dirs(self, path: str) -> List[str]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    
    def delete_directory(self, path: str, recursive: bool = False) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(path):
            raise IOError(f"Not a directory: {path}")
            
        if recursive:
            shutil.rmtree(path)
        else:
            os.rmdir(path)  # Will raise OSError if directory is not empty
    
    def join_paths(self, *paths: str) -> str:
        return os.path.join(*paths)
    
    def expand_path(self, path: str) -> str:
        """Expand user and environment variables in path."""
        return os.path.expanduser(os.path.expandvars(path))
    
    def get_absolute_path(self, path: str) -> str:
        return os.path.abspath(path)
    
    def get_relative_path(self, path: str, start: str = None) -> str:
        if start is None:
            start = os.getcwd()
        return os.path.relpath(path, start)
    
    def get_dirname(self, path: str) -> str:
        return os.path.dirname(path)
    
    def get_basename(self, path: str) -> str:
        return os.path.basename(path)
    
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
    
    def move_file(self, src: str, dst: str) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(dst)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        shutil.move(src, dst)
    
    def move_directory(self, src: str, dst: str) -> None:
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(dst)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        shutil.move(src, dst)
    
    def get_file_size(self, path: str) -> int:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        return os.path.getsize(path)
    
    def get_modified_time(self, path: str) -> float:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        return os.path.getmtime(path)
    
    def get_file_mode(self, path: str) -> int:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        return os.stat(path).st_mode
    
    def set_file_mode(self, path: str, mode: int) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        os.chmod(path, mode)
    
    def glob(self, pattern: str) -> List[str]:
        import glob
        return glob.glob(pattern)


class InMemoryFileSystem(FileSystem):
    """
    Purely in-memory implementation of FileSystem for tests.
    
    This implementation stores files and directories in memory,
    making it perfect for unit tests that don't need real file system access.
    """
    
    def __init__(self):
        """Initialize an empty file system."""
        self._files = {}  # path -> (content, mode)
        self._dirs = {}   # path -> mode
        self._mtimes = {} # path -> modified time
    
    def exists(self, path: str) -> bool:
        return path in self._files or path in self._dirs
    
    def is_file(self, path: str) -> bool:
        return path in self._files
    
    def is_dir(self, path: str) -> bool:
        if path in self._dirs:
            return True
        
        # Check if any file or directory is under this path
        path_with_sep = f"{path}/" if not path.endswith('/') else path
        for file_path in self._files:
            if file_path.startswith(path_with_sep):
                return True
        for dir_path in self._dirs:
            if dir_path.startswith(path_with_sep):
                return True
                
        return False
    
    def read_file(self, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        content, _ = self._files[path]
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return content
    
    def read_bytes(self, path: str) -> bytes:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        content, _ = self._files[path]
        if isinstance(content, str):
            return content.encode('utf-8')
        return content
    
    def write_file(self, path: str, content: str, mode: int = None) -> None:
        # Create parent directories
        parent_dir = self.get_dirname(path)
        if parent_dir:
            self.create_directory(parent_dir)
        
        self._files[path] = (content, mode)
        self._mtimes[path] = time.time()
    
    def write_bytes(self, path: str, content: bytes, mode: int = None) -> None:
        # Create parent directories
        parent_dir = self.get_dirname(path)
        if parent_dir:
            self.create_directory(parent_dir)
        
        self._files[path] = (content, mode)
        self._mtimes[path] = time.time()
    
    def append_file(self, path: str, content: str) -> None:
        if path in self._files:
            existing_content, mode = self._files[path]
            if isinstance(existing_content, bytes):
                self._files[path] = (existing_content + content.encode('utf-8'), mode)
            else:
                self._files[path] = (existing_content + content, mode)
        else:
            self.write_file(path, content)
        self._mtimes[path] = time.time()
    
    def delete_file(self, path: str) -> None:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        del self._files[path]
        if path in self._mtimes:
            del self._mtimes[path]
    
    def create_directory(self, path: str, mode: int = None) -> None:
        if not path or path == '/':
            return
            
        self._dirs[path] = mode
        
        # Ensure all parent directories exist
        parent_dir = self.get_dirname(path)
        if parent_dir and parent_dir != path:  # Prevent infinite recursion
            self.create_directory(parent_dir)
    
    def list_dir(self, path: str) -> List[str]:
        if not self.is_dir(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        # Get all files and directories directly under this path
        result = set()
        path_with_sep = f"{path}/" if not path.endswith('/') else path
        
        # Add files
        for file_path in self._files:
            if self.get_dirname(file_path) == path:
                result.add(self.get_basename(file_path))
        
        # Add directories
        for dir_path in self._dirs:
            if self.get_dirname(dir_path) == path:
                result.add(self.get_basename(dir_path))
            elif dir_path.startswith(path_with_sep):
                # Add subdirectory one level down
                rel_path = dir_path[len(path_with_sep):]
                if '/' in rel_path:
                    subdir = rel_path.split('/')[0]
                    result.add(subdir)
        
        return list(result)
    
    def list_files(self, path: str, pattern: str = None) -> List[str]:
        if not self.is_dir(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        # Get all files directly under this path
        files = []
        for file_path in self._files:
            if self.get_dirname(file_path) == path:
                files.append(self.get_basename(file_path))
        
        # Apply pattern if provided
        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]
        
        return files
    
    def list_dirs(self, path: str) -> List[str]:
        if not self.is_dir(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        # Get all directories directly under this path
        dirs = set()
        path_with_sep = f"{path}/" if not path.endswith('/') else path
        
        # Add explicit directories
        for dir_path in self._dirs:
            if self.get_dirname(dir_path) == path:
                dirs.add(self.get_basename(dir_path))
        
        # Add implicit directories (parent of files)
        for file_path in self._files:
            if file_path.startswith(path_with_sep):
                rel_path = file_path[len(path_with_sep):]
                if '/' in rel_path:
                    subdir = rel_path.split('/')[0]
                    dirs.add(subdir)
        
        return list(dirs)
    
    def delete_directory(self, path: str, recursive: bool = False) -> None:
        if not self.is_dir(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        path_with_sep = f"{path}/" if not path.endswith('/') else path
        
        # Check if directory is empty
        has_contents = False
        for file_path in self._files:
            if file_path.startswith(path_with_sep) or self.get_dirname(file_path) == path:
                has_contents = True
                break
                
        if not has_contents:
            for dir_path in self._dirs:
                if dir_path != path and (dir_path.startswith(path_with_sep) or self.get_dirname(dir_path) == path):
                    has_contents = True
                    break
        
        if has_contents and not recursive:
            raise OSError(f"Directory not empty: {path}")
        
        # Remove the directory and its contents
        if path in self._dirs:
            del self._dirs[path]
            
        if recursive:
            # Remove all files in the directory
            for file_path in list(self._files.keys()):
                if file_path.startswith(path_with_sep):
                    del self._files[file_path]
                    if file_path in self._mtimes:
                        del self._mtimes[file_path]
            
            # Remove all subdirectories
            for dir_path in list(self._dirs.keys()):
                if dir_path.startswith(path_with_sep):
                    del self._dirs[dir_path]
    
    def join_paths(self, *paths: str) -> str:
        return os.path.join(*paths)
    
    def expand_path(self, path: str) -> str:
        # In-memory doesn't need to expand paths, but we'll handle common cases
        if path.startswith('~'):
            return os.path.expanduser(path)
        return os.path.expandvars(path)
    
    def get_absolute_path(self, path: str) -> str:
        # For in-memory, we'll just normalize the path
        return os.path.normpath(path)
    
    def get_relative_path(self, path: str, start: str = None) -> str:
        if start is None:
            start = os.getcwd()
        return os.path.relpath(path, start)
    
    def get_dirname(self, path: str) -> str:
        return os.path.dirname(path)
    
    def get_basename(self, path: str) -> str:
        return os.path.basename(path)
    
    def copy_file(self, src: str, dst: str) -> None:
        if src not in self._files:
            raise FileNotFoundError(f"Source file not found: {src}")
        
        # Create parent directories
        parent_dir = self.get_dirname(dst)
        if parent_dir:
            self.create_directory(parent_dir)
        
        # Copy the file
        self._files[dst] = self._files[src]
        self._mtimes[dst] = time.time()
    
    def copy_directory(self, src: str, dst: str) -> None:
        if not self.is_dir(src):
            raise FileNotFoundError(f"Source directory not found: {src}")
        
        # Create destination directory
        self.create_directory(dst)
        
        # Copy all files in the directory
        src_with_sep = f"{src}/" if not src.endswith('/') else src
        dst_with_sep = f"{dst}/" if not dst.endswith('/') else dst
        
        for file_path in list(self._files.keys()):
            if file_path.startswith(src_with_sep) or self.get_dirname(file_path) == src:
                if file_path.startswith(src_with_sep):
                    rel_path = file_path[len(src_with_sep):]
                    dst_path = f"{dst_with_sep}{rel_path}"
                else:
                    dst_path = self.join_paths(dst, self.get_basename(file_path))
                self._files[dst_path] = self._files[file_path]
                self._mtimes[dst_path] = time.time()
        
        # Copy all subdirectories
        for dir_path in list(self._dirs.keys()):
            if dir_path.startswith(src_with_sep) or self.get_dirname(dir_path) == src:
                if dir_path.startswith(src_with_sep):
                    rel_path = dir_path[len(src_with_sep):]
                    dst_dir_path = f"{dst_with_sep}{rel_path}"
                else:
                    dst_dir_path = self.join_paths(dst, self.get_basename(dir_path))
                self._dirs[dst_dir_path] = self._dirs.get(dir_path)
    
    def move_file(self, src: str, dst: str) -> None:
        self.copy_file(src, dst)
        self.delete_file(src)
    
    def move_directory(self, src: str, dst: str) -> None:
        self.copy_directory(src, dst)
        self.delete_directory(src, recursive=True)
    
    def get_file_size(self, path: str) -> int:
        if path not in self._files:
            raise FileNotFoundError(f"File not found: {path}")
        content, _ = self._files[path]
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        return len(content)
    
    def get_modified_time(self, path: str) -> float:
        if path not in self._files and path not in self._dirs:
            raise FileNotFoundError(f"Path not found: {path}")
        return self._mtimes.get(path, 0.0)
    
    def get_file_mode(self, path: str) -> int:
        if path in self._files:
            _, mode = self._files[path]
            return mode or 0o644  # Default mode
        elif path in self._dirs:
            return self._dirs[path] or 0o755  # Default mode
        else:
            raise FileNotFoundError(f"Path not found: {path}")
    
    def set_file_mode(self, path: str, mode: int) -> None:
        if path in self._files:
            content, _ = self._files[path]
            self._files[path] = (content, mode)
        elif path in self._dirs:
            self._dirs[path] = mode
        else:
            raise FileNotFoundError(f"Path not found: {path}")
    
    def glob(self, pattern: str) -> List[str]:
        import fnmatch
        
        # Convert glob pattern to regex pattern
        regex_pattern = fnmatch.translate(pattern)
        import re
        compiled_pattern = re.compile(regex_pattern)
        
        # Check all files and directories
        matches = []
        for path in list(self._files.keys()) + list(self._dirs.keys()):
            if compiled_pattern.match(path):
                matches.append(path)
                
        return matches


class TempFileSystem(RealFileSystem):
    """
    Implementation of FileSystem that uses a temporary directory.
    
    This implementation is useful for tests that need real file system operations
    but should be isolated from the rest of the file system.
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize with an optional specific temp directory.
        
        Args:
            temp_dir: Optional path to use as the temporary directory.
                     If not provided, a new temporary directory will be created.
        """
        super().__init__()
        self._temp_dir = temp_dir or tempfile.mkdtemp()
        self._virtual_paths = {}  # virtual path -> real path
        
        # Ensure the temp directory exists
        os.makedirs(self._temp_dir, exist_ok=True)
        
        logger.debug(f"TempFileSystem initialized with temp_dir: {self._temp_dir}")
    
    def _get_real_path(self, path: str) -> str:
        """
        Convert a virtual path to a real path in the temp directory.
        
        Args:
            path: The virtual path.
            
        Returns:
            The real path in the temporary directory.
        """
        if path in self._virtual_paths:
            return self._virtual_paths[path]
            
        # Normalize the path to remove any '..' or '.' components
        norm_path = os.path.normpath(path)
        
        # If the path is already absolute and starts with the temp directory,
        # it's already a real path
        if os.path.isabs(norm_path) and norm_path.startswith(self._temp_dir):
            self._virtual_paths[path] = norm_path
            return norm_path
        
        # Remove leading '/' to make the path relative
        if norm_path.startswith('/'):
            norm_path = norm_path[1:]
            
        real_path = os.path.join(self._temp_dir, norm_path)
        self._virtual_paths[path] = real_path
        return real_path
    
    def exists(self, path: str) -> bool:
        return super().exists(self._get_real_path(path))
    
    def is_file(self, path: str) -> bool:
        return super().is_file(self._get_real_path(path))
    
    def is_dir(self, path: str) -> bool:
        return super().is_dir(self._get_real_path(path))
    
    def read_file(self, path: str) -> str:
        return super().read_file(self._get_real_path(path))
    
    def read_bytes(self, path: str) -> bytes:
        return super().read_bytes(self._get_real_path(path))
    
    def write_file(self, path: str, content: str, mode: int = None) -> None:
        return super().write_file(self._get_real_path(path), content, mode)
    
    def write_bytes(self, path: str, content: bytes, mode: int = None) -> None:
        return super().write_bytes(self._get_real_path(path), content, mode)
    
    def append_file(self, path: str, content: str) -> None:
        return super().append_file(self._get_real_path(path), content)
    
    def delete_file(self, path: str) -> None:
        return super().delete_file(self._get_real_path(path))
    
    def create_directory(self, path: str, mode: int = None) -> None:
        return super().create_directory(self._get_real_path(path), mode)
    
    def list_dir(self, path: str) -> List[str]:
        return super().list_dir(self._get_real_path(path))
    
    def list_files(self, path: str, pattern: str = None) -> List[str]:
        return super().list_files(self._get_real_path(path), pattern)
    
    def list_dirs(self, path: str) -> List[str]:
        return super().list_dirs(self._get_real_path(path))
    
    def delete_directory(self, path: str, recursive: bool = False) -> None:
        return super().delete_directory(self._get_real_path(path), recursive)
    
    def join_paths(self, *paths: str) -> str:
        # Join paths normally, but don't convert to real path
        return os.path.join(*paths)
    
    def copy_file(self, src: str, dst: str) -> None:
        return super().copy_file(self._get_real_path(src), self._get_real_path(dst))
    
    def copy_directory(self, src: str, dst: str) -> None:
        return super().copy_directory(self._get_real_path(src), self._get_real_path(dst))
    
    def move_file(self, src: str, dst: str) -> None:
        return super().move_file(self._get_real_path(src), self._get_real_path(dst))
    
    def move_directory(self, src: str, dst: str) -> None:
        return super().move_directory(self._get_real_path(src), self._get_real_path(dst))
    
    def get_file_size(self, path: str) -> int:
        return super().get_file_size(self._get_real_path(path))
    
    def get_modified_time(self, path: str) -> float:
        return super().get_modified_time(self._get_real_path(path))
    
    def get_file_mode(self, path: str) -> int:
        return super().get_file_mode(self._get_real_path(path))
    
    def set_file_mode(self, path: str, mode: int) -> None:
        return super().set_file_mode(self._get_real_path(path), mode)
    
    def expand_path(self, path: str) -> str:
        # Expand the path but don't convert to real path
        return os.path.expanduser(os.path.expandvars(path))
    
    def get_absolute_path(self, path: str) -> str:
        # Return the virtual absolute path, not the real one
        if os.path.isabs(path):
            return path
        return os.path.abspath(path)
    
    def get_relative_path(self, path: str, start: str = None) -> str:
        # Handle paths in the virtual space
        if start is None:
            start = os.getcwd()
        return os.path.relpath(path, start)
    
    def get_dirname(self, path: str) -> str:
        # Don't convert to real path
        return os.path.dirname(path)
    
    def get_basename(self, path: str) -> str:
        # Don't convert to real path
        return os.path.basename(path)
    
    def glob(self, pattern: str) -> List[str]:
        # Convert the pattern to a real path pattern
        real_pattern = self._get_real_path(pattern)
        
        # Get the real matches
        import glob
        real_matches = glob.glob(real_pattern)
        
        # Convert back to virtual paths
        virtual_matches = []
        for real_match in real_matches:
            # Find the virtual path for this real path
            for virtual, real in self._virtual_paths.items():
                if real == real_match:
                    virtual_matches.append(virtual)
                    break
            else:
                # If we don't have a mapping, create one by removing the temp dir prefix
                if real_match.startswith(self._temp_dir):
                    rel_path = os.path.relpath(real_match, self._temp_dir)
                    virtual_path = '/' + rel_path if not rel_path.startswith('/') else rel_path
                    self._virtual_paths[virtual_path] = real_match
                    virtual_matches.append(virtual_path)
        
        return virtual_matches
    
    def cleanup(self) -> None:
        """
        Clean up the temporary directory.
        
        This should be called when the file system is no longer needed.
        """
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
            logger.debug(f"TempFileSystem cleaned up: {self._temp_dir}")
    
    def get_temp_dir(self) -> str:
        """
        Get the temporary directory path.
        
        Returns:
            The path to the temporary directory.
        """
        return self._temp_dir


# Create singleton instances for convenience
real_file_system = RealFileSystem()

# Utility functions for testing
def create_in_memory_fs() -> InMemoryFileSystem:
    """
    Create a new in-memory file system for testing.
    
    Returns:
        A new InMemoryFileSystem instance.
    """
    return InMemoryFileSystem()

def create_temp_fs(temp_dir: Optional[str] = None) -> TempFileSystem:
    """
    Create a new temporary file system for testing.
    
    Args:
        temp_dir: Optional path to use as the temporary directory.
                 If not provided, a new temporary directory will be created.
    
    Returns:
        A new TempFileSystem instance.
    """
    return TempFileSystem(temp_dir)

def setup_test_files(fs: FileSystem, files: Dict[str, str]) -> None:
    """
    Set up test files in a file system.
    
    Args:
        fs: The file system to use.
        files: A dictionary mapping file paths to content.
    """
    for path, content in files.items():
        fs.write_file(path, content)

def setup_test_dirs(fs: FileSystem, dirs: List[str]) -> None:
    """
    Set up test directories in a file system.
    
    Args:
        fs: The file system to use.
        dirs: A list of directory paths to create.
    """
    for path in dirs:
        fs.create_directory(path)

def assert_file_exists(fs: FileSystem, path: str, content: Optional[str] = None) -> None:
    """
    Assert that a file exists and optionally has the expected content.
    
    Args:
        fs: The file system to use.
        path: The path to check.
        content: Optional expected content of the file.
    
    Raises:
        AssertionError: If the file does not exist or the content doesn't match.
    """
    assert fs.exists(path), f"File does not exist: {path}"
    assert fs.is_file(path), f"Path is not a file: {path}"
    
    if content is not None:
        actual_content = fs.read_file(path)
        assert actual_content == content, f"File content doesn't match for {path}. Expected: {content}, Actual: {actual_content}"

def assert_dir_exists(fs: FileSystem, path: str) -> None:
    """
    Assert that a directory exists.
    
    Args:
        fs: The file system to use.
        path: The path to check.
    
    Raises:
        AssertionError: If the directory does not exist.
    """
    assert fs.exists(path), f"Directory does not exist: {path}"
    assert fs.is_dir(path), f"Path is not a directory: {path}" 