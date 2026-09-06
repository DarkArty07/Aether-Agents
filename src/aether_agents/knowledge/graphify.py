"""A bounded subprocess adapter to the separately installed Graphify component."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .common import KnowledgeError, clean_environment


class GraphifyBackend:
    def __init__(self, python: Path, *, timeout: float = 60.0):
        # Do not resolve a venv interpreter symlink: doing so loses its environment.
        self.python = python.expanduser().absolute()
        self.timeout = min(max(float(timeout), 1.0), 300.0)

    def probe(self) -> dict[str, Any]:
        return self.run("probe")

    def run(
        self,
        action: str,
        *,
        source_root: Path | None = None,
        graph_path: Path | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.python.is_file():
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Configure the isolated Graphify component."
            )
        worker = Path(__file__).with_name("graph_worker.py")
        request = {
            "action": action,
            "source_root": str(source_root) if source_root else "",
            "graph_path": str(graph_path) if graph_path else "",
            "arguments": arguments or {},
        }
        encoded = json.dumps(request, ensure_ascii=False).encode("utf-8")
        if len(encoded) > 2_000_000:
            raise KnowledgeError(
                "SCOPE_UNAVAILABLE", "The component request exceeds its byte limit."
            )
        with tempfile.TemporaryDirectory(prefix="aether-graphify-") as scratch:
            home = Path(scratch)
            try:
                process = subprocess.Popen(
                    [str(self.python), "-I", str(worker)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=home,
                    env=clean_environment(home),
                    start_new_session=(os.name == "posix"),
                )
            except OSError as exc:
                raise KnowledgeError(
                    "COMPONENT_UNAVAILABLE", "The Graphify process could not start."
                ) from exc
            try:
                stdout, _stderr = process.communicate(encoded, timeout=self.timeout)
            except BaseException as exc:
                # Cancellation and timeout must not leave a detached indexer alive.
                with contextlib.suppress(ProcessLookupError):
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                process.communicate()
                if isinstance(exc, subprocess.TimeoutExpired):
                    raise KnowledgeError(
                        "TIMEOUT", "Graphify exceeded its execution limit."
                    ) from exc
                raise
        if len(stdout) > 2_000_000:
            raise KnowledgeError("RESULT_TOO_LARGE", "Graphify returned an oversized result.")
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeError) as exc:
            raise KnowledgeError(
                "COMPONENT_UNAVAILABLE", "Graphify returned an invalid response."
            ) from exc
        if not isinstance(result, dict) or not result.get("ok") or process.returncode:
            code = "COMPONENT_UNAVAILABLE" if action == "probe" else "INDEX_CORRUPT"
            raise KnowledgeError(code, "Graphify could not complete the requested operation.")
        return result
