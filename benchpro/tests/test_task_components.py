"""
Tests for task component implementations.

This module contains tests for the concrete component implementations used in the
composition-based task architecture.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
from typing import Dict, Any, List, Optional, Tuple

from benchpro.executor.components.script_generation import (
    BaseScriptGenerator, LocalScriptGenerator, SlurmScriptGenerator
)
from benchpro.executor.components.execution import (
    LocalExecutionComponent, SlurmExecutionComponent
)
from benchpro.executor.components.configuration import (
    BaseConfigComponent, ApplicationConfigComponent, BenchmarkConfigComponent
)
from benchpro.executor.components.validation import (
    BaseValidationComponent, ApplicationValidationComponent, BenchmarkValidationComponent
)
from benchpro.executor.components.interfaces import TemplateError, ExecutionError


class TestScriptGenerationComponents(unittest.TestCase):
    """Tests for the script generation components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_template_engine = MagicMock()
        self.mock_template_engine.render_template.return_value = "echo 'Hello, World!'"
        
        self.test_variables = {
            "name": "test_task",
            "version": "1.0",
            "job": {
                "name": "test_job",
                "nodes": 2,
                "tasks_per_node": 4,
                "time_limit": "01:00:00",
                "queue": "test_queue",
                "account": "test_account"
            },
            "workspace": {
                "logs_dir": "logs"
            }
        }
    
    def test_local_script_generator(self):
        """Test the LocalScriptGenerator."""
        generator = LocalScriptGenerator(template_engine=self.mock_template_engine)
        
        # Test script generation
        result = generator.generate_script("dummy_path", self.test_variables)
        
        # Verify template engine was called with correct arguments
        self.mock_template_engine.render_template.assert_called_once()
        self.assertEqual(result, "echo 'Hello, World!'")
        
        # Verify script_type was set correctly
        args, kwargs = self.mock_template_engine.render_template.call_args
        self.assertEqual(args[0], "dummy_path")
        self.assertEqual(args[1]["script_type"], "local")
    
    def test_slurm_script_generator(self):
        """Test the SlurmScriptGenerator."""
        generator = SlurmScriptGenerator(template_engine=self.mock_template_engine)
        
        # Test script generation
        result = generator.generate_script("dummy_path", self.test_variables)
        
        # Verify template engine was called with correct arguments
        self.mock_template_engine.render_template.assert_called_once()
        
        # Verify Slurm directives were added
        self.assertTrue(result.startswith("#!/bin/bash"))
        self.assertIn("#SBATCH -J test_job", result)
        self.assertIn("#SBATCH -N 2", result)
        self.assertIn("#SBATCH --ntasks-per-node=4", result)
        self.assertIn("#SBATCH -t 01:00:00", result)
        self.assertIn("#SBATCH -p test_queue", result)
        self.assertIn("#SBATCH -A test_account", result)
        
        # Verify template content is included
        self.assertIn("echo 'Hello, World!'", result)
        
        # Verify script_type was set correctly
        args, kwargs = self.mock_template_engine.render_template.call_args
        self.assertEqual(args[0], "dummy_path")
        self.assertEqual(args[1]["script_type"], "slurm")
    
    def test_script_generator_error_handling(self):
        """Test error handling in script generators."""
        # Make template engine raise an exception
        self.mock_template_engine.render_template.side_effect = Exception("Template error")
        
        # Test LocalScriptGenerator error handling
        local_generator = LocalScriptGenerator(template_engine=self.mock_template_engine)
        with self.assertRaises(TemplateError):
            local_generator.generate_script("dummy_path", self.test_variables)
        
        # Test SlurmScriptGenerator error handling
        slurm_generator = SlurmScriptGenerator(template_engine=self.mock_template_engine)
        with self.assertRaises(TemplateError):
            slurm_generator.generate_script("dummy_path", self.test_variables)


class TestExecutionComponents(unittest.TestCase):
    """Tests for the execution components."""
    
    @patch('os.chmod')
    @patch('subprocess.Popen')
    def test_local_execution_component(self, mock_popen, mock_chmod):
        """Test the LocalExecutionComponent."""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Create component
        component = LocalExecutionComponent()
        
        # Test execute method
        success, job_id = component.execute("test_script.sh")
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(job_id, "12345")
        
        # Verify script was made executable
        mock_chmod.assert_called_once()
        
        # Verify subprocess was called
        mock_popen.assert_called_once()
    
    @patch('os.chmod')
    def test_slurm_execution_component(self, mock_chmod):
        """Test the SlurmExecutionComponent."""
        # Create mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.submit_job.return_value = "123456"
        mock_scheduler.check_status.return_value = "RUNNING"
        mock_scheduler.cancel_job.return_value = True
        
        # Create component with mock scheduler (no need to mock get_scheduler)
        component = SlurmExecutionComponent(scheduler=mock_scheduler)
        
        # Test execute method
        success, job_id = component.execute("test_script.sh")
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(job_id, "123456")
        
        # Verify script was made executable
        mock_chmod.assert_called_once()
        
        # Verify scheduler was called
        mock_scheduler.submit_job.assert_called_once_with("test_script.sh")
        
        # Test get_status method
        status = component.get_status("123456")
        self.assertEqual(status, "RUNNING")
        mock_scheduler.check_status.assert_called_once_with("123456")
        
        # Test cancel_job method
        result = component.cancel_job("123456")
        self.assertTrue(result)
        mock_scheduler.cancel_job.assert_called_once_with("123456")


