import pytest
from benchpro.core.exceptions import (
    BenchProError,
    ConfigError,
    BuildError,
    TaskError,
    ValidationError,
    ResourceError
)

def test_base_exception():
    err = BenchProError("Something went wrong", exit_code=10)
    assert str(err) == "Something went wrong"
    assert err.message == "Something went wrong"
    assert err.exit_code == 10

def test_config_error():
    err = ConfigError("Invalid config")
    assert isinstance(err, BenchProError)
    assert err.exit_code == 1

def test_build_error():
    err = BuildError("Build failed")
    assert isinstance(err, BenchProError)
    assert err.exit_code == 2

def test_task_error():
    err = TaskError("Task failed")
    assert isinstance(err, BenchProError)
    assert err.exit_code == 3

def test_validation_error():
    err = ValidationError("Invalid input")
    assert isinstance(err, BenchProError)
    assert err.exit_code == 4

def test_resource_error():
    err = ResourceError("No resources")
    assert isinstance(err, BenchProError)
    assert err.exit_code == 5
