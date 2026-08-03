## 2024-08-03 - [Reduce SQLite I/O with Scalar Subqueries]
**Learning:** Combining multiple independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions into a single SELECT statement using scalar subqueries (e.g., 'SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)') significantly reduces connection round trips and I/O overhead.
**Action:** Always look for sequential aggregate database queries executed independently on the same connection, and refactor them into a single query using scalar subqueries to improve performance.
