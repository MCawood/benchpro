"""
Tests for the template block system.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from benchpro.templates.blocks import (
    TemplateBlock, 
    StringTemplateBlock, 
    FileTemplateBlock, 
    FunctionTemplateBlock,
    TemplateError
)
from benchpro.templates.composition import TemplateCompositionEngine
from benchpro.templates.standard_blocks import (
    SHEBANG_BLOCK,
    SLURM_DIRECTIVES_BLOCK,
    register_standard_blocks
)
# Import our script generators - use the ScriptGenerationComponent from here to avoid circular imports
from benchpro.templates.script_generators import (
    ScriptGenerationComponent,  # Import from here instead of executor.components.interfaces
    ComposableScriptGenerator,
    LocalScriptGenerator,
    SlurmScriptGenerator
)


class TestTemplateBlocks:
    """Tests for template blocks."""
    
    def test_string_template_block(self):
        """Test StringTemplateBlock with static content."""
        block = StringTemplateBlock(
            name="test_block",
            content="Hello, world!",
            priority=10
        )
        
        # Test basic properties
        assert block.name == "test_block"
        assert block.priority == 10
        assert block.content == "Hello, world!"
        
        # Test rendering
        rendered = block.render({}, "local")
        assert rendered == "Hello, world!"
    
    def test_string_template_block_with_variables(self):
        """Test StringTemplateBlock with template variables."""
        block = StringTemplateBlock(
            name="test_block",
            content="Hello, {{ name }}!",
            priority=10
        )
        
        # Test rendering with variables
        rendered = block.render({"name": "World"}, "local")
        assert rendered == "Hello, World!"
    
    def test_string_template_block_context_filtering(self):
        """Test StringTemplateBlock context filtering."""
        block = StringTemplateBlock(
            name="test_block",
            content="Hello, world!",
            priority=10,
            contexts=["local"]
        )
        
        # Test context filtering
        assert block.applies_to_context("local") is True
        assert block.applies_to_context("slurm") is False
    
    def test_file_template_block(self, tmp_path):
        """Test FileTemplateBlock with a temporary file."""
        # Create a temporary template file
        template_file = tmp_path / "test_template.j2"
        template_file.write_text("Hello, {{ name }}!")
        
        block = FileTemplateBlock(
            name="test_block",
            file_path=str(template_file),
            priority=10
        )
        
        # Test basic properties
        assert block.name == "test_block"
        assert block.priority == 10
        assert block.file_path == str(template_file)
        
        # Test rendering with variables
        rendered = block.render({"name": "World"}, "local")
        assert rendered == "Hello, World!"
    
    def test_function_template_block(self):
        """Test FunctionTemplateBlock with a simple function."""
        def template_function(context, execution_context):
            return f"Hello, {context.get('name', 'Anonymous')}! Context: {execution_context}"
        
        block = FunctionTemplateBlock(
            name="test_block",
            function=template_function,
            priority=10
        )
        
        # Test basic properties
        assert block.name == "test_block"
        assert block.priority == 10
        
        # Test rendering with variables
        rendered = block.render({"name": "World"}, "local")
        assert rendered == "Hello, World! Context: local"
    
    def test_template_block_error_handling(self):
        """Test error handling in template blocks."""
        # Create a block with an invalid template
        block = StringTemplateBlock(
            name="error_block",
            content="Hello, {{ name }",  # Missing closing brace
            priority=10
        )
        
        # Test that rendering raises a TemplateError
        with pytest.raises(TemplateError):
            block.render({}, "local")


class TestTemplateCompositionEngine:
    """Tests for the template composition engine."""
    
    def test_block_registration(self):
        """Test registering blocks with the composition engine."""
        engine = TemplateCompositionEngine()
        
        # Register a block
        block = StringTemplateBlock(
            name="test_block",
            content="Hello, world!",
            priority=10
        )
        engine.register_block(block)
        
        # Check that the block was registered
        assert "test_block" in engine.blocks
        assert engine.blocks["test_block"] == block
        
        # Test getting a block by name
        retrieved_block = engine.get_block("test_block")
        assert retrieved_block == block
        
        # Test unregistering a block
        engine.unregister_block("test_block")
        assert "test_block" not in engine.blocks
    
    def test_block_ordering(self):
        """Test that blocks are ordered by priority."""
        engine = TemplateCompositionEngine()
        
        # Register blocks with different priorities
        block1 = StringTemplateBlock(
            name="block1",
            content="Block 1",
            priority=30
        )
        block2 = StringTemplateBlock(
            name="block2",
            content="Block 2",
            priority=10
        )
        block3 = StringTemplateBlock(
            name="block3",
            content="Block 3",
            priority=20
        )
        
        engine.register_block(block1)
        engine.register_block(block2)
        engine.register_block(block3)
        
        # Get applicable blocks
        applicable_blocks = engine.get_applicable_blocks("local")
        
        # Check the order
        assert len(applicable_blocks) == 3
        assert applicable_blocks[0] == block2  # Priority 10
        assert applicable_blocks[1] == block3  # Priority 20
        assert applicable_blocks[2] == block1  # Priority 30
    
    def test_context_filtering(self):
        """Test that blocks are filtered by execution context."""
        engine = TemplateCompositionEngine()
        
        # Register blocks with different contexts
        block1 = StringTemplateBlock(
            name="block1",
            content="Block 1",
            priority=10,
            contexts=["local"]
        )
        block2 = StringTemplateBlock(
            name="block2",
            content="Block 2",
            priority=20,
            contexts=["slurm"]
        )
        block3 = StringTemplateBlock(
            name="block3",
            content="Block 3",
            priority=30,
            contexts=None  # All contexts
        )
        
        engine.register_block(block1)
        engine.register_block(block2)
        engine.register_block(block3)
        
        # Get applicable blocks for local context
        local_blocks = engine.get_applicable_blocks("local")
        assert len(local_blocks) == 2
        assert block1 in local_blocks
        assert block2 not in local_blocks
        assert block3 in local_blocks
        
        # Get applicable blocks for slurm context
        slurm_blocks = engine.get_applicable_blocks("slurm")
        assert len(slurm_blocks) == 2
        assert block1 not in slurm_blocks
        assert block2 in slurm_blocks
        assert block3 in slurm_blocks
    
    def test_composition(self):
        """Test composing a template from blocks."""
        engine = TemplateCompositionEngine()
        
        # Register blocks with different priorities
        block1 = StringTemplateBlock(
            name="block1",
            content="Block 1: {{ message }}",
            priority=30
        )
        block2 = StringTemplateBlock(
            name="block2",
            content="Block 2: {{ message }}",
            priority=10
        )
        block3 = StringTemplateBlock(
            name="block3",
            content="Block 3: {{ message }}",
            priority=20
        )
        
        engine.register_block(block1)
        engine.register_block(block2)
        engine.register_block(block3)
        
        # Compose template
        context = {"message": "Hello"}
        composed = engine.compose(context, "local")
        
        # Check the result
        expected = "Block 2: Hello\n\nBlock 3: Hello\n\nBlock 1: Hello\n"
        assert composed == expected
        
    def test_composition_ensures_trailing_newline(self):
        """Test that composition always adds a trailing newline."""
        engine = TemplateCompositionEngine()
        
        # Register a block
        block = StringTemplateBlock(
            name="test_block",
            content="Test content",
            priority=10
        )
        
        engine.register_block(block)
        
        # Compose template
        composed = engine.compose({}, "local")
        
        # Check that the result ends with a newline
        assert composed.endswith('\n')
        
        # Test with a block that already ends with a newline
        engine = TemplateCompositionEngine()
        block_with_newline = StringTemplateBlock(
            name="newline_block",
            content="Test content\n",
            priority=10
        )
        
        engine.register_block(block_with_newline)
        
        # Compose template
        composed = engine.compose({}, "local")
        
        # Check that the result ends with exactly one newline
        assert composed.endswith('\n')
        assert not composed.endswith('\n\n')


class TestScriptGenerators:
    """Tests for script generators using the template system."""
    
    def test_local_script_generator(self, tmp_path):
        """Test LocalScriptGenerator."""
        # Create a temporary template file
        template_file = tmp_path / "test_template.j2"
        template_file.write_text("echo 'Custom command: {{ job.name }}'")
        
        # Create a local script generator
        generator = LocalScriptGenerator()
        
        # Generate a script
        variables = {
            "job": {
                "name": "test_job"
            },
            "workspace": {
                "logs_dir": "/logs"
            }
        }
        script = generator.generate_script(str(template_file), variables)
        
        # Check the script content
        assert "#!/bin/bash" in script
        assert "SCRIPT_DIR=$(dirname \"$SCRIPT_PATH\")" in script
        assert "echo 'Custom command: test_job'" in script
        assert "#SBATCH" not in script  # No SLURM directives
    
    def test_slurm_script_generator(self, tmp_path):
        """Test SlurmScriptGenerator."""
        # Create a temporary template file
        template_file = tmp_path / "test_template.j2"
        template_file.write_text("echo 'Custom command: {{ job.name }}'")
        
        # Create a SLURM script generator
        generator = SlurmScriptGenerator()
        
        # Generate a script
        variables = {
            "job": {
                "name": "test_job",
                "nodes": 2,
                "tasks_per_node": 4,
                "time_limit": "01:00:00",
                "queue": "test_queue",
                "account": "test_account"
            },
            "workspace": {
                "logs_dir": "/logs"
            }
        }
        script = generator.generate_script(str(template_file), variables)
        
        # Check the script content
        assert "#!/bin/bash" in script
        assert "#SBATCH -J test_job" in script
        assert "#SBATCH -N 2" in script
        assert "#SBATCH --ntasks-per-node=4" in script
        assert "#SBATCH -t 01:00:00" in script
        assert "#SBATCH -p test_queue" in script
        assert "#SBATCH -A test_account" in script
        assert "#SBATCH -o /logs/test_job.%j.out" in script
        assert "#SBATCH -e /logs/test_job.%j.err" in script
        assert "echo 'Custom command: test_job'" in script 