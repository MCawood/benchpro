"""
Tests for the new block-based template system.

This module contains tests for the new block-based template system that has replaced
the old TemplateEngine class.
"""

import os
import pytest
import tempfile
from benchpro.templates.blocks import StringTemplateBlock, FileTemplateBlock, TemplateError
from benchpro.templates.composition import TemplateCompositionEngine
from benchpro.templates.script_generators import LocalScriptGenerator, SlurmScriptGenerator
from benchpro.templates.standard_blocks import register_standard_blocks


@pytest.fixture
def test_template_env(setup_test_env):
    """Create a test template environment for testing the template system."""
    # Create a simple test template file if it doesn't exist
    template_content = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --time={{ job.time_limit }}

echo "Running {{ job.name }}"
{{ application.executable }} {{ application.arguments }}
"""
    
    # Add the test template to the application directory
    test_template_path = os.path.join(setup_test_env["inputs_app_dir"], "test_template.j2")
    with open(test_template_path, 'w') as f:
        f.write(template_content)
        
    return setup_test_env


def test_render_template(test_template_env):
    """Test rendering a template with the new block-based system."""
    # Create a template block
    template_path = os.path.join(test_template_env["inputs_app_dir"], "test_template.j2")
    block = FileTemplateBlock(
        name="test_block",
        file_path=template_path,
        priority=100
    )
    
    # Create a composition engine
    engine = TemplateCompositionEngine()
    engine.register_block(block)
    
    # Define variables
    variables = {
        "job": {
            "name": "test_job",
            "time_limit": "01:00:00"
        },
        "application": {
            "executable": "/path/to/app",
            "arguments": "-n 10"
        }
    }
    
    # Render the template
    rendered = engine.compose(variables, "local")
    
    # Verify the result
    assert "#!/bin/bash" in rendered
    assert "#SBATCH --job-name=test_job" in rendered
    assert "#SBATCH --time=01:00:00" in rendered
    assert "echo \"Running test_job\"" in rendered
    assert "/path/to/app -n 10" in rendered


def test_render_example_template(test_template_env):
    """Test rendering a template with the LocalScriptGenerator."""
    # Create a script generator
    generator = LocalScriptGenerator()
    
    # Define variables
    variables = {
        "job": {
            "name": "example_job",
            "time_limit": "02:00:00"
        },
        "application": {
            "executable": "/path/to/example",
            "arguments": "--verbose"
        }
    }
    
    # Render the template
    template_path = os.path.join(test_template_env["inputs_app_dir"], "test_template.j2")
    rendered = generator.generate_script(template_path, variables)
    
    # Verify the result contains both the template content and standard blocks
    assert "#!/bin/bash" in rendered
    assert "#SBATCH --job-name=example_job" in rendered
    assert "#SBATCH --time=02:00:00" in rendered
    assert "echo \"Running example_job\"" in rendered
    assert "/path/to/example --verbose" in rendered
    assert "SCRIPT_PATH=$0" in rendered  # Workspace directory handling
    assert "echo \"Job started at:" in rendered  # Start timestamp


def test_write_rendered_template(test_template_env):
    """Test writing a rendered template to a file."""
    # Create a script generator
    generator = SlurmScriptGenerator()
    
    # Define variables
    variables = {
        "job": {
            "name": "write_test_job",
            "time_limit": "03:00:00",
            "nodes": 2,
            "tasks_per_node": 16,
            "queue": "batch"
        },
        "application": {
            "executable": "/path/to/mpi_app",
            "arguments": "-np 32"
        },
        "workspace": {
            "logs_dir": "/path/to/logs"
        }
    }
    
    # Create a temporary file for output
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        output_path = temp_file.name
    
    try:
        # Render the template
        template_path = os.path.join(test_template_env["inputs_app_dir"], "test_template.j2")
        rendered = generator.generate_script(template_path, variables)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(rendered)
        
        # Read back and verify
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Verify the content
        assert "#!/bin/bash" in content
        assert "#SBATCH -J write_test_job" in content
        assert "#SBATCH -N 2" in content
        assert "#SBATCH --ntasks-per-node=16" in content
        assert "#SBATCH -t 03:00:00" in content
        assert "#SBATCH -p batch" in content
        assert "echo \"Running write_test_job\"" in content
        assert "/path/to/mpi_app -np 32" in content
    finally:
        # Clean up
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_template_not_found():
    """Test handling of template not found errors."""
    # Create a script generator
    generator = LocalScriptGenerator()
    
    # Try to render a non-existent template
    with pytest.raises(TemplateError):
        generator.generate_script("non_existent_template.j2", {}) 