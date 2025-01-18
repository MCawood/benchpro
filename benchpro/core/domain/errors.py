"""Domain-specific error classes for BenchPRO."""

class DomainError(Exception):
    """Base class for domain-specific errors."""
    pass

class ResourceError(DomainError):
    """Raised when there are insufficient resources to execute a task or job."""
    pass

class TaskExecutionError(DomainError):
    """Raised when a task fails to execute."""
    pass

class JobExecutionError(DomainError):
    """Raised when a job fails to execute."""
    pass

class ValidationError(DomainError):
    """Raised when validation fails."""
    pass

class StagingError(Exception):
    """Raised when file staging fails."""
    pass 