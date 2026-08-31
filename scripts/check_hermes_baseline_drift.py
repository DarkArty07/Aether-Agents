#!/usr/bin/env python3
"""Reject drift from Aether's authoritative Hermes release-baseline resource."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from aether_agents.hermes_baseline import load_hermes_baseline_resource  # noqa: E402
from aether_agents.lifecycle import HERMES_BASELINE  # noqa: E402


def check(root: Path) -> dict[str, object]:
    """Validate current derived references while retaining classified history intact."""

    resource = load_hermes_baseline_resource()
    baseline = resource.baseline
    errors: list[str] = []
    for document in resource.derived_documents:
        candidate = root / document.path
        try:
            content = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"derived document is unavailable: {document.path} ({error})")
            continue
        for field in document.fields:
            value = getattr(baseline, field)
            if value not in content:
                errors.append(f"derived document drift: {document.path} is missing {field}")
    for snapshot in resource.historical_snapshots:
        candidate = root / snapshot.path
        if not candidate.is_file():
            errors.append(f"classified historical snapshot is unavailable: {snapshot.path}")
    if HERMES_BASELINE != baseline:
        errors.append("lifecycle compatibility export differs from the baseline resource")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {
        "baseline": asdict(baseline),
        "derived_document_paths": [document.path for document in resource.derived_documents],
        "historical_snapshot_paths": [snapshot.path for snapshot in resource.historical_snapshots],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to inspect")
    parser.add_argument(
        "--json", action="store_true", help="emit the validated resource summary as JSON"
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        result = check(args.root.resolve(strict=True))
    except (OSError, RuntimeError) as error:
        print(f"Hermes baseline drift check failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("Hermes baseline drift check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
