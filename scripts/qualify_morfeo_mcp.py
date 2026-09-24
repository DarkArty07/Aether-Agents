"""Qualify Morfeo MCP against the pinned maintained Hermes fork."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from aether_agents.lifecycle import _tree_sha256

PIN_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
PIN_TREE = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"


def _git(checkout: Path, *args: str) -> str | None:
    if not (checkout / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    args = parser.parse_args(argv)
    checkout = args.checkout.resolve()
    digest = _tree_sha256(checkout)
    if digest != PIN_TREE:
        print(f"tree digest {digest} is not the pinned Hermes tree", file=sys.stderr)
        return 1
    commit = _git(checkout, "rev-parse", "HEAD")
    if commit is not None and commit != PIN_COMMIT:
        print(f"commit {commit} is not the pinned Hermes commit", file=sys.stderr)
        return 1
    import tempfile

    temporary = tempfile.NamedTemporaryFile(prefix="morfeo-mcp-", suffix=".txt", delete=False)
    temporary.close()
    export = Path(temporary.name)
    completed = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--extra",
            "mcp",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(export),
        ],
        cwd=checkout,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        if completed.returncode != 0:
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
        text = export.read_text(encoding="utf-8")
    finally:
        if export.exists():
            export.unlink()
    if "mcp==1.28.1" not in text:
        print("locked export did not pin mcp==1.28.1", file=sys.stderr)
        return 1
    print(f"qualified hermes pin {PIN_COMMIT} tree {PIN_TREE} mcp==1.28.1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
