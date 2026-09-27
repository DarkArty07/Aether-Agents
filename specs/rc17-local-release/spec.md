# RC17 bounded local release (#542)

## Owner decision and authority

The owner authorizes Morfeo to finish one local RC17 release directly, using existing
reviewed fixes and bounded verification rather than prolonged validation or a new agent
pipeline. This includes normal source integration, an immutable local annotated tag,
package preparation and one managed local cutover. No remote tag, GitHub Release,
package publication, credential change, new feature or live rollback rehearsal is in
scope. Normal required PR checks are not bypassed. Automated Pages consequences of
an authorized green docs merge use the existing workflow; no manual deployment.

The earlier #541 diff-only instruction applies to its source-maintenance delivery.
This release has a distinct, proportionate package and activation boundary; it does
not retroactively claim that those checks ran for #541.

## Candidate identity and included work

- Package `1.0.0rc17`, display `1.0.0-rc.17`, local tag `v1.0.0-rc.17`.
- Clean reviewed Aether revision incorporating the #541 methodology and prior integrated
  source corrections since RC16. Preserve the unrelated local RC6 continuity edit.
- Maintained Hermes fork `DarkArty07/aether-hermes`, exact commit
  `007cfb77676b6b024d2c0986f4585e6cfdcf18d6`, tree
  `b26638974fc134da866b821ab3c4b34ab430aeb3`. Reuse attributed source evidence for
  HLP-433, HLP-435, HLP-460, HLP-473, HLP-474 and HLP-475, making them required for this
  candidate. Presence checking is not new behavioral qualification or upstream retirement.
- Three updated SOULs and applicable skills; `.aether` conventions and expected-behavior
  documentation; public planning skill name `aether-plan` and command `/aether-plan`.
- Operator-owned configuration remains private and preserved. No product-default change
  to the instruction-file confirmation setting follows from a local operator choice.

## Stable resource key, renamed public skill

RC16's exact reader accepts the internal `skills/plan/SKILL.md` inventory and refuses
an additional/renamed directory. Retain that storage key and change frontmatter `name`
to `aether-plan`. Native Hermes selects slash commands and name-based skill loads from
frontmatter, so the owner-visible rename does not require an alias or new inventory.
The existing reader/ownership/rollback algorithms remain unchanged; no bridge release.

The old #504 test module remains frozen evidence for its original `/plan` revision.
Current packaging checks bind the `plan` resource key to public name `aether-plan`;
a disposable native-name check verifies coexistence with a generic learned `plan`.

## Bounded verification and stop conditions

1. Inspect scoped changes and run focused affected instruction/resource/name checks.
   Reuse existing upstream/source reviews. No full local suite duplicated before CI.
2. Integrate through one normal PR/check path, correcting only actual blocking findings.
3. Build the exact clean tagged source. Let the installed RC16 manager inspect its actual
   wheel and preview the transition, binding the unchanged exact resource inventory.
4. Run the managed cutover outside originating TUI/gateway process trees. Preserve RC16,
   mutable state, profile config and the original TUI's release files.
5. After the cutover completes, confirm active identity, diagnostics, expected profile
   bytes and native `/aether-plan` lookup. Stop on success; do not add agent campaigns,
   stress loops or repeated rollback/forward cycles.

On a failed identity or transition preview, stop before live effects. A failed live
transition uses only native compensation or one supported preverified RC16 fallback;
no patching active releases, selector rewriting or recovery-by-new-RC campaign.
Report unresolved failure rather than extending scope indefinitely.

## Release conclusions

- `release_impact=major`: Aether's explicit `/plan` command is replaced, not aliased.
- `release_action=prepare`: local candidate preparation and separately authorized activation.
- `release_channel=prerelease`: continuing the pre-1.0 RC line, not stable 1.0 or 2.0.

Source, required-check evidence, package identity and installed-state evidence are
separate. No new claim of WSL2 qualification, universal prompt obedience, public release
or acceptance of the earlier RC6 objective is implied.
