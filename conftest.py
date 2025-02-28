"""Configure pytest for BenchPRO tests."""

import os
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.absolute()

# Add the project root to sys.path if not already there
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Also add the parent directory to handle the package import
parent_dir = project_root.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir)) 