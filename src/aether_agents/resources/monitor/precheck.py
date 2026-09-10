#!/usr/bin/env python3
"""Packaged deterministic pre-check for the Aether Telegram Monitor cron job.

The monitor's native hourly job installs this file under ``<HERMES_HOME>/scripts`` and
runs it with the runtime interpreter before the narration turn.  Its stdout is injected
into the reporter prompt; its final non-empty line is the native wake gate.

* A deterministic successful idle run prints only ``{"wakeAgent": false}`` so no model
  call happens.
* A run with tracked work, an unreported final outcome or a source failure prints the
  bounded narration context followed by ``{"wakeAgent": true, ...}``.
* A pre-check failure never claims idle.

The script is a thin entry point: all logic lives in the packaged, tested
``aether_agents.monitor.runtime`` module so it cannot drift from the monitor's unit
tests.
"""

from __future__ import annotations


def main() -> int:
    from aether_agents.monitor.runtime import main_precheck

    return main_precheck()


if __name__ == "__main__":
    raise SystemExit(main())
