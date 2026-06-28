import sqlite3
import time

conn = sqlite3.connect(':memory:')
conn.execute("CREATE TABLE turns (session_id TEXT, role TEXT, content TEXT, timestamp REAL)")
conn.execute("CREATE TABLE tool_calls (session_id TEXT, tool_name TEXT)")

for i in range(100):
    conn.execute("INSERT INTO turns VALUES ('s1', 'assistant', 'content', 1.0)")
    conn.execute("INSERT INTO tool_calls VALUES ('s1', 'tool')")
conn.commit()

# old way
start = time.time()
for _ in range(1000):
    c1 = conn.execute("SELECT COUNT(*) FROM turns WHERE session_id = ? AND role = 'assistant'", ('s1',)).fetchone()[0]
    c2 = conn.execute("SELECT COUNT(*) FROM turns WHERE session_id = ? AND content IS NOT NULL AND content != ''", ('s1',)).fetchone()[0]
    c3 = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", ('s1',)).fetchone()[0]
    c4 = conn.execute("SELECT MAX(timestamp) FROM turns WHERE session_id = ?", ('s1',)).fetchone()[0]
end1 = time.time()

start2 = time.time()
for _ in range(1000):
    c1, c2, c3, c4 = conn.execute("""
    SELECT
        (SELECT COUNT(*) FROM turns WHERE session_id = ? AND role = 'assistant'),
        (SELECT COUNT(*) FROM turns WHERE session_id = ? AND content IS NOT NULL AND content != ''),
        (SELECT COUNT(*) FROM tool_calls WHERE session_id = ?),
        (SELECT MAX(timestamp) FROM turns WHERE session_id = ?)
    """, ('s1', 's1', 's1', 's1')).fetchone()
end2 = time.time()

print(f"Old: {end1 - start}")
print(f"New: {end2 - start2}")
