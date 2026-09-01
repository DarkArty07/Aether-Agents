## Description

Describe the policy or configuration change and its user-visible effect.

## Validation

- [ ] The tracked manifest matches policy.
- [ ] Workflow YAML is valid.
- [ ] No local runtime state or secrets are included.

## Documentation / registry impact

- [ ] This changes a public or user-visible surface, so the applicable current docs,
  `docs/capabilities.toml`, and generated reference are updated.
- [ ] Or, this has a specific non-applicability rationale: <!-- explain -->
- [ ] Behavior-preserving internal refactor; no ceremonial documentation churn applies.

## Checklist

- [ ] One logical change per commit
- [ ] Commit message follows Conventional Commits
- [ ] SemVer impact considered
