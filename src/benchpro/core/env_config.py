import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class EnvConfigLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.compilers = self._load_config("compilers.yaml")
        self.mpi = self._load_config("mpi.yaml")

    def _load_config(self, filename: str) -> Dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f)

    def resolve_env(self, name: str, version: str, category: str) -> Dict[str, str]:
        """
        Resolve environment variables for a given software.
        category: 'compiler' or 'mpi'
        """
        config = self.compilers if category == "compiler" else self.mpi
        
        # Find matching entry by alias
        entry = None
        for key, data in config.items():
            if key == name or name in data.get("aliases", []):
                entry = data
                break
        
        if not entry:
            return {}

        # Find matching version
        # If version is None, assume latest/default, which usually matches "*"
        # But we should probably rely on the resolved version passed in.
        # If version is passed as "19.1.1", we need to check ranges.
        
        for v_config in entry.get("versions", []):
            if self._version_match(version, v_config["range"]):
                return v_config.get("env", {})
                
        return {}

    def get_aliases(self, name: str, category: str) -> List[str]:
        """
        Get all aliases for a given software name.
        category: 'compiler' or 'mpi'
        """
        config = self.compilers if category == "compiler" else self.mpi
        
        # Find matching entry
        for key, data in config.items():
            if key == name or name in data.get("aliases", []):
                # Return all aliases plus the key itself
                aliases = data.get("aliases", [])
                if key not in aliases:
                    aliases.append(key)
                return aliases
                
        # If not found, return name itself as fallback
        return [name]

    def _version_match(self, version: str, constraint: str) -> bool:
        """
        Check if version matches constraint.
        Constraints: "*", "<2024", ">=2024", etc.
        """
        if constraint == "*":
            return True
            
        if not version:
            return False

        # Simple comparison logic
        # TODO: Use a proper library like packaging.version if needed
        # For now, handle simple <, >, <=, >=, ==
        
        match = re.match(r"([<>]=?|==)(.+)", constraint)
        if not match:
            return version == constraint
            
        op, target = match.groups()
        
        # Try float comparison first, then string
        try:
            v_num = float(version.split(".")[0])
            t_num = float(target)
            
            if op == "<": return v_num < t_num
            if op == ">": return v_num > t_num
            if op == "<=": return v_num <= t_num
            if op == ">=": return v_num >= t_num
            if op == "==": return v_num == t_num
        except ValueError:
            # String comparison
            if op == "<": return version < target
            if op == ">": return version > target
            if op == "<=": return version <= target
            if op == ">=": return version >= target
            if op == "==": return version == target
            
        return False
