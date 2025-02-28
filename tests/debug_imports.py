"""Debug test to check import paths."""

import sys
import os

def test_debug_imports():
    """Print debug information about the Python environment."""
    print("\nCurrent working directory:", os.getcwd())
    print("\nPython executable:", sys.executable)
    print("\nPython path:")
    for p in sys.path:
        print(f"  {p}")
    
    print("\nTrying imports...")
    import benchpro
    print("✓ import benchpro")
    import benchpro.core
    print("✓ import benchpro.core")
    from benchpro.core.executor.scheduler import SchedulerExecutor
    print("✓ from benchpro.core.executor.scheduler import SchedulerExecutor") 