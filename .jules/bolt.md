## 2026-06-24 - [Optimize SQLite count queries]
**Learning:** In the Olympus DB module (`db.py` and `server.py`), polling functions repeatedly hit the database sequentially for different aggregates (`COUNT(*)` on multiple tables/filters) right after a WAL checkpoint. Waiting on each `await` connection step introduces cumulative async event loop blocking and I/O latency.
**Action:** Combine multiple independent SQLite scalar queries into single batched `SELECT` statement using subqueries to reduce connection round-trips and I/O latency.
