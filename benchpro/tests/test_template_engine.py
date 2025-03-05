"""
Tests for the TemplateEngine class.
"""

import os
import pytest
import tempfile
from benchpro.templates.template_engine import TemplateEngine


@pytest.fixture
def test_template_env(setup_test_env):
    """Create a test template environment for testing the TemplateEngine."""
    # Create a simple test template file if it doesn't exist
    template_content = """#!/bin/bash
#SBATCH --job-name={{ job.name }}
#SBATCH --time={{ scheduler.time_limit }}

echo "Running {{ job.name }}"
{{ application.executable }} {{ application.arguments }}
"""
    
    # Add the test template to the application directory
    test_template_path = os.path.join(setup_test_env["inputs_app_dir"], "test_template.j2")
    with open(test_template_path, 'w') as f:
        f.write(template_content)
        
    return setup_test_env


def test_render_template(test_template_env):
    """Test rendering a template with configuration data."""
    # Initialize template engine with inputs directory
    template_engine = TemplateEngine(test_template_env["inputs_app_dir"])
    
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


def test_render_example_template(test_template_env):
    """Test rendering an example template that comes from the examples directory."""
    # Initialize template engine with inputs directory
    template_engine = TemplateEngine(test_template_env["inputs_app_dir"])
    
    # Ensure hello_world.j2 exists from the examples directory
    assert os.path.exists(os.path.join(test_template_env["inputs_app_dir"], "hello_world.j2")), \
        "hello_world.j2 template should be copied from examples"
    
    config = {
        "name": "test_app",
        "version": "1.0",
        "build": {
            "compiler": "gcc",
            "flags": "-O2",
            "source": "hello_world.c",
            "output": "test_app"
        },
        "workspace": {
            "source_dir": "/tmp/source",
            "output_dir": "/tmp/output"
        },
        "job": {
            "name": "test_app_build"
        }
    }
    
    rendered = template_engine.render_template("hello_world.j2", config)
    
    # Check that the template was rendered correctly with some expected content
    assert "gcc" in rendered
    assert "hello_world.c" in rendered


def test_write_rendered_template(test_template_env):
    """Test rendering a template and writing it to a file."""
    # Initialize template engine with inputs directory
    template_engine = TemplateEngine(test_template_env["inputs_app_dir"])
    
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
        
        # Read the file and check its contents
        with open(output_path, 'r') as f:
            content = f.read()
            
        assert "#!/bin/bash" in content
        assert "#SBATCH --job-name=test_job" in content
        assert "#SBATCH --time=01:00:00" in content
        assert 'echo "Running test_job"' in content
        assert "/bin/echo Hello, World!" in content
    finally:
        # Cleanup
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_template_not_found(test_template_env):
    """Test handling of template not found errors."""
    # Initialize template engine with inputs directory
    template_engine = TemplateEngine(test_template_env["inputs_app_dir"])
    
    # Import the correct exception type
    from jinja2.exceptions import TemplateNotFound
    
    # Try to render a non-existent template
    with pytest.raises(TemplateNotFound):
        template_engine.render_template("non_existent_template.j2", {}) 