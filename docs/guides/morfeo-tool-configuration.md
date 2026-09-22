# Tool selection by role

## Ownership and scope

**The documentation belongs in Aether Agents; the actual tool configuration is
local to each user's installation and selected by that user.** This guide records
an owner-selected operating recipe for Morfeo, Supervisor, and Implementer,
including the reasons behind it. It is a reusable reference, not a mandatory
product preset, a universal optimum, or an instruction to invoke every available
tool. The existing filename is retained to preserve links to this guide.

Keep three things separate:

- **This guide:** the selected recipe, its rationale, and decisions explicitly
  deferred for later. It contains no private profile dump or installation paths.
- **Local profiles:** the user's actual Hermes settings, including platform
  toolsets and explicit exclusions. Changing this page does not apply them.
- **Packaged resources and role authority:** the defaults and boundaries shipped
  by Aether. This recipe does not silently modify either or force its selections
  on other users.

Users can adapt local tool selection to their needs within existing role and
safety boundaries. A tool being available grants no new authority. See
[roles and authority](../roles-and-authority.md) and
[artifact ownership](../authority.md). Models, reasoning effort, turn budgets,
credentials, and new delegation workflows are outside this guide's scope.

## Selection at a glance

All three roles keep the shared tools below. The differences appear in the next
table; common exclusions are explained once later in the guide.

### Shared tools

| Toolset | Why all three roles keep it available |
| --- | --- |
| `file` | Inspect instructions and source, make authorized scoped edits, and preserve unrelated work. |
| `terminal` | Run commands, tests, builds, Git inspections, and process checks to ground conclusions in execution. |
| `code_execution` | Batch repetitive tool calls and filter large results when doing so reduces overhead without obscuring evidence. |
| `web` | Research current documentation and extract source evidence without requiring interactive browsing. |
| `vision` | Understand screenshots, designs, diagrams, and visual failures; image analysis is distinct from generation or desktop control. |
| `skills` | Load relevant procedures and maintain reusable knowledge. A skill supplies method, not authority or proof of success. |
| `todo` | Track the current session's steps through context compression. It complements rather than replaces durable tasks and acceptance criteria. |
| `memory` | Preserve appropriate durable context and preferences, not temporary progress or a second copy of project decisions. |
| `session_search` | Recover useful conversation history. Inspect accessible original sources first when the question concerns their current state. |
| `kanban` | Use durable handoffs, task state, collaboration, and review according to each role's responsibility. |
| `aether_knowledge` | Reuse revision-bound project knowledge and role experiences through `project_knowledge` and `work_memory` when the optional component is available. |

Project-specific experiences belong in `work_memory`; personal preferences do not
become project principles. Missing optional knowledge does not block ordinary
source inspection.

### Role-specific selections

**On** means selected in this recipe, not mandatory to use or operationally
qualified. **Off** means not selected; it does not imply uninstallation or missing
credentials. **Deferred** means still off, with a future decision recorded below.
**Reporter only** means selected in the profile but usable only in the restricted
Monitor reporter context.

| Toolset | Morfeo | Supervisor | Implementer | Purpose when selected |
| --- | --- | --- | --- | --- |
| `browser` | Off | On | Off | Conditional UI inspection during review. |
| `delegation` | On | Off | Deferred | Focused sub-analysis for Morfeo; implementation subagents remain a future decision. |
| `cronjob` | On | Off | Off | An owner-requested follow-up, report, or future pipeline start. |
| `aether_contracts` | On | Off | Off | Author and finalize project-bound contracts and prepare their exact handoff. |
| `aether_observation` | On | Off | Off | Read compact contract progress and diagnose only the relevant evidence gaps. |
| `aether_monitor` | On | Off | Off | Inspect or control the separately configured Telegram Monitor within existing authority. |
| `aether_monitor_reporting` | Reporter only | Off | Off | Supply the bounded snapshot for a restricted Monitor reporter run. |

The recipe aligns each role's CLI and Telegram lists. Native dispatch resolves
that role's CLI selection for a worker; this does not imply separate user-facing
Supervisor or Implementer bots. Actual tool exposure still depends on the surface,
worker context, plugin opt-in, project binding, and prerequisites. Absence of an
observation tool alone says nothing about background event capture.

## Morfeo tool configuration

**Purpose:** understand intent, explain decisions, inspect evidence, preserve
context, perform bounded direct work, and hand substantial product work to the
pipeline.

