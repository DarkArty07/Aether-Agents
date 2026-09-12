# MON-D14 Implementation Evidence — provisioned preflight profile normalization and reference destination resolution

**Unit:** D14 preflight correction
**Task:** `t_5a7b776a`
**Objective Contract:** `oc_f8c9fc9320587cf3@v3` (SHA-256 `f21facaf58af20a2d0595cdaa927a99ca6336e5b14b5d073ec3501bbfbf7f47c`)
**Supervisor breakdown:** `specs/telegram-monitor/tasks.md` §"v3 continuation" at commit `6bd2ac9`
**Integration base:** `3db391a747579605304ceea91f2bdeac50c7dd67` (clean merge of preserved candidate `19dfc9d68e797f7d365f078ef65be70fbd16f158`)
**Base commit:** `6bd2ac97d4400500dc20f96184a6ec33bfddad3b`
**Phase:** implementer unit; **no live effect performed** — no `--live` run, no model call, no Telegram call, no activation, no push, no PR, no issue mutation, no external service write.

## Scope and changed paths

- `scripts/qualify_telegram_monitor.py` — implementation of `_normalize_profile_home`, updated `_provisioned_profile_home`, `_provisioned_env_files`, `_provisioned_reference_environment`, `_lab_destination`, `_lab_preflight`, `_check_lab_context`, and `_runtime_execute(..., cwd=...)`; probe body updated to invoke `hermes_cli.env_loader.load_hermes_dotenv()` before `gateway.config.load_gateway_config()`.
- `tests/test_telegram_monitor_cli_plugin.py` — added 11 focused D14 test functions covering both `HERMES_HOME` shapes, rejection of invalid/ambiguous/linked/relative candidates, native call order, target digest equality, negative control on injected lab access, worker selector non-substitution, and preserved prior receipt verification.
- `docs/guides/telegram-monitor.md` — updated the read-only phase description with D14 normalization and reference destination resolution details.
- `CHANGELOG.md` — added entry under `[Unreleased]` for the D14 qualification preflight correction.
- `specs/telegram-monitor/evidence/MON-D14.md` — this portable evidence file.

Preserved unchanged: production `src/`, all other tests, all design specifications in `specs/telegram-monitor/{spec,plan,quickstart,qualification-isolation,research,tasks}.md`, Objective Contracts `v1.md`, `v2.md`, `v3.md`, root `AGENTS.md`, and `.github/workflows/policy.yml` (manifest list exact at 376 files).

## Reproduction of broken preflight on unmodified base

Two interface gaps caused the preserved `lab-config` preflight refusal on the base commit:

1. **Profile resolution mismatch:**
   `_provisioned_profile_home()` computed `Path(monitor_runtime.hermes_home()) / "profiles" / "morfeo"`.
   Under this installation's profile-scoped runtime, `HERMES_HOME` points directly to the Morfeo profile (`<installation-root>/profiles/morfeo`), which caused the path to resolve to `<installation-root>/profiles/morfeo/profiles/morfeo`. That path does not exist, causing `config-unreadable: FileNotFoundError` in `_lab_config` and raising bounded refusal `lab-config` before the attempt boundary.

   *Command executed:*
   ```bash
   env HERMES_HOME="<installation-home>/profiles/morfeo" \
     python3 -c 'from aether_agents.monitor import runtime; from pathlib import Path; print(Path(runtime.hermes_home()) / "profiles" / "morfeo")'
   ```
   *Observed output:*
   `<installation-home>/profiles/morfeo/profiles/morfeo` (does not exist; `exists() == False`).

2. **Provisioned reference destination missing:**
   With the correct profile path supplied, `_lab_destination(interpreter, environment=None)` executed a bare child that excluded `TELEGRAM_*` variables and never invoked Hermes' native dotenv loader. Because this installation pins its Telegram destination in `profiles/morfeo/.env` (and carries no `home_channel` in `config.yaml`), `load_gateway_config()` returned `None`, yielding `destination-missing`.

   *Command executed on base behavior:*
   ```bash
   env -i PATH="$PATH" HOME="$HOME" HERMES_HOME="<installation-home>/profiles/morfeo" \
     <runtime-interpreter> -c '
   from gateway.config import Platform, load_gateway_config
   config = load_gateway_config()
   home = config.get_home_channel(Platform.TELEGRAM)
   print("Home exists without dotenv:", home is not None)
   '
   ```
   *Observed output:*
   `Home exists without dotenv: False` (`destination-missing`).

3. **Cross-check with native dotenv loader:**
   Invoking `hermes_cli.env_loader.load_hermes_dotenv()` before `gateway.config.load_gateway_config()` loaded the profile's `.env` and resolved the home channel with zero model/transport effects:

   *Command executed:*
   ```bash
   env -i PATH="$PATH" HOME="$HOME" HERMES_HOME="<installation-home>/profiles/morfeo" \
     <runtime-interpreter> -c '
   from hermes_cli.env_loader import load_hermes_dotenv
   from gateway.config import Platform, load_gateway_config
   import hashlib

   load_hermes_dotenv()
   config = load_gateway_config()
   home = config.get_home_channel(Platform.TELEGRAM)
   chat_id = str(getattr(home, "chat_id", "") or "").strip()
   thread_raw = getattr(home, "thread_id", None)
   thread_id = str(thread_raw).strip() if thread_raw is not None else ""
   target = chat_id + "\0" + thread_id
   digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
   print("Home exists:", home is not None)
   print("Digest prefix:", digest[:16])
   print("Thread present:", bool(thread_raw))
   '
   ```
   *Observed output:*
   `Home exists: True`
   `Digest prefix: 36007c9a8b0f8394`
   `Thread present: False`

