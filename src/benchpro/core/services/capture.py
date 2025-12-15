import json
import os
import gzip
import base64
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from benchpro import __version__
from benchpro.core.domain import Task, TaskStatus
from benchpro.core.results import ResultStore
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.parser import ResultParser
from benchpro.core.config import Config

class CaptureService:
    def __init__(self, result_store: ResultStore = None, config: Config = None):
        self.result_store = result_store or ResultStore()
        self.slurm = SlurmBackend()
        self.local = LocalBackend()
        self.config = config or Config.load()

    def check_task_status(self, task: Task) -> TaskStatus:
        """Check and update task status."""
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return task.status

        if not task.job_id:
            return task.status

        if task.job_id.isdigit():
            # Slurm
            statuses = self.slurm.query_job_status([task.job_id])
            if task.job_id in statuses:
                slurm_state = statuses[task.job_id]
                new_status = self._map_slurm_state(slurm_state)
                if new_status != task.status:
                    print(f"Task {task.task_id} status changed: {task.status} -> {new_status}")
                    task.status = new_status
                    self.result_store.update_task_status(task.task_id, new_status)
        
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
            return TaskStatus.RUNNING 
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
        output_files = list(work_dir.glob("slurm-*.out"))
        if not output_files:
            output_files = list(work_dir.glob("*.out")) + list(work_dir.glob("*.log"))
        
        metrics_data = {}
        if output_files:
            target_file = sorted(output_files, key=lambda p: p.stat().st_mtime)[-1]
            print(f"Parsing results from {target_file}")
            metrics_data = ResultParser.parse(target_file, task.metrics)
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

        # Submit if configured
        if self.config.system.results_server_url and self.config.system.api_token:
            try:
                self.submit_result(payload)
            except Exception as e:
                print(f"Failed to submit result: {e}")
        else:
            print("Results server not configured, skipping submission")

    def _generate_payload(self, task: Task, metrics: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
        """Generate the JSON payload for the backend."""
        
        # Convert metrics to list of FoMs
        foms = []
        for name, data in metrics.items():
            fom = {
                "name": name,
                "unit": data.get("unit"),
                "is_primary": False 
            }
            # Check if value is numeric
            try:
                val = float(data["value"])
                fom["value_numeric"] = val
            except (ValueError, TypeError):
                fom["value_text"] = str(data["value"])
            
            foms.append(fom)
            
        # Provenance artifacts
        artifacts = []
        for f in work_dir.glob("*"):
            if f.is_file() and f.stat().st_size < 5 * 1024 * 1024: # 5MB limit per artifact
                if f.suffix in [".out", ".err", ".log", ".txt", ".json", ".yaml", ".sh"]:
                    artifacts.append(self._encode_artifact(f))

        # Metadata
        metadata = [
            {"key": "working_directory", "value_text": str(work_dir)},
            {"key": "job_id", "value_text": str(task.job_id)}
        ]
        
        # Add environment variables if captured (not currently stored in Task, but maybe in env file?)
        # For now, just basic metadata

        return {
            "client": {
                "benchpro_version": __version__,
                "task_uuid": task.task_uuid,
                "submit_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "task": {
                "label": task.task_id, 
                "system": self.config.system.name,
                "status": task.status.value,
                "submit_time": datetime.now(timezone.utc).isoformat(), # We don't track submit time yet
                "node_count": task.resources.nodes,
                "runtime_seconds": task.duration_ms / 1000 if task.duration_ms else None
            },
            "figures_of_merit": foms,
            "provenance": {
                "metadata": metadata,
                "artifacts": artifacts
            }
        }

    def _encode_artifact(self, file_path: Path) -> Dict[str, Any]:
        """Encode a file as a provenance artifact."""
        content = file_path.read_bytes()
        
        # Always gzip for now if > 1KB? Spec says optional.
        # Let's gzip if > 1KB
        if len(content) > 1024:
            compressed = gzip.compress(content)
            return {
                "name": file_path.name,
                "content_type": "text/plain", # TODO: Detect type
                "encoding": "gzip",
                "data": base64.b64encode(compressed).decode('ascii')
            }
        else:
             return {
                "name": file_path.name,
                "content_type": "text/plain",
                "encoding": "raw",
                "data": base64.b64encode(content).decode('ascii') # Spec says base64 encoded content
            }

    def submit_result(self, payload: Dict[str, Any]):
        """Submit result to the server."""
        url = f"{self.config.system.results_server_url}/api/v1/task_runs"
        token = self.config.system.api_token
        
        print(f"Submitting result to {url}...")
        
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        
        if response.status_code == 201:
            data = response.json()
            if data.get('duplicate'):
                print(f"Task already submitted (ID: {data.get('task_run_id')})")
            else:
                print(f"Task submitted successfully (ID: {data.get('task_run_id')})")
        else:
            print(f"Submission failed: {response.status_code} - {response.text}")
            response.raise_for_status()
