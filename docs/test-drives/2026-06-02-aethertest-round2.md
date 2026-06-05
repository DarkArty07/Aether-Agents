# AetherTest Round 2 — 2026-06-02

**Metadata:**
- **Tester:** opencode v1.15.13
- **Environment:** AetherTest WSL Ubuntu 24.04.3
- **Python:** 3.12.3
- **Repo:** DarkArty07/Aether-Agents v0.15.0
- **Duration:** 8m48s
- **Cost:** \$0.25

---

# Aether-Agents — Installation Friction Report

**Project name (verbatim):** Aether-Agents
**Stated author:** Prometeo / Chris (per Round 1 brief). Corrected in Round 2
to: Christopher (DarkArty07) — see LICENSE & pyproject.toml of the real repo.
**Stated source (Round 1):** `https://github.com/prometeo-aether/aether-agents`
**Stated source (Round 2):** `https://github.com/DarkArty07/Aether-Agents.git`
**Working dir:** /tmp/aether-install
**Date of attempt:** 2026-06-02

This file contains two rounds of install attempts in chronological order.
**Round 1** is the false-start with a wrong URL passed by the user; that
section is preserved verbatim below as a baseline. **Round 2** is the real
attempt against the corrected URL and contains the primary friction findings
for Aether-Agents itself.

---

# Round 1 (URL passed by user was wrong)

## Round 1 — TL;DR

The repository `https://github.com/prometeo-aether/aether-agents` does not
exist on GitHub. The organization `prometeo-aether` does not exist on GitHub.
The literal clone command from the task brief fails. There is no README to
read, no source to clone, and therefore no documented install steps to follow.
This is reported as a single, unresolvable BLOCKER. There is no known-good
fallback, so per the brief I have stopped and not silently substituted a
different repo.

## Round 1 — BLOCKER (cannot proceed)

### R1-B-1. The documented source URL does not resolve to a repository

- **What step:** Step 1 of the brief — "read the README at
  https://github.com/prometeo-aether/aether-agents".
- **What happened:**
  - `GET https://github.com/prometeo-aether/aether-agents` → **HTTP 404**.
  - `GET https://github.com/prometeo-aether` (the org page) → **HTTP 404**.
  - `GET https://github.com/prometeo-aether/aether-agents/blob/main/README.md` → **404**.
  - `GET https://raw.githubusercontent.com/prometeo-aether/aether-agents/main/README.md` → **404**.
  - `GET https://raw.githubusercontent.com/prometeo-aether/aether-agents/master/README.md` → **404**.
  - `git ls-remote https://github.com/prometeo-aether/aether-agents.git` → could
    not even handshake (the org namespace is unknown to GitHub).
- **What the README said vs reality:** There is no README to compare against.
  The implied premise of the brief — that a public README exists at that URL
  describing the install — is false.
