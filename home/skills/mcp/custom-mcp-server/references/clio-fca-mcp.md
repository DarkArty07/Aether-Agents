# Clio FCA MCP — Real-World MCP Server Example

> **Purpose:** This is a detailed walkthrough of a real-world custom MCP server implementation. Use it as a concrete example alongside the general patterns in `custom-mcp-server` SKILL.md.

## What Clio Is

Clio is a custom MCP server for document generation, built by Christopher (DarkArty brand). It is a **Python** FastMCP project. The server exposes tools for AI-powered document composition, markdown-to-DOCX rendering, and FCA university task generation.

**Source location (Windows/WSL):**
```
/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/activos/clio-fca-mcp/
```

**MCP config (in Prometeo's config.yaml on Fedora):**
```yaml
clio-fca:
  command: uv
  args:
    - run
    - --directory
    - /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/activos/clio-fca-mcp
    - clio-fca
  enabled: true
  env:
    CLIO_PROVIDER_API_KEY: <key>
    CLIO_PROVIDER_BASE_URL: https://opencode.ai/zen/go/v1
    CLIO_PROVIDER_MODEL: qwen3.6-plus
```

## Source Architecture (Python)

```
src/clio_fca/
  __init__.py
  server.py                   — MCP server entry point, tool registration (FastMCP)
  tools/
    __init__.py
    compose.py                — AI content generation (compose_document)
    render_word.py            — Markdown → styled .docx conversion
    list_presets.py           — Lists available style presets
  fca/
    __init__.py
    generator.py              — Core: generate_fca_task (DOCX + optional PDF)
    reviewer.py               — fca_review_docx: format compliance audit
    progress.py               — fca_get/update/delete_progress
    drive.py                  — fca_download_drive (Google Drive)
  providers/
    __init__.py
    openai_provider.py        — OpenAI-compatible provider for compose_document
  styles/
    __init__.py
    loader.py                 — Preset loader (YAML/JSON definitions)
```

## MCP Tools Exposed

| Tool | Purpose |
|------|---------|
| `compose_document` | AI-powered Markdown generation (the "autorellenador") |
| `render_word` | Markdown → styled .docx conversion |
| `list_presets` | Show available style presets |
| `fca_generate_task` | Generate FCA university task (.docx + optional .pdf) |
| `fca_review_docx` | Audit .docx for FCA format compliance |
| `fca_get_progress` | Read task progress by subject |
| `fca_update_progress` | Update activity status |
| `fca_delete_progress` | Delete progress entries |
| `fca_download_drive` | Download file from Google Drive |

## fca_generate_task Key Parameters

```python
fca_generate_task(
    title: str,
    materia: str,
    unidad: str,
    actividad: str,
    sections: list[dict],      # [{type, text, ...}]
    output_path: str = "",
    convert_pdf: bool = True,
    style: str = "fca",        # "fca" (purple+borders) or "academico" (APA)
    academico_config: dict | None = None,
    portada_rubros: list[str] | None = None,
)
```

Section types: `heading`, `subheading`, `body`, `bold_item`, `separator`, `reference`, `table`, `image`, `footnote`.

## Preset System

Presets define visual styles for render_word. Structure in `styles/loader.py`:
- `margins` (top/right/bottom/left in cm)
- `alignment` (justified/left/center/right)
- `lineSpacing` (multiplier)
- `headingStyles` (h1-h4: fontSize, color, bold, fontName)
- `bodyStyle` (fontName, fontSize, color, lineSpacing)
- `pageBorder` (enabled, color, size, space)

## Academic Style (style="academico")

Config class `AcademicConfig` in generator.py with YAML override from `styles/academico.yaml`:
- Times New Roman, 12pt body, justified
- 1.5 line spacing between paragraphs, 1.0 within
- Footnotes support (real Word footnotes, not endnotes)
- Optional cover page via `portada_rubros`
- No page borders by default

## Known Pitfalls (Applicable to Any Doc-Gen MCP Server)

### PDF Conversion Bug
See `references/pdf-conversion-bug.md` for the full diagnostic pattern.

**Root cause:** `doc.save(output_path)` saved DOCX to a `.pdf` path before conversion. If LibreOffice missing or fails → DOCX disguised as PDF.

**Fix pattern:** Always save DOCX to `.docx` temp path, convert, then rename to desired `.pdf`.

### Cross-OS Development
Source lives on Windows (`/mnt/c/...`). MCP runs on Fedora via `uv run --directory`.
When editing from Ubuntu (Aether-Agents), access via `/mnt/c/` mount.

### PIL Image Validation
Generator validates images before processing. If PIL not installed, validation is skipped silently.
Supported formats: PNG, JPG, GIF, BMP, TIFF.

### LibreOffice Dependency
PDF conversion requires `libreoffice` or `soffice` on PATH. On Fedora:
```bash
sudo dnf install libreoffice-core
```

### Academic Config Coercion
`load_academic_config()` coerces string overrides to correct types (bool, int, float).
JSON/MCP args come as strings — the coercion handles this automatically.
