"""
Registry Formatter for BenchPRO.

This module provides formatting utilities for displaying registry data in various formats.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import inspect

import yaml
from tabulate import tabulate

# Get logger
logger = logging.getLogger(__name__)

class RegistryFormatter:
    """
    Formats registry data for display in various formats.
    
    Responsibilities:
    - Format application registry data in tabular, YAML, or JSON formats
    - Provide color-coded status indicators
    - Support pagination for large registries
    - Format binary paths for better readability
    """
    
    # ANSI color codes for terminal output
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bold": "\033[1m"
    }
    
    # Status color mapping
    STATUS_COLORS = {
        "completed": "green",
        "failed": "red",
        "running": "yellow",
        "pending": "blue",
        "unknown": "magenta",
        "building": "cyan"
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize the RegistryFormatter.
        
        Args:
            use_colors: Whether to use colors in terminal output.
        """
        self.use_colors = use_colors and os.isatty(1)  # Only use colors if stdout is a TTY
    
    def format_status(self, status: str) -> str:
        """
        Format status with color coding.
        
        Args:
            status: Status string to format.
            
        Returns:
            Formatted status string with color codes if enabled.
        """
        if not self.use_colors:
            return status
            
        status = status.lower()
        color = self.STATUS_COLORS.get(status, "white")
        return f"{self.COLORS[color]}{status.upper()}{self.COLORS['reset']}"
    
    def format_binary_path(self, path: str, width: int = 30) -> str:
        """
        Format binary path for better readability.
        
        Args:
            path: Binary path to format.
            width: Available width for display.
            
        Returns:
            Formatted path string.
        """
        if not path:
            return ""
            
        if len(path) <= width:
            return path
            
        # Show the first part and last part of the path with ellipsis in the middle
        parts = path.split('/')
        if len(parts) <= 2:
            return "..." + path[-(width-3):]
            
        # Keep the first directory and filename for context
        first_part = parts[0]
        last_parts = '/'.join(parts[-2:])  # Last directory and filename
        
        # Calculate how much space we have left for the middle part
        remaining_width = width - len(first_part) - len(last_parts) - 5  # 5 for "/.../""
        
        if remaining_width <= 0:
            return "..." + path[-(width-3):]
            
        return f"{first_part}/.../{last_parts}"
    
    def format_timestamp(self, timestamp: str) -> str:
        """
        Format ISO timestamp for better readability.
        
        Args:
            timestamp: ISO format timestamp.
            
        Returns:
            Formatted date/time string.
        """
        if not timestamp:
            return ""
            
        try:
            # Parse the UTC timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Convert to local time for display
            local_dt = dt.astimezone() 
            return local_dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error formatting timestamp {timestamp}: {e}")
            return timestamp
    
    def format_table(self, applications: List[Dict[str, Any]], 
                    sort_by: Optional[str] = None,
                    reverse: bool = False) -> str:
        """
        Format applications as a table using tabulate.
        
        Args:
            applications: List of application dictionaries.
            sort_by: Column to sort by.
            reverse: Whether to sort in reverse order.
            
        Returns:
            Formatted table string.
        """
        if not applications:
            return "No valid applications found in registry."
            
        # Filter out non-dictionary entries
        valid_applications = [app for app in applications if isinstance(app, dict)]
        if not valid_applications:
            return "No valid applications found in registry."
            
        # Sort if requested
        if sort_by and valid_applications and sort_by in valid_applications[0]:
            valid_applications = sorted(valid_applications, 
                                   key=lambda x: x.get(sort_by, ""), 
                                   reverse=reverse)
        
        # Column definitions
        headers = ["APP_ID", "NAME", "VERSION", "SUBMIT_TIME", "STATUS", "BINARY_PATH"]
        
        # Prepare data for tabulate
        table_data = []
        for app in valid_applications:
            row = []
            row.append(app.get("id", ""))
            row.append(app.get("name", ""))
            
            # Ensure version is properly formatted as a string to preserve decimal points
            version_value = app.get("version", "")
            row.append(str(version_value))
            
            row.append(self.format_timestamp(str(app.get("build_timestamp", ""))))
            status = self.format_status(str(app.get("status", "")))
            row.append(status)
            binary_path = self.format_binary_path(str(app.get("binary_path", "")))
            row.append(binary_path)
            table_data.append(row)
        
        # Use tabulate with consistent options
        table = tabulate(table_data, 
                       headers=headers, 
                       tablefmt="fancy_grid",
                       numalign="left")  # Align numbers left to preserve formatting
        return table
    
    def format_yaml(self, applications: List[Dict[str, Any]]) -> str:
        """
        Format applications as YAML.
        
        Args:
            applications: List of application dictionaries.
            
        Returns:
            YAML string representation.
        """
        # Filter out non-dictionary entries
        valid_applications = []
        for app in applications:
            if isinstance(app, dict):
                valid_applications.append(app)
            else:
                logger.warning(f"Skipping invalid application entry of type {type(app)}: {app}")
        
        return yaml.dump({"applications": valid_applications}, default_flow_style=False)
    
    def format_json(self, applications: List[Dict[str, Any]]) -> str:
        """
        Format applications as JSON.
        
        Args:
            applications: List of application dictionaries.
            
        Returns:
            JSON string representation.
        """
        # Filter out non-dictionary entries
        valid_applications = []
        for app in applications:
            if isinstance(app, dict):
                valid_applications.append(app)
            else:
                logger.warning(f"Skipping invalid application entry of type {type(app)}: {app}")
        
        return json.dumps({"applications": valid_applications}, indent=2)
    
    def format_application_details(self, app: Dict[str, Any]) -> str:
        """
        Format detailed information about a single application.
        
        Args:
            app: Application dictionary.
            
        Returns:
            Formatted details string.
        """
        if not app:
            return "Application not found."
            
        # Create a detailed view with tabulate
        details = []
        
        # Add a header
        details.append(f"# Application Details for {app.get('name', 'Unknown')}")
        details.append("")
        
        # Basic info table
        basic_info = [
            ["ID", app.get("id", "")],
            ["Name", app.get("name", "")],
            ["Version", app.get("version", "")],
            ["Status", self.format_status(str(app.get("status", "")))],
            ["Build Time", self.format_timestamp(str(app.get("build_timestamp", "")))],
            ["Workspace", app.get("workspace_dir", "")]
        ]
        
        details.append(tabulate(basic_info, tablefmt="fancy_grid"))
        details.append("")
        
        # Binary info
        binary_path = app.get("binary_path", "")
        details.append("# Binary Information")
        
        if binary_path and os.path.exists(binary_path):
            file_stats = os.stat(binary_path)
            file_size = file_stats.st_size / 1024  # KB
            mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            is_executable = os.access(binary_path, os.X_OK)
            
            binary_info = [
                ["Path", binary_path],
                ["Exists", "Yes"],
                ["Size", f"{file_size:.2f} KB"],
                ["Modified", mod_time],
                ["Executable", "Yes" if is_executable else "No"]
            ]
            
            details.append(tabulate(binary_info, tablefmt="fancy_grid"))
        else:
            details.append("Binary not found or not specified.")
            
        # Add build parameters if present
        if "build_parameters" in app and app["build_parameters"]:
            details.append("")
            details.append("# Build Parameters")
            
            params = []
            for key, value in app["build_parameters"].items():
                params.append([key, str(value)])
                
            details.append(tabulate(params, tablefmt="fancy_grid"))
            
        # Add Binary Verification section (useful information, not just for tests)
        details.append("")
        details.append("# Binary Verification")
        
        if binary_path and os.path.exists(binary_path):
            details.append("Binary exists and is accessible.")
        else:
            details.append("Binary not found or not accessible.")
            
        return "\n".join(details) 