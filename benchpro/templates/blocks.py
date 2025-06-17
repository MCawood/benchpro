"""
Template Block System for BenchPRO.

This module defines the block-based template system for composing scripts
from reusable components. Each block represents a segment of a script
with specific responsibility and execution context.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from jinja2 import Environment, FileSystemLoader, Template, exceptions

from benchpro.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateError(Exception):
    """Exception raised for template-related errors."""
    pass


class TemplateBlock(ABC):
    """
    Abstract base class for template blocks.
    
    A template block represents a reusable piece of template content with a specific
    purpose and priority in the final script.
    """
    
    def __init__(self, name: str, priority: int, 
                 description: str = "", 
                 contexts: Optional[List[str]] = None):
        """
        Initialize a template block.
        
        Args:
            name: Unique name for this block.
            priority: Priority value for ordering blocks (lower values come first).
            description: Optional description of the block's purpose.
            contexts: Optional list of execution contexts this block applies to.
                If None, applies to all contexts.
        """
        self.name = name
        self.priority = priority
        self.description = description
        self.contexts = contexts
        self.logger = get_logger(__name__)
    
    @abstractmethod
    def render(self, context: Dict[str, Any], execution_context: str) -> str:
        """
        Render this block with the given context variables.
        
        Args:
            context: Dictionary of variables to use for rendering.
            execution_context: The execution context being rendered for.
            
        Returns:
            The rendered content as a string.
            
        Raises:
            TemplateError: If rendering fails.
        """
        pass
    
    def applies_to_context(self, execution_context: str) -> bool:
        """
        Check if this block applies to the given execution context.
        
        Args:
            execution_context: The execution context to check.
            
        Returns:
            True if this block applies to the given context, False otherwise.
        """
        if self.contexts is None:
            return True
        return execution_context in self.contexts


class StringTemplateBlock(TemplateBlock):
    """
    A template block containing a string template.
    
    This block renders a Jinja2 template provided as a string.
    """
    
    def __init__(self, name: str, content: str, priority: int, 
                 description: str = "", 
                 contexts: Optional[List[str]] = None):
        """
        Initialize a string template block.
        
        Args:
            name: Unique name for this block.
            content: Jinja2 template content as a string.
            priority: Priority value for ordering blocks.
            description: Optional description of the block's purpose.
            contexts: Optional list of execution contexts this block applies to.
        """
        super().__init__(name, priority, description, contexts)
        self.content = content
    
    def render(self, context: Dict[str, Any], execution_context: str) -> str:
        """
        Render the template with the given context variables.
        
        Args:
            context: Dictionary of variables to use for rendering.
            execution_context: The execution context being rendered for.
            
        Returns:
            The rendered content as a string.
            
        Raises:
            TemplateError: If rendering fails.
        """
        try:
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            template = env.from_string(self.content)
            rendered = template.render(**context)
            # Ensure no unwanted trailing characters 
            rendered = rendered.rstrip()
            return rendered
        except exceptions.TemplateError as e:
            self.logger.error(f"Error rendering template block {self.name}: {str(e)}")
            raise TemplateError(f"Error rendering template block {self.name}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error rendering template block {self.name}: {str(e)}")
            raise TemplateError(f"Unexpected error rendering template block {self.name}: {str(e)}")


class FileTemplateBlock(TemplateBlock):
    """
    A template block that loads content from a file.
    
    This block renders a Jinja2 template loaded from a file.
    """
    
    def __init__(self, name: str, file_path: str, priority: int, 
                 description: str = "", 
                 contexts: Optional[List[str]] = None,
                 search_paths: Optional[List[str]] = None):
        """
        Initialize a file template block.
        
        Args:
            name: Unique name for this block.
            file_path: Path to the template file.
            priority: Priority value for ordering blocks.
            description: Optional description of the block's purpose.
            contexts: Optional list of execution contexts this block applies to.
            search_paths: Optional list of paths to search for the template.
        """
        super().__init__(name, priority, description, contexts)
        self.file_path = file_path
        self.search_paths = search_paths or []
    
    def render(self, context: Dict[str, Any], execution_context: str) -> str:
        """
        Render the template with the given context variables.
        
        Args:
            context: Dictionary of variables to use for rendering.
            execution_context: The execution context being rendered for.
            
        Returns:
            The rendered content as a string.
            
        Raises:
            TemplateError: If the template file cannot be found or rendering fails.
        """
        try:
            # If the file path is absolute or exists, use it directly
            if os.path.isabs(self.file_path) or os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    content = f.read()
                
                env = Environment(trim_blocks=True, lstrip_blocks=True)
                template = env.from_string(content)
                return template.render(**context)
            
            # Otherwise, try to load from search paths
            if self.search_paths:
                env = Environment(
                    loader=FileSystemLoader(self.search_paths),
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                try:
                    template = env.get_template(os.path.basename(self.file_path))
                    return template.render(**context)
                except exceptions.TemplateNotFound:
                    self.logger.error(f"Template file not found: {self.file_path}")
                    raise TemplateError(f"Template file not found: {self.file_path}")
            
            # If we get here, the template wasn't found
            self.logger.error(f"Template file not found: {self.file_path}")
            raise TemplateError(f"Template file not found: {self.file_path}")
        except exceptions.TemplateError as e:
            self.logger.error(f"Error rendering template file {self.file_path}: {str(e)}")
            raise TemplateError(f"Error rendering template file {self.file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error rendering template file {self.file_path}: {str(e)}")
            raise TemplateError(f"Unexpected error rendering template file {self.file_path}: {str(e)}")


class FunctionTemplateBlock(TemplateBlock):
    """
    A template block that generates content using a function.
    
    This block renders content by calling a function with the context variables.
    """
    
    def __init__(self, name: str, function: Callable[[Dict[str, Any], str], str], priority: int, 
                 description: str = "", 
                 contexts: Optional[List[str]] = None):
        """
        Initialize a function template block.
        
        Args:
            name: Unique name for this block.
            function: Function to call for rendering.
                Should take context and execution_context as arguments.
            priority: Priority value for ordering blocks.
            description: Optional description of the block's purpose.
            contexts: Optional list of execution contexts this block applies to.
        """
        super().__init__(name, priority, description, contexts)
        self.function = function
    
    def render(self, context: Dict[str, Any], execution_context: str) -> str:
        """
        Render the template by calling the function.
        
        Args:
            context: Dictionary of variables to pass to the function.
            execution_context: The execution context being rendered for.
            
        Returns:
            The rendered content as a string.
            
        Raises:
            TemplateError: If function execution fails.
        """
        try:
            return self.function(context, execution_context)
        except Exception as e:
            self.logger.error(f"Error executing function for template block {self.name}: {str(e)}")
            raise TemplateError(f"Error executing function for template block {self.name}: {str(e)}") 