## 2024-05-16 - SQLite Concurrent Aggregation Overhead
**Learning:** Performing multiple simple aggregate queries (like COUNT(*)) sequentially in sqlite3/aiosqlite incurs unnecessary I/O overhead compared to combining them.
**Action:** Use conditional aggregation (`SUM(CASE WHEN...)`) to combine multiple simple count queries on the same table into a single query to reduce connection overhead and execution time significantly (approx 30-40% reduction).
