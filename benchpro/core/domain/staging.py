"""File staging domain model."""

from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class StagingMode(str, Enum):
    """File staging modes."""
    LOCAL_COPY = "local_copy"  # Copy file to destination
    SYMLINK = "symlink"        # Create symbolic link
    NONE = "none"             # No staging required


class StagingFile(BaseModel):
    """Represents a file that needs to be staged.
    
    Attributes:
        source: Path to source file
        destination: Path where file should be staged
        mode: How the file should be staged
        size: Optional size in bytes
        checksum: Optional file checksum
        last_modified: Optional last modified timestamp
    """
    source: Path = Field(..., description="Path to source file")
    destination: Path = Field(..., description="Path where file should be staged")
    mode: StagingMode = Field(
        default=StagingMode.LOCAL_COPY,
        description="How the file should be staged"
    )
    size: Optional[int] = Field(
        None,
        description="File size in bytes"
    )
    checksum: Optional[str] = Field(
        None,
        description="File checksum"
    )
    last_modified: Optional[float] = Field(
        None,
        description="Last modified timestamp"
    )

    def needs_staging(self) -> bool:
        """Check if file needs to be staged.
        
        Returns:
            True if file needs staging, False otherwise
        """
        if self.mode == StagingMode.NONE:
            return False
            
        # For now, always stage if mode is not NONE
        # Future: Could check if destination exists and is up to date
        return True

    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True 