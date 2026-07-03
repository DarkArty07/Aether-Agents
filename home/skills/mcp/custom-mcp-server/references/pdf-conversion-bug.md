# PDF Conversion Bug — Diagnostic Pattern

> Generalized from the Clio FCA MCP server bug. Applicable to any document pipeline that converts between formats (docx→pdf, html→pdf, etc.)

## The Bug (discovered 2026-06-09)

`fca_generate_task` with `convert_pdf=true` generated a DOCX file with `.pdf` extension.
`file` command confirmed: `Microsoft Word 2007+` inside a `.pdf` wrapper.

## Root Cause

In a document generation pipeline:

```python
output_path = data.get("output_path", "output.docx")  # user passes "file.pdf"
doc.save(output_path)  # ← DOCX bytes saved to "file.pdf"!
```

The DOCX was saved to the user's desired output path (ending in `.pdf`) BEFORE conversion.
If LibreOffice was missing or failed silently (`except Exception: pass`), the result was
a DOCX disguised as a PDF.

## Fix Pattern — Applicable to Any Document Pipeline

**Rule: Never save intermediate format to the final output path.**

```python
if convert_pdf:
    # 1. Save intermediate DOCX to temp path
    docx_path = Path(output_path).with_suffix(".docx")
    doc.save(str(docx_path))

    # 2. Attempt conversion
    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice:
        return {"ok": True, "path": str(docx_path), "format": "docx",
                "warning": "LibreOffice not found."}

    proc = subprocess.run(
        [libreoffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, str(docx_path)],
        capture_output=True, timeout=60
    )

    # 3. Only rename to desired path if conversion succeeded
    pdf_path = Path(out_dir) / docx_path.with_suffix(".pdf").name
    if pdf_path.exists():
        desired = Path(output_path)
        if desired.suffix.lower() == ".pdf" and desired != pdf_path:
            pdf_path.rename(desired)
        # Clean up temp DOCX
        docx_path.unlink()
        return {"ok": True, "path": str(desired), "format": "pdf"}
    else:
        # Conversion failed — return DOCX with warning, NOT a fake PDF
        return {"ok": True, "path": str(docx_path), "format": "docx",
                "warning": f"PDF conversion failed (exit {proc.returncode})"}
else:
    doc.save(output_path)
```

## Anti-Patterns

1. **Silent `except Exception: pass`** on conversion — never swallow conversion errors
2. **Saving target format before conversion** — always save intermediate format to temp path
3. **Not checking `shutil.which()`** before calling external tools — fail gracefully with message
4. **Not capturing `subprocess.stderr`** — LibreOffice errors are on stderr, not stdout

## Detection

```bash
file suspicious.pdf
# Expected: "PDF document"
# Bug shows: "Microsoft Word 2007+"
```

## LibreOffice CLI

```bash
libreoffice --headless --convert-to pdf --outdir /tmp input.docx
# Converts input.docx → /tmp/input.pdf
# Exit code 0 = success, check if output file exists
```
