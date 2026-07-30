## 2025-02-12 - Combined multiple independent SQLite aggregate queries
**Learning:** Combining multiple independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions into a single SELECT statement using scalar subqueries (e.g., 'SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)') can reduce connection and I/O overhead.
**Action:** Always look out for sequential COUNT/aggregate queries in DB methods and combine them into single scalar subquery statements to optimize DB roundtrips.
