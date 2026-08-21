# R10 Specification: Security, Trust, and Authority Enforcement

**Roadmap ID**: R10
**Stage status**: done
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — Morfeo operational containment reconciled under PD-44
**Amended**: 2026-08-20 — execution, cron, delegation, skills, and vision surfaces reconciled under amended PD-44 and PD-45
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Hermes
**Future role owner**: Supervisor
**Depends on**: R1, R5, R6, R7, R8, R9, `DESIGN.md`
**May affect**: R11, R12, R13
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R10 decides what Aether protects, from whom, and by what mechanism.

The stage matters more here than in a gated system, because the owner removed the confirmation gate from the normal path (PD-15). Nothing asks him before acting, so protection comes from two places only: effects that can be undone, and effects that are structurally prevented. R10 owns the second.

R10 does not define evidence (R11), select models (R12), or write any hook.

## 2. Threat Model

Aether's threat model is deliberately narrow, and stating it plainly prevents a false sense of protection.

**In scope.** An agent doing something the contract did not authorise. A role acquiring authority it was not given. An irreversible effect performed without anyone noticing. Untrusted content steering a worker. A secret escaping into a durable record.

**Out of scope.** Defending the owner's machine from the owner. Isolating one role from another as security principals. Multi-user or multi-tenant separation.

- **FR-1001**: Aether MUST operate under a single-host, trusted-local-user model, and MUST NOT be described as providing isolation between principals.
- **FR-1002**: The board MUST NOT be treated as a security boundary. Its local database is readable and writable by any process running as the owner.
- **FR-1003**: The runtime's local dashboard plugin routes are unauthenticated by design when bound to a loopback address. Aether MUST NOT bind that surface to a non-loopback address, and MUST NOT rely on it being unreachable.
- **FR-1004**: Every profile MUST use only credentials the owner already provisioned for it. No role acquires, creates, or widens access (R1-FR-114).

## 3. Containment Is Asymmetric

This is verified in the tool registry and must never be overstated. Board routing tools are gated to orchestrators; card creation and linking are gated only on being in board mode, which every dispatched worker is.

| Direction | Mechanism | Strength |
|---|---|---|
| Morfeo selects direct action versus pipeline proportionally | Prompted reasoning over the complete owner objective; no external classifier or gate | **Agentic, not structural or enforced** |
| Morfeo lacks unrelated execution surfaces | Browser execution and computer use are not enabled by amended PD-44 | **Structural where the toolset is absent** |
| A worker cannot enumerate the board | Orchestrator gate | **Structural** |
| A worker cannot release a blocked unit, including its own | Orchestrator gate | **Structural** |
| An implementer cannot create arbitrary work | Instruction plus a blocking hook | **Enforced, not structural** |

- **FR-1005**: Aether MUST NOT claim that role containment is structural in both directions or that Morfeo's proportional route choice is enforced (PD-35). Morfeo has broad file and terminal capability; direct-versus-pipeline selection is agentic self-control. Implementer card-creation containment is enforced.
- **FR-1006**: Where a guarantee is structural, it is primary and any instruction restating it is reinforcement (PD-25).
- **FR-1007**: Where a protected-effect guarantee is not structural, it MUST be enforced by a mechanism that can refuse, not by an instruction alone. Cognitive route selection under PD-44 is not a protected-effect guarantee.

## 4. The Enforcement Point

The runtime supports shell hooks declared per profile, and a pre-tool-call hook can block a tool call before it executes. It can be configured to fail closed, so that an error in the hook denies the call rather than permitting it.

- **FR-1008**: Protected effects MUST be enforced with a pre-tool-call hook configured to fail closed, registered on the profile that must be constrained.
- **FR-1009**: A hook that cannot decide MUST deny. An enforcement point that permits on error protects nothing.
- **FR-1010**: Enforcement MUST be per profile. A single global rule set cannot express that Morfeo may write a contract artifact and an implementer may not.
- **FR-1011**: A hook MUST NOT be used to add capability, only to remove it. Hooks that rewrite arguments to widen what a call does are prohibited.
- **FR-1012**: Every protected effect MUST have exactly one enforcement point, so a denial has one explanation.

### Three properties of the mechanism, verified by execution

The enforcement point is real — a hook fed a forbidden call exited with a block and the runtime parsed it into its block directive. But three properties are narrower than this stage originally assumed, and each is a way enforcement can be present and inert.

**An unconsented hook does not fire at all.** The runtime keeps a first-use allowlist, and a hook absent from it is skipped rather than failed closed. Its diagnostic states it plainly: the hook *will not fire at runtime*. Every effect it was meant to deny is then permitted, while the configuration looks correct.

