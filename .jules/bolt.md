## 2024-05-18 - Single SQLite connection for combined scalar queries
**Learning:** Combining multiple independent aggregate queries (like `COUNT(*)`) across tables into a single SELECT statement using scalar subqueries significantly reduces SQLite connection and I/O overhead.
**Action:** When gathering multiple counts or unrelated aggregates, use `SELECT (SELECT COUNT(...) FROM table1), (SELECT COUNT(...) FROM table2)` instead of multiple separate `conn.execute` / `cursor.execute` calls.
