# RC17 activation repair — #542

## Scope and evidence

The owner authorized a focused diagnosis and patch after the existing RC17 activation
failed and the supported reconciliation restored RC16. No new release identity, tag
rewrite, integrity exception, schema change or agent campaign is introduced.

The immutable inputs remain Aether `0eacd1d6e8e9c1fc339daffb27ef1b3d6440170c`
and maintained Hermes `007cfb77676b6b024d2c0986f4585e6cfdcf18d6`. The runtime
candidate is already registered; the source fix below does not claim to alter its bytes.

## Cause reproduced before mutation

The same installed RC16 target-plan call succeeded from the project's terminal but
failed in the independent systemd unit. A read-only diagnostic of the target runner
exposed `branded one-click projections require an exact project binding`.

The unit supplied `AETHER_PROJECT_ROOT` but omitted `AETHER_PROJECT_ID`. The old
lifecycle resolver uses the verified UUID or registry/cwd; its authenticated child
runs from the release root. With multiple registered projects and `project_root=null`
in the request, it cannot recover the caller's project and correctly refuses guessing.
The compensation path also failed and its generic error concealed the original cause.

A second read-only call under the same detached environment with the exact verified
project UUID succeeded (record validation and projection preparation). No installed
code, marker, authority record or observer state was modified by these probes.

## Focused repair

- Resolve the caller's existing project binding before crossing the target-process
  boundary, for both projection preparation and validation. Explicit inputs retain
  precedence; ambiguous or unverifiable default bindings still refuse.
- Preserve original transition and compensation errors in the existing diagnostic.
- The current RC17 operation supplies the verified UUID to the detached unit and
  selects the already registered candidate. It does not rebuild or patch an immutable
  release. The durable code repair is a subsequent source commit, not a claim that
  the original RC17 package already contains that commit.

## Bounded verification

New regressions reproduced both missing-binding subprocess failures and the lost
original error before the source repair. Afterward, eight targeted tests passed,
covering prepare/validate with a verified caller, refusal without a resolvable caller,
original-plus-compensation diagnostics, target import provenance, exact previous-record
restoration and zero-change refusal. Scoped Ruff and diff checks apply; existing
protected repository checks are reused. No live rollback rehearsal, benchmark or
agent-behavior campaign is part of this repair.

Live activation/coherence results belong to the existing objective's cutover receipts
and issue handoff; this source document does not predeclare their success.
