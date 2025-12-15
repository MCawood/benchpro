import pytest
from benchpro.core.domain import Benchmark, Task, ResourceRequest, Job
from benchpro.core.services.job_builder import JobBuilder, OneToOneStrategy, SplitByVarianceStrategy

@pytest.fixture
def resource_small():
    return ResourceRequest(nodes=1, ranks_per_node=1)

@pytest.fixture
def resource_large():
    return ResourceRequest(nodes=128, ranks_per_node=32)

@pytest.fixture
def simple_benchmark(resource_small):
    t1 = Task(task_id="t1", suite_id="s1", resources=resource_small, command="echo 1")
    t2 = Task(task_id="t2", suite_id="s1", resources=resource_small, command="echo 2")
    return Benchmark(benchmark_id="b1", suite_id="s1", tasks=[t1, t2])

@pytest.fixture
def mixed_benchmark(resource_small, resource_large):
    # Chain: Mesh(1) -> Solve(128)
    t1 = Task(task_id="mesh", suite_id="s1", resources=resource_small, command="mesh")
    # t2 depends on t1
    t2 = Task(task_id="solve", suite_id="s1", resources=resource_large, command="solve", dependencies=["mesh"])
    return Benchmark(benchmark_id="mixed", suite_id="s1", tasks=[t1, t2])

def test_one_to_one(simple_benchmark):
    builder = JobBuilder("one_to_one")
    jobs = builder.build([simple_benchmark])
    
    assert len(jobs) == 1
    assert jobs[0].job_id == "b1"
    assert len(jobs[0].tasks) == 2
    assert jobs[0].resources.nodes == 1

def test_split_by_variance(mixed_benchmark):
    builder = JobBuilder("split_by_variance")
    jobs = builder.build([mixed_benchmark])
    
    # Should split into 2 jobs because resources differ
    assert len(jobs) == 2
    
    job1 = jobs[0]
    job2 = jobs[1]
    
    # Verify separation
    assert len(job1.tasks) == 1
    assert job1.tasks[0].task_id == "mesh"
    assert job1.resources.nodes == 1
    
    assert len(job2.tasks) == 1
    assert job2.tasks[0].task_id == "solve"
    assert job2.resources.nodes == 128
    
    # Verify dependency
    assert job1.job_id in job2.job_dependencies
    
def test_inter_benchmark_dependencies():
    # Benchmark A has Task A1
    # Benchmark B has Task B1 (depends on A1)
    res = ResourceRequest(nodes=1)
    t1 = Task(task_id="a1", suite_id="s1", resources=res, command="a")
    b1 = Benchmark(benchmark_id="b_a", suite_id="s1", tasks=[t1])
    
    t2 = Task(task_id="b1", suite_id="s1", resources=res, command="b", dependencies=["a1"])
    b2 = Benchmark(benchmark_id="b_b", suite_id="s1", tasks=[t2])
    
    builder = JobBuilder("one_to_one")
    jobs = builder.build([b1, b2])
    
    assert len(jobs) == 2
    job_a = next(j for j in jobs if "b_a" in j.job_id)
    job_b = next(j for j in jobs if "b_b" in j.job_id)
    
    assert job_a.job_id in job_b.job_dependencies
