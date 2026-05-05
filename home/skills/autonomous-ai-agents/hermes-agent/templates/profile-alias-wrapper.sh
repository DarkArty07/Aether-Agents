#!/bin/sh
# Hermes profile alias wrapper — GENERIC template for any named profile
# Replace <PROFILE> and paths below with your actual values.
# Usage: cp to ~/.local/bin/<profile-name> && chmod +x
#
# WHY: "hermes profile alias <name>" creates `exec hermes -p <name> "$@"`.
# If the `hermes` command is itself a wrapper that injects `-p hermes`,
# the result is `-p hermes -p <name>` — the pre-parser takes the first
# `-p`, argparse sees <name> as a subcommand, and you get
# "error: invalid choice: '<name>'". This template calls the venv binary
# directly, avoiding the conflict.
#
# CRITICAL: Set HERMES_HOME to your Aether Agents home directory.
# Without it, the profile's config.yaml, SOUL.md, skills, and sessions
# won't be found.

export HERMES_HOME=/home/YOURUSER/Aether-Agents/home
exec /home/YOURUSER/.hermes/hermes-agent/venv/bin/hermes -p <PROFILE> "$@"