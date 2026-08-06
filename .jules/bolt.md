## 2024-08-06 - Combine independent SQLite aggregate queries
**Learning:** Combining independent SQLite aggregate queries (like COUNT(*)) across different tables or conditions into a single query using scalar subqueries (e.g., SELECT (SELECT COUNT(*)...), (SELECT COUNT(*)...)) avoids multiple round trips and connection overhead. Explicit index binding like `?1` allows safely reusing the same constraint parameter without redundant tuple values.
**Action:** Always look for consecutive `COUNT(*)` queries with the same parameter and combine them using scalar subqueries.
