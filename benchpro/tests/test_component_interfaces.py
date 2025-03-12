"""
Tests for component interfaces.

This module contains tests for the component interfaces used in the
composition-based task architecture.
"""

import unittest
from typing import Dict, Any, List, Tuple, Optional

from benchpro.executor.components.interfaces import (
    ConfigComponent,
    ValidationComponent,
    ScriptGenerationComponent,
    ExecutionComponent,
    ComponentError,
    ConfigError,
    ValidationError,
    TemplateError,
    ExecutionError,
    StatusCheckError,
    CancellationError
)


class TestConfigComponent(unittest.TestCase):
    """Tests for the ConfigComponent interface."""
    
    def test_interface(self):
        """Test that the ConfigComponent interface has the expected methods."""
        self.assertTrue(hasattr(ConfigComponent, 'load_config'))
        self.assertTrue(hasattr(ConfigComponent, 'get_config'))
        self.assertTrue(hasattr(ConfigComponent, 'merge_config'))


class TestValidationComponent(unittest.TestCase):
    """Tests for the ValidationComponent interface."""
    
    def test_interface(self):
        """Test that the ValidationComponent interface has the expected methods."""
        self.assertTrue(hasattr(ValidationComponent, 'validate'))
        self.assertTrue(hasattr(ValidationComponent, 'get_required_fields'))


class TestScriptGenerationComponent(unittest.TestCase):
    """Tests for the ScriptGenerationComponent interface."""
    
    def test_interface(self):
        """Test that the ScriptGenerationComponent interface has the expected methods."""
        self.assertTrue(hasattr(ScriptGenerationComponent, 'generate_script'))
        self.assertTrue(hasattr(ScriptGenerationComponent, 'prepare_variables'))


class TestExecutionComponent(unittest.TestCase):
    """Tests for the ExecutionComponent interface."""
    
    def test_interface(self):
        """Test that the ExecutionComponent interface has the expected methods."""
        self.assertTrue(hasattr(ExecutionComponent, 'execute'))
        self.assertTrue(hasattr(ExecutionComponent, 'get_status'))
        self.assertTrue(hasattr(ExecutionComponent, 'cancel_job'))


class TestComponentExceptions(unittest.TestCase):
    """Tests for the component exception classes."""
    
    def test_exception_hierarchy(self):
        """Test that the exception classes have the expected hierarchy."""
        self.assertTrue(issubclass(ConfigError, ComponentError))
        self.assertTrue(issubclass(ValidationError, ComponentError))
        self.assertTrue(issubclass(TemplateError, ComponentError))
        self.assertTrue(issubclass(ExecutionError, ComponentError))
        self.assertTrue(issubclass(StatusCheckError, ComponentError))
        self.assertTrue(issubclass(CancellationError, ComponentError))


if __name__ == '__main__':
    unittest.main() 