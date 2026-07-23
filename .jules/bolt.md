## 2026-07-23 - Combining independent aggregate queries in SQLite
**Learning:** Sequential, independent aggregate queries (like `COUNT(*)`) against the same or different tables in SQLite result in unnecessary repetitive connection and I/O overhead.
**Action:** Combine them into a single `SELECT` statement using scalar subqueries (e.g., `SELECT (SELECT COUNT(*) FROM t1 WHERE ...), (SELECT COUNT(*) FROM t2 WHERE ...)`). This extracts all desired aggregates in one round trip, noticeably improving performance in frequently called methods like progress monitoring.
