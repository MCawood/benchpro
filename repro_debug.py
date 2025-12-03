import sys
from benchpro.cli.main import cli

print("Starting reproduction script")
try:
    cli(args=["app", "build", "nonexistent"])
except SystemExit as e:
    print(f"Caught SystemExit: {e.code}")
except Exception as e:
    print(f"Caught Exception: {type(e).__name__}: {e}")
print("Finished reproduction script")
