#!/usr/bin/env bash
# block-write-commands.sh — Hermes orchestrator terminal restriction hook
# Blocks write commands in terminal tool while allowing read-only and mutation commands
# Pre_tool_call hook: receives JSON on stdin with {tool_name, tool_input: {command: "..."}}
#
# Deployment: Copy to <profile_dir>/agent-hooks/block-write-commands.sh
#             chmod +x <profile_dir>/agent-hooks/block-write-commands.sh
#             Add hook config to <profile_dir>/config.yaml (see references/terminal-write-restriction.md)
#
# DESIGN: NO /tmp/ exception — prevents two-step bypass (write script to /tmp, execute it).
# Only /dev/ redirects are allowed (discard output). All python -c and perl -e are blocked
# entirely because multiline strings bypass same-line regex detection of dangerous patterns.
#
# THREE-LAYER DEFENSE:
# Layer 1: disabled_toolsets [file-write, code_execution, delegation] — removes tools from schema
# Layer 2: This hook — regex filter on terminal commands
# Layer 3: SOUL.md "NEVER implement" — behavioral reinforcement

payload="$(cat -)"
cmd=$(echo "$payload" | jq -r '.tool_input.command // empty')

# Block in-place file editing
if echo "$cmd" | grep -qE '\bsed\s+.*(-i|--in-place)\b'; then
  printf '{"decision": "block", "reason": "blocked: sed in-place editing is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block ALL perl one-liners (can write files without -i via open())
if echo "$cmd" | grep -qE '\bperl\s+-e\b'; then
  printf '{"decision": "block", "reason": "blocked: perl one-liner is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block patch command
if echo "$cmd" | grep -qE '\bpatch\b'; then
  printf '{"decision": "block", "reason": "blocked: patch command is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block file redirect writing (> and >>) EXCEPT to /dev/
# NO /tmp/ exception — prevents two-step bypass
# Allows: > /dev/null, > /dev/stderr, 2>&1
# Blocks: > file.py, >> config.yaml, > /tmp/anything
if echo "$cmd" | grep -qP '>\s*[^&>/]|>>\s*[^&>/]'; then
  # Check if redirect is to /dev/ ONLY
  if echo "$cmd" | grep -qP '>\s*/dev/|>>\s*/dev/'; then
    : # allow redirect to /dev/ only
  else
    printf '{"decision": "block", "reason": "blocked: file redirect writing (> or >>) is not permitted (orchestrator restriction)"}\n'
    exit 0
  fi
fi

# Block tee writing to files (not /dev/)
if echo "$cmd" | grep -qE '\btee\s+'; then
  if echo "$cmd" | grep -qE '\btee\s+/dev/'; then
    : # allow tee to /dev/
  else
    printf '{"decision": "block", "reason": "blocked: tee file writing is not permitted (orchestrator restriction)"}\n'
    exit 0
  fi
fi

# Block ALL python -c (multiline open() bypasses same-line regex)
if echo "$cmd" | grep -qE '\bpython[3]?\s+-c'; then
  printf '{"decision": "block", "reason": "blocked: python -c is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block node one-liner file writing
if echo "$cmd" | grep -qE 'node\s+-e.*writeFile|node\s+-e.*writeSync'; then
  printf '{"decision": "block", "reason": "blocked: node one-liner file writing is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block ruby one-liner file writing
if echo "$cmd" | grep -qE 'ruby\s+-e.*File\.write|ruby\s+-e.*open.*\.write'; then
  printf '{"decision": "block", "reason": "blocked: ruby one-liner file writing is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block heredoc file creation (cat << EOF > file or similar)
if echo "$cmd" | grep -qE '<<\s*(EOF|END|HEREDOC).*>\s*[^&>/]'; then
  printf '{"decision": "block", "reason": "blocked: heredoc file creation is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block heredoc feeding to interpreters (bypasses -c detection)
if echo "$cmd" | grep -qE '\bpython[3]?\s+<<|\bnode\s+<<|\bruby\s+<<|\bperl\s+<<|\bbash\s+<<|\bsh\s+<<'; then
  printf '{"decision": "block", "reason": "blocked: heredoc interpreter input is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block awk with file redirect (awk '{print > "file"}')
if echo "$cmd" | grep -qE '\bawk\b.*>'; then
  printf '{"decision": "block", "reason": "blocked: awk file redirect is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block curl/wget file downloads (curl -o, wget -O write to disk)
if echo "$cmd" | grep -qE '\bcurl\b.*-o\b|\bwget\b.*-O\b'; then
  printf '{"decision": "block", "reason": "blocked: file download to disk is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block dd output to files (dd of=file)
if echo "$cmd" | grep -qE '\bdd\b.*\bof='; then
  printf '{"decision": "block", "reason": "blocked: dd file writing is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Block install command (creates files with permissions)
if echo "$cmd" | grep -qE '\binstall\s+-'; then
  printf '{"decision": "block", "reason": "blocked: install command is not permitted (orchestrator restriction)"}\n'
  exit 0
fi

# Everything else is allowed
printf '{}\n'