## D14 Implementation Summary

1. **`_normalize_profile_home`:**
   - Normalizes either the multi-profile installation root (`<installation-root>`) or the exact profile home (`<installation-root>/profiles/morfeo`) to the exact canonical Morfeo profile directory.
   - Computes categorical path class: `"multi-profile-root"` when derived from root, or `"exact-profile"` when given the profile directly.
   - Computes path digest: SHA-256 hex digest of the canonical resolved profile path (`de71053213ebdde16a6a1e36c89f3407c2f0a08cdfbe080ff84035fcd0fdab2a`).
   - Refuses missing candidates, non-directories, and symbolic links at candidate root, child profile, and `config.yaml`.
   - Refuses ambiguous candidates (named "morfeo" but also containing a `profiles/morfeo` child directory).
   - Refuses differently named profiles (e.g. `implementer`).
   - Refuses profiles missing configuration (`config.yaml`).
   - Refuses relative paths and never falls back to cwd or worker profile identity.
   - Records only the path class and digest in public evidence and preflight records; never leaks machine paths.

2. **Provisioned Reference Destination Resolution:**
   - Evaluated in a restricted child process rooted at the normalized Morfeo profile home (`HERMES_HOME=str(profile_home)`, `cwd=profile_home`).
   - `_provisioned_reference_environment` excludes all `TELEGRAM_*` and `AETHER_ROUTER_*` variables, ensuring no lab access is leaked or injected into the reference side.
   - The probe body invokes `hermes_cli.env_loader.load_hermes_dotenv()` before `gateway.config.load_gateway_config()`, making profile-local configuration visible through Hermes' supported loader.
   - Diagnostic note: `_provisioned_env_files` drops symlinked `.env` files (which then fail closed later as `lab-access-missing` if required access is absent); only regular files are consumed.
   - Emits only bounded non-secret projections: `destination_digest` (`36007c9a8b0f839416989e6aa06b2d8225c11142837fc5539cf8a33b59935f5f`) and `destination_thread_present` (`false`).
   - Negative control: supplying lab access variables (`TELEGRAM_*` or `AETHER_ROUTER_*`) to `_lab_destination` when `lab_root is None` raises `QualificationError("lab-reference-access-rejected", ...)`.

3. **Digest Parity and Lab Independence:**
   - Ephemeral borrowed access (`_lab_access`) is passed only to lab children via `_lab_child_environment`.
   - The in-laboratory gate (`_lab_context_preflight`) resolves `destination_digest` in the created lab root from the borrowed access and asserts exact equality with `preflight["destination_digest"]`.
   - Both digests match (`36007c9a8b0f8394...`), confirming zero destination drift.

## Acceptance Criteria Mapping

