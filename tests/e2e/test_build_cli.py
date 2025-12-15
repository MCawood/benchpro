import pytest
import os
from benchpro.cli.main import cli
from benchpro.core.config import Config

@pytest.fixture
def clean_config(workspace):
    """Ensure a clean config pointing to workspace."""
    config_path = workspace / ".benchpro" / "config.yaml"
    os.environ["BENCHPRO_CONFIG"] = str(config_path)
    return config_path

def test_build_list_empty(runner, clean_config):
    result = runner.invoke(cli, ["app", "list"])
    assert result.exit_code == 0
    assert "Registered Builds" in result.output

def test_build_app_dry_run(runner, clean_config, workspace):
    # Setup valid application profile and dependencies
    profiles_dir = workspace / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    (profiles_dir / "template.sh").write_text("echo building {{ name }}")
    (profiles_dir / "source.txt").write_text("source code")
    
    (profiles_dir / "test_app.yaml").write_text("""
name: test_app
version: "1.0"
source: source.txt
build_template: template.sh
compiler: gcc
""")
    
    # Point config to profiles
    os.environ["BENCHPRO_CONFIG_DIR"] = str(workspace)

    # Run build --dry-run
    # No -n flag!
    result = runner.invoke(cli, ["app", "build", "test_app", "--dry-run"])
    if result.exit_code != 0:
        print(result.output)
    assert result.exit_code == 0
    assert "Dry run enabled" in result.output

def test_build_info_missing(runner, clean_config):
    result = runner.invoke(cli, ["app", "info", "nonexistent"])
    # It prints "not found" but exits with 0
    assert result.exit_code == 0
    assert "not found" in result.output.lower()
