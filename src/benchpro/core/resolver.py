import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from benchpro.core.config import Config
from benchpro.core.domain import Build

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
        candidates.sort(key=lambda b: b.build_timestamp, reverse=True)
        
        return candidates[0]

    @staticmethod
    def resolve_profile(name: str) -> Optional[Path]:
        """
        Resolve a profile by name.
        Search order:
        1. Local file (if name is a path)
        2. User profiles
        3. Site profiles
        """
        # 1. Check if it's a direct path
        path = Path(name)
        if path.exists():
            return path
            
        # If no extension, add .yaml
        if not name.endswith(".yaml"):
            name += ".yaml"
            
        # Get search paths from Config
        # We instantiate Config to get the resolved paths
        config = Config.load()
        
        search_paths = []
        
        # User profiles
        # We need to reconstruct the user config dir logic or expose it in Config
        # For now, let's rely on the env vars or default
        if os.environ.get("BENCHPRO_CONFIG_DIR"):
            user_profiles = Path(os.environ.get("BENCHPRO_CONFIG_DIR")) / "profiles"
        else:
            user_profiles = Path.home() / ".config/benchpro/profiles"
        search_paths.append(user_profiles)
        
        # Site profiles
        if os.environ.get("BENCHPRO_SITE_PROFILES"):
            search_paths.append(Path(os.environ.get("BENCHPRO_SITE_PROFILES")))
        
        # Search
        for base in search_paths:
            candidate = base / name
            if candidate.exists():
                return candidate
                
        return None
