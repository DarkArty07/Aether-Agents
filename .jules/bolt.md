## 2024-05-20 - Combine Multiple COUNT Queries
**Learning:** In SQLite databases, running multiple separate `SELECT COUNT(*)` queries sequentially adds unnecessary connection and I/O overhead.
**Action:** Use conditional aggregation (e.g., `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`) to combine multiple COUNTs into a single query, significantly reducing the number of database hits.
