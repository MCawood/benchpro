"""Pytest configuration for Slurm simulator tests."""

import pytest
from pathlib import Path
from .fixtures import slurm_simulator, slurm_test_script, failing_test_script

# Re-export fixtures
__all__ = ['slurm_simulator', 'slurm_test_script', 'failing_test_script'] 