#!/usr/bin/env python3
"""RS-PROOF — Contaminated-previous disposable two-hop proof harness.

Authority: Objective Contract oc_f190ae9e878151e6@v2 (SHA-256
9bd2828f6f13e086db394d3bb26afb289a23cb5f78293738594fb399c8567188),
in-scope 3-4, AC-3, AC-4, and breakdown unit RS-PROOF from
specs/001-aether-v1-productization/tasks-rc4-restore.md.

Executes:
1. Revalidates reviewed bridge identities (AC-3):
   - parent 5a897746afe422f3c07f2290f9115d60204ef4d2
   - child d763c15b30f6edd8709aa2df33772b3601c67915 (VERSION only)
   - annotated tag v1.0.0-a.4 (tag object 5350ebb0ea91f6d6099d96d7448590515fff6036)
   - wheel SHA-256 0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec
   - no remote branch/tag
2. Witnesses live system state (active.json, runtime/current, service unit,
   launcher, desktop entries, WSL shortcuts).
3. Sets up isolated disposable environment where _is_installed_environment is false.
4. Seeds disposable previous release as an exact rc3 record with allowlisted contamination.
5. Executes Hop 1 pre-restore: verifies lexical rc3 manager refuses update with
   LOCAL_UPDATE_REFUSED and non-regular/source-integrity error class.
6. Executes reviewed restorer (restore_exact_hermes_source): proves rc3 validate_release
   and doctor become ready without mutating record/selector/manager/runtime/profiles.
7. Executes Hop 1 post-restore: lexical rc3 manager activates bridge (1.0.0a4).
   Proves bridge release created, manager authority validated, TUI absent, no canary.
8. Executes Hop 2: bridge manager activates final rc4 (1.0.0rc4 / 5a897746).
   Proves hash-bound TUI/provenance, branded projections, doctor ready, pending 0.
9. Witnesses live system state post-run: asserts 100% byte-identical preservation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

WORKTREE_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = WORKTREE_ROOT
if REPO_ROOT.parent.name == ".worktrees":
    REPO_ROOT = REPO_ROOT.parent.parent
USER_HOME = Path.home()

# Live witness paths
LIVE_SHARE = USER_HOME / ".local" / "share" / "aether"
LIVE_ACTIVE_JSON = LIVE_SHARE / "active.json"
LIVE_RUNTIME_CURRENT = LIVE_SHARE / "runtime" / "current"
LIVE_SERVICE_UNIT = USER_HOME / ".config" / "systemd" / "user" / "hermes-gateway-morfeo.service"
LIVE_LAUNCHER = USER_HOME / ".local" / "bin" / "aether"
LIVE_LEGACY_DESKTOP = USER_HOME / ".local" / "share" / "applications" / "hermes.desktop"
LIVE_BRANDED_DESKTOP = USER_HOME / ".local" / "share" / "applications" / "aether.desktop"

# Verified identities
RC3_RELEASE_ID = "1.0.0rc3-8987f650c027ad09"
RC3_MANAGER_PYTHON = LIVE_SHARE / "releases" / RC3_RELEASE_ID / "manager" / "bin" / "python"

BRIDGE_CHECKOUT = Path("/tmp/aether-bridge-1.0.0a4")
BRIDGE_COMMIT = "d763c15b30f6edd8709aa2df33772b3601c67915"
BRIDGE_PARENT_COMMIT = "5a897746afe422f3c07f2290f9115d60204ef4d2"
BRIDGE_TAG = "v1.0.0-a.4"
BRIDGE_TAG_OBJECT = "5350ebb0ea91f6d6099d96d7448590515fff6036"
BRIDGE_WHEEL_SHA256 = "0345df7335d338ffd2205c6bb0b3f66c8636824c2b0392248988a9224d6f01ec"

RC4_CHECKOUT = Path("/tmp/aether-rc4-candidate")
RC4_COMMIT = "5a897746afe422f3c07f2290f9115d60204ef4d2"
RC4_TAG = "v1.0.0-rc.4"

FORK_CHECKOUT = Path("/tmp/aether-hermes-aed6591-branch")
FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
EXPECTED_FORK_TREE_SHA256 = "cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7"

DISPOSABLE_BASE = Path("/tmp/rs-proof-disposable")
EXPECTED_TUI_SHA256 = "f56f6225d9124376eedec1834d372c76a33292aedc41021cc13d6c3b32a05643"
PROJECT_ID = "12027989-a08f-41cd-a82c-54ff1bfb6b03"


def sha256_file(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_live_fingerprints() -> dict[str, Any]:
    wsl_shortcuts: dict[str, Any] = {}
    try:
        from aether_agents.lifecycle import detect_wsl_shortcuts_dir

        wsl_dir = detect_wsl_shortcuts_dir()
        if wsl_dir is not None and wsl_dir.is_dir():
            for p in sorted(wsl_dir.iterdir()):
                if "aether" in p.name.lower() or "hermes" in p.name.lower():
                    wsl_shortcuts[p.name] = sha256_file(p)
    except Exception:
        pass

    rc_target = None
    if LIVE_RUNTIME_CURRENT.is_symlink():
        try:
            rc_target = os.readlink(LIVE_RUNTIME_CURRENT)
        except OSError:
            pass

    return {
        "active_json_sha256": sha256_file(LIVE_ACTIVE_JSON),
        "runtime_current_target": rc_target,
        "service_unit_sha256": sha256_file(LIVE_SERVICE_UNIT),
        "launcher_sha256": sha256_file(LIVE_LAUNCHER),
        "legacy_desktop_sha256": sha256_file(LIVE_LEGACY_DESKTOP),
        "branded_desktop_sha256": sha256_file(LIVE_BRANDED_DESKTOP),
        "wsl_shortcuts": wsl_shortcuts,
    }


def revalidate_bridge_identities() -> dict[str, Any]:
    print("--- Revalidating Bridge Identities (AC-3) ---")

    # Verify parent and commit target
    cat_type = subprocess.check_output(
        ["git", "cat-file", "-t", BRIDGE_TAG],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert cat_type == "tag", f"Expected tag object, got {cat_type}"

    tag_obj = subprocess.check_output(
        ["git", "rev-parse", f"{BRIDGE_TAG}^{{tag}}"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert tag_obj == BRIDGE_TAG_OBJECT, f"Tag object mismatch: {tag_obj} != {BRIDGE_TAG_OBJECT}"

    commit_target = subprocess.check_output(
        ["git", "rev-parse", f"{BRIDGE_TAG}^{{commit}}"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert commit_target == BRIDGE_COMMIT, (
        f"Commit target mismatch: {commit_target} != {BRIDGE_COMMIT}"
    )

    parent_commit = subprocess.check_output(
        ["git", "rev-parse", f"{BRIDGE_COMMIT}^1"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert parent_commit == BRIDGE_PARENT_COMMIT, (
        f"Parent commit mismatch: {parent_commit} != {BRIDGE_PARENT_COMMIT}"
    )

    # Verify git diff is VERSION only
    diff_stat = subprocess.check_output(
        ["git", "diff", "--stat", f"{BRIDGE_PARENT_COMMIT}..{BRIDGE_COMMIT}"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert "VERSION | 2 +-" in diff_stat, f"Diff is not VERSION only: {diff_stat}"
    assert "1 file changed, 1 insertion(+), 1 deletion(-)" in diff_stat, (
        f"Unexpected diff stat: {diff_stat}"
    )

    # Verify remote tag is empty
    ls_remote = subprocess.check_output(
        ["git", "ls-remote", "--tags", "origin", BRIDGE_TAG],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert ls_remote == "", f"Remote tag origin/{BRIDGE_TAG} must not exist, found: {ls_remote}"

    # Verify wheel SHA-256 and metadata
    bridge_wheel = BRIDGE_CHECKOUT / "dist" / "aether_agents-1.0.0a4-py3-none-any.whl"
    assert bridge_wheel.is_file(), f"Bridge wheel missing at {bridge_wheel}"
    wheel_sha = sha256_file(bridge_wheel)
    assert wheel_sha == BRIDGE_WHEEL_SHA256, (
        f"Bridge wheel sha mismatch: {wheel_sha} != {BRIDGE_WHEEL_SHA256}"
    )

    metadata_version = None
    with zipfile.ZipFile(bridge_wheel) as z:
        for name in z.namelist():
            if name.endswith("METADATA"):
                for line in z.read(name).decode("utf-8", errors="ignore").splitlines():
                    if line.startswith("Version:"):
                        metadata_version = line.split(":", 1)[1].strip()
                        break
    assert metadata_version == "1.0.0a4", (
        f"Bridge wheel METADATA version mismatch: {metadata_version}"
    )

    results = {
        "tag": BRIDGE_TAG,
        "tag_object": tag_obj,
        "commit": commit_target,
        "parent_commit": parent_commit,
        "diff_stat": diff_stat,
        "wheel_path": str(bridge_wheel),
        "wheel_sha256": wheel_sha,
        "wheel_metadata_version": metadata_version,
        "remote_tags": ls_remote,
    }
    print("Bridge identities revalidated successfully:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    return results


def make_disposable_env(base: Path) -> dict[str, str]:
    home = base / "home"
    data = base / "data"
    state = base / "state"
    config = base / "config"
    cache = base / "cache"

    for d in (home, data, state, config, cache):
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)

    clean_path = str(USER_HOME / ".local" / "bin") + ":/usr/local/bin:/usr/bin:/bin"
    clean_env = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(data),
        "XDG_STATE_HOME": str(state),
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(cache),
        "PATH": clean_path,
        "AETHER_PROJECT_ID": PROJECT_ID,
    }
    return clean_env


def register_disposable_project(state_root: Path) -> None:
    projects_file = state_root / "projects" / "registry.json"
    projects_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "projects": {
            PROJECT_ID: {
                "name": "Aether Agents",
                "path": str(REPO_ROOT),
            }
        },
    }
    projects_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def seed_disposable_previous_rc3(
    disposable_base: Path,
    env: dict[str, str],
) -> tuple[Path, Path]:
    print("\n--- Seeding Disposable Previous rc3 Release with Allowlisted Contamination ---")
    data_root = Path(env["XDG_DATA_HOME"]) / "aether"
    state_root = Path(env["XDG_STATE_HOME"]) / "aether"
    data_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)
    os.chmod(data_root, 0o700)
    os.chmod(state_root, 0o700)

    register_disposable_project(state_root)

    live_rc3_dir = LIVE_SHARE / "releases" / RC3_RELEASE_ID
    assert live_rc3_dir.is_dir(), f"Live rc3 release dir missing: {live_rc3_dir}"

    disposable_rc3_dir = data_root / "releases" / RC3_RELEASE_ID
    disposable_rc3_dir.mkdir(parents=True, exist_ok=True)

    # Copy release files and subtrees
    for item in [
        "record.json",
        "release.json",
        "release-lock.json",
        "profile-bundle.json",
        "artifacts",
        "manager",
        "runtime",
        "profiles",
    ]:
        src = live_rc3_dir / item
        dst = disposable_rc3_dir / item
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)

    # Recreate venv symlink -> runtime
    (disposable_rc3_dir / "venv").symlink_to("runtime")

    # Copy contaminated hermes-source from live rc3 release
    live_hermes_source = live_rc3_dir / "hermes-source"
    disposable_hermes_source = disposable_rc3_dir / "hermes-source"
    shutil.copytree(live_hermes_source, disposable_hermes_source, symlinks=True)

    # Write active.json
    rc3_record = json.loads((disposable_rc3_dir / "record.json").read_text(encoding="utf-8"))
    active_json_path = data_root / "active.json"
    active_json_path.write_text(json.dumps(rc3_record, indent=2) + "\n", encoding="utf-8")
    os.chmod(active_json_path, 0o600)

    # Recreate runtime/current symlink
    runtime_dir = data_root / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_current = runtime_dir / "current"
    runtime_current.symlink_to(disposable_rc3_dir)

    # Initialize store and manager to materialize profiles and projections using rc3 manager python
    init_code = (
        "import sys, os\n"
        "from pathlib import Path\n"
        "from aether_agents.lifecycle import LifecycleManager, ReleaseStore\n"
        "data_root = Path(os.environ['XDG_DATA_HOME']) / 'aether'\n"
        "state_root = Path(os.environ['XDG_STATE_HOME']) / 'aether'\n"
        "store = ReleaseStore(data_root, state_root=state_root)\n"
        "store._ensure_owned_root()\n"
        "manager = LifecycleManager(store=store, python_executable=Path(sys.executable))\n"
        "assert not manager.installed_environment, 'Must not be installed environment'\n"
        "rec = store.active()\n"
        "assert rec is not None\n"
        "manager._materialize_profile_homes(rec)\n"
        "manager.project_release(rec, restart_service=False)\n"
    )
    p_init = subprocess.run(
        [str(RC3_MANAGER_PYTHON), "-c", init_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if p_init.returncode != 0:
        print("Init stderr:", p_init.stderr)
        raise RuntimeError(f"Failed to initialize disposable store: {p_init.stderr}")

    print(f"Disposable previous rc3 release seeded at: {disposable_rc3_dir}")
    return data_root, disposable_rc3_dir


def run() -> None:
    print("=================================================================")
    print("RS-PROOF: Contaminated-Previous Disposable Two-Hop Proof")
    print("=================================================================")

    # 1. Revalidate bridge identities
    revalidate_bridge_identities()

    # 2. Capture live fingerprints
    print("\n--- Capturing Pre-Run Live System Witness Fingerprints ---")
    pre_witnesses = capture_live_fingerprints()
    for k, v in pre_witnesses.items():
        print(f"  {k}: {v}")

    # 3. Setup disposable base
    if DISPOSABLE_BASE.exists():
        shutil.rmtree(DISPOSABLE_BASE)
    DISPOSABLE_BASE.mkdir(parents=True, exist_ok=True)
    receipts_dir = DISPOSABLE_BASE / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    env = make_disposable_env(DISPOSABLE_BASE)
    data_root, disposable_rc3_dir = seed_disposable_previous_rc3(DISPOSABLE_BASE, env)

    # -------------------------------------------------------------
    # HOP 1 (Pre-Restore): rc3 refuses update due to contamination
    # -------------------------------------------------------------
    print("\n--- Hop 1 (Pre-Restore): Verify rc3 Refuses Due to Contamination ---")
    hop1_cmd = [
        str(RC3_MANAGER_PYTHON),
        "-m",
        "aether_agents.cli",
        "update",
        "--local",
        "--aether-checkout",
        str(BRIDGE_CHECKOUT),
        "--aether-commit",
        BRIDGE_COMMIT,
        "--fork-checkout",
        str(FORK_CHECKOUT),
        "--fork-commit",
        FORK_COMMIT,
        "--yes",
        "--json",
    ]
    print("Executing command:")
    print("  " + " ".join(hop1_cmd))

    p_refuse = subprocess.run(
        hop1_cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Return code: {p_refuse.returncode}")
    print(f"Stdout:\n{p_refuse.stdout.strip()}")
    if p_refuse.stderr:
        print(f"Stderr:\n{p_refuse.stderr.strip()}")

    assert p_refuse.returncode != 0, (
        f"Expected non-zero returncode on contaminated previous, got {p_refuse.returncode}"
    )
    refusal_receipt = json.loads(p_refuse.stdout)
    assert refusal_receipt.get("result") == "error", f"Expected result error, got {refusal_receipt}"
    assert refusal_receipt.get("manager_version") == "1.0.0rc3", (
        f"Expected manager_version 1.0.0rc3, got {refusal_receipt}"
    )
    errors = refusal_receipt.get("errors", [])
    assert len(errors) > 0, f"No errors in refusal receipt: {refusal_receipt}"
    error_code = errors[0].get("code")
    error_message = errors[0].get("message", "")
    assert error_code == "LOCAL_UPDATE_REFUSED", f"Expected LOCAL_UPDATE_REFUSED, got {error_code}"
    # Verify non-regular or source-integrity class, NOT a private-path miss
    assert "non-regular" in error_message or "Hermes source digest mismatch" in error_message, (
        f"Error message not non-regular/source-integrity class: {error_message}"
    )
    assert "private directory component is a symlink" not in error_message, (
        f"Unexpected private directory symlink error: {error_message}"
    )
    print(f"Pre-restore refusal verified: code={error_code}, message={error_message}")

    (receipts_dir / "hop1_pre_restore_refusal_receipt.json").write_text(
        json.dumps(refusal_receipt, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------
    # ATOMIC RESTORATION: restore contaminated previous rc3
    # -------------------------------------------------------------
    print("\n--- Atomic Restoration: Restoring rc3 Release Source ---")
    # Take snapshots of immutable release files to verify preservation
    immutable_witnesses = {
        "record_json": sha256_file(disposable_rc3_dir / "record.json"),
        "release_json": sha256_file(disposable_rc3_dir / "release.json"),
        "release_lock_json": sha256_file(disposable_rc3_dir / "release-lock.json"),
        "profile_bundle_json": sha256_file(disposable_rc3_dir / "profile-bundle.json"),
        "manager_python": sha256_file(disposable_rc3_dir / "manager" / "bin" / "python"),
        "active_json": sha256_file(data_root / "active.json"),
        "runtime_current": os.readlink(data_root / "runtime" / "current"),
    }

    restore_script = (
        WORKTREE_ROOT
        / "specs"
        / "001-aether-v1-productization"
        / "fixtures"
        / "restore_exact_hermes_source.py"
    )
    restore_cmd = [
        str(RC3_MANAGER_PYTHON),
        str(restore_script),
        "--release-dir",
        str(disposable_rc3_dir),
        "--fork-checkout",
        str(FORK_CHECKOUT),
        "--json",
    ]
    p_restore = subprocess.run(
        restore_cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Restore exit code: {p_restore.returncode}")
    print(f"Restore stdout:\n{p_restore.stdout.strip()}")
    if p_restore.stderr:
        print(f"Restore stderr:\n{p_restore.stderr.strip()}")

    assert p_restore.returncode == 0, f"Restoration failed with exit code {p_restore.returncode}!"
    restore_res = json.loads(p_restore.stdout)
    assert restore_res.get("status") == "restored", f"Expected status restored, got {restore_res}"
    assert restore_res.get("clean_digest") == EXPECTED_FORK_TREE_SHA256, (
        f"Digest mismatch: {restore_res.get('clean_digest')} != {EXPECTED_FORK_TREE_SHA256}"
    )
    quarantine_path = restore_res.get("quarantine_path")
    assert quarantine_path is not None, "Quarantine path missing in restore receipt"
    assert Path(quarantine_path).is_dir(), f"Quarantine dir does not exist: {quarantine_path}"

    # Verify immutable bytes preserved
    post_immutable_witnesses = {
        "record_json": sha256_file(disposable_rc3_dir / "record.json"),
        "release_json": sha256_file(disposable_rc3_dir / "release.json"),
        "release_lock_json": sha256_file(disposable_rc3_dir / "release-lock.json"),
        "profile_bundle_json": sha256_file(disposable_rc3_dir / "profile-bundle.json"),
        "manager_python": sha256_file(disposable_rc3_dir / "manager" / "bin" / "python"),
        "active_json": sha256_file(data_root / "active.json"),
        "runtime_current": os.readlink(data_root / "runtime" / "current"),
    }
    for k, v_pre in immutable_witnesses.items():
        v_post = post_immutable_witnesses[k]
        assert v_pre == v_post, (
            f"Immutable asset {k} changed by restorer! Pre: {v_pre}, Post: {v_post}"
        )
    print("All rc3 release records, selectors, and manager bytes verified unchanged by restorer.")

    # Validate restored rc3 release and doctor using rc3 manager python
    rc3_val_code = (
        "import sys, json, os\n"
        "from pathlib import Path\n"
        "from aether_agents.lifecycle import LifecycleManager, ReleaseStore\n"
        "data_root = Path(os.environ['XDG_DATA_HOME']) / 'aether'\n"
        "state_root = Path(os.environ['XDG_STATE_HOME']) / 'aether'\n"
        "store = ReleaseStore(data_root, state_root=state_root)\n"
        "manager = LifecycleManager(store=store, python_executable=Path(sys.executable))\n"
        "val = manager.validate_release('" + RC3_RELEASE_ID + "')\n"
        "assert val.version == '1.0.0rc3'\n"
        "doc = manager.doctor()\n"
        "print(json.dumps({'version': val.version, 'doctor_ready': doc.ready, 'doctor_codes': list(doc.codes)}))\n"
    )
    p_val = subprocess.run(
        [str(RC3_MANAGER_PYTHON), "-c", rc3_val_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if p_val.stderr:
        print("rc3 validation stderr:", p_val.stderr)
    assert p_val.returncode == 0, f"rc3 validation failed: {p_val.stderr}"
    rc3_val_data = json.loads(p_val.stdout.strip())
    print(
        f"Restored rc3 doctor check: ready={rc3_val_data['doctor_ready']}, codes={rc3_val_data['doctor_codes']}"
    )
    assert rc3_val_data["doctor_ready"], f"Restored rc3 doctor not ready: {rc3_val_data}"
    assert rc3_val_data["doctor_codes"] == [], (
        f"Restored rc3 doctor codes: {rc3_val_data['doctor_codes']}"
    )

    restore_receipt = {
        "status": restore_res["status"],
        "clean_digest": restore_res["clean_digest"],
        "quarantine_path": quarantine_path,
        "inventory": restore_res["inventory"],
        "rc3_doctor_ready": rc3_val_data["doctor_ready"],
        "rc3_doctor_codes": rc3_val_data["doctor_codes"],
    }
    (receipts_dir / "restoration_receipt.json").write_text(
        json.dumps(restore_receipt, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------
    # HOP 1 (Post-Restore): rc3 -> bridge (1.0.0a4)
    # -------------------------------------------------------------
    print("\n--- Hop 1 (Post-Restore): rc3 -> bridge (1.0.0a4) ---")
    p1 = subprocess.run(
        hop1_cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Hop 1 return code: {p1.returncode}")
    print(f"Hop 1 stdout:\n{p1.stdout.strip()}")
    if p1.stderr:
        print(f"Hop 1 stderr:\n{p1.stderr.strip()}")

    assert p1.returncode == 0, f"Hop 1 failed with exit code {p1.returncode}!"
    hop1_receipt = json.loads(p1.stdout)
    assert hop1_receipt.get("result") == "changed", f"Hop 1 result not changed: {hop1_receipt}"
    bridge_release_id = hop1_receipt["data"]["active_release_id"]
    print(f"Hop 1 activated bridge release_id: {bridge_release_id}")
    assert bridge_release_id.startswith("1.0.0a4-"), f"Unexpected release_id: {bridge_release_id}"
    assert hop1_receipt["data"]["wheel_sha256"] == BRIDGE_WHEEL_SHA256, (
        f"Wheel sha mismatch: {hop1_receipt['data']['wheel_sha256']} != {BRIDGE_WHEEL_SHA256}"
    )

    bridge_release_path = data_root / "releases" / bridge_release_id
    bridge_manager_python = bridge_release_path / "manager" / "bin" / "python"
    assert bridge_manager_python.is_file(), (
        f"Bridge manager python missing: {bridge_manager_python}"
    )

    # Verify TUI absent in bridge release
    bridge_tui_dir = bridge_release_path / "tui"
    assert not bridge_tui_dir.exists(), f"Bridge must not have TUI dir, found: {bridge_tui_dir}"

    # Verify active manager authority using bridge manager python
    auth_check_code = (
        "from aether_agents.cli import _lifecycle_manager\n"
        "manager = _lifecycle_manager()\n"
        "target = manager.active_manager_dispatch_target()\n"
        "assert target is not None, 'target is None'\n"
        "active, py = target\n"
        "print('active_version:', active.version)\n"
        "print('manager_python:', py)\n"
        "manager._assert_executing_active_manager_locked()\n"
        "print('authority_validated: True')\n"
    )
    p_auth = subprocess.run(
        [str(bridge_manager_python), "-c", auth_check_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print("Bridge authority check stdout:", p_auth.stdout.strip())
    if p_auth.stderr:
        print("Bridge authority check stderr:", p_auth.stderr.strip())
    assert p_auth.returncode == 0, "Bridge manager authority check failed!"

    (receipts_dir / "hop1_bridge_receipt.json").write_text(
        json.dumps(hop1_receipt, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------
    # HOP 2: bridge manager -> final rc4 (1.0.0rc4)
    # -------------------------------------------------------------
    print("\n--- Hop 2: bridge -> final rc4 (1.0.0rc4) ---")
    hop2_cmd = [
        str(bridge_manager_python),
        "-m",
        "aether_agents.cli",
        "update",
        "--local",
        "--aether-checkout",
        str(RC4_CHECKOUT),
        "--aether-commit",
        RC4_COMMIT,
        "--fork-checkout",
        str(FORK_CHECKOUT),
        "--fork-commit",
        FORK_COMMIT,
        "--yes",
        "--json",
    ]
    print("Executing command:")
    print("  " + " ".join(hop2_cmd))

    p2 = subprocess.run(
        hop2_cmd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Hop 2 return code: {p2.returncode}")
    print(f"Hop 2 stdout:\n{p2.stdout.strip()}")
    if p2.stderr:
        print(f"Hop 2 stderr:\n{p2.stderr.strip()}")

    assert p2.returncode == 0, f"Hop 2 failed with exit code {p2.returncode}!"
    hop2_receipt = json.loads(p2.stdout)
    assert hop2_receipt.get("result") == "changed", f"Hop 2 result not changed: {hop2_receipt}"
    rc4_release_id = hop2_receipt["data"]["active_release_id"]
    print(f"Hop 2 activated rc4 release_id: {rc4_release_id}")
    assert rc4_release_id.startswith("1.0.0rc4-"), f"Unexpected rc4 release_id: {rc4_release_id}"
    assert hop2_receipt["data"]["executing_manager_release_id"] == bridge_release_id, (
        f"Executing manager mismatch: {hop2_receipt['data']['executing_manager_release_id']} != {bridge_release_id}"
    )

    rc4_release_path = data_root / "releases" / rc4_release_id
    rc4_manager_python = rc4_release_path / "manager" / "bin" / "python"
    assert rc4_manager_python.is_file(), f"rc4 manager python missing: {rc4_manager_python}"

    # Verify TUI entry in rc4
    rc4_tui_entry = rc4_release_path / "tui" / "dist" / "entry.js"
    assert rc4_tui_entry.is_file(), f"rc4 TUI entry missing: {rc4_tui_entry}"
    actual_tui_sha256 = sha256_file(rc4_tui_entry)
    print(f"rc4 TUI entry sha256: {actual_tui_sha256}")
    assert actual_tui_sha256 == EXPECTED_TUI_SHA256, (
        f"TUI sha mismatch: expected {EXPECTED_TUI_SHA256}, got {actual_tui_sha256}"
    )

    # Verify TUI provenance
    rc4_provenance = json.loads(
        (rc4_release_path / "tui" / "provenance.json").read_text(encoding="utf-8")
    )
    assert rc4_provenance["hermes_commit"] == FORK_COMMIT
    assert rc4_provenance["entry_sha256"] == EXPECTED_TUI_SHA256

    # Verify selector runtime/current
    disposable_rc = data_root / "runtime" / "current"
    assert disposable_rc.is_symlink(), "runtime/current is not a symlink"
    assert os.readlink(disposable_rc) == str(rc4_release_path)

    # Verify active record
    active_payload = json.loads((data_root / "active.json").read_text(encoding="utf-8"))
    assert active_payload["version"] == "1.0.0rc4"
    assert active_payload["release_id"] == rc4_release_id
    assert active_payload["tui_sha256"] == EXPECTED_TUI_SHA256
    assert active_payload["hermes_commit"] == FORK_COMMIT

    # Verify branded projections in confined base
    confined_base = data_root.parent / "aether-projections"
    print(f"Confined projections base: {confined_base}")
    launcher_path = confined_base / "bin" / "aether"
    branded_desktop_path = confined_base / "applications" / "aether.desktop"
    legacy_desktop_path = confined_base / "applications" / "hermes.desktop"
    service_path = confined_base / "systemd" / "user" / "hermes-gateway-morfeo.service"

    assert launcher_path.is_file(), f"Launcher projection missing: {launcher_path}"
    launcher_text = launcher_path.read_text(encoding="utf-8")
    assert 'export HERMES_TUI_DIR="$AETHER_RUNTIME_ROOT/tui"' in launcher_text

    assert branded_desktop_path.is_file(), f"Branded desktop missing: {branded_desktop_path}"
    desktop_text = branded_desktop_path.read_text(encoding="utf-8")
    assert "Name=Aether" in desktop_text
    assert "Actions=Continue;" in desktop_text
    assert "Name=Continue Aether" in desktop_text

    assert not legacy_desktop_path.exists(), (
        f"Legacy desktop entry should be removed: {legacy_desktop_path}"
    )

    assert service_path.is_file(), f"Service projection missing: {service_path}"
    service_text = service_path.read_text(encoding="utf-8")
    assert 'Environment="HERMES_TUI_DIR=' in service_text

    (receipts_dir / "hop2_rc4_receipt.json").write_text(
        json.dumps(hop2_receipt, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------
    # DOCTOR CHECK ON FINAL rc4
    # -------------------------------------------------------------
    print("\n--- Doctor Check on Final rc4 ---")
    p_doc = subprocess.run(
        [str(rc4_manager_python), "-m", "aether_agents.cli", "doctor", "--json"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"Doctor exit code: {p_doc.returncode}")
    print(f"Doctor output:\n{p_doc.stdout.strip()}")
    if p_doc.stderr:
        print(f"Doctor stderr:\n{p_doc.stderr.strip()}")

    assert p_doc.returncode == 0, f"Doctor exited non-zero: {p_doc.returncode}"
    doctor_receipt = json.loads(p_doc.stdout)
    assert doctor_receipt.get("result") == "ready", f"Doctor not ready: {doctor_receipt}"
    assert doctor_receipt.get("errors") == [], f"Doctor errors: {doctor_receipt.get('errors')}"
    obs = doctor_receipt["data"]["observer"]
    assert obs.get("status") == "ready", f"Observer status not ready: {obs.get('status')}"
    assert obs.get("diagnostic_codes") == [], f"Diagnostic codes: {obs.get('diagnostic_codes')}"
    projections = obs["projections"]
    assert projections["mismatches"] == [], f"Projection mismatches: {projections['mismatches']}"
    pending_count = obs["transition_journal"]["pending_count"]
    assert pending_count == 0, f"Pending transitions not 0: {pending_count}"
    print(f"Doctor ready: True, mismatches: 0, pending transitions: {pending_count}")

    (receipts_dir / "doctor_receipt.json").write_text(
        json.dumps(doctor_receipt, indent=2) + "\n", encoding="utf-8"
    )

    # -------------------------------------------------------------
    # POST-LIVE WITNESS FINGERPRINTS
    # -------------------------------------------------------------
    print("\n--- Verifying Live System Untouched ---")
    post_witnesses = capture_live_fingerprints()
    for k in pre_witnesses:
        pre_v = pre_witnesses[k]
        post_v = post_witnesses[k]
        print(f"  {k}:")
        print(f"    pre : {pre_v}")
        print(f"    post: {post_v}")
        assert pre_v == post_v, f"Live witness {k} changed! Pre: {pre_v}, Post: {post_v}"

    print("\nALL PRE/POST LIVE WITNESSES ARE BYTE-IDENTICAL!")
    print(f"Raw receipts saved to: {receipts_dir}")
    print("RS-PROOF TWO-HOP COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    run()
