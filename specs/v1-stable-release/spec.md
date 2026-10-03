# Aether 1.0.0 stable release and feature freeze

## Owner decision and authority

On 2026-10-03 the owner declared the current feature set final and directed the stable
`1.0.0` launch («Mira ya no tengo tiempo de continuar trabajando este proyecto así como
está necesito mandarlo a 1.0.0. Ordenar los readmes, las documentaciones, los
tutoriales, destacar la landing page en github, hacer los assets del readme, todo eso
que se tiene que hacer cuando lanzas un proyecto [...] pero de funciones así se quedan
ya no puedo estar resolviéndolos»). In the same session the owner selected English for
the public documentation and authorized these effects:

- normal source integration through a pull request with required checks;
- the annotated tag `v1.0.0`, pushed so the existing `release.yml` workflow builds the
  qualified bundle and creates the public GitHub Release;
- the automatic GitHub Pages deployment caused by the merge;
- repository metadata: website link, description and topics;
- closing #261 and #368 with a pointer to this record;
- the managed local update of the owner's installation from RC19 to `1.0.0`.

It authorizes no PyPI publication, Hermes fork change, credential change, provider-backed
agent campaign or new feature work.

## What 1.0.0 is

`1.0.0` is the RC19 product source unchanged in behavior, plus:

- the stable version identity (package `1.0.0`, tag `v1.0.0`);
- user-facing documentation: a rewritten README, an installation guide, tutorials and a
  reorganized documentation index;
- README and social-preview assets generated from the existing approved artwork;
- the landing page status label and documentation map.

The maintained Hermes fork stays at RC19's pin,
`66e87f3487d75cda3681146818006b7c796a71a9` (`aether-main`). The console scripts
(`aether`, `aether-kanban-worker`) and the three-plugin map are identical to RC19, so
RC19's frozen manager can adopt `1.0.0` directly. No adoption bridge is needed (see the
[RC19 scope](../rc19-local-release/spec.md) for why a shape change would require one).

## Feature freeze and known issues

The owner freezes features at this release. The project is published as-is: open
defects stay open and are documented as known issues, not fixed in this objective.
At release time they are #539, #553, #557, #558, #559, #560 and #561. The enhancements
#316 and #491 stay open without a delivery commitment.

The [#261](https://github.com/DarkArty07/Aether-Agents/issues/261) acceptance items that
this release does not meet are explicitly deferred by the owner, not claimed:

- `start`, `stop`, `restart` and `status` remain explicit unsupported placeholders;
- `aether reconcile` supports only `--to active`;
- `uninstall --export` remains unimplemented;
- installation is the manual release-bundle route through `aether setup`; there is no
  hosted installer, package-index publication or automatic update channel;
- no WSL2 platform qualification and no provider-backed live qualification;
- the PD-74 rolling reliability gate is not passed. Releasing is the owner's decision
  with that gate outstanding, not a reliability PASS or a waiver of its evidence.

## Verification

1. The version identity checks, the full exact-Hermes suite, Ruff, mypy, the
   documentation checker and the website build, check and content tests run on the
   release branch. The required PR checks run without bypass.
2. A local release bundle is built from the exact branch revision and RC19's fork pin.
   The installation guide is then followed in disposable, redirected XDG roots
   (`aether setup --yes`, `aether doctor`, `aether init`, the launch plan) without
   touching the live installation, services or shortcuts.
3. Before the tag push, RC19's own manager inspects the `1.0.0` wheel offline
   (`LifecycleManager._inspect_wheel`) to confirm direct adoption.
4. After the merge, the tag is cut on the merged `main` commit (the release workflow
   requires that equality). The published Release and its assets are checked.
5. The local update runs a `--dry-run` preview, then `--yes`, then `aether doctor`.

On a failed check, stop before the next external effect. A failed live transition uses
only `aether reconcile --to active` or `aether rollback`; no installed release is patched.

## Release conclusions

- `release_impact=major`: the first stable major release. The public surface is
  identical to RC19.
- `release_action=publish`: a public GitHub Release with the qualified bundle.
- `release_channel=stable`.

Source, required-check evidence, the published bundle and installed-state evidence stay
separate claims. This record implies no WSL2 qualification, universal prompt obedience,
PyPI publication or PD-74 reliability result.
