## 2024-05-27 - [Optimize sequential SQLite aggregate queries]
**Learning:** When combining independent aggregate queries (like `COUNT(*)`) across different SQLite tables, use scalar subqueries within a single `SELECT` statement (e.g., `SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)`) to reduce connection and I/O overhead.
**Action:** Always combine independent aggregate queries in SQLite when they are executed sequentially without conditional logic.
