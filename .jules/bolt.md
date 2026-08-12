## 2023-10-27 - O(N) database filtering in python
**Learning:** Found a performance bottleneck in `TraceStore.records_for` where all records from the database are loaded into memory and filtered in Python (O(N) operation) instead of utilizing an SQL `WHERE` clause.
**Action:** Always prefer explicit SQL queries with `WHERE` clauses instead of fetching all records into memory and applying Python-side filtering to avoid O(N) bottlenecks and reduce memory footprint.
