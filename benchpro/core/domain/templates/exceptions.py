"""Template-specific exceptions."""

class TemplateError(Exception):
    """Base exception for all template-related errors."""
    pass

class TemplateNotFoundError(TemplateError):
    """Raised when a template cannot be found."""
    pass

class TemplateConfigError(TemplateError):
    """Raised when there is an error in the template configuration."""
    pass

class TemplateVersionError(TemplateError):
    """Raised when there is an error with template versioning."""
    pass

class TemplateRenderError(TemplateError):
    """Raised when there is an error rendering a template."""
    pass

class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""
    pass

class TemplateVariableError(TemplateError):
    """Raised when there is an error with template variables."""
    pass

class TemplateSyntaxError(TemplateError):
    """Raised when there is a syntax error in the template."""
    pass 