import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from benchpro.core.config import Config
from benchpro.core.domain import Build
from benchpro.core.env import get_dev_profiles_path

class Resolver:
    def __init__(self, builds: List[Build]):
        self.builds = builds

    def resolve(self, 
                code: str, 
                version: str = None, 
                system: str = None, 
                build_label: str = None) -> Optional[Build]:
        """
        Select the best matching build based on constraints.
        Ordering:
        1. code (must match)
        2. version (exact > wildcard/unspecified)
        3. system (exact > unspecified)
        4. build_label (exact > unspecified)
        5. build_timestamp (newest first)
        """
        candidates = [b for b in self.builds if b.code == code]
        
        if not candidates:
            return None
            
        # Filter by constraints if provided
        if version:
            candidates = [b for b in candidates if b.version == version]
            
        if system:
            candidates = [b for b in candidates if b.system == system]
            
        if build_label:
            candidates = [b for b in candidates if b.build_label == build_label]
            
        if not candidates:
            return None
            
        # Sort by timestamp descending (newest first)
        candidates.sort(key=lambda b: b.build_timestamp, reverse=True)
        
        return candidates[0]

    @staticmethod
    def get_profile_search_paths() -> List[Path]:
        """
        Get all profile search paths in order of precedence.
        Returns list of directories to search for profiles.
        
        Search order:
        1. Project-local profiles (.benchpro/profiles)
        2. User profiles (~/.config/benchpro/profiles)
        3. Site profiles ($BENCHPRO_SITE_PROFILES) - production
        4. Development profiles (examples/build) - fallback if site profiles not set
        """
        search_paths = []
        
        # Project-local profiles (highest precedence)
        project_profiles = Path.cwd() / ".benchpro" / "profiles"
        if project_profiles.exists():
            search_paths.append(project_profiles)
        
        # User profiles
        if os.environ.get("BENCHPRO_CONFIG_DIR"):
            user_profiles = Path(os.environ.get("BENCHPRO_CONFIG_DIR")) / "profiles"
        else:
            user_profiles = Path.home() / ".config/benchpro/profiles"
        if user_profiles.exists():
            search_paths.append(user_profiles)
        
        # Site profiles (production)
        if os.environ.get("BENCHPRO_SITE_PROFILES"):
            site_profiles = Path(os.environ.get("BENCHPRO_SITE_PROFILES"))
            if site_profiles.exists():
                search_paths.append(site_profiles)
        else:
            # Development fallback: use examples/build if available
            dev_profiles = get_dev_profiles_path()
            if dev_profiles:
                search_paths.append(dev_profiles)
        
        return search_paths

    @staticmethod
    def resolve_profile(name: str) -> Optional[Path]:
        """
        Resolve a profile by name.
        Search order:
        1. Local file (if name is a path)
        2. Project profiles (.benchpro/profiles)
        3. User profiles
        4. Site profiles
        """
        # 1. Check if it's a direct path
        path = Path(name)
        if path.exists():
            return path
            
        # If no extension, add .yaml
        if not name.endswith(".yaml"):
            name += ".yaml"
        
        # Get search paths
        search_paths = Resolver.get_profile_search_paths()
        
        # Search
        for base in search_paths:
            candidate = base / name
            if candidate.exists():
                return candidate
                
        return None

    @staticmethod
    def list_available_profiles() -> Dict[str, List[Path]]:
        """
        List all available profiles from all search paths.
        Returns a dictionary mapping search path to list of profile files found there.
        """
        available = {}
        search_paths = Resolver.get_profile_search_paths()
        
        for search_path in search_paths:
            profiles = []
            if search_path.exists() and search_path.is_dir():
                for profile_file in sorted(search_path.glob("*.yaml")):
                    if profile_file.is_file():
                        profiles.append(profile_file)
                if profiles:
                    available[str(search_path)] = profiles
        
        return available
