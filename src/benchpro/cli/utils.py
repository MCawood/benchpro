import os
from pathlib import Path
from benchpro.core.resolver import Resolver
from benchpro.core.results import ResultStore

def get_installed_builds(ctx, param, incomplete):
    """
    Completion callback for installed application builds.
    Returns a list of Build IDs matching the query.
    """
    try:
        store = ResultStore()
        # This might be slow if DB is large, but for CLI completion typical sizes it's fine.
        builds = store.get_builds()
        
        matches = []
        for b in builds:
            bid = b.get("build_id", "")
            if bid.startswith(incomplete):
                matches.append(bid)
                
        return sorted(list(set(matches)))
    except Exception:
        # Fail silently for completion
        return []

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
