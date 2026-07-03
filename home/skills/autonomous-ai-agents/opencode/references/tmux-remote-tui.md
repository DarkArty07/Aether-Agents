# Launching a TUI Agent Inside a Remote tmux Session

The pattern for running opencode (or claude code, codex, or any agentic TUI) on a remote box over SSH in a way that survives between Hermes tool calls, lets the user connect and interact directly, and lets Hermes "see" what the TUI is showing without taking it over.

## The wrong way (L1 / naive L2)

```bash
# Naive L1: dies the moment the call returns
wsl.exe -d <remote> -- bash -c "opencode"    # blocks until opencode exits
ssh <alias> "opencode"                       # same: ssh call returns, opencode is killed

# Naive L2: pty lost on disconnect
ssh -t <alias> "opencode"                    # interactive but no persistent session
```

These all die the moment the wrapping call returns. You have no state, no way to "see" what opencode is showing, and the user can't connect to drive it from their own terminal.

## The right way (L2 with tmux as state bridge)

Prerequisites: L2 SSH channel already set up to the remote box, with a `main` tmux session alive. See `aether-agents-orchestration` Pitfall #13 and `references/expanding-team-reach.md` for the full SSH+tmux setup recipe. This reference assumes that's done.

### Launch sequence

```bash
# 1. Pre-flight: ensure sshd is up (in case /etc/wsl.conf [boot] didn't fire)
ssh -o ConnectTimeout=3 <alias> 'true' 2>/dev/null || \
  wsl.exe -d <remote> -- sudo /usr/sbin/sshd

# 2. Ensure a 'main' tmux session exists in the user's home dir
ssh <alias> 'tmux has-session -t main 2>/dev/null || \
  tmux new-session -d -s main -c /home/<remoteuser>'

# 3. Send Ctrl+C first (in case the prior command is still running)
ssh <alias> 'tmux send-keys -t main:0 C-c'
sleep 0.3

# 4. Send the launch command + Enter
ssh <alias> 'tmux send-keys -t main:0 "opencode" C-m'

# 5. Wait for the TUI to render (TUIs have 3-10s startup latency)
sleep 8

# 6. Read what the TUI is currently showing
ssh <alias> 'tmux capture-pane -t main:0 -p -S -200'
```

The TUI is now alive inside the `main` tmux session on the remote box. It survives:
- The user closing their ssh connection
- The user opening a new connection with `ssh <alias>` (which auto-attaches to `main` if you used the helper function)
- Hermes' tool calls ending and the agent loop continuing on a different prompt
- The remote distro being shut down (with `wsl --shutdown <remote>`) and restarted, IF tmux was set to persist — it doesn't by default, so the session is lost on cold boot. That's fine for "drive it for a few hours" use cases; for "keep it alive across days" see the cron-resume pattern below.

### User connects to drive

From the user's terminal (any box with SSH access to the remote):

```bash
ssh <alias>                      # attaches to 'main' tmux session
# OR with the helper function from .bashrc:
<alias>                          # opens tmux directly
# Inside: Ctrl-B d to detach without killing
```

The user takes over the TUI. They type, they navigate, they exit. The next time they connect, the same session resumes. **The user's terminal is the primary interface; Hermes is a passive observer.**

### Hermes reads but does not interfere

Hermes uses `capture-pane` to peek at what's on screen. Hermes should NOT `send-keys` to type for the user — the user is driving. Hermes' role here is:
- Confirm the TUI launched and rendered correctly
- Diagnose if the user reports a stuck TUI ("what's on screen right now?")
- Capture non-interactive artifacts (like `--format json` output) by reading the buffer

## Sending multi-line prompts: `load-buffer` + `paste-buffer`, NOT `send-keys -l`

For a short literal command, `send-keys` is fine:

```bash
ssh <alias> 'tmux send-keys -t main:0 "ls -la" C-m'
```

For a multi-line prompt, a prompt with shell metacharacters, or a prompt with apostrophes / `$variables` / `&` / `|`, do NOT do this:

```bash
# WRONG — silently fails on multi-line, quoting, or special chars
ssh <alias> 'tmux send-keys -t main:0 -l "long prompt with $variables and '\''quotes'\''"'
ssh <alias> 'tmux send-keys -t main:0 C-m'
# Symptom: capture-pane shows the prompt placeholder is still there, no text in the input box
```

