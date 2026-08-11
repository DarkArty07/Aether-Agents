"""Atomically enable or disable the installed Aether MCP registration."""

from __future__ import annotations

import argparse
import json

from installation import InstallError, activate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-home", required=True)
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(activate(args.hermes_home, enabled=not args.disable), sort_keys=True))
        return 0
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
