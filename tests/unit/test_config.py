import os
import pytest
from benchpro.core.config import Config

def test_config_load_defaults(workspace):
    """Test loading config with defaults."""
    # We need to point Config.load to our test config
    config_path = workspace / ".benchpro" / "config.yaml"
    config = Config.load([config_path])
    
    assert config.system.name == "test_system"
    assert config.system.max_local_tasks == 2

def test_config_interpolation(workspace):
    """Test variable interpolation in config."""
    config_path = workspace / ".benchpro" / "config.yaml"
    config = Config.load([config_path])
    
    expected_output = f"{workspace}/results"
    assert config.defaults["output_dir"] == expected_output

def test_config_layered_loading(workspace):
    """Test that user config overrides system config."""
    system_config = workspace / "system_config.yaml"
    user_config = workspace / "user_config.yaml"
    
    with open(system_config, "w") as f:
        f.write("system:\n  max_walltime: 100\n")
        
    with open(user_config, "w") as f:
        f.write("system:\n  max_walltime: 200\n")
        
    config = Config.load([system_config, user_config])
    assert config.system.max_walltime == 200