The text never lands in the TUI input. tmux's `send-keys -l` is fine for short literal commands; for prompts with newlines, quotes, or `$` characters, the shell quoting layer eats the content. The TUI's input box stays empty, the placeholder `Ask anything... "Fix a TODO in the codebase"` is unchanged, and opencode is still waiting.

The right primitive is tmux's paste buffer:

```bash
# RIGHT — write prompt as a heredoc on the remote, load into tmux buffer, paste
ssh <alias> 'tmux load-buffer - << "PROMPT_EOF"
Your long multi-line prompt goes here.
It can contain "quotes", $variables, and
newlines without any shell-escape gymnastics.
PROMPT_EOF
tmux paste-buffer -t main:0'
# paste-buffer fills the TUI input and auto-fires Enter in many TUIs (opencode does).
# If the TUI does NOT auto-submit, follow with:
ssh <alias> 'tmux send-keys -t main:0 C-m'
```

Key insight: the heredoc lives on the **remote** shell, so the only thing that has to survive the ssh quoting is the literal text between `<< "PROMPT_EOF"` and the closing `PROMPT_EOF`. Once it lands in tmux's paste buffer on the remote side, `paste-buffer` writes it into the TUI input in a single `bracketed paste` operation. No shell escaping required at the input level.

This pattern works for any TUI taking multi-line input — opencode, claude code, codex, vim, nano. Once you internalize "long input via paste-buffer", you'll stop fighting `send-keys` quoting.

## Permission modals: how to detect and resolve them from the orchestrator

OpenCode's TUI has a permission gate: dangerous operations (Write/Edit to outside-the-cwd paths, Bash with `rm -rf`, file reads outside trust zone) raise a modal that requires user choice. When the user is the one driving the TUI, they press arrow keys + Enter. **When Hermes is the one driving via tmux send-keys, the modal blocks forever — Hermes must resolve it programmatically.**

How to detect a modal: `tmux capture-pane` output contains a literal line `△ Permission required` followed by `← Access external directory X` (or similar) and a row of options like `Allow once   Allow always   Reject`. Modal layouts in opencode v1.15.13:

| Modal state | Default highlight | Keys to send |
|-------------|------------------|--------------|
| Initial: `Allow once` highlighted | first option | `Right` (moves to `Allow always`) or directly `C-m` (accepts `Allow once`) |
| `Allow always` selected | second option | `C-m` (accepts) |
| Confirmation: "This will allow the following patterns until OpenCode is restarted" | `Confirm` highlighted | `C-m` (accepts the confirmation) |
| To Reject | third option | `Right Right C-m` (or `Tab` then `C-m` on some builds) |

The two-step confirmation is intentional friction: you can grant a one-shot (`Allow once`) cheaply, or commit to a session-wide allow (`Allow always`) but it costs an extra Enter. OpenCode does NOT remember `Allow always` across restarts — the grant dies with the process. So if you re-launch opencode in a later session, you'll see the modals again. Plan for that.

Resolution loop from Hermes:

```bash
# 1. Detect modal in capture-pane output
MODAL=$(ssh <alias> 'tmux capture-pane -t main:0 -p -S -25' | grep -c "Permission required")
if [ "$MODAL" -gt 0 ]; then
  # 2. Move highlight to "Allow always" (more durable for the rest of this run)
  ssh <alias> 'tmux send-keys -t main:0 Right'
  sleep 0.3
  # 3. Confirm — triggers the second "until OpenCode is restarted" modal
  ssh <alias> 'tmux send-keys -t main:0 C-m'
  sleep 1
  # 4. Confirm the confirmation
  ssh <alias> 'tmux send-keys -t main:0 C-m'
  sleep 1
  # 5. Verify the modal is gone
  ssh <alias> 'tmux capture-pane -t main:0 -p -S -15'
fi
```

Anti-pattern: ignoring the modal. If you `capture-pane`, see `Permission required`, and walk away, the agent's session is frozen — no commands will run, no other modal will fire, and the user will see a stuck TUI when they connect. Always check capture-pane for modals before assuming the agent is making progress.

Anti-pattern: hammering Enter without reading. The first `C-m` accepts `Allow once` (which may be the wrong choice for a recurring `/tmp/*` pattern that will fire 10 times in this run). Read the option row, decide. For test drives that will write to `/tmp/` repeatedly, jump straight to `Allow always` with `Right` + `C-m` + `C-m` once at the start of the run.

