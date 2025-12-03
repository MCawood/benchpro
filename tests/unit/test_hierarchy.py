import pytest
from benchpro.core.domain import Task, Benchmark, Suite, ResourceRequest
from benchpro.core.planner import Planner

def test_benchmark_creation():
    """Test that a Benchmark can be created with multiple tasks."""
    res = ResourceRequest(nodes=1, ranks_per_node=1)
    
    t1 = Task(task_id="t1", suite_id="s1", command="echo 1", resources=res)
    t2 = Task(task_id="t2", suite_id="s1", command="echo 2", resources=res)
    
    bench = Benchmark(
        benchmark_id="b1",
        suite_id="s1",
        tasks=[t1, t2]
    )
    
    assert len(bench.tasks) == 2
    assert bench.tasks[0].task_id == "t1"
    assert bench.tasks[1].task_id == "t2"

def test_planner_returns_benchmarks():
    """Test that Planner.expand_matrix returns a list of Benchmarks."""
    matrix = {
        "nodes": [1, 2],
        "ranks_per_node": [1]
    }
    base_res = {}
    
    # This will fail until Planner is updated
    benchmarks = Planner.expand_matrix("s1", matrix, base_res)
    
    assert len(benchmarks) > 0
    assert isinstance(benchmarks[0], Benchmark)
    # Default strategy: 1 task per benchmark
    assert len(benchmarks[0].tasks) == 1
