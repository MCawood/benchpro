# User Directory Manager

The User Directory Manager is responsible for managing user-specific directories and files for BenchPRO. It provides a consistent interface for accessing user directories, ensuring they exist, and managing user settings.

## Overview

The User Directory Manager handles the following responsibilities:

- Creating and managing user-specific directories
- Ensuring proper permissions for user directories
- Providing paths to user-specific files
- Loading and saving user settings
- Copying default files to user directories

## Architecture

The User Directory Manager follows a dependency injection pattern, allowing for better testability and flexibility:

```
┌─────────────────────────┐
│UserDirectoryManagerInterface│
└───────────┬─────────────┘
            │
            │implements
            ▼
┌─────────────────────────┐
│   UserDirectoryManager  │
└───────────┬─────────────┘
            │
            │uses
            ▼
┌─────────────────────────┐
│      FileSystem         │
└─────────────────────────┘
```

## Key Components

### UserDirectoryManagerInterface

An interface that defines the contract for all UserDirectoryManager implementations. This allows for dependency injection and easier testing.

```python
class UserDirectoryManagerInterface:
    def get_path(self, dir_key: str, *paths: str) -> str: ...
    def ensure_file_directory(self, file_path: str) -> bool: ...
    def get_application_directory(self) -> str: ...
    def get_benchmark_directory(self) -> str: ...
    def get_source_directory(self) -> str: ...
    def load_settings(self) -> Dict[str, Any]: ...
    def save_settings(self, settings: Dict[str, Any]) -> bool: ...
    def copy_default_files(self, source_dir: str, dest_dir_key: str, files: List[str]) -> bool: ...
    def copy_example_profiles(self) -> bool: ...
    def copy_default_source_files(self) -> bool: ...
```

### UserDirectoryManager

The concrete implementation of the UserDirectoryManagerInterface. It manages user-specific directories and files for BenchPRO.

```python
class UserDirectoryManager(UserDirectoryManagerInterface):
    def __init__(self, base_dir: Optional[str] = None, file_system: Optional[FileSystem] = None): ...
    def get_path(self, dir_key: str, *paths: str) -> str: ...
    def ensure_file_directory(self, file_path: str) -> bool: ...
    def get_application_directory(self) -> str: ...
    def get_benchmark_directory(self) -> str: ...
    def get_source_directory(self) -> str: ...
    def load_settings(self) -> Dict[str, Any]: ...
    def save_settings(self, settings: Dict[str, Any]) -> bool: ...
    def copy_default_files(self, source_dir: str, dest_dir_key: str, files: List[str]) -> bool: ...
    def copy_example_profiles(self) -> bool: ...
    def copy_default_source_files(self) -> bool: ...
    def set_test_environment(self, temp_dir: str, test_dirs: Optional[Dict[str, str]] = None) -> None: ...
    def reset_test_environment(self) -> None: ...
```

### Factory Function

A factory function to get or create a UserDirectoryManager instance. This provides a consistent way to get a UserDirectoryManager instance while supporting dependency injection.

```python
def get_user_dir_manager(base_dir: Optional[str] = None, file_system: Optional[FileSystem] = None) -> UserDirectoryManagerInterface: ...
```

## Default Directory Structure

The UserDirectoryManager creates and manages the following directory structure:

```
~/.benchpro/
├── inputs/
│   ├── application/  # Application profiles
│   ├── benchmark/    # Benchmark profiles
│   └── source/       # Source files
├── outputs/
│   ├── application/  # Application outputs
│   └── benchmark/    # Benchmark outputs
├── registry/         # Application registry
├── logs/             # Log files
└── cache/            # Cache files
```

## Usage Examples

### Basic Usage

```python
from benchpro.utils.user_dir import get_user_dir_manager

# Get the default UserDirectoryManager
user_dir_manager = get_user_dir_manager()

# Get a path to a user directory
app_dir = user_dir_manager.get_path("inputs_application")

# Ensure a directory exists for a file
user_dir_manager.ensure_file_directory("/path/to/file.txt")

# Load user settings
settings = user_dir_manager.load_settings()

# Save user settings
settings["logging_level"] = "DEBUG"
user_dir_manager.save_settings(settings)
```

### Dependency Injection

```python
from benchpro.utils.user_dir import UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.utils.filesystem import create_in_memory_fs

class MyComponent:
    def __init__(self, user_dir_manager: UserDirectoryManagerInterface = None):
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
    def get_app_dir(self):
        return self.user_dir_manager.get_application_directory()

# Create a UserDirectoryManager with an in-memory file system for testing
fs = create_in_memory_fs()
user_dir_manager = get_user_dir_manager(file_system=fs)

# Create the component with the injected UserDirectoryManager
component = MyComponent(user_dir_manager)
```

### Testing

```python
import pytest
from benchpro.utils.user_dir import UserDirectoryManager
from benchpro.utils.filesystem import create_in_memory_fs

@pytest.fixture
def in_memory_user_dir_manager():
    """Create a UserDirectoryManager with an in-memory file system."""
    fs = create_in_memory_fs()
    return UserDirectoryManager(base_dir="/test", file_system=fs)

def test_my_component(in_memory_user_dir_manager):
    # Create the component with the test UserDirectoryManager
    component = MyComponent(in_memory_user_dir_manager)
    
    # Test the component
    assert component.get_app_dir() == "/test/outputs/application"
```

## Best Practices

1. **Use Dependency Injection**: Always use dependency injection to provide a UserDirectoryManager to your components. This makes testing easier and reduces coupling.

2. **Use the Factory Function**: Use the `get_user_dir_manager()` function to get a UserDirectoryManager instance. This ensures consistent behavior and supports dependency injection.

3. **Handle File System Errors**: Always handle file system errors when using the UserDirectoryManager. The UserDirectoryManager will log errors, but it's up to the caller to handle them appropriately.

4. **Use the Interface**: Use the UserDirectoryManagerInterface type for parameters and variables. This makes it clear that any implementation of the interface can be used.

5. **Test with In-Memory File System**: Use the InMemoryFileSystem for testing. This avoids file system operations during tests and makes tests faster and more reliable. 