## 2023-10-27 - SQLite Query Combinations
**Learning:** Multiple sequential `COUNT(*)` database queries (e.g., getting multiple independent metrics for session status) can be optimized into a single database roundtrip using single-query subqueries or conditional aggregations (`SUM(CASE WHEN ... THEN 1 ELSE 0 END)`). This heavily reduces async roundtrips through `aiosqlite`.
**Action:** When gathering multiple metrics or counts from a database at once, check if they can be combined into a single `SELECT` block.

## 2023-10-27 - Useless dead code vs Performance
**Learning:** Linters like `ruff` will correctly flag unused variables but may keep the expression side-effects during auto-fixing. For operations like `Path(project_root)` or `path.read_text()` that perform disk I/O, auto-fixing just the assignment to remove the linter warning is insufficient and leaves the performance cost intact.
**Action:** When fixing "unused variable" linting errors, inspect the RHS of the assignment. If the expression itself has no meaningful side effect or is just an expensive operation being discarded, delete the entire statement, not just the assignment.
