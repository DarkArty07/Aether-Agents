# Hermes Agent CLI Skins — Complete Reference

Source: Context7 query of hermes-agent docs (2026-05-22). Full YAML schema for custom skins.

## Location

Custom skins live at `~/.hermes/skins/<name>.yaml`. Activate with `/skin <name>` in the CLI or set in `config.yaml`.

## Inheritance

Skins inherit from the `default` skin. Only specify values you want to override. Missing keys fall back automatically.

## Complete YAML Schema

```yaml
# ~/.hermes/skins/mytheme.yaml
name: mytheme
description: My custom theme

colors:
  banner_border: "#CD7F32"       # Panel border color
  banner_title: "#FFD700"        # Panel title color
  banner_accent: "#FFBF00"       # Section header color
  banner_dim: "#B8860B"          # Muted/dim text color
  banner_text: "#FFF8DC"         # Body text color
  ui_accent: "#FFBF00"           # UI accent color (bars, highlights)
  ui_label: "#4dd0e1"            # Labels and metadata color
  ui_ok: "#4caf50"               # Success/confirmation color
  ui_error: "#ef5350"             # Error color
  ui_warn: "#ffa726"             # Warning color
  prompt: "#FFF8DC"              # User input text color
  input_rule: "#CD7F32"          # Prompt separator line color
  response_border: "#FFD700"     # Response box border color
  session_label: "#DAA520"       # Active session label color
  session_border: "#8B8682"     # Session border color
  status_bar_bg: "#1a1a2e"       # Status bar background
  voice_status_bg: "#1a1a2e"     # Voice status background
  selection_bg: "#333355"        # Text selection background
  completion_menu_bg: "#1a1a2e"   # Autocomplete menu background
  completion_menu_current_bg: "#333355"  # Selected autocomplete item bg
  completion_menu_meta_bg: "#1a1a2e"    # Menu metadata background
  completion_menu_meta_current_bg: "#333355"  # Selected metadata bg

spinner:
  waiting_faces:
    - "(⚔)"
    - "(⛨)"
    - "(▲)"
  thinking_faces:
    - "(⚔)"
    - "(⌁)"
    - "(<>)"
  thinking_verbs:
    - "processing"
    - "analyzing"
    - "computing"
    - "evaluating"
  wings:
    - ["⟪⚡", "⚡⟫"]
    - ["⟪●", "●⟫"]

branding:
  agent_name: "My Agent"
  welcome: "Welcome to My Agent! Type your message or /help for commands."
  goodbye: "See you later! ⚡"
  response_label: " ⚡ My Agent "
  prompt_symbol: "⚡"
  help_header: "(⚡) Available Commands"

tool_prefix: "┊"

# Per-tool emoji overrides (optional)
tool_emojis:
  terminal: "⚔"
  web_search: "🔮"
  read_file: "📄"

# Custom ASCII art banners (optional, Rich markup supported)
# Use pyfiglet or asciified API to generate banner text — NEVER hand-draw.
# banner_logo: |
#   [bold #FFD700] MY AGENT [/]
# banner_hero: |
#   [#FFD700]  Custom art here  [/]
```

## Key Notes

- **banner_logo and banner_hero**: Support Rich markup (`[bold #color]...[/]`). Use pyfiglet or asciified API to generate banner text — hand-drawn ASCII art is unreliable.
- **Colors**: All values are hex strings (`"#RRGGBB"`). These map to Rich color names or hex values.
- **spinner.wings**: Left/right decorations that frame the spinner. Pairs of strings in each list item.
- **spinner.thinking_verbs**: Rotated through during the thinking animation.
- **tool_emojis**: Override the default emoji for any tool by tool function name.
- **tool_prefix**: Single character prefixing each tool output line.
- **Activation**: `/skin <name>` from CLI, or set `display.skin: mytheme` in `config.yaml` under the `display:` section.

### Pitfall: Dark colors invisible on black terminals

When designing skins, dark purple/indigo colors (e.g. `#311B92`, `#4A148C`, `#6A1B9A`) are nearly invisible on a black terminal background. When fixing visibility issues, stay within the existing dual-palette — brighten shades within the same color family rather than introducing a third color family. For a cyan+lilac theme, use bright saturated lilac/purple values that remain visible on black:

