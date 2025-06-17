"""Test module for verifying the test environment setup."""
import os
import pytest
from benchpro.utils.user_dir import user_dir_manager


def test_environment_setup(setup_test_env):
    """Test that verifies the test environment is set up correctly."""
    # This test simply exercises the setup_test_env fixture
    assert setup_test_env is not None
    
    # Verify the basic directory structure
    assert os.path.exists(setup_test_env["temp_dir"])
    assert os.path.exists(setup_test_env["config_dir"])
    assert os.path.exists(setup_test_env["inputs_dir"])
    
    # Verify the application and benchmark directories
    assert os.path.exists(setup_test_env["inputs_app_dir"])
    assert os.path.exists(setup_test_env["inputs_bench_dir"])
    assert os.path.exists(setup_test_env["inputs_source_dir"])
    
    # Print the directory contents for debugging
    print(f"\nTest environment directories created at: {setup_test_env['temp_dir']}")
    
    # Check for hello_world.j2 template files in application and benchmark directories
    app_template = os.path.join(setup_test_env["inputs_app_dir"], "hello_world.j2")
    bench_template = os.path.join(setup_test_env["inputs_bench_dir"], "hello_world.j2")
    
    print(f"Application template exists: {os.path.exists(app_template)}")
    print(f"Benchmark template exists: {os.path.exists(bench_template)}")
    
    # Check contents of the input directories to see what was copied
    print(f"Application directory contents: {os.listdir(setup_test_env['inputs_app_dir'])}")
    print(f"Benchmark directory contents: {os.listdir(setup_test_env['inputs_bench_dir'])}")
    print(f"Source directory contents: {os.listdir(setup_test_env['inputs_source_dir'])}")
    
    # Verify the template files exist
    assert os.path.exists(app_template), "Application template hello_world.j2 not found"
    assert os.path.exists(bench_template), "Benchmark template hello_world.j2 not found"


def test_environment_isolation(setup_test_env):
    """Test that the test environment is isolated from the user's real ~/.benchpro directory."""
    # Get the test environment root directory
    test_root = user_dir_manager.get_path("root")
    
    # Get the user's real ~/.benchpro directory
    real_benchpro_path = os.path.expanduser("~/.benchpro")
    
    # Verify that the test is NOT using the user's real ~/.benchpro directory
    assert test_root != real_benchpro_path, f"Test is using real user directory {real_benchpro_path} instead of isolated test environment {test_root}"
    
    # Verify that paths requested through user_dir_manager use the test environment
    test_app_path = user_dir_manager.get_path("inputs_application")
    assert real_benchpro_path not in test_app_path, f"Path {test_app_path} contains real user directory {real_benchpro_path}"
    
    # Verify that writing to the test environment doesn't affect the real user directory
    test_file = os.path.join(test_app_path, "test_isolation.txt")
    with open(test_file, "w") as f:
        f.write("This is a test file that should only exist in the test environment")
    
    real_file_path = os.path.join(real_benchpro_path, "inputs", "application", "test_isolation.txt")
    assert not os.path.exists(real_file_path), f"Test modified real user file at {real_file_path}" 