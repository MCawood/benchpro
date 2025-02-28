#!/usr/bin/env python3
"""Script to update BenchPro version across all necessary files."""

import re
import sys
from pathlib import Path
from datetime import datetime
import yaml

def update_version_py(version: str) -> None:
    """Update version in version.py."""
    version_file = Path("benchpro/version.py")
    with open(version_file, "w") as f:
        f.write('"""BenchPro version information."""\n\n')
        f.write(f'__version__ = "{version}"\n')

def update_defaults_yaml(version: str) -> None:
    """Update version in defaults.yaml."""
    defaults_file = Path("benchpro/data/settings/defaults.yaml")
    with open(defaults_file) as f:
        data = yaml.safe_load(f)
    
    # Update version in immutable settings
    data["settings"]["immutable"]["version"]["value"] = version
    
    # Update metadata
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    
    with open(defaults_file, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)

def validate_version(version: str) -> bool:
    """Validate version string format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))

def main():
    if len(sys.argv) != 2:
        print("Usage: bump_version.py NEW_VERSION")
        print("Example: bump_version.py 1.0.1")
        sys.exit(1)
    
    new_version = sys.argv[1]
    if not validate_version(new_version):
        print("Error: Version must be in format X.Y.Z")
        sys.exit(1)
    
    print(f"Updating version to {new_version}")
    
    # Update files
    update_version_py(new_version)
    update_defaults_yaml(new_version)
    
    print("Version updated successfully")
    print("Don't forget to:")
    print("1. Review the changes")
    print("2. Commit the changes")
    print("3. Create a git tag")

if __name__ == "__main__":
    main() 