#!/usr/bin/env bash
# block-write-commands.sh — Hermes orchestrator terminal restriction hook
# Blocks write commands in terminal tool while allowing read-only and mutation commands
# Pre_tool_call hook: receives JSON on stdin with {tool_name, tool_input: {command: "..."}}

payload="$(cat -)"
cmd=$(echo "$payload" | jq -r '.tool_input.command // empty')

# Block in-place file editing
if echo "$cmd" | grep -qE '\bsed\s+.*(-i|--in-place)\b'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Sed -i writes files."}\n'
  exit 0
fi

# Block perl one-liners (can write files without -i)
if echo "$cmd" | grep -qE '\bperl\s+-e\b'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Perl writes files."}\n'
  exit 0
fi

# Block patch command
if echo "$cmd" | grep -qE '\bpatch\b'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Patch modifies files."}\n'
  exit 0
fi

# Block file redirect writing (> and >>) EXCEPT to /dev/
# Allows: > /dev/null, > /dev/stderr, 2>&1
# Blocks: > file.py, >> config.yaml, > /tmp/anything, cat << EOF > script.sh
if echo "$cmd" | grep -qP '>\s*[^&>/]|>>\s*[^&>/]'; then
  # Check if redirect is to /dev/ ONLY
  if echo "$cmd" | grep -qP '>\s*/dev/|>>\s*/dev/'; then
    : # allow redirect to /dev/ only
  else
    printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Redirect writes to files."}\n'
    exit 0
  fi
fi

# Block tee writing to files (not /dev/)
if echo "$cmd" | grep -qE '\btee\s+'; then
  if echo "$cmd" | grep -qE '\btee\s+/dev/'; then
    : # allow tee to /dev/
  else
    printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Tee writes to files."}\n'
    exit 0
  fi
fi

# Block python -c entirely (multiline open() bypasses same-line regex)
if echo "$cmd" | grep -qE '\bpython[3]?\s+-c'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Python -c can write files."}\n'
  exit 0
fi

# Block node one-liner file writing
if echo "$cmd" | grep -qE 'node\s+-e.*writeFile|node\s+-e.*writeSync'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Node -e can write files."}\n'
  exit 0
fi

# Block ruby one-liner file writing
if echo "$cmd" | grep -qE 'ruby\s+-e.*File\.write|ruby\s+-e.*open.*\.write'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Ruby -e can write files."}\n'
  exit 0
fi

# Block heredoc file creation (cat << EOF > file or similar)
if echo "$cmd" | grep -qE '<<\s*(EOF|END|HEREDOC).*>\s*[^&>/]'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Heredoc creates files."}\n'
  exit 0
fi

# Block heredoc feeding to interpreters (bypasses -c detection)
if echo "$cmd" | grep -qE '\bpython[3]?\s+<<|\bnode\s+<<|\bruby\s+<<|\bperl\s+<<|\bbash\s+<<|\bsh\s+<<'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Heredoc executes code."}\n'
  exit 0
fi

# Block awk with file redirect (awk '{print > "file"}')
if echo "$cmd" | grep -qE '\bawk\b.*>'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Awk can write files."}\n'
  exit 0
fi

# Block curl/wget file downloads (curl -o, wget -O write to disk)
if echo "$cmd" | grep -qE '\bcurl\b.*-o\b|\bwget\b.*-O\b'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Curl/wget downloads to files."}\n'
  exit 0
fi

# Block dd output to files (dd of=file)
if echo "$cmd" | grep -qE '\bdd\b.*\bof='; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Dd writes files."}\n'
  exit 0
fi

# Block install command (creates files with permissions)
if echo "$cmd" | grep -qE '\binstall\s+-'; then
  printf '{"decision": "block", "reason": "Delegate. You are an orchestrator, not an implementer. Install creates files."}\n'
  exit 0
fi

# Everything else is allowed
printf '{}\n'