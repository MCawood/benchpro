"""
Tests for the RegistryManager with focus on environment handling.

This module contains tests to verify that the RegistryManager correctly handles
environment information in application data.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, call

from benchpro.registry.registry_manager import RegistryManager
from benchpro.workspace.module_manager import ModuleError


class TestRegistryManagerEnvironment(unittest.TestCase):
    """Tests for the RegistryManager class environment handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Patch the user directory manager
        self.user_dir_patcher = patch('benchpro.registry.registry_manager.get_user_dir_manager')
        self.mock_user_dir = self.user_dir_patcher.start()
        self.mock_user_dir.return_value.get_path.return_value = 'test_registry.yaml'
        
        # Patch file operations
        self.file_open_patcher = patch('builtins.open', create=True)
        self.mock_open = self.file_open_patcher.start()
        self.mock_file = MagicMock()
        self.mock_open.return_value.__enter__.return_value = self.mock_file
        
        # Patch file existence check
        self.path_exists_patcher = patch('os.path.exists')
        self.mock_exists = self.path_exists_patcher.start()
        self.mock_exists.return_value = True
        
        # Patch fcntl for file locking
        self.fcntl_patcher = patch('fcntl.flock')
        self.mock_flock = self.fcntl_patcher.start()
        
        # Patch yaml for loading/dumping
        self.yaml_patcher = patch('yaml.safe_load')
        self.mock_yaml_load = self.yaml_patcher.start()
        self.mock_yaml_load.return_value = {
            "version": "1.0",
            "last_updated": "",
            "applications": []
        }
        
        self.yaml_dump_patcher = patch('yaml.dump')
        self.mock_yaml_dump = self.yaml_dump_patcher.start()
        
        # Create test app data with environment
        self.app_data_with_env = {
            "name": "test_app",
            "version": "1.2.3",
            "workspace_dir": "/test/workspace",
            "binary_path": "/test/workspace/bin/test_app",
            "environment": {
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ],
                "variables": {
                    "PATH": "$PATH:/custom/path"
                }
            }
        }
        
        # Create test app data without environment
        self.app_data_without_env = {
            "name": "test_app_no_env",
            "version": "1.0.0",
            "workspace_dir": "/test/workspace",
            "binary_path": "/test/workspace/bin/test_app_no_env"
        }
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.user_dir_patcher.stop()
        self.file_open_patcher.stop()
        self.path_exists_patcher.stop()
        self.fcntl_patcher.stop()
        self.yaml_patcher.stop()
        self.yaml_dump_patcher.stop()
        if hasattr(self, 'module_manager_patcher'):
            self.module_manager_patcher.stop()
    
    def test_register_application_with_environment(self):
        """Test registering an application with environment information."""
        # Patch the ModuleManager constructor and create_module_file method
        self.module_manager_patcher = patch('benchpro.registry.registry_manager.ModuleManager')
        self.mock_module_manager_class = self.module_manager_patcher.start()
        self.mock_module_manager = MagicMock()
        self.mock_module_manager_class.return_value = self.mock_module_manager
        self.mock_module_manager.create_module_file.return_value = "/path/to/module/file"
        
        registry_manager = RegistryManager()
        
        # Mock the _save_registry method
        registry_manager._save_registry = MagicMock(return_value=True)
        # Mock the _generate_random_string method
        registry_manager._generate_random_string = MagicMock(return_value="abc123")
        
        # Register the application
        app_id = registry_manager.register_application(self.app_data_with_env)
        
        # Check that module manager was called
        self.mock_module_manager.create_module_file.assert_called_once()
        
        # Verify the correct data was passed to create_module_file
        # Get the first positional argument (app_data_or_name)
        call_args, call_kwargs = self.mock_module_manager.create_module_file.call_args
        if call_args:
            # If using positional arguments
            passed_data = call_args[0]
        else:
            # If using keyword arguments
            passed_data = call_kwargs.get('app_data_or_name')
        
        # Validate the passed data
        self.assertIsNotNone(passed_data)
        self.assertIsInstance(passed_data, dict)
        self.assertEqual(passed_data["name"], "test_app")
        self.assertEqual(passed_data["version"], "1.2.3")
        self.assertIn("environment", passed_data)
        
        # Check the app_id is generated correctly
        self.assertEqual(app_id, "test_app_123_abc123")
        
        # Check the module file path is stored in the registry
        self.assertIn("module_file", registry_manager.registry["applications"][0])
        self.assertEqual(registry_manager.registry["applications"][0]["module_file"], "/path/to/module/file")
    
    def test_register_application_without_environment(self):
        """Test registering an application without environment information."""
        # Patch the ModuleManager constructor and create_module_file method
        self.module_manager_patcher = patch('benchpro.registry.registry_manager.ModuleManager')
        self.mock_module_manager_class = self.module_manager_patcher.start()
        self.mock_module_manager = MagicMock()
        self.mock_module_manager_class.return_value = self.mock_module_manager
        self.mock_module_manager.create_module_file.return_value = "/path/to/module/file"
        
        registry_manager = RegistryManager()
        
        # Mock the _save_registry method
        registry_manager._save_registry = MagicMock(return_value=True)
        # Mock the _generate_random_string method
        registry_manager._generate_random_string = MagicMock(return_value="abc123")
        
        # Register the application
        app_id = registry_manager.register_application(self.app_data_without_env)
        
        # Check that module manager was called
        self.mock_module_manager.create_module_file.assert_called_once()
        
        # Verify the correct data was passed to create_module_file
        # Get the first positional argument (app_data_or_name)
        call_args, call_kwargs = self.mock_module_manager.create_module_file.call_args
        if call_args:
            # If using positional arguments
            passed_data = call_args[0]
        else:
            # If using keyword arguments
            passed_data = call_kwargs.get('app_data_or_name')
        
        # Validate the passed data
        self.assertIsNotNone(passed_data)
        self.assertIsInstance(passed_data, dict)
        self.assertEqual(passed_data["name"], "test_app_no_env")
        self.assertEqual(passed_data["version"], "1.0.0")
        
        # The current implementation adds an environment section, so we should check it exists
        self.assertIn("environment", passed_data)
        self.assertIn("modules", passed_data["environment"])
        self.assertEqual(passed_data["environment"]["modules"], [])
        
        # Check the app_id is generated correctly
        self.assertEqual(app_id, "test_app_no_env_100_abc123")
        
        # Check the module file path is stored in the registry
        self.assertIn("module_file", registry_manager.registry["applications"][0])
        self.assertEqual(registry_manager.registry["applications"][0]["module_file"], "/path/to/module/file")
    
    def test_register_application_missing_required_fields(self):
        """Test that registering an application with missing required fields fails."""
        registry_manager = RegistryManager()
        
        # Create app data with missing required fields
        incomplete_app_data = {
            "name": "incomplete_app"
            # Missing workspace_dir and binary_path
        }
        
        # Register the application
        app_id = registry_manager.register_application(incomplete_app_data)
        
        # Check that registration failed
        self.assertEqual(app_id, "")
    
    def test_register_application_with_module_error(self):
        """Test that app registration continues even if module file creation fails."""
        # Patch the ModuleManager constructor and create_module_file method
        self.module_manager_patcher = patch('benchpro.registry.registry_manager.ModuleManager')
        self.mock_module_manager_class = self.module_manager_patcher.start()
        self.mock_module_manager = MagicMock()
        self.mock_module_manager_class.return_value = self.mock_module_manager
        self.mock_module_manager.create_module_file.side_effect = ModuleError("Test error")
        
        registry_manager = RegistryManager()
        
        # Mock the _save_registry method
        registry_manager._save_registry = MagicMock(return_value=True)
        # Mock the _generate_random_string method
        registry_manager._generate_random_string = MagicMock(return_value="abc123")
        
        # Register the application
        app_id = registry_manager.register_application(self.app_data_with_env)
        
        # Check that module manager was called
        self.mock_module_manager.create_module_file.assert_called_once()
        
        # Check that registration succeeded even with module error
        self.assertEqual(app_id, "test_app_123_abc123")
        
        # Verify module_file is not in the registered app due to error
        self.assertNotIn("module_file", registry_manager.registry["applications"][0])


if __name__ == '__main__':
    unittest.main() 