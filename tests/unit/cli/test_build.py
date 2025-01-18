"""Tests for build CLI commands."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from click.shell_completion import CompletionItem

from benchpro.cli.build import get_template_names, parse_variables
from benchpro.core.domain.templates.loader import TemplateLoader
from benchpro.core.domain.templates.config import TemplateConfig

@pytest.fixture
def mock_template_loader():
    """Create a mock template loader with test templates."""
    loader = Mock(spec=TemplateLoader)
    
    # Mock list_applications to return test templates
    loader.list_applications.return_value = [
        "hello_world",
        "matrix_mult",
        "mpi_test"
    ]
    
    # Mock load_config to return test configs
    configs = {
        "hello_world": TemplateConfig({
            "name": "hello_world",
            "version": "1.0.0",
            "type": "application",
            "description": "A simple Hello World application",
            "build": {
                "language": "c",
                "compiler": "gcc",
                "binary": {
                    "directory": "bin",
                    "executable": "hello_world"
                }
            },
            "source": {
                "files": ["hello_world.c"]
            }
        }),
        "matrix_mult": TemplateConfig({
            "name": "matrix_mult",
            "version": "1.0.0",
            "type": "application",
            "description": "Matrix multiplication benchmark",
            "build": {
                "language": "c",
                "compiler": "gcc",
                "binary": {
                    "directory": "bin",
                    "executable": "matrix_mult"
                }
            },
            "source": {
                "files": ["matrix_mult.c"]
            }
        }),
        "mpi_test": TemplateConfig({
            "name": "mpi_test",
            "version": "1.0.0",
            "type": "application",
            "description": "MPI test application",
            "build": {
                "language": "c",
                "compiler": "gcc",
                "binary": {
                    "directory": "bin",
                    "executable": "mpi_test"
                }
            },
            "source": {
                "files": ["mpi_test.c"]
            }
        })
    }
    loader.load_config = lambda name: configs[name]
    return loader

def test_get_template_names_no_filter(mock_template_loader):
    """Test template name completion with no filter."""
    with patch('benchpro.cli.build.TemplateLoader', return_value=mock_template_loader):
        ctx = Mock()
        args = []
        incomplete = ""
        
        completions = get_template_names(ctx, args, incomplete)
        
        assert len(completions) == 3
        assert all(isinstance(item, CompletionItem) for item in completions)
        assert {item.value for item in completions} == {"hello_world", "matrix_mult", "mpi_test"}
        
        # Check descriptions are included
        hello_world = next(item for item in completions if item.value == "hello_world")
        assert hello_world.help == "A simple Hello World application"

def test_get_template_names_with_filter(mock_template_loader):
    """Test template name completion with filter."""
    with patch('benchpro.cli.build.TemplateLoader', return_value=mock_template_loader):
        ctx = Mock()
        args = []
        incomplete = "mat"
        
        completions = get_template_names(ctx, args, incomplete)
        
        assert len(completions) == 1
        assert completions[0].value == "matrix_mult"
        assert completions[0].help == "Matrix multiplication benchmark"

def test_get_template_names_no_match(mock_template_loader):
    """Test template name completion with no matches."""
    with patch.multiple('benchpro.cli.build', TemplateLoader=Mock(return_value=mock_template_loader)):
        ctx = Mock()
        args = []
        incomplete = "nonexistent"
        
        completions = get_template_names(ctx, args, incomplete)
        assert len(completions) == 0

def test_get_template_names_error_handling(mock_template_loader):
    """Test template name completion with template loading error."""
    with patch('benchpro.cli.build.TemplateLoader', return_value=mock_template_loader):
        # Make load_config raise an exception for one template
        def mock_load_config(name):
            if name == "matrix_mult":
                raise Exception("Failed to load config")
            return TemplateConfig({
                "name": name,
                "version": "1.0.0",
                "type": "application",
                "description": f"{name} description",
                "build": {
                    "language": "c",
                    "compiler": "gcc",
                    "binary": {
                        "directory": "bin",
                        "executable": name
                    }
                }
            })
            
        mock_template_loader.load_config = mock_load_config
        
        ctx = Mock()
        args = []
        incomplete = ""
        
        completions = get_template_names(ctx, args, incomplete)
        
        # Should still return all templates, with error message for failed one
        assert len(completions) == 3
        matrix_mult = next(item for item in completions if item.value == "matrix_mult")
        assert matrix_mult.help == "[Error loading configuration]"

def test_parse_variables():
    """Test variable parsing from command line arguments."""
    variables = parse_variables(["FOO=bar", "DEBUG=1"])
    assert variables == {"FOO": "bar", "DEBUG": "1"}

def test_parse_variables_invalid():
    """Test variable parsing with invalid format."""
    with pytest.raises(Exception) as exc:
        parse_variables(["INVALID"])
    assert "Invalid variable format" in str(exc.value) 