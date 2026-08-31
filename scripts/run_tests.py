#!/usr/bin/env python3
"""Run pytest against one verified checkout of Aether's selected Hermes baseline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.lifecycle import (  # noqa: E402
    HERMES_BASELINE,
    IntegrityError,
    verify_clean_checkout,
)


def _environment(checkout: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(checkout), existing) if value
    )
    environment["AETHER_EXACT_HERMES_CHECKOUT"] = str(checkout)
    return environment


def run_tests(
    checkout: Path, pytest_arguments: Sequence[str]
) -> subprocess.CompletedProcess[bytes]:
    """Verify the exact annotated release, then execute pytest with it first on ``PYTHONPATH``."""

    evidence = verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    return subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_arguments],
        cwd=ROOT,
        env=_environment(evidence.path),
        check=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path, help="clean exact Hermes checkout")
    parser.add_argument(
        "pytest_arguments", nargs=argparse.REMAINDER, help="arguments forwarded to pytest"
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    pytest_arguments = args.pytest_arguments
    if pytest_arguments[:1] == ["--"]:
        pytest_arguments = pytest_arguments[1:]
    try:
        completed = run_tests(args.checkout, pytest_arguments)
    except (IntegrityError, OSError) as error:
        print(f"exact Hermes test bootstrap failed: {error}", file=sys.stderr)
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
