"""
Registry Manager for BenchPRO.

This module provides functionality for managing application registries in BenchPRO.
"""

import os
import yaml
import time
import json
import fcntl
from typing import Dict, Any, List, Optional, Union
import copy

from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.utils.logger import get_logger
from benchpro.workspace.module_manager import ModuleManager, ModuleError


class RegistryManager:
    """
    Manages application registries for BenchPRO.
    
    Responsibilities:
    - Store metadata about built applications
    - Provide CRUD operations for application entries
    - Query interface for finding applications by criteria
    - Registry persistence with concurrency handling
    """
    
    def __init__(self, registry_path: Optional[str] = None, user_dir_manager: Optional[UserDirectoryManagerInterface] = None):
        """
        Initialize the RegistryManager.
        
        Args:
            registry_path: Path to the registry file. If None, uses the default path.
            user_dir_manager: UserDirectoryManager instance. If None, uses the default instance.
        """
        # Check if we're in completion mode
        if "_BP_COMPLETE" in os.environ:
            # In completion mode, use a null logger
            import logging
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else:
            # Normal mode, use the regular logger
            self.logger = get_logger(__name__)
            self.logger.info("Initializing RegistryManager")
        
        # Use the provided user_dir_manager or get the default one
        self.user_dir_manager = user_dir_manager or get_user_dir_manager()
        
        if registry_path is None:
            # Use the user directory manager to get the registry path
            self.registry_path = self.user_dir_manager.get_path("registry", "registry.yaml")
        else:
            self.registry_path = registry_path
            
        self.logger.debug(f"Registry path set to: {self.registry_path}")
        
        self.registry = {
            "version": "1.0",
            "last_updated": "",
            "applications": []
        }
        
    def load(self) -> Dict[str, Any]:
        """
        Load the registry from disk.
        
        Returns:
            The loaded registry data.
        """
        self.logger.debug(f"Loading registry from {self.registry_path}")
        
        if not os.path.exists(self.registry_path):
            self.logger.info(f"Registry file not found at {self.registry_path}. Creating new registry.")
            self._save_registry()
            return self.registry
            
        try:
            with open(self.registry_path, 'r') as f:
                # Acquire a shared lock for reading
                fcntl.flock(f, fcntl.LOCK_SH)
                self.registry = yaml.safe_load(f) or {
                    "version": "1.0",
                    "last_updated": "",
                    "applications": []
                }
                fcntl.flock(f, fcntl.LOCK_UN)
                
            self.logger.debug(f"Loaded registry with {len(self.registry.get('applications', []))} applications")
            return self.registry
        except Exception as e:
            self.logger.error(f"Error loading registry: {str(e)}")
            return self.registry
            
    def save(self) -> bool:
        """
        Save the registry to disk.
        
        Returns:
            True if successful, False otherwise.
        """
        self.logger.debug("Saving registry to disk")
        return self._save_registry()
            
    def register_application(self, app_data: Dict[str, Any]) -> str:
        """
        Register a new application in the registry.
        
        Args:
            app_data: Application data to register. Should contain:
                - name: Application name (required)
                - version: Application version (defaults to "1.0")
                - workspace_dir: Workspace directory path (required)
                - binary_path: Path to application binary (required)
                - module_file: Path to the module file (optional, provided by Application.run())
                - environment: Environment configuration including modules (optional but expected)
                
        Returns:
            The ID of the registered application, or empty string on failure.
        """
        app_name = app_data.get('name', 'unknown')
        self.logger.info(f"Registering application: {app_name}")
        
        # Simplified debug logging
        if self.logger.isEnabledFor(10):  # DEBUG level
            self.logger.debug(f"Application data keys: {list(app_data.keys())}")
        
        # Load the latest registry
        self.load()
        
        # Validate required fields
        required_fields = ["name", "workspace_dir", "binary_path"]
        missing_fields = [field for field in required_fields if field not in app_data]
        if missing_fields:
            error_msg = f"Missing required fields in application data: {', '.join(missing_fields)}"
            self.logger.error(error_msg)
            return ""
        
        # Log environment information if present
        if "environment" in app_data:
            self.logger.info(f"Application has environment configuration")
            if "modules" in app_data["environment"]:
                modules = app_data["environment"]["modules"]
                self.logger.info(f"Application has {len(modules)} module dependencies")
                if self.logger.isEnabledFor(10):  # DEBUG level
                    self.logger.debug(f"Module details: {modules}")
        else:
            # Add environment back if it got lost somehow - ensure it at least exists
            app_data["environment"] = {"modules": []}
            self.logger.info(f"Added empty environment section to app_data")
        
        # Make a deep copy of app_data to avoid reference issues
        app_data_copy = copy.deepcopy(app_data)
        
        # Generate a unique ID if not provided
        if "id" not in app_data_copy:
            # Get version, default to "1.0" if not provided
            version = app_data_copy.get("version", "1.0")
            # Remove dots from version for cleaner ID
            version_str = str(version).replace(".", "")
            # Generate ID in the format: [name]_[version]_[6-digit-hash]
            app_data_copy["id"] = f"{app_name}_{version_str}_{self._generate_random_string(6)}"
            
        # Add timestamp if not provided
        if "build_timestamp" not in app_data_copy:
            app_data_copy["build_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
        # Set status if not provided
        if "status" not in app_data_copy:
            app_data_copy["status"] = "completed"
        
        # Create a module file if possible
        if all(field in app_data_copy for field in ["name", "version", "workspace_dir", "binary_path"]):
            try:
                module_manager = ModuleManager()
                module_file_path = module_manager.create_module_file(app_data_copy)
                app_data_copy["module_file"] = module_file_path
                self.logger.info(f"Created module file: {module_file_path}")
            except Exception as e:
                self.logger.error(f"Failed to create module file: {str(e)}")
                # Continue registration even if module file creation fails
            
        # Add the application to the registry
        self.registry["applications"].append(app_data_copy)
        self.registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Save the registry
        if self._save_registry():
            self.logger.info(f"Successfully registered application {app_name} with ID {app_data_copy['id']}")
            return app_data_copy["id"]
        else:
            self.logger.error(f"Failed to register application {app_name}")
            return ""
            
    def update_application(self, app_id: str, app_data: Dict[str, Any]) -> bool:
        """
        Update an existing application in the registry.
        
        Args:
            app_id: ID of the application to update.
            app_data: New application data.
            
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info(f"Updating application with ID: {app_id}")
        
        # Load the latest registry
        self.load()
        
        # Find the application
        for i, app in enumerate(self.registry["applications"]):
            if app.get("id") == app_id:
                # Update the application data
                for key, value in app_data.items():
                    self.registry["applications"][i][key] = value
                    
                # Update the last_updated timestamp
                self.registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                
                # Save the registry
                if self._save_registry():
                    self.logger.info(f"Successfully updated application with ID {app_id}")
                    return True
                else:
                    self.logger.error(f"Failed to update application with ID {app_id}")
                    return False
                    
        self.logger.error(f"Application with ID {app_id} not found in registry")
        return False
            
    def remove_application(self, app_id: str) -> bool:
        """
        Remove an application from the registry.
        
        Args:
            app_id: ID of the application to remove.
            
        Returns:
            True if successful, False otherwise.
        """
        self.logger.info(f"Removing application with ID: {app_id}")
        
        # Load the latest registry
        self.load()
        
        # Find the application
        for i, app in enumerate(self.registry["applications"]):
            if app.get("id") == app_id:
                app_name = app.get("name", "unknown")
                # Remove the application
                del self.registry["applications"][i]
                
                # Update the last_updated timestamp
                self.registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                
                # Save the registry
                if self._save_registry():
                    self.logger.info(f"Successfully removed application {app_name} with ID {app_id}")
                    return True
                else:
                    self.logger.error(f"Failed to remove application with ID {app_id}")
                    return False
                    
        self.logger.error(f"Application with ID {app_id} not found in registry")
        return False
            
    def find_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an application by ID.
        
        Args:
            app_id: ID of the application to find.
            
        Returns:
            The application data if found, None otherwise.
        """
        self.logger.debug(f"Finding application with ID: {app_id}")
        
        # Load the latest registry
        self.load()
        
        # Find the application
        for app in self.registry["applications"]:
            if app.get("id") == app_id:
                self.logger.debug(f"Found application: {app.get('name', 'unknown')}")
                return app
                
        self.logger.debug(f"Application with ID {app_id} not found in registry")
        return None
            
    def find_application_by_name(self, app_name: str, criteria: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Find an application by name and optional criteria.
        
        Args:
            app_name: Name of the application to find.
            criteria: Optional dictionary of additional criteria to match.
            
        Returns:
            The most recently built application data if found, None otherwise.
        """
        self.logger.debug(f"Finding application with name: {app_name}")
        
        # Load the latest registry
        self.load()
        
        # Prepare search criteria
        search_criteria = {"name": app_name}
        if criteria:
            search_criteria.update(criteria)
            
        # Find matching applications
        matches = self.find_applications(search_criteria)
        
        if matches:
            # Sort matches by build timestamp (newest first)
            sorted_matches = sorted(
                matches, 
                key=lambda x: x.get("build_timestamp", ""), 
                reverse=True
            )
            
            # Return the most recently built application
            self.logger.debug(f"Found application: {sorted_matches[0].get('name', 'unknown')} (ID: {sorted_matches[0].get('id', 'unknown')})")
            return sorted_matches[0]
                
        self.logger.debug(f"Application with name {app_name} not found in registry")
        return None
            
    def find_applications(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find applications matching the given criteria.
        
        Args:
            criteria: Dictionary of criteria to match.
                Supported fields:
                - name: Application name
                - version: Application version
                - label: Label inside metadata.label
                
        Returns:
            List of matching applications.
        """
        # Load the latest registry to get fresh data
        self.load()
        
        if not self.registry or "applications" not in self.registry:
            self.logger.warning("No applications found in registry")
            return []

        # Start with all applications
        applications = self.registry["applications"]
        matching_apps = []

        for app in applications:
            # Check if app is a dictionary
            if not isinstance(app, dict):
                continue
                
            # Check name match (required)
            if "name" in criteria and app.get("name") != criteria["name"]:
                continue

            # Check version match (optional)
            if "version" in criteria and criteria["version"]:
                if app.get("version") != criteria["version"]:
                    continue

            # Check label match (optional)
            if "label" in criteria and criteria["label"]:
                # Labels are stored in metadata.label, handle internally
                if not app.get("metadata") or app.get("metadata", {}).get("label") != criteria["label"]:
                    continue

            # If we got here, all specified criteria matched
            matching_apps.append(app)

        # Sort by build timestamp if available, newest first
        matching_apps.sort(
            key=lambda app: app.get("build_timestamp", ""), 
            reverse=True
        )

        return matching_apps
            
    def get_binary_path(self, app_id: str) -> str:
        """
        Get the binary path for an application.
        
        Args:
            app_id: ID of the application.
            
        Returns:
            The binary path if found, empty string otherwise.
        """
        app = self.find_application(app_id)
        if app and "binary_path" in app:
            return app["binary_path"]
            
        return ""
            
    def list_applications(self) -> List[Dict[str, Any]]:
        """
        List all applications in the registry.
        
        Returns:
            List of all applications.
        """
        # Load the latest registry
        self.load()
        
        # Filter out non-dictionary entries to prevent errors
        valid_applications = []
        for app in self.registry.get("applications", []):
            if isinstance(app, dict):
                valid_applications.append(app)
            else:
                self.logger.warning(f"Skipping invalid registry entry: {app}")
        
        return valid_applications
            
    def clean_registry(self, verify_paths: bool = True) -> int:
        """
        Clean the registry by removing entries with invalid paths.
        
        Args:
            verify_paths: If True, verify that binary paths exist.
            
        Returns:
            Number of entries removed.
        """
        # Load the latest registry
        self.load()
        
        # Track the number of entries removed
        removed_count = 0
        
        # Clean the registry
        if verify_paths:
            valid_apps = []
            for app in self.registry["applications"]:
                if "binary_path" in app and os.path.exists(app["binary_path"]):
                    valid_apps.append(app)
                else:
                    self.logger.info(f"Removing application {app.get('name', 'unknown')} with ID {app.get('id', 'unknown')} due to missing binary")
                    removed_count += 1
                    
            self.registry["applications"] = valid_apps
            self.registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Save the registry
            if self._save_registry():
                self.logger.info(f"Cleaned registry, removed {removed_count} entries")
            else:
                self.logger.error("Failed to save registry after cleaning")
                
        return removed_count
            
    def _save_registry(self) -> bool:
        """
        Save the registry to disk with proper locking.
        
        Returns:
            True if successful, False otherwise.
        """
        # Ensure the directory exists
        self.user_dir_manager.ensure_file_directory(self.registry_path)
        
        try:
            with open(self.registry_path, 'w') as f:
                # Acquire an exclusive lock for writing
                fcntl.flock(f, fcntl.LOCK_EX)
                yaml.dump(self.registry, f, default_flow_style=False, sort_keys=False)
                fcntl.flock(f, fcntl.LOCK_UN)
                
            self.logger.debug(f"Saved registry to {self.registry_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving registry: {str(e)}")
            return False
            
    @staticmethod
    def _generate_random_string(length: int = 6) -> str:
        """
        Generate a random string of the specified length.
        
        Args:
            length: Length of the string to generate.
            
        Returns:
            A random string.
        """
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) 