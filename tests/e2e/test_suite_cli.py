import pytest
import yaml
from benchpro.cli.main import cli

def test_suite_run_dry_run(runner, workspace):
    # Create a suite file
    suite_path = workspace / "suite.yaml"
    suite_data = {
        "name": "test_suite",
        "matrix": {"nodes": [1]},
        "resources": {"threads": 1, "gpus": 0}
    }
    with open(suite_path, "w") as f:
        yaml.dump(suite_data, f)
        
    # Run with dry-run
    result = runner.invoke(cli, ["bench", "run", str(suite_path), "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run enabled" in result.output
    # Benchmarks are printed with generated IDs, verifying suffix
    assert "bench_0" in result.output or "test_suite_bench_0" in result.output
