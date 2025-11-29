import pytest
from benchpro.cli.main import cli

def test_version(runner):
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "BenchPRO-NG v" in result.output

def test_config_show(runner, workspace):
    # Create a config in the workspace
    config_path = workspace / "config.yaml"
    with open(config_path, "w") as f:
        f.write("system:\n  name: e2e_test_system\n")
        
    # Run with env var
    result = runner.invoke(cli, ["config", "show", "--resolved"], env={"BENCHPRO_CONFIG": str(config_path)})
    
    assert result.exit_code == 0
    assert "e2e_test_system" in result.output
