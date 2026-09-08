# Project knowledge and role work memory

Aether packages an optional native Hermes plugin, `aether-project-knowledge`, with two tools: `project_knowledge` and `work_memory`. Morfeo, Supervisor and Implementer receive the same action schemas. The Graphify engine is an external, isolated component, not a fork of Hermes and not an MCP requirement.

This build provides local structural indexing, bounded graph exploration, optional read-only
GitHub/visualization views, durable role/project experience records, and an explicit
configured semantic-maintenance path through the existing auxiliary connection. Semantic
extraction, live-agent qualification and any token-savings or universal-quality claim are
not implied by packaging or deterministic tests. See the [capability registry](../reference/capabilities.md)
and [005 specification](../../specs/005-project-knowledge-graphify/spec.md).

## Prerequisites and activation

Use an existing Git repository initialized through [project initialization](project-initialization.md), with its portable marker and registered identity. Indexing reads a committed revision; it never creates commits, rewrites project guidance, runs project hooks or executes source files.

The managed installer requires Linux, `uv`, and an already available Python 3.11 interpreter. It installs the original Graphify 0.9.54 distribution and dependencies using the package-owned hash lock. It does not download Python, enable an agent profile, install Graphify's upstream skills, or register Git hooks.

```bash
aether knowledge install --json
aether knowledge doctor --json
```

Alternatively, an operator may configure an existing isolated interpreter:

```bash
aether knowledge configure --python /absolute/path/to/isolated/bin/python --json
```

`configure` checks Graphify's version but does not certify the transitive dependencies or provenance of an externally managed environment. Use the managed installation when reproducible component provenance is required. The Aether wheel's own interpreter may remain Python 3.11–3.13; Graphify runs in its separate environment.

The portable role templates include the plugin but keep its setting disabled. In each intended profile's configuration, enable it deliberately and make its `aether_knowledge` toolset available through Hermes's normal toolset configuration. The plugin entry should contain:

```yaml
plugins:
  enabled:
    - aether-project-knowledge
  entries:
    aether-project-knowledge:
      settings:
        enabled: true
```

Merge this entry with existing plugins; do not replace the profile's plugin list. Aether-managed profile updates must use the managed configuration path rather than editing an immutable release. Apply the change to new sessions; do not mutate tool schemas or rebuild a conversation's system prompt mid-turn.

Installing the component, enabling the plugin and binding the project are separate facts. None proves that a live agent has used it successfully.

## Project and session selection

The agent cannot submit `role`, `project_id`, `project_path`, `graph_path`, `memory_dir`, environment overrides or an executable to either tool. Aether derives role from the native plugin context and receives the session identity from Hermes's dispatch.

The adapter reads the workspace recorded for that exact native session. It verifies the portable project marker against Aether's existing registry and requires the same Git common directory for an attached worktree. It does not select by project name, current process directory, active/last session or remote URL.

For a session without native workspace metadata, the operator can bind it explicitly:

```bash
aether knowledge bind --project-id PROJECT_UUID --role morfeo --session SESSION_ID --json
```

`PROJECT_UUID` and `SESSION_ID` are placeholders. `--workspace` can select a verified attached worktree. Replacing an existing binding requires `--replace`. Native and explicit bindings must agree; a conflict returns no graph or memory content. Bind each real session, not a generic shared session name.

Switching projects must also be handled at the conversation level: selecting another graph does not erase context already seen by the model. Prefer project-bound conversations. Cross-project analysis should retrieve separately labeled results, not silently merge their indices.

## Daily workflow

Use a narrow graph query when understanding the repository benefits the task. The result already includes revision, coverage and dirty paths; there is no required `status` call before every query. Read the current relevant sources and verify changes with the project's tests. The graph does not replace either.

```json
{"action":"query","question":"Where is objective contract validation implemented?","budget_tokens":2000}
```

### Discovery: query → explain → community

Knowledge discovery proceeds from broad queries to focused inspection without guessing node or cluster identifiers:

