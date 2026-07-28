## 2024-05-24 - [Batching SQLite aggregate queries]
**Learning:** Combining multiple independent SQLite aggregate queries (like `COUNT(*)`) across different tables or conditions into a single statement using scalar subqueries significantly reduces connection and I/O overhead.
**Action:** Always combine independent aggregate queries into a single `SELECT` statement instead of executing them separately.
