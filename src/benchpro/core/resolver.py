from typing import List, Optional, Dict, Any
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
