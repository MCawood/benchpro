import os
from pathlib import Path
from typing import Dict, Optional, Union

def abbreviate_path(path: Union[Path, str], extra_vars: Optional[Dict[str, Union[Path, str]]] = None) -> str:
    """
    Abbreviate a path by substituting common environment variables.
    Prioritizes variables by length (longest match first).
    
    Args:
        path: The path to abbreviate.
        extra_vars: Additional variables to consider for substitution (e.g., {'BP_HOME': ...}).
    """
    if not path:
        return str(path)
        
    path_str = str(path)
    # Don't resolve if it looks like a variable expression already
    if path_str.startswith("$"):
        return path_str
        
    # Only resolve if it's an existing path or absolute. 
    # Otherwise treat as string to avoid CWD prepending.
    p = Path(path).expanduser()
    if p.exists() or p.is_absolute():
        resolved_path = str(p.resolve())
    else:
        resolved_path = path_str
    
    # Gather candidate variables
    candidates = {}
    
    # Standard env vars
    for var in ["HOME", "SCRATCH", "WORK", "PROJECT"]:
        val = os.environ.get(var)
        if val:
            candidates[val] = f"${var}"
            
    # Extra vars
    if extra_vars:
        for var, val in extra_vars.items():
            if val:
                val_resolved = str(Path(val).expanduser().resolve())
                candidates[val_resolved] = f"${var}"
    
    # Sort by length descending to ensure most specific match wins
    # (e.g. $BP_HOME might be inside $HOME)
    sorted_vals = sorted(candidates.keys(), key=len, reverse=True)
    
    for val in sorted_vals:
        if resolved_path.startswith(val):
            # Ensure we match full directory components (prevent partial matching like /home/user -> /home/user2)
            # Or simplified startswith check if paths are strictly directories?
             if resolved_path == val:
                 return candidates[val]
             if resolved_path.startswith(val + os.sep):
                 return resolved_path.replace(val, candidates[val], 1)
                 
    return str(path)
