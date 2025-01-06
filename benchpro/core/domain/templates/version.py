"""Template version management."""
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class Version:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    VERSION_PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)'
        r'\.(?P<minor>0|[1-9]\d*)'
        r'\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>[0-9A-Za-z-][0-9A-Za-z-\.]*)|(?!-))?'
        r'(?:\+(?P<build>[0-9A-Za-z-][0-9A-Za-z-\.]*)|(?!\+))?$'
    )

    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse version string into Version object.
        
        Args:
            version_str: Version string in semantic version format.
            
        Returns:
            Version object.
            
        Raises:
            ValueError: If version string is invalid.
        """
        match = cls.VERSION_PATTERN.match(version_str)
        if not match:
            raise ValueError(
                f"Invalid version string: {version_str}. "
                "Must follow semantic versioning format (e.g., 1.0.0, 2.1.0-alpha)"
            )
        
        version_dict = match.groupdict()
        return cls(
            major=int(version_dict['major']),
            minor=int(version_dict['minor']),
            patch=int(version_dict['patch']),
            prerelease=version_dict['prerelease'] or None,
            build=version_dict['build'] or None
        )

    def __str__(self) -> str:
        """Convert version to string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: 'Version') -> bool:
        """Compare versions."""
        if not isinstance(other, Version):
            return NotImplemented
        
        # Compare major.minor.patch
        for s, o in zip(
            [self.major, self.minor, self.patch],
            [other.major, other.minor, other.patch]
        ):
            if s != o:
                return s < o
        
        # Handle prerelease
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease != other.prerelease:
            return (self.prerelease or "") < (other.prerelease or "")
        
        return False

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease and
            self.build == other.build
        )


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