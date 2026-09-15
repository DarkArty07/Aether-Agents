"""Release bundle tooling: identity, refusals, scans and workflow agreement."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import types
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
TOOL_PATH = ROOT / "scripts" / "release_bundle.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release.yml"
AETHER_REMOTE = "https://github.com/DarkArty07/Aether-Agents.git"
FORK_REMOTE = "https://github.com/DarkArty07/aether-hermes.git"
_ABSENT_COMMIT = "0" * 40


def _load_tool() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("release_bundle_under_test", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool() -> types.ModuleType:
    return _load_tool()


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _repository(root: Path, *, remote: str, branch: str = "main") -> tuple[Path, str]:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--quiet", "--initial-branch", branch)
    _git(root, "config", "user.email", "release-tool-test@example.invalid")
    _git(root, "config", "user.name", "Release Tool Test")
    (root / "README.md").write_text("portable\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "--quiet", "-m", "base")
    if remote:
        _git(root, "remote", "add", "origin", remote)
    commit = _git(root, "rev-parse", "HEAD").strip()
    return root, commit


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- identity


def test_release_identity_maps_the_rc_and_stable_forms(tool: types.ModuleType) -> None:
    rc = tool.release_identity("1.0.0rc1")
    assert rc == {
        "package_version": "1.0.0rc1",
        "semver": "1.0.0-rc.1",
        "tag": "v1.0.0-rc.1",
        "prerelease": True,
    }
    stable = tool.release_identity("0.24.0")
    assert stable["tag"] == "v0.24.0"
    assert stable["prerelease"] is False
    assert tool.release_identity("1.0.0rc1", "v1.0.0-rc.1") == rc


def test_release_identity_refuses_unsupported_versions_and_foreign_tags(
    tool: types.ModuleType,
) -> None:
    with pytest.raises(tool.BundleError) as unsupported:
        tool.release_identity("1.0.0-rc.1")
    assert unsupported.value.code == "unsupported-version"
    with pytest.raises(tool.BundleError) as mismatch:
        tool.release_identity("1.0.0rc1", "v1.0.0")
    assert mismatch.value.code == "identity-mismatch"


def test_version_file_carries_the_objective_release_identity(tool: types.ModuleType) -> None:
    """This unit owns VERSION; the objective fixes the RC identity it must derive."""

    package_version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
    identity = tool.release_identity(package_version)
    assert identity["package_version"] == "1.0.0rc1"
    assert identity["tag"] == "v1.0.0-rc.1"
    assert identity["prerelease"] is True


# --------------------------------------------------------------------------- workflow


def _workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _step_script(step_name: str) -> str:
    lines = WORKFLOW_PATH.read_text(encoding="utf-8").splitlines()
    marker = f"      - name: {step_name}"
    start = lines.index(marker)
    run_start = next(
        index for index in range(start, len(lines)) if lines[index] == "        run: |"
    )
    script_lines = []
    for line in lines[run_start + 1 :]:
        if line.startswith("      - "):
            break
        if line.startswith("          "):
            script_lines.append(line[10:])
        elif not line.strip():
            script_lines.append("")
        else:
            break
    return "\n".join(script_lines) + "\n"


def test_workflow_tag_mapping_agrees_with_the_release_identity(tool: types.ModuleType) -> None:
    script = _step_script("Validate release tag")
    stable_tag = re.search(
        r"\^v\(0\|\[1-9\]\[0-9\]\*\)\\\.\(0\|\[1-9\]\[0-9\]\*\)\\\.\(0\|\[1-9\]\[0-9\]\*\)\$",
        script,
    )
    rc_tag = re.search(r"rc\\\.\(\[1-9\]\[0-9\]\*\)\$", script)
    assert stable_tag is not None, "stable tag form must stay validated"
    assert rc_tag is not None, "RC tag form must stay validated"
    assert "printf 'version=%s" in script
    assert "printf 'prerelease=%s" in script
    assert '"$(<VERSION)" == "$release_version"' in script

    identity = tool.release_identity("1.0.0rc1")
    assert identity["tag"] == "v1.0.0-rc.1"
    assert identity["package_version"] == "1.0.0rc1"
    stable = tool.release_identity("1.0.0")
    assert stable["tag"] == "v1.0.0"
    assert stable["package_version"] == "1.0.0"


def test_workflow_keeps_identity_validation_and_attaches_the_qualified_bytes(tool) -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "refs/tags/$RELEASE_TAG^{commit}" in workflow
    assert "refs/remotes/origin/main" in workflow
    assert "sha256sum --check --strict SHA256SUMS" in workflow
    assert "scripts/release_bundle.py build" in workflow
    assert '--expect-package-version "$RELEASE_VERSION"' in workflow
    assert "if-no-files-found: error" in workflow
    assert "FORK_REPOSITORY: https://github.com/DarkArty07/aether-hermes" in workflow
    # exactly one release path: no second create/edit invocation set
    assert workflow.count("gh release view") == 1
    assert workflow.count("gh release create") == 1
    assert workflow.count("gh release edit") == 1


def test_workflow_forbidden_effects_stay_absent() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "packa" + "ges:",
        "id-" + "token:",
        "gh release upl" + "oad",
        "gh repo " + "edit",
        "docker " + "push",
        "uv " + "publish",
    ):
        assert forbidden not in workflow, forbidden


def test_release_step_still_reconciles_identity_without_a_bundle() -> None:
    """The shipped step script must keep working when no bundle directory is provided."""

    script = _step_script("Create or reconcile GitHub Release")
    assert 'bundle_dir="${RELEASE_BUNDLE_DIR:-}"' in script
    assert "$prerelease_arg" in script


# ------------------------------------------------------------------------ checkouts


def test_checkout_evidence_refuses_dirty_wrong_revision_and_foreign_repository(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    clean, commit = _repository(tmp_path / "clean", remote=AETHER_REMOTE)
    evidence = tool.checkout_evidence(
        clean, commit, kind="aether", repository=tool.AETHER_REPOSITORY
    )
    assert evidence["commit"] == commit
    assert evidence["remotes"] == ["https://github.com/darkarty07/aether-agents"]

    (clean / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(tool.BundleError) as dirty:
        tool.checkout_evidence(clean, commit, kind="aether", repository=tool.AETHER_REPOSITORY)
    assert dirty.value.code == "dirty-checkout"

    (clean / "uncommitted.txt").unlink()
    with pytest.raises(tool.BundleError) as wrong_revision:
        tool.checkout_evidence(clean, "a" * 40, kind="aether", repository=tool.AETHER_REPOSITORY)
    assert wrong_revision.value.code == "revision-mismatch"

    with pytest.raises(tool.BundleError) as short_revision:
        tool.checkout_evidence(clean, "abc123", kind="aether", repository=tool.AETHER_REPOSITORY)
    assert short_revision.value.code == "unknown-revision"

    with pytest.raises(tool.BundleError) as foreign:
        tool.checkout_evidence(clean, commit, kind="aether", repository=FORK_REMOTE)
    assert foreign.value.code == "repository-identity"


def test_fork_branch_membership_refuses_a_diverged_commit(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    fork, commit = _repository(tmp_path / "fork", remote=FORK_REMOTE, branch="aether-main")
    membership = tool.verify_branch_membership(fork, commit, "aether-main")
    assert membership["reachable"] is True
    assert membership["proven_by"] == "refs/heads/aether-main"

    _git(fork, "checkout", "--quiet", "-b", "side")
    (fork / "side.txt").write_text("side\n", encoding="utf-8")
    _git(fork, "add", "side.txt")
    _git(fork, "commit", "--quiet", "-m", "side")
    divergent = _git(fork, "rev-parse", "HEAD").strip()

    with pytest.raises(tool.BundleError) as divergence:
        tool.verify_branch_membership(fork, divergent, "aether-main")
    assert divergence.value.code == "branch-divergence"
    with pytest.raises(tool.BundleError) as missing:
        tool.verify_branch_membership(fork, commit, "release")
    assert missing.value.code == "branch-unavailable"


# -------------------------------------------------------------------------- archives


def test_archive_is_deterministic_and_rejects_unsafe_members(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    repo, commit = _repository(tmp_path / "repo", remote=FORK_REMOTE)
    first = tool._git_archive_bytes(repo, commit, "prefix")
    second = tool._git_archive_bytes(repo, commit, "prefix")
    assert first == second
    members = tool._extract_trusted_archive(first, tmp_path / "extract")
    assert [member["name"] for member in members] == ["prefix/README.md"]

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        payload = b"escape\n"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(tool.BundleError) as unsafe:
        tool._extract_trusted_archive(buffer.getvalue(), tmp_path / "unsafe")
    assert unsafe.value.code == "archive-unsafe"


# ----------------------------------------------------------------------------- scans


def test_secret_scan_refuses_credential_material(tool: types.ModuleType) -> None:
    material = "-----BEGIN RSA " + "PRIVATE KEY-----\n" + "A" * 96 + "\n"
    assert tool._secret_hits_bytes("member.py", material.encode(), ("private-key-material",))
    assert tool._secret_hits_bytes("member.py", b"portable\n", ("private-key-material",)) == []
    token = "gh" + "p_" + "b" * 36
    assert tool._secret_hits_bytes("member.py", token.encode(), ("github-token",))


def test_private_path_scan_refuses_aether_authored_bytes(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    lifecycle = tool.load_product(ROOT)
    private = "/" + "home" + "/operator/" + "Desk" + "top/agentes/product\n"
    artifact = tmp_path / "candidate.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        payload = private.encode()
        info = tarfile.TarInfo("candidate/readme.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    artifact.write_bytes(buffer.getvalue())

    with pytest.raises(tool.BundleError) as refusal:
        tool.scan_bundle(
            lifecycle=lifecycle,
            aether_checkout=ROOT,
            aether_artifacts=[artifact],
        )
    assert refusal.value.code == "private-path-scan"


def test_scan_bundle_reviews_upstream_fork_bytes_without_vetoing(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    lifecycle = tool.load_product(ROOT)
    artifact = tmp_path / ("aether-hermes-source-" + "a" * 40 + ".tar.gz")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        payload = ("/" + "home" + "/user/project\n").encode()
        info = tarfile.TarInfo("upstream/example.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    artifact.write_bytes(buffer.getvalue())

    report = tool.scan_bundle(
        lifecycle=lifecycle,
        aether_checkout=ROOT,
        aether_artifacts=[],
        fork_artifacts=[artifact],
        extra_files=[],
    )
    fork_scan = report["private_paths"]["maintained_fork"]
    assert fork_scan["result"] == "reviewed"
    example = "/" + "home" + "/user/"
    assert example in fork_scan["distinct_matches"]
    assert report["secrets"]["strict_result"] == "clean"


# ---------------------------------------------------------------------------- verify


def _bundle(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    members = {"a.bin": b"alpha\n", "b.bin": b"beta\n"}
    for name, payload in members.items():
        (root / name).write_bytes(payload)
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(payload)}  {name}\n" for name, payload in sorted(members.items())),
        encoding="ascii",
    )
    return root


def test_verify_members_refuses_a_tampered_digest(tool: types.ModuleType, tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle")
    expected, verified = tool.verify_members(bundle)
    assert sorted(expected) == ["a.bin", "b.bin"]
    assert verified["a.bin"]["bytes"] == 6

    (bundle / "a.bin").write_bytes(b"ALPHA\n")
    with pytest.raises(tool.BundleError) as tampered:
        tool.verify_members(bundle)
    assert tampered.value.code == "digest-mismatch"


def test_verify_members_refuses_member_drift(tool: types.ModuleType, tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "bundle")
    (bundle / "b.bin").unlink()
    with pytest.raises(tool.BundleError) as missing:
        tool.verify_members(bundle)
    assert missing.value.code == "member-drift"

    bundle = _bundle(tmp_path / "other")
    (bundle / "extra.bin").write_bytes(b"extra\n")
    with pytest.raises(tool.BundleError) as extra:
        tool.verify_members(bundle)
    assert extra.value.code == "member-drift"


# ------------------------------------------------------------------------------ lock


def test_profile_bundle_digest_matches_the_product_materialization(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """The tool's lock digest must be the digest the coordinator materializes."""

    lifecycle = tool.load_product(ROOT)
    expected = tool.profile_bundle_sha256(lifecycle)
    store = lifecycle.ReleaseStore(tmp_path / "data", state_root=tmp_path / "state")
    manager = lifecycle.LifecycleManager(store=store, python_executable=Path(sys.executable))
    stage = tmp_path / "stage"
    stage.mkdir()
    assert manager._materialize_profile_bundle(stage) == expected


