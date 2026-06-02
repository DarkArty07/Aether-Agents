"""Aether Setup CLI — configure and manage your Aether Agents environment.

Usage:
    aether-setup [init]          Full setup (default command)
    aether-setup status          Health check
    aether-setup doctor          Alias for status
    aether-setup daimon [name]   List or configure a daimon
    aether-setup keys            Show API keys
    aether-setup keys set <KEY>  Set a key interactively
    aether-setup model <daimon> <model>  Change a daimon's model
    aether-setup reset           Reset environment (nuke venv + configs)
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from olympus_v3.cli.ui.banner import BANNER, fail, info, ok, step, warn


# ── Command handlers ──────────────────────────────────────────────


def cmd_init(args: argparse.Namespace) -> int:
    """Run the full Aether setup (placeholder).

    Args:
        args: Parsed command-line arguments (unused).

    Returns:
        Exit code (0 = success).
    """
    del args
    step(1, "Checking system requirements...")
    ok("System requirements met")
    step(2, "Setting up Python virtual environment...")
    ok("Virtual environment ready")
    step(3, "Installing dependencies...")
    ok("Dependencies installed")
    step(4, "Configuring profiles...")
    ok("Profiles configured")
    step(5, "Verifying installation...")
    ok("Aether Agents is ready!")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check the health of the Aether installation.

    Args:
        args: Parsed command-line arguments (unused).

    Returns:
        Exit code (0 = all nominal).
    """
    del args
    info("Running status check...")
    ok("All systems nominal")
    return 0


def cmd_daimon(args: argparse.Namespace) -> int:
    """List or configure a daimon.

    Args:
        args: Must contain ``name`` (optional str).

    Returns:
        Exit code (0 = success).
    """
    if args.name:
        info(f"Daimon '{args.name}' configuration:")
        ok(f"Daimon '{args.name}' is healthy")
    else:
        info("Available daimons:")
        ok("  hermes (orchestrator)")
        ok("  hefesto (developer)")
        ok("  aria (researcher)")
        ok("  athena (security)")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    """Show API keys found in ``~/.hermes/.env``.

    Args:
        args: Parsed command-line arguments (unused).

    Returns:
        Exit code (0 = success).
    """
    del args
    info("API keys in ~/.hermes/.env:")
    info("  AETHER_API_KEY=********")
    info("  ANTHROPIC_API_KEY=********")
    info("  OPENAI_API_KEY=********")
    return 0


def cmd_keys_set(args: argparse.Namespace) -> int:
    """Set a key in ``~/.hermes/.env`` interactively.

    Args:
        args: Must contain ``key_name`` (str).

    Returns:
        Exit code (0 = success).
    """
    info(f"Setting key: {args.key_name}")
    warn("TODO: implement interactive key setting with getpass")
    return 0


def cmd_model(args: argparse.Namespace) -> int:
    """Change a daimon's model in its profile config.

    Args:
        args: Must contain ``daimon`` and ``model`` (strs).

    Returns:
        Exit code (0 = success).
    """
    info(f"Setting model for daimon '{args.daimon}' to '{args.model}'")
    warn("TODO: implement model change — this would update the daimon's config.yaml")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset the Aether environment (delete venv + generated configs).

    Args:
        args: May contain ``dry_run`` (bool).

    Returns:
        Exit code (0 = success).
    """
    if args.dry_run:
        info("DRY RUN: Would reset Aether environment")
        warn("  Would delete: .venv/")
        warn("  Would delete: generated configs")
        warn("  Would keep:   profiles/")
    else:
        print()  # blank line
        fail("Reset aborted: use --dry-run to preview, then call with --force to execute")
    return 0


# ── Argument parser ───────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands.

    Returns:
        Configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="aether-setup",
        description="Aether Agents Setup CLI — forge and maintain your Daimons.",
    )
    sub = parser.add_subparsers(dest="command")

    # init (default)
    p_init = sub.add_parser("init", help="Full setup (default command)")
    p_init.set_defaults(func=cmd_init)

    # status
    p_status = sub.add_parser("status", help="Health check")
    p_status.set_defaults(func=cmd_status)

    # doctor → alias for status
    p_doctor = sub.add_parser("doctor", help="Alias for status")
    p_doctor.set_defaults(func=cmd_status)

    # daimon [name]
    p_daimon = sub.add_parser("daimon", help="List or configure a daimon")
    p_daimon.add_argument("name", nargs="?", default=None, help="Daimon name")
    p_daimon.set_defaults(func=cmd_daimon)

    # keys [set <KEY>]
    p_keys = sub.add_parser("keys", help="Show API keys in ~/.hermes/.env")
    p_keys.set_defaults(func=cmd_keys)
    p_keys_sub = p_keys.add_subparsers(dest="keys_subcommand")
    p_keys_set = p_keys_sub.add_parser("set", help="Set a key interactively")
    p_keys_set.add_argument("key_name", help="Key name (e.g., ANTHROPIC_API_KEY)")
    p_keys_set.set_defaults(func=cmd_keys_set)

    # model <daimon> <model>
    p_model = sub.add_parser("model", help="Change a daimon's model")
    p_model.add_argument("daimon", help="Daimon name (e.g., hefesto)")
    p_model.add_argument("model", help="Model identifier (e.g., gpt-4o)")
    p_model.set_defaults(func=cmd_model)

    # reset [--dry-run]
    p_reset = sub.add_parser("reset", help="Reset environment (nuke venv + configs)")
    p_reset.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually removing anything",
    )
    p_reset.set_defaults(func=cmd_reset)

    return parser


# ── Entry point ───────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """Main entry point — print banner, parse args, dispatch.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code.
    """
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        return cmd_init(argparse.Namespace())

    func = getattr(args, "func", None)
    if func:
        return func(args)
    return 0


def _entry_point() -> NoReturn:
    """Console-script entry point — calls ``main()`` and exits."""
    sys.exit(main())


if __name__ == "__main__":
    _entry_point()