- Light lilac (dim text): `#CE93D8` — not pastel green `#8BC34A`
- Medium lilac (rules, separators): `#BA68C8` — not dark green `#558B2F`
- Neon lilac (borders, highlights): `#E040FB` — not lime green `#7CB342`
- Bright purple (selection bg): `#9C27B0` — not dark green `#1B5E20`
- Medium bright purple (current item bg): `#AB47BC` — not green `#2E7D32`

The key test: view the color on a black (#000000) background. If it blends in, it's too dark.

### Pitfall: Skin files have two locations — keep them in sync

The skin engine uses `get_hermes_home()` to resolve the skins directory. In Aether Agents deployments, this means skin YAML files exist in TWO locations that must stay in sync:

1. `~/.hermes/skins/<name>.yaml` — Hermes home directory (fallback)
2. `$HERMES_HOME/skins/<name>.yaml` — Aether Agents home (active when `HERMES_HOME` is set, e.g. `/home/prometeo/Aether-Agents/home`)

When `HERMES_HOME` is set, skins are loaded from `$HERMES_HOME/skins/`, so edits to `~/.hermes/skins/` alone will NOT take effect. When editing a skin, always update BOTH copies and verify with `md5sum`. If `HERMES_HOME` is unset, it falls back to `~/.hermes/`.

**Config key**: The default skin is set under `display.skin` in `config.yaml` (NOT under a separate `ui:` section). Example:

```yaml
display:
  skin: hermes-cyberpunk
```

## Built-in Skins

Use `/skin` with no arguments to list all available skins. Built-in skins can be activated by name. Custom skins from `~/.hermes/skins/` are listed alongside built-ins.

## Recommended Font Choices for banner_logo

Generated with `python3 -m pyfiglet "TEXT" -f <font>`:

| Font | Style | Best for |
|------|-------|----------|
| slant | Italic modern, diagonal lines | Project names, speed/movement themes |
| doom | Bold blocks, strong presence | Titles, maximum impact |
| cyberlarge | Thick lines, no serif | Cyberpunk/digital themes |
| speed | Stylized like paths/routes | Messaging, relay themes |
| big | Large and readable | General banners |
| 3-d | 3D effect with shadow | Holographic/depth themes |

## Design Methodology for Custom Skins

### Dual-Palette Approach

The most visually cohesive skins use two complementary accent colors (not one) plus a deep background:

1. **Primary accent** (e.g. cyan `#18FFFF`) — for active data, titles, user input, signals
2. **Secondary accent** (e.g. lilac `#E040FB`) — for structure, branding, borders, prompt
3. **Deep background** (e.g. `#0A0E27`) — navy-black void that makes both accents pop

### Brightness Hierarchy, Not Just Color

Map each accent across 3-4 brightness levels:

- **Bright** (`#18FFFF`, `#E040FB`) — titles, borders, important labels
- **Medium** (`#00BCD4`, `#7C4DFF`, `#B388FF`) — body text, response borders, accents
- **Dark** (`#4A148C`, `#00838F`) — separators, subtle borders
- **Very dark** (`#311B92`, `#0A0E27`) — backgrounds, selection, dim text

This creates depth without needing more than 2 accent colors.

### Semantic Color Preservation

Green, red, and amber are reserved for their universal meanings:
- `ui_ok` = green (success)
- `ui_error` = red (error)
- `ui_warn` = amber (warning)

Never replace these with your accent colors — users need instant visual semantics.

### Recurring Glyph Identity

Pick one Unicode symbol and use it everywhere as your brand glyph:
- Spinner faces: `(◈)`, wings: `⟪◈`, `◈⟫`
- Prompt symbol: `◈`
- Response label: `◈ Hermes ◈`
- Welcome/help: `◈ HERMES — Orchestrator Online ◈`

This creates visual coherence across all UI elements.

### Banner Generation

ALWAYS generate banner text with `pyfiglet` or `asciified API`. NEVER hand-draw ASCII art — LLMs produce misaligned, ugly banners. Use Rich markup for color:

```yaml
banner_logo: |
  [bold #18FFFF]    __  ____________  __  ______________[/]
  [bold #18FFFF]   / / / / ____/ __ \/  |/  / ____/ ___/[/]
  [bold #E040FB]/_/ /_/_____/_/ |_/_/  /_/_____//____/  [/]
```

### Template

A complete working example is at `templates/hermes-cyberpunk.yaml` — copy it as a starting point for your own skin.