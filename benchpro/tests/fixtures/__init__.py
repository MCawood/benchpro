"""
Centralized test fixtures for BenchPRO.

This module provides standardized test data that can be reused across all tests,
ensuring consistency and reducing maintenance overhead.

This includes:
- Standard test data for applications, benchmarks, templates, and source files
- Mock SLURM system for testing scheduler functionality without SLURM dependencies
- Convenient fixtures for various testing scenarios
"""

# Import SLURM testing utilities for easy access
from .mock_slurm import (
    MockSlurmSystem,
    JobState,
    create_mock_slurm_system,
    patch_slurm_commands
)

from .slurm_fixtures import (
    SlurmTestHelper,
    create_slurm_script,
    create_minimal_slurm_script,
    assert_slurm_directives_present
)

# Standard test data imports
from .test_data import (
    get_standard_application_profile,
    get_standard_benchmark_profile,
    get_standard_template,
    get_standard_source_file,
    get_standard_system_data,
    get_all_standard_profiles
)

__all__ = [
    # SLURM testing
    'MockSlurmSystem',
    'JobState',
    'SlurmTestHelper',
    'create_mock_slurm_system',
    'patch_slurm_commands',
    'create_slurm_script',
    'create_minimal_slurm_script',
    'assert_slurm_directives_present',
    
    # Standard test data
    'get_standard_application_profile',
    'get_standard_benchmark_profile', 
    'get_standard_template',
    'get_standard_source_file',
    'get_standard_system_data',
    'get_all_standard_profiles'
] 