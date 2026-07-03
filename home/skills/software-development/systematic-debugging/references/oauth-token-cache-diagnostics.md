# OAuth Token Cache Diagnostics — Pydantic Model vs Raw JSON

When debugging why an OAuth prompt fires on every agent invocation despite valid cached tokens, the first diagnostic is to determine whether the token caching layer is working correctly. This reference documents the diagnostic script pattern that separates **storage/caching bugs** from **caller logic bugs**.

## When to Use

- The user reports "OAuth prompt fires every time" despite tokens being cached on disk
- `has_cached_tokens()` returns `True` but the OAuth flow still runs
- You need to prove whether `get_tokens()` deserializes correctly
- You suspect Pydantic's `extra='ignore'` default is silently dropping fields

## The Three-Layer Diagnostic Pattern

The fundamental check: compare what's on disk (raw JSON) vs what comes out of the Pydantic model (via `model_validate()`). Any discrepancy between the two means the model layer is transforming or dropping data.

### Layer 1 — File Existence + Raw Content

```python
import json
from pathlib import Path

tokens_path = Path(HERMES_HOME) / "mcp-tokens" / f"{server_name}.json"
print(f"File exists: {tokens_path.exists()}")

if tokens_path.exists():
    raw = json.loads(tokens_path.read_text(encoding="utf-8"))
    print(f"Keys in file: {list(raw.keys())}")
    for k, v in raw.items():
        if k in ("access_token", "refresh_token", "client_secret"):
            print(f"  {k}: NON_EMPTY={bool(v)}")
        else:
            print(f"  {k}: {v!r}")
```

### Layer 2 — Pydantic-Model-Parsed Content

```python
async def check_model():
    storage = HermesTokenStorage(server_name)
    tokens = await storage.get_tokens()
    if tokens is not None:
        dump = tokens.model_dump(exclude_none=True)
        print(f"Model keys: {list(dump.keys())}")
        print(f"Model dump: {dump}")
    else:
        print("Model returned None")
```

### Layer 3 — Comparison (the critical step)

```python
# Compare model fields vs raw file keys
token_model_fields = {"access_token", "token_type", "expires_in", "scope", "refresh_token"}
extra_in_file = set(raw.keys()) - token_model_fields
if extra_in_file:
    print(f"⚠ EXTRA fields in file (silently dropped by model_validate): {extra_in_file}")
```

## Common Findings

### 1. `expires_at` is silently dropped

The OAuthToken Pydantic model from the MCP SDK has these fields:

```python
class OAuthToken(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int | None = None
    scope: str | None = None
    refresh_token: str | None = None
```

Many OAuth servers return an `expires_at` field (absolute UNIX timestamp) in the token response. This field is **present in the raw JSON file** (because model_dump(exclude_none=True) preserves unknown fields when manually constructing, or was written by a previous version of the code), but **silently dropped** when loaded via `OAuthToken.model_validate()` because Pydantic v2 defaults to `model_config = {'extra': 'ignore'}`.

**Impact:** Any code path that reads the raw JSON file directly and checks `expires_at` will find it — but the same field will be absent after the data passes through `model_validate()`. This can cause different code paths to disagree about token validity.

**Diagnosis script output example:**

```
Keys in file: ['access_token', 'token_type', 'expires_in', 'scope', 'refresh_token', 'expires_at']
EXTRA fields (not in OAuthToken model): {'expires_at'}
```

### 2. `expires_in` differs between file and model

**Observation:** The file may store the original TTL (e.g., 259200 = 3 days) while `model_validate()` reads a slightly smaller value.

**Root cause:** This is typically benign — the `expires_in` in the file is the server's original TTL, while the model value reflects a recomputation. Verify with the `expires_at` validity check below. If `now + model.expires_in` equals `file.expires_at` (within ~1s), the token expiry is internally consistent and the discrepancy is harmless.

**Diagnosis script code:**

```python
import time

now = time.time()
file_expires_at = raw.get("expires_at")
model_expires_in = tokens.expires_in if tokens else None

if file_expires_at and model_expires_in:
    computed = now + model_expires_in
    diff = abs(computed - file_expires_at)
    if diff < 5:
        print("✓ File expires_at MATCHES computed value (within 5s)")
    else:
        print(f"⚠ File expires_at DIFFERS: {diff:.1f}s — possible recomputation")
```

### 3. Token is valid but caller doesn't check

If all of the following are true, the storage layer is NOT the problem:

- `has_cached_tokens()` returns `True`
- `get_tokens()` returns a valid `OAuthToken` with non-empty `access_token`
- Token expiry shows `> 0` seconds remaining
- Raw JSON file contains all expected fields

