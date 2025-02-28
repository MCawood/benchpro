"""Domain-specific error classes for BenchPRO."""

class DomainError(Exception):
    """Base class for domain-specific errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
        
    def __str__(self) -> str:
        return self.message

class ResourceError(DomainError):
    """Raised when there are insufficient resources to execute a task or job."""
    pass

class TaskExecutionError(DomainError):
    """Raised when task execution fails."""
    pass

class JobExecutionError(DomainError):
    """Raised when a job fails to execute."""
    pass

class ValidationError(DomainError):
    """Raised when validation fails."""
    pass

class StagingError(DomainError):
    """Raised when file staging fails."""
    pass

class ExecutorError(DomainError):
    """Raised when executor operations fail."""
    pass 