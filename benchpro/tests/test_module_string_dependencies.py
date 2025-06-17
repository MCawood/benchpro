import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from benchpro.workspace.module_manager import ModuleManager, ModuleError
from benchpro.workspace.workspace_manager import WorkspaceManager


class TestModuleStringDependencies(unittest.TestCase):
    """Test case for handling string module dependencies in the ModuleManager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary workspace directory
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = os.path.join(self.temp_dir, "test_workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Mock workspace manager
        self.workspace_manager = MagicMock(spec=WorkspaceManager)
        
        # Create a ModuleManager instance
        self.module_manager = ModuleManager(workspace_manager=self.workspace_manager)
        
        # Prepare test data with string module dependencies
        self.app_data_with_string_modules = {
            "name": "test_app",
            "version": "1.0",
            "workspace_dir": self.workspace_dir,
            "binary_path": os.path.join(self.workspace_dir, "test_app"),
            "environment": {
                "modules": [
                    "gcc/10.2.0",
                    "openmpi/4.0.5",
                    "python"
                ]
            }
        }
        
        # Prepare config component mock
        self.config_component = MagicMock()
        self.config_component.get_config.return_value = {
            "name": "test_app",
            "version": "1.0",
            "workspace": {
                "workspace_dir": self.workspace_dir
            },
            "build": {
                "output": "test_app"
            },
            "environment": {
                "modules": [
                    "gcc/10.2.0",
                    "openmpi/4.0.5",
                    "python"
                ]
            }
        }
        
    def tearDown(self):
        """Tear down test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_create_module_file_with_string_dependencies(self):
        """Test that create_module_file correctly handles string module dependencies."""
        # Create the module file
        with patch('benchpro.workspace.module_manager.Template') as mock_template:
            # Configure mock template
            mock_template_instance = MagicMock()
            mock_template.return_value = mock_template_instance
            mock_template_instance.render.return_value = "-- Test module file"
            
            # Mock verify_module_file to always return True
            with patch.object(self.module_manager, 'verify_module_file', return_value=True):
                module_file_path = self.module_manager.create_module_file(self.app_data_with_string_modules)
                
                # Verify template was called with correct dependencies
                mock_template_instance.render.assert_called_once()
                template_vars = mock_template_instance.render.call_args[1]
                
                # Verify dependencies list has been processed correctly
                self.assertIn('dependencies', template_vars)
                dependencies = template_vars['dependencies']
                
                # Should have 3 dependencies
                self.assertEqual(len(dependencies), 3)
                
                # Verify each dependency is a dictionary with correct format
                self.assertIn('name', dependencies[0])
                self.assertIn('version', dependencies[0])
                self.assertEqual(dependencies[0]['name'], 'gcc')
                self.assertEqual(dependencies[0]['version'], '10.2.0')
                
                self.assertIn('name', dependencies[1])
                self.assertIn('version', dependencies[1])
                self.assertEqual(dependencies[1]['name'], 'openmpi')
                self.assertEqual(dependencies[1]['version'], '4.0.5')
                
                self.assertIn('name', dependencies[2])
                self.assertEqual(dependencies[2]['name'], 'python')

    def test_create_module_file_with_config_component(self):
        """Test that create_module_file correctly handles module dependencies from a config component."""
        # Create the module file
        with patch('benchpro.workspace.module_manager.Template') as mock_template:
            # Configure mock template
            mock_template_instance = MagicMock()
            mock_template.return_value = mock_template_instance
            mock_template_instance.render.return_value = "-- Test module file"
            
            # Mock verify_module_file to always return True
            with patch.object(self.module_manager, 'verify_module_file', return_value=True):
                binary_path = os.path.join(self.workspace_dir, "test_app")
                # Construct app_data from config
                app_data = {
                    'name': self.config_component.get_config()['name'],
                    'version': self.config_component.get_config()['version'],
                    'workspace_dir': self.workspace_dir,
                    'binary_path': binary_path,
                    'environment': self.config_component.get_config().get('environment', {})
                }
                module_file_path = self.module_manager.create_module_file(app_data)
                
                # Verify template was called with correct dependencies
                mock_template_instance.render.assert_called_once()
                template_vars = mock_template_instance.render.call_args[1]
                
                # Verify dependencies list has been processed correctly
                self.assertIn('dependencies', template_vars)
                dependencies = template_vars['dependencies']
                
                # Should have 3 dependencies
                self.assertEqual(len(dependencies), 3)
                
                # Verify each dependency is a dictionary with correct format
                self.assertTrue(any(d['name'] == 'gcc' and d['version'] == '10.2.0' for d in dependencies))
                self.assertTrue(any(d['name'] == 'openmpi' and d['version'] == '4.0.5' for d in dependencies))
                self.assertTrue(any(d['name'] == 'python' for d in dependencies))


if __name__ == "__main__":
    unittest.main() 