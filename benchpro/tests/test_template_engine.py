"""
Tests for the TemplateEngine class.
"""

import os
import pytest
import tempfile
from benchpro.templates.template_engine import TemplateEngine


@pytest.fixture
def temp_template_dir():
    """Create a temporary directory with test template files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple template file
        template_content = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --time={{ scheduler.time_limit }}

echo "Running {{ job.name }}"
{{ application.executable }} {{ application.arguments }}
"""
        with open(os.path.join(temp_dir, "test_template.j2"), 'w') as f:
            f.write(template_content)
            
        yield temp_dir


def test_render_template(temp_template_dir):
    """Test rendering a template with configuration data."""
    template_engine = TemplateEngine(temp_template_dir)
    
    config = {
        "job": {
            "name": "test_job"
        },
        "scheduler": {
            "time_limit": "01:00:00"
        },
        "application": {
            "executable": "/bin/echo",
            "arguments": "Hello, World!"
        }
    }
    
    rendered = template_engine.render_template("test_template.j2", config)
    
    # Check that the template was rendered correctly
    assert "#!/bin/bash" in rendered
    assert "#SBATCH --job-name=test_job" in rendered
    assert "#SBATCH --time=01:00:00" in rendered
    assert 'echo "Running test_job"' in rendered
    assert "/bin/echo Hello, World!" in rendered


def test_write_rendered_template(temp_template_dir):
    """Test rendering a template and writing it to a file."""
    template_engine = TemplateEngine(temp_template_dir)
    
    config = {
        "job": {
            "name": "test_job"
        },
        "scheduler": {
            "time_limit": "01:00:00"
        },
        "application": {
            "executable": "/bin/echo",
            "arguments": "Hello, World!"
        }
    }
    
    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        output_path = temp_file.name
    
    try:
        # Render and write the template
        template_engine.write_rendered_template("test_template.j2", config, output_path)
        
        # Check that the file was written correctly
        with open(output_path, 'r') as f:
            content = f.read()
            
        assert "#!/bin/bash" in content
        assert "#SBATCH --job-name=test_job" in content
        assert "#SBATCH --time=01:00:00" in content
        assert 'echo "Running test_job"' in content
        assert "/bin/echo Hello, World!" in content
        
    finally:
        # Clean up the temporary file
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_template_not_found(temp_template_dir):
    """Test that an exception is raised when a template is not found."""
    template_engine = TemplateEngine(temp_template_dir)
    
    config = {
        "job": {
            "name": "test_job"
        }
    }
    
    # Attempt to render a non-existent template
    with pytest.raises(Exception):
        template_engine.render_template("non_existent_template.j2", config) 