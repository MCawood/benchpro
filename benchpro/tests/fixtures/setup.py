"""
Test environment setup utilities.

This module provides functions to create standardized test environments
using the centralized test data definitions.
"""

import os
import yaml
from typing import Dict, Any, List, Optional

from .test_data import (
    STANDARD_APPLICATION_PROFILES,
    STANDARD_BENCHMARK_PROFILES,
    STANDARD_TEMPLATES,
    STANDARD_SOURCE_FILES,
    STANDARD_DEFAULT_CONFIG,
    STANDARD_SYSTEM_CONFIG,
    get_standard_application_profile,
    get_standard_benchmark_profile,
    get_standard_template,
    get_standard_source_file,
    get_standard_system_data
)


def create_standard_test_profiles(test_env: Dict[str, str], 
                                profile_names: Optional[List[str]] = None) -> None:
    """
    Create standard test profiles in the test environment.
    
    Args:
        test_env: Test environment dictionary with directory paths.
        profile_names: List of profile names to create. If None, creates all standard profiles.
    """
    if profile_names is None:
        # Create all standard profiles
        app_profiles = list(STANDARD_APPLICATION_PROFILES.keys())
        bench_profiles = list(STANDARD_BENCHMARK_PROFILES.keys())
    else:
        # Filter profiles by requested names
        app_profiles = [name for name in profile_names 
                       if name in STANDARD_APPLICATION_PROFILES]
        bench_profiles = [name for name in profile_names 
                         if name in STANDARD_BENCHMARK_PROFILES]
    
    # Create application profiles
    for profile_name in app_profiles:
        profile_data = get_standard_application_profile(profile_name)
        profile_path = os.path.join(test_env["inputs_app_dir"], f"{profile_name}.yaml")
        
        with open(profile_path, "w") as f:
            yaml.dump(profile_data, f, default_flow_style=False)
    
    # Create benchmark profiles
    for profile_name in bench_profiles:
        profile_data = get_standard_benchmark_profile(profile_name)
        profile_path = os.path.join(test_env["inputs_bench_dir"], f"{profile_name}.yaml")
        
        with open(profile_path, "w") as f:
            yaml.dump(profile_data, f, default_flow_style=False)


def create_standard_templates(test_env: Dict[str, str], 
                            template_names: Optional[List[str]] = None) -> None:
    """
    Create standard templates in the test environment.
    
    Args:
        test_env: Test environment dictionary with directory paths.
        template_names: List of template names to create. If None, creates all standard templates.
    """
    if template_names is None:
        template_names = list(STANDARD_TEMPLATES.keys())
    
    # Create templates in both application and benchmark directories
    for template_name in template_names:
        template_content = get_standard_template(template_name)
        
        # Create in application directory
        app_template_path = os.path.join(test_env["inputs_app_dir"], template_name)
        with open(app_template_path, "w") as f:
            f.write(template_content)
        
        # Create in benchmark directory
        bench_template_path = os.path.join(test_env["inputs_bench_dir"], template_name)
        with open(bench_template_path, "w") as f:
            f.write(template_content)


def create_standard_source_files(test_env: Dict[str, str], 
                                source_names: Optional[List[str]] = None) -> None:
    """
    Create standard source files in the test environment.
    
    Args:
        test_env: Test environment dictionary with directory paths.
        source_names: List of source file names to create. If None, creates all standard source files.
    """
    if source_names is None:
        source_names = list(STANDARD_SOURCE_FILES.keys())
    
    for source_name in source_names:
        source_content = get_standard_source_file(source_name)
        source_path = os.path.join(test_env["inputs_source_dir"], source_name)
        
        with open(source_path, "w") as f:
            f.write(source_content)


def create_standard_configs(test_env: Dict[str, str]) -> None:
    """
    Create standard configuration files in the test environment.
    
    Args:
        test_env: Test environment dictionary with directory paths.
    """
    # Create default configuration
    default_config_path = os.path.join(test_env["config_dir"], "default.yaml")
    with open(default_config_path, "w") as f:
        yaml.dump(STANDARD_DEFAULT_CONFIG, f, default_flow_style=False)
    
    # Create system configuration directory and file
    system_config_dir = os.path.join(test_env["config_dir"], "system")
    os.makedirs(system_config_dir, exist_ok=True)
    
    system_config_path = os.path.join(system_config_dir, "default.yaml")
    with open(system_config_path, "w") as f:
        yaml.dump(STANDARD_SYSTEM_CONFIG, f, default_flow_style=False)


def setup_complete_test_environment(test_env: Dict[str, str], 
                                  profile_names: Optional[List[str]] = None,
                                  template_names: Optional[List[str]] = None,
                                  source_names: Optional[List[str]] = None) -> None:
    """
    Set up a complete test environment with all standard test data.
    
    Args:
        test_env: Test environment dictionary with directory paths.
        profile_names: List of profile names to create. If None, creates all.
        template_names: List of template names to create. If None, creates all.
        source_names: List of source file names to create. If None, creates all.
    """
    # Create standard configurations
    create_standard_configs(test_env)
    
    # Create standard profiles
    create_standard_test_profiles(test_env, profile_names)
    
    # Create standard templates
    create_standard_templates(test_env, template_names)
    
    # Create standard source files
    create_standard_source_files(test_env, source_names)


def setup_minimal_test_environment(test_env: Dict[str, str]) -> None:
    """
    Set up a minimal test environment with essential test data.
    
    Args:
        test_env: Test environment dictionary with directory paths.
    """
    # Essential profiles for most tests
    essential_profiles = ["test_app", "test_benchmark"]
    
    # Essential templates
    essential_templates = ["hello_world.j2", "vanilla.j2", "test.j2"]
    
    # Essential source files
    essential_sources = ["hello_world.c", "test_app.c"]
    
    setup_complete_test_environment(
        test_env,
        profile_names=essential_profiles,
        template_names=essential_templates,
        source_names=essential_sources
    )


def setup_config_test_environment(test_env: Dict[str, str]) -> None:
    """
    Set up test environment specifically for configuration tests.
    
    Args:
        test_env: Test environment dictionary with directory paths.
    """
    # Profiles needed for config tests
    config_profiles = ["test_app", "merge_test", "cli_test", "test_profile"]
    
    # Templates needed
    config_templates = ["hello_world.j2", "test_app.j2"]
    
    # Source files needed
    config_sources = ["test_app.c", "merge_test.c", "cli_test.c"]
    
    setup_complete_test_environment(
        test_env,
        profile_names=config_profiles,
        template_names=config_templates,
        source_names=config_sources
    )


def setup_orchestrator_test_environment(test_env: Dict[str, str]) -> None:
    """
    Set up test environment specifically for orchestrator tests.
    
    Args:
        test_env: Test environment dictionary with directory paths.
    """
    # Profiles needed for orchestrator tests
    orchestrator_profiles = [
        "test_app", "orchestrator_test_profile", "factory_test_profile", "golden_path_profile"
    ]
    
    # Templates needed
    orchestrator_templates = ["hello_world.j2", "vanilla.j2", "test.j2"]
    
    # Source files needed
    orchestrator_sources = ["hello_world.c", "test_app.c"]
    
    setup_complete_test_environment(
        test_env,
        profile_names=orchestrator_profiles,
        template_names=orchestrator_templates,
        source_names=orchestrator_sources
    ) 