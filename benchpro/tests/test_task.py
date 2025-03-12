"""
Tests for the Task classes.

This module contains tests for the new composition-based Task classes.
"""

import os
import unittest
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from benchpro.executor.task import Task, Application, Benchmark
from benchpro.executor.task_factory import TaskFactory
from benchpro.executor.components.interfaces import ConfigComponent, ValidationComponent, ScriptGenerationComponent, ExecutionComponent


class TestTask(unittest.TestCase):
    """Tests for the Task class."""
    
    def setUp(self):
        """Set up the test case."""
        # Create mock components
        self.mock_config = MagicMock(spec=ConfigComponent)
        self.mock_validation = MagicMock(spec=ValidationComponent)
        self.mock_script_gen = MagicMock(spec=ScriptGenerationComponent)
        self.mock_execution = MagicMock(spec=ExecutionComponent)
        
        # Create a task instance
        self.task = Task(
            config_component=self.mock_config,
            validation_component=self.mock_validation,
            script_generation_component=self.mock_script_gen,
            execution_component=self.mock_execution
        )
        
        # Set up mock return values
        self.mock_config.get_config.return_value = {"key": "value"}
        self.mock_validation.validate.return_value = (True, None)
        self.mock_script_gen.prepare_variables.return_value = {"var": "value"}
        self.mock_script_gen.generate_script.return_value = "#!/bin/bash\necho 'Hello, World!'"
        self.mock_execution.execute.return_value = (True, "job123")
        
    def test_prepare(self):
        """Test the prepare method."""
        # Set up mock return values
        self.mock_config.load_config.return_value = {"key": "value"}
        self.mock_config.merge_config.return_value = {"key": "value", "override": "value"}
        
        # Call the method
        config = self.task.prepare("profile_name", {"override": "value"})
        
        # Verify interactions
        self.mock_config.load_config.assert_called_once_with("profile_name")
        self.mock_config.merge_config.assert_called_once_with({"override": "value"})
        self.mock_validation.validate.assert_called_once()
        
        # Verify return value
        self.assertEqual(config, {"key": "value", "override": "value"})
        
    @patch('os.makedirs')
    @patch('os.chmod')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_generate_script(self, mock_open, mock_chmod, mock_makedirs):
        """Test the generate_script method."""
        # Call the method
        script_path = self.task.generate_script("template.sh", "output.sh")
        
        # Verify interactions
        self.mock_script_gen.prepare_variables.assert_called_once()
        self.mock_script_gen.generate_script.assert_called_once_with("template.sh", {"var": "value"})
        mock_open.assert_called_once()
        mock_chmod.assert_called_once()
        
        # Verify return value
        self.assertEqual(script_path, "output.sh")
        
    def test_submit_job(self):
        """Test the submit_job method."""
        # Call the method
        success, job_id = self.task.submit_job("script.sh")
        
        # Verify interactions
        self.mock_execution.execute.assert_called_once_with("script.sh")
        
        # Verify return values
        self.assertTrue(success)
        self.assertEqual(job_id, "job123")
        
    def test_get_job_status(self):
        """Test the get_job_status method."""
        # Set up mock
        self.mock_execution.get_status.return_value = "RUNNING"
        
        # Call the method
        status = self.task.get_job_status("job123")
        
        # Verify interactions
        self.mock_execution.get_status.assert_called_once_with("job123")
        
        # Verify return value
        self.assertEqual(status, "RUNNING")
        
    def test_cancel_job(self):
        """Test the cancel_job method."""
        # Set up mock
        self.mock_execution.cancel_job.return_value = True
        
        # Call the method
        success = self.task.cancel_job("job123")
        
        # Verify interactions
        self.mock_execution.cancel_job.assert_called_once_with("job123")
        
        # Verify return value
        self.assertTrue(success)


class TestApplication(unittest.TestCase):
    """Tests for the Application class."""
    
    def setUp(self):
        """Set up the test case."""
        # Create mock components
        self.mock_config = MagicMock(spec=ConfigComponent)
        self.mock_validation = MagicMock(spec=ValidationComponent)
        self.mock_script_gen = MagicMock(spec=ScriptGenerationComponent)
        self.mock_execution = MagicMock(spec=ExecutionComponent)
        
        # Create an Application instance
        self.app = Application(
            config_component=self.mock_config,
            validation_component=self.mock_validation,
            script_generation_component=self.mock_script_gen,
            execution_component=self.mock_execution
        )
        
    def test_initialization(self):
        """Test that the Application is initialized correctly."""
        self.assertIsInstance(self.app, Task)
        self.assertEqual(self.app.config_component, self.mock_config)
        self.assertEqual(self.app.validation_component, self.mock_validation)
        self.assertEqual(self.app.script_generation_component, self.mock_script_gen)
        self.assertEqual(self.app.execution_component, self.mock_execution)


