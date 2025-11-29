import pytest
from benchpro.core.domain import Task, ResourceRequest, TaskStatus

def test_save_and_get_run(result_store):
    result_store.save_run("run_1", "suite_A", metadata={"foo": "bar"})
    
    runs = result_store.get_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run_1"
    assert runs[0]["suite_id"] == "suite_A"
    assert runs[0]["metadata"]["foo"] == "bar"

def test_save_and_get_task(result_store):
    result_store.save_run("run_1", "suite_A")
    
    task = Task(
        task_id="task_1",
        suite_id="suite_A",
        resources=ResourceRequest(nodes=1),
        command="echo hello",
        status=TaskStatus.COMPLETED,
        exit_code=0
    )
    
    result_store.save_task(task, "run_1")
    
    tasks = result_store.get_run_tasks("run_1")
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "task_1"
    assert tasks[0]["status"] == "completed"
    assert tasks[0]["exit_code"] == 0
