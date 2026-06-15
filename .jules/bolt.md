## 2024-06-25 - Group multiple identical SELECT COUNT queries in SQLite
**Learning:** When retrieving summary progress containing identical conditions (e.g. `WHERE session_id = ?`) across `COUNT(*)` in the database, breaking them down into multiple `conn.execute()` sequentially increases Python-SQLite boundary overhead.
**Action:** Use scalar subqueries within a single `SELECT` block for multiple counts on the same identifier (like `session_id`) to significantly reduce connection and I/O overhead.
