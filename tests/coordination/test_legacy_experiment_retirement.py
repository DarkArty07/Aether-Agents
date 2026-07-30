"""Removal contract for retired v0.19 parallel and pre-kernel runtimes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETIRED_MODULES = (
    "admission",
    "capabilities",
    "channels",
    "context",
    "harmonia",
    "identity",
    "native_transport",
    "pilot",
    "pilot_compiler",
    "pilot_evidence",
    "pilot_model",
    "pilot_store",
    "presence",
    "protocol",
    "schema",
    "shadow",
    "shadow_store",
    "transport",
)
RETIRED_RUNTIME_PATHS = (
    "scripts/run_r7_shadow_benchmark.py",
    "scripts/run_r8_snake_pilot.py",
    "spikes/001-harmonia-lease-heartbeat/main.py",
    "tests/phase0/authorization_boundary_proof.py",
    "tests/phase0/coordination_sqlite_proof.py",
    "tests/phase0/test_authorization_boundary_proof.py",
    "tests/phase0/test_coordination_sqlite_proof.py",
    "tests/phase0/test_effect_boundary_proof.py",
    *(f"src/olympus_v3/coordination/{module}.py" for module in RETIRED_MODULES),
)
RETIRED_PUBLIC_EXPORTS = (
    "AdmissionEngine",
    "CapabilityClaim",
    "Channel",
    "ContextArtifact",
    "Envelope",
    "HarmoniaCoordinator",
    "IdentityCredential",
    "LedgerNativeTransport",
    "NativeTransportAdapter",
    "ParticipantCard",
    "PilotCoordinator",
    "PilotError",
    "PilotManifest",
    "PilotStore",
    "PilotTask",
    "PresenceTracker",
    "ShadowConfig",
    "TaskStatus",
    "compile_snake_manifest",
    "encode_result",
    "parse_and_verify_result",
)


def test_parallel_and_pre_kernel_runtime_files_are_retired() -> None:
    remaining = [path for path in RETIRED_RUNTIME_PATHS if (ROOT / path).exists()]

    assert remaining == [], f"retired runtime files still shipped: {remaining}"


def test_coordination_api_has_no_retired_runtime() -> None:
    import olympus_v3.coordination as coordination
    from olympus_v3.coordination.olympus_adapter import OlympusRuntimeAdapter

    exports = [name for name in RETIRED_PUBLIC_EXPORTS if hasattr(coordination, name)]
    adapter_methods = [
        name
        for name in ("dispatch", "observe", "dispatch_pilot_task", "observe_pilot_task")
        if hasattr(OlympusRuntimeAdapter, name)
    ]

    assert exports == [], f"retired exports still public: {exports}"
    assert adapter_methods == [], f"retired adapter methods still public: {adapter_methods}"


def test_server_import_does_not_load_retired_runtime() -> None:
    retired_modules = repr(tuple(f"olympus_v3.coordination.{module}" for module in RETIRED_MODULES))
    code = f"""\
import sys
import olympus_v3.server
retired = {retired_modules}
loaded = sorted(name for name in sys.modules if name in retired)
if loaded:
    raise SystemExit("loaded retired modules: " + ",".join(loaded))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
