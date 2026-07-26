## 2024-07-26 - Consolidating SQLite Aggregate Queries
**Learning:** Multiple independent `COUNT(*)` queries on different tables or conditions execute as separate round-trips to the SQLite database, causing connection and I/O overhead.
**Action:** Combine them into a single SELECT statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)`) to significantly reduce this overhead.
