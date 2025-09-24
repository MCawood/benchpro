import pytest
from benchpro.executor.task_orchestrator import TaskOrchestrator
from benchpro.executor.task_factory import TaskFactory

def test_orchestrator_can_execute_task_in_isolated_dir(orchestrator_test_env, monkeypatch):
    """
    This is the final isolation test. It verifies that the TaskOrchestrator
    can successfully execute a task using our standardized test environment.
    """
    # 1. Mock the execution component to prevent actual shell commands
    def mock_execute(self, script_path, config):
        return True, "mock_job_id_123"
    monkeypatch.setattr(
        "benchpro.executor.components.execution.LocalExecutionComponent.execute",
        mock_execute
    )
    
    # 2. Create components using the standardized test environment
    from benchpro.config.config_manager import ConfigManager
    from benchpro.utils.user_dir import user_dir_manager
    from unittest.mock import MagicMock

    # The fixture sets up user_dir_manager to point to the test environment
    config_manager = ConfigManager(user_dir_manager=user_dir_manager)
    
    # Mock registry manager to avoid database dependency
    mock_registry_manager = MagicMock()
    mock_registry_manager.register_task_submission.return_value = "mock_task_id"
    
    # 3. Create the orchestrator using the standardized components
    from benchpro.workspace.workspace_manager import WorkspaceManager
    workspace_manager = WorkspaceManager(user_dir_manager=user_dir_manager)
    
    orchestrator = TaskOrchestrator(
        config_manager=config_manager,
        registry_manager=mock_registry_manager,
        workspace_manager=workspace_manager
    )
    
    # 4. Replace the orchestrator's internal factory with one using our test managers
    orchestrator.task_factory = TaskFactory(
        config_manager=config_manager,
        registry_manager=mock_registry_manager
    )

    # 5. Register the required application (the standardized test env should have test_app available)
    try:
        # The orchestrator_test_env should already have test_app registered, but let's ensure it
        registry_manager.register_application({
            "name": "test_app", "version": "1.0", "binary_path": "/bin/true",
            "workspace_dir": "dummy", "build_parameters": {}, "metadata": {}
        })
    except Exception:
        # Application might already be registered, which is fine
        pass

    # 6. Execute the orchestrator test profile (should be available from standardized test data)
    success, job_id, script_path = orchestrator.execute("orchestrator_test_profile", {})

    # 7. Assert that the entire workflow succeeded
    assert success is True
    assert job_id == "mock_job_id_123"
    assert script_path is not None
