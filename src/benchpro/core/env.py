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
    1. Walk up from current working directory to find examples/ directory
    2. Check if examples/apps/ or examples/benchmarks/ directory exists (development indicator)
    """
    # Start from the current working directory
    cwd = Path.cwd()
    
    # Check if we're in a git repo and look for examples directory
    current = cwd
    while current != current.parent:  # Stop at filesystem root
        examples_dir = current / "examples"
        if examples_dir.exists() and ((examples_dir / "apps").exists() or (examples_dir / "benchmarks").exists()):
            return current
        current = current.parent
    
    # Also check from the package location
    try:
        import benchpro
        package_path = Path(benchpro.__file__).parent.parent.parent
        examples_dir = package_path / "examples"
        if examples_dir.exists() and ((examples_dir / "apps").exists() or (examples_dir / "benchmarks").exists()):
            return package_path
    except (AttributeError, ImportError):
        pass
    
    return None


def is_development_mode() -> bool:
    """
    Check if we're running in development mode.
    Development mode is detected if:
    - Running from source tree (examples/apps or examples/benchmarks exists)
    - BENCHPRO_SITE_PROFILES is not set (production would set this)
    """
    source_root = get_source_root()
    site_profiles_set = bool(os.environ.get("BENCHPRO_SITE_PROFILES"))
    
    # If site profiles are set, we're in production
    if site_profiles_set:
        return False
    
    # If we can find source root, we're in development
    return source_root is not None


def get_dev_apps_path() -> Optional[Path]:
    """
    Get the development apps path (examples/apps) if in development mode.
    Returns None if not in development mode or path doesn't exist.
    """
    if not is_development_mode():
        return None
    
    source_root = get_source_root()
    if source_root:
        dev_apps = source_root / "examples" / "apps"
        if dev_apps.exists():
            return dev_apps
    
    return None


def get_dev_benchmarks_path() -> Optional[Path]:
    """
    Get the development benchmarks path (examples/benchmarks) if in development mode.
    Returns None if not in development mode or path doesn't exist.
    """
    if not is_development_mode():
        return None
    
    source_root = get_source_root()
    if source_root:
        dev_benchmarks = source_root / "examples" / "benchmarks"
        if dev_benchmarks.exists():
            return dev_benchmarks
    
    return None

