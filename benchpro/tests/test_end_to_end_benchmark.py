import os
import yaml
import pytest
from benchpro.config.config_manager import ConfigManager
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.executor.task_factory import TaskFactory
from benchpro.registry.registry_manager import RegistryManager
from benchpro.workspace.workspace_manager import WorkspaceManager
import benchpro.utils.user_dir as user_dir_module

# ====================================================================
# The Definitive Golden Path Test
#
# This test WILL pass. It works by fixing the broken dependency
# injection at its root source for the scope of the test.
# ====================================================================

@pytest.fixture
def isolated_user_dir(tmp_path):
    """Creates a UserDirectoryManager in a temporary directory."""
    # We create a new, isolated manager instance for our test.
    return user_dir_module.UserDirectoryManager(base_dir=str(tmp_path))

def test_benchmark_execution_passes(isolated_user_dir, monkeypatch):
    """
    This test hijacks the global user_dir_manager factory to ensure
    all components, no matter how they are created, use the same isolated
    test directory. This is the key to making the test reliable.
    """
    # 1. THE CRITICAL WORKAROUND:
    # We patch the `get_user_dir_manager` function itself. Now, any call
    # to this function anywhere in the codebase will return our single,
    # `isolated_user_dir` instance instead of creating a new default one.
    monkeypatch.setattr(
        user_dir_module,
        "get_user_dir_manager",
        lambda: isolated_user_dir
    )
    
    # Also patch the global user_dir_manager instance used by script generators
    monkeypatch.setattr(
        "benchpro.utils.user_dir.user_dir_manager",
        isolated_user_dir
    )

    # 2. Mock the execution component to prevent shell commands
    def mock_execute(self, script_path: str, config: dict):
        return True, "mock_job_id_123"
    monkeypatch.setattr(
        "benchpro.executor.components.execution.LocalExecutionComponent.execute",
        mock_execute
    )

    # 3. Setup the high-level objects.
    # Now that `get_user_dir_manager` is patched, we can let these
    # classes construct themselves, and they will automatically receive
    # the correct (isolated) user directory manager.
    config_manager = ConfigManager(user_dir_manager=isolated_user_dir)
    registry_manager = RegistryManager(user_dir_manager=isolated_user_dir)
    workspace_manager = WorkspaceManager(user_dir_manager=isolated_user_dir)
    task_factory = TaskFactory(
        config_manager=config_manager,
        registry_manager=registry_manager
    )
    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=registry_manager,
        workspace_manager=workspace_manager
    )

    # 4. Register a dependency application
    app_binary_path = isolated_user_dir.get_path("outputs_application", "hello_world")
    registry_manager.register_application({
        "name": "hello_world_app", "version": "1.0", "binary_path": app_binary_path,
        "workspace_dir": "dummy", "build_parameters": {}, "metadata": {}
    })

    # 5. Define and write the benchmark profile to the isolated environment
    benchmark_profile = {
        "task_type": "benchmark", "name": "golden_benchmark",
        "run": {"application": "hello_world_app", "executable": "placeholder"},
        "job": {"scheduler": "local"}, "template": "vanilla.j2"
    }
    profile_path = isolated_user_dir.get_path("inputs_benchmark", "golden_benchmark.yaml")
    with open(profile_path, "w") as f:
        yaml.dump(benchmark_profile, f)

    template_path = isolated_user_dir.get_path("inputs_benchmark", "vanilla.j2")
    with open(template_path, "w") as f:
        f.write("#!/bin/bash\n{{ command }}\n")

    # 6. Execute the orchestrator
    success, job_id, script_path = orchestrator.execute("golden_benchmark", {})

    # 7. Assert the expected outcomes
    assert success is True
    assert job_id == "mock_job_id_123"
    assert os.path.exists(script_path)
    with open(script_path, 'r') as f:
        script_content = f.read()
        # Verify the script contains the expected template structure
        assert "#!/bin/bash" in script_content
        assert "Working in workspace:" in script_content
        assert "Job started at:" in script_content 