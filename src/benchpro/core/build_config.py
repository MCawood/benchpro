from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    name: str
    version: str
    source: str  # URL or path
    build_template: str  # Path to build script template
    
    # Build environment
    compiler: str = "gcc"
    mpi: str = "openmpi"
    modules: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    
    # Build options
    build_label: str = "default"
    prefix: Optional[str] = None  # Install prefix
    
    # Extra vars for template
    variables: Dict[str, Any] = Field(default_factory=dict)