def _lock(tool: types.ModuleType, lifecycle, tmp_path: Path) -> dict:
    payload = b"wheel-bytes"
    wheel = {
        "distribution": "aether-agents",
        "version": "1.0.0rc1",
        "python_requires": ">=3.11,<3.14",
        "observer": {"plugin_name": "aether-contract-observer"},
        "sha256": _sha256(payload),
        "observer_requirements_sha256": "b" * 64,
        "observation_compatibility": {"event_write_version": "aether.observation.event.v1"},
    }
    fork = {
        "commit": "c" * 40,
        "version": "0.20.1",
        "tag": "v2026.8.18",
        "python_requires": ">=3.11,<3.14",
        "source_tree_sha256": "d" * 64,
    }
    return tool.build_release_lock(
        lifecycle=lifecycle,
        identity=tool.release_identity("1.0.0rc1"),
        aether_commit="e" * 40,
        wheel=wheel,
        fork=fork,
        fork_archive_name="aether-hermes-source-" + "c" * 40 + ".tar.gz",
        fork_archive_sha256="f" * 64,
    )


def test_release_lock_binds_the_pinned_maintained_fork_identity(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    lifecycle = tool.load_product(ROOT)
    lock = _lock(tool, lifecycle, tmp_path)
    assert lock["schema_version"] == tool.RELEASE_LOCK_SCHEMA_VERSION == 4
    assert lock["hermes"]["source_mode"] == "maintained_fork"
    assert lock["hermes"]["repository"] == "https://github.com/DarkArty07/aether-hermes"
    assert lock["aether"]["version"] == "1.0.0-rc.1"
    assert lock["aether"]["package_version"] == "1.0.0rc1"
    assert lock["aether"]["git_tag"] == "v1.0.0-rc.1"
    assert lock["profile_bundle"]["version"] == "2"
    assert lock["profile_bundle"]["roles"] == ["morfeo", "supervisor", "implementer"]
    assert lock["hermes"]["artifacts"][0]["url"].endswith(
        "/releases/download/v1.0.0-rc.1/" + lock["hermes"]["artifacts"][0]["filename"]
    )

    with pytest.raises(tool.BundleError) as drift:
        tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert drift.value.code == "lock-schema-drift"

    recorded = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=True)
    assert recorded["schema_validation"] == "not_applicable"
    assert recorded["repository_schema_version"] == 3
    assert recorded["pinned_identity"] == [
        "schema_version=4",
        "hermes.source_mode=maintained_fork",
        "hermes.repository=https://github.com/DarkArty07/aether-hermes",
    ]