1. **`query`**: Search for relevant symbols or topics across the project graph. `traversal`
   accepts `bfs` or `dfs`, `depth` is 1–6, and `context_filter` is a query-only list of
   relation or label filters.
2. **`explain`**: Inspect a specific returned symbol using `node`. The response returns
   `resolved_node` with `{id, community_id, community_name}` (community fields are `null`
   if the node is unclassified).
3. **`community`**: Pass the snapshot-local `community_id` discovered from `explain` to
   inspect community membership and context. The response echoes `{id, name, node_count}`.
4. **Exploration views**: `neighbors` accepts an optional relation filter; `impact` accepts
   `depth` and query-only relation selection; `path` accepts `undirected` for reverse traversal.
   `god_nodes` ranks bounded centrality results. These controls do not change the snapshot.
5. **Repository views**: `list_prs`, `pr_impact` and `triage_prs` use only verified,
   read-only GitHub CLI calls when the project is configured for GitHub. `visualize` writes
   managed graph or tree export handles without changing snapshot bytes. Unavailable GitHub
   or auxiliary access is reported as unavailable, not replaced with another source.

Community IDs belong strictly to the active snapshot. Never treat `0` or any other community ID as a portable default across snapshots or rebuilds; always discover community IDs through `explain`.

All three roles can request an update after relevant committed changes:

```json
{"action":"update","reason":"Refresh the map after the interface and tests changed","mode":"configured"}
```

Skills and agents are instructed to perform or resume configured updates (`mode="configured"`, default) at coherent committed checkpoints whenever covered code or documentation changed, including on integrated main before closeout. Ordinary queries, status checks, and greetings never call a model, and no background watcher is installed.

`changed_paths` may be supplied as a hint, but it is not trusted as a complete change list. Updates capture the selected committed revision from Git objects. Ordinary updates and note writes require no additional per-role approval once the component, task and profile are authorized. If temporary failures occur, at most one bounded retry is allowed; persistent unavailable or deferred work is reported rather than looping to force completion.

Repeated updates of the same view/revision reuse its valid snapshot. Different commits or worktrees do not overwrite each other. A stable external lock serializes managed publication, including the waiting-writer case found in the upstream audit. Readers only see finalized snapshots. A failed build leaves the previous snapshot intact, though a different current revision may require an explicit rebuild before query availability.

An implementation branch describes that branch, not the integrated product. After integration, update from the integrated revision (including integrated main before closeout) instead of union-merging graphs of divergent code. Uncommitted and new files are reported as not indexed and must be read directly.

## Tool actions

| Tool | Actions | Meaning |
| --- | --- | --- |
| `project_knowledge` | `status`, `query`, `explain`, `neighbors`, `community`, `path`, `impact`, `update`, `stats`, `god_nodes`, `list_prs`, `pr_impact`, `triage_prs`, `visualize` | Inspect, maintain and export bounded views of the bound revision's shared technical graph. |
| `work_memory` | `save`, `search`, `read`, `correct`, `reflect` | Maintain experiences belonging to the bound project and role. |

See [plugins and tools](../reference/plugins-and-tools.md) and the [tool/data contract](../../specs/005-project-knowledge-graphify/contracts/tools-and-data.md) for arguments. Both tools use action-discriminated parameter schemas with retained root properties; field descriptions name accepted actions, and runtime validation rejects extraneous or inapplicable fields. Community IDs belong to one snapshot. Impact traversal is not proof of complete runtime impact, and an absent relationship is not evidence that no dependency exists.

Graph query output is bounded using UTF-8 bytes and Graphify's token estimate, not exact provider tokenization. The default requested budget is 2,000 tokens; the supported range is 128–8,000 with a 32,768-byte content ceiling.

### Truncation and supported recovery

The `truncated` indicator is cumulative: it is reported as `true` if Graphify natively omitted nodes or lines at the requested budget, if Aether's 32,768-byte ceiling bounded the response content, or if visible source items reached the 50-reference cap.

When a native Graphify response is complete but exceeds the requested token estimate, it remains `truncated=false` with an explicit warning noting that output exceeded the requested estimate.

