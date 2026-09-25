"""Runtime argument guards."""

from __future__ import annotations

from aether_agents.mcp.morfeo_server import main


def test_runtime_refuses_a_public_bind(capsys, tmp_path) -> None:
    code = main(
        [
            "--mode",
            "harness",
            "--transport",
            "stdio",
            "--project",
            str(tmp_path),
            "--project-id",
            "12027989-a08f-41cd-a82c-54ff1bfb6b03",
            "--profile",
            str(tmp_path),
            "--host",
            "0.0.0.0",
        ]
    )
    assert code == 2
    assert "127.0.0.1" in capsys.readouterr().err
