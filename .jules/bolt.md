## 2024-06-27 - Combining Aggregate Queries in SQLite
**Learning:** Optimizing multiple independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions can be done by combining them into a single SELECT statement using scalar subqueries (e.g., 'SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)'). This reduces connection and I/O overhead.
**Action:** When performing multiple count queries for session progress, use a single query with scalar subqueries to batch the counts in a single I/O operation.