Morfeo uses the shared core for evidence and direct work. Its additional contract,
observation, and Monitor tools support its stewardship responsibilities rather
than create another execution system. `kanban` is for genuine durable pipeline
work, not ceremony for every small request. A completed card is not automatically
an accepted owner objective.

`delegation` supports a focused search or sub-analysis within Morfeo's own bounded
work. It does not replace the Supervisor/Implementer route for product
implementation. `cronjob` is available for requested scheduling, not a reason to
create recurring autonomous work. Delivery depends on the surface and destination.

The current Morfeo role boundary excludes interactive browser execution and
computer use; this is not merely an optional omission in a tool list. Use web
search/extraction, files, and provisioned APIs for ordinary research, and report a
limit rather than route around the boundary through terminal-driven browsing.

`todo` helps retain the current thread, but does not decide when the whole
objective is complete. Likewise, `/plan` is a planning skill, not an execution
lock. Neither is a proven cure for scope expansion or a reason to turn every
request into a planning exercise.

## Supervisor tool configuration

**Purpose:** decompose an accepted contract, coordinate Implementer tasks, review
their evidence, and integrate the result.

The shared tools let Supervisor inspect actual artifacts and run required checks
instead of accepting worker self-reports. `kanban` owns durable coordination;
Supervisor does not need ephemeral `delegate_task` children or its own cron
schedule as a parallel workflow. Its `todo` list tracks the current review or
integration steps, not a second task graph.

