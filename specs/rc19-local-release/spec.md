# RC19 bounded local release through the RC18 adoption bridge (#564)

## Owner decision and authority

On 2026-10-03 the owner directed finishing the opt-in Claude Code Implementer objective
(#563), integrating it into `main`, preparing the next release candidate and updating
the local installation, granting the effects that requires («Necesito que ya termines
ese trabajo lo lleves a main, y pases al siguente rc. Actulices lo local. Tienes todo
permitido»). This record carries that release:

- normal source integration;
- immutable local annotated tags;
- package preparation;
- the managed local update through the adoption bridge described below.

Following the RC17 precedent, it pushes no tag and creates no GitHub Release or package
publication. Its only Hermes change is the reviewed maintained-fork guard described below
(HLP-554). It changes no credentials or private configuration, and runs no
agent-behavior campaign or live rollback rehearsal. Normal required PR checks are not
bypassed. Automated Pages consequences of a green merge use the existing workflow.

## Candidate identity and included work

- Package `1.0.0rc19`, display `1.0.0-rc.19`, local tag `v1.0.0-rc.19`, cut from the
  clean merged `main` revision that carries this record.
- Maintained Hermes fork `DarkArty07/aether-hermes` at merge
  `66e87f3487d75cda3681146818006b7c796a71a9` (tree
  `097053ce9ca6b91021a2ba15107fdec9783df11e`). That is RC17's commit
  `007cfb77676b6b024d2c0986f4585e6cfdcf18d6` plus fork PRs #24 and #25 (HLP-554).
- HLP-554 keeps a replayed Codex Responses assistant message id only when it starts with
  `msg`. The installed RC17 runtime carried this guard as a live edit: it fixes #554, and
  it is why `aether doctor` reports the active release as incoherent (#560). Shipping at
  RC17's pin would silently drop that fix from the installation, so the reviewed fork
  source replaces the live edit through the managed path. Every other required HLP and
  its attributed evidence is reused unchanged
  ([HLP-554 evidence](../issue-554-codex-message-id/evidence/HLP-554.md)).
- Source integrated since RC17:
  - the detached-activation project-binding fix (#544);
  - the retirement of the formal Lab, Telegram Monitor and periodic reports
    ([spec](../lab-monitor-retirement/spec.md), #547);
  - Morfeo MCP forwarding of only supplied optional arguments (#556);
  - the documentation reconciliations #545, #548, #549, #551, #555 and #562;
  - the source-versus-release oracle (#550);
  - the opt-in Claude Code Implementer executor
    ([spec](../external-implementer-harness/spec.md), #563).
- Operator-owned configuration remains private and preserved.

## Managed adoption path: the RC18 bridge

Only the active release's manager may coordinate an update, and RC17's manager is frozen.
Its wheel inspection accepts only the console scripts `{aether}` and the exact
four-plugin map that includes the Telegram Monitor entry. RC19 declares
`aether-kanban-worker` (#563) and three plugins (the retirement), so RC17 refuses it with
`candidate public CLI entry point mismatch`. This was reproduced offline with RC17's own
`_inspect_wheel` on the built candidate wheel. The non-mutating `update --local --dry-run`
preview does not build the wheel, so it never reaches that check. This is the
forward-adoption limit of the [retirement plan](../lab-monitor-retirement/plan.md) §2.2,
widened by #563's console script.

The adoption path:

1. **RC18 bridge:** package `1.0.0rc18`, display `1.0.0-rc.18`, local tag
   `v1.0.0-rc.18`. It is cut on a side branch from the RC19 release commit, restoring only
   the historical package shape:
   - console scripts exactly `{aether}`;
   - the four-plugin map, whose `aether-telegram-monitor` entry targets an inert
     `aether_agents.monitor.hermes_plugin` that registers no tool, hook, schedule or
     notification.

   The bridge carries RC19's manager, lifecycle readers, resources and Hermes pin.
   Without the `aether-kanban-worker` launcher the gateway override leaves `HERMES_BIN`
   unset, so the #563 opt-in stays inactive while the bridge is active. The bridge is
   never merged into `main`.
2. RC17's manager accepts the bridge wheel, and the new lifecycle accepts both the bridge
   and the RC19 wheels. Each was verified offline with that manager's `_inspect_wheel`.
3. Two managed cutovers, RC17 → RC18 bridge → RC19. Each runs a `--dry-run` preview
   first, then `--yes`, carrying the verified project identity (`AETHER_PROJECT_ID`).

Installed releases are never patched, and no candidate is rebuilt or retagged to work
around a refusal. The evidence records the exact bridge commit and both cutovers.

## Bounded verification and stop conditions

1. The #563 objective ran its full integrated gate and one replacement isolated real run
   ([evidence](../external-implementer-harness/evidence/EIH-INT.md)). This release adds
   the version identity checks, the full suite on the release branch and the normal
   required PR checks.
2. Prepare each exact clean tagged source through the managed `--local` route.
3. Run each cutover outside the TUI and gateway process trees. Preserve RC17, the bridge,
   mutable state, profile configuration and earlier releases.
4. After the bridge cutover, `aether doctor` must report the bridge coherent before the
   second cutover starts. After RC19, confirm the active identity, `aether doctor`, the
   expected profile resources and the three official plugins. Stop on success, with no
   agent campaign, stress loop or repeated rollback/forward cycle.

On a failed identity check or preview, stop before any live effect. A failed live
transition uses only native compensation, `aether reconcile --to active` or the
supported fallback to the prior release. An unresolved failure is reported, not worked
around with a new candidate.

## Release conclusions

- `release_impact=major`: the retirement removes the public `aether monitor` command and
  the Telegram Monitor plugin within the pre-1.0 line. The harness itself is additive.
- `release_action=prepare`: local candidate preparation, with activation recorded
  separately.
- `release_channel=prerelease`: the RC line continues; this is not stable `1.0.0`.

The bridge shares these conclusions; it is an adoption artifact, not a separate feature
release. Source, required-check evidence, package identity and installed-state evidence
stay separate. This record implies no WSL2 qualification, universal prompt obedience,
public release or PD-74 reliability result.
