"""
Benchmark configuration schema for BenchPRO.

This module defines the schema for validating benchmark configuration files.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator


class RunConfig(BaseModel):
    """Run configuration for benchmarks."""
    
    application: str = Field(..., description="Application to run")
    arguments: str = Field("", description="Command-line arguments for the application")
    input_files: List[str] = Field(default_factory=list, description="Input files for the benchmark")
    output_files: List[str] = Field(default_factory=list, description="Output files to capture")
    threads: int = Field(1, description="Number of threads to use for the benchmark")
    
    class Config:
        extra = "forbid"


class EnvironmentConfig(BaseModel):
    """Environment configuration for benchmarks."""
    
    modules: List[str] = Field(default_factory=list, description="List of modules to load")
    variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables to set")
    
    class Config:
        extra = "forbid"


class ExecutionConfig(BaseModel):
    """Execution configuration for benchmarks."""
    
    type: str = Field("slurm", description="Execution type (slurm, local, etc.)")
    
    class Config:
        extra = "forbid"


class JobConfig(BaseModel):
    """Job configuration for benchmarks."""
    
    scheduler: str = Field("slurm", description="Job scheduler to use")
    queue: Optional[str] = Field(None, description="Queue/partition to submit the job to")
    account: Optional[str] = Field(None, description="Account to charge for the job")
    nodes: int = Field(1, description="Number of nodes to request")
    tasks_per_node: int = Field(1, description="Number of tasks per node")
    time_limit: str = Field("01:00:00", description="Time limit for the job")
    
    class Config:
        extra = "allow"


class WorkspaceConfig(BaseModel):
    """Workspace configuration for benchmarks."""
    
    input_dir: str = Field(..., description="Input directory for the benchmark")
    output_dir: str = Field("output", description="Output directory for the benchmark")
    logs_dir: str = Field("logs", description="Logs directory for the benchmark")
    keep_input: bool = Field(True, description="Whether to keep input files after running")
    keep_output: bool = Field(True, description="Whether to keep output files after running")
    
    class Config:
        extra = "forbid"


class ExtractionConfig(BaseModel):
    """Configuration for result extraction."""
    
    method: str = Field(..., description="Method for extracting results (regex, command)")
    pattern: Optional[str] = Field(None, description="Pattern for regex extraction")
    command: Optional[str] = Field(None, description="Command for command-based extraction")
    metric: str = Field(..., description="Name of the metric to extract")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    
    class Config:
        extra = "forbid"


class ResultConfig(BaseModel):
    """Result configuration for benchmarks."""
    
    # Legacy fields
    metrics: List[str] = Field(default_factory=list, description="Metrics to capture from the benchmark")
    parser: Optional[str] = Field(None, description="Parser to use for extracting metrics")
    
    # New extraction fields
    extraction: Optional[ExtractionConfig] = Field(None, description="Configuration for result extraction")
    output_format: str = Field("json", description="Format for storing benchmark results")
    
    class Config:
        extra = "forbid"


class BenchmarkSchema(BaseModel):
    """Schema for benchmark configuration."""
    
    task_type: str = Field("benchmark", description="Type of task")
    name: str = Field(..., description="Name of the benchmark")
    version: str = Field("1.0", description="Version of the benchmark")
    description: Optional[str] = Field(None, description="Description of the benchmark")
    
    run: RunConfig = Field(..., description="Run configuration")
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig, description="Environment configuration")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution configuration")
    job: JobConfig = Field(default_factory=JobConfig, description="Job configuration")
    workspace: WorkspaceConfig = Field(..., description="Workspace configuration")
    results: ResultConfig = Field(default_factory=ResultConfig, description="Result configuration")
    template: str = Field(..., description="Template to use for running the benchmark")
    
    @validator("task_type")
    def validate_task_type(cls, v):
        """Validate that task_type is 'benchmark'."""
        if v != "benchmark":
            raise ValueError("task_type must be 'benchmark'")
        return v
    
    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "task_type": "benchmark",
                "name": "hello_world_bench",
                "version": "1.0",
                "description": "Simple Hello World benchmark",
                "run": {
                    "application": "hello_world",
                    "arguments": "--verbose",
                    "input_files": ["input.dat"],
                    "output_files": ["output.dat"],
                    "threads": 1
                },
                "environment": {
                    "modules": ["gcc/11.2.0"],
                    "variables": {
                        "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1"
                    }
                },
                "execution": {
                    "type": "slurm"
                },
                "job": {
                    "scheduler": "slurm",
                    "queue": "compute",
                    "nodes": 1,
                    "tasks_per_node": 1,
                    "time_limit": "00:10:00"
                },
                "workspace": {
                    "input_dir": "examples/input/hello_world_bench",
                    "output_dir": "output",
                    "logs_dir": "logs",
                    "keep_input": True,
                    "keep_output": True
                },
                "results": {
                    "extraction": {
                        "method": "regex",
                        "pattern": "runtime",
                        "metric": "runtime",
                        "unit": "seconds"
                    },
                    "output_format": "json"
                },
                "template": "hello_world_bench.j2"
            }
        } 