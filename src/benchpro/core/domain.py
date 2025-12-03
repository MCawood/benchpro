from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MetricDefinition(BaseModel):
    name: str
    regex: str
    unit: Optional[str] = None


class ResourceRequest(BaseModel):
    nodes: int = 1
    ranks_per_node: int = 1
    threads: int = 1
    gpus: int = 0
    partition: Optional[str] = None
    time: Optional[str] = None
    account: Optional[str] = None
    qos: Optional[str] = None
    reservation: Optional[str] = None
    mode: str = "mpi"  # mpi, openmp, hybrid, serial


class Task(BaseModel):
    task_id: str
    suite_id: str
    benchmark_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    resources: ResourceRequest
    command: str
    env: Dict[str, str] = Field(default_factory=dict)
    requirements: Optional[Dict[str, str]] = None # code, version, etc.
    metrics: List[MetricDefinition] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    
    # Provenance
    task_uuid: str = Field(default_factory=lambda: str(uuid4()))
    working_directory: Optional[str] = None
    job_id: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None
    
    # Files
    script_file: Optional[str] = None
    output_file: Optional[str] = None
    error_file: Optional[str] = None


class Job(BaseModel):
    job_id: str
    scheduler_job_id: Optional[str] = None
    tasks: List[str] = Field(default_factory=list)  # List of task_ids
    script_content: str
    status: str = "pending"


class Build(BaseModel):
    build_id: str
    code: str
    version: str
    system: str = "default"
    build_label: str = "default"
    build_timestamp: str # ISO8601
    activation_script: str
    
    # Metadata
    compiler: Optional[str] = None
    mpi: Optional[str] = None
    flags: List[str] = Field(default_factory=list)
    
    def __lt__(self, other):
        # Sort by timestamp (newest first) for resolver
        # But Python sort is ascending, so we want newest (larger string) to be "smaller" 
        # if we want default sort to be newest-first? 
        # Actually, let's just stick to standard comparison and handle sorting in Resolver.
        return self.build_timestamp < other.build_timestamp

class Benchmark(BaseModel):
    benchmark_id: str
    suite_id: str
    tasks: List[Task] = Field(default_factory=list)
    job_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    template: Optional[str] = None

class Suite(BaseModel):
    suite_id: str
    name: str
    benchmarks: List[Benchmark] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    template: Optional[str] = None
