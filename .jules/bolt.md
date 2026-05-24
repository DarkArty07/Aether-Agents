## 2024-05-24 - Combine multiple sequential SQLite aggregate queries
**Learning:** Sequential `COUNT(*)` queries against different SQLite tables in the same code path cause unnecessary connection and I/O overhead.
**Action:** When combining independent aggregate queries, use scalar subqueries within a single SELECT statement (e.g., `SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)`) to reduce overhead while maintaining clean code syntax.
