import os
from pathlib import Path
from benchpro.core.resolver import Resolver

def get_valid_apps(ctx, param, incomplete):
    """
    Completion callback for application profiles.
    Returns a list of available application profiles.
    """
    available = []
    search_paths = Resolver.get_app_search_paths()
    
    for search_path in search_paths:
        if search_path.exists() and search_path.is_dir():
            for profile_file in search_path.glob("*.yaml"):
                if profile_file.is_file():
                    name = profile_file.stem
                    if name.startswith(incomplete):
                        available.append(name)
                        
    return sorted(list(set(available)))

def get_valid_suites(ctx, param, incomplete):
    """
    Completion callback for benchmark suites.
    Returns a list of available benchmark suites.
    """
    available = []
    search_paths = Resolver.get_suite_search_paths()
    
    for search_path in search_paths:
        if search_path.exists() and search_path.is_dir():
            for profile_file in search_path.glob("*.yaml"):
                if profile_file.is_file():
                    name = profile_file.stem
                    if name.startswith(incomplete):
                        available.append(name)
                        
    return sorted(list(set(available)))
