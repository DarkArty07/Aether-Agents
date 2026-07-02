## 2024-07-02 - Combine independent aggregate queries
**Learning:** When executing multiple independent `COUNT(*)` queries on SQLite in asynchronous contexts (using aiosqlite), the I/O and connection overhead of dispatching multiple individual statements can become a bottleneck.
**Action:** Combine independent aggregate queries into a single statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM a), (SELECT COUNT(*) FROM b)`) to reduce overhead and improve throughput.
