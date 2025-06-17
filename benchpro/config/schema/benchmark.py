"""
Benchmark configuration schema for BenchPRO.

This module defines the schema for validating benchmark configuration files.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator

from benchpro.config.schema.base import BaseTaskSchema


class RunConfig(BaseModel):
    """Run configuration for benchmarks."""
    
    executable: str = Field(..., description="Executable to run for the benchmark")
    arguments: str = Field("", description="Arguments to pass to the executable")
    input_files: List[str] = Field(default_factory=list, description="List of input files")
    output_files: List[str] = Field(default_factory=list, description="List of output files")
    threads: int = Field(1, description="Number of threads to use for running")
    
    model_config = ConfigDict(extra="allow")


class RequirementsConfig(BaseModel):
    """Requirements configuration for benchmarks."""
    
    application: str = Field(..., description="Required application name")
    version: str = Field("latest", description="Required application version")
    
    model_config = ConfigDict(extra="allow")


class EnvironmentConfig(BaseModel):
    """Environment configuration for benchmarks."""
    
    modules: List[str] = Field(default_factory=list, description="List of modules to load")
    variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables to set")
    
    model_config = ConfigDict(extra="allow")


class ExecutionConfig(BaseModel):
    """Execution configuration for benchmarks."""
    
    type: str = Field("local", description="Execution type (local, sched, etc.)")
    
    model_config = ConfigDict(extra="allow")


class JobConfig(BaseModel):
    """Job configuration for benchmarks."""
    
    scheduler: str = Field("slurm", description="Job scheduler to use (controls script directives)")
    queue: Optional[str] = Field(None, description="Queue/partition to submit the job to")
    account: Optional[str] = Field(None, description="Account to charge for the job")
    nodes: int = Field(1, description="Number of nodes to request")
    tasks_per_node: int = Field(1, description="Number of tasks per node")
    time_limit: str = Field("01:00:00", description="Time limit for the job")
    
    model_config = ConfigDict(extra="allow")


class WorkspaceConfig(BaseModel):
    """Workspace configuration for benchmarks."""
    
    input_dir: str = Field(..., description="Input directory for the benchmark")
    output_dir: str = Field("output", description="Output directory for the benchmark")
    logs_dir: str = Field("logs", description="Logs directory for the benchmark")
    keep_input: bool = Field(True, description="Whether to keep input files after running")
    keep_output: bool = Field(True, description="Whether to keep output files after running")
    
    model_config = ConfigDict(extra="allow")


class ExtractionConfig(BaseModel):
    """Configuration for result extraction."""
    
    method: str = Field(..., description="Method for extracting results (regex, command)")
    pattern: Optional[str] = Field(None, description="Pattern for regex extraction")
    command: Optional[str] = Field(None, description="Command for command-based extraction")
    metric: str = Field(..., description="Name of the metric to extract")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    
    model_config = ConfigDict(extra="allow")


class ResultConfig(BaseModel):
    """Result configuration for benchmarks."""
    
    # Legacy fields
    metrics: List[str] = Field(default_factory=list, description="Metrics to capture from the benchmark")
    parser: Optional[str] = Field(None, description="Parser to use for extracting metrics")
    
    # New extraction fields
    extraction: Optional[ExtractionConfig] = Field(None, description="Configuration for result extraction")
    output_format: str = Field("json", description="Format for storing benchmark results")
    
    model_config = ConfigDict(extra="allow")


class BenchmarkSchema(BaseTaskSchema):
    """Schema for benchmark configuration."""
    
    run: RunConfig = Field(..., description="Run configuration")
    requirements: Optional[RequirementsConfig] = Field(None, description="Requirements configuration")
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig, description="Environment configuration")
    execution: Optional[ExecutionConfig] = Field(default_factory=ExecutionConfig, description="Execution configuration")
    job: JobConfig = Field(default_factory=JobConfig, description="Job configuration")
    workspace: WorkspaceConfig = Field(..., description="Workspace configuration")
    results: Optional[ResultConfig] = Field(None, description="Results configuration")
    template: str = Field(..., description="Template to use for running the benchmark")
    
    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v):
        """Validate that task_type is 'benchmark'."""
        if v != "benchmark":
            raise ValueError("task_type must be 'benchmark'")
        return v
    
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "task_type": "benchmark",
                "name": "linpack",
                "version": "1.0",
                "description": "LINPACK benchmark",
                "run": {
                    "executable": "linpack",
                    "arguments": "-n 1000",
                    "input_files": ["input.dat"],
                    "output_files": ["output.dat"],
                    "threads": 4
                },
                "requirements": {
                    "application": "linpack",
                    "version": "1.0"
                },
                "environment": {
                    "modules": ["intel/24.0", "impi/21.11"],
                    "variables": {
                        "OMP_NUM_THREADS": "4",
                        "MKL_NUM_THREADS": "4"
                    }
                },
                "execution": {
                    "type": "local"
                },
                "job": {
                    "scheduler": "slurm",
                    "queue": "compute",
                    "nodes": 1,
                    "tasks_per_node": 1,
                    "time_limit": "00:30:00"
                },
                "workspace": {
                    "input_dir": "examples/input/linpack",
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
                "template": "linpack.j2"
            }
        }
    ) 