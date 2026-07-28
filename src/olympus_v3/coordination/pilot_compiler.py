"""Compile the one pre-reviewed R8 Snake task graph."""

from __future__ import annotations

from pathlib import Path

from .pilot_model import CANONICAL_PILOT_ROOT, PILOT_ID, PilotManifest, PilotTask


def compile_snake_manifest(*, root: Path = CANONICAL_PILOT_ROOT) -> PilotManifest:
    root = Path(root)
    tasks = (
        PilotTask(
            "snake-spec",
            "design",
            "daedalus",
            "Create DESIGN.md for an original polished Three.js Snake: visual system, interactions, responsive controls, motion, accessibility, game states, and exact acceptance checklist. Do not implement code.",
            (),
            "write",
            ("DESIGN.md",),
            ("DESIGN.md",),
        ),
        PilotTask(
            "snake-build",
            "implement",
            "hefesto",
            "Implement the complete Three.js Snake product from DESIGN.md. Use Vite, deterministic game logic tests, responsive keyboard/touch UX, accessible controls, reduced motion, persistence, audio toggle, polished 3D feedback, README, and a production build. Keep every file under the pilot root.",
            ("snake-spec",),
            "write",
            (
                "DESIGN.md",
                "index.html",
                "package.json",
                "package-lock.json",
                "README.md",
                "src",
                "tests",
                "vite.config.js",
            ),
            ("package.json", "README.md", "index.html", "src/main.js"),
        ),
        PilotTask(
            "snake-verify",
            "verify",
            "hefesto",
            "Run the complete local test/build/static validation suite, inspect the product implementation, and correct only bounded defects needed to satisfy DESIGN.md. Report exact commands and hashes.",
            ("snake-build",),
            "write",
            (
                "DESIGN.md",
                "index.html",
                "package.json",
                "package-lock.json",
                "README.md",
                "src",
                "tests",
                "vite.config.js",
            ),
            ("package.json", "README.md", "index.html", "src/main.js"),
        ),
        PilotTask(
            "snake-review",
            "review",
            "athena",
            "Independently review the immutable Snake artifact for security, scope containment, correctness, accessibility, responsive controls, build/test evidence, and console-risk. Do not modify files. Accept only if no blocking finding remains.",
            ("snake-verify",),
            "read_only",
            (
                "DESIGN.md",
                "index.html",
                "package.json",
                "package-lock.json",
                "README.md",
                "src",
                "tests",
                "vite.config.js",
            ),
            (),
            "snake-verify",
        ),
        PilotTask(
            "snake-closure",
            "completion",
            "ictinus",
            "Independently decide whether the complete Snake artifact and review evidence satisfy the R8 product contract. Do not modify files. Accept closure only from verified artifacts and review evidence.",
            ("snake-review",),
            "read_only",
            (
                "DESIGN.md",
                "index.html",
                "package.json",
                "package-lock.json",
                "README.md",
                "src",
                "tests",
                "vite.config.js",
            ),
            (),
            "snake-review",
        ),
    )
    return PilotManifest(PILOT_ID, PILOT_ID, str(root), tasks)


__all__ = ["compile_snake_manifest"]
