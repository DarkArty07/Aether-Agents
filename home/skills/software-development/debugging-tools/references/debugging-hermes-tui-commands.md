# Debugging Hermes TUI Slash Commands — Full Reference

## Architecture

```
Python backend (hermes_cli/commands.py)     <- canonical COMMAND_REGISTRY
       │
       ▼
TUI gateway (tui_gateway/server.py)         <- slash.exec / command.dispatch
       │
       ▼
TUI frontend (ui-tui/src/app/slash/)        <- local handlers + fallthrough
```

## Investigation Steps
1. Check TUI frontend: `rg "/commandname" --type ts[x] --path ui-tui/`
2. Examine TUI command definition: `ls ui-tui/src/app/slash/commands/`
3. Check Python backend: `rg "CommandDef" --type py --path hermes_cli/`
4. Examine gateway: `rg "complete.slash|slash.exec" --path tui_gateway/`

## Fix: Missing Command Autocomplete

Add `CommandDef` to `COMMAND_REGISTRY` in `hermes_cli/commands.py`:
```python
CommandDef("commandname", "Description of the command", "Session",
           cli_only=True, aliases=("alias",),
           args_hint="[arg1|arg2|arg3]",
           subcommands=("arg1", "arg2", "arg3")),
```

Add handler in `cli.py::process_command`:
```python
elif canonical == "commandname":
    self._handle_commandname(cmd_original)
```

## Common Issues
1. Command in TUI but not autocomplete → missing from COMMAND_REGISTRY
2. Command in autocomplete but doesn't work → handler missing
3. Behavior differs CLI vs TUI → different implementations
4. Command persists config but doesn't apply live → patch nanostore state
5. Gateway dispatch silently ignores → not in GATEWAY_KNOWN_COMMANDS

## Debugging Tactics
- Python side: use python-debugpy skill
- Ink side: use node-inspect-debugger skill
- Registry mismatch: compare COMMAND_REGISTRY vs TUI local list

## Pitfalls
- Don't forget CommandDef category
- cli_only=True won't work in gateway without gateway_config_gate
- Thread live UI state through all render paths
- Always rebuild TUI: `npm --prefix ui-tui run build`

## Verification
1. Rebuild: `npm --prefix ui-tui run build`
2. Run TUI: `hermes --tui`
3. Type `/` and verify command in autocomplete
4. Execute and confirm expected behavior
5. If gateway-available, test on messaging platform