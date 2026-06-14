## 2024-06-14 - [Combine multiple independent SQLite queries into a single query]
**Learning:** In the `olympus_v3/db.py`, `get_session_progress` executed multiple independent aggregate SQLite queries sequentially which adds unnecessary database connection roundtrips and IO overhead.
**Action:** Used scalar subqueries combined into a single SELECT statement to execute all aggregate functions in one database query, which is significantly faster and reduces latency overhead.
