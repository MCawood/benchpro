"""Test environment configuration."""

import sys
import os

def test_env():
    """Print environment details."""
    print("\nPython executable:", sys.executable)
    print("\nPython version:", sys.version)
    print("\nCurrent working directory:", os.getcwd())
    print("\nPython path:")
    for p in sys.path:
        print(f"  {p}")
    
    print("\nTrying imports...")
    import benchpro
    print("✓ import benchpro")
    print("benchpro.__file__:", benchpro.__file__)
    
    from benchpro.core.domain.job import Job, JobState
    print("✓ from benchpro.core.domain.job import Job, JobState") 