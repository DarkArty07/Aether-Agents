#!/usr/bin/env python3
"""Migrate data from home/.aether/aether.db to project-level .aether/aether.db.

This script merges valid Aether Agents data from the contaminated home/.aether/aether.db
into the correct Aether-Agents/.aether/aether.db, then removes the contaminated DB.

USAGE:
    python scripts/migrate_aether_db.py --dry-run   # Preview changes without writing
    python scripts/migrate_aether_db.py              # Perform migration

After successful migration, you can manually delete home/.aether/ if desired:
    rm -rf home/.aether/

IMPORTANT: This script does NOT delete home/.aether/aether.db automatically.
It only merges data INTO the project-level DB. You must verify and then
remove the old DB manually.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default paths (adjust if your setup differs)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOME_AETHER_DB = PROJECT_ROOT / "home" / ".aether" / "aether.db"
PROJECT_AETHER_DB = PROJECT_ROOT / ".aether" / "aether.db"

# Keywords that identify Aether Agents data (vs Barajas Dumont ERP data)
AETHER_AGENTS_KEYWORDS = [
    "olympus", "aether", "hefesto", "plugin", "hooks", "daimon",
    "hermes", "acp", "mcp", "server", "adapter", "profile",
    "talk_to", "delegate", "consulta", "consult",
]


def is_aether_agents_record(text: str | None) -> bool:
    """Check if a text field contains Aether Agents keywords."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in AETHER_AGENTS_KEYWORDS)


def migrate(dry_run: bool = False) -> None:
    """Perform the migration."""
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Source (home): {HOME_AETHER_DB}")
    print(f"Target (project): {PROJECT_AETHER_DB}")
    print()

    # Check source exists
    if not HOME_AETHER_DB.exists():
        print(f"Source DB not found at {HOME_AETHER_DB}. Nothing to migrate.")
        return

    # Ensure target .aether/ directory exists
    if not PROJECT_AETHER_DB.parent.exists():
        if dry_run:
            print(f"[DRY RUN] Would create directory: {PROJECT_AETHER_DB.parent}")
        else:
            PROJECT_AETHER_DB.parent.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {PROJECT_AETHER_DB.parent}")

    # Connect to source DB
    src = sqlite3.connect(str(HOME_AETHER_DB))
    src.row_factory = sqlite3.Row

    # Read source data
    src_sessions = src.execute("SELECT * FROM sessions").fetchall()
    src_decisions = src.execute("SELECT * FROM decisions").fetchall()
    src_issues = src.execute("SELECT * FROM issues").fetchall()
    src_hot_state = src.execute("SELECT * FROM hot_state WHERE id = 1").fetchone()
    src.close()

    print(f"Source DB contains:")
    print(f"  Sessions: {len(src_sessions)}")
    print(f"  Decisions: {len(src_decisions)}")
    print(f"  Issues: {len(src_issues)}")
    print()

    # Filter Aether Agents data
    aether_sessions = []
    for s in src_sessions:
        summary = s["result_summary"] or ""
        request = s["request"] or ""
        agent = s["agent"] or ""
        # Aether Agents sessions: agent names like hefesto, ariadna, etc. on
        # Aether Agents project, or sessions mentioning Aether Agents keywords
        if agent.lower() in ("hefesto", "etalides", "daedalus", "athena", "ictinus"):
            # Only include if content is about Aether Agents, not Barajas
            if not _is_barajas_record(summary) or is_aether_agents_record(summary + request):
                aether_sessions.append(s)
        elif is_aether_agents_record(summary + request):
            aether_sessions.append(s)

    aether_decisions = [d for d in src_decisions if is_aether_agents_record(
        (d["title"] or "") + (d["decision"] or "") + (d["rationale"] or "")
    )]

    # Issues: exclude #2 (Tauri bug belongs to Barajas) — keep Aether Agents issues only
    aether_issues = [i for i in src_issues if is_aether_agents_record(
        (i["description"] or "") + (i["error_type"] or "")
    )]

    print(f"Aether Agents data to migrate:")
    print(f"  Sessions: {len(aether_sessions)}")
    print(f"  Decisions: {len(aether_decisions)}")
    print(f"  Issues: {len(aether_issues)}")
    print()

    if not any([aether_sessions, aether_decisions, aether_issues]):
        print("No Aether Agents data found in source DB. Nothing to migrate.")
        return

    if dry_run:
        print("[DRY RUN] Would merge the above records into project-level DB.")
        print("[DRY RUN] Would NOT delete home/.aether/aether.db.")
        print()
        print("Aether Agents sessions to migrate:")
        for s in aether_sessions:
            print(f"  - {s['session_id']} ({s['agent']}): {(s['result_summary'] or '')[:80]}")
        print("Aether Agents decisions to migrate:")
        for d in aether_decisions:
            print(f"  - #{d['id']}: {d['title']}")
        print("Aether Agents issues to migrate:")
        for i in aether_issues:
            print(f"  - #{i['id']}: {i['description'][:80]}")
        return

    # Connect to target DB (create if needed)
    if not PROJECT_AETHER_DB.exists():
        print(f"Target DB does not exist. Creating: {PROJECT_AETHER_DB}")
        # Need to create tables — use the same schema as aether_db.py
        _init_db(PROJECT_AETHER_DB)

    dst = sqlite3.connect(str(PROJECT_AETHER_DB))
    dst.row_factory = sqlite3.Row

    # Migrate sessions
    migrated_sessions = 0
    for s in aether_sessions:
        try:
            dst.execute(
                "INSERT OR IGNORE INTO sessions "
                "(session_id, agent, started_at, completed_at, status, "
                "request, result_summary, files_modified, errors, model, platform, duration_seconds) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    s["session_id"], s["agent"], s["started_at"], s["completed_at"],
                    s["status"], s["request"], s["result_summary"],
                    s["files_modified"], s["errors"], s["model"], s["platform"],
                    s["duration_seconds"],
                ),
            )
            migrated_sessions += 1
        except sqlite3.IntegrityError:
            print(f"  Session {s['session_id']} already exists in target, skipping.")

    # Migrate decisions (with new auto-increment IDs)
    migrated_decisions = 0
    for d in aether_decisions:
        try:
            dst.execute(
                "INSERT INTO decisions "
                "(title, decision, rationale, alternatives, made_by, status, created_at, superseded_at, superseded_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    d["title"], d["decision"], d["rationale"], d["alternatives"],
                    d["made_by"], d["status"], d["created_at"],
                    d["superseded_at"], d["superseded_by"],
                ),
            )
            migrated_decisions += 1
        except sqlite3.IntegrityError:
            print(f"  Decision '{d['title']}' already exists in target, skipping.")

    # Migrate issues (with new auto-increment IDs)
    migrated_issues = 0
    for i in aether_issues:
        try:
            dst.execute(
                "INSERT INTO issues "
                "(session_id, description, error_type, status, created_at, resolution, resolved_by, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    i["session_id"], i["description"], i["error_type"],
                    i["status"], i["created_at"],
                    i["resolution"], i["resolved_by"], i["resolved_at"],
                ),
            )
            migrated_issues += 1
        except sqlite3.IntegrityError:
            print(f"  Issue #{i['id']} already exists in target, skipping.")

    # Update hot_state with correct project_root
    dst.execute(
        "UPDATE hot_state SET project_root = ?, project_name = 'Aether Agents' WHERE id = 1",
        (str(PROJECT_ROOT),),
    )

    dst.commit()
    dst.close()

    print(f"\nMigration complete!")
    print(f"  Sessions migrated: {migrated_sessions}")
    print(f"  Decisions migrated: {migrated_decisions}")
    print(f"  Issues migrated: {migrated_issues}")
    print()
    print(f"IMPORTANT: home/.aether/aether.db was NOT deleted.")
    print(f"After verifying the migration, remove it manually:")
    print(f"  rm {HOME_AETHER_DB}")


