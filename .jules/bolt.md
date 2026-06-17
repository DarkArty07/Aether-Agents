## 2024-06-17 - [Combine Multiple COUNT(*) Queries into One]
**Learning:** SQLite aggregate queries like `COUNT(*)` across different tables or conditions can be combined into a single `SELECT` statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM table1), (SELECT COUNT(*) FROM table2)`). This significantly reduces connection and I/O overhead.
**Action:** When seeing multiple independent aggregate queries executed sequentially, refactor them into a single query to enhance performance.