- **FR-1008a**: Every enforcement hook MUST be confirmed as allowlisted on its profile before that profile does unattended work. Configuration alone is not enforcement.
- **FR-1008b**: Dispatcher-spawned workers are **not** exposed to this gap: the dispatcher passes an explicit accept-hooks flag when spawning, precisely so a worker registers its own profile's hooks. Supervisor and implementer enforcement therefore holds without operator action.
- **FR-1008c**: **Morfeo is the exception**, because it runs as a persistent interactive session rather than a dispatched worker. Any hook constraining Morfeo MUST be consented to explicitly — through its profile's auto-accept setting or a one-time confirmation — or it is inert.
- **FR-1008h**: Morfeo's revised prompt, `file + terminal` toolsets, and reconciled hook policy MUST be prepared while the profile is stopped and activated as one bounded change. The hook continues to enforce independent protected effects but MUST NOT classify task size, block terminal generally, or confine Morfeo to contract-file writes.

**Failing closed is a crash net, not a deny-by-default.** The dispatcher converts a spawn error, a timeout, or malformed output into a block. An ordinary non-zero exit does not block: a hook exiting with an arbitrary error code contributes nothing and the call proceeds.

- **FR-1008d**: A hook MUST deny explicitly, with the runtime's block exit code and a block payload carrying the reason. Aether MUST NOT rely on a non-zero exit alone to deny.
- **FR-1008e**: `fail_closed` MUST be set on every enforcement hook, but MUST be understood as covering only crash, timeout, and malformed output.

**The payload's shape is not what the documentation says.** The documentation describes a top-level arguments key that the runtime does not deliver. A real Phase 4 capture showed `tool_name`, `tool_input`, and `session_id` at the top level; `task_id`, `tool_call_id`, `turn_id`, `api_request_id`, and `middleware_trace` are under `extra`. There is no top-level `args` key.

- **FR-1008f**: A hook MUST be written against the payload the runtime actually delivers, confirmed by capture, not against its documentation. A hook that reads a non-existent key sees an empty value and — for a deny-unless-permitted rule — denies **everything**, halting all work while appearing correctly configured.
- **FR-1008g**: The built-in hook test harness merges a supplied payload into a synthetic one rather than replacing the arguments, so it MUST NOT be used as the only validation of a hook's argument logic.

## 5. Protected Effects

Each row is a thing no instruction can be trusted to prevent, with the role it is enforced on.

| Protected effect | Enforced on | Rule |
|---|---|---|
| Creating work beyond a decision card | Implementer | Card creation is denied unless the card is addressed to the supervisor and declared as a decision card (R7-FR-719) |
| Linking cards for any other purpose | Implementer | Linking is denied unless it attaches a decision card as a parent of the worker's own card |
| Writing a contract artifact | Implementer, Supervisor | Writes to `spec.md` and `plan.md` are denied to both; writes to `tasks.md` are denied to implementers (R8-FR-805) |
| Rewriting shared history | Implementer | Force-push and history-rewriting operations are denied outright (R8-FR-811) |
| Touching a branch it does not own | Implementer | Operations naming a branch other than the worker's own are denied (R8-FR-810) |
| Irreversible external effects | Implementer | Release, deploy, destructive migration, and external destructive calls are denied; they belong to integration (R8-FR-824) |
| Writing secrets into durable fields | All roles | Completion, comment, and metadata payloads matching credential shapes are denied (R9-FR-908) |
| Acquiring or widening credentials | All roles | Credential-provisioning operations are denied (FR-1004) |

- **FR-1013**: The list above MUST be maintained as the definitive enumeration of Aether's protected effects. An effect that is not on it is not protected, and adding one is a design change.
- **FR-1013a**: Morfeo writing project files or using terminal, `code_execution`, `cronjob`, or `delegate_task` for an amended PD-44 objective is not by itself a protected effect. The Morfeo hook MUST NOT deny `execute_code`, `cronjob`, or `delegate_task` as unrelated execution surfaces; it MUST retain transversal secret and credential protections and all Supervisor/Implementer restrictions, while removing only obsolete Morfeo no-execution and contract-only-write containment. Direct-versus-pipeline selection and the rule that delegated subagents assist Morfeo rather than bypassing Supervisor/Implementer MUST remain agentic self-control, following FR-1005/FR-1007, and MUST NOT be implemented as hook enforcement in R10.
- **FR-1014**: A denied call MUST be visible: the worker records what it attempted and why it was refused, so a denial becomes evidence rather than a silent dead end.
- **FR-1015**: A worker that is denied MUST NOT route around the denial. Repeatedly attempting a denied effect is itself a reportable condition.

## 6. Authority

