# Hermes Pure Orchestrator — v0.13.0 Implementation Plan

## Architecture

Hermes stripped to reasoning + delegation. Tools removed from Hermes and transferred to consumer Daimons. This is the highest-impact cost optimization because every tool in Hermes' system prompt burns expensive model tokens every turn.

## Hermes Toolset: Before → After

| Toolset | Before | After | Consumer |
|---------|--------|-------|----------|
| `messaging` | ✅ | ✅ | — |
| `vision` | ✅ | ✅ | — |
| `skills` | ✅ | ✅ | — |
| `todo` | ✅ | ✅ | — |
| `memory` | ✅ | ✅ | — |
| `session_search` | ✅ | ✅ | — |
| `cronjob` | ✅ | ✅ | — |
| `file-read` | ✅ | ❌ → | Etalides |
| `web` | ✅ | ❌ → | Etalides |
| `terminal` | ✅ (platform only) | ❌ → | Hefesto |
| `tts` | ✅ | ❌ | (none) |

## config.yaml Changes (15 edits)

### Remove from toolsets:
- Line 11: `- web`
- Line 12: `- file-read`
- Line 19: `- tts`

### Remove from platform_toolsets.cli:
- Line 480: `- file-read`
- Line 485: `- terminal`
- Line 487: `- tts`
- Line 489: `- web`

### Remove from platform_toolsets.telegram:
- Line 492: `- file-read`
- Line 497: `- terminal`
- Line 499: `- tts`
- Line 501: `- web`

### Delete entire sections:
- Lines 47–70: `terminal:` config block
- Lines 261–285: `tts:` config block
- Lines 397–400: `pre_tool_call` hook (matcher: terminal)
- Line 401: `hooks_auto_accept: false` (if hooks emptied)

### Verify NOT touched:
- Lines 286–302: `stt:` and `voice:` sections — voice INPUT, not TTS output. May keep.
- Lines 33–35: `disabled_toolsets` — no change needed.

## SOUL.md Changes (6 edits)

### §1 — Manifesto (Line 9)
```
"I plan, I decompose, I delegate, I synthesize. I do NOT implement. 
My tools are for reasoning, delegation, and communication — I do not 
read files, search the web, or execute commands myself."
```

### §6 — Delegation Checkpoint (Line 257)
```
3. Quick fact? (<2 web searches) → Route to Etalides via delegate (fast mode)
```

### §6 — Routing Table (Line 273)
```
| Quick fact (< 2 links) | Etalides | delegate (fast mode) |
```

### §6 — Economy Rule (Line 275)
```
Economy rule: Use the minimum necessary Daimon effort. One Daimon? 
Don't involve two. Quick fact? Use Etalides in fast mode (≤5 actions).
```

### §6 — Code Research Rule (Line 277)
```
Code research rule: ALL codebase investigation goes to Etalides. 
Hermes does NOT have search_files, read_file, or terminal. Etalides 
handles everything from single-file look-ups to full project analysis.
```

### §11 — Anti-Patterns (Line 461)
```
| Using talk_to for simple quick facts | Delegate quick facts to Etalides in fast mode |
```

## Consumer Daimon Verification

Before finalizing, verify these Daimons have the needed toolsets:

- **Etalides**: Must have `web`, `file-read`, `terminal` in config.yaml ✓ (verified: web, browser, file, terminal)
- **Hefesto**: Must have `terminal`, `file-read` in config.yaml ✓ (verified: terminal, file, search_files, patch)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Hermes errors with "unknown tool" after conversion | Toolset removal in config.yaml prevents gateway from sending those tools — Hermes' SOUL.md instructions prevent attempts |
| Stale references in SOUL.md say "do it yourself" | Must patch all 4 occurrences (lines 257, 275, 277, 461) |
| `stt`+`voice` removed accidentally with `tts` | stt/voice are input (mic → text), tts is output (text → speech). Verify they're separate before deleting sections. |
| Platform inconsistency | Remove from ALL platform_toolsets (cli + telegram) |

## Experiment Validation (May 2026)

The "Etalides as eyes" pattern was tested: Etalides read 2 large files (config.yaml: 540 lines, SOUL.md: 535 lines), performed 9 tool calls, and produced a complete implementation plan with exact line numbers — all without Hermes using a single file-reading tool. Result: fully viable.