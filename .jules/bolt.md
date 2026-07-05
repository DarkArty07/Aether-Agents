## 2025-07-05 - [Single-Query Progress Optimization]
**Learning:** SQLite supports combining independent aggregate queries into single roundtrips via scalar subqueries. This drastically reduces context switches and driver overhead in both aiosqlite (async) and sqlite3 (sync) adapters, especially during frequent progress checks on active connections.
**Action:** When querying progress counters or multiple disconnected aggregates simultaneously, combine them into a single `SELECT (SELECT ...), (SELECT ...)` query.
