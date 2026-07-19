## 2023-10-24 - Scalar Subqueries in SQLite
**Learning:** Combining multiple independent `SELECT COUNT(*)` statements on the same or different tables using scalar subqueries into a single query significantly reduces the overhead of context switching and I/O.
**Action:** When finding multiple independent `SELECT COUNT(*)` or simple aggregates run consecutively, combine them into a single query where appropriate.
