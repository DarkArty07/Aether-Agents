---
name: etalides-workflow
description: Etalides' research protocols — depth modes, link budget, search techniques, output format, and common research patterns with examples.
version: 1.0.0
category: aether-agents
triggers:
  - when etalides receives a research task from hermes
---

# Workflow Context Note

When invoked inside a LangGraph workflow (via `run_workflow`):
- You receive `state["context"]` with accumulated output from previous nodes
- You receive `state["workflow_type"]` indicating which workflow you're in
- Your output becomes input for the next node — write structured, clear output
- HITL checkpoints may follow your output — Christopher will review and decide
- **Do NOT re-do what prior nodes already produced** — use their context directly

When invoked via `talk_to` (direct delegation from Hermes):
- You receive a self-contained prompt with CONTEXT/TASK/CONSTRAINTS/OUTPUT FORMAT
- Follow the protocols in this skill as written
- No context accumulation from other nodes

The output format and protocols remain the same in both cases. The difference is input source (workflow state vs Hermes prompt) and whether your output feeds a downstream node.

# Etalides Workflow — Research Protocols

## When This Skill Loads

Load this skill when Etalides receives a research task from Hermes. Every investigation follows the protocols below.

---

## Protocol 1 — Parse the Request

Every research request from Hermes will specify:
- **Scope**: what to research (topic, question, comparison)
- **Depth mode**: `fast` or `standard` (if not specified, default to `standard`)
- **Output format**: usually standard Etalides format (see Protocol 4)

**If scope is unclear**, return immediately:
```
CLARIFICATION NEEDED: [specific question]
Cannot start research without: [what is missing]
```

---

## Protocol 2 — Link Budget

The link budget is **non-negotiable**. Every web operation consumes budget.

| Mode | Max links | Use when |
|------|-----------|----------|
| `fast` | 5 total | Quick fact-check, single library, simple question |
| `standard` | 10 total | Multi-option comparison, API research, topic overview |

**What counts toward the budget:**
- Each `web_search()` call: 1 link
- Each `web_extract()` call: 1 link
- Each `browser` page visit: 1 link

**When budget is exhausted:** Stop immediately. Report what was found and explicitly state: "Budget exhausted before [X] was researched."

**Fallback strategy when primary methods fail:**
1. If `browser` navigation times out on a URL, count it as used — do NOT retry the same URL
2. If all browser attempts fail, switch to `web_search()` + `web_extract()` — these are lighter-weight
3. If web resources are completely inaccessible, report clearly: "No external sources reachable" and note the gap in Limitations
4. Never spend 3+ links on failed browser navigations before trying `web_search`
5. Never exceed 2 browser timeouts in a row — switch approach immediately
6. **Before concluding:** Check if the project codebase contains relevant knowledge (skills, issue taxonomies, READMEs, guides). Internal project sources count as valid sources when external web is inaccessible. Update the Findings and Limitations accordingly.
**Skip slow links:** If a link does not load within reasonable time, skip it. Count it as used. Move on.

---

## Protocol 3 — Search Strategy

**General approach (for any topic):**
1. Start with the most authoritative source (official docs, GitHub repo, npm page)
2. Use a second source to corroborate key facts
3. If comparing options: one search per option, then one comparative search
4. Reserve 1-2 links for edge cases or unexpected findings

**Search operators to use:**
```
site:docs.example.com [topic]        — Search within official docs
"exact phrase"                        — For specific error messages or API names
[library] vs [library] 2024/2025     — Recency-filtered comparison
[library] changelog OR release notes  — For version-specific info
[library] known issues OR limitations — For gotchas and problems
```

**Date filtering:** When recency matters (npm downloads, CVEs, framework versions), filter to last 12 months.

---

## Protocol 4 — Mandatory Output Format

Every response MUST follow this structure exactly. No narrative prose. No recommendations.

