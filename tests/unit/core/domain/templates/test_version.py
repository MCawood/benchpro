"""Tests for template version management."""
import pytest
from benchpro.core.domain.templates.version import Version, VersionedTemplate


def test_version_parsing():
    """Test parsing version strings."""
    # Test valid versions
    assert str(Version.parse("1.0.0")) == "1.0.0"
    assert str(Version.parse("2.1.0-alpha")) == "2.1.0-alpha"
    assert str(Version.parse("3.0.1+build.123")) == "3.0.1+build.123"
    assert str(Version.parse("4.2.3-beta+build.456")) == "4.2.3-beta+build.456"
    
    # Test invalid versions
    with pytest.raises(ValueError):
        Version.parse("invalid")
    with pytest.raises(ValueError):
        Version.parse("1.0")
    with pytest.raises(ValueError):
        Version.parse("1.0.0.0")
    with pytest.raises(ValueError):
        Version.parse("1.0.0-+")  # Empty prerelease and build identifiers


def test_version_comparison():
    """Test version comparison."""
    # Test major version comparison
    assert Version(1, 0, 0) < Version(2, 0, 0)
    assert Version(2, 0, 0) > Version(1, 0, 0)
    
    # Test minor version comparison
    assert Version(1, 0, 0) < Version(1, 1, 0)
    assert Version(1, 1, 0) > Version(1, 0, 0)
    
    # Test patch version comparison
    assert Version(1, 0, 0) < Version(1, 0, 1)
    assert Version(1, 0, 1) > Version(1, 0, 0)
    
    # Test prerelease comparison
    assert Version(1, 0, 0, "alpha") < Version(1, 0, 0)
    assert Version(1, 0, 0) > Version(1, 0, 0, "alpha")
    assert Version(1, 0, 0, "alpha") < Version(1, 0, 0, "beta")
    
    # Test equality
    assert Version(1, 0, 0) == Version(1, 0, 0)
    assert Version(1, 0, 0, "alpha") == Version(1, 0, 0, "alpha")
    assert Version(1, 0, 0, "alpha", "123") == Version(1, 0, 0, "alpha", "123")


def test_version_string_representation():
    """Test version string representation."""
    assert str(Version(1, 0, 0)) == "1.0.0"
    assert str(Version(2, 1, 0, "alpha")) == "2.1.0-alpha"
    assert str(Version(3, 0, 1, None, "build.123")) == "3.0.1+build.123"
    assert str(Version(4, 2, 3, "beta", "build.456")) == "4.2.3-beta+build.456"


def test_versioned_template():
    """Test versioned template functionality."""
    version = Version(1, 0, 0)
    config = {
        "name": "test",
        "type": "application",
        "build": {"compiler": "gcc"}
    }
    
    template = VersionedTemplate("test", version, config)
    assert template.name == "test"
    assert template.version == version
    assert template.config == config
    assert template.full_name == "test@1.0.0"
    
    # Test version compatibility
    assert template.is_compatible_with(Version(1, 0, 0))
    assert not template.is_compatible_with(Version(1, 0, 1))
    assert not template.is_compatible_with(Version(2, 0, 0)) 