import asyncio
import time
import uuid
import sys
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path("src").absolute()))

from olympus_v3.db import OlympusDB

async def main():
    db_path = Path("test_perf.db")
    if db_path.exists():
        db_path.unlink()

    db = OlympusDB(db_path)
    await db.connect()

    session_id = str(uuid.uuid4())
    await db.insert_session(session_id, "test_agent")

    for i in range(100):
        await db.insert_turn(session_id, i, "assistant", f"content {i}")
        await db.insert_tool_call(str(uuid.uuid4()), session_id, "test_tool")

    # Baseline
    start = time.time()
    for _ in range(100):
        # Do the separate queries
        cursor = await db._execute("SELECT COUNT(*) FROM turns WHERE session_id = ? AND role = 'assistant'", (session_id,))
        thoughts = (await cursor.fetchone())[0]

        cursor = await db._execute("SELECT COUNT(*) FROM turns WHERE session_id = ? AND content IS NOT NULL AND content != ''", (session_id,))
        messages = (await cursor.fetchone())[0]

        cursor = await db._execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,))
        tool_calls = (await cursor.fetchone())[0]
    end = time.time()
    baseline_time = end - start
    print(f"Separate queries: {baseline_time:.4f}s")

    # Optimized
    start = time.time()
    for _ in range(100):
        cursor = await db._execute(
            """
            SELECT
                (SELECT COUNT(*) FROM turns WHERE session_id = ? AND role = 'assistant'),
                (SELECT COUNT(*) FROM turns WHERE session_id = ? AND content IS NOT NULL AND content != ''),
                (SELECT COUNT(*) FROM tool_calls WHERE session_id = ?)
            """,
            (session_id, session_id, session_id)
        )
        row = await cursor.fetchone()
        thoughts, messages, tool_calls = row[0], row[1], row[2]
    end = time.time()
    optimized_time = end - start
    print(f"Combined query: {optimized_time:.4f}s")

    await db.close()
    if db_path.exists():
        db_path.unlink()
    if Path("test_perf.db-wal").exists():
        Path("test_perf.db-wal").unlink()
    if Path("test_perf.db-shm").exists():
        Path("test_perf.db-shm").unlink()

asyncio.run(main())