When output is truncated or requires refinement, use supported Aether recovery actions:
- Ask a narrower `question`;
- Specify a higher `budget_tokens` within the supported 128–8,000 range; or
- Call `explain` on a returned node to inspect detailed definitions and relationships.

`context_filter` is supported only by `query` and `undirected` only by `path`; they are not
general recovery parameters. Only the Aether actions listed above are supported recovery;
external graph paths, commands and tools are not exposed.

### Provenance and references

Source-bearing actions (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) return structured, project-relative, revision-bound, deduplicated references `{path, location, revision}` in stable order for visible definitions and relation sites. For `path`, references include both path nodes and edge relation sites along the traversal.

References are capped at 50 items. Reaching this cap is never silent: it sets `truncated=true` and emits an explicit warning. Private working-tree or snapshot-internal absolute filesystem paths never escape into references.

## Experiences that survive sessions

Experience records are keyed by project and role. Morfeo, Supervisor and Implementer have separate namespaces. Temporary Implementer instances contribute to the same role/project memory, with task/session attribution when supplied by the runtime; they do not share a Hermes home.

Save a non-obvious outcome when its context is fresh, not every successful command. Record applicability and evidence without credentials or irrelevant conversation content:

```json
{"action":"save","idempotency_key":"wm-save-interface-integration-01","situation":"A focused test passed but integration failed","lesson":"Run the integration test after wiring the changed interface","applicability":"When this interface crosses the component boundary","outcome":"useful","evidence":[],"source_nodes":[]}
```

Every save requires an opaque `idempotency_key` of 8–160 supported ASCII characters. Preserve the same key and exact payload only when retrying one intended save; the replay returns the existing note with `idempotent_replay=true`. Use a different key for a separate contribution, even when its text is identical. Reusing a key with changed content fails explicitly. Aether stores only the key's digest.

An empty evidence list is allowed, but the record is reported, not independently verified. Checking that a referenced file exists does not certify a claimed test result. Prefer references to the actual revision and observations.

`source_exists` checks a literal regular-file entry (including executable files) at the
referenced Git commit. Directories, symlinks, submodules, missing paths and non-commit
revisions do not count as source files. It does not follow the working tree or expand globs.

Search returns excerpts and note IDs. Read the original note, following `next_cursor` until the relevant content is complete. Corrections require the revision returned by the read, preserve prior versions, and replace the effective version for search/reflection. Conflicting corrections do not silently overwrite each other.

`reflect` aggregates native Graphify outcome signals. It does not train model weights or synthesize every answer into a new procedure. Aether explicitly invokes `reflect(..., graph_path=None)` in the component process: it never relies on omitting the CLI's `--graph`, which can auto-detect the shared graph. Notes and reflections stay outside shared graph inputs; no personal `.graphify_learning.json` is written there.

A verified project rule belongs in its canonical documentation or procedure. Promote that rule through the normal authorized change, not by exposing all private notes to the other roles. Learned procedures never override canonical skills.

## Storage and limits

State follows Aether's XDG configuration. The component is under the product data root; published snapshots are in the product knowledge cache; bindings and durable notes are in the product state root. Repository Git contains the adapter, schemas, skills and reproducible dependency selection, not private graphs or notes.

The initial corpus limit is 5,000 selected files, 256,000 bytes per file and 32,000,000 source bytes. Graphs have a 64,000,000-byte ceiling. Unsupported files, symlinks, submodules, LFS pointers, installed dependencies, runtime homes, sessions, logs and high-confidence credential patterns are excluded. A tracked file is not automatically safe or authoritative. These controls reduce accidental inclusion; they are not a complete secret detector or an OS sandbox.

