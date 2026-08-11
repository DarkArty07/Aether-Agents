# Configuration

## Tracked and live files

| Tracked | Machine-local |
|---|---|
| `home/config.yaml.template` | `home/config.yaml` |
| `home/profiles/*/config.yaml.template` | `home/profiles/*/config.yaml` |
| `.env.example` files | `.env` files |
| `home/SOUL.md` | sessions, databases, caches and installed binaries |

`scripts/setup.sh` replaces `__AETHER_ROOT__`, `__HERMES_PYTHON__` and legacy-compatible Python placeholders only in generated live config. Existing configured files are preserved.

## Models and profiles

The root template routes Hermes through `openai-codex/gpt-5.6-sol`. The three allowed profile templates use `openai-codex/gpt-5.6-luna` with role-specific fallback providers. A model setting does not authorize a provider call or spend.

Configured auxiliary tasks use `gpt-5.6-luna` where the template names that route. Automatic skill review and curation retain the standard Hermes values: no Aether override of `skills.creation_nudge_interval`, free writes unless Hermes configuration says otherwise, the standard content guard setting, and the curator enabled on its normal schedule.

Supported profile templates are:

- `home/profiles/hefesto/config.yaml.template`;
- `home/profiles/daedalus/config.yaml.template`;
- `home/profiles/ictinus/config.yaml.template`.

## Aether MCP registration

The installer manages the live `aether_mcp` entry and binds these values in its generated launcher: state root, coordinator principal/session, provider CLI, coordinator handle, repository selector, base ref, provider catalog digest and timeout. Do not commit or duplicate the generated absolute paths.

Use `make runtime-status` to inspect registration without printing credentials. Use the installer/activate/rollback scripts for changes rather than editing the generated launcher.