- **Fix / workaround tried:**
  - Case-flip on the org: `Prometeo-Aether/aether-agents` → still 404.
  - Case-flip on the repo: `aether-agents` ↔ `Aether-Agents` ↔ `AetherAgents` —
    irrelevant, the org is the failure point, not the repo name.
  - Adjacent user: a real GitHub user named `Prometeo` (handle: "Xairi
    Prometeo", Peru, 4 followers) exists at `https://github.com/Prometeo` with
    27 repos (emacs config, dotfiles, Django cookbook, leetcode exercises,
    etc.). None are Aether-Agents. This appears to be a name collision, not
    the intended author, and switching to it would be a silent workaround
    forbidden by the brief.
  - GitHub code search for `aether-agents` returns 88 hits (e.g.
    `DarkArty07/Aether-Agents`, `Sebby1770/AetherAgents`,
    `msu-denver/bili-core` which contains a sub-project called AETHER,
    `mesanford/aether-agents`, etc.). None are at the `prometeo-aether` org
    and none credibly match the "by Prometeo / Chris" attribution at the
    time. Picking one of these would be a silent workaround, so it was not
    done.
- **Severity:** **BLOCKER.** Steps 1, 2, 3, 4, 5 of the install path all
  depend on having a clone. Without a clone there is no `requirements.txt`,
  no `pyproject.toml`, no Makefile, no install script, no docker-compose,
  nothing to execute. The install cannot start.
- **Known-good fallback:** **None.** I will not invent one. The brief
  explicitly forbids silent workarounds ("If a step fails or is ambiguous, do
  NOT silently work around it. Stop, log the friction, and continue only if
  you can document a known-good fallback.") and there is no documented
  fallback for "the entire repo is missing."

### R1-B-2. The literal clone command from the brief fails with a misleading error

- **What step:** Step 2 of the brief — "Use
  `git clone https://github.com/prometeo-aether/aether-agents.git /tmp/aether-agents`
  if no path is given."
- **What happened:** With `GIT_TERMINAL_PROMPT=0` (i.e. no interactive
  auth), the command produced:
  ```
  Cloning into '/tmp/aether-agents'...
  fatal: could not read Username for 'https://github.com': terminal prompts disabled
  ```
  Exit code: `128`. No directory was created at `/tmp/aether-agents`.
- **What the README said vs reality:** Again, no README. The brief assumes
  the command succeeds. It does not.
- **Fix / workaround:** None. The error message is also actively misleading
  (see R1-M-1 below) — it suggests an auth problem, not a missing repo.
- **Severity:** **BLOCKER** (in conjunction with R1-B-1; this is the symptom
  of the same root cause).

## Round 1 — MAJOR (works but ugly)

*(None observed — no install steps were reached, so there is nothing that
"works but ugly" to report.)*

## Round 1 — MINOR (cosmetic)

### R1-M-1. GitHub / libgit2 error message misleads on a 404 namespace

- **What step:** Step 2 (the `git clone` itself).
- **What happened:** When cloning a URL whose org does not exist on
  GitHub.com, modern `git` should surface "repository not found". Here it
  surfaced "could not read Username ... terminal prompts disabled", which
  reads like an auth/credential problem. A first-time user would reasonably
  start debugging SSH keys, PATs, or `git credential helper` config —
  none of which would fix a missing org.
- **What the README said vs reality:** No README. But the brief's implicit
  assumption is that the clone works. It doesn't, and the diagnostic points
  the user at the wrong problem.
- **Fix / workaround:** None at the user level — this is upstream behavior.
  A more helpful local fallback would be to first `curl -fsS -o /dev/null
  -w "%{http_code}\n" https://github.com/prometeo-aether` and only attempt
  the clone on a 200/3xx. (Not done here, because the goal of this run is
  to record what a naive user would experience, not to script around it.)
- **Severity:** **MINOR** in the context of a task that is already fully
  blocked by R1-B-1/R1-B-2. Would be **MAJOR** in a context where the repo
  did exist and only the error message was confusing.

## Round 1 — What I did NOT do, and why

Per the brief, I did not:

1. **Substitute a different repository.** There are at least six other
   GitHub repos named `Aether-Agents` / `AetherAgents` / `aether-agents`
   from unrelated authors (DarkArty07, Sebby1770, Dartans, bharat948,
   dheeraj7000, mesanford). Installing any of them and writing up "it
   works" would be a silent workaround and would also produce a dishonest
   friction report attributed to a project that is not Aether-Agents.
2. **Guess at install steps from the project name alone** (e.g. assume
   `pip install aether-agents`, assume a PyPI release, assume a Docker
   image). No such assumption is documented; inventing one is exactly the
   silent-workaround behavior the brief prohibits.
3. **Fabricate a friction report for a successful install.** The brief
   says "Do not skip the friction log - that is the primary deliverable,
   not the install success." The friction log is the deliverable. It is
   delivered. The install success is not, because it cannot be.

## Round 1 — Recommended next action for the user (i.e. for Chris / Prometeo)

1. Confirm whether the repository was renamed, moved, made private, or
   deleted. If moved: re-run this same exercise against the new URL and
   this friction log becomes a clean baseline.
2. If the org was renamed, the README link should be updated in any
   public materials pointing at `prometeo-aether/aether-agents`. As of
   this run, every link in that form returns 404.
3. If the project is intended to be public, verify the org
   `prometeo-aether` exists and is not, e.g., a personal account that was
   renamed or deleted.
4. Re-issue the install brief with a working URL, and the rest of steps
   2–5 of the original task can be executed against the real repo.

## Round 1 — Evidence appendix

Commands run, with results:

| # | Command | Result |
|---|---|---|
| 1 | `webfetch https://github.com/prometeo-aether/aether-agents` | HTTP 404 |
| 2 | `webfetch https://github.com/prometeo-aether` | HTTP 404 |
| 3 | `webfetch https://github.com/prometeo-aether/aether-agents/blob/main/README.md` | HTTP 404 |
| 4 | `webfetch https://raw.githubusercontent.com/prometeo-aether/aether-agents/main/README.md` | HTTP 404 |
| 5 | `webfetch https://raw.githubusercontent.com/prometeo-aether/aether-agents/master/README.md` | HTTP 404 |
| 6 | `webfetch https://github.com/Prometeo-Aether/aether-agents` | HTTP 404 |
| 7 | `webfetch https://github.com/Prometeo-Aether` | HTTP 404 |
| 8 | `webfetch https://github.com/Prometeo` (user page) | 200, but 27 unrelated repos, no aether-agents |
| 9 | `webfetch https://github.com/search?q=aether-agents&type=repositories` | 200, 88 unrelated hits |
| 10 | `mkdir -p /tmp/aether-install` | OK (working dir created) |
| 11 | `GIT_TERMINAL_PROMPT=0 git clone https://github.com/prometeo-aether/aether-agents.git /tmp/aether-agents` | exit 128, "fatal: could not read Username ...", no directory created |

No install command beyond step 11 was reachable.

---

# Round 2 (URL corrected to DarkArty07/Aether-Agents)

## Round 2 — TL;DR

After Chris corrected the URL, install **succeeded end-to-end** for the
core flow (`git clone` → `bash scripts/setup.sh` → `make doctor` →
`hermes --version`). 70+ transitive packages pulled, venv created,
`olympus_v3` importable, all six daimon `config.yaml` files generated, five
of six daimon `.env` files created, `aether` / `hermes` / `aether-setup`
wrappers in `~/.local/bin`, and `HERMES_HOME` export in `~/.bashrc`. The
Hermes binary works: `hermes --version` reports
`Hermes Agent v0.15.2 (2026.5.29.2)`.

But there is **one true BLOCKER** for the documented "memory provider"
path (`make setup-honcho`): the pinned git submodule commit for
`honcho-server` is unreachable in the upstream repo, so the memory layer
is unbuildable on a fresh install. And there are a handful of MAJOR
frictions that won't stop a patient user but will absolutely trip a
first-time one.

## Round 2 — Environment (baseline for reproducing)

| Item | Value |
|---|---|
| Working dir | `/tmp/aether-install` (empty) |
| Clone target | `/tmp/aether-agents` |
| Cloned URL | `https://github.com/DarkArty07/Aether-Agents.git` |
| Result of `git clone` | exit 0, full repo, 209 commits on `main` |
| Python | 3.12.3 (`/usr/bin/python3.12`) — meets 3.11+ requirement |
| `pip` on host PATH | **not present** (`/usr/bin/python3: No module named pip`) — does not block install because venv bootstraps its own |
| `nvidia-smi` | not present — setup.sh correctly skips faster-whisper |
| `docker` | not present — would block `make setup-honcho` step 5 even if the submodule worked |
| Kernel | `6.6.87.2-microsoft-standard-WSL2` — setup.sh's WSL detection correctly fires |
| Pre-existing `~/.bashrc` | contained a stale `HERMES_HOME` export from a prior install at a different path; setup.sh's logic does not overwrite this — see M-R2-1 |
| Pre-existing `~/.local/bin/aether` and `~/.local/bin/hermes` | also from prior install, pointing to a different venv; setup.sh **does** overwrite these (wrapper content differs) |

## Round 2 — BLOCKER (cannot proceed)

### R2-B-1. `make setup-honcho` fails on a fresh install: the pinned submodule commit is unreachable

- **What step:** README §"🧠 Memory Provider (Honcho)" — "`make setup-honcho`"
  to set up the Honcho memory layer, which is the only way to get the
  "89 Skills", "Cross-session context recall", and ".aether Continuity"
  features described in the README's key features table.
- **What happened:**
  ```
  $ make setup-honcho
  [1/5] Initializing git submodules
  Submodule 'honcho-server' (https://github.com/plastic-labs/honcho.git) registered for path 'honcho-server'
  Cloning into '/tmp/aether-agents/honcho-server'...
  fatal: remote error: upload-pack: not our ref 887223ef9685076e81d17505a843def3be3a6384
  fatal: Fetched in submodule path 'honcho-server', but it did not contain 887223ef9685076e81d17505a843def3be3a6384. Direct fetching of that commit failed.
  ✗ Submodule update failed
  make: *** [Makefile:26: setup-honcho] Error 1
  ```
  The submodule is pinned (in `.gitmodules` and the superproject's gitlink)
  to commit `887223ef9685076e81d17505a843def3be3a6384` of
  `plastic-labs/honcho`, and that commit is no longer reachable on the
  upstream (presumably force-pushed, amended, or removed). A plain
  `git submodule update --init --recursive` (the same command
  `setup-honcho.sh` runs at step 1/5) fails the same way.
- **What the README said vs reality:** README §"Memory Provider (Honcho)" →
  "Setup: `make setup-honcho` — This initializes the Honcho git submodule,
  generates honcho-server/.env from template (using your
  OPENCODE_GO_API_KEY), and starts all services." That implies the
  submodule step is a guaranteed-success operation. It is not.
- **Why I stopped:** No known-good fallback. The next-action choices for
  the user are: (a) repoint the submodule to a current upstream commit
  and hope it still applies, (b) remove the memory-provider feature, or
  (c) vendor a known-good snapshot of honcho-server into the repo.
  None of these are documented.
- **Severity:** **BLOCKER** for the documented Honcho / memory-provider
  feature path. **Not** a blocker for the rest of Aether-Agents — the core
  install via `bash scripts/setup.sh` succeeds without it. But the README
  advertises the memory features prominently (6 of 8 feature bullets), so
  a user who wants what was promised cannot get it on a fresh install.

## Round 2 — MAJOR (works but ugly)

### R2-M-1. `setup.sh` does not update a stale `HERMES_HOME` in `~/.bashrc`; the wrappers and the env var silently disagree

- **What step:** Step 8 ("Creating wrapper scripts") and step 9
  ("Configuring shell environment") of `setup.sh`.
- **What happened:** I had a previous install of Aether-Agents at
  `/tmp/opencode/aether-install/Aether-Agents/`. The previous run had
  written:
  - `~/.bashrc`: `export HERMES_HOME="/tmp/opencode/aether-install/Aether-Agents/home"`
  - `~/.local/bin/aether` / `~/.local/bin/hermes`: wrappers pointing to
    the old venv.
  When the Round 2 `bash scripts/setup.sh` ran, it:
  - Correctly detected the old wrappers' content differed from the new
    content and **overwrote** `~/.local/bin/aether` and `~/.local/bin/hermes`
    to point at the new venv. (Step 8 of the script: ✓ aether → ...; ✓
    hermes → ...; ✓ aether-setup → ...).
  - But in step 9 it ran
    `if grep -qF "HERMES_HOME" "$bashrc" 2>/dev/null; then ok "HERMES_HOME
    already configured in ~/.bashrc — skipping"`, matched the old export,
    and **did not touch it**. So my `~/.bashrc` still says
    `HERMES_HOME=/tmp/opencode/aether-install/Aether-Agents/home`, which
    is a directory that no longer exists.
- **What the README said vs reality:** README §"⚡ Quick Start" says "Edit
  `.env` with your API keys, **restart your terminal**, and run `aether`."
  The expected mental model is "restart terminal → env is right". For a
  user who re-installs in a new path, the reality is "restart terminal →
  `HERMES_HOME` points to a dead path; `aether` exec's the right hermes
  binary but with a wrong `HERMES_HOME` env var; downstream features
  that look up `home/profiles/*/config.yaml` via `HERMES_HOME` may load
  stale or missing config."
- **Why this is MAJOR not MINOR:** The wrappers and the env var are now
  asymmetric. A user following the README cannot easily tell the
  difference — `aether --help` works (it execs the right hermes binary,
  with the wrong env var). Latent breakage is hidden until the user
  exercises a feature that reads `HERMES_HOME`.
- **Fix / workaround:** Edit `~/.bashrc` manually, find the existing
  `HERMES_HOME` line, update the path, `source ~/.bashrc`. (Or nuke the
  old export and re-run `setup.sh`.) setup.sh itself could fix this by
  detecting an existing `HERMES_HOME=` and replacing the whole line via
  `sed_inplace` instead of just `grep -qF ... && skip`.
- **Severity:** **MAJOR.**

### R2-M-2. `setup.sh` does not create `home/.env` (the orchestrator-level env file), but `INSTALLATION.md` says it is required

- **What step:** Step 6 of `setup.sh` ("Setting up .env files from
  templates"). Also affects `scripts/setup-honcho.sh` step 3/5.
- **What happened:** `setup.sh` only iterates
  `home/profiles/*/.env.example` and copies them to per-profile
  `home/profiles/*/.env`. It does **not** create `home/.env` itself.
  The Round 2 install log shows step 6 created exactly five files:
  `ariadna/.env`, `athena/.env`, `daedalus/.env`, `etalides/.env`,
  `hefesto/.env` — but no `home/.env` at the top of the `home/` dir.
  `INSTALLATION.md` §6.1 says:
  > Edit the `.env` file in each profile to set your API keys. **At
  > minimum, configure the orchestrator:** `nano home/.env`
  So the orchestrator-level env is documented as required, but the
  install script does not produce it. The "Next steps" output of
  `setup.sh` likewise only points the user at
  `home/profiles/*/ .env`, omitting `home/.env`.
- **What the README said vs reality:** `setup.sh` says "Next steps: 1.
  Edit API keys in profile .env files: /tmp/aether-agents/home/profiles/*/ .env".
  Reality: the profile envs alone are not enough — the orchestrator env
  is also required.
- **Downstream consequence:** `scripts/setup-honcho.sh` step 3/5
  (`Reading API keys from home/.env`) will fail with
  `home/.env not found at /tmp/aether-agents/home/.env` if you reach that
  point before creating `home/.env` by hand.
- **Fix / workaround:** `cp home/.env.example home/.env` if such a
  template exists; otherwise create `home/.env` with the keys documented
  in `INSTALLATION.md` §6.1. (For Round 2, I did not pursue this because
  the Round 2 install was not configured to actually exercise the
  orchestrator, and the Honcho path is already blocked by R2-B-1.)
- **Severity:** **MAJOR** (silent omission of a documented prerequisite
  in the auto-generated install).

### R2-M-3. `setup.sh` silently skips the ictinus profile for `.env` generation without explaining why

- **What step:** Step 6 of `setup.sh`.
- **What happened:** Five of six daimon profiles got a `.env` from
  `.env.example`. The sixth — `ictinus` — did not. The script just
  prints five "created from .env.example" lines and stops, with no
  message about ictinus. Inspection: `ictinus/` contains only
  `SOUL.md`, `config.yaml`, `config.yaml.template`, `plugins/`. There is
  no `ictinus/.env.example`. Other daimons all have one.
- **What the README said vs reality:** README §"🎭 The Daimons" says
  ictinus is "Backend Architect, Level 1" and explains "Level 2 Daimons
  execute tasks. Level 1 Consultants provide expert input when
  summoned." The install script does **not** surface this asymmetry. A
  naive user reading the step-6 output sees "5 created" and may assume
  their install is broken or that they need to add an ictinus env by
  hand.
- **Fix / workaround:** None needed functionally — the absence of an
  ictinus `.env` is by design (consultants don't run tasks). But the
  script should print an info line like
  `→ ictinus: no .env.example (Level 1 Consultant — config-only)` so
  the user isn't left wondering.
- **Severity:** **MAJOR** (silent omission, but not blocking; the
  install is correct as-is, just confusingly under-explained).

### R2-M-4. `setup.sh` does not initialize git submodules; the Honcho memory path is left half-wired

- **What step:** After the README's quickstart sequence
  (`git clone` → `cd Aether-Agents` → `bash scripts/setup.sh`), the
  user is expected to be able to run `make setup-honcho` (or any of the
  honcho-* targets). The repo contains a `.gitmodules` referencing
  `honcho-server` at `plastic-labs/honcho`. A plain `git clone` does
  not populate submodules. The `honcho-server` directory in the
  Round 2 clone was empty.
- **What happened:** I had to discover this by reading `.gitmodules`
  and noticing the empty `honcho-server/` dir. `git submodule status`
  printed `-887223e... honcho-server` (leading `-` means
  uninitialized). `make setup-honcho` (which does try to init
  submodules) then failed with the R2-B-1 error.
- **What the README said vs reality:** README §"Memory Provider
  (Honcho)" → "Setup: `make setup-honcho` — This initializes the
  Honcho git submodule, generates honcho-server/.env from template
  (using your OPENCODE_GO_API_KEY), and starts all services." That
  phrasing suggests the user only needs to run `make setup-honcho`;
  the README never tells the user to first run
  `git submodule update --init --recursive` (or to clone with
  `--recurse-submodules`).
- **Fix / workaround:** Either (a) update README to instruct users to
  clone with `--recurse-submodules`, (b) update `setup.sh` to call
  `git submodule update --init --recursive` at the top, or (c) have
  `make setup-honcho` do this with a clear "submodule missing" message
  before the unreachable-commit failure.
- **Severity:** **MAJOR** (combines with R2-B-1 to fully break the
  documented Honcho setup).

### R2-M-5. `setup.sh` creates an `aether-setup` wrapper but neither setup.sh's "Next steps" output nor the README tells the user what it is

- **What step:** Step 8 of `setup.sh`. Round 2 install log:
  `✓ aether-setup → /home/tester/.local/bin/aether-setup`.
- **What happened:** Three wrappers are installed: `aether`, `hermes`,
  `aether-setup`. The `aether` and `hermes` wrappers are identical
  bash files that exec the venv's hermes binary. The
  `aether-setup` wrapper is also a copy of the same file (the
  `create_wrappers` function uses the same `wrapper_content` for all
  three; see `scripts/setup.sh:323-339`). So in practice, the three
  wrappers are functionally equivalent right now — the user has three
  names for the same thing. The setup.sh "Next steps" panel only
  mentions `aether`. `README.md` does not mention `aether-setup` in
  the quickstart. `pyproject.toml` declares a console script
  `aether-setup = "olympus_v3.cli.setup:main"`, suggesting a
  distinct Python entry point — but the wrapper bypasses that entry
  point and just exec's `hermes` directly.
- **What the README said vs reality:** README does not mention
  `aether-setup`. Setup.sh creates it. The user is left to guess
  what it does.
- **Fix / workaround:** Either remove the `aether-setup` wrapper from
  `create_wrappers()` (the `olympus_v3.cli.setup:main` entry point is
  already installed as a real Python console script by
  `pip install -e .`), or have the wrapper actually invoke
  `python -m olympus_v3.cli.setup` so it does what its name suggests.
- **Severity:** **MAJOR** (a phantom wrapper that does the same thing
  as two other wrappers, advertised in the install log, undocumented
  in the README).

### R2-M-6. `setup-honcho.sh` defers its Docker check until step 5/5, after the user has already paid the submodule + env cost

- **What step:** `scripts/setup-honcho.sh` step 5/5.
- **What happened:** The script's first four steps are: init
  submodules, copy `.env.template` → `.env`, read API keys from
  `home/.env`, sed-substitute keys into Honcho's `.env`. The
  `command -v docker` check happens at step 5/5. So if Docker is not
  installed (as in this Round 2 environment), the user does not learn
  that until they have already seen 4 steps of "ok" / "warn" output
  and possibly edited `home/.env`.
- **What the README said vs reality:** README §"🧠 Memory Provider
  (Honcho)" lists Docker only implicitly ("starts all services"). A
  user who tries to follow the documented path on a machine without
  Docker only discovers the requirement after most of the script
  has run.
- **Fix / workaround:** Add a `command -v docker` check at the top
  of `setup-honcho.sh` and exit early with a clear "install Docker
  first" message. Also list it in the README prerequisites.
- **Severity:** **MAJOR** (time wasted + requires extra cleanup if
  user partially populated `home/.env` before learning Docker is
  missing).

## Round 2 — MINOR (cosmetic)

### R2-m-1. `setup.sh` self-reports version "v0.11.1" while the project is at v0.15.0

- **What step:** First lines of `setup.sh` and every section header.
- **What happened:** The on-screen install banner reads
  `Aether Agents v0.11.1 — Setup`. `README.md` and `pyproject.toml`
  both say `v0.15.0`. The CHANGELOG has a `v0.13.0` (2026-06-02)
  release as the latest visible tag, plus 20 releases total.
- **What the README said vs reality:** README badge:
  `version-0.15.0`. Setup banner: `v0.11.1`. Mismatch.
- **Fix / workaround:** Bump `SCRIPT_VERSION` in `scripts/setup.sh`
  and `scripts/setup-honcho.sh` to match the project version. (Or, if
  versioning the script independently is intentional, the README
  should say so.)
- **Severity:** **MINOR** (cosmetic, but undermines confidence in
  the install's freshness).

### R2-m-2. `ictinus/SOUL.md` is the generic hermes-agent fallback persona, not an Ictinus persona

- **What step:** Static content of the repo.
- **What happened:** The ictinus profile's `SOUL.md` begins
  `You are Hermes Agent, an intelligent AI assistant created by Nous
  Research...` — i.e. the stock hermes-agent text. Other daimons
  (hefesto, etc.) have proper personas
  (`# Hefesto — Senior Developer` / `You are Hefesto, Senior
  Developer...`). README §"🎭 The Daimons" describes ictinus as
  "Backend Architect, Level 1 Consultant" but no actual Ictinus
  persona is committed.
- **Severity:** **MINOR** for the install path (no install failure),
  but a content gap relative to the README.

### R2-m-3. The pip install output is hundreds of lines long; no `--quiet` / `2>&1 | tail -N` guidance

- **What step:** Steps 3 and 4 of `setup.sh` (hermes-agent and
  olympus-mcp installs).
- **What happened:** Step 3 dumps the resolution of ~50 packages
  (mostly cached) and step 4 dumps the resolution of another ~80
  packages. Round 2 produced several hundred lines of `Collecting /
  Using cached / Downloading` output. Functional, but visually
  overwhelming and risks the user missing the actual error line in
  case of failure.
- **Fix / workaround:** Pipe through `tail -n 20` or summarize with
  `pip install --quiet` for already-cached wheels; only show the
  tail / a final summary on success. (Cosmetic only.)
- **Severity:** **MINOR.**

### R2-m-4. README "Next steps" in setup.sh points at `home/profiles/*/ .env` but does not enumerate which keys are required, or which daimon needs which

- **What step:** `setup.sh` `print_summary` function.
- **What happened:** The summary says "Edit API keys in profile .env
  files: /tmp/aether-agents/home/profiles/*/ .env". It does not
  tell the user:
  - which daimon actually needs an API key at runtime (the
    orchestrator hermes does; per-daimon daimons only need keys for
    their configured model provider),
  - that `OPENAI_API_KEY` is the canonical starting point and other
    providers are optional,
  - that ictinus has no `.env` and that's expected.
  `INSTALLATION.md` §6.1 has a table of provider env vars, but a
  naive user who stops at the install summary will not see it.
- **Severity:** **MINOR** (information is in the docs, just not
  surfaced at the moment of install).

### R2-m-5. WSL-specific banner prints unconditionally once WSL is detected, even if the user is not using WSL-specific features

- **What step:** `setup.sh` `print_summary` WSL notes block.
- **What happened:** Setup detected WSL2 (correctly — this box
  reports `Linux version 6.6.87.2-microsoft-standard-WSL2`) and
  printed the WSL notes panel
  ("If using Windows terminals, update any .desktop shortcuts...",
  "GPU access requires NVIDIA driver for WSL..."). The "Windows
  terminals / .desktop shortcuts" line is irrelevant in a headless
  container; the GPU line is also irrelevant because setup.sh
  already detected the absence of `nvidia-smi` and skipped
  faster-whisper.
- **Severity:** **MINOR** (banner noise, not broken behavior).

## Round 2 — What worked (positive observations)

For balance, here is the list of things that *did* work as a naive user
would experience them. None of these excuse the friction above; they just
set the bar against which to weigh them.

- `git clone` succeeded on the first try.
- `bash scripts/setup.sh` ran cleanly, exit 0, with clear, colorized
  step output.
- WSL detection worked correctly (this box is genuinely WSL2).
- The venv was created automatically, no `python3-venv` apt install
  needed.
- `pip install hermes-agent` from PyPI worked; hermes-agent 0.15.2
  installed without dependency conflicts.
- `pip install -e .` for olympus-mcp worked; `olympus_v3.server` was
  importable immediately after install.
- Per-profile `config.yaml` files were correctly templated with
  `__AETHER_ROOT__` and `__HERMES_PYTHON__` substituted for the
  actual paths.
- The ictinus-config-only behavior was silently correct (consultant
  doesn't need its own env).
- Wrapper scripts in `~/.local/bin` were correctly updated to the
  new venv path on re-install (only the env var in bashrc lagged —
  see R2-M-1).
- `make doctor` ran cleanly and reported all green checks (Python
  version, venv present, hermes binary present, olympus import,
  GPU "not available" — the latter is informational, not a failure).
- `hermes --version` returned a sensible version string and confirmed
  the install is functional.
- `aether --help` returned a real CLI help screen, listing ~40
  subcommands. The `aether` wrapper does what its name suggests.

## Round 2 — Evidence appendix

Commands run, with results (Round 2):

| # | Command | Result |
|---|---|---|
| 1 | `git clone https://github.com/DarkArty07/Aether-Agents.git /tmp/aether-agents` | exit 0, full repo |
| 2 | `ls -la /tmp/aether-agents/` | full repo, 209 commits on main |
| 3 | `python3 --version` | `Python 3.12.3` |
| 4 | `python3 -m pip --version` | `No module named pip` (host; does not block) |
| 5 | `cat /tmp/aether-agents/README.md \| head` | confirmed Quick Start = `git clone && cd && bash scripts/setup.sh` |
| 6 | `cat /tmp/aether-agents/scripts/setup.sh` | 468 lines, 10 numbered steps |
| 7 | `cat /tmp/aether-agents/pyproject.toml` | name `olympus-mcp` v0.15.0, requires-python >=3.11 |
| 8 | `cat /tmp/aether-agents/docs/guides/INSTALLATION.md` | full manual-install doc |
| 9 | `cp -a ~/.bashrc /tmp/bashrc.before; cp -a ~/.local/bin /tmp/localbin.before` | snapshotted prior state |
| 10 | `cd /tmp/aether-agents && bash scripts/setup.sh` | **exit 0**, full output captured; see R2-M-1, R2-M-2, R2-M-3, R2-M-5, R2-m-1, R2-m-3, R2-m-4, R2-m-5 |
| 11 | `ls /tmp/aether-agents/home/profiles/ictinus/` | only SOUL.md, config.yaml, config.yaml.template, plugins — **no .env.example** (R2-M-3) |
| 12 | `ls -la /home/tester/.local/bin/` | aether, hermes, aether-setup rewritten (R2-M-5) |
| 13 | `tail ~/.bashrc` | still contains old `HERMES_HOME=/tmp/opencode/aether-install/Aether-Agents/home` (R2-M-1) |
| 14 | `cat /proc/version` | `Linux version 6.6.87.2-microsoft-standard-WSL2` — WSL detection correct (R2-m-5) |
| 15 | `cd /tmp/aether-agents && make doctor` | exit 0, all checks pass (Python 3.12.3, venv ✓, hermes binary ✓, olympus import ✓, GPU not available) |
| 16 | `/home/tester/.local/bin/hermes --version` | `Hermes Agent v0.15.2 (2026.5.29.2)` |
| 17 | `/home/tester/.local/bin/aether --help` | real CLI help screen, ~40 subcommands |
| 18 | `git submodule status` | `-887223e... honcho-server` (uninitialized, R2-M-4) |
| 19 | `ls -la /tmp/aether-agents/honcho-server` | empty directory |
| 20 | `cd /tmp/aether-agents && make setup-honcho` | **exit 2**, "fatal: remote error: upload-pack: not our ref 887223e..." (R2-B-1) |
| 21 | `cat /tmp/aether-agents/home/profiles/ictinus/SOUL.md \| head` | generic hermes-agent persona, not Ictinus (R2-m-2) |
| 22 | `cat /tmp/aether-agents/home/profiles/hefesto/SOUL.md \| head` | proper Hefesto persona, contrast with ictinus |
| 23 | `cat /tmp/aether-agents/.gitmodules` | pins `honcho-server` to commit `887223e` |

## Round 2 — "Should I install this?" one-paragraph summary

(replaces the Round 1 summary)

The core install of Aether-Agents — clone, `bash scripts/setup.sh`,
`make doctor`, run `aether` — works on a fresh WSL2 / Python 3.12 box
in roughly 90 seconds, and the resulting `hermes` / `aether` binaries
are real, version-stamped, and import the right things. If you only
want the orchestrator and the six daimons and you're willing to feed
in your own API keys via the per-profile `.env` files it generates,
it's a polished, automated, single-command install and you should try
it. But the README oversells what you get: the heavily-advertised
"Honcho" memory layer (cross-session context recall, .aether
continuity, dialectic reasoning) cannot actually be set up on a fresh
clone right now, because the git submodule is pinned to a specific
honcho commit that the upstream repo no longer serves — `make
setup-honcho` exits with a fatal fetch error. There are also a few
MAJOR but non-fatal paper cuts you'll hit: `setup.sh` will quietly
leave a stale `HERMES_HOME` in your `~/.bashrc` if you ever re-install
in a new path (it overwrites the wrapper scripts but not the env var,
so the two silently disagree), the script never creates the
`home/.env` orchestrator file that `INSTALLATION.md` §6.1 says is
required at minimum, it silently skips the ictinus profile's `.env`
without explaining that ictinus is a Level 1 Consultant by design, and
the `aether-setup` wrapper it installs is just a third copy of the
`aether` wrapper. Bottom line: install yes, but be ready to (a) hand-
edit `home/.env`, (b) ignore the Honcho section of the README for
now or repoint the submodule yourself, and (c) double-check
`~/.bashrc` after re-installs.
