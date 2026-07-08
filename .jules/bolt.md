## 2024-05-18 - [Combine SQLite Aggregations with Scalar Subqueries]
**Learning:** Multiple independent aggregate queries (like COUNT(*)) across different tables or condition filters can be combined into a single SELECT statement using scalar subqueries. This reduces connection/context overhead for database fetches.
**Action:** When gathering multiple counts or unrelated aggregates, use `SELECT (SELECT COUNT(...) FROM ...), (SELECT COUNT(...) FROM ...)` to fetch them all in one operation.
