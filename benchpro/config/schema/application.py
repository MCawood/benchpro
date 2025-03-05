"""
Application configuration schema for BenchPRO.

This module defines the schema for validating application configuration files.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator


class BuildConfig(BaseModel):
    """Build configuration for applications."""
    
    source: str = Field(..., description="Source file or directory for the application")
    compiler: str = Field(..., description="Compiler to use for building the application")
    flags: str = Field("", description="Compiler flags")
    output: str = Field(..., description="Output binary name")
    threads: int = Field(1, description="Number of threads to use for building")
    
    class Config:
        extra = "forbid"


class EnvironmentVariable(BaseModel):
    """Environment variable configuration."""
    
    name: str = Field(..., description="Name of the environment variable")
    value: str = Field(..., description="Value of the environment variable")
    
    class Config:
        extra = "forbid"


class EnvironmentConfig(BaseModel):
    """Environment configuration for applications."""
    
    modules: List[str] = Field(default_factory=list, description="List of modules to load")
    variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables to set")
    
    class Config:
        extra = "forbid"


class ExecutionConfig(BaseModel):
    """Execution configuration for applications."""
    
    type: str = Field("slurm", description="Execution type (slurm, local, etc.)")
    
    class Config:
        extra = "forbid"


class JobConfig(BaseModel):
    """Job configuration for applications."""
    
    scheduler: str = Field("slurm", description="Job scheduler to use")
    queue: Optional[str] = Field(None, description="Queue/partition to submit the job to")
    account: Optional[str] = Field(None, description="Account to charge for the job")
    nodes: int = Field(1, description="Number of nodes to request")
    tasks_per_node: int = Field(1, description="Number of tasks per node")
    time_limit: str = Field("01:00:00", description="Time limit for the job")
    
    class Config:
        extra = "allow"


class WorkspaceConfig(BaseModel):
    """Workspace configuration for applications."""
    
    source_dir: str = Field(..., description="Source directory for the application")
    build_dir: str = Field("build", description="Build directory for the application")
    logs_dir: str = Field("logs", description="Logs directory for the application")
    keep_source: bool = Field(True, description="Whether to keep source files after building")
    keep_build: bool = Field(True, description="Whether to keep build files after building")
    
    class Config:
        extra = "forbid"


class ApplicationSchema(BaseModel):
    """Schema for application configuration."""
    
    task_type: str = Field("application", description="Type of task")
    name: str = Field(..., description="Name of the application")
    version: str = Field("1.0", description="Version of the application")
    description: Optional[str] = Field(None, description="Description of the application")
    
    build: BuildConfig = Field(..., description="Build configuration")
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig, description="Environment configuration")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution configuration")
    job: JobConfig = Field(default_factory=JobConfig, description="Job configuration")
    workspace: WorkspaceConfig = Field(..., description="Workspace configuration")
    template: str = Field(..., description="Template to use for building the application")
    
    @validator("task_type")
    def validate_task_type(cls, v):
        """Validate that task_type is 'application'."""
        if v != "application":
            raise ValueError("task_type must be 'application'")
        return v
    
    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "task_type": "application",
                "name": "hello_world",
                "version": "1.0",
                "description": "Simple Hello World application",
                "build": {
                    "source": "hello_world.c",
                    "compiler": "gcc",
                    "flags": "-O2",
                    "output": "hello_world",
                    "threads": 4
                },
                "environment": {
                    "modules": ["gcc/11.2.0"],
                    "variables": {
                        "OMP_NUM_THREADS": "4",
                        "MKL_NUM_THREADS": "4"
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
                    "source_dir": "examples/input/hello_world",
                    "build_dir": "build",
                    "logs_dir": "logs",
                    "keep_source": True,
                    "keep_build": True
                },
                "template": "hello_world.j2"
            }
        } 