"""
Tests for the ApplicationData class.

This module contains tests for the ApplicationData class and related structures.
"""

import unittest
from typing import Dict, Any

from benchpro.registry.application_data import ApplicationData, ModuleConfig, EnvironmentConfig


class TestApplicationData(unittest.TestCase):
    """Tests for the ApplicationData class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a sample app data with environment
        self.app_data_dict = {
            "name": "test_app",
            "version": "1.2.3",
            "workspace_dir": "/test/workspace",
            "binary_path": "/test/workspace/bin/test_app",
            "build_parameters": {
                "source": "test.c",
                "output": "test_binary"
            },
            "environment": {
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ],
                "module_paths": ["/test/modules"],
                "variables": {
                    "PATH": "$PATH:/custom/path"
                }
            },
            "metadata": {
                "author": "Test User",
                "date": "2023-01-01"
            }
        }
        
        # Create app data without environment
        self.app_data_no_env_dict = {
            "name": "test_app_no_env",
            "version": "1.0.0",
            "workspace_dir": "/test/workspace",
            "binary_path": "/test/workspace/bin/test_app_no_env",
            "build_parameters": {
                "source": "test_no_env.c",
                "output": "test_binary_no_env"
            }
        }
        
    def test_from_dict_with_environment(self):
        """Test creating ApplicationData from a dictionary with environment."""
        app_data = ApplicationData.from_dict(self.app_data_dict)
        
        # Check basic fields
        self.assertEqual(app_data.name, "test_app")
        self.assertEqual(app_data.version, "1.2.3")
        self.assertEqual(app_data.workspace_dir, "/test/workspace")
        self.assertEqual(app_data.binary_path, "/test/workspace/bin/test_app")
        
        # Check build parameters
        self.assertEqual(app_data.build_parameters["source"], "test.c")
        self.assertEqual(app_data.build_parameters["output"], "test_binary")
        
        # Check environment
        self.assertIsNotNone(app_data.environment)
        self.assertEqual(len(app_data.environment.modules), 2)
        self.assertEqual(app_data.environment.modules[0].name, "gcc")
        self.assertEqual(app_data.environment.modules[0].version, "10.2.0")
        self.assertEqual(app_data.environment.modules[1].name, "openmpi")
        self.assertEqual(app_data.environment.module_paths, ["/test/modules"])
        self.assertEqual(app_data.environment.variables["PATH"], "$PATH:/custom/path")
        
        # Check metadata
        self.assertEqual(app_data.metadata["author"], "Test User")
        
    def test_from_dict_without_environment(self):
        """Test creating ApplicationData from a dictionary without environment."""
        app_data = ApplicationData.from_dict(self.app_data_no_env_dict)
        
        # Check basic fields
        self.assertEqual(app_data.name, "test_app_no_env")
        self.assertEqual(app_data.version, "1.0.0")
        
        # Check environment is None
        self.assertIsNone(app_data.environment)
        
    def test_to_dict(self):
        """Test converting ApplicationData to a dictionary."""
        # Create ApplicationData instance
        app_data = ApplicationData.from_dict(self.app_data_dict)
        
        # Convert back to dictionary
        result_dict = app_data.to_dict()
        
        # Check basic fields
        self.assertEqual(result_dict["name"], "test_app")
        self.assertEqual(result_dict["version"], "1.2.3")
        
        # Check environment
        self.assertIn("environment", result_dict)
        self.assertIn("modules", result_dict["environment"])
        self.assertEqual(len(result_dict["environment"]["modules"]), 2)
        self.assertEqual(result_dict["environment"]["modules"][0]["name"], "gcc")
        self.assertEqual(result_dict["environment"]["modules"][0]["version"], "10.2.0")
        
    def test_validate(self):
        """Test validation of ApplicationData."""
        # Valid application data
        app_data = ApplicationData.from_dict(self.app_data_dict)
        errors = app_data.validate()
        self.assertEqual(len(errors), 0)
        
        # Invalid application data
        invalid_app_data = ApplicationData(
            name="",  # Invalid: empty name
            version="1.0",
            workspace_dir="/test/workspace",
            binary_path="/test/binary"
        )
        errors = invalid_app_data.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("Application name is required", errors)
        
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Create data with missing workspace_dir
        missing_data = {
            "name": "test_app",
            "binary_path": "/test/binary"
        }
        
        # This should raise a ValueError
        with self.assertRaises(ValueError):
            ApplicationData.from_dict(missing_data)


if __name__ == '__main__':
    unittest.main() 