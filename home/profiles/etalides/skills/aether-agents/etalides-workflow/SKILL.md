---
name: etalides-workflow
description: Etalides' research protocols — depth modes, link budget, search techniques, output format, and common research patterns with examples.
version: 1.0.0
category: aether-agents
triggers:
  - when etalides receives a research task from hermes
---

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
## Hallazgos
- [Finding 1]: [concise, factual description — one sentence]
- [Finding 2]: [concise, factual description]
- ...

## Fuentes
1. [URL] — [what was extracted from this source]
2. [URL] — [what was extracted from this source]
...

## Confianza: [alta | media | baja]
- alta = official documentation, multiple independent sources confirm
- media = reliable source (reputable blog, secondary docs) without corroboration
- baja = single source, undated, blog post without references

## Límites encontrados
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

## Hallazgos
- jsonwebtoken: current version 9.0.2, last published: 2023-06-20
- Weekly downloads: ~14 million
- CVE-2022-23529: fixed in 9.0.0 (algorithm confusion attack). No new CVEs found in 2024-2025 search.
- GitHub: 72k stars, actively maintained (last commit: 2024-11)

## Fuentes
1. https://www.npmjs.com/package/jsonwebtoken — version, downloads, publish date
2. https://github.com/auth0/node-jsonwebtoken — star count, last commit
3. https://nvd.nist.gov (search result) — CVE-2022-23529 status: patched in 9.0.0

## Confianza: alta
- Official npm page + NVD database confirm key facts

## Límites encontrados
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

## Hallazgos
- BullMQ: requires Redis, ~800k weekly downloads, last release: 2025-01 (active). Features: delayed jobs, repeatable jobs, priorities, rate limiting. Limitation: Redis required, no in-memory mode.
- Bee-Queue: requires Redis, ~120k weekly downloads, last release: 2023-08 (low activity since). Features: simple queue, fast. Limitation: fewer features than BullMQ, low maintenance activity.
- Agenda: requires MongoDB (not Redis), ~150k weekly downloads, last release: 2024-03. Features: cron-style scheduling, MongoDB persistence. Limitation: no Redis support, MongoDB latency higher for high-frequency tasks.

## Fuentes
1. https://www.npmjs.com/package/bullmq — downloads, version, last publish
2. https://github.com/taskforcesh/bullmq — features, docs
3. https://www.npmjs.com/package/bee-queue — downloads, version
4. https://github.com/bee-queue/bee-queue — last commit, maintenance status
5. https://www.npmjs.com/package/agenda — downloads, version
6. https://github.com/agenda/agenda — features, MongoDB requirement
7. web_search("bullmq limitations 2024") — known issues
8. web_search("bee-queue maintenance status 2024") — activity check
9. web_search("agenda mongodb queue performance") — limitation corroboration

## Confianza: alta (BullMQ, Agenda) / media (Bee-Queue — fewer corroborating sources)

## Límites encontrados
- Did not find formal benchmark comparison between the three. Hermes may need to delegate a perf test to Hefesto if raw speed comparison is needed.
```

---

### Example C — Not Found Case

Etalides cannot find the requested information after exhausting budget:

```
## Hallazgos
- No official documentation found for "hermes-acp protocol specification" in 10 links searched.
- Found references to "ACP" in two GitHub issues but no formal spec document.
- No npm package named "hermes-acp" exists.

## Fuentes
1. https://github.com/search?q=hermes+acp — no relevant results
2. [8 more URLs searched]...

## Confianza: baja
- Only indirect references found. No authoritative source.

## Límites encontrados
- Budget exhausted (10 links used). Topic may be internal/private or not publicly documented.
- Searched: GitHub, npm, official hermes docs site (if exists), general web search.
```