def _is_barajas_record(text: str) -> bool:
    """Check if a text field is specifically about Barajas Dumont ERP."""
    if not text:
        return False
    text_lower = text.lower()
    barajas_keywords = ["barajas", "dumont", "erp", "tauri", "trpc", "prisma"]
    return any(kw in text_lower for kw in barajas_keywords)


def _init_db(db_path: Path) -> None:
    """Initialize a fresh aether.db with the standard schema."""
    SCHEMA_STMTS = [
        """CREATE TABLE IF NOT EXISTS hot_state (
            id INTEGER PRIMARY KEY DEFAULT 1,
            project_name TEXT, project_root TEXT, description TEXT,
            current_phase TEXT DEFAULT 'idea', current_task TEXT,
            last_session_id TEXT, last_agent TEXT,
            last_request TEXT, last_result TEXT, last_error TEXT,
            recent_files TEXT, pending_items TEXT, blockers TEXT,
            total_sessions INTEGER DEFAULT 0, updated_at REAL NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, agent TEXT NOT NULL,
            started_at REAL NOT NULL, completed_at REAL, status TEXT DEFAULT 'active',
            request TEXT, result_summary TEXT, files_modified TEXT, errors TEXT,
            model TEXT, platform TEXT, duration_seconds INTEGER
        )""",
        "CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
        """CREATE TABLE IF NOT EXISTS file_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(session_id),
            agent TEXT NOT NULL, file_path TEXT NOT NULL,
            action TEXT NOT NULL, timestamp REAL NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_file_changes_path ON file_changes(file_path)",
        "CREATE INDEX IF NOT EXISTS idx_file_changes_session ON file_changes(session_id)",
        """CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            decision TEXT NOT NULL, rationale TEXT, alternatives TEXT,
            made_by TEXT NOT NULL, status TEXT DEFAULT 'active',
            created_at REAL NOT NULL, superseded_at REAL,
            superseded_by INTEGER REFERENCES decisions(id)
        )""",
        """CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(session_id),
            description TEXT NOT NULL, error_type TEXT,
            resolution TEXT, resolved_by TEXT,
            status TEXT DEFAULT 'open', created_at REAL NOT NULL, resolved_at REAL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)",
        "INSERT OR IGNORE INTO hot_state (id, project_name, project_root, updated_at) VALUES (1, '', '', 0)",
    ]

    conn = sqlite3.connect(str(db_path))
    for stmt in SCHEMA_STMTS:
        conn.execute(stmt)
    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Aether Agents data from home/.aether/ to project-level .aether/"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to the database.",
    )
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()