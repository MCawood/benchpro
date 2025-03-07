"""
Global configuration schema for BenchPRO.

This module defines the schema for validating global configuration settings
that apply across the entire application rather than being specific to tasks.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    
    level: str = Field("INFO", description="Logging level (INFO, DEBUG, WARNING, ERROR, CRITICAL)")
    file: str = Field("benchpro.log", description="Log file name")
    
    model_config = ConfigDict(extra="allow")


class PathsConfig(BaseModel):
    """Path configuration settings."""
    
    modules: Optional[str] = Field(None, description="Path to modules directory")
    scratch: Optional[str] = Field("/tmp/benchpro", description="Path to scratch directory")
    
    model_config = ConfigDict(extra="allow")


class GlobalWorkspaceConfig(BaseModel):
    """Global workspace configuration settings."""
    
    base_input_dir: str = Field("examples/input", description="Base input directory")
    base_output_dir: str = Field("examples/output", description="Base output directory")
    keep_source_files: bool = Field(True, description="Whether to keep source files")
    keep_build_files: bool = Field(True, description="Whether to keep build files")
    keep_logs: bool = Field(True, description="Whether to keep log files")
    
    model_config = ConfigDict(extra="allow")


class GlobalConfigSchema(BaseModel):
    """Schema for global configuration settings."""
    
    logging: Optional[LoggingConfig] = Field(default_factory=LoggingConfig, description="Logging configuration")
    paths: Optional[PathsConfig] = Field(default_factory=PathsConfig, description="Path configuration")
    workspace: Optional[GlobalWorkspaceConfig] = Field(default_factory=GlobalWorkspaceConfig, description="Global workspace configuration")
    
    model_config = ConfigDict(extra="allow") 