class TestBenchmark(unittest.TestCase):
    """Tests for the Benchmark class."""
    
    def setUp(self):
        """Set up the test case."""
        # Create mock components
        self.mock_config = MagicMock(spec=ConfigComponent)
        self.mock_validation = MagicMock(spec=ValidationComponent)
        self.mock_script_gen = MagicMock(spec=ScriptGenerationComponent)
        self.mock_execution = MagicMock(spec=ExecutionComponent)
        
        # Create a Benchmark instance
        self.benchmark = Benchmark(
            config_component=self.mock_config,
            validation_component=self.mock_validation,
            script_generation_component=self.mock_script_gen,
            execution_component=self.mock_execution
        )
        
        # Set up mock return values
        self.mock_config.get_config.return_value = {
            "application": {"name": "test_app", "version": "1.0"},
            "benchmark": {"name": "test_bench"}
        }
        
    def test_initialization(self):
        """Test that the Benchmark is initialized correctly."""
        self.assertIsInstance(self.benchmark, Task)
        self.assertEqual(self.benchmark.config_component, self.mock_config)
        self.assertEqual(self.benchmark.validation_component, self.mock_validation)
        self.assertEqual(self.benchmark.script_generation_component, self.mock_script_gen)
        self.assertEqual(self.benchmark.execution_component, self.mock_execution)


class TestTaskFactory(unittest.TestCase):
    """Tests for the TaskFactory."""
    
    @patch('benchpro.executor.task_factory.get_user_dir_manager')
    @patch('benchpro.executor.task_factory.ConfigManager')
    @patch('benchpro.executor.task_factory.TemplateEngine')
    @patch('benchpro.executor.task_factory.WorkspaceManager')
    @patch('benchpro.executor.task_factory.RegistryManager')
    def setUp(self, mock_registry_manager, mock_workspace_manager, mock_template_engine,
               mock_config_manager, mock_get_user_dir_manager):
        """Set up the test case."""
        # Set up mocks
        self.mock_registry_manager = mock_registry_manager.return_value
        self.mock_workspace_manager = mock_workspace_manager.return_value
        self.mock_template_engine = mock_template_engine.return_value
        self.mock_config_manager = mock_config_manager.return_value
        self.mock_user_dir_manager = mock_get_user_dir_manager.return_value
        
        # Create factory instance
        self.factory = TaskFactory()
    
    @patch('benchpro.executor.task_factory.ApplicationConfigComponent')
    @patch('benchpro.executor.task_factory.ApplicationValidationComponent')
    @patch('benchpro.executor.task_factory.LocalScriptGenerator')
    @patch('benchpro.executor.task_factory.LocalExecutionComponent')
    def test_create_application_task_local(self, mock_local_exec, mock_local_script, 
                                           mock_app_validation, mock_app_config):
        """Test creating an application task with local execution."""
        # Set up mocks
        mock_app_config_instance = mock_app_config.return_value
        mock_app_validation_instance = mock_app_validation.return_value
        mock_local_script_instance = mock_local_script.return_value
        mock_local_exec_instance = mock_local_exec.return_value
        
        # Call the method
        task = self.factory.create_task("application", "local")
        
        # Verify the task is created correctly
        self.assertIsInstance(task, Application)
        self.assertEqual(task.config_component, mock_app_config_instance)
        self.assertEqual(task.validation_component, mock_app_validation_instance)
        self.assertEqual(task.script_generation_component, mock_local_script_instance)
        self.assertEqual(task.execution_component, mock_local_exec_instance)
        
        # Verify component creation
        mock_app_config.assert_called_once()
        mock_app_validation.assert_called_once()
        mock_local_script.assert_called_once()
        mock_local_exec.assert_called_once()
    
    @patch('benchpro.executor.task_factory.BenchmarkConfigComponent')
    @patch('benchpro.executor.task_factory.BenchmarkValidationComponent')
    @patch('benchpro.executor.task_factory.SlurmScriptGenerator')
    @patch('benchpro.executor.task_factory.SlurmExecutionComponent')
    def test_create_benchmark_task_slurm(self, mock_slurm_exec, mock_slurm_script, 
                                         mock_bench_validation, mock_bench_config):
        """Test creating a benchmark task with Slurm execution."""
        # Set up mocks
        mock_bench_config_instance = mock_bench_config.return_value
        mock_bench_validation_instance = mock_bench_validation.return_value
        mock_slurm_script_instance = mock_slurm_script.return_value
        mock_slurm_exec_instance = mock_slurm_exec.return_value
        
        # Call the method
        task = self.factory.create_task("benchmark", "slurm")
        
        # Verify the task is created correctly
        self.assertIsInstance(task, Benchmark)
        self.assertEqual(task.config_component, mock_bench_config_instance)
        self.assertEqual(task.validation_component, mock_bench_validation_instance)
        self.assertEqual(task.script_generation_component, mock_slurm_script_instance)
        self.assertEqual(task.execution_component, mock_slurm_exec_instance)
        
        # Verify component creation
        mock_bench_config.assert_called_once()
        mock_bench_validation.assert_called_once()
        mock_slurm_script.assert_called_once()
        mock_slurm_exec.assert_called_once()
    
    def test_create_task_with_config_execution_type(self):
        """Test creating a task with execution type from config."""
        # Create a task with execution type from config
        config = {"execution": {"type": "slurm"}}
        
        # Patch the _create_script_generation_component and _create_execution_component methods
        with patch.object(self.factory, '_create_script_generation_component') as mock_create_script:
            with patch.object(self.factory, '_create_execution_component') as mock_create_exec:
                # Call the method
                task = self.factory.create_task("application", "slurm", config)
                
                # Verify the correct execution components are created
                mock_create_script.assert_called_once_with("slurm")
                mock_create_exec.assert_called_once_with("slurm")


if __name__ == '__main__':
    unittest.main() 