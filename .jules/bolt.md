## 2024-05-24 - [Optimize SQLite count queries]
**Learning:** In `db.py`, performing multiple separate aggregate queries (`COUNT(*)`, `MAX()`) sequentially creates unnecessary round-trips and connection/IO overhead.
**Action:** When multiple independent SQLite aggregate queries are needed across different conditions or tables for a single request, combine them into a single `SELECT` statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*)...), (SELECT MAX(*)...)`) to improve performance. This yielded a ~45% speed improvement in benchmarking.
