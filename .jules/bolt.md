## 2024-07-29 - Combine Independent COUNT Queries
**Learning:** Making multiple independent `COUNT(*)` queries using separate execute calls incurs significant connection and I/O overhead.
**Action:** Combine independent aggregates into a single SELECT statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)`). This reduced query execution time by roughly 3x in benchmarks.
