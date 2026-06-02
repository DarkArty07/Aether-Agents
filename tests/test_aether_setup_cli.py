from pathlib import Path
from olympus_v3.cli.wrappers import write_aether_setup_wrapper, WRAPPER_TEMPLATE


class TestWrapperHelper:
    def test_template_has_required_fields(self) -> None:
        assert "HERMES_HOME" in WRAPPER_TEMPLATE and "aether-setup" in WRAPPER_TEMPLATE

    def test_wrapper_creates_executable(self, tmp_path) -> None:
        target = tmp_path / "aether-setup"
        result = write_aether_setup_wrapper(
            project_root=Path("/home/prometeo/Aether-Agents"),
            venv_dir=Path("/home/prometeo/Aether-Agents/home/.venv-hermes"),
            target=target,
        )
        assert result == target and target.exists() and (target.stat().st_mode & 0o111)

    def test_wrapper_is_idempotent(self, tmp_path) -> None:
        target = tmp_path / "aether-setup"
        kw = dict(project_root=Path("/home/prometeo/Aether-Agents"), venv_dir=Path("/home/prometeo/Aether-Agents/home/.venv-hermes"), target=target)
        a = write_aether_setup_wrapper(**kw).read_text()
        b = write_aether_setup_wrapper(**kw).read_text()
        assert a == b

    def test_wrapper_content_has_hermes_home(self, tmp_path) -> None:
        target = tmp_path / "aether-setup"
        write_aether_setup_wrapper(project_root=Path("/home/prometeo/Aether-Agents"), venv_dir=Path("/home/prometeo/Aether-Agents/home/.venv-hermes"), target=target)
        text = target.read_text()
        assert "HERMES_HOME" in text and "/home/prometeo/Aether-Agents/home" in text