Anti-pattern: trusting the modal between remote detection and the next poll. The modal can re-appear on a different tool call (different path, different pattern). Loop the detection — don't run it once and assume.

## When the brief itself is wrong: agent honesty under bad inputs

OpenCode, when given a brief that contains a bad URL / wrong path / stale name, should refuse to silently work around it. The intended behavior, validated June 2026 in the AetherTest test drive:

- The agent tries the brief as written
- The action fails (404, file not found, etc.)
- The agent does NOT pick a "nearest match" repo / substitute a path / invent a fix
- The agent documents the failure as a BLOCKER with evidence
- The agent asks the user (i.e. the human or the orchestrator) to correct the brief

This is the "naive user" friction pattern: the user typing the wrong URL is itself a friction. The agent's correct response is to surface the friction, not paper over it. If the agent makes a "helpful" substitution, the resulting friction report is dishonest and unfixable.

When orchestrating an opencode agent for an installability test, give the brief the right URL/path the first time. If you don't know it, the test is not ready to run. Validate URLs with `curl -fsS -o /dev/null -w "%{http_code}\n" <url>` before sending the brief; reject anything that returns 404.

## capture-pane options cheat sheet

```bash
tmux capture-pane -t main:0 -p -S -200
# -t main:0    target session:window (window 0 of session 'main')
# -p           print to stdout (otherwise goes to paste buffer)
# -S -200      start from 200 lines back (full scrollback)
#                          use -S - to mean "from the beginning of history"

tmux capture-pane -t main:0 -p -S - -E -    # entire visible history
tmux capture-pane -t main:0 -p -S -50        # last 50 lines
tmux capture-pane -t main:0 -p -J            # join wrapped lines
```

`capture-pane` is **non-destructive** — it doesn't disturb the running TUI. Safe to call as often as needed. This is why it's the right primitive for "Hermes wants to see what's on screen".

## send-keys cheat sheet

```bash
tmux send-keys -t main:0 "ls -la" C-m    # type "ls -la" then Enter (carriage return)
tmux send-keys -t main:0 C-c             # Ctrl+C — interrupt current command
tmux send-keys -t main:0 C-d             # Ctrl+D — EOF / exit
tmux send-keys -t main:0 C-z             # Ctrl+Z — suspend
tmux send-keys -t main:0 Escape          # ESC key
tmux send-keys -t main:0 Up              # Up arrow
tmux send-keys -t main:0 BSpace          # Backspace
tmux send-keys -t main:0 ":wq" C-m       # vim save-and-quit
```

`C-m` is the canonical Enter in tmux send-keys. Some sources use `Enter` or `Return` — `C-m` is portable.

## Why not just use `opencode run` over SSH?

You could, for one-shot tasks. `ssh <alias> "opencode run 'do X'"` works fine for a bounded task. But:
- TUI is for **iterative** work — the user wants to refine prompts, see model output, switch agents
- `run` mode doesn't let the user take over the session
- The TUI shows thinking blocks, agent switching (Tab), model switching (Ctrl+X M) — none of that in `run` mode

So: `opencode run` for agentic one-shots you delegate to a sub-agent; the TUI for the user's primary working interface. tmux-as-state-bridge is the right primitive for the latter.

## Anti-pattern: launching the TUI and then closing the SSH connection

```bash
# WRONG: opens TUI, dies when ssh returns
ssh <alias> "opencode"
# Even with -t, the TUI dies when the ssh call ends (SIGHUP from the pty closing)
```

```bash
# RIGHT: launches TUI inside persistent tmux, ssh returns immediately, TUI lives
ssh <alias> 'tmux send-keys -t main:0 "opencode" C-m'
```

The `tmux new-session -d` + `tmux send-keys` pattern is the same one you'd use to script any long-running interactive process that you want to outlive the script that started it.

## Diagnostic: "I sent the command but capture-pane shows nothing"

Sequence to check, in order:
1. `ssh <alias> 'tmux list-sessions'` — is `main` alive? If not, create it.
2. `ssh <alias> 'tmux list-windows -t main'` — what window index? Default 0, but you may have created others.
3. `ssh <alias> 'tmux capture-pane -t main -p -S -50'` (note: `-t main` not `-t main:0` if you want the current pane of any window) — what's on screen?
4. `sleep 5; ssh <alias> 'tmux capture-pane -t main:0 -p -S -50'` — maybe the TUI just needs more startup time.
5. `ssh <alias> 'which opencode; opencode --version'` — is the binary there and executable? Reuse the cross-shell verification from `aether-agents-orchestration` Pitfall #14 if `which` returns empty in non-interactive mode.

