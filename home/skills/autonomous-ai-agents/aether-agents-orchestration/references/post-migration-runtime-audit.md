# Post-Migration Runtime Audit for Aether Agents

Use this after moving Aether to a new OS, home directory, Python environment, or Hermes installation. The goal is to distinguish **registered**, **enabled**, **credentialed**, and **functionally working** components without exposing secrets or blindly rewriting live configuration.

## Audit order

1. **Check the current log first**
   - Inspect `home/logs/agent.log` before diagnosing framework behavior.
   - Prefer entries from the current session/startup. Historical WSL or old-provider warnings are not evidence about the current runtime.
   - Confirm the actual model/provider, plugin registration, MCP tool counts, and `check_fn` failures.

2. **Establish the active instance**
   - Confirm `HERMES_HOME`, active Hermes binary/version, project root, current config path, and Python executable.
   - Aether, Prometeo, and other projects are separate instances. Do not infer one instance's credentials or MCPs from another.

3. **Run read-only framework diagnostics**
   - Run `HERMES_HOME=/absolute/aether/home hermes doctor`.
   - Run `hermes tools list` to distinguish an installed tool from an enabled tool.
   - Treat `doctor` as one signal, not final proof: smoke-test important capabilities directly.

4. **Inventory credentials safely**
   - Parse `.env` and print only variable names, presence, length, and placeholder status—never values.
   - Compare `${VAR}` references in live configs with present variable names.
   - OAuth providers may use `auth.json`; report only provider/top-level key names and file permissions.
   - If a needed key exists in another instance, do not copy it without explicit authorization.

5. **Separate web search from browser automation**
   - Web search/extraction and browser navigation are independent.
   - Verify all four layers:
     1. provider plugin registered;
     2. toolset enabled for the active platform;
     3. required credential present;
     4. real search/extract or navigation smoke test passes.
   - For Exa, empty `web.search_backend` or `web.extract_backend` can override `web.backend`; remove them or set them explicitly.
   - A browser binary working from its absolute package path proves the engine, not that Hermes exposes the `browser` toolset.

6. **Probe configured APIs without leaking secrets**
   - Use authenticated read-only endpoints such as `/v1/models`.
   - Report provider, HTTP status, response content type/shape, and model count only.
   - Use a client that handles compression (e.g. `httpx`); a raw client may misclassify gzipped JSON as non-JSON.
   - A successful models endpoint proves key connectivity, not model-generation quality.

7. **Verify MCPs end-to-end**
   - Olympus: `discover`, `aether_status`, and one real Daimon smoke session.
   - Graphify: structural query plus verification that any semantic-provider env reference resolves.
   - Context7: resolve a known library; an empty resources list alone is not failure.
   - Registration proves process startup only. Provider-backed MCP operations need their own authenticated smoke test.

8. **Verify Daimon reproducibility**
   - For all six profiles, check live config, template, SOUL, `.env` symlink, OAuth `auth.json`, provider/model, toolsets, and config version.
   - Compare live config to template semantically. Machine paths should differ by placeholder substitution; provider, fallback, role, and toolset drift may be dangerous.
   - Prefer the latest explicit user decision and recorded runtime smoke evidence when deciding which side is the source of truth.

9. **Check memory and background services**
   - If `memory.provider: honcho`, verify configuration, health endpoint, listener, and an actual memory operation. Local `MEMORY.md` working does not prove Honcho works.
   - Check gateway service presence separately from TUI operation; a healthy TUI does not prove Telegram/gateway service health.

10. **Inspect process hygiene without mass-killing**
    - Count Olympus/MCP processes, parents, age, and RSS.
    - Processes adopted by user systemd are orphan candidates, not automatic proof of safety to kill.
    - Preserve processes attached to active TUI/ACP sessions. Terminate only instances whose ownership and inactivity are demonstrated.

11. **Test config migration in a sandbox first**
    - Copy only non-secret config/persona files into a temporary `HERMES_HOME`.
    - Run `hermes doctor --fix` there, then inspect the exact diff and resulting config version.
    - Confirm model, web, MCP, platform toolsets, and custom providers survive before applying to live state.

12. **Inspect Git hygiene**
    - Record branch, dirty tracked files, submodule state, backups, caches, and runtime artifacts.
    - Do not clean blindly: separate valuable skill/template work from disposable runtime state.

## Status classification

- **Healthy:** core model, required tools, APIs, MCPs, Daimons, and configured services pass real smoke tests.
- **Degraded:** core work continues, but an intended capability (web, browser, memory, gateway, semantic Graphify) is unavailable or configuration is not reproducible.
- **Broken:** primary model/auth, file/terminal execution, or ACP orchestration cannot complete a real task.

## Repair gate

Present a synthesized report before remediation. Separate:

- **Safe changes:** empty backend keys, stale runtime state, ignored caches, template synchronization, config-version migration after diff review.
- **Sensitive changes:** copying credentials, changing providers/models/auth, enabling external gateways, or moving secrets between instances.
- **Operationally disruptive changes:** restarting TUI/gateway, killing MCP processes, rebuilding Graphify, or restoring Honcho.

Require explicit approval for sensitive changes. After repair, open a fresh session when config is startup-cached and repeat the functional smoke tests; file edits alone are not acceptance.

## Closure gate after remediation

Do not convert a long repair report into “complete” until all layers below have direct evidence:

1. **Framework:** current config version, `hermes doctor`, config validation, and full project tests.
2. **Services:** bounded health polling, container status/restart counts, effective port publication, and one isolated non-destructive SDK/API transaction for stateful services.
3. **Tools:** one real operation for web search, browser, each MCP, and semantic/provider-backed paths—not registration alone.
4. **Daimons:** one ACP smoke per profile that performs a real file/tool call and reports the configured role/model. Pass the exact project-local config path in the prompt; a Daimon may otherwise assume a global `~/.hermes/profiles/...` path and produce a false failure.
5. **Independent QA:** ask Athena to audit the actual diff and runtime evidence. If Athena returns FAIL, fix the specific blocker, independently verify it, then run a focused second audit. A first-pass failure followed by an unreviewed fix is not closure.
6. **Repository hygiene:** `git diff --check`, ignored runtime config/state, secret-safe inspection, and explicit separation of remediation changes from pre-existing dirty worktree content.
7. **Continuity:** resolve now-fixed `.aether` issues with concrete evidence, record significant operational decisions, set the hot task accurately, and curate `CONTEXT.md` only after QA passes.

### ACP follow-up pitfall

A completed consultation session may already be gone when a follow-up message is sent, even if the initial result exposed a session ID. If `message` returns `Unknown session`, do not loop or pretend the prior turn contains the new review. Open a fresh session with the prior evidence and a narrowly scoped prompt, then close it after receiving the verdict.

### Self-hosted memory provider evidence

For Honcho-like providers, distinguish cloud credential status from local availability. A self-hosted `baseUrl` may be sufficient when server authentication is disabled; verify against the installed provider parser/docs rather than inventing an API key. Acceptance requires: optional SDK installed, provider status available, local config mode `0600` and gitignored, health HTTP 200, stable backing services, and an isolated create/read/delete transaction outside the production workspace.