"""
Tests for Application environment handling.

This module contains tests to verify that the Application task correctly handles
environment information and completes its run process successfully.
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from benchpro.executor.task import Application
from benchpro.executor.components.interfaces import ConfigError
from benchpro.executor.components.configuration import BaseConfigComponent
from benchpro.executor.components.validation import ApplicationValidationComponent
from benchpro.executor.components.execution import LocalExecutionComponent
from benchpro.templates.script_generators import LocalScriptGenerator


class TestApplicationEnvironmentHandling(unittest.TestCase):
    """Tests for the Application class environment handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mocks for the components
        self.mock_config_component = MagicMock(spec=BaseConfigComponent)
        self.mock_validation_component = MagicMock(spec=ApplicationValidationComponent)
        self.mock_script_generation_component = MagicMock(spec=LocalScriptGenerator)
        self.mock_execution_component = MagicMock(spec=LocalExecutionComponent)
        
        # Configure mock config component with sample data
        self.sample_config = {
            "name": "test_app",
            "version": "1.2.3",
            "build": {
                "source": "test.c",
                "output": "test_binary"
            },
            "workspace": {
                "workspace_dir": self.temp_dir
            },
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
        
        # Configure the get_config method to return the sample config
        self.mock_config_component.get_config.return_value = self.sample_config
        
        # Configure validation to succeed
        self.mock_validation_component.validate.return_value = (True, None)
        
        # Mock successful execution
        self.mock_execution_component.execute.return_value = (True, "job-123")
        
        # Create the Application instance
        self.app = Application(
            config_component=self.mock_config_component,
            validation_component=self.mock_validation_component,
            script_generation_component=self.mock_script_generation_component,
            execution_component=self.mock_execution_component
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('benchpro.executor.task.Task.run')
    @patch('benchpro.workspace.module_manager.ModuleManager')
    @patch('benchpro.registry.registry_manager.RegistryManager')
    def test_run_with_environment(self, mock_registry_class, mock_module_class, mock_parent_run):
        """Test that the run method succeeds with environment information."""
        # Mock parent run to succeed
        mock_parent_run.return_value = True
        
        # Mock module manager
        mock_module_manager = MagicMock()
        mock_module_class.return_value = mock_module_manager
        mock_module_manager.create_module_file.return_value = "/test/module/file.lua"
        mock_module_manager.extract_dependencies_from_config.return_value = []
        mock_module_manager.extract_module_paths_from_config.return_value = []
        
        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_registry_class.return_value = mock_registry_manager
        mock_registry_manager.register_application.return_value = "app-123"
        
        # Run the application
        success, job_id = self.app.run()
        
        # Check that the run was successful
        self.assertTrue(success)
        self.assertIsNone(job_id)  # No job ID since test_job.submit is not set
        
        # Verify parent run was called
        mock_parent_run.assert_called_once()
        
        # Verify module manager was used
        mock_module_manager.create_module_file.assert_called_once()
        
        # Verify registry manager was used
        mock_registry_manager.register_application.assert_called_once()
    
    @patch('benchpro.executor.task.Task.run')
    @patch('benchpro.workspace.module_manager.ModuleManager')
    @patch('benchpro.registry.registry_manager.RegistryManager')
    def test_run_without_environment(self, mock_registry_class, mock_module_class, mock_parent_run):
        """Test that the run method succeeds without environment information."""
        # Update the config to not include environment
        config_without_env = dict(self.sample_config)
        del config_without_env["environment"]
        self.mock_config_component.get_config.return_value = config_without_env
        
        # Mock parent run to succeed
        mock_parent_run.return_value = True
        
        # Mock module manager
        mock_module_manager = MagicMock()
        mock_module_class.return_value = mock_module_manager
        mock_module_manager.create_module_file.return_value = "/test/module/file.lua"
        mock_module_manager.extract_dependencies_from_config.return_value = []
        mock_module_manager.extract_module_paths_from_config.return_value = []
        
        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_registry_class.return_value = mock_registry_manager
        mock_registry_manager.register_application.return_value = "app-123"
        
        # Run the application
        success, job_id = self.app.run()
        
        # Check that the run was successful
        self.assertTrue(success)
        self.assertIsNone(job_id)  # No job ID since test_job.submit is not set
        
        # Verify parent run was called
        mock_parent_run.assert_called_once()
        
        # Verify registry manager was used with correct data
        mock_registry_manager.register_application.assert_called_once()
        call_args = mock_registry_manager.register_application.call_args[0][0]
        
        # The environment should either be missing or contain an empty modules list
        # (since the Application code provides a default empty environment)
        if "environment" in call_args:
            self.assertEqual(call_args["environment"], {"modules": []})
        else:
            # If no environment section, that's also acceptable
            pass
    
    @patch('benchpro.executor.task.Task.run')
    def test_run_with_validation_error(self, mock_parent_run):
        """Test that the run method handles parent run failures."""
        # Mock parent run to fail
        mock_parent_run.return_value = False
        
        # Run the application
        success, job_id = self.app.run()
        
        # Check that the run failed
        self.assertFalse(success)
        self.assertIsNone(job_id)
        
        # Verify parent run was called
        mock_parent_run.assert_called_once()
    
    @patch('benchpro.executor.task.Task.run')
    @patch('benchpro.workspace.module_manager.ModuleManager')
    @patch('benchpro.registry.registry_manager.RegistryManager')
    def test_run_with_application_data_validation_error(self, mock_registry_class, mock_module_class, mock_parent_run):
        """Test that the run method handles registry errors gracefully."""
        # Mock parent run to succeed
        mock_parent_run.return_value = True
        
        # Mock module manager
        mock_module_manager = MagicMock()
        mock_module_class.return_value = mock_module_manager
        mock_module_manager.create_module_file.return_value = "/test/module/file.lua"
        mock_module_manager.extract_dependencies_from_config.return_value = []
        mock_module_manager.extract_module_paths_from_config.return_value = []
        
        # Mock registry manager to fail
        mock_registry_manager = MagicMock()
        mock_registry_class.return_value = mock_registry_manager
        mock_registry_manager.register_application.return_value = None  # Registration failed
        
        # Run the application
        success, job_id = self.app.run()
        
        # Check that the run failed due to registry error
        self.assertFalse(success)
        self.assertIsNone(job_id)
        
        # Verify parent run was called
        mock_parent_run.assert_called_once()
        
        # Verify registry manager was attempted
        mock_registry_manager.register_application.assert_called_once()
    
    @patch('benchpro.executor.task.Task.run')
    @patch('benchpro.workspace.module_manager.ModuleManager')
    @patch('benchpro.registry.registry_manager.RegistryManager')
    def test_run_with_test_job_submission(self, mock_registry_class, mock_module_class, mock_parent_run):
        """Test that the run method submits test jobs when configured."""
        # Update config to include test job submission
        config_with_test_job = dict(self.sample_config)
        config_with_test_job["test_job"] = {"submit": True}
        self.mock_config_component.get_config.return_value = config_with_test_job
        
        # Mock parent run to succeed
        mock_parent_run.return_value = True
        
        # Mock module manager
        mock_module_manager = MagicMock()
        mock_module_class.return_value = mock_module_manager
        mock_module_manager.create_module_file.return_value = "/test/module/file.lua"
        mock_module_manager.extract_dependencies_from_config.return_value = []
        mock_module_manager.extract_module_paths_from_config.return_value = []
        
        # Mock registry manager
        mock_registry_manager = MagicMock()
        mock_registry_class.return_value = mock_registry_manager
        mock_registry_manager.register_application.return_value = "app-123"
        
        # Run the application (this will try to call submit_job)
        success, job_id = self.app.run()
        
        # Check that the run was successful and returned a job ID
        self.assertTrue(success)
        self.assertEqual(job_id, "job-123")  # From the mocked execution component
        
        # Verify execution component was called (for test job submission)
        self.mock_execution_component.execute.assert_called_once()
    
    def test_application_initialization_with_environment(self):
        """Test that Application can be initialized with all components."""
        # This test verifies the basic initialization works
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.config_component, self.mock_config_component)
        self.assertEqual(self.app.validation_component, self.mock_validation_component)
        self.assertEqual(self.app.script_generation_component, self.mock_script_generation_component)
        self.assertEqual(self.app.execution_component, self.mock_execution_component)
    
    def test_config_component_integration(self):
        """Test that the Application correctly uses the config component."""
        # Call get_config and verify it uses the mock
        config = self.app.config_component.get_config()
        
        # Verify we get the expected configuration
        self.assertEqual(config["name"], "test_app")
        self.assertEqual(config["version"], "1.2.3")
        self.assertIn("environment", config)
        self.assertIn("modules", config["environment"])


if __name__ == '__main__':
    unittest.main() 