"""Inert Telegram Monitor entry for the RC18 adoption bridge (#564).

RC17's frozen release manager accepts only candidates that declare the historical
``aether-telegram-monitor`` plugin entry point and load a callable ``register``. The
RC18 bridge declares it so RC17 can adopt the bridge, whose newer manager then adopts
RC19. The Telegram Monitor stays retired (``specs/lab-monitor-retirement/spec.md``):
this module registers no tool, hook, schedule or notification and is never part of a
``main`` release.
"""

from __future__ import annotations


def register(ctx: object) -> None:
    """Register nothing; the bridge only satisfies RC17's exact plugin map."""
    del ctx
