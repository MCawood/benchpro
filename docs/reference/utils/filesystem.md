# FileSystem Abstraction

## Overview

The FileSystem abstraction provides a unified interface for file system operations in BenchPRO. It allows the application to interact with the file system in a consistent way, regardless of whether it's running in a production environment or in tests.

## Purpose

The primary purposes of the FileSystem abstraction are:

1. **Decoupling**: Decouple the application code from the actual file system implementation, making it easier to test and maintain.
2. **Testing**: Enable testing of file system operations without relying on the actual file system, which can be slow, non-deterministic, and can leave behind test artifacts.
3. **Consistency**: Provide a consistent interface for file system operations across the application.
4. **Error Handling**: Standardize error handling for file system operations.

## Design

The FileSystem abstraction consists of:

1. **Abstract Interface**: The `FileSystem` abstract base class defines the interface for all file system operations.
2. **Implementations**:
   - `RealFileSystem`: Uses the actual file system for operations.
   - `InMemoryFileSystem`: Stores files and directories in memory, ideal for unit tests.
   - `TempFileSystem`: Uses a temporary directory for operations, useful for integration tests.
3. **Utility Functions**: Helper functions for testing and common operations.

### FileSystem Interface

The `FileSystem` interface provides methods for:

- **Basic File Operations**: `exists()`, `is_file()`, `is_dir()`, `read_file()`, `write_file()`, etc.
- **Directory Operations**: `create_directory()`, `list_dir()`, `list_files()`, `list_dirs()`, etc.
- **Path Operations**: `join_paths()`, `expand_path()`, `get_absolute_path()`, etc.
- **Copy/Move Operations**: `copy_file()`, `copy_directory()`, `move_file()`, `move_directory()`.
- **File Properties**: `get_file_size()`, `get_modified_time()`, `get_file_mode()`, etc.
- **Specialized Operations**: `read_yaml()`, `write_yaml()`, `glob()`, etc.

### RealFileSystem

The `RealFileSystem` implementation uses the actual file system for operations. It's the default implementation used in production code.

```python
from benchpro.utils.filesystem import RealFileSystem

fs = RealFileSystem()
fs.write_file("example.txt", "Hello, world!")
content = fs.read_file("example.txt")
```

### InMemoryFileSystem

The `InMemoryFileSystem` implementation stores files and directories in memory. It's ideal for unit tests that don't need to interact with the actual file system.

```python
from benchpro.utils.filesystem import InMemoryFileSystem, setup_test_files

fs = InMemoryFileSystem()
setup_test_files(fs, {
    "example.txt": "Hello, world!",
    "config/settings.yaml": "setting: value"
})
content = fs.read_file("example.txt")
```

### TempFileSystem

The `TempFileSystem` implementation uses a temporary directory for operations. It's useful for integration tests that need to interact with the actual file system but should be isolated from the rest of the system.

```python
from benchpro.utils.filesystem import TempFileSystem

fs = TempFileSystem()
fs.write_file("example.txt", "Hello, world!")
content = fs.read_file("example.txt")
# The file is created in a temporary directory
fs.cleanup()  # Clean up the temporary directory
```

## Usage in BenchPRO

The FileSystem abstraction is used throughout BenchPRO for file system operations. Key components that use it include:

### ConfigManager

The `ConfigManager` class uses the FileSystem abstraction to load, save, and manage configuration files.

```python
from benchpro.utils.filesystem import RealFileSystem
from benchpro.config.config_manager import ConfigManager

fs = RealFileSystem()
config_manager = ConfigManager(file_system=fs)
config = config_manager.load_profile_config("my_profile")
```

### Testing

The FileSystem abstraction is particularly useful for testing. It allows tests to run without relying on the actual file system, making them faster, more reliable, and avoiding test artifacts.

```python
from benchpro.utils.filesystem import InMemoryFileSystem, setup_test_files
from benchpro.config.config_manager import ConfigManager

def test_config_manager():
    fs = InMemoryFileSystem()
    setup_test_files(fs, {
        "config/default.yaml": "default: value",
        "profiles/test_profile.yaml": "profile: value"
    })
    config_manager = ConfigManager(file_system=fs)
    config = config_manager.load_profile_config("test_profile")
    assert config["profile"] == "value"
```

## Utility Functions

The FileSystem abstraction includes several utility functions to make testing easier:

- `create_in_memory_fs()`: Create a new InMemoryFileSystem instance.
- `create_temp_fs()`: Create a new TempFileSystem instance.
- `setup_test_files()`: Set up test files in a file system.
- `setup_test_dirs()`: Set up test directories in a file system.
- `assert_file_exists()`: Assert that a file exists and optionally has the expected content.
- `assert_dir_exists()`: Assert that a directory exists.

## Best Practices

When using the FileSystem abstraction, follow these best practices:

1. **Dependency Injection**: Pass a FileSystem instance to classes that need file system access, rather than creating one internally.
2. **Use the Interface**: Program against the FileSystem interface, not specific implementations.
3. **Error Handling**: Handle file system errors appropriately, using try/except blocks for operations that might fail.
4. **Testing**: Use InMemoryFileSystem or TempFileSystem for tests, not RealFileSystem.
5. **Cleanup**: Always clean up temporary resources, especially when using TempFileSystem.

## Example: Reading and Writing Files

```python
from benchpro.utils.filesystem import FileSystem, RealFileSystem

def process_file(input_path: str, output_path: str, fs: FileSystem = None):
    """Process a file and write the results to another file."""
    fs = fs or RealFileSystem()
    
    # Read the input file
    try:
        content = fs.read_file(input_path)
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        return
    
    # Process the content
    processed_content = content.upper()
    
    # Write the output file
    try:
        fs.write_file(output_path, processed_content)
    except IOError as e:
        print(f"Error writing output file: {e}")
```

## Example: Working with Directories

```python
from benchpro.utils.filesystem import FileSystem, RealFileSystem

def process_directory(input_dir: str, output_dir: str, fs: FileSystem = None):
    """Process all files in a directory and write the results to another directory."""
    fs = fs or RealFileSystem()
    
    # Create the output directory if it doesn't exist
    fs.create_directory(output_dir)
    
    # Get all files in the input directory
    try:
        files = fs.list_files(input_dir)
    except FileNotFoundError:
        print(f"Input directory not found: {input_dir}")
        return
    
    # Process each file
    for filename in files:
        input_path = fs.join_paths(input_dir, filename)
        output_path = fs.join_paths(output_dir, filename)
        
        # Skip directories
        if not fs.is_file(input_path):
            continue
        
        # Read, process, and write the file
        content = fs.read_file(input_path)
        processed_content = content.upper()
        fs.write_file(output_path, processed_content)
``` 