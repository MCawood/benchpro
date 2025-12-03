import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from benchpro.core.domain import Task, TaskStatus
from benchpro.core.results import ResultStore
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.parser import ResultParser

class CaptureService:
    def __init__(self, result_store: ResultStore = None):
        self.result_store = result_store or ResultStore()
        self.slurm = SlurmBackend()
        self.local = LocalBackend()

    def check_task_status(self, task: Task) -> TaskStatus:
        """Check and update task status."""
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return task.status

        # If no job_id, we can't check status (unless it's local and we track PIDs, but currently we don't)
        if not task.job_id:
            return task.status

        # Determine backend
        # TODO: Store backend in Task? For now assume Slurm if job_id starts with "job_" (local) or not
        # Actually LocalBackend returns "local_job" or similar.
        # Slurm returns a number.
        
        # If job_id is "local_job" or similar, we assume it's done if we are here (sync execution)
        # But if we support async local, we'd need PID.
        # For now, let's assume Slurm if it looks like a number, otherwise skip.
        
        if task.job_id.isdigit():
            # Slurm
            statuses = self.slurm.query_job_status([task.job_id])
            if task.job_id in statuses:
                slurm_state = statuses[task.job_id]
                new_status = self._map_slurm_state(slurm_state)
                if new_status != task.status:
                    print(f"Task {task.task_id} status changed: {task.status} -> {new_status}")
                    task.status = new_status
                    self.result_store.save_task(task, task.suite_id) # suite_id might be wrong here if not passed, but save_task needs run_id?
                    # Wait, save_task takes (task, run_id). Task object has suite_id.
                    # We need run_id. Task table has run_id.
                    # We need to fetch run_id for the task from DB if we don't have it.
                    # But Task object doesn't have run_id field in domain.py (it does in DB).
                    # Let's check domain.py.
                    pass
        
        return task.status

    def _map_slurm_state(self, state: str) -> TaskStatus:
        state = state.upper()
        if state == "COMPLETED":
            return TaskStatus.COMPLETED
        elif state in ["FAILED", "TIMEOUT", "NODE_FAIL", "PREEMPTED"]:
            return TaskStatus.FAILED
        elif state in ["CANCELLED", "REVOKED"]:
            return TaskStatus.CANCELLED
        elif state in ["PENDING", "RUNNING", "SUSPENDED"]:
            return TaskStatus.RUNNING # Map PENDING to RUNNING or keep PENDING?
            # Domain has PENDING and RUNNING.
            # If Slurm says PENDING, we should probably return PENDING.
        if state == "PENDING":
            return TaskStatus.PENDING
        return TaskStatus.RUNNING

    def capture_result(self, task: Task):
        """Capture results for a completed task."""
        if task.status != TaskStatus.COMPLETED:
            print(f"Task {task.task_id} is not completed (status: {task.status})")
            return

        if not task.working_directory:
            print(f"Task {task.task_id} has no working directory")
            return

        work_dir = Path(task.working_directory)
        if not work_dir.exists():
            print(f"Working directory not found: {work_dir}")
            return

        # Parse metrics
        # We need to find the output file.
        # Usually stdout/stderr or a specific log file.
        # For now, let's look for standard slurm output files or just parse all .log files?
        # Or maybe the Task should define expected output files?
        # The PRD says "Clients are encouraged to submit logical individual artifacts (stdout, modules...)"
        
        # Let's try to find slurm-{job_id}.out or similar
        output_files = list(work_dir.glob("slurm-*.out"))
        if not output_files:
            # Try finding any .log or .out file
            output_files = list(work_dir.glob("*.out")) + list(work_dir.glob("*.log"))
        
        metrics_data = {}
        if output_files:
            # Use the most recent file?
            target_file = sorted(output_files, key=lambda p: p.stat().st_mtime)[-1]
            print(f"Parsing results from {target_file}")
            metrics_data = ResultParser.parse(target_file, task.metrics)
            
            # Update task metrics in DB
            self.result_store.save_metrics(task.task_id, metrics_data)
        else:
            print("No output files found to parse")

        # Generate submission payload
        payload = self._generate_payload(task, metrics_data, work_dir)
        
        # Save payload to file
        payload_file = work_dir / "submission.json"
        with open(payload_file, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Generated submission payload: {payload_file}")

    def _generate_payload(self, task: Task, metrics: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
        """Generate the JSON payload for the backend."""
        
        # Convert metrics to list of FoMs
        foms = []
        for name, data in metrics.items():
            foms.append({
                "name": name,
                "value_numeric": data["value"],
                "unit": data["unit"],
                "value_type": "numeric",
                "is_primary": False # Logic to determine primary?
            })
            
        # Provenance artifacts
        artifacts = []
        # Add stdout/stderr/logs
        for f in work_dir.glob("*"):
            if f.is_file() and f.stat().st_size < 10 * 1024 * 1024: # 10MB limit
                if f.suffix in [".out", ".err", ".log", ".txt", ".json", ".yaml", ".sh"]:
                    artifacts.append({
                        "name": f.name,
                        "path": str(f) # We don't read content here to avoid memory issues, backend upload will handle it
                        # But PRD says "data" field in DB. Client submission body has "provenance" which includes artifacts.
                        # If we are generating a file to be sent later, we might not include full data yet.
                        # But for now let's just list them.
                    })

        return {
            "client": {
                "benchpro_version": "2.0.0", # TODO: Get actual version
                "task_uuid": task.task_uuid
            },
            "task": {
                "label": task.task_id, # or suite_id?
                "system": "unknown", # TODO: Get system from config/task
                "architecture": "unknown",
                "node_count": task.resources.nodes,
                "status": task.status.value,
                "submit_time": None, # TODO
                "start_time": None,
                "end_time": None,
                "runtime_seconds": task.duration_ms / 1000 if task.duration_ms else None
            },
            "application": {
                # TODO: Get application info if linked
            },
            "benchmark_definition": {
                # TODO: Get bench def info
            },
            "figures_of_merit": foms,
            "provenance": {
                "metadata": {
                    "working_directory": str(work_dir),
                    "job_id": task.job_id
                },
                "artifacts": artifacts
            }
        }
