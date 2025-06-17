import pytest
import yaml
from benchpro.config.config_manager import ConfigManager
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.registry.registry_manager import RegistryManager
from benchpro.workspace.workspace_manager import WorkspaceManager
from benchpro.utils.user_dir import UserDirectoryManager
import benchpro.utils.user_dir as user_dir_module

@pytest.fixture
def isolated_user_dir(tmp_path):
    """Provides a UserDirectoryManager in a temporary directory."""
    return UserDirectoryManager(base_dir=str(tmp_path))

def test_end_to_end_workflow_in_isolation(isolated_user_dir, monkeypatch):
    """
    This test verifies the entire orchestration path, from loading a profile
    to submitting a job, using a fully isolated, dependency-injected setup.
    """
    # 1. Patch user directory manager functions to use isolated directory
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
    
    # 2. Mock the final execution step to prevent shell commands
    def mock_execute(self, script_path):
        return True, "mock_job_id_123"
    monkeypatch.setattr(
        "benchpro.executor.task.Task.submit_job",
        mock_execute
    )

    # 3. Create the dependency chain using our isolated directory manager.
    #    This is now possible because the source code is correctly refactored.
    config_manager = ConfigManager(user_dir_manager=isolated_user_dir)
    registry_manager = RegistryManager(user_dir_manager=isolated_user_dir)
    workspace_manager = WorkspaceManager(user_dir_manager=isolated_user_dir)
    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=registry_manager,
        workspace_manager=workspace_manager
    )

    # 4. Create the dummy profile file for the orchestrator to find
    profile_content = {
        "task_type": "benchmark",
        "name": "golden_path_profile",
        "run": { "application": "some_app", "executable": "placeholder" },
        "job": { "scheduler": "local" },
        "template": "vanilla.j2"
    }
    profile_path = isolated_user_dir.get_path("inputs_benchmark", "golden_path_profile.yaml")
    
    import os
    os.makedirs(os.path.dirname(profile_path), exist_ok=True)
    with open(profile_path, "w") as f:
        yaml.dump(profile_content, f)

    template_path = isolated_user_dir.get_path("inputs_benchmark", "vanilla.j2")
    with open(template_path, "w") as f:
        f.write("#!/bin/bash\\n{{ command }}\\n")
        
    # 5. Register a dummy dependency application
    registry_manager.register_application({
        "name": "some_app", "version": "1.0", "binary_path": "/bin/true",
        "workspace_dir": "dummy", "build_parameters": {}, "metadata": {}
    })

    # 6. Execute the orchestrator, which should now succeed
    success, job_id, script_path = orchestrator.execute("golden_path_profile", {})

    # 7. Assert that the entire workflow succeeded.
    assert success is True
    assert job_id == "mock_job_id_123"
