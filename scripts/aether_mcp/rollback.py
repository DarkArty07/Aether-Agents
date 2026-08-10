"""Remove only the named local Aether MCP installation."""

from __future__ import annotations

import argparse
import json

from installation import InstallError, rollback


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-home", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(rollback(args.hermes_home), sort_keys=True))
        return 0
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
