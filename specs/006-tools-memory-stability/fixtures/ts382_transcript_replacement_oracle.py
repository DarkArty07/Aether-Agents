"""TS-382 causal reproduction and pre/post acceptance oracle.

Bounded research fixture for the SessionDB transcript-write starvation
(SessionDB's single write lock vs. a transcript-replacement publisher).

What it exercises
-----------------
The automatic transcript publishers in the product (in-place compaction and the
proactive tool-result prune) publish a rewritten transcript through
``SessionDB.archive_and_compact`` -> ``_insert_message_rows``, i.e. ONE
``BEGIN IMMEDIATE`` transaction that re-inserts every row of the live
transcript while both legacy FTS insert triggers fire per row.  This fixture
builds that store shape in a temporary database and drives the real
SessionDB/state modules, then:

* ``test_generic_short_lock_is_waited_out`` — negative control: a short lock
  held by a plain connection is waited out (the store is healthy when busy
  briefly).  Passes on the unfixed source.
* ``test_replacement_does_not_starve_concurrent_append`` — acceptance: a real
  transcript append from a second SessionDB instance must succeed within its
  budget while a replacement batch is publishing.  FAILS on the unfixed source
  (the append exhausts its budget and raises the product's storage-busy error).
* ``test_replacement_lock_hold_within_budget`` — acceptance: no single write
  transaction opened by the replacement may hold the store's write lock longer
  than the append budget.  FAILS on the unfixed source.
* ``test_replacement_preserves_visibility_counters_archive_and_search`` —
  preservation: atomic visible replacement, counters, soft-archive + search
  semantics, model_config patch.
* ``test_failed_replacement_rolls_back_visible_transcript`` — preservation:
  an injected mid-publish failure leaves the old transcript visible, counters
  unchanged and the failed batch unsearchable.

Run it against a maintained-fork checkout (never the live runtime tree)::

    HERMES_FORK_SRC=<fork-checkout> \
    <fork-checkout>/.venv/bin/python -m pytest -q \
      specs/006-tools-memory-stability/fixtures/ts382_transcript_replacement_oracle.py \
      -p no:cacheprovider

Scale knobs (env, never raise a product timeout — they shorten the fixture):
    TS382_REPLACEMENT_ROWS   rows published per replacement (default 2400)
    TS382_CONTENT_CHARS      characters of deterministic content per row (default 8192)
    TS382_APPEND_BUDGET_S    the append's transcript budget used by the oracle
                             (default 1.0 — a scaled stand-in for the product's
                             20 s routine / 60 s transcript budgets).  The default
                             scale pair reproduces the RED on the production
                             (legacy inline FTS) store shape.
"""

from __future__ import annotations

import atexit
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

FORK_SRC = os.environ.get("HERMES_FORK_SRC", "")
if not FORK_SRC or not (Path(FORK_SRC) / "hermes_state.py").is_file():
    pytest.fail(
        "HERMES_FORK_SRC must point at the maintained-fork checkout that owns "
        "hermes_state.py (e.g. the unit's detached worktree); the fixture never "
        "loads the live editable runtime tree",
        pytrace=False,
    )

# Isolate every Hermes home lookup before importing the state modules.
_HOME = tempfile.mkdtemp(prefix="ts382-home-")
os.environ.setdefault("HERMES_HOME", _HOME)
atexit.register(shutil.rmtree, _HOME, ignore_errors=True)
sys.path.insert(0, FORK_SRC)

from hermes_state import SessionDB  # noqa: E402
from hermes_state_common import (  # noqa: E402
    FTS_TOOL_FULL_CONTENT_HIGH_WATER_KEY,
    LEGACY_FTS_SQL,
    LEGACY_FTS_TRIGRAM_SQL,
)

REPLACEMENT_ROWS = int(os.environ.get("TS382_REPLACEMENT_ROWS", "2400"))
CONTENT_CHARS = int(os.environ.get("TS382_CONTENT_CHARS", "8192"))
APPEND_BUDGET_S = float(os.environ.get("TS382_APPEND_BUDGET_S", "1.0"))