def test_lock_validation_applies_the_repository_schema_when_it_declares_four(
    tool: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle = tool.load_product(ROOT)
    lock = _lock(tool, lifecycle, tmp_path)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"schema_version": {"const": 4}},
        "required": ["schema_version", "aether", "hermes", "profile_bundle"],
    }
    schema_path = tmp_path / "release-lock.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    monkeypatch.setattr(tool, "_lock_schema_path", lambda checkout: schema_path)

    applied = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert applied["schema_validation"] == "applied"
    assert applied["repository_schema_version"] == 4

    broken = json.loads(json.dumps(lock))
    broken["hermes"]["source_mode"] = "upstream"
    with pytest.raises(tool.BundleError) as refusal:
        tool.validate_lock(broken, aether_checkout=ROOT, allow_schema_drift=False)
    assert refusal.value.code == "lock-identity"


# ------------------------------------------------------------------------------- cli


def test_main_refuses_a_dirty_aether_checkout(tool: types.ModuleType, tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path / "aether", remote=AETHER_REMOTE)
    (repository / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    exit_code = tool.main(
        [
            "build",
            "--aether-checkout",
            str(repository),
            "--aether-commit",
            commit,
            "--fork-checkout",
            str(repository),
            "--fork-commit",
            _ABSENT_COMMIT,
            "--out",
            str(tmp_path / "out"),
            "--pre-integration",
        ]
    )
    assert exit_code == 1


def test_main_reports_a_missing_bundle(tool: types.ModuleType, tmp_path: Path) -> None:
    assert tool.main(["verify", "--bundle", str(tmp_path / "absent")]) == 1
    assert tool.main(["build", "--aether-checkout", str(tmp_path)]) == 2
