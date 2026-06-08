## 2024-06-08 - Combine multiple aggregate queries into a single query using scalar subqueries
**Learning:** In SQLite, making multiple separate aggregate queries (like `COUNT(*)` or `MAX()`) adds unnecessary connection and I/O overhead. Combining them into a single query using scalar subqueries can reduce roundtrips and improve performance.
**Action:** Always combine independent aggregate queries across different tables or conditions into a single `SELECT` statement with scalar subqueries when fetching metrics or progress indicators.
