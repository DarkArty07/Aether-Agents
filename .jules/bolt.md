## 2024-05-24 - Consolidate SQLite aggregate queries using scalar subqueries
**Learning:** Combining multiple independent SQLite aggregate queries (like COUNT(*)) across different tables/conditions into a single SELECT statement using scalar subqueries significantly reduces connection and I/O overhead.
**Action:** When making multiple aggregate queries to a SQLite database sequentially, check if they can be grouped into a single query to improve performance.
