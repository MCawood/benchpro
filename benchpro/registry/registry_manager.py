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

from benchpro.utils.user_dir import user_dir_manager, UserDirectoryManagerInterface, get_user_dir_manager
from benchpro.utils.logger import get_logger


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
            app_data: Application data to register.
            
        Returns:
            The ID of the registered application.
        """
        self.logger.info(f"Registering application: {app_data.get('name', 'unknown')}")
        self.logger.debug(f"Application data: {app_data}")
        
        # Load the latest registry
        self.load()
        
        # Ensure required fields are present
        required_fields = ["name", "workspace_dir", "binary_path"]
        for field in required_fields:
            if field not in app_data:
                self.logger.error(f"Missing required field '{field}' in application data")
                return ""
                
        # Generate a unique ID if not provided
        if "id" not in app_data:
            # Get version, default to "1.0" if not provided
            version = app_data.get("version", "1.0")
            # Remove dots from version for cleaner ID
            version_str = str(version).replace(".", "")
            # Generate ID in the format: [name]_[version]_[6-digit-hash]
            app_data["id"] = f"{app_data['name']}_{version_str}_{self._generate_random_string(6)}"
            
        # Add timestamp if not provided
        if "build_timestamp" not in app_data:
            app_data["build_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
        # Set status if not provided
        if "status" not in app_data:
            app_data["status"] = "completed"
            
        # Add the application to the registry
        self.registry["applications"].append(app_data)
        self.registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Save the registry
        if self._save_registry():
            self.logger.info(f"Successfully registered application {app_data['name']} with ID {app_data['id']}")
            return app_data["id"]
        else:
            self.logger.error(f"Failed to register application {app_data['name']}")
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
        self.logger.debug(f"Update data: {app_data}")
        
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
            self.logger.debug(f"Using binary path: {sorted_matches[0].get('binary_path', '')}")
            return sorted_matches[0]
                
        self.logger.debug(f"Application with name {app_name} not found in registry")
        return None
            
    def find_applications(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find applications matching the given criteria.
        
        Args:
            criteria: Dictionary of criteria to match.
            
        Returns:
            List of matching applications.
        """
        # Load the latest registry
        self.load()
        
        # Find matching applications
        matches = []
        for app in self.registry["applications"]:
            match = True
            for key, value in criteria.items():
                # Handle nested keys (e.g., "build_parameters.compiler")
                if "." in key:
                    parts = key.split(".")
                    app_value = app
                    for part in parts:
                        if part not in app_value:
                            match = False
                            break
                        app_value = app_value[part]
                    if match and app_value != value:
                        match = False
                # Handle direct keys
                elif key not in app or app[key] != value:
                    match = False
                    
            if match:
                matches.append(app)
                
        return matches
            
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