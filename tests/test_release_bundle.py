"""Release bundle tooling: identity, refusals, scans and workflow agreement."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
TOOL_PATH = ROOT / "scripts" / "release_bundle.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release.yml"
AETHER_REMOTE = "https://github.com/DarkArty07/Aether-Agents.git"
FORK_REMOTE = "https://github.com/DarkArty07/aether-hermes.git"
FORK_COMMIT = "aed6591a69f453a1867b73628603e7b53ba40ffc"
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


@pytest.fixture(scope="module", autouse=True)
def _restore_product_module_cache() -> Iterator[None]:
    """Leave the ``aether_agents`` module cache as this module found it.

    ``load_product`` imports the product from the checkout under qualification and purges
    every cached ``aether_agents`` module to do it, which is deliberate: the release tool
    must never inspect a stale copy of the code it is qualifying.  Test modules collected
    after this one hold module-scope references to the previous objects, and the product's
    own function-local imports would otherwise start resolving to the freshly imported
    copies, so the cache is put back once this module's tests have finished.
    """

    saved = {
        name: module
        for name, module in sys.modules.items()
        if name.split(".")[0] == "aether_agents"
    }
    yield
    for name in [name for name in sys.modules if name.split(".")[0] == "aether_agents"]:
        del sys.modules[name]
    sys.modules.update(saved)


def _git(repo: Path, *arguments: str) -> str:
    """Run one fixture Git command with no ambient repository binding inherited."""

    completed = subprocess.run(
        ("git", *arguments),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    )
    return completed.stdout


def _this_checkout_git_entry() -> Path:
    """This checkout's own ``.git`` entry, derived from the test file rather than the cwd."""

    entry = ROOT / ".git"
    assert entry.exists()
    return entry


def _this_checkout_object_directory() -> Path:
    """The object store this checkout's Git commands resolve, linked worktree included."""

    common = _git(ROOT, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return Path(common) / "objects"


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
    assert identity["package_version"] == "1.0.0rc10"
    assert identity["semver"] == "1.0.0-rc.10"
    assert identity["tag"] == "v1.0.0-rc.10"
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
    # the attach set is the tool's verified member list, and a reconcile re-verifies the
    # published bytes instead of passing files to `gh release edit`
    assert "scripts/release_bundle.py members --bundle" in workflow
    assert "verify-published-assets --bundle" in workflow
    # exactly one release path: no second create/edit invocation set
    assert workflow.count('gh release view "$RELEASE_TAG"') == 1
    assert workflow.count('gh release create "$RELEASE_TAG"') == 1
    assert workflow.count('gh release edit "$RELEASE_TAG"') == 1


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


# -------------------------------------------------- release step, exercised for real

_MEMBER_NAMES = (
    "aether_agents-1.0.0rc1-py3-none-any.whl",
    "aether_agents-1.0.0rc1.tar.gz",
    "aether-hermes-source-" + "5" * 40 + ".tar.gz",
    "aether-agents-1.0.0rc1-release-lock.json",
    "aether-agents-1.0.0rc1-provenance.json",
    "aether-agents-1.0.0rc1-package-members.json",
    "aether-agents-1.0.0rc1-clean-install.json",
)
_QUALIFIED_NAMES = tuple(sorted([*_MEMBER_NAMES, "SHA256SUMS"]))

_RELEASE_GH_STUB = '''#!__PYTHON__
"""Record every gh invocation; answer the two reads the release step performs."""

import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
with Path(os.environ["GH_STUB_LOG"]).open("a", encoding="utf-8") as stream:
    json.dump(args, stream)
    stream.write("\\n")
if args[:2] == ["release", "view"]:
    if os.environ.get("GH_STUB_RELEASE_EXISTS") != "1":
        print("release not found", file=sys.stderr)
        raise SystemExit(1)
    assets = json.loads(Path(os.environ["GH_STUB_ASSETS"]).read_text(encoding="utf-8"))
    if "--jq" in args:
        for asset in assets:
            print(f"{asset['name']}\\t{asset.get('digest') or ''}")
    else:
        print(json.dumps({"assets": assets}))
    raise SystemExit(0)
if args[:2] in (["release", "create"], ["release", "edit"]):
    raise SystemExit(0)
raise SystemExit(97)
'''


def _workflow_bundle(root: Path) -> Path:
    """A bundle directory shaped like the tool's own output (eight named members)."""

    root.mkdir(parents=True, exist_ok=True)
    payloads = {name: f"payload:{name}\n".encode() for name in _MEMBER_NAMES}
    for name, payload in payloads.items():
        (root / name).write_bytes(payload)
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(payload)}  {name}\n" for name, payload in sorted(payloads.items())),
        encoding="ascii",
    )
    return root


