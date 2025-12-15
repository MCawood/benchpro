from benchpro.core.results import ResultStore
from benchpro.core.domain import TaskStatus, Build
from benchpro.core.scheduler import SlurmBackend, LocalBackend
from benchpro.core.config import Config
import sqlite3
import logging

logger = logging.getLogger(__name__)

class StatusChecker:
    def __init__(self, store=None, scheduler=None):
        self.store = store or ResultStore()
        config = Config.load()
        if scheduler:
            self.scheduler = scheduler
        elif config.system.scheduler == "slurm":
            self.scheduler = SlurmBackend()
        else:
            self.scheduler = LocalBackend()

    def sync_builds(self, build_ids=None):
        """
        Check and update status for specified build IDs or all active builds.
        Returns the number of builds updated.
        """
        if build_ids:
            # Fetch specific builds
            all_builds = self.store.get_builds() 
            # Optimization: get_builds fetches all, which might be slow. 
            # But currently we don't have get_build(id).
            targets = [b for b in all_builds if b["build_id"] in build_ids]
        else:
            # Fetch all active
            try:
                # We can optimize this by adding get_active_builds to ResultStore later
                all_builds = self.store.get_builds()
                targets = [b for b in all_builds if b.get("status") in [TaskStatus.RUNNING.value, TaskStatus.PENDING.value, "submitted"]]
            except Exception as e:
                logger.error(f"Failed to fetch builds: {e}")
                return 0

        if not targets:
            return 0

        updates = 0
        job_ids = [b["job_id"] for b in targets if b.get("job_id")]
        if not job_ids:
            return 0
            
        statuses = self.scheduler.query_job_status(job_ids)
        
        for build in targets:
            jid = build.get("job_id")
            if jid and jid in statuses:
                slurm_state = statuses[jid]
                new_status = self._map_slurm_state(slurm_state)
                
                current = build.get("status")
                # Normalize current status to enum value or string
                if hasattr(current, "value"):
                    current = current.value
                
                if new_status and new_status.value != current:
                    # Update status
                    # We need to manually update via SQL as ResultStore.save_build works but requires full object.
                    # Or we can use save_build.
                    try:
                        # Construct minimal Build object or fetch full?
                        # Using SQL is safer/faster for just status update
                        self._update_build_status(build["build_id"], new_status)
                        build["status"] = new_status.value # Update in-place for caller
                        updates += 1
                    except Exception as e:
                        logger.error(f"Failed to update build {build['build_id']}: {e}")
                        
        return updates

    def sync_tasks(self, task_ids=None):
        """
        Check and update status for specified task IDs or all active tasks.
        Returns the number of tasks updated.
        """
        targets = []
        if task_ids:
            for tid in task_ids:
                t = self.store.get_task(tid)
                if t:
                    targets.append(t)
        else:
            # Need a way to get active tasks efficiently.
            # ResultStore.get_runs() -> get_run_tasks is current way.
            # But that iterates runs.
            # Let's query DB directly for active tasks.
            targets = self._get_active_tasks_from_db()
            
        if not targets:
            return 0
            
        updates = 0
        job_ids = [t["job_id"] for t in targets if t.get("job_id")]
        if not job_ids:
            return 0
            
        statuses = self.scheduler.query_job_status(job_ids)
        
        for task in targets:
            jid = task.get("job_id")
            if jid and jid in statuses:
                slurm_state = statuses[jid]
                new_status = self._map_slurm_state(slurm_state)
                
                current = task.get("status")
                if hasattr(current, "value"):
                    current = current.value
                    
                if new_status and new_status.value != current:
                    try:
                        self.store.update_task_status(task["task_id"], new_status)
                        task["status"] = new_status.value
                        updates += 1
                    except Exception as e:
                         logger.error(f"Failed to update task {task['task_id']}: {e}")
                         
        return updates

    def _map_slurm_state(self, slurm_state):
        if slurm_state == "COMPLETED":
            return TaskStatus.COMPLETED
        elif slurm_state in ["FAILED", "TIMEOUT", "NODE_FAIL", "BOOT_FAIL"]:
            return TaskStatus.FAILED
        elif slurm_state.startswith("CANCELLED"):
            return TaskStatus.CANCELLED # If we have this enum?
        elif slurm_state == "PENDING":
            return TaskStatus.PENDING
        elif slurm_state == "RUNNING":
            return TaskStatus.RUNNING
        return None

    def _update_build_status(self, build_id, status):
        # Direct SQL update for build status
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE builds SET status=? WHERE build_id=?", (status.value, build_id))
        conn.commit()
        conn.close()

    def _get_active_tasks_from_db(self):
        # Query tasks in PENDING/RUNNING state
        conn = sqlite3.connect(self.store.db_path)
        # return rows as dicts
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Assume status column stores string values
        cursor.execute("SELECT * FROM tasks WHERE status IN (?, ?, ?)", 
                      (TaskStatus.PENDING.value, TaskStatus.RUNNING.value, "submitted"))
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            tasks.append(dict(row))
        conn.close()
        return tasks
