"""Template version management."""
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
from datetime import datetime


@dataclass(frozen=True)
class Version:
    """Version representation supporting both semantic versioning and date-based formats."""
    version_str: str
    
    # Support both semantic versioning and date-based versions
    SEMVER_PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)'
        r'\.(?P<minor>0|[1-9]\d*)'
        r'\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>[0-9A-Za-z-][0-9A-Za-z-\.]*)|(?!-))?'
        r'(?:\+(?P<build>[0-9A-Za-z-][0-9A-Za-z-\.]*)|(?!\+))?$'
    )
    
    DATE_PATTERN = re.compile(
        r'^(?P<day>\d{1,2})'
        r'(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        r'(?P<year>\d{4})$'
    )

    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse version string into Version object.
        
        Args:
            version_str: Version string in either semantic version or date format.
            
        Returns:
            Version object.
            
        Raises:
            ValueError: If version string is invalid.
        """
        # Try semantic version format
        if cls.SEMVER_PATTERN.match(version_str):
            return cls(version_str)
            
        # Try date format
        match = cls.DATE_PATTERN.match(version_str)
        if match:
            # Validate date components
            try:
                day = int(match.group('day'))
                month = match.group('month')
                year = int(match.group('year'))
                # Convert to datetime to validate date
                datetime.strptime(f"{day}{month}{year}", "%d%b%Y")
                return cls(version_str)
            except ValueError:
                pass
        
        raise ValueError(f"Invalid version format: {version_str}")

    def __str__(self) -> str:
        """Convert version to string."""
        return self.version_str

    def __lt__(self, other: Union['Version', str]) -> bool:
        """Compare versions.
        
        For semantic versions, follows semver comparison rules.
        For date versions, compares dates chronologically.
        Mixed comparisons treat semantic versions as older than date versions.
        """
        if isinstance(other, str):
            try:
                other = Version.parse(other)
            except ValueError:
                return NotImplemented
                
        if not isinstance(other, Version):
            return NotImplemented
            
        # If both are semantic versions
        self_semver = self.SEMVER_PATTERN.match(self.version_str)
        other_semver = self.SEMVER_PATTERN.match(other.version_str)
        if self_semver and other_semver:
            self_dict = self_semver.groupdict()
            other_dict = other_semver.groupdict()
            
            # Compare major.minor.patch
            for part in ['major', 'minor', 'patch']:
                self_num = int(self_dict[part])
                other_num = int(other_dict[part])
                if self_num != other_num:
                    return self_num < other_num
            
            # Handle prerelease
            self_pre = self_dict['prerelease'] or ''
            other_pre = other_dict['prerelease'] or ''
            if self_pre != other_pre:
                # No prerelease is greater than any prerelease
                if not self_pre:
                    return False
                if not other_pre:
                    return True
                return self_pre < other_pre
            
            return False
            
        # If both are date versions
        self_date = self.DATE_PATTERN.match(self.version_str)
        other_date = self.DATE_PATTERN.match(other.version_str)
        if self_date and other_date:
            self_dt = datetime.strptime(self.version_str, "%d%b%Y")
            other_dt = datetime.strptime(other.version_str, "%d%b%Y")
            return self_dt < other_dt
            
        # Mixed comparison - semantic versions are considered older than date versions
        if self_semver and other_date:
            return True
        if self_date and other_semver:
            return False
            
        # Fallback to string comparison
        return self.version_str < other.version_str

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if isinstance(other, str):
            try:
                other = Version.parse(other)
            except ValueError:
                return False
                
        if not isinstance(other, Version):
            return False
            
        return self.version_str == other.version_str


class VersionedTemplate:
    """Template with version information."""

    def __init__(self, name: str, version: Version, config: Dict[str, Any]):
        """Initialize versioned template.
        
        Args:
            name: Template name.
            version: Template version.
            config: Template configuration.
        """
        self.name = name
        self.version = version
        self.config = config

    @property
    def full_name(self) -> str:
        """Get full template name including version."""
        return f"{self.name}@{self.version}"

    def is_compatible_with(self, required_version: Version) -> bool:
        """Check if template is compatible with required version.
        
        Args:
            required_version: Required version.
            
        Returns:
            True if compatible, False otherwise.
        """
        # For now, versions must match exactly
        # In the future, we could implement more sophisticated compatibility rules
        return self.version == required_version 