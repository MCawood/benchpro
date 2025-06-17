import pytest
import yaml
from benchpro.config.config_manager import ConfigManager
from benchpro.utils.user_dir import UserDirectoryManager

@pytest.fixture
def isolated_user_dir(tmp_path):
    """Provides a UserDirectoryManager in a temporary directory."""
    return UserDirectoryManager(base_dir=str(tmp_path))


def test_config_manager_can_find_profile_in_isolated_dir(isolated_user_dir):
    """
    This is the simplest possible test. It verifies one thing:
    Can the ConfigManager, when properly injected with a test-only
    UserDirectoryManager, find a file that we have placed in the
    test-only directory?
    """
    # 1. We create the ConfigManager and directly inject our
    #    isolated directory manager.
    config_manager = ConfigManager(user_dir_manager=isolated_user_dir)

    # 2. We create a dummy profile file inside the isolated
    #    benchmark inputs directory.
    profile_content = {"task_type": "benchmark", "name": "test_profile"}
    profile_path = isolated_user_dir.get_path("inputs_benchmark", "test_profile.yaml")
    
    # Ensure the parent directory exists before writing
    # This is good practice for isolated tests.
    import os
    os.makedirs(os.path.dirname(profile_path), exist_ok=True)
    
    with open(profile_path, "w") as f:
        yaml.dump(profile_content, f)

    # 3. We ask the config_manager to load the profile by name.
    #    If dependency injection is working correctly at this level,
    #    it should find the file.
    try:
        loaded_config = config_manager.load_profile_config("test_profile")
        # 4. We assert that it found the file and the content is correct.
        assert loaded_config["name"] == "test_profile"
    except FileNotFoundError:
        pytest.fail(
            "ConfigManager failed to find 'test_profile.yaml'. "
            "This confirms a deep issue with how it uses the "
            "injected UserDirectoryManager to resolve paths."
        )

