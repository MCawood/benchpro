import pytest
import os
from benchpro.core.domain import Benchmark, Task, ResourceRequest
from benchpro.core.services.job_builder import JobBuilder

def test_scenario_a_split_strategy():
    """
    Test Scenario A: Mesh (1 node) -> Solve (2 nodes)
    Result should be 2 dependent jobs.
    """
    # 1. Define resources
    res_mesh = ResourceRequest(nodes=1, ranks_per_node=1, time="00:10:00")
    res_solve = ResourceRequest(nodes=2, ranks_per_node=32, time="01:00:00")
    
    # 2. Define tasks
    t1 = Task(
        task_id="mesh", 
        suite_id="scen_a", 
        resources=res_mesh, 
        command="run_mesh",
        working_directory="/tmp/benchpro_test"
    )
    
    t2 = Task(
        task_id="solve", 
        suite_id="scen_a", 
        resources=res_solve, 
        command="run_solve",
        dependencies=["mesh"],
        working_directory="/tmp/benchpro_test"
    )
    
    # 3. Create Benchmark
    bench = Benchmark(
        benchmark_id="b_scenario_a",
        suite_id="scen_a",
        tasks=[t1, t2]
    )
    
    # 4. Invoke JobBuilder with Split Strategy
    builder = JobBuilder("split_by_variance")
    jobs = builder.build([bench])
    
    # 5. Verify
    assert len(jobs) == 2, f"Expected 2 jobs, got {len(jobs)}"
        
    job1 = jobs[0]
    job2 = jobs[1]
    
    # Check resources
    assert job1.resources.nodes == 1
    assert job2.resources.nodes == 2
        
    # Check dependencies
    assert job1.job_id in job2.job_dependencies, f"Job 2 should depend on Job 1 ({job1.job_id})"
