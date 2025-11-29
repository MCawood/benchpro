import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchpro.core.domain import Task, TaskStatus

class ResultStore:
    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Default to ~/.benchpro/results.db
            db_dir = Path.home() / ".benchpro"
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
                FOREIGN KEY(run_id) REFERENCES runs(run_id)
            )
        """)
        
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
                metadata JSON
            )
        """)
        
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
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (task_id, run_id, suite_id, status, exit_code, duration_ms, job_id, parameters, resources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                resources_json
            )
        )
        
        conn.commit()
        conn.close()

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
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO builds
            (build_id, code, version, system, build_label, build_timestamp, activation_script, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build.build_id,
                build.code,
                build.version,
                build.system,
                build.build_label,
                build.build_timestamp,
                build.activation_script,
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
            b.update(metadata)
            builds.append(b)
            
        conn.close()
        return builds

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
            tasks.append(task)
            
        conn.close()
        return tasks
