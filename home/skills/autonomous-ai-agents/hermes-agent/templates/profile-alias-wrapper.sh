#!/bin/sh
# Hermes wrapper — GENERIC template
# Replace paths below with your actual values.
# Usage: cp to ~/.local/bin/hermes && chmod +x
#
# DEFAULT PROFILE (recommended for orchestrator):
# When HERMES_HOME points to a custom directory (not ~/.hermes), the framework
# uses that directory as the default profile. No -p flag needed — SOUL.md,
# config.yaml, .env, auth.json are read from HERMES_HOME/ directly.
#
# NAMED PROFILE (for Daimons):
# Add `-p <profile-name>` after the hermes binary path. Examples:
#   exec "${HERMES_BIN}" -p hefesto "$@"
#   exec "${HERMES_BIN}" -p etalides "$@"
#
# WHY NOT "hermes profile alias": The `hermes profile alias <name>` command
# creates `exec hermes -p <name>`. If the `hermes` command is itself a wrapper
# that injects `-p hermes`, the result is `-p hermes -p <name>` — the
# pre-parser takes the first `-p`, argparse sees <name> as a subcommand, and
# you get "error: invalid choice: '<name>'". This template calls the venv
# binary directly, avoiding the conflict.
#
# CRITICAL: Set HERMES_HOME to your project's home directory.
# Without it, config.yaml, SOUL.md, skills, and sessions won't be found.

HERMES_HOME="/home/YOURUSER/Aether-Agents/home"
HERMES_BIN="${HERMES_HOME}/.venv-hermes/bin/hermes"

export HERMES_HOME
exec "${HERMES_BIN}" "$@"