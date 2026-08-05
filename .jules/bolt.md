## 2024-08-05 - Combined SQLite COUNT queries for better performance
**Learning:** Combining multiple independent SQLite aggregate queries (like COUNT(*)) across different tables/conditions into a single SELECT statement using scalar subqueries reduces overhead and improves execution time significantly (~57% improvement locally).
**Action:** When performing multiple COUNT(*) operations on the same logical entity in SQLite, always try to use scalar subqueries inside a single SELECT rather than making sequential executes.
