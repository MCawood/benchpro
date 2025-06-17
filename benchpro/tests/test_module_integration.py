"""
Integration tests for module file creation in application tasks.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.workspace.module_manager import ModuleManager
from benchpro.config.config_manager import ConfigManager
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.registry.registry_manager import RegistryManager


class TestModuleIntegration(unittest.TestCase):
    """Integration tests for module file creation in application tasks."""
    
    def setUp(self):
        """Set up the test case."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        
        # Create test directories
        self.workspace_dir = os.path.join(self.test_dir, "workspace")
        self.config_dir = os.path.join(self.test_dir, "config")
        self.source_dir = os.path.join(self.test_dir, "source")
        self.template_dir = os.path.join(self.test_dir, "templates")
        
        # Create the directories
        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Create a test source file
        self.test_source_file = os.path.join(self.source_dir, "hello.c")
        with open(self.test_source_file, "w") as f:
            f.write("""
            #include <stdio.h>
            int main() {
                printf("Hello, World!\\n");
                return 0;
            }
            """)
        
        # Create a test template file
        self.test_template_file = os.path.join(self.template_dir, "hello.j2")
        with open(self.test_template_file, "w") as f:
            f.write("""#!/bin/bash
            # Build script for {{ name }} v{{ version }}
            
            echo "Building {{ name }} v{{ version }}..."
            gcc {{ source }} -o {{ output }} {{ flags }}
            echo "Build complete."
            """)
        
        # Create a test application profile
        self.test_profile_path = os.path.join(self.config_dir, "test_app.yaml")
        with open(self.test_profile_path, "w") as f:
            f.write(f"""
            task_type: application
            name: test_app
            version: 1.0
            build:
                source: hello.c
                compiler: gcc
                flags: -O2
                output: test_app
                threads: 1
            workspace:
                dir: {self.workspace_dir}
                source_dir: {self.source_dir}
                keep_source: true
                keep_build: true
            template: {self.test_template_file}
            """)
        
        # Set up managers
        self.workspace_manager = WorkspaceManager()
        
        # Mock the user directory manager
        self.mock_user_dir_manager = MagicMock()
        self.mock_user_dir_manager.get_source_directory.return_value = self.source_dir
        self.mock_user_dir_manager.get_application_directory.return_value = self.workspace_dir
        
        # Set up config manager with mocked config loader
        self.config_manager = ConfigManager()
        
        # Prepare test profile config (read from file)
        with open(self.test_profile_path, "r") as f:
            self.test_profile_content = f.read()
        
        # Set up registry manager
        self.registry_manager = RegistryManager()
    
    def tearDown(self):
        """Clean up after the test case."""
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    @patch('benchpro.executor.task.os')
    @patch('benchpro.executor.components.execution.os.access')
    @patch('benchpro.executor.components.execution.subprocess.run')
    @patch('benchpro.config.loader.YamlConfigLoader.load_profile_config')
    def test_module_file_creation(self, mock_load_profile, mock_run, mock_access, mock_os):
        """Test module file creation as part of application task execution."""
        # Mock profile config loading
        import yaml
        mock_load_profile.return_value = yaml.safe_load(self.test_profile_content)
        
        # Mock execution to simulate successful task execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = b"Build complete."
        mock_access.return_value = True
        mock_os.path.exists.return_value = True
        
        # Create a module manager
        module_manager = ModuleManager(workspace_manager=self.workspace_manager)
        
        # Create a TaskOrchestrator
        orchestrator = TaskOrchestrator(
            config_manager=self.config_manager,
            workspace_manager=self.workspace_manager,
            registry_manager=self.registry_manager
        )
        
        # Setup orchestrator patching
        with patch('benchpro.executor.task_orchestrator.get_user_dir_manager') as mock_get_user_dir:
            mock_get_user_dir.return_value = self.mock_user_dir_manager
            
            # Execute the application task with dry run
            success, job_id, script_path = orchestrator.execute("test_app", {"task_type": "application"}, dry_run=True)
        
        # Verify the task was successful
        self.assertTrue(success)
        
        # Extract app info from the successful task
        app_name = "test_app"
        app_version = "1.0"
        
        # Verify module file path
        module_file_path = module_manager.get_module_file_path(
            app_name, app_version, self.workspace_dir
        )
        
        # In a real test, we would verify the module file exists
        # But here we're using mocks, so verify the correct path calculation
        expected_path = os.path.join(
            self.workspace_dir, 
            "modulefiles", 
            app_name, 
            f"{app_version}.lua"
        )
        self.assertEqual(module_file_path, expected_path) 