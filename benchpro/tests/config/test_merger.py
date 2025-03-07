"""
Tests for the HierarchicalConfigMerger class.
"""

import pytest
from copy import deepcopy

from benchpro.config.merger import HierarchicalConfigMerger


@pytest.fixture
def config_merger():
    """Create a HierarchicalConfigMerger for testing."""
    return HierarchicalConfigMerger()


def test_merge_simple(config_merger):
    """Test merging two simple configurations."""
    # Create base and override configurations
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    
    # Merge the configurations
    result = config_merger.merge(base, override)
    
    # Check the result
    assert result["a"] == 1
    assert result["b"] == 3
    assert result["c"] == 4
    
    # Check that the original configurations were not modified
    assert base == {"a": 1, "b": 2}
    assert override == {"b": 3, "c": 4}


def test_merge_nested(config_merger):
    """Test merging configurations with nested dictionaries."""
    # Create base and override configurations
    base = {
        "a": 1,
        "b": {
            "c": 2,
            "d": 3
        }
    }
    override = {
        "b": {
            "d": 4,
            "e": 5
        },
        "f": 6
    }
    
    # Merge the configurations
    result = config_merger.merge(base, override)
    
    # Check the result
    assert result["a"] == 1
    assert result["b"]["c"] == 2
    assert result["b"]["d"] == 4
    assert result["b"]["e"] == 5
    assert result["f"] == 6
    
    # Check that the original configurations were not modified
    assert base == {"a": 1, "b": {"c": 2, "d": 3}}
    assert override == {"b": {"d": 4, "e": 5}, "f": 6}


def test_merge_lists(config_merger):
    """Test merging configurations with lists."""
    # Create base and override configurations
    base = {
        "a": [1, 2, 3],
        "b": {"c": [4, 5, 6]}
    }
    override = {
        "a": [7, 8, 9],
        "b": {"c": [10, 11, 12]}
    }
    
    # Merge the configurations
    result = config_merger.merge(base, override)
    
    # Check the result
    assert result["a"] == [7, 8, 9]
    assert result["b"]["c"] == [10, 11, 12]
    
    # Check that the original configurations were not modified
    assert base == {"a": [1, 2, 3], "b": {"c": [4, 5, 6]}}
    assert override == {"a": [7, 8, 9], "b": {"c": [10, 11, 12]}}


def test_merge_all_empty(config_merger):
    """Test merging an empty list of configurations."""
    # Merge an empty list
    result = config_merger.merge_all([])
    
    # Check the result
    assert result == {}


def test_merge_all_single(config_merger):
    """Test merging a list with a single configuration."""
    # Create a configuration
    config = {"a": 1, "b": 2}
    
    # Merge the list
    result = config_merger.merge_all([config])
    
    # Check the result
    assert result == config
    assert result is not config  # Should be a copy


def test_merge_all_multiple(config_merger):
    """Test merging multiple configurations."""
    # Create configurations
    config1 = {"a": 1, "b": 2}
    config2 = {"b": 3, "c": 4}
    config3 = {"c": 5, "d": 6}
    
    # Merge the configurations
    result = config_merger.merge_all([config1, config2, config3])
    
    # Check the result
    assert result["a"] == 1
    assert result["b"] == 3
    assert result["c"] == 5
    assert result["d"] == 6
    
    # Check that the original configurations were not modified
    assert config1 == {"a": 1, "b": 2}
    assert config2 == {"b": 3, "c": 4}
    assert config3 == {"c": 5, "d": 6}


def test_merge_all_nested(config_merger):
    """Test merging multiple configurations with nested dictionaries."""
    # Create configurations
    config1 = {
        "a": 1,
        "b": {
            "c": 2,
            "d": 3
        }
    }
    config2 = {
        "b": {
            "d": 4,
            "e": 5
        }
    }
    config3 = {
        "b": {
            "e": 6,
            "f": 7
        },
        "g": 8
    }
    
    # Merge the configurations
    result = config_merger.merge_all([config1, config2, config3])
    
    # Check the result
    assert result["a"] == 1
    assert result["b"]["c"] == 2
    assert result["b"]["d"] == 4
    assert result["b"]["e"] == 6
    assert result["b"]["f"] == 7
    assert result["g"] == 8
    
    # Check that the original configurations were not modified
    assert config1 == {"a": 1, "b": {"c": 2, "d": 3}}
    assert config2 == {"b": {"d": 4, "e": 5}}
    assert config3 == {"b": {"e": 6, "f": 7}, "g": 8} 