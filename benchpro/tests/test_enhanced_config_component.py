"""
Tests for the enhanced ConfigComponent.

This module contains tests for the enhanced ConfigComponent with improved
configuration section access methods and validation.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from benchpro.executor.components.config import YamlConfigComponent
from benchpro.executor.components.interfaces import ConfigError


class TestEnhancedConfigComponent(unittest.TestCase):
    """Tests for the enhanced ConfigComponent."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a sample config with environment and module sections
        self.sample_config = {
            "name": "test_app",
            "version": "1.0",
            "environment": {
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ],
                "variables": {
                    "PATH": "$PATH:/custom/path"
                }
            },
            "build": {
                "source": "test.c",
                "output": "test_binary"
            }
        }
        
        # Create a temporary YAML file with the sample config
        _, self.config_path = tempfile.mkstemp(suffix=".yaml")
        with open(self.config_path, 'w') as f:
            import yaml
            yaml.dump(self.sample_config, f)
            
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary YAML file
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def test_get_environment_section(self):
        """Test getting the environment section from config."""
        component = YamlConfigComponent(self.config_path)
        
        # Test with a config that has an environment section
        env_section = component.get_environment_section()
        self.assertIsNotNone(env_section)
        self.assertIn("modules", env_section)
        self.assertEqual(len(env_section["modules"]), 2)
        self.assertIn("variables", env_section)
        
        # Test with missing environment section
        with patch.dict(component.config, {}, clear=True):
            component.config.update({"name": "test_app", "version": "1.0"})  # No environment section
            env_section = component.get_environment_section()
            self.assertIsNone(env_section)
    
    def test_get_module_dependencies(self):
        """Test getting the module dependencies from config."""
        component = YamlConfigComponent(self.config_path)
        
        # Test with a config that has module dependencies
        modules = component.get_module_dependencies()
        self.assertIsNotNone(modules)
        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0]["name"], "gcc")
        self.assertEqual(modules[0]["version"], "10.2.0")
        
        # Test with missing modules
        with patch.dict(component.config, {"environment": {}}, clear=True):
            modules = component.get_module_dependencies()
            self.assertIsNone(modules)
            
        # Test with missing environment section
        with patch.dict(component.config, {}, clear=True):
            component.config.update({"name": "test_app", "version": "1.0"})  # No environment section
            modules = component.get_module_dependencies()
            self.assertIsNone(modules)
    
    def test_validate_required_sections(self):
        """Test validation of required configuration sections."""
        component = YamlConfigComponent(self.config_path)
        
        # Test with all required sections present
        required_sections = ["name", "version", "build"]
        is_valid = component.validate_required_sections(required_sections)
        self.assertTrue(is_valid)
        
        # Test with missing sections
        required_sections = ["name", "version", "missing_section"]
        with self.assertRaises(ConfigError):
            component.validate_required_sections(required_sections)
            
        # Test with optional sections
        required_sections = ["name", "version"]
        optional_sections = ["build", "environment"]
        is_valid = component.validate_required_sections(required_sections, optional_sections)
        self.assertTrue(is_valid)
        
        # Log warning for missing optional sections
        optional_sections = ["build", "missing_optional"]
        with self.assertLogs(level='WARNING'):
            is_valid = component.validate_required_sections(required_sections, optional_sections)
            self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main() 