class TestConfigComponents(unittest.TestCase):
    """Tests for the configuration components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config_manager = MagicMock()
        self.test_config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {
                "source": "test.c"
            }
        }
        self.mock_config_manager.load_profile_config.return_value = self.test_config
    
    def test_base_config_component(self):
        """Test the BaseConfigComponent."""
        component = BaseConfigComponent(config_manager=self.mock_config_manager)
        
        # Test load_config method
        config = component.load_config("test_config.yaml")
        self.assertEqual(config, self.test_config)
        self.mock_config_manager.load_profile_config.assert_called_once_with("test_config.yaml", None)
        
        # Test get_config method
        result = component.get_config()
        self.assertEqual(result, self.test_config)
        
        # Test merge_config method
        override_config = {"version": "2.0"}
        merged_config = {"task_type": "application", "name": "test_app", "version": "2.0", "build": {"source": "test.c"}}
        self.mock_config_manager.merge_configs.return_value = merged_config
        
        result = component.merge_config(override_config)
        self.assertEqual(result, merged_config)
        self.mock_config_manager.merge_configs.assert_called_once()
    
    def test_application_config_component(self):
        """Test the ApplicationConfigComponent."""
        component = ApplicationConfigComponent(config_manager=self.mock_config_manager)
        
        # Test load_config method
        config = component.load_config("test_config.yaml")
        self.assertEqual(config, self.test_config)
        
        # Test with invalid task type
        invalid_config = dict(self.test_config)
        invalid_config["task_type"] = "benchmark"
        self.mock_config_manager.load_profile_config.return_value = invalid_config
        
        with self.assertRaises(Exception):
            component.load_config("test_config.yaml")
    
    def test_benchmark_config_component(self):
        """Test the BenchmarkConfigComponent."""
        # Update mock config manager to return benchmark config
        benchmark_config = {
            "task_type": "benchmark",
            "name": "test_benchmark",
            "version": "1.0",
            "run": {
                "application": "test_app"
            }
        }
        self.mock_config_manager.load_profile_config.return_value = benchmark_config
        
        component = BenchmarkConfigComponent(config_manager=self.mock_config_manager)
        
        # Test load_config method
        config = component.load_config("test_config.yaml")
        self.assertEqual(config, benchmark_config)
        
        # Test with invalid task type
        invalid_config = dict(benchmark_config)
        invalid_config["task_type"] = "application"
        self.mock_config_manager.load_profile_config.return_value = invalid_config
        
        with self.assertRaises(Exception):
            component.load_config("test_config.yaml")


class TestValidationComponents(unittest.TestCase):
    """Tests for the validation components."""
    
    def test_base_validation_component(self):
        """Test the BaseValidationComponent."""
        component = BaseValidationComponent()
        
        # Test with valid config
        valid_config = {
            "name": "test_app",
            "version": "1.0",
            "task_type": "application"
        }
        is_valid, errors = component.validate(valid_config)
        self.assertTrue(is_valid)
        self.assertIsNone(errors)
        
        # Test with invalid config (missing fields)
        invalid_config = {
            "name": "test_app"
        }
        is_valid, errors = component.validate(invalid_config)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 2)  # Missing version and task_type
    
    def test_application_validation_component(self):
        """Test the ApplicationValidationComponent."""
        component = ApplicationValidationComponent()
        
        # Test with valid config
        valid_config = {
            "name": "test_app",
            "version": "1.0",
            "task_type": "application",
            "build": {
                "source": "test.c"
            }
        }
        is_valid, errors = component.validate(valid_config)
        self.assertTrue(is_valid)
        self.assertIsNone(errors)
        
        # Test with invalid config (wrong task type)
        invalid_config = dict(valid_config)
        invalid_config["task_type"] = "benchmark"
        is_valid, errors = component.validate(invalid_config)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        
        # Test with invalid config (missing build.source)
        invalid_config = {
            "name": "test_app",
            "version": "1.0",
            "task_type": "application",
            "build": {}
        }
        is_valid, errors = component.validate(invalid_config)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
    
    def test_benchmark_validation_component(self):
        """Test the BenchmarkValidationComponent."""
        component = BenchmarkValidationComponent()
        
        # Test with valid config
        valid_config = {
            "name": "test_benchmark",
            "version": "1.0",
            "task_type": "benchmark",
            "run": {
                "application": "test_app"
            }
        }
        is_valid, errors = component.validate(valid_config)
        self.assertTrue(is_valid)
        self.assertIsNone(errors)
        
        # Test with invalid config (wrong task type)
        invalid_config = dict(valid_config)
        invalid_config["task_type"] = "application"
        is_valid, errors = component.validate(invalid_config)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        
        # Test with invalid config (missing run.application)
        invalid_config = {
            "name": "test_benchmark",
            "version": "1.0",
            "task_type": "benchmark",
            "run": {}
        }
        is_valid, errors = component.validate(invalid_config)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)


if __name__ == '__main__':
    unittest.main() 