SESSION_ID = "ts382-session"
_NEW_NEEDLE = "ts382-new-needle"
_OLD_NEEDLE = "ts382-old-needle"
_MODEL_CONFIG_KEY = "_ts382_probe"


def _content(index: int, needle: str | None = None) -> str:
    """Deterministic high-entropy content so FTS trigram cost is realistic."""
    blocks = []
    block = hashlib.sha256(f"ts382-{index}".encode()).digest()
    while sum(len(part) for part in blocks) < CONTENT_CHARS:
        block = hashlib.sha256(block).digest()
        blocks.append(block.hex())
    body = "".join(blocks)[:CONTENT_CHARS]
    if needle:
        body = f"{needle} {index:05d} {body}"
    return body


def _transcript(rows: int, needle: str | None = None) -> list[dict]:
    """A tool-heavy transcript of exactly *rows* messages, every row large.

    The shape mirrors what an automatic transcript publisher re-inserts: the
    whole live message list (user / assistant-tool-call / tool-result /
    assistant-summary), not just the recent tail.
    """
    messages: list[dict] = []
    for i in range(rows):
        variant = i % 4
        if variant == 0:
            messages.append({"role": "user", "content": f"ts382 turn header {i}"})
        elif variant == 1:
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": f"call-{i}",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path": "/tmp/x"}'},
                }],
            })
        elif variant == 2:
            messages.append({
                "role": "tool",
                "content": _content(i, needle),
                "tool_name": "read_file",
                "tool_call_id": f"call-{i}",
            })
        else:
            messages.append({"role": "assistant", "content": f"ts382 summary {i}"})
    return messages[:rows]


def _force_legacy_layout(db: SessionDB) -> None:
    """Reproduce the production store's legacy inline-FTS layout + bound marker.

    The affected profile store is a pre-v23 install: inline ``messages_fts`` /
    ``messages_fts_trigram`` tables, the Aether #305 tool-content high-water
    bound, and no CJK index.  Fresh SessionDB databases are v23 external-content
    by default, so the fixture explicitly installs the legacy shape.
    """
    with db._lock:
        db._drop_fts_triggers(db._conn)
        db._conn.executescript(
            "DROP TABLE IF EXISTS messages_fts;"
            "DROP TABLE IF EXISTS messages_fts_trigram;"
            "DROP VIEW IF EXISTS messages_fts_trigram_src;"
            + LEGACY_FTS_SQL
            + LEGACY_FTS_TRIGRAM_SQL
        )
        db._conn.execute(
            "INSERT INTO state_meta(key, value) VALUES (?, '0') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (FTS_TOOL_FULL_CONTENT_HIGH_WATER_KEY,),
        )
        db._conn.commit()


_TEMPLATES: dict[str, Path] = {}


@pytest.fixture(scope="session")
def template_dir(tmp_path_factory) -> Path:
    """Pytest-managed scratch for the per-layout template stores."""
    return tmp_path_factory.mktemp("ts382-templates")


def _template(layout: str, template_dir: Path) -> Path:
    """Build (once per layout) a populated store to copy per test."""
    cached = _TEMPLATES.get(layout)
    if cached is not None and cached.exists():
        return cached

    path = template_dir / f"template-{layout}.db"
    db = SessionDB(path)
    db.create_session(SESSION_ID, source="tui")
    if layout == "legacy":
        _force_legacy_layout(db)
    db.append_messages_batch(SESSION_ID, _transcript(min(REPLACEMENT_ROWS, 400), _OLD_NEEDLE))
    db.close()
    _TEMPLATES[layout] = path
    return path


