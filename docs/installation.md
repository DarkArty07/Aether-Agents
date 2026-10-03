# Installation

This guide installs a managed Aether release from its GitHub Release bundle. A managed
release contains the `aether` manager, an isolated Hermes runtime built from the pinned
maintained fork, the three role profiles (Morfeo, Supervisor, Implementer), the
release-owned terminal UI and the launcher. `aether setup` installs the first release;
`aether update` and `aether rollback` move between releases later.

## Requirements

| Requirement | Why |
| --- | --- |
| Linux on x86-64. WSL2 works but has not been platform-qualified. | The managed runtime, launcher and user service target Linux. |
| A running systemd user session | Setup asks Hermes to install the gateway user service and stops if systemd is unavailable. On WSL2, add `systemd=true` under `[boot]` in `/etc/wsl.conf`, then run `wsl --shutdown` from Windows. |
| [Git](https://git-scm.com/) | Setup verifies the Hermes source as a Git checkout. |
| [uv](https://docs.astral.sh/uv/) | Runs the installer and provides Python 3.11–3.13. |
| [Node.js](https://nodejs.org/) 22 or later, with npm | Setup builds the Hermes terminal UI once from the pinned source. |
| `jq` and `sha256sum` | Used by the commands below to read the release lock and verify checksums. |
| The [GitHub CLI](https://cli.github.com/) (optional) | Downloads the release assets; a browser download works too. |
| An account with a model provider that Hermes supports | Each role needs a configured model. Aether never acquires credentials for you. |

Allow about 3 GB of disk space for the runtime, the Hermes source clone and caches.

## 1. Download and verify the release bundle

```bash
gh release download v1.0.0 --repo DarkArty07/Aether-Agents --dir aether-1.0.0
cd aether-1.0.0
sha256sum --check SHA256SUMS
```

Without the GitHub CLI, download every asset of the
[v1.0.0 release](https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0) into one
directory. The bundle contains:

| Asset | Purpose |
| --- | --- |
| `aether_agents-1.0.0-py3-none-any.whl` | The Aether package installed into the managed runtime. |
| `aether-agents-1.0.0-release-lock.json` | The release lock: the exact Hermes repository, branch, commit, source digest and artifacts. |
| `aether-hermes-source-<commit>.tar.gz` | The pinned Hermes source archive, for provenance and audit. |
| `aether_agents-1.0.0.tar.gz` | The source distribution. |
| `*-provenance.json`, `*-package-members.json`, `*-clean-install.json` | Build provenance, the package member list and the clean-install qualification report. |
| `SHA256SUMS` | Checksums for every asset above. |

Every line of `sha256sum --check` must report `OK`. Stop if any asset fails.

## 2. Clone the pinned Hermes source

Setup builds the runtime from a clean Git checkout of the maintained fork, on branch
`aether-main`, at the exact commit named in the release lock:

```bash
git clone --branch aether-main https://github.com/DarkArty07/aether-hermes.git
git -C aether-hermes reset --hard "$(jq -r .hermes.commit aether-agents-1.0.0-release-lock.json)"
```

Setup refuses a detached HEAD, a different branch or remote, a dirty tree or any other
commit. It never repairs the checkout for you.

## 3. Preview and install

Run the installer from the downloaded wheel with `uvx`, which keeps it in a temporary
environment. Without `--yes`, setup only prints a plan:

```bash
uvx --python 3.11 --from ./aether_agents-1.0.0-py3-none-any.whl aether setup \
  --wheel ./aether_agents-1.0.0-py3-none-any.whl \
  --hermes-checkout ./aether-hermes \
  --release-lock ./aether-agents-1.0.0-release-lock.json
```

Review the plan, then repeat the same command with `--yes` to install and activate the
release. Setup verifies the wheel, the lock, the Hermes checkout and every artifact digest
before it changes anything, and it does not modify another Hermes installation.

An activated release writes only Aether-owned locations:

| Location | Contents |
| --- | --- |
| `~/.local/share/aether/` | Immutable releases, the `runtime/current` selector and components. |
| `~/.local/state/aether/` | Mutable state: Hermes profiles, sessions, boards, memory, observations and the project registry. |
| `~/.local/bin/aether` | The launcher. It always runs the active release. |
| Desktop entries | `Aether` (new session) and `Continue Aether` (resume the latest). On WSL2, matching Windows Terminal actions. |
| `hermes-gateway-morfeo.service` | The Hermes gateway user service for the Morfeo profile, installed by Hermes and set to start on login. |

These paths follow `XDG_DATA_HOME` and `XDG_STATE_HOME` when you set them. Make sure
`~/.local/bin` is on your `PATH`.

## 4. Verify the installation

```bash
aether --version
aether doctor
```

`aether doctor` is read-only. It reports `ready` with the active release ID when the
release record, `runtime/current`, the launcher, the desktop entries, the gateway service
selection and the profiles agree. Any other result names diagnostic codes; see
[limitations and troubleshooting](reference/limitations-and-troubleshooting.md).

## 5. Configure a model for each role

Each role is a Hermes profile with its own home under
`~/.local/state/aether/hermes/profiles/`. Select a provider and model for each one with
the release's Hermes CLI:

```bash
hermes_bin=~/.local/share/aether/runtime/current/runtime/bin/hermes
for role in morfeo supervisor implementer; do
  HERMES_HOME=~/.local/state/aether/hermes/profiles/$role "$hermes_bin" model
done
```

`hermes model` is interactive. Authentication, provider options and model choice are
Hermes behavior: follow the [Hermes documentation](https://hermes-agent.nousresearch.com/docs/).
You may use one provider for all three roles or a different model per role.

Morfeo needs the `file` and `kanban` toolsets, and `aether` refuses to launch it without
them (`missing required Morfeo toolsets`). The packaged profile leaves tool selection to
you, so add them once:

```bash
morfeo_config=~/.local/state/aether/hermes/profiles/morfeo/config.yaml
grep -q '^toolsets:' "$morfeo_config" || printf 'toolsets:\n  - file\n  - kanban\n' >> "$morfeo_config"
```

If the file already has a top-level `toolsets:` list, add `- file` and `- kanban` to it
instead. Optional per-role tool recipes are described in
[tool selection by role](guides/morfeo-tool-configuration.md).

The Supervisor and Implementers run as board workers dispatched by the Hermes gateway.
Start the gateway service once if it is not running yet:

```bash
systemctl --user start hermes-gateway-morfeo.service
```

## 6. Next steps

Continue with [getting started](getting-started.md) to initialize your first project and
launch Morfeo, then follow [your first objective](tutorials/first-objective.md).

## Update to a later release

Download and verify the new bundle and its pinned Hermes source as in steps 1 and 2, then
run the update through the installed `aether`:

```bash
aether update \
  --wheel ./aether_agents-<version>-py3-none-any.whl \
  --hermes-checkout ./aether-hermes \
  --release-lock ./aether-agents-<version>-release-lock.json
```

Without `--yes` this is a preview. With `--yes` it stages and verifies the candidate,
then switches `runtime/current` atomically. Activation may interrupt Aether-owned TUI,
gateway and worker processes immediately, so finish or pause running work first. Your
profiles, credentials, sessions, boards, memory and observations are preserved.

## Roll back

```bash
aether rollback --dry-run
aether rollback --yes
```

Rollback switches the product code, runtime, launcher and service back to the previous
coherent release, or to a version you name. It never rolls your state backward.

## Uninstall

```bash
aether uninstall --dry-run
aether uninstall --yes
```

Uninstall removes the product installation and preserves your state, including
observations. Add `--purge` (with `--yes`) only when you also want to delete Aether's
state. `--export` is not implemented
and reports `EXPORT_NOT_IMPLEMENTED`; back up `~/.local/state/aether/` yourself if you
need a copy.

## Run from source (contributors)

A source checkout is for development and tests, not for daily use:

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
uv sync --frozen
uv run --frozen aether --help
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the test and release workflow.
