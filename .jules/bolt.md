## 2026-07-07 - [Avoid Unsafe Ruff Fixes]
**Learning:** Using `--unsafe-fixes` with `ruff check` in this codebase can execute poor automated fixes for unused variables. It may remove only the variable assignment but leave the right-hand side expression floating (e.g., preserving expensive but unused I/O calls), introducing unmaintainable code.
**Action:** Avoid using `--unsafe-fixes`. Handle unused variable warnings manually to ensure proper logic, or leave them if removing them breaks correctness.