**Then the root cause is upstream:** the calling code does not gate the OAuth flow on cached tokens. The `OAuthClientProvider.async_auth_flow()` in the MCP SDK loads from storage at initialization, but the code that invokes the provider (e.g., `mcp_tool.py` or `build_oauth_auth()`) must check `storage.has_cached_tokens()` before deciding to initiate a fresh OAuth flow.

## Complete Diagnostic Template

Save this as a diagnostic script when needed. Place it on a shared path accessible from the target environment.

<details>
<summary>Click to expand the full template</summary>

```python
#!/usr/bin/env python3
"""Diagnose OAuth token cache for a Hermes Agent MCP server."""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

os.environ["HERMES_HOME"] = "/path/to/.prometeo"  # SET THIS

from tools.mcp_oauth import HermesTokenStorage
from mcp.shared.auth import OAuthToken

SERVER_NAME = "magnific"  # SET THIS

async def main():
    storage = HermesTokenStorage(SERVER_NAME)
    tokens_path = storage._tokens_path()

    print("=" * 60)
    print(f"  OAuth Token Diagnostics: {SERVER_NAME}")
    print("=" * 60)

    # 1. File existence
    print(f"\n[1] File exists: {tokens_path.exists()}")

    # 2. Raw JSON
    print("\n[2] Raw JSON file:")
    if tokens_path.exists():
        raw = json.loads(tokens_path.read_text(encoding="utf-8"))
        print(f"    Keys: {list(raw.keys())}")
        token_fields = {"access_token", "token_type", "expires_in", "scope", "refresh_token"}
        extra = set(raw.keys()) - token_fields
        if extra:
            print(f"    ⚠ EXTRA fields (silently dropped by Pydantic): {extra}")
        print(f"    access_token non-empty: {bool(raw.get('access_token'))}")
        print(f"    refresh_token non-empty: {bool(raw.get('refresh_token'))}")
        print(f"    expires_in: {raw.get('expires_in')}")
        if raw.get("expires_at"):
            remaining = raw["expires_at"] - time.time()
            print(f"    expires_at: {raw['expires_at']} ({'VALID' if remaining > 0 else 'EXPIRED'}, {remaining:.0f}s left)")

    # 3. Model validation
    print("\n[3] HermesTokenStorage:")
    print(f"    has_cached_tokens(): {storage.has_cached_tokens()}")
    tokens = await storage.get_tokens()
    if tokens is not None:
        dump = tokens.model_dump(exclude_none=True)
        print(f"    get_tokens() → OAuthToken loaded: YES")
        print(f"    Model keys: {list(dump.keys())}")
        if tokens.expires_in:
            computed_at = time.time() + tokens.expires_in
            print(f"    expires_in: {tokens.expires_in}")
            print(f"    computed expires_at: {computed_at:.1f}")
            if raw.get("expires_at"):
                diff = abs(computed_at - raw["expires_at"])
                print(f"    vs file expires_at: {'MATCH' if diff < 5 else 'MISMATCH'} ({diff:.1f}s diff)")
    else:
        print(f"    get_tokens() → None")

    # 4. Client info
    ci = await storage.get_client_info()
    print(f"\n[4] get_client_info(): {'loaded' if ci else 'None'}")

    # 5. Conclusion
    print("\n" + "=" * 60)
    print("  CONCLUSION")
    print("=" * 60)
    if tokens and tokens.access_token:
        print("  ✓ Token IS cached and loads correctly.")
        print("  → Root cause is NOT in storage. Check calling code logic.")
    else:
        print("  ⚠ Token storage has an issue — see above.")

if __name__ == "__main__":
    asyncio.run(main())
```

</details>

## Cross-Distro Execution (WSL)

When the agent runs in one WSL distro (e.g., Ubuntu) but the target Hermes instance is in another (e.g., Fedora), write the diagnostic script to a shared Windows path and execute via `wsl.exe`:

```bash
# Write script to shared path (accessible from both distros)
# Host (Ubuntu): write to /mnt/c/Users/<user>/AppData/Local/Temp/diagnose.py
# Target (Fedora): reference the same /mnt/c/... path
wsl.exe -d FedoraLinux-43 -u user -- bash -c \
  '/path/to/venv/bin/python3 /mnt/c/Users/user/AppData/Local/Temp/diagnose.py'
```

Note: The `wsl: Failed to translate` warning is non-fatal (see `wsl-distros` reference, Pitfall #11).

## Related Reference

- `systematic-debugging` SKILL.md — The 4-phase investigation framework this technique feeds into
- `cross-process-hook-debugging.md` — Debugging data flow across ACP process boundaries (Hermes ←→ Daimon) with similar layer-by-layer comparison approach