- **FR-1016**: Authority MUST NOT be inherited or self-granted. The supervisor MUST NOT confer on an implementer more than the contract conferred on it, and MUST NOT widen its own (R2-FR-206).
- **FR-1017**: A card body MUST NOT be a channel for granting authority the contract did not grant. Authority lives in `plan.md`; a card instance carries it, never extends it (R2-FR-204a).
- **FR-1018**: Waking Morfeo on a terminal event is a reporting event and confers no additional authority (R6-FR-617).
- **FR-1019**: No role may delete or overwrite work it did not produce without an instruction that covers it (R1-FR-115).
- **FR-1020**: The owner's current instruction outranks every artifact, and every artifact outranks memory (R1-FR-128).

## 7. Untrusted Content

Unattended workers read material Aether did not write: fetched pages, attachments, dependency documentation, and the contents of an existing repository in brownfield work.

- **FR-1021**: Content read during execution MUST be treated as data, never as instruction. A directive found inside fetched or repository content MUST NOT change what a worker does.
- **FR-1022**: A worker MUST NOT expand its own scope on the authority of anything it read. Scope comes from the card body and the contract.
- **FR-1023**: Attachment paths and fetched content MUST NOT be executed merely because a card references them.
- **FR-1024**: Where the runtime already filters inbound content or scrubs outbound credential-shaped strings, that filtering is primary and Aether's instruction is reinforcement.

## 8. What Enforcement Cannot Do

Stating the limits prevents the design from resting on them.

- **FR-1025**: Enforcement MUST NOT be treated as a substitute for reversibility. Most protection in Aether comes from R8's revertibility; hooks cover only what cannot be undone.
- **FR-1026**: Enforcement cannot make a wrong decision safe. A unit that implements the contract incorrectly, within its authority, is caught by review and evidence, not by a hook.
- **FR-1027**: Enforcement runs inside the same trust boundary as the agent it constrains. It raises the cost of a mistake; it does not defend against a hostile local process.

## 9. Evidence

Verified directly at the recorded revision:

- Board tool gating: only board enumeration and unblocking are gated to orchestrator mode; card creation and linking are available to every dispatched worker. Confirmed by reading each tool's registration and its gate function.
- Shell hooks are declared per profile, a pre-tool-call hook can block a call, and it can be configured to fail closed; the block exit code blocks with a reason, while an ordinary non-zero exit is not itself a denial.
- The dashboard's plugin API deliberately skips the authentication middleware, so the board's routes are reachable from any local process when the dashboard runs.
- The runtime filters inbound protocol content and scrubs credential-shaped strings from outbound text on the agent-to-agent surface.

**Verified by execution** in the pass recorded in [`../r13-synthesis-and-release/research.md`](../r13-synthesis-and-release/research.md): a hook fed a forbidden card creation exited with the block code and a block payload, and the runtime parsed it into its wire block directive. The consent gap, the narrow scope of failing closed, and the true payload shape were all established in the same pass and are stated as FR-1008a through FR-1008g.

Phase 4 then verified the installed hook on all three profiles through the real plugin dispatcher: each exact command was allowlisted, each permitted call continued, each tested protected effect returned a caller-visible denial, and making the installed hook non-executable caused the configured `fail_closed` path to block. These tests did not start a worker or model.

Still assumed: that a denial is legible to the worker as an event it can record, since that requires a real worker to be denied.

## 10. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| A denied call is evidence and appears in the record | R11 |
| Repeated denial attempts are a reportable condition | R11 |
| Enforcement is verified before the first unattended run | R13 |
| Morfeo's prompt, file/terminal capability, and independent hook protections are activated coherently | R13 |

## 11. Success Criteria

- **SC-1001**: Every protected effect has exactly one fail-closed enforcement point on the correct profile.
- **SC-1002**: An implementer cannot create work other than a decision card, and the attempt is recorded.
- **SC-1003**: No contract artifact is ever modified by a role that does not own it.
- **SC-1004**: No durable field contains a credential.
- **SC-1005**: No role ends a run with more authority than it started with.
- **SC-1006**: Content read during execution never changes a worker's scope.
- **SC-1007**: Aether's documentation never describes implementer containment as structural.
- **SC-1008**: Morfeo can use file and terminal across the managed project; the hook neither blocks direct work as implementation nor chooses the route, while independent protected effects remain enforced.

## 12. Done When

- [x] The threat model is stated, including what is deliberately out of scope.
- [x] The asymmetry of containment is recorded with the strength of each direction.
- [x] PD-44 supersedes the contract-only Morfeo boundary: file and terminal are operational capabilities, direct-route selection is agentic, and independent protected effects remain explicit.
- [x] The enforcement point is named and required to fail closed.
- [x] Protected effects are enumerated definitively, each bound to a role.
- [x] Authority rules are consolidated and the card is barred as a grant channel.
- [x] Untrusted content is bounded as data.
- [x] The limits of enforcement are stated so the design does not lean on them.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [x] The hook dispatcher was read: failing closed covers spawn error, timeout, and malformed output only; explicit denial is the block exit code plus a payload; the delivered payload shape differs from the documentation. Recorded as FR-1008d to FR-1008g.
