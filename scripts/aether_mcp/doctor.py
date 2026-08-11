"""Validate the installed Aether MCP without enabling its registration."""

from __future__ import annotations

import argparse
import json

from installation import InstallError, doctor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-home", required=True)
    args = parser.parse_args()
    try:
        result = doctor(args.hermes_home)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["ok"] else 2
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
