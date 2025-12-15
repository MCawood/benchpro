import pytest
import subprocess
from unittest.mock import patch, MagicMock
from benchpro.core.modules import ModuleHandler

class TestModuleHandler:
    
    @pytest.fixture
    def handler(self):
        return ModuleHandler()

    @patch("shutil.which")
    def test_init_finds_module_cmd(self, mock_which):
        mock_which.return_value = "/usr/bin/module"
        handler = ModuleHandler()
        assert handler.lmod_cmd == "/usr/bin/module"
        
    @patch("shutil.which")
    def test_init_defaults_to_module(self, mock_which):
        mock_which.return_value = None
        handler = ModuleHandler()
        assert handler.lmod_cmd == "module"

    @patch("subprocess.run")
    def test_modules_available_success(self, mock_run, handler):
        mock_run.return_value.returncode = 0
        assert handler.modules_available() is True
        mock_run.assert_called_with(
            ["bash", "-l", "-c", "module --version"],
            capture_output=True,
            text=True,
            timeout=2
        )

    @patch("subprocess.run")
    def test_modules_available_failure(self, mock_run, handler):
        mock_run.return_value.returncode = 1
        assert handler.modules_available() is False

    @patch("subprocess.run")
    def test_modules_available_exception(self, mock_run, handler):
        mock_run.side_effect = subprocess.SubprocessError("Boom")
        assert handler.modules_available() is False

    @patch("subprocess.run")
    def test_validate_modules_success(self, mock_run, handler):
        mock_run.return_value.stdout = "SUCCESS"
        assert handler.validate_modules(["gcc", "openmpi"]) is True
        mock_run.assert_called()
        cmd = mock_run.call_args[0][0]
        assert "module load gcc openmpi" in cmd[3]

    @patch("subprocess.run")
    def test_validate_modules_failure(self, mock_run, handler):
        mock_run.return_value.stdout = "Error: Unable to load module"
        assert handler.validate_modules(["gcc"]) is False

    @patch("subprocess.run")
    def test_find_available_module(self, mock_run, handler):
        # Setup mock to fail first, succeed second
        def side_effect(cmd, **kwargs):
            if "gcc/9.1.0" in cmd[3]:
                return MagicMock(returncode=1, stderr="No module", stdout="")
            if "gcc/9.2.0" in cmd[3]:
                return MagicMock(returncode=0, stderr="", stdout="gcc/9.2.0")
            return MagicMock(returncode=1)
            
        mock_run.side_effect = side_effect
        
        result = handler.find_available_module(["gcc/9.1.0", "gcc/9.2.0"])
        assert result == "gcc/9.2.0"

    @patch("subprocess.run")
    def test_resolve_defaults(self, mock_run, handler):
        # Test resolving 'gcc' to 'gcc/11.2.0'
        mock_run.return_value.stdout = "gcc/11.2.0"
        mock_run.return_value.stderr = ""
        
        resolved = handler.resolve_defaults(["gcc"])
        assert resolved == ["gcc/11.2.0"]
        
    @patch("subprocess.run")
    def test_resolve_defaults_ignores_explicit(self, mock_run, handler):
        # Should not call subprocess for modules with versions
        resolved = handler.resolve_defaults(["gcc/9.3.0"])
        assert resolved == ["gcc/9.3.0"]
        mock_run.assert_not_called()

    def test_generate_module_file(self, handler):
        content = handler.generate_module_file(
            name="testapp",
            version="1.0",
            modules=["gcc/11", "openmpi/4"],
            paths=["/opt/testapp/bin"],
            env_vars={"TEST_HOME": "/opt/testapp"}
        )
        
        # BenchPro uses try_load for robustness
        # assert "module load gcc/11" in content
        assert 'try_load("gcc/11")' in content
        assert 'try_load("openmpi/4")' in content
        assert 'prepend_path("PATH", "/opt/testapp/bin")' in content
        assert 'setenv("TEST_HOME", "/opt/testapp")' in content