@pytest.fixture(params=["legacy", "v23"])
def store(request, template_dir, tmp_path):
    """Per-test copy of the populated template plus the handles it needs."""
    layout = request.param
    src = _template(layout, template_dir)
    db_path = tmp_path / "state.db"
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(db_path))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    writer = SessionDB(db_path)
    writer._sqlite_echo = False
    reader = SessionDB(db_path)
    appender = SessionDB(db_path)
    # Fixture-scale budgets ONLY shorten waits; no product timeout is raised.
    appender._TRANSCRIPT_WRITE_PATIENCE_S = APPEND_BUDGET_S
    appender._WRITE_PATIENCE_S = APPEND_BUDGET_S
    yield {
        "layout": layout,
        "db_path": db_path,
        "writer": writer,
        "reader": reader,
        "appender": appender,
    }
    for handle in (writer, reader, appender):
        handle.close()


def _visible(reader: SessionDB) -> list[tuple]:
    return [
        (m["role"], (m.get("content") or "")[:64], m.get("tool_call_id"))
        for m in reader.get_messages(SESSION_ID)
    ]


def _instrument_holds(db: SessionDB) -> dict:
    """Record every write transaction's (start, end) while the store is used."""
    result = {"holds": [], "inside": threading.Event(), "first_row_at": None}
    original_write = db._execute_write
    original_rows = db._insert_message_rows

    def timed_write(fn, patience_s=None):
        start = time.monotonic()
        try:
            return original_write(fn, patience_s=patience_s)
        finally:
            result["holds"].append((start, time.monotonic()))

    def observed_rows(conn, session_id, messages):
        if result["first_row_at"] is None:
            result["first_row_at"] = time.monotonic()
            result["inside"].set()
        return original_rows(conn, session_id, messages)

    db._execute_write = timed_write
    db._insert_message_rows = observed_rows
    return result


def _publish(writer: SessionDB, messages: list[dict], monkeypatch=None):
    return writer.archive_and_compact(
        SESSION_ID,
        messages,
        model_config_patch={_MODEL_CONFIG_KEY: REPLACEMENT_ROWS},
    )


def test_generic_short_lock_is_waited_out(store):
    """Negative control: a briefly held plain-SQLite lock must not starve an append."""
    started = threading.Event()
    failures: list[BaseException] = []

    def hold():
        conn = sqlite3.connect(str(store["db_path"]), timeout=1.0, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")
            started.set()
            time.sleep(0.2)
            conn.execute("ROLLBACK")
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)
        finally:
            conn.close()

    thread = threading.Thread(target=hold)
    thread.start()
    try:
        assert started.wait(5.0)
        msg_id = store["appender"].append_message(
            SESSION_ID, role="user", content="short-lock control"
        )
    finally:
        thread.join(timeout=10.0)
    assert not failures, f"lock holder failed: {failures[0]!r}"
    assert isinstance(msg_id, int)


def test_replacement_does_not_starve_concurrent_append(store):
    """Acceptance (RED pre-fix): an append must land while a replacement publishes."""
    writer, appender = store["writer"], store["appender"]
    plan = _instrument_holds(writer)
    replacement = _transcript(REPLACEMENT_ROWS, _NEW_NEEDLE)
    errors: list[BaseException] = []

    def publish():
        try:
            _publish(writer, replacement)
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    thread = threading.Thread(target=publish)
    thread.start()
    try:
        assert plan["inside"].wait(120.0), "publisher never entered its transaction"
        append_started = time.monotonic()
        appender.append_message(SESSION_ID, role="user", content="concurrent append")
        append_elapsed = time.monotonic() - append_started
    finally:
        thread.join(timeout=300.0)

    assert not errors, f"replacement failed: {errors[0]!r}"
    holds = [end - start for start, end in plan["holds"]]
    print(
        f"\n[{store['layout']}] longest write-lock hold: {max(holds):.3f}s "
        f"of {len(holds)} transaction(s); concurrent append: {append_elapsed:.3f}s "
        f"(budget {APPEND_BUDGET_S:.2f}s)"
    )
    # Post-fix this is the assertion that must hold; pre-fix the append above
    # raises sqlite3.OperationalError naming the held state.db write lock.
    assert append_elapsed <= APPEND_BUDGET_S * 1.5


