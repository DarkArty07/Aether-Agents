# Contributing

Keep changes within Aether's versioned design, design-stage specifications, repository policy, and reproducible Hermes profile templates.

- Write canonical documentation and durable system prompts in English.
- Update the artifact that owns a decision before reconciling derived artifacts.
- Keep `ROADMAP.md` shallow; detailed stage content belongs under `specs/<stage>/`.
- Do not commit local configuration, credentials, databases, sessions, memories, logs, caches, or generated runtime state.
- Do not treat design acceptance as authority to implement or activate the design.

Before proposing a change:

1. Run the same canonical-manifest and R0 baseline checks defined in `.github/workflows/policy.yml`.
2. Validate YAML, Markdown links, file modes, and `git diff --check`.
3. Inspect the complete staged diff and confirm no local runtime state is tracked.
4. Record evidence, alternatives, and change impact for material design decisions.

Publication and release are protected external effects and require current authority.
