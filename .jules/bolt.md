## 2025-02-18 - Query Optimization for SQLite
**Learning:** Combining multiple `COUNT(*)` queries into a single SQL statement using scalar subqueries can significantly reduce the number of database round-trips for both synchronous and asynchronous operations.
**Action:** When performing aggregate operations on different tables or using different conditions, group them into a single `SELECT (SELECT ...), (SELECT ...) ` statement instead of making individual database calls.
