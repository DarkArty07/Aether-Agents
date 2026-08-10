"""Install the named local Aether MCP registration in disabled mode."""

from __future__ import annotations

import argparse
import json

from installation import InstallError, setup


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "project-root",
        "hermes-home",
        "appimage",
        "profile-root",
        "repo-selector",
        "base-ref",
        "coordinator-handle",
    ):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--uv", default="uv")
    parser.add_argument("--timeout-ms", type=int, default=600000)
    args = parser.parse_args()
    try:
        result = setup(**vars(args))
        print(json.dumps({"ok": True, "launcher": result.launcher, "tool_count": result.tool_count}, sort_keys=True))
        return 0
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": {"code": exc.code}}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
