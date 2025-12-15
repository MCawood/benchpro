import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchpro.core.domain import Task, TaskStatus
from benchpro.core.config import Config

class ResultStore:
    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Load full config to respect file settings
            try:
                config = Config.load()
                if config.benchpro.config_dir:
                     # expandvars handled by template engine usually, but safer to robustly expand
                     db_dir = Path(os.path.expandvars(config.benchpro.config_dir)).expanduser()
                else:
                     db_dir = Config.get_user_config_dir()
            except Exception as e:
                # Fallback if config load fails
                db_dir = Config.get_user_config_dir()
                
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "results.db"
            
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                suite_id TEXT,
                timestamp TEXT,
                system TEXT,
                metadata JSON
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                run_id TEXT,
                suite_id TEXT,
                status TEXT,
                exit_code INTEGER,
                duration_ms REAL,
                job_id TEXT,
                parameters JSON,
                resources JSON,
                metric_definitions JSON,
                working_directory TEXT,
                task_uuid TEXT,
                FOREIGN KEY(run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Migrate existing tasks table if needed
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN metric_definitions JSON")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN working_directory TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN task_uuid TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN script_file TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN output_file TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN error_file TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Builds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS builds (
                build_id TEXT PRIMARY KEY,
                code TEXT,
                version TEXT,
                system TEXT,
                build_label TEXT,
                build_timestamp TEXT,
                activation_script TEXT,
                status TEXT,
                job_id TEXT,
                modules JSON,
                metadata JSON
            )
        """)
        
        # Migrate builds table if needed
        try:
            cursor.execute("ALTER TABLE builds ADD COLUMN status TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE builds ADD COLUMN job_id TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE builds ADD COLUMN modules JSON")
        except sqlite3.OperationalError:
            pass
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                task_id TEXT,
                name TEXT,
                value REAL,
                unit TEXT,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id)
            )
        """)
        
        conn.commit()
        conn.close()

    def save_run(self, run_id: str, suite_id: str, system: str = "local", metadata: Dict[str, Any] = None):
        """Save a new run."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute(
            "INSERT OR REPLACE INTO runs (run_id, suite_id, timestamp, system, metadata) VALUES (?, ?, ?, ?, ?)",
            (run_id, suite_id, timestamp, system, metadata_json)
        )
        
        conn.commit()
        conn.close()

    def save_task(self, task: Task, run_id: str):
        """Save or update a task result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        params_json = json.dumps(task.parameters)
        resources_json = task.resources.model_dump_json()
        metric_defs_json = json.dumps([m.model_dump() for m in task.metrics])
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (task_id, run_id, suite_id, status, exit_code, duration_ms, job_id, parameters, resources, metric_definitions, working_directory, task_uuid, script_file, output_file, error_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                run_id,
                task.suite_id,
                task.status.value,
                task.exit_code,
                task.duration_ms,
                task.job_id,
                params_json,
                resources_json,
                metric_defs_json,
                task.working_directory,
                task.task_uuid,
                task.script_file,
                task.output_file,
                task.error_file
            )
        )
        
        conn.commit()
        conn.close()
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update the status of a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE task_id = ?",
            (status.value, task_id)
        )
        
        conn.commit()
        conn.close()

    def save_metrics(self, task_id: str, metrics: Dict[str, Any]):
        """Save extracted metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for name, data in metrics.items():
            cursor.execute(
                "INSERT OR REPLACE INTO metrics (task_id, name, value, unit) VALUES (?, ?, ?, ?)",
                (task_id, name, data["value"], data.get("unit"))
            )
            
        conn.commit()
        conn.close()

    def get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        """Get metrics for a task."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM metrics WHERE task_id = ?", (task_id,))
        rows = cursor.fetchall()
        
        metrics = {}
        for row in rows:
            metrics[row["name"]] = {
                "value": row["value"],
                "unit": row["unit"]
            }
            
        conn.close()
        return metrics
    def save_build(self, build: Any):
        """Save a build to the database."""
        # Avoid circular import
        from benchpro.core.domain import Build
        if not isinstance(build, Build):
            raise ValueError("Expected Build object")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata = {
            "compiler": build.compiler,
            "mpi": build.mpi,
            "flags": build.flags
        }
        metadata_json = json.dumps(metadata)
        
        modules_json = json.dumps(build.modules)
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO builds
            (build_id, code, version, system, build_label, build_timestamp, activation_script, status, job_id, modules, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build.build_id,
                build.code,
                build.version,
                build.system,
                build.build_label,
                build.build_timestamp,
                build.activation_script,
                build.status.value,
                build.job_id,
                modules_json,
                metadata_json
            )
        )
        
        conn.commit()
        conn.close()

    def get_builds(self) -> List[Dict[str, Any]]:
        """Get all builds."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM builds ORDER BY build_timestamp DESC")
        rows = cursor.fetchall()
        
        builds = []
        for row in rows:
            b = dict(row)
            metadata = json.loads(b.pop("metadata"))
            if b.get("modules"):
                b["modules"] = json.loads(b["modules"])
            b.update(metadata)
            builds.append(b)
            
        conn.close()
        return builds

    def delete_build(self, build_id: str) -> bool:
        """Delete a build by build_id. Returns True if deleted, False if not found."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM builds WHERE build_id = ?", (build_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted

    def delete_builds_by_code(self, code: str) -> int:
        """Delete all builds for a given code. Returns number of builds deleted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM builds WHERE code = ?", (code,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted_count

    def get_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent runs."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        runs = []
        for row in rows:
            run = dict(row)
            run["metadata"] = json.loads(run["metadata"])
            runs.append(run)
            
        conn.close()
        return runs

    def get_run_tasks(self, run_id: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific run."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE run_id = ?", (run_id,))
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = dict(row)
            task["parameters"] = json.loads(task["parameters"])
            task["resources"] = json.loads(task["resources"])
            if "metric_definitions" in task and task["metric_definitions"]:
                task["metric_definitions"] = json.loads(task["metric_definitions"])
            else:
                task["metric_definitions"] = []
            tasks.append(task)
            
        conn.close()
        return tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        
        task = None
        if row:
            task = dict(row)
            task["parameters"] = json.loads(task["parameters"])
            task["resources"] = json.loads(task["resources"])
            if "metric_definitions" in task and task["metric_definitions"]:
                task["metric_definitions"] = json.loads(task["metric_definitions"])
            else:
                task["metric_definitions"] = []
                
        conn.close()
        return task

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and its tasks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete tasks first (foreign key)
        cursor.execute("DELETE FROM tasks WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted

    def delete_empty_runs(self) -> int:
        """Delete runs with no tasks."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find runs with no tasks
        cursor.execute("""
            DELETE FROM runs 
            WHERE run_id NOT IN (SELECT DISTINCT run_id FROM tasks)
        """)
        
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted_count

    def clear_all_builds(self) -> int:
        """Delete all builds. Returns number of builds deleted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM builds")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted_count

    def clear_all_runs(self) -> int:
        """Delete all runs, tasks, and metrics. Returns number of runs deleted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics are deleted via cascade if foreign keys enabled, but sqlite default often off
        # Let's delete explicitly to be safe
        cursor.execute("DELETE FROM metrics")
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM runs")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted_count
