"""Tests for template version management."""
import pytest
from datetime import datetime
from benchpro.core.domain.templates.version import Version, VersionedTemplate


def test_semver_parsing():
    """Test parsing semantic version strings."""
    # Test valid semantic versions
    assert str(Version.parse("1.0.0")) == "1.0.0"
    assert str(Version.parse("2.1.0-alpha")) == "2.1.0-alpha"
    assert str(Version.parse("3.0.1+build.123")) == "3.0.1+build.123"
    assert str(Version.parse("4.2.3-beta+build.456")) == "4.2.3-beta+build.456"
    
    # Test invalid semantic versions
    with pytest.raises(ValueError):
        Version.parse("1.0")
    with pytest.raises(ValueError):
        Version.parse("1.0.0.0")
    with pytest.raises(ValueError):
        Version.parse("1.0.0-+")  # Empty prerelease and build identifiers


def test_date_version_parsing():
    """Test parsing date-based version strings."""
    # Test valid date versions
    assert str(Version.parse("23Jun2022")) == "23Jun2022"
    assert str(Version.parse("1Jan2024")) == "1Jan2024"
    assert str(Version.parse("31Dec2023")) == "31Dec2023"
    
    # Test invalid date versions
    with pytest.raises(ValueError):
        Version.parse("32Jan2024")  # Invalid day
    with pytest.raises(ValueError):
        Version.parse("00Jan2024")  # Invalid day
    with pytest.raises(ValueError):
        Version.parse("15ABC2024")  # Invalid month
    with pytest.raises(ValueError):
        Version.parse("15Jan202")   # Invalid year format


def test_invalid_version_formats():
    """Test handling of invalid version formats."""
    invalid_versions = [
        "invalid",
        "v1.0.0",
        "1.0.0.0",
        "2024-01-15",
        "15/01/2024",
        "Jan152024",
    ]
    
    for version in invalid_versions:
        with pytest.raises(ValueError):
            Version.parse(version)


def test_semver_comparison():
    """Test comparison of semantic versions."""
    # Create version objects
    v1_0_0 = Version.parse("1.0.0")
    v2_0_0 = Version.parse("2.0.0")
    v2_1_0 = Version.parse("2.1.0")
    v2_1_1 = Version.parse("2.1.1")
    v2_1_0_alpha = Version.parse("2.1.0-alpha")
    v2_1_0_beta = Version.parse("2.1.0-beta")
    
    # Test ordering
    assert v1_0_0 < v2_0_0
    assert v2_0_0 < v2_1_0
    assert v2_1_0 < v2_1_1
    assert v2_1_0_alpha < v2_1_0
    assert v2_1_0_alpha < v2_1_0_beta
    
    # Test equality
    assert Version.parse("1.0.0") == Version.parse("1.0.0")
    assert Version.parse("2.1.0-alpha") == Version.parse("2.1.0-alpha")


def test_date_version_comparison():
    """Test comparison of date-based versions."""
    # Create version objects
    v1_jan = Version.parse("1Jan2024")
    v15_jan = Version.parse("15Jan2024")
    v1_feb = Version.parse("1Feb2024")
    v31_dec = Version.parse("31Dec2023")
    
    # Test ordering
    assert v31_dec < v1_jan
    assert v1_jan < v15_jan
    assert v15_jan < v1_feb
    
    # Test equality
    assert Version.parse("23Jun2022") == Version.parse("23Jun2022")
    assert Version.parse("1Jan2024") == Version.parse("1Jan2024")


def test_mixed_version_comparison():
    """Test comparison between semantic and date-based versions."""
    # Semantic versions are considered older than date versions
    semver = Version.parse("9.9.9")
    date_ver = Version.parse("1Jan2000")
    
    assert semver < date_ver
    assert not date_ver < semver
    assert not semver == date_ver


def test_versioned_template():
    """Test versioned template functionality."""
    # Test with semantic version
    semver = Version.parse("1.0.0")
    date_ver = Version.parse("23Jun2022")
    
    config = {
        "name": "test",
        "type": "application",
        "build": {"compiler": "gcc"}
    }
    
    # Test with semantic version
    template1 = VersionedTemplate("test", semver, config)
    assert template1.name == "test"
    assert template1.version == semver
    assert template1.config == config
    assert template1.full_name == "test@1.0.0"
    
    # Test with date version
    template2 = VersionedTemplate("test", date_ver, config)
    assert template2.name == "test"
    assert template2.version == date_ver
    assert template2.config == config
    assert template2.full_name == "test@23Jun2022"
    
    # Test version compatibility
    assert template1.is_compatible_with(Version.parse("1.0.0"))
    assert template2.is_compatible_with(Version.parse("23Jun2022"))
    assert not template1.is_compatible_with(Version.parse("2.0.0"))
    assert not template2.is_compatible_with(Version.parse("24Jun2022")) 