"""Test module for verifying the test environment setup."""
import os
import pytest


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