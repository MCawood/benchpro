"""
Tests for task component implementations.

This module contains tests for the concrete component implementations used in the
composition-based task architecture.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
from typing import Dict, Any, List, Optional, Tuple

from benchpro.templates.script_generators import (
    LocalScriptGenerator, SlurmScriptGenerator, TemplateError, ScriptGenerationComponent
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
from benchpro.executor.components.interfaces import ExecutionError


class TestScriptGenerationComponents(unittest.TestCase):
    """Tests for the script generation components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock for the script generator that returns a simple script
        self.mock_script_generator = MagicMock()
        self.mock_script_generator.generate_script.return_value = "echo 'Hello, World!'"
        
        self.test_variables = {
            "name": "test_task",
            "version": "1.0",
            "job": {
                "name": "test_job",
                "queue": "test_queue",
                "nodes": 1,
                "time_limit": "01:00:00"
            }
        }
        
        # Create a temporary directory for output
        self.output_dir = "/tmp/test_script_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create a test template file
        self.template_path = os.path.join(self.output_dir, "test_template.j2")
        with open(self.template_path, "w") as f:
            f.write("echo 'Hello, {{ name }}!'")
    
    def _write_script_to_file(self, script_content, output_dir):
        """Helper to write script content to a file and return the path."""
        script_path = os.path.join(output_dir, "test_script.sh")
        with open(script_path, "w") as f:
            f.write(script_content)
        return script_path
        
    def test_local_script_generator(self):
        """Test the LocalScriptGenerator."""
        # Create a generator
        generator = LocalScriptGenerator()
        
        # Generate a script
        script_content = generator.generate_script(self.template_path, self.test_variables)
        
        # Save script to file
        script_path = self._write_script_to_file(script_content, self.output_dir)
        
        # Check the script content
        self.assertIn("Hello, test_task", script_content)
        self.assertTrue(os.path.exists(script_path))
        
    def test_slurm_script_generator(self):
        """Test the SlurmScriptGenerator."""
        # Create a generator
        generator = SlurmScriptGenerator()
        
        # Generate a script
        script_content = generator.generate_script(self.template_path, self.test_variables)
        
        # Save script to file
        script_path = self._write_script_to_file(script_content, self.output_dir)
        
        # Check the script content includes template content
        self.assertIn("Hello, test_task", script_content)
        self.assertTrue(os.path.exists(script_path))
        
        # Verify SLURM directives are present
        self.assertIn("#SBATCH", script_content)
        self.assertIn("#SBATCH -J test_job", script_content)
        self.assertIn("#SBATCH -p test_queue", script_content)
        self.assertIn("#SBATCH -N 1", script_content)
        self.assertIn("#SBATCH -t 01:00:00", script_content)
        
    def test_script_generator_error_handling(self):
        """Test error handling in script generators."""
        # Create a non-existent template path
        non_existent_path = os.path.join(self.output_dir, "non_existent.j2")
        
        # Test LocalScriptGenerator error handling
        local_generator = LocalScriptGenerator()
        with self.assertRaises(TemplateError):
            local_generator.generate_script(non_existent_path, self.test_variables)
            
        # Test SlurmScriptGenerator error handling
        slurm_generator = SlurmScriptGenerator()
        with self.assertRaises(TemplateError):
            slurm_generator.generate_script(non_existent_path, self.test_variables)


class TestExecutionComponents(unittest.TestCase):
    """Tests for the execution components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for output
        self.output_dir = "/tmp/test_execution_output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create a test script file
        self.script_path = os.path.join(self.output_dir, "test_script.sh")
        with open(self.script_path, "w") as f:
            f.write("#!/bin/bash\necho 'Hello, World!'\n")
        os.chmod(self.script_path, 0o755)
    
    @patch('subprocess.Popen')
    def test_local_execution_component(self, mock_popen):
        """Test the LocalExecutionComponent."""
        # Mock time.time() to return a fixed value for job ID generation
        with patch('time.time', return_value=1234567.89):
            # Create component
            component = LocalExecutionComponent()
            
            # Test execute method
            success, job_id = component.execute(self.script_path)
            
            # Verify results
            self.assertTrue(success)
            # Job ID should be time.time() * 1000 as an integer string
            expected_job_id = str(int(1234567.89 * 1000))
            self.assertEqual(job_id, expected_job_id)
            
            # Check that os.system was called, but we can't directly test it
            # since it's a direct system call
        
    def test_slurm_execution_component(self):
        """Test the SlurmExecutionComponent using mock SLURM fixtures."""
        import pytest
        
        # We'll use the mock SLURM system directly since this is a unittest class
        from benchpro.tests.fixtures.mock_slurm import create_mock_slurm_system, patch_slurm_commands
        
        mock_slurm = create_mock_slurm_system(auto_progress_jobs=True, job_run_time=0.05)
        
        try:
            with patch_slurm_commands(mock_slurm):
                # Create component
                component = SlurmExecutionComponent()
                
                # Test execute method
                success, job_id = component.execute(self.script_path)
                
                # Verify results
                self.assertTrue(success)
                self.assertIsNotNone(job_id)
                self.assertTrue(job_id.isdigit(), f"Job ID should be numeric, got: {job_id}")
                
                # Verify job exists in mock system
                job = mock_slurm.get_job(job_id)
                self.assertIsNotNone(job, "Job should exist in mock system")
                
                # Verify command history
                command_history = mock_slurm.command_history
                sbatch_calls = [call for call in command_history if call[0] == "sbatch"]
                self.assertEqual(len(sbatch_calls), 1, "Should have called sbatch once")
                
        finally:
            mock_slurm.stop()


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
                "application": "test_app",
                "executable": "/path/to/executable"
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