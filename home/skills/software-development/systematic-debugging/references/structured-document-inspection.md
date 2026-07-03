# Structured Document Inspection — False-Positive Traps

When a user reports a bug with **structured evidence** (twips, key positions, attribute values), the FIRST check is whether the inspection method is sound. Bugs in parsing/inspection create "false positives" — symptoms that look real but aren't.

## OOXML `<w:pgMar>` — The Classic Trap

`<w:pgMar>` (page margins) is one of the most-inspected elements in Word documents. python-docx writes the attributes in **ECMA-376 canonical order**: `top, right, bottom, left, header, footer, gutter`.

### The False-Positive Pattern

A user inspects the .docx XML with:
```python
import re
margins = re.findall(r'w:(?:top|bottom|left|right)="(\d+)"', doc_xml)
# Returns: ['1417', '1701', '1417', '1701'] in (top, bottom, left, right) pattern order
# NOT in (top, right, bottom, left) XML canonical order
```

The user then presents a table:
```
| top    | 1417  | 2.50cm | 2.50cm ✓ |
| bottom | 1701  | 3.00cm | 2.50cm ✗ |
| left   | 1417  | 2.50cm | 3.00cm ✗ |
| right  | 1701  | 3.00cm | 3.00cm ✓ |
```

And concludes: "bottom and left are swapped." But the values are correct — the user's regex returned the 4 values in **pattern group order**, not XML order. The correct mapping:

```
XML order:     top (1417), right (1701), bottom (1417), left (1701)  ← all correct
Regex order:   top (1417), bottom (1701), left (1417), right (1701)  ← mislabeled
```

### Correct Inspection Recipe

Always use the canonical API to read structured elements, not raw text parsing:

```python
import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}

with zipfile.ZipFile("file.docx") as z:
    doc = z.read("word/document.xml")
    tree = etree.fromstring(doc)

# Find the pgMar element
pgMar = tree.find(".//w:sectPr/w:pgMar", NS)
if pgMar is not None:
    margins = {
        attr: int(pgMar.get(f"{{{W}}}{attr}"))
        for attr in ("top", "right", "bottom", "left")
    }
    # margins = {"top": 1417, "right": 1701, "bottom": 1417, "left": 1701}  ← correct
```

Convert twips to cm: `cm = twips / 567.0`.

### Why This Matters

The user provided **specific numeric evidence** (1417, 1701, 1417, 1701), which created an illusion of certainty. But the numbers were correct; the labels were wrong. The bug was in the inspection tool (regex), not in the code (the .docx). The lesson: **specific data + wrong inspection method = false-positive bug report**.

## When This Class of Bug Appears

| Domain | Symptom | Spec Reference | Verify With |
|--------|---------|----------------|-------------|
| OOXML `<w:pgMar>` | Margins look "swapped" | ECMA-376 §17.6.21 | `lxml` parsing of sectPr/pgMar |
| OOXML `<w:tblPr>` | Table properties look wrong | ECMA-376 §17.4.60 | `lxml` parsing of tblPr |
| JSON object keys | Key "order" looks wrong | RFC 8259 (order not specified) | `json.load` + explicit key access |
| XML attributes (general) | Attribute order looks wrong | XML 1.0 (no order) | `lxml` element iteration |
| CSV columns | Column "position" looks wrong | RFC 4180 (header row defines) | `csv.DictReader` |
| PDF coordinates | Object position looks wrong | PDF spec (origin bottom-left) | `pdfplumber`/`PyPDF2` bbox |
| YAML mappings | Key order looks wrong | YAML 1.2 (order preserved in PyYAML) | `yaml.safe_load` + key access |

## The "Reverse the Regex Pattern" Quick Test

If you suspect the bug is a measurement error (not in the code), try this:

1. The user's regex returns N values.
2. The user interprets them in pattern order (group 1, group 2, ...).
3. Re-run the regex with a different pattern order.
4. If the same values now "look correct" under the new order, the bug is in interpretation, not in the code.

Example:
```python
# User's regex (suspicious order)
re.findall(r'w:(top|bottom|left|right)="(\d+)"', doc)
# Returns: [('top', '1417'), ('bottom', '1701'), ('left', '1417'), ('right', '1701')]

# Try canonical OOXML order
re.findall(r'w:(top|right|bottom|left)="(\d+)"', doc)
# Returns: [('top', '1417'), ('right', '1701'), ('bottom', '1417'), ('left', '1701')]

# Now the values match the spec ordering. No bug.
```

## Lesson for the Orchestrator

When a user reports a bug with structured evidence:

1. **First** check the inspection method. A 2-line `lxml` script takes 30 seconds.
2. **Then** check the code. Don't delegate to Hefesto to "fix" a bug that doesn't exist.
3. **Never** trust specific evidence without verifying the extraction method. Numbers lie when the parser lies.

When delegating a bug fix to Hefesto, include a verification recipe in the prompt:
```markdown
VERIFICATION:
1. Run this lxml script to read margins from the .docx:
   [insert 5-line script]
2. If the script shows the expected values, the bug is real.
3. If the script shows different values from the bug report, the bug report was wrong — investigate the inspection method, not the code.
```

This pattern matches the "User-Provided Bug Fix" variant in SKILL.md — but the variant assumes the user has localized the bug in the code. The variant should NOT apply when the user has localized the bug in a measurement, not in the code. The orchestrator (Hermes) is responsible for this distinction.
