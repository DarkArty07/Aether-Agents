## 2024-07-31 - Combine multiple SQLite COUNT queries with scalar subqueries
**Learning:** Independent aggregate queries (like COUNT) across different tables or conditions can cause unnecessary roundtrips, I/O, and connection overhead when executed one by one. SQLite's scalar subqueries allow you to merge them into a single SELECT statement.
**Action:** When gathering multiple counts or isolated aggregates, always use a single query structured as `SELECT (SELECT COUNT(*)...), (SELECT COUNT(*)...)` and bind parameters using `?1` to reuse them.
