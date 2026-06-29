## 2024-06-29 - [Optimized SQLite Queries]
**Learning:** Multiple independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions cause high connection and I/O overhead.
**Action:** Combine them into a single SELECT statement using scalar subqueries (e.g., 'SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)') to significantly reduce overhead.
