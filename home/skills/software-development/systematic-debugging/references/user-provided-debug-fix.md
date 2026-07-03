# User-Provided Bug Fix Pattern

## Overview

When the user has already localized a bug and provides exact fix steps, the agent's role is **mechanical execution**, not investigation. This pattern is the inverse of the standard systematic-debugging workflow: the investigation (Phases 1-3) was done by the user.

## Session Example: Clio-FCA Margin Swap Bug

### Context
- Project: `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/activos/clio-fca-mcp`
- File: `src/clio_fca/fca/generator.py`
- Bug: A "Reorder pgMar attributes" block (lines ~250-265) reordered XML attribute order from OOXML canonical (top/right/bottom/left) to (top/bottom/left/right), causing Word/python-docx to interpret values in wrong semantic slots → bottom/left margins swapped.

### Fix Steps
The user provided:
1. Exact file path and line numbers
2. The exact code block to delete (with comment text as anchor)
3. A reproduction script to verify
4. A regex-based verification command
5. Commit message template
6. Gateway restart command

### Key Observations

#### 1. The patch tool can produce false-positive "success" on no-op edits
When the `old_string` doesn't actually exist in the file, the patch tool's fuzzy matching may report `success: true` with a diff anyway, **without actually modifying the file**. Always verify with `git diff HEAD -- <file>` after patching to confirm the change was real.

#### 2. The reorder block may not exist in any commit
In this session, `_create_academic_doc()` was introduced in commit `6056b9e` without the reorder block. The user was describing a local, uncommitted change. Step to verify:
```bash
git show HEAD:src/clio_fca/fca/generator.py | sed -n '245,265p'
git log --all -p -- src/clio_fca/fca/generator.py | grep "Reorder pgMar"
```
If both return empty, the block was never committed — it existed only in the user's working tree.

#### 3. After a no-op fix, still run the user's verification script
Even if `git diff HEAD` is empty, run the reproduction script and regex check to confirm margins are correct. The verification output confirms the code is sound.

#### 4. Gateway restart
```bash
systemctl --user restart hermes-gateway-prometeo.service
systemctl --user is-active hermes-gateway-prometeo.service
```

### Reproduction Script (adapted for actual API)
```python
import sys
sys.path.insert(0, "/path/to/project/src")
from clio_fca.fca.generator import generate_fca_task

data = {
    'title': 'Test',
    'materia': 't', 'unidad': 'I', 'actividad': '1',
    'sections': [{'type':'body','text':'x'}],
    'output_path': '/tmp/test/margenes_test.docx',
}
result = generate_fca_task(data, style='academico',
    academico_config={'margin_top_cm':2.5,'margin_bottom_cm':2.5,
                      'margin_left_cm':3.0,'margin_right_cm':3.0},
    convert_pdf=False)
print(result)
```

### Verification Command
```bash
python3 -c "
import zipfile, re
with zipfile.ZipFile('/tmp/test/margenes_test.docx') as z:
    doc = z.read('word/document.xml').decode('utf-8')
margins = re.findall(r'w:(?:top|bottom|left|right)=\"(\d+)\"', doc)
print(margins)
"
```

### OOXML Margin Values Reference
| cm  | MU (1/360000 inch → actually 1/914400 inch EMU) |
|-----|---------------------------------------------------|
| 2.5 | 1417 (top, bottom default)                        |
| 3.0 | 1701 (left, right default)                        |

### Canonical OOXML pgMar Attribute Order
`top, right, bottom, left, header, footer, gutter`
