"""
Unit tests for the ModuleManager class.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from benchpro.workspace.module_manager import ModuleManager, ModuleError


class TestModuleManager(unittest.TestCase):
    """Test case for ModuleManager."""
    
    def setUp(self):
        """Set up the test case."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a workspace directory within the temp directory
        self.workspace_dir = os.path.join(self.temp_dir.name, "test_workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Create a mock WorkspaceManager
        self.mock_workspace_manager = MagicMock()
        self.mock_workspace_manager.get_module_file_path.return_value = os.path.join(
            self.workspace_dir, "modulefiles", "test_app", "1.0.lua"
        )
        
        # Create a ModuleManager instance with the mock WorkspaceManager
        self.module_manager = ModuleManager(workspace_manager=self.mock_workspace_manager)
        
        # Basic app data for tests
        self.app_data = {
            "name": "test_app",
            "version": "1.0",
            "workspace_dir": self.workspace_dir,
            "binary_path": os.path.join(self.workspace_dir, "test_app"),
            "environment": {
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ]
            }
        }
        
        # Create a dummy binary file
        with open(self.app_data["binary_path"], "w") as f:
            f.write("#!/bin/bash\necho 'Hello, World!'\n")
        os.chmod(self.app_data["binary_path"], 0o755)
    
    def tearDown(self):
        """Clean up after the test case."""
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    def test_get_module_file_path(self):
        """Test getting the module file path."""
        # Get the module file path
        module_file_path = self.module_manager.get_module_file_path(
            "test_app", "1.0", self.workspace_dir
        )
        
        # Verify the path is correct
        expected_path = os.path.join(
            self.workspace_dir, "modulefiles", "test_app", "1.0.lua"
        )
        self.assertEqual(module_file_path, expected_path)
    
    def test_create_module_file(self):
        """Test creating a module file."""
        # Create the module file
        module_file_path = self.module_manager.create_module_file(self.app_data)
        
        # Verify the module file was created
        self.assertTrue(os.path.exists(module_file_path))
        
        # Verify the module file contains the expected content
        with open(module_file_path, "r") as f:
            content = f.read()
            
        # Check key components
        self.assertIn("test_app", content)
        self.assertIn("1.0", content)
        self.assertIn("prepend_path", content)
        self.assertIn("whatis", content)
        self.assertIn("setenv", content)
        
        # Check environment variable
        self.assertIn("BP_TEST_APP_DIR", content)
        self.assertIn(self.workspace_dir, content)
        
        # Check module dependencies
        self.assertIn("depends_on(\"gcc/10.2.0\")", content)
        self.assertIn("depends_on(\"openmpi/4.0.5\")", content)
    
    def test_create_module_file_missing_data(self):
        """Test creating a module file with missing data."""
        # Test missing name
        missing_name = {
            "version": "1.0",
            "workspace_dir": self.workspace_dir,
            "binary_path": self.app_data["binary_path"]
        }
        with self.assertRaises(ModuleError):
            self.module_manager.create_module_file(missing_name)
            
        # Test missing workspace_dir
        missing_workspace = {
            "name": "test_app",
            "version": "1.0",
            "binary_path": self.app_data["binary_path"]
        }
        with self.assertRaises(ModuleError):
            self.module_manager.create_module_file(missing_workspace)
            
        # Test missing binary_path
        missing_binary = {
            "name": "test_app",
            "version": "1.0",
            "workspace_dir": self.workspace_dir
        }
        with self.assertRaises(ModuleError):
            self.module_manager.create_module_file(missing_binary)
    
    def test_verify_module_file(self):
        """Test verifying a module file."""
        # Create the module file
        module_file_path = self.module_manager.create_module_file(self.app_data)
        
        # Verify the module file
        self.assertTrue(self.module_manager.verify_module_file(module_file_path))
        
        # Test with non-existent file
        non_existent_path = os.path.join(self.workspace_dir, "non_existent.lua")
        self.assertFalse(self.module_manager.verify_module_file(non_existent_path))
        
        # Test with invalid file (empty)
        invalid_path = os.path.join(self.workspace_dir, "invalid.lua")
        with open(invalid_path, "w") as f:
            f.write("")
        self.assertFalse(self.module_manager.verify_module_file(invalid_path))
        
        # Test with invalid file (missing required keywords)
        invalid_path2 = os.path.join(self.workspace_dir, "invalid2.lua")
        with open(invalid_path2, "w") as f:
            f.write("-- This is a dummy module file without required keywords")
        self.assertFalse(self.module_manager.verify_module_file(invalid_path2))
    
    def test_module_creation_filesystem_error(self):
        """Test module creation with filesystem errors."""
        # Create a directory with the same name as the module file to cause an error
        os.makedirs(os.path.join(self.workspace_dir, "modulefiles", "test_app"), exist_ok=True)
        module_file_path = os.path.join(self.workspace_dir, "modulefiles", "test_app", "1.0.lua")
        os.makedirs(module_file_path, exist_ok=True)  # This should cause a failure
        
        # Verify the ModuleError is raised
        with self.assertRaises(ModuleError):
            self.module_manager.create_module_file(self.app_data)
            
    @patch('benchpro.workspace.module_manager.Template')
    def test_template_rendering_error(self, mock_template):
        """Test module creation with template rendering errors."""
        # Mock the Template to raise an exception
        mock_template_instance = MagicMock()
        mock_template_instance.render.side_effect = Exception("Template rendering error")
        mock_template.return_value = mock_template_instance
        
        # Verify the ModuleError is raised
        with self.assertRaises(ModuleError):
            self.module_manager.create_module_file(self.app_data)
            
    def test_extract_dependencies_from_config(self):
        """Test extracting dependencies from config."""
        # Test with valid config
        config = {
            "environment": {
                "modules": [
                    {"name": "gcc", "version": "10.2.0"},
                    {"name": "openmpi", "version": "4.0.5"}
                ]
            }
        }
        dependencies = self.module_manager.extract_dependencies_from_config(config)
        self.assertEqual(len(dependencies), 2)
        self.assertEqual(dependencies[0]["name"], "gcc")
        self.assertEqual(dependencies[0]["version"], "10.2.0")
        
        # Test with string-based modules
        config = {
            "environment": {
                "modules": ["gcc/10.2.0", "openmpi"]
            }
        }
        dependencies = self.module_manager.extract_dependencies_from_config(config)
        self.assertEqual(len(dependencies), 2)
        self.assertEqual(dependencies[0]["name"], "gcc")
        self.assertEqual(dependencies[0]["version"], "10.2.0")
        self.assertEqual(dependencies[1]["name"], "openmpi")
        self.assertNotIn("version", dependencies[1])
        
        # Test with invalid config
        config = {"environment": {}}
        dependencies = self.module_manager.extract_dependencies_from_config(config)
        self.assertEqual(dependencies, [])
        
        # Test with None config
        dependencies = self.module_manager.extract_dependencies_from_config(None)
        self.assertEqual(dependencies, [])
        
    def test_extract_module_paths_from_config(self):
        """Test extracting module paths from config."""
        # Test with valid config
        config = {
            "environment": {
                "module_paths": [
                    "/path/to/modulefiles",
                    "relative/path"
                ]
            }
        }
        module_paths = self.module_manager.extract_module_paths_from_config(config)
        self.assertEqual(len(module_paths), 2)
        self.assertEqual(module_paths[0], "/path/to/modulefiles")
        self.assertTrue(os.path.isabs(module_paths[1]))
        
        # Test with invalid config
        config = {"environment": {}}
        module_paths = self.module_manager.extract_module_paths_from_config(config)
        self.assertEqual(module_paths, [])
        
        # Test with None config
        module_paths = self.module_manager.extract_module_paths_from_config(None)
        self.assertEqual(module_paths, []) 