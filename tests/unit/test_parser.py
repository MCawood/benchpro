import pytest
from benchpro.core.parser import ResultParser
from benchpro.core.domain import MetricDefinition

def test_result_parser_metric_extraction(tmp_path):
    # Setup log file
    log_file = tmp_path / "bench.log"
    log_file.write_text("""
    Step 1: 100
    Performance: 50.5 GFlops
    Invalid: abc
    """)
    
    metrics = [
        MetricDefinition(name="steps", regex=r"Step 1: (\d+)", unit="count"),
        MetricDefinition(name="perf", regex=r"Performance: ([\d.]+) GFlops", unit="GFlops")
    ]
    
    results = ResultParser.parse(log_file, metrics)
    
    assert results["steps"]["value"] == 100
    assert results["perf"]["value"] == 50.5
    assert results["perf"]["unit"] == "GFlops"

def test_result_parser_missing_file(tmp_path):
    metrics = [MetricDefinition(name="steps", regex=r"(\d+)", unit="")]
    results = ResultParser.parse(tmp_path / "missing", metrics)
    assert results == {}

def test_result_parser_no_match(tmp_path):
    log_file = tmp_path / "bench.log"
    log_file.write_text("No match here")
    metrics = [MetricDefinition(name="steps", regex=r"Step: (\d+)", unit="")]
    
    results = ResultParser.parse(log_file, metrics)
    assert "steps" not in results
