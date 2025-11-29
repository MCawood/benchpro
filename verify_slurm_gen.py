from benchpro.core.domain import Task, ResourceRequest, TaskStatus
from benchpro.core.executor import Executor
from benchpro.core.scheduler import SchedulerBackend, Job

class MockSlurmBackend(SchedulerBackend):
    def submit_job(self, job: Job) -> str:
        print("--- Generated Script ---")
        print(job.script_content)
        print("------------------------")
        return "job_123"

    def cancel_job(self, job_id: str) -> bool:
        return True

def test_slurm_gen():
    task = Task(
        task_id="test_task",
        suite_id="test_suite",
        resources=ResourceRequest(
            nodes=2,
            ranks_per_node=4,
            threads=8,
            gpus=1,
            time="01:00:00",
            partition="debug",
            account="myproject"
        ),
        command="echo 'Running on Slurm'",
        status=TaskStatus.PENDING
    )
    
    executor = Executor(backend="slurm")
    # Swap backend for mock
    executor.scheduler = MockSlurmBackend()
    
    executor._submit_slurm_task(task, "run_123")

if __name__ == "__main__":
    test_slurm_gen()