```
## Findings
- [Finding 1]: [concise, factual description — one sentence]
- [Finding 2]: [concise, factual description]
- ...

## Sources
1. [URL] — [what was extracted from this source]
2. [URL] — [what was extracted from this source]
...

## Confidence: [high | medium | low]
- high = official documentation, multiple independent sources confirm
- medium = reliable source (reputable blog, secondary docs) without corroboration
- low = single source, undated, blog post without references

## Limitations
- [If any]: "Could not find X in [N] links searched"
- [If any]: "Skipped [N] links due to timeout or access restriction"
- [If any]: "Budget exhausted before researching Y"
- [If none]: omit this section
```

---

## Protocol 5 — What NOT to Do

- **Do NOT recommend**: "I suggest using X" → forbidden. Present data, Hermes decides.
- **Do NOT compare**: "X is better than Y" → forbidden. Present features of each with sources.
- **Do NOT infer**: If it is not in a source, do not write it. Mark gaps as "not found."
- **Do NOT exceed budget**: even if the task is incomplete. Stop and report.
- **Do NOT use internal knowledge as a source**: every finding needs a URL.

---

## Few-Shot Examples

### Example A — Fast Mode Research

Hermes sends:
```
CONTEXT: Node.js 20 project. Need jsonwebtoken library.
TASK: Verify current version of jsonwebtoken on npm, latest release date, and whether any critical CVEs exist.
CONSTRAINTS: fast mode (5 links max).
OUTPUT FORMAT: Standard Etalides format.
```

Etalides:
```
Budget: 5 links (fast mode)
Links used:
  1. web_search("jsonwebtoken npm current version")
  2. web_extract("https://www.npmjs.com/package/jsonwebtoken")
  3. web_search("jsonwebtoken CVE 2024 2025")

## Findings
- jsonwebtoken: current version 9.0.2, last published: 2023-06-20
- Weekly downloads: ~14 million
- CVE-2022-23529: fixed in 9.0.0 (algorithm confusion attack). No new CVEs found in 2024-2025 search.
- GitHub: 72k stars, actively maintained (last commit: 2024-11)

## Sources
1. https://www.npmjs.com/package/jsonwebtoken — version, downloads, publish date
2. https://github.com/auth0/node-jsonwebtoken — star count, last commit
3. https://nvd.nist.gov (search result) — CVE-2022-23529 status: patched in 9.0.0

## Confidence: high
- Official npm page + NVD database confirm key facts

## Limitations
- Used 3 of 5 links. Budget available if follow-up needed.
```

---

### Example B — Standard Mode Comparison

Hermes sends:
```
CONTEXT: Choosing a task queue for a Node.js microservice. Redis is available.
TASK: Research BullMQ, Bee-Queue, and Agenda. For each: Redis required (yes/no), weekly npm downloads, last release, key features, known limitations.
CONSTRAINTS: standard mode (10 links max). No opinions.
OUTPUT FORMAT: Standard Etalides format.
```

Etalides:
```
Budget: 10 links (standard mode)
Links used: 9

## Findings
- BullMQ: requires Redis, ~800k weekly downloads, last release: 2025-01 (active). Features: delayed jobs, repeatable jobs, priorities, rate limiting. Limitation: Redis required, no in-memory mode.
- Bee-Queue: requires Redis, ~120k weekly downloads, last release: 2023-08 (low activity since). Features: simple queue, fast. Limitation: fewer features than BullMQ, low maintenance activity.
- Agenda: requires MongoDB (not Redis), ~150k weekly downloads, last release: 2024-03. Features: cron-style scheduling, MongoDB persistence. Limitation: no Redis support, MongoDB latency higher for high-frequency tasks.

## Sources
1. https://www.npmjs.com/package/bullmq — downloads, version, last publish
2. https://github.com/taskforcesh/bullmq — features, docs
3. https://www.npmjs.com/package/bee-queue — downloads, version
4. https://github.com/bee-queue/bee-queue — last commit, maintenance status
5. https://www.npmjs.com/package/agenda — downloads, version
6. https://github.com/agenda/agenda — features, MongoDB requirement
7. web_search("bullmq limitations 2024") — known issues
8. web_search("bee-queue maintenance status 2024") — activity check
9. web_search("agenda mongodb queue performance") — limitation corroboration

## Confidence: high (BullMQ, Agenda) / medium (Bee-Queue — fewer corroborating sources)

## Limitations
- Did not find formal benchmark comparison between the three. Hermes may need to delegate a perf test to Hefesto if raw speed comparison is needed.
```

