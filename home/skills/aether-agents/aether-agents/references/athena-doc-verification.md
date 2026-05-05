# Documentation Refactoring Verification Protocol

Moved from Athena SOUL.md on 2026-05-05 during optimization. Retained for reference.

### Protocol 5 — Documentation Refactoring Verification

When asked to verify that a documentation refactoring preserves functionality and doesn't introduce security issues:

**7-step verification process:**
```
1. LOAD SPEC        — Read the PLAN.md or spec defining required changes
2. INVENTORY        — Confirm all target files exist on disk
3. REQUIRED CHECK   — For each file, verify every required section/string is present
4. FORBIDDEN CHECK  — Verify no old/removed references remain (e.g., old workflow names)
5. CROSS-REF CHECK  — Ensure terminology is consistent across all files
6. SECURITY SCAN    — Check for hardcoded secrets, tokens, or credentials in modified files
7. REPORT           — Use Athena output format. If all checks pass → PASSED. Else → list issues.
```

**Checklist per file:**
- [ ] File exists and is readable
- [ ] All sections specified in PLAN.md are present
- [ ] All required strings/phrases are found
- [ ] No forbidden/obsolete strings remain
- [ ] Cross-references to other files use consistent terminology
- [ ] No hardcoded secrets (API keys, tokens, passwords) introduced

**Verification technique — go deeper than `git status`:**
1. Run `git status --short` to see modified files, but do NOT stop there.
2. Run `git diff <file>` for **every** file the spec says should change. A file can appear in `git status` yet contain completely wrong content.
3. Use `search_files` (or `grep -r`) across the entire profile/project tree to verify new terminology (workflow names, HITL options) appears in all expected files and old terminology is absent everywhere.

**Common pitfalls:**
- Plan says "add section X" but file is unmodified → report as MISSING
- File WAS modified, but with completely unrelated content (e.g., wrong protocol injected instead of required section) → report as WRONG_CONTENT. Always diff the file, don't trust `git status` alone.
- Old references exist in comments or appendices even if removed from main text → report
- HITL options or workflow names differ slightly between files → report as INCONSISTENT
- Git status shows only 1-2 files modified when 13 should be → report REFACTORING NOT APPLIED

**Security governance gaps to flag in documentation reviews:**
- `accept_risk` or similar bypass options that allow skipping security fixes without requiring explicit justification or audit-trail logging
- `state["context"]` or similar accumulation mechanisms that propagate data between nodes without sanitization warnings — sensitive data (secrets, PII) can leak downstream
- Missing warnings about secret propagation in multi-node workflows