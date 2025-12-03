#!/usr/bin/env python3
"""Seed data generation script for BenchPRO Results Server.

Usage:
    cd backend
    source venv/bin/activate
    python ../seed/seed_data.py
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (
    Application,
    BenchmarkDefinition,
    FigureOfMerit,
    FomValueType,
    ProvenanceArtifact,
    ArtifactEncoding,
    SavedView,
    SavedViewVisibility,
    TaskProvenanceMetadata,
    TaskRun,
    TaskStatus,
    User,
    UserRole,
)

settings = get_settings()

# Sample data
SYSTEMS = ["stampede3", "frontera", "lonestar6", "vista"]
ARCHITECTURES = ["intel_spr", "intel_icx", "amd_milan", "nvidia_a100"]
BENCHMARKS = [
    ("lammps_ljmelt", "LAMMPS Lennard-Jones melt benchmark", "tau_day"),
    ("hpl", "High Performance Linpack", "gflops"),
    ("stream", "STREAM memory bandwidth", "copy_bandwidth"),
    ("ior", "IOR parallel I/O benchmark", "write_bandwidth"),
    ("osu_latency", "OSU MPI latency benchmark", "latency_us"),
]
APPLICATIONS = [
    ("lammps", ["23Jun2022", "29Aug2024"]),
    ("hpl", ["2.3", "2.3.1"]),
    ("stream", ["5.10"]),
    ("ior", ["3.3.0", "4.0.0"]),
    ("osu-micro-benchmarks", ["7.0", "7.2"]),
]
MODULES_BY_SYSTEM = {
    "stampede3": ["intel/23.1", "impi/21.9", "phdf5/1.14"],
    "frontera": ["intel/19.1", "impi/19.0", "phdf5/1.12"],
    "lonestar6": ["gcc/12.2", "mvapich2/2.3", "phdf5/1.14"],
    "vista": ["nvhpc/23.9", "cuda/12.2", "openmpi/4.1"],
}


async def create_seed_data():
    """Generate and insert seed data."""
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Check if seed data already exists
        from sqlalchemy import select, func
        result = await db.execute(select(func.count(TaskRun.id)))
        existing_count = result.scalar_one()
        if existing_count >= 1:
            print(f"Database already has {existing_count} task run(s). Skipping seed data.")
            print("To re-seed, clear the database first:")
            print("  cd backend && alembic downgrade base && alembic upgrade head")
            return

        print("Creating seed data...")

        # Create or get users
        print("  Creating users...")
        users = []
        from sqlalchemy import select
        for i, (ext_id, name, role) in enumerate([
            ("dev_user", "Development User", UserRole.ADMIN),
            ("alice", "Alice Smith", UserRole.USER),
            ("bob", "Bob Johnson", UserRole.USER),
        ]):
            # Check if user exists
            result = await db.execute(
                select(User).where(User.external_id == ext_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    external_id=ext_id,
                    display_name=name,
                    email=f"{ext_id}@example.com",
                    role=role,
                )
                db.add(user)
            users.append(user)
        await db.flush()

        # Create applications
        print("  Creating applications...")
        applications = []
        for app_label, versions in APPLICATIONS:
            for version in versions:
                for system in SYSTEMS[:2]:  # Just a couple systems per app
                    app = Application(
                        label=app_label,
                        version=version,
                        system=system,
                        architecture=random.choice(ARCHITECTURES),
                        modules=MODULES_BY_SYSTEM.get(system, []),
                        benchpro_version="2.0.0",
                        build_user=random.choice(users).external_id,
                        build_time=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
                    )
                    db.add(app)
                    applications.append(app)
        await db.flush()

        # Create benchmark definitions
        print("  Creating benchmark definitions...")
        benchmarks = []
        for label, desc, primary_fom in BENCHMARKS:
            bench = BenchmarkDefinition(
                label=label,
                description=desc,
                default_primary_fom_name=primary_fom,
            )
            db.add(bench)
            benchmarks.append(bench)
        await db.flush()

        # Create task runs with FoMs and provenance
        print("  Creating task runs...")
        statuses = [TaskStatus.COMPLETED] * 8 + [TaskStatus.FAILED, TaskStatus.PARTIAL]

        for i in range(50):
            system = random.choice(SYSTEMS)
            bench = random.choice(benchmarks)
            app = random.choice([a for a in applications if a.label in bench.label] or applications)
            user = random.choice(users)
            node_count = random.choice([1, 2, 4, 8, 16, 32, 64, 128])
            status = random.choice(statuses)

            submit_time = datetime.now(timezone.utc) - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
            )
            runtime = random.uniform(30, 3600) if status == TaskStatus.COMPLETED else None

            task = TaskRun(
                user_id=user.id,
                task_uuid=uuid4(),
                label=f"{bench.label}_{node_count}n_{i}",
                benchmark_definition_id=bench.id,
                application_id=app.id,
                system=system,
                architecture=app.architecture,
                node_count=node_count,
                runtime_seconds=runtime,
                status=status,
                submit_time=submit_time,
                start_time=submit_time + timedelta(minutes=random.randint(1, 30)) if status != TaskStatus.FAILED else None,
                end_time=submit_time + timedelta(seconds=runtime + 60) if runtime else None,
                benchpro_version="2.0.0",
            )
            db.add(task)
            await db.flush()

            # Add FoMs
            if status == TaskStatus.COMPLETED:
                primary_value = random.uniform(100, 10000) * node_count
                fom = FigureOfMerit(
                    task_run_id=task.id,
                    name=bench.default_primary_fom_name or "performance",
                    value_numeric=primary_value,
                    value_type=FomValueType.NUMERIC,
                    unit="units",
                    is_primary=True,
                )
                db.add(fom)

                # Add secondary FoM
                fom2 = FigureOfMerit(
                    task_run_id=task.id,
                    name="memory_used",
                    value_numeric=random.uniform(1, 128) * node_count,
                    value_type=FomValueType.NUMERIC,
                    unit="GB",
                    is_primary=False,
                )
                db.add(fom2)

            # Add provenance metadata
            meta1 = TaskProvenanceMetadata(
                task_run_id=task.id,
                key="modules",
                value_json=MODULES_BY_SYSTEM.get(system, []),
            )
            db.add(meta1)

            meta2 = TaskProvenanceMetadata(
                task_run_id=task.id,
                key="scheduler",
                value_json={
                    "type": "slurm",
                    "job_id": str(random.randint(100000, 999999)),
                    "queue": "normal",
                    "nodes": node_count,
                },
            )
            db.add(meta2)

            # Add sample artifact (stdout)
            stdout_content = f"""
