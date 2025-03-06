"""
Completion module for BenchPRO CLI.

This module provides functions for shell completion in the BenchPRO CLI.
"""

import os
import glob
from typing import List, Optional
from pathlib import Path

from benchpro.utils.user_dir import user_dir_manager
from benchpro.registry.registry_manager import RegistryManager


def get_profile_names(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of available profile names for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of profile names that match the incomplete string
    """
    # Get application and benchmark profile directories
    app_profile_dir = os.path.join(user_dir_manager.get_path("inputs_application"), "*.yaml")
    bench_profile_dir = os.path.join(user_dir_manager.get_path("inputs_benchmark"), "*.yaml")
    
    # Get all YAML files in both directories
    app_profiles = glob.glob(app_profile_dir)
    bench_profiles = glob.glob(bench_profile_dir)
    
    # Extract the base names without extensions
    profiles = []
    for profile in app_profiles + bench_profiles:
        name = os.path.basename(profile).replace(".yaml", "")
        if name.startswith(incomplete):
            profiles.append(name)
    
    return sorted(list(set(profiles)))


def get_system_names(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of available system names for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of system names that match the incomplete string
    """
    # Get system configuration directory
    system_dir = os.path.join(user_dir_manager.get_path("inputs"), "system", "*.yaml")
    
    # Get all YAML files in the directory
    system_files = glob.glob(system_dir)
    
    # Extract the base names without extensions
    systems = []
    for system in system_files:
        name = os.path.basename(system).replace(".yaml", "")
        if name.startswith(incomplete):
            systems.append(name)
    
    return sorted(systems)


def get_app_names(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of available application names for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of application names that match the incomplete string
    """
    # Initialize registry manager
    registry_manager = RegistryManager()
    
    # Get all applications
    applications = registry_manager.list_applications()
    
    # Extract application names
    app_names = set()
    for app in applications:
        name = app.get("name", "")
        if name and name.startswith(incomplete):
            app_names.add(name)
    
    return sorted(list(app_names))


def get_app_versions(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of available application versions for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of application versions that match the incomplete string
    """
    # Initialize registry manager
    registry_manager = RegistryManager()
    
    # Get all applications
    applications = registry_manager.list_applications()
    
    # Extract application versions
    app_versions = set()
    for app in applications:
        version = app.get("version", "")
        if version and str(version).startswith(incomplete):
            app_versions.add(str(version))
    
    return sorted(list(app_versions))


def get_app_ids(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of available application IDs for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of application IDs that match the incomplete string
    """
    # Initialize registry manager
    registry_manager = RegistryManager()
    
    # Get all applications
    applications = registry_manager.list_applications()
    
    # Extract application IDs
    app_ids = []
    for app in applications:
        app_id = app.get("id", "")
        if app_id and app_id.startswith(incomplete):
            app_ids.append(app_id)
    
    return sorted(app_ids)


def get_binary_paths(ctx, param, incomplete: str) -> List[str]:
    """
    Get a list of binary paths for completion.
    
    Args:
        ctx: Click context
        param: Click parameter
        incomplete: The incomplete command being typed
        
    Returns:
        List of binary paths that match the incomplete string
    """
    # If incomplete starts with a path, use that as the base
    if incomplete.startswith('/') or incomplete.startswith('./') or incomplete.startswith('../'):
        base_dir = os.path.dirname(incomplete) or '.'
        prefix = os.path.basename(incomplete)
        
        try:
            # Get all files in the directory
            items = os.listdir(base_dir)
            
            # Filter items that match the prefix
            matches = []
            for item in items:
                if item.startswith(prefix):
                    path = os.path.join(base_dir, item)
                    if os.path.isdir(path):
                        matches.append(f"{path}/")
                    else:
                        matches.append(path)
            
            return matches
        except (FileNotFoundError, PermissionError):
            return []
    
    # Otherwise, suggest current directory
    return ['./'] 