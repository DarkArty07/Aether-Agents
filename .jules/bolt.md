## 2025-06-28 - Combine independent aggregate queries in SQLite
**Learning:** When retrieving multiple independent aggregate counts from different tables or using different conditions in SQLite, executing them sequentially incurs overhead from multiple parsing/execution round-trips.
**Action:** Use a single SELECT statement with multiple scalar subqueries (e.g. `SELECT (SELECT COUNT(*) FROM A), (SELECT COUNT(*) FROM B)`) to fetch all the necessary values in one go, which meaningfully reduces connection and I/O overhead.