`browser` remains available for relevant UI review: checking navigation, a form,
rendering, or console evidence against the requested outcome. It is **not a
mandatory phase for every contract**. Backend-only or documentation work need not
use it. See [browser tools versus automated tests](#browser-tools-versus-automated-tests).

Supervisor is not the owner's conversational interface or an asset-generation
assistant. Image/video generation and TTS are therefore outside this selected
recipe; supplied visual evidence can still be inspected with `vision`.

## Implementer tool configuration

**Purpose:** implement and verify the assigned unit, then deliver its artifact and
evidence through the existing Supervisor review path.

The owner chose the shared core without the interactive `browser` toolset or media
generation. This keeps the selected surface focused on code, documented commands,
research, and reproducible checks. It is a role-specific preference, not a claim
that asset generation or browser automation is never useful in software projects.

Removing `browser` does **not** remove Implementer's testing obligations or
silently transfer them to Supervisor. Run the project's authorized test commands,
including an existing Playwright/E2E suite when required. Do not add another
interactive browser integration merely to recreate the excluded surface.

### Deferred: implementation subagents

The owner favors allowing Implementer to split suitable implementation work into
subagents for greater parallelism. Enabling `delegation` and defining that
workflow were deferred; it remains unselected. This is not a permanent rejection
of subagents or evidence of a demonstrated speedup.

This guide does not introduce new subagents, permissions, decomposition rules, or
review routes. How that future workflow fits the assigned unit and Supervisor's
review remains a later decision.

## Common exclusions and their rationale

These groups are not selected for any of the three roles in this recipe. The
reasons distinguish local preferences from existing role or framework boundaries.

| Toolsets | Reason for exclusion |
| --- | --- |
| `clarify` | Morfeo favors explained conversation over option menus; headless workers have no live owner to answer an interactive prompt. |
| `computer_use` | The owner prefers inspectable file, command, and API operations over unreliable graphical-desktop actions observed in practice. Existing role limits also apply. |
| `context_engine` | No alternative context engine or its additional tools is selected. Normal compression remains active. |
| `image_gen`, `video`, `video_gen`, `bfl` | Image/video generation and video analysis are unnecessary for this chosen baseline. The separate BFL backend must not be overlooked when excluding video. |
| `tts` | Morfeo's interaction is text-first; workers communicate through task handoffs, comments, and review evidence rather than speaking to the owner. |
| `x_search` | No specialized X search integration is needed for the ordinary research covered by `web`. |
| `homeassistant`, `spotify`, `discord`, `discord_admin`, `yuanbao`, `feishu_doc`, `feishu_drive` | These domain-specific service tools are outside the chosen baseline; some are also platform-scoped. |
| `a2a` | Aether currently uses its native Hermes coordination path. Framework availability does not authorize a different communication mechanism. |
| `desktop_ui` | Desktop-panel controls are surface-specific, not a portable CLI/Telegram requirement. |

### Clarification and desktop-control experience

The owner's experience with `clarify` was that it encouraged trivial questions or
presented complex alternatives without enough explanation, as if their meaning
were already obvious. This is qualitative experience, not a benchmark or a claim
that Hermes forces all models to behave that way. Morfeo should explain the
problem, alternatives, and consequences before asking for a necessary decision.
Excluding the tool does not permit guessing missing product intent.

Headless workers have a different reason: unresolved input goes through the
supported Kanban comment/block path. Their existing portable resources explicitly
disable `clarify` and `computer_use`; see
[default worker selection](../reference/plugins-and-tools.md#default-worker-tool-selection).

The desktop-control choice likewise reflects observed model mistakes and limited
value in terminal-oriented environments such as WSL2. It is not a claim that WSL2
cannot run GUI applications or that all desktop agents fail. `vision` remains
available for reading an image without controlling the machine.

### Browser tools versus automated tests

Hermes' native `browser` toolset is not a Playwright MCP installation or a
project's Playwright Test suite. It offers page navigation, structured snapshots,
click/type/scroll actions, screenshots, and console/protocol inspection. Depending
on the backend, the interface can instead be Browser Use's `browser_exec`.
Selection alone identifies neither a working browser nor its local/cloud backend.

Interactive inspection targets web pages rather than the whole desktop, but is
not immune to model mistakes. It can complement reproducible tests, never replace
them or invent a new acceptance gate. Keep any use within the authorized test
environment and requested behavior. See the
[Hermes browser documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser/).

### Context management, speech, and optional integrations

- **Context:** Hermes normally uses the built-in `ContextCompressor`. The
  `context_engine` toolset exposes extra tools from a selected engine plugin;
  `context.engine` chooses the engine separately. Leaving out that toolset does
  not disable compression, memory, or session recall. No alternative engine was
  evaluated and rejected by this recipe. See the
  [context-engine documentation](https://hermes-agent.nousresearch.com/docs/developer-guide/context-engine-plugin/).
- **Speech:** excluding `tts` does not disable transcription. Check `stt.enabled`
  separately; a tool-list display is not proof that speech-to-text is off.
- **Projects:** native TUI/Desktop may expose `project` tools to Morfeo. Workers
  retain their exact Project binding without needing interactive switching tools.
- **MCP:** an already-provisioned documentation server can be an optional addition,
  not a baseline requirement. Configured does not mean loaded or successfully
  connected; keep private server settings out of this guide.
- **Bundles:** `search`, `debugging`, `coding`, and `safe` are subsets or bundles,
  not independent missing engines. Do not enable a broad bundle to recover one
  omitted tool without checking what else it includes.

## Maintaining a user's local selection

The user's choices belong in the intended local Hermes profile, not in a copied
public profile dump or an automatic repository-wide configuration rewrite. Use
the Hermes executable selected by Aether; an unrelated `hermes` on `PATH` may
belong to another installation. Native read-only checks include:

```text
hermes tools list --platform cli
hermes tools list --platform telegram
hermes config get platform_toolsets
hermes config get agent.disabled_toolsets
hermes config get context.engine
hermes config get stt.enabled
```

For an authorized change:

1. Preserve the current profile and unrelated selections. Apply only the chosen
   change with native configuration; do not paste this guide over `config.yaml`.
2. Compare saved and effective selections. Hermes may serialize already-effective
   plugin defaults when saving a toggle; extra explicit entries need inspection.
3. Distinguish configuration, exposure in a fresh agent, prerequisites, and actual
   execution when a probe is needed. A selected tool is not proof of readiness.
4. Let existing sessions/workers reach their normal boundary unless interruption
   is separately authorized. They may retain old schemas until a fresh agent starts.
5. Update the rationale when the user changes the recipe, without promoting that
   choice into a mandatory default for other users or altering role authority.

No credentials, provider installation, live browser qualification, deployment, or
new autonomous process is authorized or demonstrated by this document.

## Related sources

- [Plugins and tools](../reference/plugins-and-tools.md) owns Aether's registration
  and handler boundaries; [capability coverage](../reference/capabilities.md)
  remains the implementation-status reference.
- Packaged resources: [Morfeo](../../src/aether_agents/resources/profiles/morfeo/config.yaml),
  [Supervisor](../../src/aether_agents/resources/profiles/supervisor/config.yaml),
  [Implementer](../../src/aether_agents/resources/profiles/implementer/config.yaml).
- Role instructions: [Morfeo](../../src/aether_agents/resources/profiles/morfeo/SOUL.md),
  [Supervisor](../../src/aether_agents/resources/profiles/supervisor/SOUL.md),
  [Implementer](../../src/aether_agents/resources/profiles/implementer/SOUL.md).
- [Hermes tools documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/)
  owns generic commands and runtime semantics. This guide adds rationale, not a
  second capability registry or configuration-enforcement mechanism.
