"""
Tests for the TaskOrchestrator class.

This module contains tests for the composition-based TaskOrchestratorComposition.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile
import yaml
import pytest

from benchpro.executor.task import Task, Application, Benchmark
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.config.config_manager import ConfigManager
from benchpro.templates.template_engine import TemplateEngine
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager


class TestTaskOrchestrator(unittest.TestCase):
    """Tests for the TaskOrchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config_manager = MagicMock()
        self.mock_template_engine = MagicMock()
        self.mock_workspace_manager = MagicMock()
        self.mock_registry_manager = MagicMock()
        
        # Create a temporary directory for file operations
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a mock task
        self.mock_task = MagicMock(spec=Task)
        self.mock_task.prepare.return_value = {"template": "test_template.j2"}
        self.mock_task.generate_script.return_value = os.path.join(self.temp_dir, "script.sh")
        self.mock_task.submit_job.return_value = (True, "12345")
        
        # Create a mock config component
        self.mock_config_component = MagicMock()
        self.mock_config_component.get_config.return_value = {
            "workspace": {"logs_dir": os.path.join(self.temp_dir, "logs")}
        }
        
        # Attach the mock config component to the mock task
        self.mock_task.config_component = self.mock_config_component
        
        # Set up the orchestrator
        self.orchestrator = TaskOrchestrator(
            self.mock_config_manager,
            self.mock_template_engine,
            self.mock_workspace_manager,
            self.mock_registry_manager
        )
        
        # Mock the task factory
        self.orchestrator.task_factory = MagicMock()
        self.orchestrator.task_factory.create_task.return_value = self.mock_task
        
        # Set up profile configuration
        self.mock_profile_config = {
            "task_type": "application",
            "execution": {"type": "local"}
        }
        self.mock_config_manager.load_profile_config.return_value = self.mock_profile_config
        self.mock_config_manager.merge_configs.return_value = self.mock_profile_config
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_execute_with_default_config(self):
        """Test executing a task with default configuration."""
        # Call the method
        success, job_id, script_path = self.orchestrator.execute("test_profile")
        
        # Verify the result
        self.assertTrue(success)
        self.assertEqual(job_id, "12345")
        self.assertEqual(script_path, os.path.join(self.temp_dir, "script.sh"))
        
        # Verify method calls
        self.mock_config_manager.load_profile_config.assert_called_once_with("test_profile", None)
        self.mock_config_manager.merge_configs.assert_called_once()
        self.orchestrator.task_factory.create_task.assert_called_once_with(
            "application", "local", self.mock_profile_config
        )
        self.mock_task.prepare.assert_called_once()
        self.mock_task.generate_script.assert_called_once()
        self.mock_task.submit_job.assert_called_once()
    
    def test_execute_with_cli_overrides(self):
        """Test executing a task with CLI overrides."""
        # Set up CLI overrides
        cli_overrides = {
            "task_type": "benchmark",
            "execution": {"type": "slurm"}
        }
        
        # Update mock profile config
        self.mock_profile_config["task_type"] = "benchmark"
        self.mock_profile_config["execution"]["type"] = "slurm"
        
        # Call the method
        success, job_id, script_path = self.orchestrator.execute("test_profile", cli_overrides)
        
        # Verify the result
        self.assertTrue(success)
        self.assertEqual(job_id, "12345")
        
        # Verify method calls
        self.orchestrator.task_factory.create_task.assert_called_once_with(
            "benchmark", "slurm", self.mock_profile_config
        )
        self.mock_task.prepare.assert_called_once()
    
    def test_execute_with_dry_run(self):
        """Test executing a task with dry run option."""
        # Call the method
        success, job_id, script_path = self.orchestrator.execute("test_profile", dry_run=True)
        
        # Verify the result
        self.assertTrue(success)
        self.assertIsNone(job_id)
        
        # Verify method calls
        self.mock_task.prepare.assert_called_once()
        self.mock_task.generate_script.assert_called_once()
        self.mock_task.submit_job.assert_not_called()
    
    def test_execute_with_scheduler_to_slurm_mapping(self):
        """Test mapping scheduler executor type to slurm execution type."""
        # Set up profile with scheduler executor
        self.mock_profile_config["execution"]["type"] = "scheduler"
        
        # Call the method
        self.orchestrator.execute("test_profile")
        
        # Verify slurm was used
        self.orchestrator.task_factory.create_task.assert_called_once_with(
            "application", "slurm", self.mock_profile_config
        )


if __name__ == '__main__':
    unittest.main() 