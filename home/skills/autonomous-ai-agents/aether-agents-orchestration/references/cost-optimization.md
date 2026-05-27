# Cost Optimization for Aether Agents

Detailed audit methodology and concrete findings from the 2026-05-27 cost analysis session.

## Audit Output (2026-05-27)

### Current Model Assignment

| Agent | Model | Cost Tier | Flag |
|-------|-------|-----------|------|
| Hermes (orchestrator) | deepseek-v4-pro | $$$$ | Reference (baseline) |
| Hefesto (developer) | deepseek-v4-pro | $$$$ | 🔴 SAME AS HERMES — cost leak |
| Etalides (researcher) | deepseek-v4-flash | $$ | ✅ Acceptable |
| Athena (security) | kimi-k2.6 | $ | ✅ Cheapest tier |
| Ariadna (curator) | kimi-k2.5 | $ | ✅ Cheapest tier |
| Daedalus (UX) | mimo-v2-omni | $ | ✅ Cheapest tier |
| Ictinus (backend) | glm-5.1 | $ | ✅ Cheapest tier |

### Current Toolset Assignment

| Agent | Toolsets | Bloat |
|-------|----------|-------|
| Hermes | 10+ (full orchestrator) | N/A — orchestrator |
| Hefesto | terminal, file, search_files, patch, **execute_code** | 🔴 execute_code redundant (has terminal) |
| Etalides | web, browser, file, terminal | ✅ Research-appropriate |
| Athena | file, terminal, skills | ✅ Minimal |
| Ariadna | file, skills | ✅ Minimal |
| Daedalus | terminal, file, search_files, **patch**, **execute_code** | 🔴 patch + execute_code unused (consultant) |
| Ictinus | terminal, file, search_files, **patch**, **execute_code** | 🔴 patch + execute_code unused (consultant) |

### Cost Impact Estimates

```
Hefesto downgrade (pro → flash):     ~60% reduction on 80% of sessions
Hefesto execute_code removal:         ~300 tokens/session saved
Daedalus toolset trim:                ~500 tokens/session saved
Ictinus toolset trim:                 ~500 tokens/session saved
```

### Concrete Recommendations

1. **Hefesto:** `deepseek-v4-pro` → `deepseek-v4-flash` (HIGH priority)
2. **Hefesto:** Remove `execute_code` from toolsets (MEDIUM priority)
3. **Daedalus:** Remove `execute_code`, `patch` from toolsets (LOW priority)
4. **Ictinus:** Remove `execute_code`, `patch` from toolsets (LOW priority)
5. **Hefesto SOUL.md:** Compress ~14K chars → ~8K chars (MEDIUM priority)

### Provider: opencode-go

All Daimons use `opencode-go` provider with `api_mode: chat_completions`. Base URL: `https://opencode.ai/zen/go/v1`.