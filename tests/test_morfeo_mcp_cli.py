"""The manager CLI stays usable when Hermes and the MCP SDK are absent."""

from __future__ import annotations

import sys

import pytest

from aether_agents.cli import main


class _BlockedImport:
    def find_spec(self, fullname, path, target=None):  # noqa: ANN001
        if fullname in {"mcp", "hermes_cli", "model_tools", "run_agent"} or fullname.startswith(
            ("mcp.", "hermes_cli.", "model_tools.")
        ):
            raise ImportError(fullname)
        return None


@pytest.fixture
def blocked_hermes_imports():
    hook = _BlockedImport()
    sys.meta_path.insert(0, hook)
    for name in ("mcp", "hermes_cli", "model_tools", "run_agent"):
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        sys.meta_path.remove(hook)


def test_help_and_version_do_not_need_hermes_or_mcp(capsys, blocked_hermes_imports) -> None:
    assert main(["--help"]) == 0
    assert "mcp" in capsys.readouterr().out
    assert main(["--version"]) == 0
    assert "aether" in capsys.readouterr().out
    assert main(["mcp", "--help"]) == 0
    assert "morfeo" in capsys.readouterr().out
    assert main(["mcp", "morfeo", "--help"]) == 0
    assert "serve" in capsys.readouterr().out


def test_public_host_is_refused_before_runtime(capsys) -> None:
    code = main(["mcp", "morfeo", "serve", "--host", "0.0.0.0", "--project", "/tmp/not-a-project"])
    assert code == 2
    assert "127.0.0.1" in capsys.readouterr().err
