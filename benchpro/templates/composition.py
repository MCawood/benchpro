"""
Template composition engine for BenchPRO.

This module provides a template composition engine that assembles template blocks
into complete scripts.
"""

from typing import Dict, Any, List, Optional

from benchpro.templates.blocks import TemplateBlock
from benchpro.utils.logger import get_logger


class TemplateCompositionEngine:
    """
    Engine for composing templates from blocks.
    
    The TemplateCompositionEngine is responsible for assembling template blocks
    into complete scripts.
    """
    
    def __init__(self):
        """Initialize the TemplateCompositionEngine."""
        self.logger = get_logger(__name__)
        self.blocks = {}  # name -> block
    
    def register_block(self, block: TemplateBlock):
        """
        Register a template block.
        
        Args:
            block: The template block to register.
        """
        self.logger.debug(f"Registering template block: {block.name}")
        self.blocks[block.name] = block
    
    def unregister_block(self, block_name: str):
        """
        Unregister a template block.
        
        Args:
            block_name: The name of the block to unregister.
        """
        if block_name in self.blocks:
            self.logger.debug(f"Unregistering template block: {block_name}")
            del self.blocks[block_name]
    
    def get_block(self, block_name: str) -> Optional[TemplateBlock]:
        """
        Get a template block by name.
        
        Args:
            block_name: The name of the block to get.
            
        Returns:
            The template block, or None if not found.
        """
        return self.blocks.get(block_name)
    
    def get_applicable_blocks(self, execution_context: str) -> List[TemplateBlock]:
        """
        Get blocks applicable to the given execution context.
        
        Args:
            execution_context: The execution context to filter by.
            
        Returns:
            List of applicable blocks, sorted by priority.
        """
        applicable_blocks = []
        
        for name, block in self.blocks.items():
            if block.applies_to_context(execution_context):
                applicable_blocks.append(block)
        
        # Sort blocks by priority
        applicable_blocks.sort(key=lambda b: b.priority)
        
        return applicable_blocks
    
    def compose(self, context: Dict[str, Any], execution_context: str) -> str:
        """
        Compose a template from blocks.
        
        Args:
            context: The context variables for rendering.
            execution_context: The execution context to filter blocks by.
            
        Returns:
            The composed template as a string.
        """
        self.logger.debug(f"Composing template for execution context: {execution_context}")
        
        # Get applicable blocks
        applicable_blocks = self.get_applicable_blocks(execution_context)
        
        # Render blocks
        rendered_blocks = []
        for block in applicable_blocks:
            self.logger.debug(f"Rendering block: {block.name}")
            try:
                rendered = block.render(context, execution_context)
                if rendered.strip():  # Only include non-empty blocks
                    rendered_blocks.append(rendered)
            except Exception as e:
                self.logger.error(f"Error rendering block {block.name}: {str(e)}")
                raise
        
        # Join with newlines and ensure there's a trailing newline
        composed_content = "\n\n".join(rendered_blocks)
        
        # Add a newline at the end if it doesn't have one already
        if not composed_content.endswith('\n'):
            composed_content += '\n'
            
        return composed_content 