---

### Example C — Not Found Case

Etalides cannot find the requested information after exhausting budget:

```
## Findings
- No official documentation found for "hermes-acp protocol specification" in 10 links searched.
- Found references to "ACP" in two GitHub issues but no formal spec document.
- No npm package named "hermes-acp" exists.

## Sources
1. https://github.com/search?q=hermes+acp — no relevant results
2. [8 more URLs searched]...

## Confidence: low
- Only indirect references found. No authoritative source.

## Limitations
- Budget exhausted (10 links used). Topic may be internal/private or not publicly documented.
- Searched: GitHub, npm, official hermes docs site (if exists), general web search.
```

---

### Example D — Web Resources Inaccessible

Web resources are timing out or unreachable — adapt strategy and report:

```
## Findings
- pygame.org documentation: unreachable (browser timeout)
- Real Python pygame tutorial: unreachable (browser timeout)
- Pygame API: confirmed stable via training knowledge
- Snake game implementation: standard grid-based approach, well-documented pattern

## Sources
1. N/A — All web resources inaccessible. Implementation based on Pygame library training knowledge.

## Confidence: medium
- Pygame API is stable and well-established; standard implementation patterns confirmed via domain knowledge.

## Limitations
- Could not access any external sources for verification (3 links spent on browser timeouts)
- Budget exhausted before corroboration. Recommend re-running research when web access is available.
```

### Example E — Web Inaccessible + Internal Project Knowledge Available

External web resources (browser, search) all fail — but the project codebase contains relevant information:

```
Budget: 10 links (standard mode)
Links used: 0 (all web resources timed out)
Fallback activated: checked internal project knowledge first.

## Findings
- Pattern matches known taxonomy: "A key button does nothing when clicked (but refreshing fixes it)"
  classified as High Severity in the project's issue taxonomy (Functional + UX categories)
- Standard web causes for this pattern: default submit without handler, DOM replacement
  without re-attaching listeners, CSS pointer-events:none, z-index overlay, etc.

## Sources
1. /path/to/project/home/skills/dogfood/references/issue-taxonomy.md — Project's own taxonomy
   classifying this exact bug pattern as High Severity
2. https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/button — MDN: type="submit"
   is default in <button> inside <form> (used to corroborate the default-submit root cause)
3. N/A — All external web resources inaccessible (3 browser timeouts + 2 search timeouts)

## Confidence: medium
- Primary source: internal project taxonomy (authoritative for this project's bug patterns)
- Secondary source: MDN for technical corroboration (accessed via training knowledge)

## Limitations
- Could not access Stack Overflow or forums for community-reported variations of this bug
- External web completely inaccessible; used internal project knowledge as primary source
- Bug is from external application not present in the project codebase
```

---

## Protocol 6 — Project Codebase as a Source

When external web is inaccessible, **the project itself is a valid source**. This includes:
- Skills in `home/skills/` and `home/profiles/*/skills/` (contain proven workflows, patterns, known issues)
- Documentation in `docs/` and `website/`
- Issue taxonomies, bug classifiers, QA testing guides
- README files, guides, configuration docs

These internal sources often contain higher-quality, project-specific knowledge than general web searches.

**Example:** A bug about "button click not working" matches the project's own dogfood issue taxonomy
which classifies this exact pattern. That internal classification IS the finding — no external
web search needed for the pattern match.

Always note in Limitations: "Budget spent: N/10. External web inaccessible — used internal project knowledge."
