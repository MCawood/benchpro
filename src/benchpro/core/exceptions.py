class BenchProError(Exception):
    """Base class for all BenchPro exceptions."""
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

class ConfigError(BenchProError):
    """Raised when there is an error in configuration loading or validation."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=1)

class BuildError(BenchProError):
    """Raised when an application build fails."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=2)

class TaskError(BenchProError):
    """Raised when a task execution fails."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=3)

class ValidationError(BenchProError):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=4)

class ResourceError(BenchProError):
    """Raised when there are issues with resource allocation."""
    def __init__(self, message: str):
        super().__init__(message, exit_code=5)
