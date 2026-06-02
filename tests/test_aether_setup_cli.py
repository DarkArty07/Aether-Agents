"""Tests for the Aether Setup CLI (``olympus_v3.cli.setup``)."""

from __future__ import annotations

import subprocess
import sys

from olympus_v3.cli.ui.banner import BANNER


# ── Banner tests ──────────────────────────────────────────────────


class TestBanner:
    """Verify the banner constant meets spec requirements."""

    def test_banner_is_ascii(self) -> None:
        """Banner contains only ASCII characters and is at least 8 lines."""
        assert all(ord(c) < 128 for c in BANNER), "Banner contains non-ASCII characters"
        assert BANNER.count("\n") >= 8, f"Banner has {BANNER.count(chr(10))} newlines, expected >= 8"

    def test_banner_contains_aether(self) -> None:
        """Banner contains the word 'AETHER' (case-insensitive, space-tolerant)."""
        cleaned = BANNER.upper().replace(" ", "")
        assert "AETHER" in cleaned, f"'AETHER' not found (case-insensitive) in:\n{BANNER}"


# ── CLI tests ─────────────────────────────────────────────────────


class TestCLI:
    """Integration tests for the argparse-based CLI (via subprocess)."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        """Run the CLI module with given arguments."""
        return subprocess.run(
            [sys.executable, "-m", "olympus_v3.cli.setup", *args],
            capture_output=True,
            text=True,
        )

    def test_no_args_runs_init(self) -> None:
        """Calling the CLI without arguments defaults to ``init`` and exits 0."""
        result = self._run()
        assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    def test_help_exits_0(self) -> None:
        """``--help`` displays usage and exits 0."""
        result = self._run("--help")
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

    def test_subcommand_status(self) -> None:
        """``status`` subcommand runs without error."""
        result = self._run("status")
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

    def test_subcommand_daimon_list(self) -> None:
        """``daimon`` (no name) runs without error."""
        result = self._run("daimon")
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

    def test_subcommand_keys(self) -> None:
        """``keys`` subcommand runs without error."""
        result = self._run("keys")
        assert result.returncode == 0, f"stderr:\n{result.stderr}"

    def test_subcommand_model_requires_two_args(self) -> None:
        """``model`` without arguments exits with a non-zero code."""
        result = self._run("model")
        assert result.returncode != 0, "Expected model to fail without required args"

    def test_subcommand_reset_dry_run(self) -> None:
        """``reset --dry-run`` runs without error (does not nuke anything)."""
        result = self._run("reset", "--dry-run")
        assert result.returncode == 0, f"stderr:\n{result.stderr}"
