## 2024-05-17 - [Combine Scalar Subqueries]
**Learning:** Combining multiple independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions using scalar subqueries can significantly reduce connection and I/O overhead.
**Action:** In future optimizations, I will combine independent queries into a single SELECT statement using scalar subqueries (e.g., 'SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)') to reduce connection overhead. Using explicit index binding like '?1' allows reusing the same parameter safely.
