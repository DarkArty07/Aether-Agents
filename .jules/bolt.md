## 2024-05-24 - Consolidating multiple SQLite aggregate queries
**Learning:** When executing multiple independent `COUNT(*)` queries against different tables or conditions on a SQLite database, it is more performant to combine them into a single `SELECT` statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) ...), (SELECT COUNT(*) ...)`). This avoids the connection and I/O overhead of multiple separate executions.
**Action:** Combine multiple independent aggregate queries into a single query using scalar subqueries whenever possible to reduce connection overhead.
