# R6 Specification: Protocol and Communication

**Roadmap ID**: R6
**Stage status**: done
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Hermes
**Future role owner**: Morfeo
**Depends on**: R2, R3, R4, R5, `DESIGN.md`
**May affect**: R7, R9, R10, R11
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R6 decides how Aether's parts communicate: between roles, with systems outside Aether, and with the owner.

The stage was scoped as "decide A2A's scope". Direct inspection collapsed that question and replaced it with a more useful one. A2A in Hermes is a **platform adapter** — it sits beside Telegram and Discord in `plugins/platforms/`, not beside the board as a coordination primitive. The question of which transport carries work between roles was therefore already answered by R5, and what remains genuinely undecided is the owner's channel.

R6 does not set concurrency or budgets (R7), decide integration mechanics (R8), choose retention (R9), or design enforcement (R10).

## 2. Three Transports, Three Different Questions

Conflating these produced the assumption that they were alternatives. They are layers.

| Transport | The question it answers | Status in Aether |
|---|---|---|
| MCP | How does an agent obtain tools? | Used outward only (§5) |
| A2A | How do two agents talk across a boundary? | Available, unused (§4) |
| The durable board | Where does work wait when nobody is present? | The only inter-role transport (§3) |

Only the third question is load-bearing for Aether, because the owner is absent by design. A transport that carries a message but holds no state cannot satisfy a requirement whose whole content is *survive my absence*.

- **FR-601**: Aether MUST classify a transport by the question it answers before adopting it, and MUST NOT treat message-passing and work-holding as interchangeable.

## 3. The Board Is the Only Inter-Role Transport

- **FR-602**: Work crossing a role boundary MUST move as a card on the durable board. This restates PD-29 and is not reopened here.
- **FR-603**: In-process delegation MAY be used inside a single worker's run for a bounded reasoning answer. It MUST NOT cross a role boundary.
- **FR-604**: Aether MUST NOT introduce a second inter-role channel. Two channels would mean two records of what work exists, and the board is the record (PD-34).

Upstream states the same boundary in its own documentation: when multiple agents run on one machine, delegation or the board are the intended mechanisms, and A2A is for crossing process, machine, or framework boundaries.

## 4. A2A — Available, Unused, With a Stated Trigger

The A2A plugin is complete and bidirectional. Outbound it provides peer discovery, task send, conversation recall, and capability fan-out. Inbound it serves an agent card and routes incoming tasks into the receiving agent's **live gateway session**.

Aether does not use it, for three reasons that are properties of Aether rather than opinions about the protocol:

1. **Aether has no boundary for it to cross.** Every role runs on one host, as a process under a profile. A2A's stated purpose is crossing process, machine, or framework boundaries.
2. **It would cost a permanent server per callable role.** Parallelism on the board is a concurrency number against one profile; under A2A it is one long-lived HTTP listener per concurrent peer, each with a port and a credential.
3. **It routes into a live session, which destroys fresh context.** A single supervisor session would accumulate every contract it was ever sent. Aether depends on the opposite property: each unit starts with fresh context, which is what makes a reconciling worker impartial (PD-31).

- **FR-605**: Aether MUST NOT use A2A for inter-role work while all roles are co-located on one host.
- **FR-606**: A2A MUST be reconsidered when either of two conditions holds, and MUST NOT be reconsidered merely because it is available:
  - a role must execute on a different machine than the board; or
  - a non-Hermes agent must participate as a role.
- **FR-607**: If either condition is met, the board MUST remain the record and A2A MUST carry only the crossing. Aether MUST NOT move coordination state into the protocol.
- **FR-608**: A2A's inbound adapter MUST NOT be enabled on a profile that also runs unattended work, because inbound tasks join that profile's live session and would interleave with a run in progress.

## 5. MCP — Outward Only

MCP's purpose is exposing tools to an agent. Using it as a work transport inverts the direction: the tool result returns into the caller's context, whereas Aether needs work to leave the caller entirely and survive it.

- **FR-609**: MCP MUST NOT be used to hand work between Aether roles.
- **FR-610**: MCP MAY be used to expose Aether outward — for example, letting an external host create a contract or query pipeline status. That is a legitimate integration surface and belongs to whoever builds it, not to the role model.
- **FR-611**: An outward MCP surface MUST be read-mostly and MUST NOT expose board mutation beyond contract creation, so an external caller cannot reassign or retire work the contract never authorised.