def _published_assets(bundle: Path) -> list[dict[str, str]]:
    return [
        {"name": name, "digest": "sha256:" + _sha256((bundle / name).read_bytes())}
        for name in _QUALIFIED_NAMES
    ]


def _run_release_step(
    root: Path,
    *,
    bundle: Path | None = None,
    release_exists: bool,
    assets: list[dict[str, str]] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    """Run the shipped step script with the real tool and a stub `gh` on PATH."""

    bin_path = root / "bin"
    bin_path.mkdir(parents=True, exist_ok=True)
    stub = bin_path / "gh"
    stub.write_text(_RELEASE_GH_STUB.replace("__PYTHON__", sys.executable), encoding="utf-8")
    stub.chmod(0o755)
    assets_path = root / "published-assets.json"
    assets_path.write_text(json.dumps(assets or []), encoding="utf-8")
    log_path = root / "gh-calls.jsonl"
    environment = dict(os.environ)
    environment.update(
        RELEASE_TAG="v1.0.0-rc.1",
        RELEASE_PRERELEASE="true",
        GH_STUB_LOG=str(log_path),
        GH_STUB_RELEASE_EXISTS="1" if release_exists else "0",
        GH_STUB_ASSETS=str(assets_path),
        PATH=f"{bin_path}{os.pathsep}{environment.get('PATH', '')}",
    )
    environment.pop("RELEASE_BUNDLE_DIR", None)
    if bundle is not None:
        environment["RELEASE_BUNDLE_DIR"] = str(bundle)
    completed = subprocess.run(
        ("bash",),
        cwd=ROOT,
        env=environment,
        input=_step_script("Create or reconcile GitHub Release"),
        text=True,
        capture_output=True,
        check=False,
    )
    calls = []
    if log_path.exists():
        calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    return completed, calls


def test_release_step_attaches_exactly_the_qualified_member_set(tmp_path: Path) -> None:
    bundle = _workflow_bundle(tmp_path / "bundle")
    completed, calls = _run_release_step(tmp_path, bundle=bundle, release_exists=False)

    assert completed.returncode == 0, completed.stderr
    assert [call[:2] for call in calls] == [["release", "view"], ["release", "create"]]
    create = calls[1]
    assert create[2] == "v1.0.0-rc.1"
    attached = [argument for argument in create[3:] if not argument.startswith("-")]
    assert attached == [str(bundle / name) for name in _QUALIFIED_NAMES]
    assert len(attached) == 8, attached
    for flag in ("--verify-tag", "--generate-notes", "--prerelease"):
        assert flag in create


def test_release_step_reconcile_verifies_the_release_and_passes_no_files(tmp_path: Path) -> None:
    bundle = _workflow_bundle(tmp_path / "bundle")
    completed, calls = _run_release_step(
        tmp_path, bundle=bundle, release_exists=True, assets=_published_assets(bundle)
    )

    assert completed.returncode == 0, completed.stderr
    assert "carries the qualified bytes" in completed.stdout
    assert [call[:2] for call in calls] == [["release", "view"], ["release", "edit"]]
    assert calls[1] == ["release", "edit", "v1.0.0-rc.1", "--prerelease"]


def test_release_step_reconcile_fails_closed_before_editing_anything(tmp_path: Path) -> None:
    bundle = _workflow_bundle(tmp_path / "bundle")
    tampered = _published_assets(bundle)
    for asset in tampered:
        if asset["name"] == _MEMBER_NAMES[1]:
            asset["digest"] = "sha256:" + "0" * 64

    drifted, drifted_calls = _run_release_step(
        tmp_path / "drifted", bundle=bundle, release_exists=True, assets=tampered
    )
    assert drifted.returncode != 0
    assert "published-asset-mismatch" in drifted.stderr
    assert _MEMBER_NAMES[1] in drifted.stderr
    assert all(call[:2] != ["release", "edit"] for call in drifted_calls)
    assert all(call[:2] != ["release", "create"] for call in drifted_calls)

    incomplete = [asset for asset in _published_assets(bundle) if asset["name"] != "SHA256SUMS"]
    missing, missing_calls = _run_release_step(
        tmp_path / "missing", bundle=bundle, release_exists=True, assets=incomplete
    )
    assert missing.returncode != 0
    assert "published-asset-drift" in missing.stderr
    assert "SHA256SUMS" in missing.stderr
    assert all(call[:2] != ["release", "edit"] for call in missing_calls)

    digestless = _published_assets(bundle)
    digestless[0]["digest"] = ""
    unverifiable, unverifiable_calls = _run_release_step(
        tmp_path / "digestless", bundle=bundle, release_exists=True, assets=digestless
    )
    assert unverifiable.returncode != 0
    assert "published-asset-unverifiable" in unverifiable.stderr
    assert all(call[:2] != ["release", "edit"] for call in unverifiable_calls)


def test_release_step_refuses_a_bundle_that_drifted_before_attaching(tmp_path: Path) -> None:
    bundle = _workflow_bundle(tmp_path / "bundle")
    (bundle / "unlisted.bin").write_bytes(b"unlisted\n")

    completed, calls = _run_release_step(tmp_path, bundle=bundle, release_exists=False)

    assert completed.returncode != 0
    assert "member-drift" in completed.stderr
    assert all(call[:2] != ["release", "create"] for call in calls)


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


def test_archive_bytes_ignore_an_ambient_repository_binding(
    tool: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fork that lacks the pin cannot archive this checkout through ambient ``GIT_*``.

    ``_isolated_environment`` inherits ``GIT_*`` from the process environment, so the
    archive step has to delete those names rather than merely omit them from an overlay.
    """

    fork, _ = _repository(tmp_path / "fork", remote=FORK_REMOTE)
    (fork / "pyproject.toml").write_text(
        '[project]\nname = "hermes-agent"\nversion = "0.20.4"\nrequires-python = ">=3.11,<3.14"\n',
        encoding="utf-8",
    )
    _git(fork, "add", "pyproject.toml")
    _git(fork, "commit", "--quiet", "-m", "fork metadata")
    fork_head = _git(fork, "rev-parse", "HEAD").strip()

    monkeypatch.setenv("GIT_DIR", str(_this_checkout_git_entry()))

    with pytest.raises(tool.BundleError) as refusal:
        tool._git_archive_bytes(fork, FORK_COMMIT, "hermes-agent")
    assert refusal.value.code == "archive-failed"

    assert tool._git(["rev-parse", "HEAD"], fork).strip() == fork_head

    monkeypatch.delenv("GIT_DIR")
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(_this_checkout_object_directory()))
    with pytest.raises(tool.BundleError) as object_refusal:
        tool._git_archive_bytes(fork, FORK_COMMIT, "hermes-agent")
    assert object_refusal.value.code == "archive-failed"

    metadata = tool._read_project_metadata(fork, fork_head)
    assert metadata["name"] == "hermes-agent"
    assert metadata["version"] == "0.20.4"

    data = tool._git_archive_bytes(fork, fork_head, "hermes-agent")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = [member.name for member in archive.getmembers()]
    assert "hermes-agent/README.md" in members
    assert not any(name.startswith("hermes-agent/ui-tui") for name in members)


# --------------------------------------------------------------- clean-install TUI stage


def _write_fork_tree(root: Path, marker: str) -> None:
    """Write a minimal maintained-fork-shaped tree whose ui-tui build emits ``marker``."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps({"name": "hermes-agent", "workspaces": ["ui-tui"]}) + "\n",
        encoding="utf-8",
    )
    tui = root / "ui-tui"
    tui.mkdir(parents=True, exist_ok=True)
    marker_in_shell = marker.replace("\\", "\\\\").replace('"', '\\"')
    (tui / "package.json").write_text(
        json.dumps(
            {
                "name": "ui-tui",
                "version": "1.0.0",
                "scripts": {
                    "build": (
                        "node -e \"const fs=require('fs'); "
                        "fs.mkdirSync('dist',{recursive:true}); "
                        f"fs.writeFileSync('dist/entry.js','{marker_in_shell}\\n')\""
                    )
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _fork_closure_archive(tmp_path: Path, marker: str) -> Path:
    """Write the single-root maintained-fork archive shape ``clean_install`` extracts."""

    tree = tmp_path / "archive-source" / "aether-hermes-source"
    _write_fork_tree(tree, marker)
    archive_path = tmp_path / "aether-hermes-source.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        archive.add(tree, arcname=tree.name)
    return archive_path


def test_fork_closure_extraction_refuses_a_multi_root_archive(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    archive_path = tmp_path / "two-roots.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        for name in ("first/README.md", "second/README.md"):
            payload = b"portable\n"
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(tool.BundleError) as layout:
        tool.materialize_fork_closure(archive_path, tmp_path / "closure")
    assert layout.value.code == "archive-layout"


def test_clean_install_stages_tui_from_the_extracted_fork_closure(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """The bundle TUI step builds the extracted exact-commit closure, not an enclosing repo."""

    lifecycle = tool.load_product(ROOT)
    enclosing = tmp_path / "enclosing-repository"
    _write_fork_tree(enclosing, "ENCLOSING-REPOSITORY-ENTRY")
    _git(enclosing, "init", "--quiet", "--initial-branch", "main")
    _git(enclosing, "config", "user.email", "release-tool-test@example.invalid")
    _git(enclosing, "config", "user.name", "Release Tool Test")
    _git(enclosing, "add", ".")
    _git(enclosing, "commit", "--quiet", "-m", "enclosing tree")
    enclosing_commit = _git(enclosing, "rev-parse", "HEAD").strip()

    archive_path = _fork_closure_archive(tmp_path, "BUNDLE-CLOSURE-ENTRY")
    closure_root = tool.materialize_fork_closure(
        archive_path, enclosing / "roots" / "hermes-source"
    )
    assert closure_root.is_dir()
    assert not (closure_root / ".git").exists()

    destination = tmp_path / "staged-tui"
    receipt = tool.stage_fork_tui(
        closure_root,
        commit=enclosing_commit,
        destination=destination,
        lifecycle=lifecycle,
    )

    entry = destination / "dist" / "entry.js"
    assert entry.read_text(encoding="utf-8") == "BUNDLE-CLOSURE-ENTRY\n"
    assert receipt["source"] == "materialized-tree"
    assert receipt["tui_sha256"] == _sha256(entry.read_bytes())
    # The closure is read only: the build happens in the disposable copy.
    assert not (closure_root / "node_modules").exists()
    assert not (closure_root / "ui-tui" / "dist").exists()


# ----------------------------------------------------------------------------- scans


def test_secret_scan_refuses_credential_material(tool: types.ModuleType) -> None:
    material = "-----BEGIN RSA " + "PRIVATE KEY-----\n" + "A" * 96 + "\n"
    assert tool._secret_hits_bytes("member.py", material.encode(), ("private-key-material",))
    assert tool._secret_hits_bytes("member.py", b"portable\n", ("private-key-material",)) == []
    token = "gh" + "p_" + "b" * 36
    assert tool._secret_hits_bytes("member.py", token.encode(), ("github-token",))


def test_report_scan_refuses_operator_paths_in_plain_text_members(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """Reports, the lock and SHA256SUMS are plain text; the canonical scanner cannot open them."""

    lifecycle = tool.load_product(ROOT)
    operator_path = "/" + "home" + "/operator/" + "Desk" + "top/agentes/product"
    report = tmp_path / "aether-agents-1.0.0rc1-clean-install.json"
    report.write_text(json.dumps({"note": operator_path}), encoding="utf-8")
    with pytest.raises(tool.BundleError) as refusal:
        tool.scan_report_bytes(lifecycle, [report])
    assert refusal.value.code == "private-path-scan"

    clean = tmp_path / "aether-agents-1.0.0rc1-provenance.json"
    clean.write_text(json.dumps({"note": "<disposable-root>/manager"}), encoding="utf-8")
    scanned = tool.scan_report_bytes(lifecycle, [clean])
    assert scanned == {
        "scope": ["aether-agents-1.0.0rc1-provenance.json"],
        "result": "clean",
    }


def test_path_shapes_do_not_match_the_canonical_patterns(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    lifecycle = tool.load_product(ROOT)
    for literal in (
        "/" + "home" + "/user/",
        "/" + "Users" + "/Example/",
        "C:\\" + "Users" + "\\Someone\\",
    ):
        shaped = tool._path_shape(literal)
        assert "<name>" in shaped
        assert tool._operator_path_matches(lifecycle, shaped.encode()) == []


def test_portable_masks_every_host_path_a_report_could_disclose(tmp_path: Path) -> None:
    tool = _load_tool()
    roots = tmp_path / "work" / "install-roots"
    bundle = tmp_path / "bundle"
    checkout = tmp_path / "checkout"
    masks = tool._report_masks(roots, tmp_path / "work", bundle, checkout)
    text = f"{roots}/manager {bundle}/x.whl {checkout}/src {sys.executable}"
    masked = tool._portable(text, masks)
    assert str(tmp_path) not in masked
    assert "<disposable-root>/manager" in masked
    assert "<bundle>/x.whl" in masked
    assert "<aether-checkout>/src" in masked
    assert "<probe-interpreter>" in masked


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
    shape = "/" + "home" + "/<name>/"
    assert shape in fork_scan["distinct_match_shapes"]
    assert all("<name>" in value for value in fork_scan["distinct_match_shapes"])
    assert report["secrets"]["strict_result"] == "clean"


def test_captured_tool_output_records_no_run_to_run_elapsed_value(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """The elapsed value is the only part of uv's output that differs between two runs of
    the same inputs, and the qualified member set must be reproducible from them."""

    lines = (
        "Resolved 6 packages in 8ms",
        "Prepared 1 package in 29ms",
        "Checked 6 packages in 0.50ms",
        "Installed 1 package in 1.2s",
        "Audited 5 packages in 1m 3s",
    )
    for line in lines:
        assert tool._normalize_captured(line) == line.split(" in ")[0] + " in <elapsed>"
    assert tool._normalize_captured("nothing timed here") == "nothing timed here"

    recorded = tool._probe(
        "elapsed",
        [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('Installed 1 package in 35ms\\n')",
        ],
        root=tmp_path,
        environment=dict(os.environ),
        required=True,
        expectation="exit-zero",
    )
    assert recorded["exit_code"] == 0
    assert recorded["stderr"] == "Installed 1 package in <elapsed>"


def test_captured_interpreter_leaf_is_normalized_like_the_elapsed_value(
    tool: types.ModuleType,
) -> None:
    """`bin/python` and `bin/python3` (and `bin/python3.13`) are the same interpreter, and
    which alias a run records depends only on whether the venv already existed, so a
    capture records the leaf canonically instead of certifying the alias as a member byte."""

    for leaf in ("python", "python3", "python3.13", "python3.13t", "python3.exe"):
        line = f"Using CPython interpreter at: /checkout/.venv/bin/{leaf}"
        assert tool._normalize_captured(line) == (
            "Using CPython interpreter at: /checkout/.venv/bin/<interpreter>"
        )
    for untouched in (
        "run python3 -m aether_agents",
        "Activate with: source manager/bin/activate",
        "manager/bin/python-config --cflags",
    ):
        assert tool._normalize_captured(untouched) == untouched


def test_build_interpreter_is_masked_before_the_checkout_it_lives_in(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """The build interpreter normally lives inside the Aether checkout, so a checkout mask
    that ran first would leave the one part of the path that differs between a fresh and an
    already-populated venv in every capture."""

    interpreter = Path(sys.executable)
    checkout = interpreter.parent.parent if interpreter.parent.name == "bin" else interpreter.parent
    masks = tool._report_masks(
        tmp_path / "install-roots", tmp_path / "work", tmp_path / "bundle", checkout
    )
    recorded = tool._portable_capture(f"Using CPython interpreter at: {interpreter}", masks)
    assert recorded == "Using CPython interpreter at: <probe-interpreter>"
    assert "bin/python" not in recorded


def test_recorded_capture_does_not_depend_on_the_build_directory_or_the_venv_alias(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    """Two builds of the same revisions must record the same bytes.  A capture may not
    embed the length of the build directory (the ``[truncated N characters]`` footer counts
    the real host path when masking happens after excerpting) nor which alias the venv
    happens to expose for its interpreter."""

    script = "import sys; sys.stdout.write(sys.argv[1] + 'y' * 1200)"
    recorded = []
    for directory, leaf in (("a", "python"), ("a-much-longer-build-directory", "python3")):
        work = tmp_path / directory
        root = work / "install-roots"
        interpreter = root / "runtime" / "bin" / leaf
        interpreter.parent.mkdir(parents=True)
        interpreter.symlink_to(sys.executable)
        recorded.append(
            tool._probe(
                "capture",
                [str(interpreter), "-c", script, str(root)],
                root=root,
                environment=dict(os.environ),
                required=True,
                expectation="exit-zero",
                mask=tool._report_masks(root, work, tmp_path / "bundle", tmp_path / "checkout"),
            )
        )

    first, second = recorded
    assert first["exit_code"] == second["exit_code"] == 0
    assert "<disposable-root>/runtime/bin/<interpreter>" in first["argv"]
    assert first["argv"] == second["argv"]
    assert "[truncated" in first["stdout"]
    assert first["stdout"] == second["stdout"]


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


def _published(bundle: Path) -> list[str]:
    return [
        f"{path.name}\tsha256:{_sha256(path.read_bytes())}"
        for path in sorted(bundle.iterdir())
        if path.is_file()
    ]


def test_qualified_members_are_the_verified_set_plus_the_checksum_file(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    bundle = _bundle(tmp_path / "bundle")
    members = tool.qualified_members(bundle)
    assert sorted(members) == ["SHA256SUMS", "a.bin", "b.bin"]
    assert members["a.bin"] == {"sha256": _sha256(b"alpha\n"), "bytes": 6}
    assert members["SHA256SUMS"]["sha256"] == _sha256((bundle / "SHA256SUMS").read_bytes())

    (bundle / "unlisted.bin").write_bytes(b"unlisted\n")
    with pytest.raises(tool.BundleError) as unlisted:
        tool.qualified_members(bundle)
    assert unlisted.value.code == "member-drift"


def test_verify_published_assets_accepts_only_the_qualified_bytes(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    bundle = _bundle(tmp_path / "bundle")
    report = tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=_published(bundle))
    assert report["result"] == "verified"
    assert report["tag"] == "v1.0.0-rc.1"
    assert sorted(report["assets"]) == ["SHA256SUMS", "a.bin", "b.bin"]


def test_verify_published_assets_refuses_every_way_a_release_can_disagree(
    tool: types.ModuleType, tmp_path: Path
) -> None:
    bundle = _bundle(tmp_path / "bundle")
    qualified = _published(bundle)

    tampered = [
        "a.bin\tsha256:" + "0" * 64 if line.startswith("a.bin\t") else line for line in qualified
    ]
    with pytest.raises(tool.BundleError) as mismatch:
        tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=tampered)
    assert mismatch.value.code == "published-asset-mismatch"
    assert "a.bin" in str(mismatch.value)
    assert _sha256(b"alpha\n") in str(mismatch.value)

    missing = [line for line in qualified if not line.startswith("b.bin\t")]
    with pytest.raises(tool.BundleError) as drift:
        tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=missing)
    assert drift.value.code == "published-asset-drift"
    assert "['b.bin']" in str(drift.value)

    unexpected = [*qualified, "stray.bin\tsha256:" + "1" * 64]
    with pytest.raises(tool.BundleError) as extra:
        tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=unexpected)
    assert extra.value.code == "published-asset-drift"
    assert "['stray.bin']" in str(extra.value)

    digestless = ["a.bin\t" if line.startswith("a.bin\t") else line for line in qualified]
    with pytest.raises(tool.BundleError) as unverifiable:
        tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=digestless)
    assert unverifiable.value.code == "published-asset-unverifiable"
    assert "['a.bin']" in str(unverifiable.value)

    malformed = [line for line in qualified if not line.startswith("a.bin\t")] + ["a.bin"]
    with pytest.raises(tool.BundleError) as malformed_line:
        tool.verify_published_assets(bundle, tag="v1.0.0-rc.1", lines=malformed)
    assert malformed_line.value.code == "published-assets-malformed"


def test_members_and_verify_published_assets_cli(
    tool: types.ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle = _bundle(tmp_path / "bundle")
    assert tool.main(["members", "--bundle", str(bundle)]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed == [str(bundle / name) for name in ("SHA256SUMS", "a.bin", "b.bin")]

    listing = tmp_path / "published.tsv"
    listing.write_text("".join(f"{line}\n" for line in _published(bundle)), encoding="utf-8")
    assert (
        tool.main(
            [
                "verify-published-assets",
                "--bundle",
                str(bundle),
                "--tag",
                "v1.0.0-rc.1",
                "--assets",
                str(listing),
            ]
        )
        == 0
    )
    assert "v1.0.0-rc.1" in capsys.readouterr().out

    # the workflow pipes the asset listing in on stdin
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("".join(f"{line}\n" for line in _published(bundle)))
    )
    assert (
        tool.main(
            [
                "verify-published-assets",
                "--bundle",
                str(bundle),
                "--tag",
                "v1.0.0-rc.1",
                "--assets",
                "-",
            ]
        )
        == 0
    )
    capsys.readouterr()

    listing.write_text("a.bin\tsha256:" + "0" * 64 + "\n", encoding="utf-8")
    assert (
        tool.main(
            [
                "verify-published-assets",
                "--bundle",
                str(bundle),
                "--tag",
                "v1.0.0-rc.1",
                "--assets",
                str(listing),
            ]
        )
        == 1
    )
    assert "published-asset-drift" in capsys.readouterr().err

    assert tool.main(["verify-published-assets", "--bundle", str(bundle), "--tag", "t"]) == 2
    assert (
        tool.main(
            [
                "verify-published-assets",
                "--bundle",
                str(bundle),
                "--tag",
                "v1.0.0-rc.1",
                "--assets",
                str(tmp_path / "absent.tsv"),
            ]
        )
        == 1
    )
    assert "assets-missing" in capsys.readouterr().err


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
        "observer": {
            "plugin_name": "aether-contract-observer",
            "group": "hermes_agent.plugins",
            "target": "aether_agents.observation.capture.hermes_plugin",
        },
        "sha256": _sha256(payload),
        "observer_requirements_sha256": "b" * 64,
        "observation_compatibility": {
            "event_write_version": "aether.observation.event.v1",
            "event_read_versions": ["aether.observation.event.v1"],
            "summary_write_version": "aether.observation.summary.v1",
            "summary_read_versions": ["aether.observation.summary.v1"],
            "segment_manifest_write_version": "aether.observation.segment-manifest.v1",
            "segment_manifest_read_versions": ["aether.observation.segment-manifest.v1"],
            "projection_schema_version": "aether.observation.projection.v1",
        },
    }
    fork = {
        "commit": "c" * 40,
        "version": "0.20.1",
        "tag": "v2026.8.18",
        "branch": "aether-main",
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
    tool: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lifecycle = tool.load_product(ROOT)
    lock = _lock(tool, lifecycle, tmp_path)
    assert lock["schema_version"] == tool.RELEASE_LOCK_SCHEMA_VERSION == 5
    assert lock["hermes"]["extras"] == ["mcp"]
    assert lock["hermes"]["source_mode"] == "maintained_fork"
    assert lock["hermes"]["repository"] == "https://github.com/DarkArty07/aether-hermes"
    assert lock["hermes"]["branch"] == "aether-main"
    assert lock["aether"]["version"] == "1.0.0-rc.1"
    assert lock["aether"]["package_version"] == "1.0.0rc1"
    assert lock["aether"]["git_tag"] == "v1.0.0-rc.1"
    assert lock["profile_bundle"]["version"] == "2"
    assert lock["profile_bundle"]["roles"] == ["morfeo", "supervisor", "implementer"]
    assert lock["hermes"]["artifacts"][0]["url"].endswith(
        "/releases/download/v1.0.0-rc.1/" + lock["hermes"]["artifacts"][0]["filename"]
    )

    # Integration state: the canonical schema this checkout ships declares 4, so strict
    # validation applies it (this unit's branch shipped while it still declared 3, which is
    # why the pair is only resolvable on the merged tree).
    applied = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert applied["schema_validation"] == "applied"
    assert applied["accepted_schema_versions"] == [4, 5]
    assert applied["repository_schema_version"] is None
    assert applied["pinned_identity"] == [
        "schema_version=5",
        "hermes.source_mode=maintained_fork",
        "hermes.repository=https://github.com/DarkArty07/aether-hermes",
        "hermes.branch=aether-main",
    ]

    recorded = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=True)
    assert recorded["schema_validation"] == "applied"
    assert recorded["accepted_schema_versions"] == [4, 5]
    assert recorded["repository_schema_version"] is None
    assert recorded["pinned_identity"] == applied["pinned_identity"]

    # Drift refusal stays covered: a repository whose canonical schema still declares the
    # retired version must refuse the v4 lock under strict validation rather than accept a
    # shape it cannot check, and the unchanged pinned identity is what the lenient path
    # records instead.
    legacy_path = tmp_path / "legacy-release-lock.schema.json"
    legacy = json.loads(json.dumps(_v4_lock_schema()))
    legacy["properties"]["schema_version"] = {"const": 3}
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
    monkeypatch.setattr(tool, "_lock_schema_path", lambda checkout: legacy_path)

    with pytest.raises(tool.BundleError) as drift:
        tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert drift.value.code == "lock-schema-drift"

    recorded_legacy = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=True)
    assert recorded_legacy["schema_validation"] == "not_applicable"
    assert recorded_legacy["repository_schema_version"] == 3
    assert recorded_legacy["pinned_identity"] == applied["pinned_identity"]


def _v4_lock_schema() -> dict:
    """The v4 lock shape, key-set closed, for the schema-declares-four test.

    This mirrors the key sets of the release-runtime unit's
    `specs/001-aether-v1-productization/contracts/release-lock.schema.json` (the schema this
    repository ships once that unit lands), including `hermes.branch` being a closed-block
    requirement with the constant `aether-main`.  It is a key-set stub, not a copy: nested
    payloads the product's own inspection supplies (`observer`,
    `observation_compatibility`) are only required to be objects here.
    """

    entry_stub = {"type": "object"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "aether", "hermes", "profile_bundle"],
        "properties": {
            "schema_version": {"const": 5},
            "aether": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "version",
                    "package_version",
                    "distribution",
                    "git_tag",
                    "git_commit",
                    "python_requires",
                    "observer",
                    "wheel_sha256",
                    "observer_requirements_sha256",
                    "observation_compatibility",
                ],
                "properties": {
                    "version": {"type": "string"},
                    "package_version": {"type": "string"},
                    "distribution": {"const": "aether-agents"},
                    "git_tag": {"type": "string"},
                    "git_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    "python_requires": {"const": ">=3.11,<3.14"},
                    "observer": entry_stub,
                    "wheel_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "observer_requirements_sha256": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$",
                    },
                    "observation_compatibility": entry_stub,
                },
            },
            "hermes": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_mode",
                    "repository",
                    "branch",
                    "version",
                    "commit",
                    "python_requires",
                    "source_tree_sha256",
                    "artifacts",
                    "extras",
                ],
                "properties": {
                    "source_mode": {"const": "maintained_fork"},
                    "repository": {"const": "https://github.com/DarkArty07/aether-hermes"},
                    "branch": {"const": "aether-main"},
                    "version": {"type": "string"},
                    "tag": {"type": "string"},
                    "commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    "python_requires": {"type": "string"},
                    "source_tree_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "artifacts": {"type": "array", "minItems": 1, "items": entry_stub},
                    "extras": {"type": "array", "items": {"const": "mcp"}},
                },
            },
            "profile_bundle": {
                "type": "object",
                "additionalProperties": False,
                "required": ["version", "sha256", "roles"],
                "properties": {
                    "version": {"const": "2"},
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "roles": {"type": "array", "minItems": 3, "maxItems": 3},
                },
            },
        },
    }


def test_lock_validation_applies_the_repository_schema_when_it_declares_four(
    tool: types.ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lock without `hermes.branch` cannot pass: the pinned identity and the closed v4 shape
    each refuse it, so this test fails if the tool stops emitting the declared branch."""

    lifecycle = tool.load_product(ROOT)
    lock = _lock(tool, lifecycle, tmp_path)
    schema_path = tmp_path / "release-lock.schema.json"
    schema_path.write_text(json.dumps(_v4_lock_schema()), encoding="utf-8")
    monkeypatch.setattr(tool, "_lock_schema_path", lambda checkout: schema_path)

    applied = tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert applied["schema_validation"] == "applied"
    assert applied["repository_schema_version"] == 5

    broken = json.loads(json.dumps(lock))
    broken["hermes"]["source_mode"] = "upstream"
    with pytest.raises(tool.BundleError) as refusal:
        tool.validate_lock(broken, aether_checkout=ROOT, allow_schema_drift=False)
    assert refusal.value.code == "lock-identity"

    del lock["hermes"]["branch"]
    with pytest.raises(tool.BundleError) as unpinned:
        tool.validate_lock(lock, aether_checkout=ROOT, allow_schema_drift=False)
    assert unpinned.value.code == "lock-identity"
    assert "hermes.branch is None" in str(unpinned.value)

    # Every pinned value is correct here, so only the schema can refuse this: a stub that
    # required just `schema_version` would accept a lock the v4 shape rejects.
    drifted = _lock(tool, lifecycle, tmp_path)
    drifted["hermes"]["artifacts"] = []
    drifted["hermes"]["unexpected"] = True
    with pytest.raises(tool.BundleError) as unshaped:
        tool.validate_lock(drifted, aether_checkout=ROOT, allow_schema_drift=False)
    assert unshaped.value.code == "lock-schema-invalid"
    assert "'unexpected' was unexpected" in str(unshaped.value)
    assert "hermes/artifacts" in str(unshaped.value)


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
