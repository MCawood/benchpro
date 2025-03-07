"""
Base schema for BenchPRO tasks.

This module defines the base schema for task configurations,
containing fields common to all task types.
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class BaseTaskSchema(BaseModel):
    """Base schema for task configurations."""
    
    task_type: str = Field(..., description="Type of task (application, benchmark)")
    name: str = Field(..., description="Name of the task")
    version: str = Field("1.0", description="Version of the task")
    description: Optional[str] = Field(None, description="Description of the task")
    
    model_config = ConfigDict(extra="allow") 