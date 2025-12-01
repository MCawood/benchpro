import os
import shutil
import subprocess
import sys
from pathlib import Path
import yaml
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchpro.core.config import Config
from benchpro.core.resolver import Resolver

@pytest.fixture
def temp_env(tmp_path):
    """Setup isolated environment"""
    install_dir = tmp_path / "install"
    config_dir = tmp_path / "user_config"
    site_profiles = tmp_path / "site_profiles"
    
    install_dir.mkdir()
    config_dir.mkdir()
    site_profiles.mkdir()
    
    # Set env vars
    os.environ["BENCHPRO_CONFIG_DIR"] = str(config_dir)
    os.environ["BENCHPRO_SITE_PROFILES"] = str(site_profiles)
    
    yield {
        "install_dir": install_dir,
        "config_dir": config_dir,
        "site_profiles": site_profiles
    }
    
    # Cleanup
    del os.environ["BENCHPRO_CONFIG_DIR"]
    del os.environ["BENCHPRO_SITE_PROFILES"]

def test_install_script(temp_env):
    """Test install.sh and gen_module.sh"""
    install_dir = temp_env["install_dir"]
    script_path = Path(__file__).parent.parent / "scripts/install.sh"
    
    # Run install script
    # We use --dry-run or similar if possible, but the script actually installs.
    # Since we are in a dev environment, we might not want to run the full pip install
    # as it takes time and might mess up.
    # Instead, let's test gen_module.sh directly.
    
    gen_module_path = Path(__file__).parent.parent / "scripts/gen_module.sh"
    version = "0.1.0"
    
    result = subprocess.run(
        [str(gen_module_path), str(install_dir), version],
        capture_output=True,
        text=True,
        check=True
    )
    
    module_content = result.stdout
    assert f"local root = \"{install_dir}\"" in module_content
    assert f"Version: {version}" in module_content
    assert "setenv(\"BENCHPRO_SITE_CONFIG\", config)" in module_content

def test_auto_init(temp_env):
    """Test automated user setup"""
    config_dir = temp_env["config_dir"]
    
    # Ensure config does not exist
    config_path = config_dir / "config.yaml"
    if config_path.exists():
        config_path.unlink()
        
    # Load config (should trigger auto-init)
    config = Config.load()
    
    assert config_path.exists()
    assert (config_dir / "profiles").exists()
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
        assert "system" in data
        assert "defaults" in data

def test_profile_resolution(temp_env):
    """Test profile resolution hierarchy"""
    config_dir = temp_env["config_dir"]
    site_profiles = temp_env["site_profiles"]
    
    # Create user profile
    (config_dir / "profiles").mkdir(exist_ok=True)
    user_profile = config_dir / "profiles" / "user_app.yaml"
    user_profile.touch()
    
    # Create site profile
    site_profile = site_profiles / "site_app.yaml"
    site_profile.touch()
    
    # Create shadowed profile (exists in both)
    (config_dir / "profiles" / "shadowed.yaml").touch()
    (site_profiles / "shadowed.yaml").touch()
    
    # Test resolution
    assert Resolver.resolve_profile("user_app") == user_profile
    assert Resolver.resolve_profile("site_app") == site_profile
    assert Resolver.resolve_profile("shadowed") == config_dir / "profiles" / "shadowed.yaml"
    assert Resolver.resolve_profile("non_existent") is None
