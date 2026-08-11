# Quickstart

## 1. Install or refresh Hermes assets

```bash
bash scripts/setup.sh
make doctor
```

This creates missing live configuration from templates and preserves existing config and `.env` files.

## 2. Configure credentials

Edit only ignored live files such as `home/.env`, `home/config.yaml` and allowed profile `.env` files. Never place real keys in a template or document.

## 3. Inspect Aether MCP

For an existing installation:

```bash
make runtime-status
make runtime-doctor
```

A healthy status reports version `0.23.0.dev0`, enabled registration and 15 tools. Run the installed-runtime doctor while the runtime is quiescent; live owned MCP processes are intentionally reported as stale resources.

## 4. Start Hermes

```bash
aether
```

Hermes may work directly. Visibility of the multi-agent tools does not authorize model dispatch, spending or external effects.