def test_replacement_lock_hold_within_budget(store):
    """Acceptance (RED pre-fix): no single replacement transaction may exceed the budget."""
    writer = store["writer"]
    plan = _instrument_holds(writer)
    replacement = _transcript(REPLACEMENT_ROWS, _NEW_NEEDLE)
    _publish(writer, replacement)

    by_start = sorted(plan["holds"])
    longest = max(end - start for start, end in by_start)
    print(
        f"\n[{store['layout']}] {len(by_start)} write transaction(s); "
        f"longest hold {longest:.3f}s (budget {APPEND_BUDGET_S:.2f}s)"
    )
    assert longest <= APPEND_BUDGET_S


def test_replacement_preserves_visibility_counters_archive_and_search(store):
    """Preservation: atomic visible replacement, counters, archive and search semantics."""
    writer, reader = store["writer"], store["reader"]
    old_visible = _visible(reader)
    old_counts = dict(
        writer._conn.execute(
            "SELECT message_count, tool_call_count FROM sessions WHERE id = ?",
            (SESSION_ID,),
        ).fetchone()
    )
    replacement = _transcript(REPLACEMENT_ROWS, _NEW_NEEDLE)

    samples: list[list[tuple]] = []
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            samples.append(_visible(reader))
            time.sleep(0.01)

    sampler = threading.Thread(target=sample)
    sampler.start()
    try:
        _publish(writer, replacement)
    finally:
        stop.set()
        sampler.join(timeout=10.0)

    new_visible = _visible(reader)
    old_set = set(old_visible)
    new_set = set(new_visible)
    assert len(new_visible) == len(replacement), "publish did not replace the live transcript"
    for sample_ in samples:
        assert set(sample_) in (old_set, new_set), (
            "a concurrent reader observed a partially published transcript"
        )

    counts = dict(
        writer._conn.execute(
            "SELECT message_count, tool_call_count FROM sessions WHERE id = ?",
            (SESSION_ID,),
        ).fetchone()
    )
    assert counts["message_count"] == len(replacement)
    assert counts["message_count"] != old_counts["message_count"] or len(old_visible) == len(replacement)

    archived = writer._conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ? AND active = 0 AND compacted = 1",
        (SESSION_ID,),
    ).fetchone()[0]
    assert archived >= len(old_visible), "pre-replacement rows were not soft-archived"

    assert reader.search_messages(_NEW_NEEDLE), "published content is not searchable"
    assert reader.search_messages(_OLD_NEEDLE), "archived content lost search discoverability"

    config = writer._conn.execute(
        "SELECT model_config FROM sessions WHERE id = ?", (SESSION_ID,)
    ).fetchone()[0]
    assert f'"{_MODEL_CONFIG_KEY}"' in (config or ""), "model_config patch did not land"


def test_failed_replacement_rolls_back_visible_transcript(store):
    """Preservation: an injected mid-publish failure must leave the store unchanged."""
    writer, reader = store["writer"], store["reader"]
    old_visible = _visible(reader)
    old_counts = dict(
        writer._conn.execute(
            "SELECT message_count, tool_call_count FROM sessions WHERE id = ?",
            (SESSION_ID,),
        ).fetchone()
    )
    replacement = _transcript(REPLACEMENT_ROWS, _NEW_NEEDLE)

    original_rows = writer._insert_message_rows

    def failing_rows(conn, session_id, messages):
        partial = messages[: max(1, len(messages) // 4)]
        original_rows(conn, session_id, partial)
        raise RuntimeError("ts382 injected publish failure")

    writer._insert_message_rows = failing_rows
    with pytest.raises(Exception):
        _publish(writer, replacement)
    writer._insert_message_rows = original_rows

    assert _visible(reader) == old_visible, "visible transcript changed after a failed publish"
    counts = dict(
        writer._conn.execute(
            "SELECT message_count, tool_call_count FROM sessions WHERE id = ?",
            (SESSION_ID,),
        ).fetchone()
    )
    assert counts == old_counts, "counters changed after a failed publish"
    assert not reader.search_messages(_NEW_NEEDLE), (
        "text from a failed publish is still searchable"
    )