=== BenchPRO Task Output ===
Task: {task.label}
System: {system}
Nodes: {node_count}
Status: {status.value}

Running benchmark...
{'Benchmark completed successfully.' if status == TaskStatus.COMPLETED else 'Error occurred.'}

Performance: {primary_value if status == TaskStatus.COMPLETED else 'N/A'}
""".encode('utf-8')

            artifact = ProvenanceArtifact(
                task_run_id=task.id,
                name="stdout",
                content_type="text/plain",
                encoding=ArtifactEncoding.RAW,
                size_bytes=len(stdout_content),
                data=stdout_content,
            )
            db.add(artifact)

        # Create saved views
        print("  Creating saved views...")
        views = [
            ("LAMMPS Performance", "LAMMPS benchmark results", {"system": ["stampede3"]}, "public"),
            ("Failed Runs", "All failed task runs", {"status": "failed"}, "public"),
            ("Recent Large Jobs", "Jobs with 64+ nodes", {"node_count_min": 64}, "private"),
        ]
        for name, desc, filters, visibility in views:
            view = SavedView(
                owner_user_id=users[0].id,
                name=name,
                description=desc,
                config={"filters": filters, "chart_type": "scatter"},
                visibility=SavedViewVisibility.PUBLIC if visibility == "public" else SavedViewVisibility.PRIVATE,
            )
            db.add(view)

        await db.commit()
        print("Seed data created successfully!")
        print(f"  - {len(users)} users")
        print(f"  - {len(applications)} applications")
        print(f"  - {len(benchmarks)} benchmark definitions")
        print(f"  - 50 task runs with FoMs and provenance")
        print(f"  - {len(views)} saved views")


if __name__ == "__main__":
    asyncio.run(create_seed_data())

