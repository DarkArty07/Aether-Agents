# RC18 bounded local release (#564)

## Owner decision and authority

On 2026-10-03 the owner directed finishing the opt-in Claude Code Implementer objective
(#563), integrating it into `main`, preparing the next release candidate and updating
the local installation, granting the effects that requires («Necesito que ya termines
ese trabajo lo lleves a main, y pases al siguente rc. Actulices lo local. Tienes todo
permitido»). This record carries that release:

- normal source integration;
- an immutable local annotated tag;
- package preparation;
- one managed local cutover.

Following the RC17 precedent, it pushes no tag and creates no GitHub Release or package
publication. It changes no credentials, Hermes fork or private configuration, and runs
no agent-behavior campaign or live rollback rehearsal. Normal required PR checks are not
bypassed. Automated Pages consequences of a green merge use the existing workflow.

## Candidate identity and included work

- Package `1.0.0rc18`, display `1.0.0-rc.18`, local tag `v1.0.0-rc.18`, cut from the
  clean merged `main` revision that carries this record.
- Maintained Hermes fork `DarkArty07/aether-hermes` at RC17's exact commit
  `007cfb77676b6b024d2c0986f4585e6cfdcf18d6` (tree
  `b26638974fc134da866b821ab3c4b34ab430aeb3`). Hermes does not change, and the HLP
  selection with its attributed evidence is reused unchanged.
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

## Managed adoption path

The retirement emits exactly three official plugins. New lifecycle readers also accept
the exact historical four-plugin map. The frozen RC17 manager may still reject the new
three-plugin artifact; this is the forward-adoption limit recorded in the
[retirement plan](../lab-monitor-retirement/plan.md) §2.2. A non-mutating preview
decides the adoption path:

1. Preview with the installed RC17 manager (`aether update --local … --dry-run --json`).
2. If RC17 accepts the candidate, activate it with the same command and `--yes`.
3. If RC17 refuses because of the plugin map, coordinate the same `--local` transition
   with the candidate's own manager from the clean tagged checkout. That manager
   validates the active RC17 record through the exact historical map.

Installed releases are never patched, and the candidate is never rebuilt or retagged
to work around a refusal. The detached transition carries the verified project identity
(`AETHER_PROJECT_ID`), as the lifecycle guide requires. The evidence records the path
actually taken.

## Bounded verification and stop conditions

1. The #563 objective ran its full integrated gate and one replacement isolated real
   run ([evidence](../external-implementer-harness/evidence/EIH-INT.md)). This record
   adds only the identity checks for the version bump and the normal required PR checks.
2. Prepare the exact clean tagged source through the managed `--local` route.
3. Run the managed cutover outside the TUI and gateway process trees. Preserve RC17,
   mutable state, profile configuration and earlier releases.
4. After the cutover, confirm the active identity, `aether doctor`, the expected profile
   resources and the three official plugins. Stop on success, with no agent campaign,
   stress loop or repeated rollback/forward cycle.

On a failed identity check or transition preview, stop before any live effect. A failed
live transition uses only native compensation, `aether reconcile --to active` or the
supported RC17 fallback. An unresolved failure is reported, not worked around with a new
candidate.

## Release conclusions

- `release_impact=major`: the retirement removes the public `aether monitor` command
  and the Telegram Monitor plugin within the pre-1.0 line. The harness itself is
  additive.
- `release_action=prepare`: local candidate preparation, with activation recorded
  separately.
- `release_channel=prerelease`: the RC line continues; this is not stable `1.0.0`.

Source, required-check evidence, package identity and installed-state evidence stay
separate. This record implies no WSL2 qualification, universal prompt obedience, public
release or PD-74 reliability result.
