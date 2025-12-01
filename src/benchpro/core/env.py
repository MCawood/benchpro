"""
Environment detection utilities for development vs production mode.
"""
import os
from pathlib import Path
from typing import Optional


def get_source_root() -> Optional[Path]:
    """
    Detect the source root directory if running from a development environment.
    Returns None if running from an installed package.
    
    Detection strategy:
    1. Check if we're in a git repository (has .git directory)
    2. Walk up from current file location to find examples/ directory
    3. Check if examples/build/ directory exists (development indicator)
    """
    # Start from the current working directory
    cwd = Path.cwd()
    
    # Check if we're in a git repo and look for examples directory
    current = cwd
    while current != current.parent:  # Stop at filesystem root
        examples_dir = current / "examples"
        if examples_dir.exists() and (examples_dir / "build").exists():
            return current
        current = current.parent
    
    # Also check from the package location
    try:
        import benchpro
        package_path = Path(benchpro.__file__).parent.parent.parent
        examples_dir = package_path / "examples"
        if examples_dir.exists() and (examples_dir / "build").exists():
            return package_path
    except (AttributeError, ImportError):
        pass
    
    return None


def is_development_mode() -> bool:
    """
    Check if we're running in development mode.
    Development mode is detected if:
    - Running from source tree (examples/ directory exists)
    - BENCHPRO_SITE_PROFILES is not set (production would set this)
    """
    source_root = get_source_root()
    site_profiles_set = bool(os.environ.get("BENCHPRO_SITE_PROFILES"))
    
    # If site profiles are set, we're in production
    if site_profiles_set:
        return False
    
    # If we can find source root, we're in development
    return source_root is not None


def get_dev_profiles_path() -> Optional[Path]:
    """
    Get the development profiles path (examples/build) if in development mode.
    Returns None if not in development mode or path doesn't exist.
    """
    if not is_development_mode():
        return None
    
    source_root = get_source_root()
    if source_root:
        dev_profiles = source_root / "examples" / "build"
        if dev_profiles.exists():
            return dev_profiles
    
    return None

