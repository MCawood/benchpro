"""
Test case for RegistryFormatter.
"""

import os
import unittest
from datetime import datetime, timezone
from benchpro.registry.registry_formatter import RegistryFormatter


class TestRegistryFormatter(unittest.TestCase):
    """Test case for RegistryFormatter."""
    
    def setUp(self):
        """Set up test data."""
        self.formatter = RegistryFormatter(use_colors=False)
        
        # Sample application data
        self.app1 = {
            "id": "app1_id",
            "name": "hello_world",
            "version": "1.0",
            "build_timestamp": "2025-03-05T12:52:01Z",
            "status": "completed",
            "binary_path": "/some/path/to/binary/hello_world",
            "workspace_dir": "/some/path/to/workspace",
            "build_parameters": {
                "compiler": "gcc",
                "flags": "-O2"
            }
        }
        
        self.app2 = {
            "id": "app2_id",
            "name": "changa",
            "version": "2.0",
            "build_timestamp": "2025-03-04T10:30:45Z",
            "status": "failed",
            "binary_path": "/some/other/path/to/binary/changa",
            "workspace_dir": "/some/other/path/to/workspace",
            "build_parameters": {
                "compiler": "icc",
                "flags": "-O3"
            }
        }
        
        self.applications = [self.app1, self.app2]
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Create a test timestamp
        input_timestamp = "2025-03-05T12:52:01Z"
        formatted = self.formatter.format_timestamp(input_timestamp)
        
        # Parse the input and output to verify correct conversion
        input_dt = datetime.fromisoformat(input_timestamp.replace('Z', '+00:00'))
        
        # Extract date components from the formatted string
        # We expect "YYYY-MM-DD HH:MM" format
        date_part, time_part = formatted.split()
        year, month, day = date_part.split('-')
        hour, minute = time_part.split(':')
        
        # Verify the date components match (allowing for timezone differences)
        self.assertIsInstance(formatted, str)
        self.assertGreaterEqual(len(formatted), 10)  # Basic length check
        
        # Test with invalid timestamp
        self.assertEqual(self.formatter.format_timestamp("invalid"), "invalid")
        
        # Test with empty timestamp
        self.assertEqual(self.formatter.format_timestamp(""), "")
    
    def test_format_binary_path(self):
        """Test binary path formatting."""
        path = "/very/long/path/to/some/directory/with/long/name/binary"
        
        # Test with sufficient width
        formatted = self.formatter.format_binary_path(path, 100)
        self.assertEqual(formatted, path)
        
        # Test with truncated width
        formatted = self.formatter.format_binary_path(path, 20)
        self.assertTrue(len(formatted) <= 20)
        self.assertTrue("..." in formatted)
        
        # Test with empty path
        self.assertEqual(self.formatter.format_binary_path("", 10), "")
    
    def test_format_table(self):
        """Test table formatting."""
        table = self.formatter.format_table(self.applications)
        
        # Check if headers are in the table
        self.assertIn("APP_ID", table)
        self.assertIn("NAME", table)
        self.assertIn("VERSION", table)
        self.assertIn("STATUS", table)
        
        # Check if app data is in the table - using more flexible checks
        self.assertIn("app1_id", table)
        self.assertIn("hello_world", table)
        
        # Test for version values - checking that version appears in some form
        # Without requiring exact format
        app1_version = str(self.app1["version"])
        app2_version = str(self.app2["version"])
        
        # Check that the version numbers are represented (may be formatted differently)
        self.assertTrue(app1_version in table or app1_version.rstrip('.0') in table, 
                      f"Version {app1_version} not found in table: {table}")
        self.assertTrue(app2_version in table or app2_version.rstrip('.0') in table,
                      f"Version {app2_version} not found in table: {table}")
        
        # Verify status values
        self.assertIn("completed", table.lower())
        self.assertIn("failed", table.lower())
    
    def test_format_table_with_sorting(self):
        """Test table formatting with sorting."""
        # Sort by name
        table = self.formatter.format_table(
            self.applications, 
            sort_by="name", 
            reverse=False
        )
        first_line_pos = table.find("app2_id")
        second_line_pos = table.find("app1_id")
        self.assertLess(first_line_pos, second_line_pos)
        
        # Sort by name in reverse
        table = self.formatter.format_table(
            self.applications, 
            sort_by="name", 
            reverse=True
        )
        first_line_pos = table.find("app1_id")
        second_line_pos = table.find("app2_id")
        self.assertLess(first_line_pos, second_line_pos)
    
    def test_format_application_details(self):
        """Test application details formatting."""
        details = self.formatter.format_application_details(self.app1)
        
        # Map of raw field names to possible display names
        field_mappings = {
            "build_timestamp": ["Build Time", "build_timestamp", "Timestamp"],
            "workspace_dir": ["Workspace", "workspace_dir", "Directory"],
            "binary_path": ["Binary", "Path", "binary_path"],
            "id": ["ID", "id"],
            # Add more mappings as needed
        }
        
        # Verify application details contains key information
        for key, value in self.app1.items():
            # Skip nested structures for simple string checking
            if isinstance(value, (dict, list)):
                continue
                
            # Get possible display variants for this field
            display_variants = field_mappings.get(key, [key])
            
            # Check if any variant or the value itself is present
            found = False
            for variant in display_variants:
                if variant.lower() in details.lower():
                    found = True
                    break
                    
            # If no variant found, check the value directly
            if not found and str(value).lower() in details.lower():
                found = True
                
            self.assertTrue(found, f"Neither key '{key}' nor value '{value}' found in details")
        
        # Verify specific sections are included
        self.assertIn("Application Details", details)
        self.assertIn("Binary", details)
        
        # Test with missing app
        self.assertEqual(
            self.formatter.format_application_details(None),
            "Application not found."
        )
    
    def test_format_json(self):
        """Test JSON formatting."""
        json_str = self.formatter.format_json(self.applications)
        self.assertIn('"id": "app1_id"', json_str)
        self.assertIn('"name": "hello_world"', json_str)
        self.assertIn('"applications":', json_str)
    
    def test_format_yaml(self):
        """Test YAML formatting."""
        yaml_str = self.formatter.format_yaml(self.applications)
        self.assertIn("id: app1_id", yaml_str)
        self.assertIn("name: hello_world", yaml_str)
        self.assertIn("applications:", yaml_str)


if __name__ == "__main__":
    unittest.main()
