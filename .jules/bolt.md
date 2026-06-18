## 2024-06-11 - [Optimize multiple independent COUNT(*) queries]
**Learning:** In SQLite, executing multiple independent `COUNT(*)` queries on different tables/conditions back-to-back incurs repeated I/O and connection overhead.
**Action:** Combine them into a single `SELECT` statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM turns...), (SELECT COUNT(*) FROM tool_calls...);`) to reduce DB round-trips while guaranteeing a single row result.
