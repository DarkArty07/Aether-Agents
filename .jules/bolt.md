## 2024-05-18 - SQLite Batching and Python DB Calls
**Learning:** In the SQLite database wrapper (`OlympusDB` and `OlympusDBSync`), performing multiple separate `COUNT(*)` queries can be significantly slow because of connection and I/O overhead. Converting multiple `COUNT(*)` statements to be fetched in one network round trip using scalar subqueries resulted in a 2.8x speedup. Furthermore, removing utility scripts after testing helps keep the codebase clean.
**Action:** Always batch related count queries inside SQLite functions. Clean up temporary test files immediately after you finish.
