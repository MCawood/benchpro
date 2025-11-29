import pytest
from benchpro.core.domain import Build
from benchpro.core.resolver import Resolver

@pytest.fixture
def sample_builds():
    return [
        Build(
            build_id="b1", code="lammps", version="2023", system="sysA", 
            build_timestamp="2023-01-01T00:00:00", activation_script="source b1.sh"
        ),
        Build(
            build_id="b2", code="lammps", version="2023", system="sysA", 
            build_timestamp="2023-02-01T00:00:00", activation_script="source b2.sh"
        ),
        Build(
            build_id="b3", code="lammps", version="2022", system="sysA", 
            build_timestamp="2022-01-01T00:00:00", activation_script="source b3.sh"
        ),
        Build(
            build_id="b4", code="gromacs", version="2023", system="sysA", 
            build_timestamp="2023-01-01T00:00:00", activation_script="source b4.sh"
        ),
    ]

def test_resolve_exact(sample_builds):
    resolver = Resolver(sample_builds)
    build = resolver.resolve(code="lammps", version="2022")
    assert build.build_id == "b3"

def test_resolve_latest(sample_builds):
    resolver = Resolver(sample_builds)
    # Should pick b2 (newer than b1)
    build = resolver.resolve(code="lammps", version="2023")
    assert build.build_id == "b2"

def test_resolve_code_only(sample_builds):
    resolver = Resolver(sample_builds)
    # Should pick b2 (newest lammps overall)
    build = resolver.resolve(code="lammps")
    assert build.build_id == "b2"

def test_resolve_missing(sample_builds):
    resolver = Resolver(sample_builds)
    build = resolver.resolve(code="unknown")
    assert build is None
