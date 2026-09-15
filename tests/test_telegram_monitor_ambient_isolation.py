"""Ambient- and order-independence regressions for the exact-Hermes Monitor lane (#438).

The canonical suite must reach the same result no matter which native module an earlier
case imported and no matter which profile the machine's environment points at.  Before
the manager-only Monitor module pinned its own native configuration, an environment whose
ambient ``HERMES_HOME`` configured a narration language made
``configured_owner_language`` re-render an already enqueued outbox part under that
language; the immutable outbox identity then refused the dispatch and the second case of
the ordered pair failed with ``assert [] == [<expected rendered part>]``.

This module runs that ordered pair, and the manager-only case on its own, through real
child processes whose ambient ``HERMES_HOME`` is a disposable profile that *does* configure
a language.  Only disposable roots are used: the operator's live profile is never read,
written or required, and a machine without the release-locked checkout skips the lane the
same way the rest of the exact-Hermes tests do.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from aether_agents.lifecycle import HERMES_BASELINE, verify_clean_checkout

ROOT = Path(__file__).parents[1]

EXACT_CASE = (
    "tests/test_telegram_monitor_cli_plugin.py"
    "::test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter"
)
MANAGER_CASE = (
    "tests/test_telegram_monitor_runtime.py"
    "::test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator"
)

#: The ambient profile's narration language.  Any value works; it must only differ from the
#: no-language default the disposable Monitor state is seeded with.
AMBIENT_LANGUAGE = "Spanish"


def _exact_checkout() -> Path:
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "aether-agents" / "hermes" / HERMES_BASELINE.tag


def _ambient_profile(root: Path) -> Path:
    """A disposable profile whose configuration names a narration language."""

    home = root / "ambient-profile"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "\n".join(
            (
                "plugins:",
                "  enabled:",
                "    - aether-telegram-monitor",
                "  entries:",
                "    aether-telegram-monitor:",
                "      settings:",
                f"        language: {AMBIENT_LANGUAGE}",
                "",
            )
        ),
        encoding="utf-8",
    )
    return home


def _run_cases(
    tmp_path: Path, checkout: Path, cases: list[str]
) -> subprocess.CompletedProcess[str]:
    """Run the given nodes in one child pytest process under a language-configured ambient home."""

    profile_home = tmp_path / "home"
    profile_home.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(profile_home),
        "PYTHONPATH": os.pathsep.join((str(checkout), str(ROOT / "src"))),
        "HERMES_HOME": str(_ambient_profile(tmp_path)),
        "AETHER_EXACT_HERMES_CHECKOUT": str(checkout),
    }
    interpreter = os.environ.get("AETHER_HERMES_PYTHON", "").strip()
    if interpreter:
        environment["AETHER_HERMES_PYTHON"] = interpreter
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider", *cases],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
    )


@pytest.mark.hermes_exact
def test_the_ordered_pair_is_independent_of_the_ambient_profile(tmp_path: Path) -> None:
    """The exact case must not let the manager-only case read the ambient profile."""

    checkout = _exact_checkout()
    if not checkout.is_dir():
        pytest.skip(f"exact Hermes checkout unavailable at {checkout}")
    verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )

    completed = _run_cases(tmp_path, checkout, [EXACT_CASE, MANAGER_CASE])

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "2 passed" in completed.stdout, completed.stdout + completed.stderr


@pytest.mark.hermes_exact
def test_the_manager_only_case_is_independent_of_the_ambient_profile(tmp_path: Path) -> None:
    """The manager-only pre-check must not resolve the ambient profile's language at all."""

    checkout = _exact_checkout()
    if not checkout.is_dir():
        pytest.skip(f"exact Hermes checkout unavailable at {checkout}")
    verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )

    completed = _run_cases(tmp_path, checkout, [MANAGER_CASE])

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "1 passed" in completed.stdout, completed.stdout + completed.stderr
