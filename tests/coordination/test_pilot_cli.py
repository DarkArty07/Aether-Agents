import importlib.util
from pathlib import Path

import pytest

from olympus_v3.coordination.pilot_model import PilotError

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "run_r8_snake_pilot.py"
SPEC = importlib.util.spec_from_file_location("run_r8_snake_pilot", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_start_requires_empty_root_and_separate_control(tmp_path):
    root = (tmp_path / "product").resolve()
    control = (tmp_path / "control").resolve()
    root.mkdir()
    (root / "forged.txt").write_text("bad")
    with pytest.raises(PilotError, match="empty"):
        module._admit_root("start", root, expected_root=root, control_root=control)
    assert not control.exists()


def test_start_creates_external_control_and_resume_reuses_it(tmp_path):
    root = (tmp_path / "product").resolve()
    control = (tmp_path / "control").resolve()
    admitted_root, admitted_control, store = module._admit_root("start", root, expected_root=root, control_root=control)
    assert admitted_root == root
    assert admitted_control == control
    assert store.parent == control
    assert control.parent == root.parent and control != root
    assert (control / "marker.json").is_file()
    assert module._admit_root("resume", root, expected_root=root, control_root=control)[2] == store


def test_inspect_admission_is_read_only_and_never_creates_paths(tmp_path):
    root = (tmp_path / "product").resolve()
    control = (tmp_path / "control").resolve()
    with pytest.raises(PilotError, match="existing"):
        module._admit_root("inspect", root, expected_root=root, control_root=control)
    assert not root.exists()
    assert not control.exists()


def test_control_symlink_is_rejected(tmp_path):
    root = (tmp_path / "product").resolve()
    outside = (tmp_path / "outside").resolve()
    control = (tmp_path / "control").resolve(strict=False)
    root.mkdir()
    outside.mkdir()
    control.symlink_to(outside, target_is_directory=True)
    with pytest.raises(PilotError):
        module._admit_root("resume", root, expected_root=root, control_root=control)


def test_resume_rejects_insecure_control_permissions(tmp_path):
    root = (tmp_path / "product").resolve()
    control = (tmp_path / "control").resolve()
    module._admit_root("start", root, expected_root=root, control_root=control)
    control.chmod(0o755)
    with pytest.raises(PilotError, match="permissions"):
        module._admit_root("resume", root, expected_root=root, control_root=control)
