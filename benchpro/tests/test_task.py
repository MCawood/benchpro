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
from benchpro.config.config_manager import ConfigManager
from benchpro.registry.registry_manager import RegistryManager
from benchpro.executor.components.interfaces import ConfigComponent, ValidationComponent, ExecutionComponent
from benchpro.templates.script_generators import ScriptGenerationComponent
from benchpro.executor.components.configuration import BaseConfigComponent
from benchpro.executor.components.validation import (
    ApplicationValidationComponent, BenchmarkValidationComponent
)
from benchpro.executor.components.execution import (
    LocalExecutionComponent, SlurmExecutionComponent
)
from benchpro.templates.script_generators import (
    LocalScriptGenerator, SlurmScriptGenerator
)


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
        # Set up the mock config to return a workspace
        self.mock_config.get_config.return_value = {"workspace": {"dir": "/test/workspace"}}
        
        # Call the method
        success, job_id = self.task.submit_job("script.sh")
        
        # Verify interactions
        self.mock_execution.execute.assert_called_once_with("script.sh", {"dir": "/test/workspace"})
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
    
    def setUp(self):
        """Set up the test case."""
        # Create mock dependencies with proper specs
        self.mock_config_manager = MagicMock(spec=ConfigManager)
        self.mock_registry_manager = MagicMock(spec=RegistryManager)
        
        # Create factory with injected dependencies
        self.factory = TaskFactory(
            config_manager=self.mock_config_manager,
            registry_manager=self.mock_registry_manager
        )
    
    def test_create_application_task_local(self):
        """Test creating an application task with local execution."""
        # Prepare test configuration
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "execution": {"type": "local"},
            "job": {"scheduler": "local"},
            "build": {"source": "test.c"},
            "template": "test.j2"
        }
        
        # Create the task
        task = self.factory.create_task(config)
        
        # Verify the task is created correctly
        self.assertIsInstance(task, Application)
        
        # Verify the components are of the expected types
        self.assertIsInstance(task.config_component, BaseConfigComponent)
        self.assertIsInstance(task.validation_component, ApplicationValidationComponent)
        self.assertIsInstance(task.script_generation_component, LocalScriptGenerator)
        self.assertIsInstance(task.execution_component, LocalExecutionComponent)
        
        # Verify the configuration was set correctly
        task_config = task.config_component.get_config()
        self.assertEqual(task_config["task_type"], "application")
        self.assertEqual(task_config["name"], "test_app")
    
    def test_create_benchmark_task_slurm(self):
        """Test creating a benchmark task with Slurm execution."""
        # Prepare test configuration
        config = {
            "task_type": "benchmark",
            "name": "test_bench",
            "version": "1.0",
            "execution": {"type": "sched"},
            "job": {"scheduler": "slurm"},
            "run": {"executable": "test_exec", "application": "test_app"},
            "template": "test.j2"
        }
        
        # Create the task
        task = self.factory.create_task(config)
        
        # Verify the task is created correctly
        self.assertIsInstance(task, Benchmark)
        
        # Verify the components are of the expected types
        self.assertIsInstance(task.config_component, BaseConfigComponent)
        self.assertIsInstance(task.validation_component, BenchmarkValidationComponent)
        self.assertIsInstance(task.script_generation_component, SlurmScriptGenerator)
        self.assertIsInstance(task.execution_component, SlurmExecutionComponent)
        
        # Verify the configuration was set correctly
        task_config = task.config_component.get_config()
        self.assertEqual(task_config["task_type"], "benchmark")
        self.assertEqual(task_config["name"], "test_bench")
    
    def test_create_task_defaults_to_local_execution(self):
        """Test that tasks default to local execution when no scheduler is specified."""
        # Prepare test configuration without explicit scheduler
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {"source": "test.c"},
            "template": "test.j2"
        }
        
        # Create the task
        task = self.factory.create_task(config)
        
        # Verify local execution components are used by default
        self.assertIsInstance(task.script_generation_component, LocalScriptGenerator)
        self.assertIsInstance(task.execution_component, LocalExecutionComponent)
    
    def test_create_task_with_unknown_scheduler_defaults_to_local(self):
        """Test that unknown schedulers default to local execution."""
        # Prepare test configuration with unknown scheduler
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "job": {"scheduler": "unknown_scheduler"},
            "build": {"source": "test.c"},
            "template": "test.j2"
        }
        
        # Create the task
        task = self.factory.create_task(config)
        
        # Verify local execution components are used as fallback
        self.assertIsInstance(task.script_generation_component, LocalScriptGenerator)
        self.assertIsInstance(task.execution_component, LocalExecutionComponent)
    
    def test_create_task_with_missing_task_type_raises_error(self):
        """Test that missing task_type raises appropriate error."""
        # Prepare invalid configuration without task_type
        config = {
            "name": "test_app",
            "version": "1.0",
            "build": {"source": "test.c"},
            "template": "test.j2"
        }
        
        # Verify that ValueError is raised
        with self.assertRaises(ValueError) as context:
            self.factory.create_task(config)
        
        self.assertIn("task_type", str(context.exception))
    
    def test_create_task_with_unsupported_task_type_raises_error(self):
        """Test that unsupported task types raise appropriate error."""
        # Prepare configuration with invalid task_type
        config = {
            "task_type": "unsupported_type",
            "name": "test_app",
            "version": "1.0",
            "template": "test.j2"
        }
        
        # Verify that ValueError is raised
        with self.assertRaises(ValueError) as context:
            self.factory.create_task(config)
        
        # Check that the error mentions the task type (more robust than exact message)
        error_message = str(context.exception)
        self.assertTrue(
            "task type" in error_message.lower(),
            f"Expected error message to mention 'task type', got: {error_message}"
        )
    
    def test_config_component_receives_injected_config_manager(self):
        """Test that the config component receives the factory's config manager."""
        # Prepare test configuration
        config = {
            "task_type": "application",
            "name": "test_app",
            "version": "1.0",
            "build": {"source": "test.c"},
            "template": "test.j2"
        }
        
        # Create the task
        task = self.factory.create_task(config)
        
        # Verify the config component has the correct config manager
        self.assertEqual(task.config_component.config_manager, self.mock_config_manager)


if __name__ == '__main__':
    unittest.main() 