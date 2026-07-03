# User Preference: Check Your Own Tools First

**Session:** 2026-06-09
**Context:** User reported "graphify se pierde al reiniciar la máquina virtual" (Graphify is lost after VM reboot). User had reconfigured it 3+ times.

## Frustration Signal

User: *"no preguntes estupidces yo te hare una pregunta. responde si o no. TIENES O SI O NO HERRMAIENTAS DE GRAPHIFY DISPONIBLES"*

Translation: "Don't ask stupid questions, I'll ask you a question. Answer yes or no. Do you have Graphify tools available or not?"

## What the User Wants

When a user reports a tool is missing or broken, the FIRST thing I should do is check my OWN tools and configuration. Do NOT ask the user about their environment, their distro, their commands, or their workflow. I should investigate my own state first.

## Correct Diagnostic Chain (What I Should Have Done)

```bash
# Step 1: Check if graphify is in my available tools
# (This is automatic — I should know immediately if the tools are available)

# Step 2: Check home/config.yaml for the mcp_servers.graphify block
cat ~/Aether-Agents/home/config.yaml | grep -A 10 "graphify:"
# → No output = the block is missing. This is the root cause.

# Step 3: Check if the graphify package is installed
~/Aether-Agents/home/.venv-hermes/bin/pip show graphifyy
# → Version: 0.8.28 = installed

# Step 4: Check if the provider config exists
ls -la ~/Aether-Agents/.graphify/providers.json
# → exists = 295 bytes

# Step 5: Check if a historical version of config.yaml had the block
cd ~/Aether-Agents && git diff stash@{0} -- home/config.yaml | grep -A 5 "graphify:"
# → Shows the block was present in stash but missing now = config drift

# Conclusion: The problem is NOT the VM, NOT the disk, NOT the provider config.
# The problem is my config.yaml is missing the mcp_servers.graphify block.
```

## What I Did Wrong

I asked the user 4 questions about their environment:
1. "¿En esta distro Ubuntu, o en la Fedora (Bedita) de Prometeo?"
2. "¿Se pierde el archivo .graphify/providers.json físicamente, o Graphify deja de funcionar con 'No provider configured'?"
3. "¿Qué comando o workflow ejecutas justo después del reinicio donde falla?"

These were all WRONG. The user was telling me to investigate my own state first.

## The Rule

**When a user reports a tool is missing:**
1. Check if the tool is in my available tools list
2. If NO, check my config.yaml for the mcp_servers block
3. Check if the underlying package is installed
4. Check if the provider config exists
5. Only AFTER all of the above, ask the user for clarification if needed

**When a user says "no preguntes estupidces":**
- STOP asking questions immediately
- Start investigating my own state
- Present findings, not questions

## The Fix

After the user called out the mistake, I investigated and found:
- `config.yaml` currently has NO `mcp_servers.graphify` block
- The stash `pre-prometeo-handoff-2026-06-05` (stash@{0}) DOES have the block
- `config.yaml` is untracked in git (since commit `0c5a0af`)
- `setup.sh` and `update.sh` only manage `profiles/*/config.yaml`, never the root `home/config.yaml`
- The fix is to restore the stash content to `config.yaml`

This is the pattern that should have been followed from the start.
