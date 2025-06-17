# FileSystem Abstraction Enhancement Design

## Current State Analysis

The existing FileSystem abstraction provides a solid foundation but has several limitations:

1. **Mixed Implementation in TestFileSystem**: The TestFileSystem implementation currently mixes in-memory operations with real file system operations when using a base_temp_dir, making testing less deterministic.

2. **Inconsistent Interface**: Some methods handle directory creation differently between RealFileSystem and TestFileSystem.

3. **Missing Operations**: Several common file system operations are missing from the interface.

4. **Error Handling**: Inconsistent error handling across implementations.

5. **Permissions**: No consistent handling of file permissions.

6. **Lack of Test Utilities**: No helper methods specifically designed for testing.

## Design Goals

1. Create a more comprehensive and consistent FileSystem abstraction that:
   - Eliminates the need for test-specific code paths
   - Provides complete isolation for tests
   - Supports all necessary file system operations
   - Has consistent error handling

2. Provide implementations that:
   - RealFileSystem: Wraps actual file system operations
   - InMemoryFileSystem: Pure in-memory implementation for tests
   - TempFileSystem: Uses a temporary directory for tests

3. Create utility functions to help with testing file system operations.

## Interface Design

```python
class FileSystem:
    """Abstract interface for file system operations."""

    # Basic file operations
    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        
    def is_file(self, path: str) -> bool:
        """Check if a path is a file."""
        
    def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        
    def read_file(self, path: str) -> str:
        """Read a file's contents as a string."""
        
    def read_bytes(self, path: str) -> bytes:
        """Read a file's contents as bytes."""
        
    def write_file(self, path: str, content: str, mode: int = None) -> None:
        """Write string content to a file."""
        
    def write_bytes(self, path: str, content: bytes, mode: int = None) -> None:
        """Write binary content to a file."""
        
    def append_file(self, path: str, content: str) -> None:
        """Append string content to a file."""
        
    def delete_file(self, path: str) -> None:
        """Delete a file."""
    
    # Directory operations
    def create_directory(self, path: str, mode: int = None) -> None:
        """Create a directory and any parent directories."""
        
    def list_dir(self, path: str) -> List[str]:
        """List contents of a directory."""
        
    def list_files(self, path: str, pattern: str = None) -> List[str]:
        """List files in a directory, optionally matching a pattern."""
        
    def list_dirs(self, path: str) -> List[str]:
        """List subdirectories in a directory."""
        
    def delete_directory(self, path: str, recursive: bool = False) -> None:
        """Delete a directory."""
    
    # Path operations
    def join_paths(self, *paths: str) -> str:
        """Join paths together."""
        
    def expand_path(self, path: str) -> str:
        """Expand user and environment variables in a path."""
        
    def get_absolute_path(self, path: str) -> str:
        """Get the absolute path."""
        
    def get_relative_path(self, path: str, start: str = None) -> str:
        """Get a path relative to another path."""
        
    def get_dirname(self, path: str) -> str:
        """Get the directory name of a path."""
        
    def get_basename(self, path: str) -> str:
        """Get the base name of a path."""
    
    # Copy/move operations
    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file from src to dst."""
        
    def copy_directory(self, src: str, dst: str) -> None:
        """Copy a directory from src to dst."""
        
    def move_file(self, src: str, dst: str) -> None:
        """Move a file from src to dst."""
        
    def move_directory(self, src: str, dst: str) -> None:
        """Move a directory from src to dst."""
    
    # File properties
    def get_file_size(self, path: str) -> int:
        """Get the size of a file in bytes."""
        
    def get_modified_time(self, path: str) -> float:
        """Get the last modified time of a file."""
        
    def get_file_mode(self, path: str) -> int:
        """Get the permission mode of a file."""
        
    def set_file_mode(self, path: str, mode: int) -> None:
        """Set the permission mode of a file."""
    
    # Specialized operations
    def read_yaml(self, path: str) -> Dict[str, Any]:
        """Read a YAML file."""
        
    def write_yaml(self, path: str, data: Dict[str, Any]) -> None:
        """Write data to a YAML file."""
        
    def glob(self, pattern: str) -> List[str]:
        """Find paths matching a glob pattern."""
```

## Implementation Strategy

### 1. RealFileSystem

```python
class RealFileSystem(FileSystem):
    """Implementation that uses the real file system."""
    
    def exists(self, path: str) -> bool:
        return os.path.exists(path)
        
    def is_file(self, path: str) -> bool:
        return os.path.isfile(path)
    
    # ... implement other methods using os, shutil, etc.
```

### 2. InMemoryFileSystem

```python
class InMemoryFileSystem(FileSystem):
    """Purely in-memory implementation for tests."""
    
    def __init__(self):
        self._files = {}  # path -> content
        self._dirs = set()  # set of directory paths
        
    def exists(self, path: str) -> bool:
        return path in self._files or path in self._dirs
        
    def is_file(self, path: str) -> bool:
        return path in self._files
    
    # ... implement other methods using in-memory data structures
```

### 3. TempFileSystem

```python
class TempFileSystem(RealFileSystem):
    """Implementation that uses a temporary directory."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize with an optional specific temp directory."""
        self._temp_dir = temp_dir or tempfile.mkdtemp()
        self._real_paths = {}  # virtual path -> real path
        
    def _get_real_path(self, path: str) -> str:
        """Convert a virtual path to a real path in the temp directory."""
        if path in self._real_paths:
            return self._real_paths[path]
            
        real_path = os.path.join(self._temp_dir, path.lstrip('/'))
        self._real_paths[path] = real_path
        return real_path
        
    def exists(self, path: str) -> bool:
        return super().exists(self._get_real_path(path))
    
    # ... implement other methods by delegating to RealFileSystem with path translation
```

## Migration Strategy

1. **Step 1**: Implement the enhanced FileSystem interface
   - Create the new interface with additional methods
   - Implement RealFileSystem completely
   - Create initial versions of InMemoryFileSystem and TempFileSystem

2. **Step 2**: Update existing components to use the enhanced interface
   - Update ConfigManager to use the new methods
   - Update UserDirManager to use the enhanced FileSystem
   - Update other components that use file system operations directly

3. **Step 3**: Improve test utilities
   - Create helper functions for setting up test file systems
   - Add assertion functions for file system operations

4. **Step 4**: Refactor tests to use the enhanced file system
   - Replace test-specific code paths with proper abstractions
   - Use InMemoryFileSystem or TempFileSystem based on test needs

## Benefits

1. **Improved Testability**: No need for test-specific code paths
2. **Better Isolation**: Tests can run in complete isolation from the real file system
3. **Comprehensive Interface**: All necessary file system operations are available
4. **Consistent Error Handling**: Standardized approach to file system errors
5. **Reduced Duplication**: Common patterns like "ensure parent directory exists" are handled consistently

## Testing Approach

1. **Unit Tests**: 
   - Test each file system implementation against the interface contract
   - Verify error handling for edge cases

2. **Integration Tests**:
   - Verify components work correctly with different file system implementations
   - Test cross-component interactions using the abstraction

## Next Steps

1. Implement the enhanced FileSystem interface and implementations
2. Update UserDirManager to use the enhanced FileSystem
3. Update ConfigManager to use the enhanced FileSystem
4. Refactor tests to use the new abstraction 