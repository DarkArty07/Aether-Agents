# Aether runtime home

`home/` combines tracked product assets with ignored machine-local Hermes/Aether state.

Tracked:

- `SOUL.md` — active lean Hermes prompt (`0.4.0`);
- `config.yaml.template` — root configuration template;
- `profiles/{hefesto,daedalus,ictinus}/` — allowed role contracts and templates;
- `skills/` — curated reusable procedures;
- `prompts/hermes/0.4.0/SOUL.md` — byte-exact active prompt archive;
- `prompts/hermes/3.0.0-hot.3/SOUL.md` — byte-exact rollback predecessor.

Machine-local and ignored:

- `.env`, `config.yaml` and generated profile configs;
- `.venv-hermes/`;
- `.aether-mcp/` and `.aether-mcp-state/`;
- sessions, logs, memories, databases, caches, images and backups.

Do not delete or edit live databases to reconcile source. Use the supported status, doctor, activation and rollback scripts. Do not commit runtime state or credentials.

Prompt edits affect only fresh Hermes sessions. The `0.4.0` numbering is a deliberate lean pre-1.0 line reset, not a claim that it sorts after the archived `3.0.0-hot.3` prerelease.