Structural update mode never invokes a model. Configured mode (`mode="configured"`, default)
uses the existing component configuration: when `semantic.enabled` is true it performs or resumes
the selected `semantic.auxiliary_task` (the qualified activation uses `web_extract`) through the
profile-scoped auxiliary connection. Ordinary queries, status checks, and greetings never call a
model, and no background watcher is installed. Semantic metadata reports `state`, covered/pending/
failed paths, a fingerprint and observed usage. Missing, ambiguous or exhausted auxiliary
access is `unavailable`/`partial`, never a primary-model fallback. One bounded retry is allowed
for temporary failures; persistent unavailable/deferred work is reported, not looped.
Rebuilding a new revision captures the selected corpus again; reuse is guaranteed for an
unchanged view/revision, not every possible incremental optimization. This behavior does
not establish token savings or universal quality superiority.


Role search is lexical and limited to 10,000 active notes. Reflection rejects generations above 1,000,000 raw note bytes instead of silently dropping history. Pagination preserves full notes. Further scale and semantic retrieval require separate qualification.

Work-memory `save.applicability` is limited to 4,096 characters; `correct.reason`,
`correct.replacement.applicability` and lesson text allow 16,000 characters. Runtime
validation preserves these action-specific schema limits, including Unicode readback.
Memory component calls reuse the configured backend and its `timeout_seconds` value;
they do not silently reset to the default timeout.

## Reproducible qualification

The repository includes an offline/deterministic lane that exercises the production
service and plugin contracts against disposable, distinct project IDs:

```bash
uv run --frozen python scripts/qualify_knowledge_expansion.py --json
```

The report validates all fourteen project actions and five work-memory actions, updates two
isolated fixtures, checks query/explain/community, traversal controls, statistics, centrality,
visualization, and memory persistence, then disposes the fixture roots. It does not call an
auxiliary model or GitHub. Add `--live-auxiliary` only when the existing active profile has
provisioned auxiliary access; the script reports unavailable or partial live evidence as a
skip. For a real read-only GitHub check, provide an existing registered project and optional
qualified PR number:

```bash
uv run --frozen python scripts/qualify_knowledge_expansion.py \
  --live-auxiliary --project-id PROJECT_UUID --pr-number PR_NUMBER --json
```

The script reads the active component/profile configuration and never accepts or stores a
credential, auxiliary URL, model identifier or alternate provider. A passed offline lane is
not live-agent adoption, a benchmark, a token-saving measurement or a release decision.

## Inspection, deletion and disablement

Operator commands accept a project UUID, role and optional verified worktree:

```bash
aether knowledge export --project-id PROJECT_UUID --role implementer --json
aether knowledge delete --project-id PROJECT_UUID --role implementer --note-id NOTE_ID --yes --json
aether knowledge disable --json
```

Export writes the selected namespace to stdout, not an automatically chosen file. Delete removes the note's retained versions and invalidates its reflection. It cannot delete exported copies or independent backups. Disable stops component-dependent operations; existing notes remain readable through search/read and operator export. It does not remove profile tools mid-conversation or uninstall the component. Component garbage collection and uninstall integration are not exposed in this build.

## Diagnosis and qualification boundary

| Result | Interpretation and next action |
| --- | --- |
| `PROJECT_UNRESOLVED`, `PROJECT_CONFLICT`, `VIEW_MISMATCH` | Check the session binding, registry and worktree; never fall back to another project. |
| `COMPONENT_UNAVAILABLE` | Run component doctor, check the exact isolated interpreter and enablement. No install occurs inside a tool call. |
| `INDEX_MISSING`, `INDEX_CORRUPT` | Rebuild the selected revision; continue with direct files meanwhile. |
| `BUSY`, `TIMEOUT` | Another update or a bounded component operation did not complete; inspect status before retrying. |
| `REVISION_CONFLICT` | Read the current note version before applying a correction. |
| `IDEMPOTENCY_CONFLICT` | Reuse a save key only with its original payload; assign a new key to a distinct note. |
| `SCOPE_UNAVAILABLE`, `RESULT_TOO_LARGE` | Narrow the operation or review documented limits; coverage is not silently invented. |

No callback changes the prompt or automatically invokes a model. Graphify failures do not disable file/terminal tools. Deterministic component/plugin tests do not establish live-agent behavior, production readiness or token savings. Qualification must compare against directed search and reading, include indexing costs, and test modified repositories across sessions.