## Detecting "the agent has finished" from outside the TUI

When driving opencode remotely, you need a way to know "the run is done, the agent is idle, I can read the final log". The naive signal — "the input box is empty, asking for the next message" — is unreliable because opencode's TUI doesn't always render a clear "Type your message" prompt. The reliable composite signal, validated June 2026 in the AetherTest installability test drive:

**Composite end-of-task signal (all three must hold):**

1. **Token counter frozen across two polls ≥30s apart.** Parse the status bar: `tmux capture-pane -t main:0 -p -S -5 | grep -oE '[0-9]+\.[0-9]+K \([0-9]+%\) · \$[0-9.]+'`. If the same value appears in two captures 30s apart, the model is no longer consuming tokens — it's idle. The agent's `last_turn` is in scrollback.
2. **Agent stamp visible at the bottom of the screen.** The status bar reads `Build · MiniMax M3 · 8m 48s` followed by `ctrl+p commands`. The "Build · MODEL · TIME" line is the agent persona stamp; the absence of an active spinner/thinking animation alongside the token freeze is a strong idle signal.
3. **The most recent scrollback contains a coherent final response.** A multi-paragraph answer or summary, not mid-thought code, not a tool call, not "..." continuation. The "TL;DR" / "Bottom line" / "## Summary" heading near the bottom of capture-pane is the canonical end-of-task marker for tasks that produce a report.

**Anti-patterns:**

- **Don't trust "prompt appears empty"** — opencode sometimes renders the input box as blank even mid-thought, and sometimes keeps a placeholder "Ask anything..." visible when the agent is done. Use the composite, not the placeholder.
- **Don't trust "X minutes since last token change" alone** — a thinking agent can freeze tokens for 30-60s mid-reasoning, then resume. Require the second poll to confirm freeze.
- **Don't trust `▣  Build` alone** — that line is present at all times once the TUI is on the build agent; it just means the active agent is build, not that the run is done.

**Implementation pattern (silent polling for the user who said "no me avises hasta que termines"):**

```bash
LAST_TOKENS=""
FROZEN_COUNT=0
for i in $(seq 1 60); do  # up to 30 min, polling every 30s
  sleep 30
  STATE=$(ssh <alias> 'tmux capture-pane -t main:0 -p -S -5')
  TOKENS=$(echo "$STATE" | grep -oE '[0-9]+\.[0-9]+K \([0-9]+%\) · \$[0-9.]+' | tail -1)
  if [ "$TOKENS" = "$LAST_TOKENS" ] && [ -n "$TOKENS" ]; then
    FROZEN_COUNT=$((FROZEN_COUNT + 1))
    if [ $FROZEN_COUNT -ge 2 ]; then
      # Tokens frozen ≥2 polls. Verify with a deeper capture that scrollback has
      # a final response, not mid-thought.
      DEEP=$(ssh <alias> 'tmux capture-pane -t main:0 -p -S -60')
      if echo "$DEEP" | grep -qE 'TL;DR|Bottom line|## Summary|## Conclusion|install yes'; then
        echo "TASK DONE at $(date +%H:%M:%S)"
        break
      fi
    fi
  else
    FROZEN_COUNT=0
    LAST_TOKENS="$TOKENS"
  fi
done
```

This pattern is what lets you honor the user's "don't interrupt" instruction without missing genuine completion. The token-freeze + final-report-grep combo is robust against the placeholder-empty false positive.

**Sibling pattern for `talk_to(action="delegate")` (Daimon sessions, not opencode TUI):** use `talk_to(action="poll")` and wait for `status="completed"` OR `clarification_needed=true`. Same silent-polling contract.

## Reference

- `aether-agents-orchestration/references/expanding-team-reach.md` — the L2 SSH setup recipe and boot preflight pattern.
- `aether-agents-orchestration` SKILL.md Pitfall #13 — the 3-Level Ladder (why L2 is the right choice for "I want to drive opencode on another box").
- `aether-agents-orchestration` SKILL.md Pitfall #14 — cross-box verification (login vs non-interactive shell PATH).
