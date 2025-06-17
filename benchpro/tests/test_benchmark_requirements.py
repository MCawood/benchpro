"""
Tests for Benchmark requirements resolution.

This module tests that benchmark tasks correctly resolve application requirements.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from benchpro.executor.task import Benchmark
from benchpro.executor.components.interfaces import ConfigError


class MockRegistryManager:
    """Mock RegistryManager for testing"""
    
    def __init__(self, return_value=None):
        self.find_applications = MagicMock(return_value=return_value or [])


class TestBenchmarkRequirements(unittest.TestCase):
    """Tests for benchmark application requirements resolution."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mocks for the components
        self.mock_config_component = MagicMock()
        self.mock_validation_component = MagicMock()
        # Make validation component return a valid result
        self.mock_validation_component.validate.return_value = (True, [])
        self.mock_script_generation_component = MagicMock()
        self.mock_execution_component = MagicMock()
        
        # Configure mock config component with sample data
        self.sample_config = {
            "name": "test_bench",
            "version": "1.0",
            "task_type": "benchmark",
            "requirements": {
                "application": "test_app",
                "version": "1.2.3",
                "label": "mpi"
            },
            "run": {
                "executable": "test_exec",
                "arguments": "-n 10"
            },
            "workspace": {
                "workspace_dir": "/test/workspace",
                "output_dir": "output"
            },
            "environment": {
                "modules": []
            }
        }
        
        # Configure the get_config method to return the sample config
        self.mock_config_component.get_config.return_value = self.sample_config
        self.mock_config_component.load_config.return_value = self.sample_config
        self.mock_config_component.merge_config.return_value = self.sample_config
        
        # Sample application data from registry
        self.app_data = {
            "id": "test_app_123",
            "name": "test_app",
            "version": "1.2.3",
            "workspace_dir": "/app/workspace",
            "binary_path": "/app/workspace/bin/test_app",
            "module_file": "/app/workspace/modulefiles/test_app/1.2.3.lua",
            "metadata": {
                "label": "mpi"
            },
            "environment": {
                "module_paths": [
                    "/custom/modulefiles"
                ],
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ],
                "variables": {
                    "PATH": "$PATH:/custom/path"
                }
            }
        }
        
    def test_debug_config_issue(self):
        """Debug why config isn't passed correctly."""
        with patch('benchpro.executor.task.RegistryManager', autospec=True) as MockRegistry:
            # Setup the mock
            mock_instance = MockRegistry.return_value
            mock_instance.find_applications.return_value = [self.app_data]
            
            # Create benchmark with our mocks
            benchmark = Benchmark(
                config_component=self.mock_config_component,
                validation_component=self.mock_validation_component,
                script_generation_component=self.mock_script_generation_component,
                execution_component=self.mock_execution_component
            )
            
            # Ensure proper config is returned
            print(f"Test config before prepare: {self.mock_config_component.get_config()}")
            
            # Call prepare 
            config = benchmark.prepare("test_profile")
            
            # Print the config to debug
            print(f"Config after prepare: {config}")
            
            # Check if find_applications was called
            self.assertTrue(mock_instance.find_applications.called)
        
    @patch('benchpro.executor.task.RegistryManager', autospec=True)
    def test_resolve_application_requirements(self, MockRegistry):
        """Test resolving application requirements."""
        # Configure the mock instance
        mock_instance = MockRegistry.return_value
        mock_instance.find_applications.return_value = [self.app_data]
        
        # Create a Benchmark instance with our mocks
        benchmark = Benchmark(
            config_component=self.mock_config_component,
            validation_component=self.mock_validation_component,
            script_generation_component=self.mock_script_generation_component,
            execution_component=self.mock_execution_component
        )
        
        # Call prepare
        config = benchmark.prepare("test_profile")
        
        # Check that requirements were resolved correctly
        mock_instance.find_applications.assert_called_once()
        call_args = mock_instance.find_applications.call_args[0][0]
        
        # Verify the search criteria
        self.assertEqual(call_args["name"], "test_app")
        self.assertEqual(call_args["version"], "1.2.3")
        self.assertEqual(call_args["label"], "mpi")
        
        # Check that application info was stored
        self.assertIn("dependencies", config)
        self.assertIn("application", config["dependencies"])
        self.assertEqual(config["dependencies"]["application"]["id"], "test_app_123")
        
        # Check module paths were added
        self.assertIn("environment", config)
        self.assertIn("module_paths", config["environment"])
        self.assertIn("/app/workspace/modulefiles", config["environment"]["module_paths"])
        self.assertIn("/custom/modulefiles", config["environment"]["module_paths"])
        
        # Check modules were added and normalized
        self.assertIn("modules", config["environment"])
        for module in config["environment"]["modules"]:
            self.assertIsInstance(module, str)
    
    @patch('benchpro.executor.task.RegistryManager', autospec=True)
    def test_no_matching_applications(self, MockRegistry):
        """Test handling when no applications match the requirements."""
        # Configure the mock to return no matches
        mock_instance = MockRegistry.return_value
        mock_instance.find_applications.return_value = []
        
        # Create a Benchmark instance with our mocks
        benchmark = Benchmark(
            config_component=self.mock_config_component,
            validation_component=self.mock_validation_component,
            script_generation_component=self.mock_script_generation_component,
            execution_component=self.mock_execution_component
        )
        
        # Call prepare - should raise ApplicationNotFoundError when required dependency not found
        from benchpro.executor.task import ApplicationNotFoundError
        with self.assertRaises(ApplicationNotFoundError) as context:
            benchmark.prepare("test_profile")
        
        # Check that find_applications was called
        mock_instance.find_applications.assert_called_once()
        
        # Check the error message
        self.assertIn("Required application 'test_app' not found in registry", str(context.exception))
    
    @patch('benchpro.executor.task.RegistryManager', autospec=True)
    def test_multiple_matching_applications(self, MockRegistry):
        """Test handling when multiple applications match the requirements."""
        # Create a second app with a later timestamp
        app_data2 = dict(self.app_data)
        app_data2["id"] = "test_app_456"
        app_data2["build_timestamp"] = "2023-01-02T12:00:00Z"
        self.app_data["build_timestamp"] = "2023-01-01T12:00:00Z"
        
        # Configure the mock to return multiple matches
        mock_instance = MockRegistry.return_value
        mock_instance.find_applications.return_value = [self.app_data, app_data2]
        
        # Create a Benchmark instance with our mocks
        benchmark = Benchmark(
            config_component=self.mock_config_component,
            validation_component=self.mock_validation_component,
            script_generation_component=self.mock_script_generation_component,
            execution_component=self.mock_execution_component
        )
        
        # Call prepare
        config = benchmark.prepare("test_profile")
        
        # Check that find_applications was called
        mock_instance.find_applications.assert_called_once()
        
        # Check that the newest application was chosen
        self.assertIn("dependencies", config)
        self.assertIn("application", config["dependencies"])
        self.assertEqual(config["dependencies"]["application"]["id"], "test_app_456")
    
    @patch('benchpro.executor.task.RegistryManager', autospec=True)
    def test_no_requirements_section(self, MockRegistry):
        """Test handling when the benchmark has no requirements section."""
        # Configure the mock
        mock_instance = MockRegistry.return_value
        
        # Remove requirements from config
        config_without_requirements = dict(self.sample_config)
        del config_without_requirements["requirements"]
        self.mock_config_component.get_config.return_value = config_without_requirements
        self.mock_config_component.load_config.return_value = config_without_requirements
        self.mock_config_component.merge_config.return_value = config_without_requirements
        
        # Create a Benchmark instance with our mocks
        benchmark = Benchmark(
            config_component=self.mock_config_component,
            validation_component=self.mock_validation_component,
            script_generation_component=self.mock_script_generation_component,
            execution_component=self.mock_execution_component
        )
        
        # Call prepare
        config = benchmark.prepare("test_profile")
        
        # Check that find_applications was not called
        mock_instance.find_applications.assert_not_called()
        
        # Config should not have application dependency
        self.assertNotIn("dependencies", config) 