## 6. The Owner's Channel

This is the part of R6 that was genuinely undecided, and R5 left it unaddressed while depending on it: R1 requires that difficulties reach the owner at the end without interrupting him, and named no mechanism.

The runtime provides one. A card's terminal events can carry a subscription with three delivery modes — a passive message, a passive message plus a real turn taken by the destination agent, or a turn with no message. When a card is created from inside a persistent session, that session is subscribed automatically, so its originator is resumed with a synthetic status turn when the card terminates.

- **FR-612**: Morfeo MUST run as a persistent session, because it is the only role the owner converses with and the only role that must be resumable when work terminates.
- **FR-613**: Morfeo's contract card MUST carry a subscription that wakes Morfeo on terminal events. Morfeo assembles the end-of-work report from durable board state, never from memory (R1-FR-122).
- **FR-614**: Supervisor and implementer processes MUST NOT hold owner-facing subscriptions. Only Morfeo speaks to the owner (PD-02).
- **FR-615**: The channel the owner is reached through MUST be a configuration choice, not a design assumption. The design MUST work when the only channel is the terminal the owner returns to.
- **FR-616**: If a messaging channel is enabled, it MUST be attached to Morfeo's profile only, and the accuracy of the originating chat type MUST be preserved, because it determines which session a woken turn resolves to.
- **FR-617**: A woken Morfeo MUST NOT act on the owner's behalf on anything the contract does not already authorise. Waking is a reporting event, not an authority event.
- **FR-617a**: **Review requests wake subscribers too.** Verified in source: requesting review wakes a subscribed originator in the same way a block does, so a subscription is not woken only at terminal events. Morfeo therefore wakes mid-flight whenever same-card review is used, and those wakes MUST be absorbed by Morfeo's own reasoning without reaching the owner (FR-619).

### Why the owner is not the first responder

Christopher's instruction, recorded during this stage: an implementer that gets stuck is resolved *by the system through the supervisor*; only work that cannot be built because something was never defined returns to Morfeo and then to him.

- **FR-618**: The owner MUST NOT be the first responder to a blocked unit. Tier 1 of R7 §5 resolves it without a human.
- **FR-619**: A wake that reaches the owner MUST represent either the end of a body of work or a contract defect that Morfeo could not resolve. Any other wake is a design defect in the role that raised it.

## 7. Evidence

Inspected directly at the recorded revision:

- The A2A plugin lives at `plugins/platforms/a2a/` and is registered as a platform, with outbound client tools and an inbound adapter serving an agent card. It requires a bound port and a bearer credential; without a credential it binds to loopback only.
- Upstream's own guidance places delegation or the board first for same-machine multi-agent work and reserves A2A for crossing process, machine, or framework boundaries.
- The board's documentation declares multi-host explicitly out of scope: the database is a local file and crash detection assumes host-local process identifiers.
- Delivery modes and automatic subscription on creation are documented behaviours of the board's notifier, with subscription defaults active.

Not inspected: the A2A plugin's internals beyond its manifest and tool surface, and the notifier's delivery path. Neither carries an accepted decision here beyond availability, and both are re-read by whoever enables them.

## 8. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Tier 1 escalation must not reach a human; specify the mechanism | R7 |
| Waking Morfeo is a reporting event with no added authority | R10 |
| An outward MCP surface must not permit board mutation beyond contract creation | R10 |
| The end-of-work report is assembled from durable state, not from memory | R11 |
| Enabling a messaging channel is a per-profile configuration decision | R12 |

## 9. Success Criteria

- **SC-601**: No work crosses a role boundary by any mechanism other than a card.
- **SC-602**: Aether runs to completion with A2A absent and no capability is missing.
- **SC-603**: Every owner-facing wake is either an end-of-work report or an unresolvable contract defect.
- **SC-604**: The design functions unchanged when the owner's only channel is the terminal.
- **SC-605**: No Aether component holds coordination state outside the board.

## 10. Done When

- [x] The three transports are separated by the question each answers.
- [x] The board is confirmed as the only inter-role transport.
- [x] A2A's non-use is decided with two explicit reopening conditions.
- [x] MCP is placed as an outward surface and excluded as a work transport.
- [x] The owner's channel is specified, including that the terminal alone suffices.
- [x] The owner is removed from first-responder duty, per Christopher's instruction.
- [ ] Christopher has reviewed the stage.