| Requirement / AC | Check | Observed Result | Evidence Location |
| --- | --- | --- | --- |
| D14 HERMES_HOME normalization (both shapes) | `test_d14_hermes_home_both_shapes_normalize_to_same_profile` | PASS: Both multi-profile root and exact profile resolve to the same canonical directory and digest (`de710532...`); classes recorded as `multi-profile-root` and `exact-profile` | `tests/test_telegram_monitor_cli_plugin.py:5873` |
| D14 Missing candidate refusal | `test_d14_normalize_profile_refuses_missing_and_wrong_candidates` | PASS: Nonexistent candidate raises `QualificationError("lab-profile")` before any effect | `tests/test_telegram_monitor_cli_plugin.py:5895` |
| D14 Wrong-named candidate refusal | `test_d14_normalize_profile_refuses_missing_and_wrong_candidates` | PASS: Candidate named "implementer" without `profiles/morfeo` raises `QualificationError("lab-profile")` | `tests/test_telegram_monitor_cli_plugin.py:5903` |
| D14 Ambiguous candidate refusal | `test_d14_normalize_profile_refuses_ambiguous_and_symlinked_candidates` | PASS: Directory named "morfeo" containing a `profiles/morfeo` child raises `QualificationError("lab-profile")` | `tests/test_telegram_monitor_cli_plugin.py:5913` |
| D14 Symlinked candidate refusal | `test_d14_normalize_profile_refuses_ambiguous_and_symlinked_candidates` | PASS: Symlinked profile directory raises `QualificationError("lab-profile")` | `tests/test_telegram_monitor_cli_plugin.py:5927` |
| D14 Missing / symlinked config refusal | `test_d14_normalize_profile_refuses_missing_and_symlinked_config` | PASS: Profile with missing `config.yaml` or symlinked `config.yaml` raises `QualificationError("lab-profile")` | `tests/test_telegram_monitor_cli_plugin.py:5941` |
| D14 Current-worker selector rejection | `test_d14_normalize_profile_refuses_relative_path_and_worker_identity_substitution` | PASS: Relative path and `HERMES_HOME=implementer` with `HERMES_PROFILE=morfeo` refused | `tests/test_telegram_monitor_cli_plugin.py:5963` |
| D14 Provisioned reference environment access stripping | `test_d14_provisioned_reference_environment_strips_access` | PASS: `_provisioned_reference_environment` roots at profile home and strips all `TELEGRAM_*` and `AETHER_ROUTER_*` variables | `tests/test_telegram_monitor_cli_plugin.py:5988` |
| D14 Negative control on injected lab access | `test_d14_negative_control_reference_probe_rejects_injected_lab_access` | PASS: Supplying `TELEGRAM_HOME_CHANNEL` or `TELEGRAM_BOT_TOKEN` to reference probe raises `QualificationError("lab-reference-access-rejected")` | `tests/test_telegram_monitor_cli_plugin.py:6013` |
| D14 Native loader call order | `test_d14_native_probe_body_executes_load_hermes_dotenv_before_load_gateway_config` | PASS: `load_hermes_dotenv()` syntactically and functionally precedes `load_gateway_config()` | `tests/test_telegram_monitor_cli_plugin.py:6042` |
| D14 Target digest equality | `test_d14_target_digest_equality_and_no_access_values` & `test_real_laboratory_chain_reaches_the_fixture_and_the_transition` | PASS: Reference probe and laboratory probe compute identical destination_digest (`4e7c5b38...`), no access values leaked in fingerprints; full chain asserts `facts["destination_matches"] is True` | `tests/test_telegram_monitor_cli_plugin.py:6055,5683` |
| D14 Real runtime reference probe | `test_d14_runtime_reference_destination_probe_matches_gateway_context` | PASS: Reference probe executed against installation runtime resolves `36007c9a8b0f8394...` with `destination_thread_present=False` (skips cleanly if product runtime/profile absent) | `tests/test_telegram_monitor_cli_plugin.py:6100` |
| D14 Preserved prior refusal receipt untouched | `test_d14_preserved_prior_refusal_receipt_and_log_unchanged` | PASS: Preserved receipt SHA-256 `eb2f3ad3...` and log SHA-256 `5a9ca1fe...` unchanged (skips cleanly if evidence directory absent) | `tests/test_telegram_monitor_cli_plugin.py:6154` |
| Deterministic offline lane | `uv run --frozen python scripts/qualify_telegram_monitor.py --json` | PASS: 11/11 checks pass with 0 model calls, 0 Telegram sends, `ok=true` | `scripts/qualify_telegram_monitor.py:884` |

## Verification Results

1. **Deterministic lane:**
   ```bash
   uv run --frozen python scripts/qualify_telegram_monitor.py --json
   ```
   Result: `ok: true`, 11/11 checks passed, `external_effects: {"model_calls": 0, "telegram_sends": 0}`.

2. **Focused monitor test suite:**
   ```bash
   uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_*.py
   ```
   Result: **304 passed in 21.37s** (exit code 0).

3. **Documentation validation:**
   ```bash
   uv run --frozen python scripts/check_documentation.py
   ```
   Result: `documentation validation passed` (exit code 0).

4. **Static quality gates:**
   ```bash
   uv run --frozen ruff check scripts/qualify_telegram_monitor.py tests/test_telegram_monitor_cli_plugin.py
   uv run --frozen ruff format --check scripts/qualify_telegram_monitor.py tests/test_telegram_monitor_cli_plugin.py
   uv run --frozen mypy src/aether_agents
   python3 -m compileall -q scripts src tests
   uv build
   git diff --check
   ```
   Result: all static gates passed cleanly with 0 errors or warnings.

5. **Policy manifest check:**
   Policy file list in `.github/workflows/policy.yml` matches `git ls-files` (excluding `specs/`) exactly: 376/376 files, 0 missing, 0 extra.

6. **Public artifact path scan:**
   ```bash
   uv build
   uv run --frozen python scripts/check_public_artifacts.py --root . --artifact dist/*.whl --artifact dist/*.tar.gz
   ```
   Result: 0 violations added in tracked surface or built artifacts; baseline parity preserved (only pre-existing `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` flagged).

7. **Public artifacts test suite:**
   ```bash
   uv run --frozen pytest -q tests/test_public_artifacts.py
   ```
   Result: baseline parity preserved (5 passed, 1 pre-existing failure on oc_0084270d940c98d9/v1.md).

## Residual Risk

- **Live runtime execution:** This unit performs no `--live` run and makes no external effect. The single authorized live qualification attempt (`--live --wait-hourly-boundaries 2`) is owned by terminal integration child `t_b8077e66` (Supervisor), which will execute against the reviewed candidate with the private runtime shim re-pinned.
- **Operator environment dependency:** Destination resolution requires the provisioned Morfeo profile to carry a valid `.env` file with `TELEGRAM_HOME_CHANNEL`. The D14 preflight fails closed with bounded error `destination-missing` if that provisioned file is absent or incomplete.
