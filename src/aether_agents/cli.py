"""Aether CLI entry point — the ``[project.scripts] aether`` target.

Normative source: ``specs/001-aether-v1-productization/contracts/cli.md``. This module
implements the Hermes-free observation/version surface plus the release-scoped A1
``setup``/``doctor``/``update``/``rollback``/``uninstall`` lifecycle. Commands that
still require live project/profile/service orchestration are explicitly unsupported and
return exit code 3 rather than pretending to perform those effects.

Nothing this module imports — directly, or by building the ``observe`` subparser so
``aether observe --help`` can show its full flag surface — imports Hermes, so
``--help``/``--version`` keep working even when the managed Hermes runtime is absent or
broken. ``aether_agents.commands.observe`` and the modules it imports at its own module
scope (``observation.query``, ``observation.report``, ``observation.contracts``,
``paths``, ``result``) are all Hermes-free by construction; the actual reduce/storage
seam ``observe`` depends on is imported lazily inside :mod:`aether_agents.observation.
query`, only once ``observe`` is the selected subcommand and its handler runs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from aether_agents import product_version
from aether_agents.observation.contracts import canonical_json_str
from aether_agents.result import Envelope

__all__ = ["main"]

#: cli.md section 2: every documented command this build does not implement. The bare
#: `aether` launch (no subcommand) is handled the same way, just outside this tuple.
_UNSUPPORTED_COMMANDS = (
    "start",
    "stop",
    "restart",
    "status",
)

_STDOUT_RESULTS = ("ready", "changed", "no_change", "planned")
_STATEFUL_COMMANDS = ("setup", "update", "rollback", "uninstall")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aether", description="Aether Agents CLI.")
    parser.add_argument(
        "--version", action="store_true", help="Print the Aether product version and exit."
    )
    # Accepted at top level too so a bare `aether --project PATH --json` (the implicit
    # Morfeo launch) reaches the documented `unsupported` path instead of a usage error.
    parser.add_argument("--project", metavar="PATH", default=None)
    parser.add_argument("--json", action="store_true")

    subparsers = parser.add_subparsers(dest="command")

    from aether_agents.commands.observe import build_subparser as build_observe_subparser

    build_observe_subparser(subparsers)

    from aether_agents.commands.init import build_subparser as build_init_subparser

    build_init_subparser(subparsers)

    from aether_agents.commands.knowledge import build_subparser as build_knowledge_subparser

    build_knowledge_subparser(subparsers)

    from aether_agents.monitor.commands import build_subparser as build_monitor_subparser

    build_monitor_subparser(subparsers)

    version_parser = subparsers.add_parser("version", help="Report the Aether product version.")
    version_parser.add_argument("--json", action="store_true")

    doctor_parser = subparsers.add_parser(
        "doctor", help="Inspect the active Aether/observer release without importing Hermes."
    )
    doctor_parser.add_argument("--project", metavar="PATH", default=None)
    doctor_parser.add_argument("--json", action="store_true")

    setup_parser = subparsers.add_parser(
        "setup", help="Install one verified local Aether wheel and locked Hermes checkout."
    )
    setup_parser.add_argument("--wheel", type=Path, required=True)
    setup_parser.add_argument("--hermes-checkout", type=Path, required=True)
    setup_parser.add_argument("--release-lock", type=Path, required=True)
    setup_parser.add_argument("--dry-run", action="store_true")
    setup_parser.add_argument("--yes", action="store_true")
    setup_parser.add_argument("--json", action="store_true")

    update_parser = subparsers.add_parser(
        "update", help="Activate a fully staged, verified Aether release."
    )
    update_parser.add_argument("version", nargs="?", default=None)
    update_parser.add_argument("--prerelease", action="store_true")
    update_parser.add_argument("--wheel", type=Path, default=None)
    update_parser.add_argument("--hermes-checkout", type=Path, default=None)
    update_parser.add_argument("--release-lock", type=Path, default=None)
    update_parser.add_argument(
        "--local",
        action="store_true",
        help=(
            "Promote one local candidate from explicit clean Aether and maintained-fork "
            "commits. Preview is non-mutating; activation requires --yes."
        ),
    )
    update_parser.add_argument("--aether-checkout", type=Path, default=None)
    update_parser.add_argument("--aether-commit", default=None)
    update_parser.add_argument("--fork-checkout", type=Path, default=None)
    update_parser.add_argument("--fork-commit", default=None)
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--yes", action="store_true")
    update_parser.add_argument("--json", action="store_true")

    rollback_parser = subparsers.add_parser(
        "rollback", help="Atomically select a prior coherent Aether release."
    )
    rollback_parser.add_argument("version", nargs="?", default=None)
    rollback_parser.add_argument("--dry-run", action="store_true")
    rollback_parser.add_argument("--yes", action="store_true")
    rollback_parser.add_argument("--json", action="store_true")

    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Remove product releases while preserving state by default."
    )
    uninstall_parser.add_argument("--purge", action="store_true")
    uninstall_parser.add_argument("--export", metavar="PATH", default=None)
    uninstall_parser.add_argument("--dry-run", action="store_true")
    uninstall_parser.add_argument("--yes", action="store_true")
    uninstall_parser.add_argument("--json", action="store_true")

    reconcile_parser = subparsers.add_parser(
        "reconcile",
        help="Reconcile product projections for the authenticated active release.",
    )
    reconcile_parser.add_argument(
        "--to",
        default=None,
        help="Target for reconciliation. Only 'active' is supported in this build.",
    )
    reconcile_parser.add_argument("--dry-run", action="store_true")
    reconcile_parser.add_argument("--yes", action="store_true")
    reconcile_parser.add_argument("--json", action="store_true")

    for name in _UNSUPPORTED_COMMANDS:
        unsupported_parser = subparsers.add_parser(
            name, help="Not implemented in this build (A1 manager contract)."
        )
        unsupported_parser.add_argument("--json", action="store_true")

    return parser


def _emit(envelope: Envelope, *, json_mode: bool, human: str) -> int:
    if json_mode:
        print(canonical_json_str(envelope.to_json()))
        return envelope.exit_code
    target = sys.stdout if envelope.result in _STDOUT_RESULTS else sys.stderr
    print(human, file=target)
    return envelope.exit_code


def _run_version(json_mode: bool) -> int:
    version = product_version()
    envelope = Envelope(
        command="version",
        result="ready",
        manager_version=version,
        active_version=version,
        data={"product_version": version},
    )
    # cli.md's `version` also documents Hermes source mode/tag/commit and
    # profile-policy version; those belong to the A1 manager contract's runtime, which
    # this build does not implement, so their absence is a visible warning rather than
    # a fabricated field (the same "partial/estimated/unavailable stays visible" ethos
    # OBS-FR-058/059 apply to observation fields).
    envelope.warn(
        "MANAGER_DETAIL_UNAVAILABLE",
        "Hermes source mode/tag/commit and profile-policy version belong to the A1 "
        "manager contract and are not reported by this build.",
    )
    return _emit(envelope, json_mode=json_mode, human=f"aether {version}")


def _run_unsupported(command: str, *, json_mode: bool) -> int:
    envelope = Envelope(command=command, result="unsupported")
    message = (
        f"'{command}' is part of the A1 manager contract and is not implemented in this build."
    )
    envelope.fail("COMMAND_NOT_IMPLEMENTED", message)
    return _emit(envelope, json_mode=json_mode, human=f"error: {message}")


def _run_launch(argv: Sequence[str]) -> int:
    """Hand a bare ``aether`` invocation to the canonical Morfeo launcher."""
    from aether_agents.launcher import main as launcher_main

    return launcher_main(argv)


def _lifecycle_manager():
    # Lazy manager import preserves the static Hermes-free CLI boundary and keeps
    # ``aether --version`` independent from lifecycle state.
    from aether_agents.lifecycle import LifecycleManager, ReleaseStore
    from aether_agents.paths import data_root, state_root

    return LifecycleManager(
        store=ReleaseStore(data_root(), state_root=state_root()),
        python_executable=Path(sys.executable),
    )


def _manager_authority_error(command: str, message: str, *, json_mode: bool) -> int:
    envelope = Envelope(
        command=command,
        result="error",
        manager_version=product_version(),
        failure_kind="integrity_failure",
        data={
            "remediation": [
                "aether doctor",
                "aether reconcile --to active",
                "aether rollback",
            ]
        },
    )
    envelope.fail("ACTIVE_MANAGER_AUTHORITY_REQUIRED", message)
    return _emit(envelope, json_mode=json_mode, human=f"error: {message}")


def _dispatch_stateful_to_active(
    args_list: list[str],
    *,
    command: str,
    json_mode: bool,
) -> int | None:
    """Run a stateful command in the authenticated active manager environment.

    The public uv-tool command remains the entry point.  When it is not already the
    active release manager, this launcher verifies the immutable active manager and
    invokes that environment directly with every ambient Python/uv/pip override
    removed.  An old managed manager refuses instead of recursively forwarding.
    """

    from aether_agents.lifecycle import IntegrityError, _isolated_subprocess_environment

    manager = _lifecycle_manager()
    try:
        target = manager.active_manager_dispatch_target()
    except (IntegrityError, OSError) as error:
        return _manager_authority_error(command, str(error), json_mode=json_mode)
    if target is None:
        if command == "setup":
            return None
        # First local-candidate promotion may bootstrap the active manager the same
        # way setup does; subsequent update/rollback/uninstall still require it.
        if command == "update" and "--local" in args_list:
            return None
        if command == "reconcile":
            return _manager_authority_error(
                command,
                "no active manager can authorize reconciliation; unsupported legacy route or uninitialized product",
                json_mode=json_mode,
            )
        return _manager_authority_error(
            command,
            "no active manager can authorize this mutation; run 'aether setup' or "
            "'aether reconcile --to active' before retrying",
            json_mode=json_mode,
        )
    active, manager_python = target
    try:
        executing = manager.executing_active_manager()
    except (IntegrityError, OSError) as mismatch:
        if manager.executing_manager_is_release_scoped():
            return _manager_authority_error(command, str(mismatch), json_mode=json_mode)
    else:
        if executing.release_id == active.release_id:
            return None

    environment = _isolated_subprocess_environment()
    if any(name.startswith(("PYTHON", "UV_", "PIP_")) for name in environment):
        return _manager_authority_error(
            command,
            "active manager dispatch environment is not isolated",
            json_mode=json_mode,
        )
    try:
        completed = subprocess.run(
            [str(manager_python), "-m", "aether_agents.cli", *args_list],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
    except OSError:
        return _manager_authority_error(
            command,
            "verified active manager could not be executed; run 'aether doctor', then "
            "'aether reconcile --to active' or 'aether rollback'",
            json_mode=json_mode,
        )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


def _run_setup(args: argparse.Namespace) -> int:
    from aether_agents.lifecycle import IntegrityError

    manager = _lifecycle_manager()
    try:
        if args.dry_run or not args.yes:
            candidate = manager.inspect_candidate(
                wheel=args.wheel,
                hermes_checkout=args.hermes_checkout,
                release_lock=args.release_lock,
            )
            envelope = Envelope(
                command="setup",
                result="planned",
                manager_version=product_version(),
                data={
                    "target_version": candidate["version"],
                    "wheel_filename": candidate["wheel_filename"],
                    "wheel_sha256": candidate["wheel_sha256"],
                    "managed_profiles": ["morfeo", "supervisor", "implementer"],
                    "live_profiles_or_services_modified": False,
                },
            )
            if not args.yes and not args.dry_run:
                envelope.warn(
                    "CONFIRMATION_REQUIRED",
                    "Re-run setup with --yes after reviewing this local install plan.",
                )
            return _emit(
                envelope,
                json_mode=args.json,
                human=f"planned Aether install: {candidate['version']}",
            )
        installed = manager.install(
            wheel=args.wheel,
            hermes_checkout=args.hermes_checkout,
            release_lock=args.release_lock,
        )
    except (IntegrityError, OSError) as error:
        envelope = Envelope(
            command="setup",
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail("SETUP_REFUSED", str(error))
        return _emit(envelope, json_mode=args.json, human=f"error: {error}")
    envelope = Envelope(
        command="setup",
        result="changed",
        changed=True,
        manager_version=product_version(),
        active_version=installed.version,
        data={
            "active_release_id": installed.release_id,
            "wheel_sha256": installed.wheel_sha256,
            "managed_profiles": ["morfeo", "supervisor", "implementer"],
            "live_profiles_or_services_modified": False,
        },
    )
    return _emit(
        envelope,
        json_mode=args.json,
        human=f"installed Aether release: {installed.version}",
    )


def _run_doctor(*, json_mode: bool) -> int:
    manager = _lifecycle_manager()
    result = manager.doctor()
    observed_version = result.details.get("active_version")
    active_version = observed_version if isinstance(observed_version, str) else None
    observer = {
        "status": "ready" if result.ready else "unavailable",
        "active_release_id": result.active_release_id,
        "diagnostic_codes": list(result.codes),
        **result.details,
    }
    envelope = Envelope(
        command="doctor",
        result="ready" if result.ready else "error",
        manager_version=product_version(),
        active_version=active_version,
        failure_kind="integrity_failure",
        data={"observer": observer},
    )
    if not result.ready:
        envelope.fail(
            "LIFECYCLE_INTEGRITY_FAILED",
            "The active Aether observer release is absent or incoherent.",
            diagnostic_codes=list(result.codes),
        )
    human = (
        f"Aether observer ready ({result.active_release_id})"
        if result.ready
        else "Aether observer unavailable: " + ", ".join(result.codes)
    )
    return _emit(envelope, json_mode=json_mode, human=human)


def _select_release(manager, version: str | None, *, rollback: bool):
    from aether_agents.lifecycle import IntegrityError

    active = manager.store.active()
    assert active is not None
    if rollback and version is None:
        if active.previous_release_id is None:
            raise IntegrityError("active release has no rollback target")
        return manager.store._read_release(active.previous_release_id)
    candidates = [
        record
        for record in manager.store.records()
        if record.release_id != active.release_id and (version is None or record.version == version)
    ]
    if len(candidates) != 1:
        raise IntegrityError("requested release is not one unique staged candidate")
    return candidates[0]


def _local_candidate_arguments(args: argparse.Namespace) -> tuple[Path, str, Path, str]:
    """Validate the pinned local-candidate surface before any lifecycle work."""

    from aether_agents.lifecycle import IntegrityError

    conflicts = [
        name
        for name, present in (
            ("[VERSION]", args.version is not None),
            ("--prerelease", args.prerelease),
            ("--wheel", args.wheel is not None),
            ("--hermes-checkout", args.hermes_checkout is not None),
            ("--release-lock", args.release_lock is not None),
        )
        if present
    ]
    if conflicts:
        raise IntegrityError("--local is mutually exclusive with " + ", ".join(conflicts))
    required = {
        "--aether-checkout": args.aether_checkout,
        "--aether-commit": args.aether_commit,
        "--fork-checkout": args.fork_checkout,
        "--fork-commit": args.fork_commit,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise IntegrityError(
            "--local requires " + ", ".join(missing) + " (identity is never guessed)"
        )
    return (
        args.aether_checkout,
        args.aether_commit,
        args.fork_checkout,
        args.fork_commit,
    )


def _run_local_transition(args: argparse.Namespace) -> int:
    """Preview or activate one local candidate from explicit clean commits."""

    from aether_agents.lifecycle import IntegrityError

    manager = _lifecycle_manager()
    command = "update"
    try:
        aether_checkout, aether_commit, fork_checkout, fork_commit = _local_candidate_arguments(
            args
        )
        try:
            executing_manager = manager.executing_active_manager()
        except IntegrityError:
            if manager.store.active(required=False) is not None:
                raise
            executing_manager = None
        candidate = manager.local_candidate(
            aether_checkout=aether_checkout,
            aether_commit=aether_commit,
            fork_checkout=fork_checkout,
            fork_commit=fork_commit,
        )
        if args.dry_run or not args.yes:
            current = manager.store.active(required=False)
            envelope = Envelope(
                command=command,
                result="planned",
                manager_version=product_version(),
                active_version=None if current is None else current.version,
                data={
                    "mode": "local",
                    "current_release_id": None if current is None else current.release_id,
                    "candidate": candidate.to_record(),
                    "service_interruption": manager.service_plan(),
                    "preserved_state": manager.preserved_state_report(),
                    "blockers": [],
                },
            )
            if not args.yes and not args.dry_run:
                envelope.warn(
                    "CONFIRMATION_REQUIRED",
                    "Re-run update --local with --yes to build and activate this candidate.",
                )
            return _emit(
                envelope,
                json_mode=args.json,
                human=(
                    "planned local "
                    + (
                        "install"
                        if current is None
                        else f"update: {current.version} -> {candidate.display_version}"
                    )
                    + (f": {candidate.display_version}" if current is None else "")
                    + f" (aether {candidate.aether_commit[:12]}, fork "
                    f"{candidate.fork_commit[:12]})"
                ),
            )
        manager.recover()
        current = manager.store.active(required=False)
        selected = manager.update_local(
            aether_checkout=aether_checkout,
            aether_commit=aether_commit,
            fork_checkout=fork_checkout,
            fork_commit=fork_commit,
            expected_active_release_id=None if current is None else current.release_id,
        )
    except IntegrityError as error:
        envelope = Envelope(
            command=command,
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail("LOCAL_UPDATE_REFUSED", str(error))
        return _emit(envelope, json_mode=args.json, human=f"error: {error}")
    envelope = Envelope(
        command=command,
        result="changed",
        changed=True,
        manager_version=product_version(),
        active_version=selected.version,
        data={
            "mode": "local",
            "active_release_id": selected.release_id,
            "executing_manager_release_id": (
                None if executing_manager is None else executing_manager.release_id
            ),
            "wheel_sha256": selected.wheel_sha256,
            "hermes_commit": selected.hermes_commit,
            "observation_state_preserved": True,
        },
    )
    return _emit(
        envelope,
        json_mode=args.json,
        human=f"active Aether release: {selected.version}",
    )


def _run_transition(args: argparse.Namespace, *, rollback: bool) -> int:
    from aether_agents.lifecycle import IntegrityError

    command = "rollback" if rollback else "update"
    if not rollback and getattr(args, "local", False):
        return _run_local_transition(args)
    if not rollback and any(
        value is not None
        for value in (
            getattr(args, "aether_checkout", None),
            getattr(args, "aether_commit", None),
            getattr(args, "fork_checkout", None),
            getattr(args, "fork_commit", None),
        )
    ):
        envelope = Envelope(
            command=command,
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail(
            "LOCAL_UPDATE_REFUSED",
            "local candidate inputs require --local; identity is never guessed",
        )
        return _emit(
            envelope,
            json_mode=getattr(args, "json", False),
            human="error: local candidate inputs require --local",
        )
    manager = _lifecycle_manager()
    try:
        executing_manager = manager.executing_active_manager()
        local_wheel = getattr(args, "wheel", None)
        local_checkout = getattr(args, "hermes_checkout", None)
        local_release_lock = getattr(args, "release_lock", None)
        if rollback and (local_wheel is not None or local_checkout is not None):
            raise IntegrityError("rollback does not accept local candidate inputs")
        local_inputs = (local_wheel, local_checkout, local_release_lock)
        if any(value is not None for value in local_inputs) and any(
            value is None for value in local_inputs
        ):
            raise IntegrityError(
                "local update requires --wheel, --hermes-checkout and --release-lock"
            )
        # A dry-run and the ordinary confirmation prompt are plans, not recovery
        # requests.  Reading the coherent active record and target must therefore
        # complete before any lifecycle mutation is considered.
        if args.dry_run or not args.yes:
            current = manager.store.active()
            assert current is not None
            if local_wheel is not None:
                assert local_checkout is not None
                assert local_release_lock is not None
                candidate = manager.inspect_candidate(
                    wheel=local_wheel,
                    hermes_checkout=local_checkout,
                    release_lock=local_release_lock,
                )
                if args.version is not None and candidate["version"] != args.version:
                    raise IntegrityError("requested version differs from candidate wheel")
                target_version = candidate["version"]
                target_release_id = f"{target_version}-{candidate['wheel_sha256'][:16]}"
            else:
                target = _select_release(manager, args.version, rollback=rollback)
                target_version = target.version
                target_release_id = target.release_id
            envelope = Envelope(
                command=command,
                result="planned",
                manager_version=product_version(),
                active_version=current.version,
                data={
                    "current_release_id": current.release_id,
                    "target_release_id": target_release_id,
                    "target_version": target_version,
                    "preserved_state": ["observations", "projects", "credentials", "sessions"],
                },
            )
            if not args.yes and not args.dry_run:
                envelope.warn(
                    "CONFIRMATION_REQUIRED",
                    f"Re-run {command} with --yes after reviewing this plan.",
                )
            return _emit(
                envelope,
                json_mode=args.json,
                human=f"planned {command}: {current.version} -> {target_version}",
            )
        # Rollback is deliberately available when the active Hermes runtime is
        # broken.  Structural store recovery is Hermes-free; the selected rollback
        # target is fully revalidated by activate_existing before the pointer moves.
        if rollback:
            manager.recover_for_rollback()
        else:
            manager.recover()
        current = manager.store.active()
        assert current is not None
        candidate = None
        target = None
        if local_wheel is not None:
            assert local_checkout is not None
            assert local_release_lock is not None
            candidate = manager.inspect_candidate(
                wheel=local_wheel,
                hermes_checkout=local_checkout,
                release_lock=local_release_lock,
            )
            if args.version is not None and candidate["version"] != args.version:
                raise IntegrityError("requested version differs from candidate wheel")
            target_version = candidate["version"]
            target_release_id = f"{target_version}-{candidate['wheel_sha256'][:16]}"
        else:
            target = _select_release(manager, args.version, rollback=rollback)
            target_version = target.version
            target_release_id = target.release_id
        if candidate is not None:
            selected = manager.update(
                wheel=local_wheel,
                hermes_checkout=local_checkout,
                release_lock=local_release_lock,
                expected_active_release_id=current.release_id,
            )
        else:
            assert target is not None
            if rollback and args.version is None:
                selected = manager.rollback(expected_active_release_id=current.release_id)
            else:
                selected = manager.activate_existing(
                    target.release_id,
                    transition_kind="rollback" if rollback else "update",
                    expected_active_release_id=current.release_id,
                )
    except IntegrityError as error:
        envelope = Envelope(
            command=command,
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail("RELEASE_TRANSITION_REFUSED", str(error))
        return _emit(envelope, json_mode=args.json, human=f"error: {error}")
    envelope = Envelope(
        command=command,
        result="changed",
        changed=True,
        manager_version=product_version(),
        active_version=selected.version,
        data={
            "active_release_id": selected.release_id,
            "executing_manager_release_id": executing_manager.release_id,
            "wheel_sha256": selected.wheel_sha256,
            "observation_state_preserved": True,
        },
    )
    return _emit(
        envelope,
        json_mode=args.json,
        human=f"active Aether release: {selected.version}",
    )


def _run_uninstall(args: argparse.Namespace) -> int:
    from aether_agents.lifecycle import IntegrityError

    manager = _lifecycle_manager()
    if args.export is not None:
        envelope = Envelope(
            command="uninstall",
            result="error",
            manager_version=product_version(),
            failure_kind="missing_prerequisite",
        )
        envelope.fail(
            "EXPORT_NOT_IMPLEMENTED",
            "State export is not available; no uninstall action was taken.",
        )
        return _emit(envelope, json_mode=args.json, human="error: state export unavailable")
    if args.dry_run:
        envelope = Envelope(
            command="uninstall",
            result="planned",
            manager_version=product_version(),
            data={
                "purge": bool(args.purge),
                "observation_state_preserved": not args.purge,
            },
        )
        return _emit(envelope, json_mode=args.json, human="planned Aether uninstall")
    if args.purge and not args.yes:
        envelope = Envelope(
            command="uninstall",
            result="blocked",
            manager_version=product_version(),
            failure_kind="blocked",
        )
        envelope.fail(
            "PROTECTED_ACTION_CONFIRMATION_REQUIRED",
            "Purging persistent Aether state requires explicit --yes confirmation.",
        )
        return _emit(
            envelope,
            json_mode=args.json,
            human="blocked: purge requires explicit --yes confirmation",
        )
    try:
        executing_manager = manager.executing_active_manager()
        result = manager.uninstall(purge=args.purge, confirmed=args.yes)
    except IntegrityError as error:
        envelope = Envelope(
            command="uninstall",
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail("UNINSTALL_REFUSED", str(error))
        return _emit(envelope, json_mode=args.json, human=f"error: {error}")
    envelope = Envelope(
        command="uninstall",
        result="changed",
        changed=True,
        manager_version=product_version(),
        data={
            "purged": result.purged,
            "executing_manager_release_id": executing_manager.release_id,
            "observation_state_preserved": result.preserved_observations,
        },
    )
    return _emit(envelope, json_mode=args.json, human="Aether product releases removed")


def _run_reconcile(args: argparse.Namespace) -> int:
    from aether_agents.lifecycle import IntegrityError

    command = "reconcile"
    if args.to != "active":
        envelope = Envelope(
            command=command,
            result="unsupported",
            manager_version=product_version(),
        )
        if args.to == "installed":
            msg = (
                "'aether reconcile --to installed' is part of the A1 manager contract and is "
                "not implemented in this build; use 'aether reconcile --to active'"
            )
        else:
            msg = "reconcile requires '--to active'; other modes are not supported in this build"
        envelope.fail("UNSUPPORTED_RECONCILE_MODE", msg)
        return _emit(envelope, json_mode=args.json, human=f"error: {msg}")

    manager = _lifecycle_manager()
    try:
        active = manager.store.active(required=False)
        if active is None:
            raise IntegrityError("no active release to reconcile")
        if not active.installed_file_fingerprint or active.schema_version < 3:
            raise IntegrityError(
                f"active release {active.release_id} cannot prove authentication; unsupported legacy route"
            )
        manager.executing_active_manager()
        status = manager.projection_status(active)
        mismatches = list(status.get("mismatches", []))

        if args.dry_run or not args.yes:
            envelope = Envelope(
                command=command,
                result="planned" if mismatches else "no_change",
                changed=False,
                manager_version=product_version(),
                active_version=active.version,
                data={
                    "mode": "active",
                    "active_release_id": active.release_id,
                    "mismatches": mismatches,
                    "projections_reconciled": 0,
                },
            )
            if not args.yes and not args.dry_run:
                envelope.warn(
                    "CONFIRMATION_REQUIRED",
                    "Re-run reconcile with --yes to apply projections.",
                )
            human = (
                f"planned reconciliation for active release: {active.version} ({len(mismatches)} mismatches)"
                if mismatches
                else f"projections already match active release: {active.version}"
            )
            return _emit(envelope, json_mode=args.json, human=human)

        recovery_result = manager.recover()
        post_status = manager.projection_status(active)
        reconciled_count = recovery_result.get("projections_reconciled", 0)
        changed = reconciled_count > 0 or bool(mismatches)
    except (IntegrityError, OSError) as error:
        envelope = Envelope(
            command=command,
            result="error",
            manager_version=product_version(),
            failure_kind="integrity_failure",
        )
        envelope.fail("RECONCILE_REFUSED", str(error))
        return _emit(envelope, json_mode=args.json, human=f"error: {error}")

    envelope = Envelope(
        command=command,
        result="changed" if changed else "no_change",
        changed=changed,
        manager_version=product_version(),
        active_version=active.version,
        data={
            "mode": "active",
            "active_release_id": active.release_id,
            "mismatches": list(post_status.get("mismatches", [])),
            "projections_reconciled": reconciled_count,
            "recovered": recovery_result,
        },
    )
    human = (
        f"reconciled projections for active release: {active.version}"
        if changed
        else f"projections already match active release: {active.version}"
    )
    return _emit(envelope, json_mode=args.json, human=human)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` and dispatch. Always returns an exit code; never raises."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    # Prepare argv for argparse subparsers: an option like `--resume latest` passed
    # at the top level for bare Morfeo launch has a value token that argparse subparsers
    # would otherwise misinterpret as a positional command before _run_launch can see it.
    parser_args: list[str] = []
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == "--resume" and i + 1 < len(args_list) and not args_list[i + 1].startswith("-"):
            parser_args.append(f"--resume={args_list[i + 1]}")
            i += 2
            continue
        parser_args.append(arg)
        i += 1

    parser = _build_parser()
    try:
        # `parse_known_args`, not `parse_args`: an unimplemented command may be
        # invoked with flags this build does not model at all
        # (e.g. `--dry-run`), and it must still reach the documented `unsupported`
        # path rather than an argparse usage error. `argparse.REMAINDER` was tried
        # first and rejected: CPython's own documentation flags it as unreliable when
        # combined with subparsers, and it reproducibly swallowed valid trailing flags
        # here too.
        args, extras = parser.parse_known_args(parser_args)
    except SystemExit as exc:
        # argparse's own --help/-h and usage-error paths call parser.exit(); normalize
        # them to a plain return so `main` never raises, matching its `-> int` contract.
        code = exc.code
        if code is None:
            return 0
        return int(code) if isinstance(code, int) else 1

    # Unknown flags are tolerated only for commands whose real A1 parser is not in
    # this telemetry-focused build.  Silently discarding a misspelled observe or
    # version option would turn invalid operator input into a plausible result.
    if extras and args.command is not None and args.command not in _UNSUPPORTED_COMMANDS:
        parser.print_usage(sys.stderr)
        print(f"aether: error: unrecognized arguments: {' '.join(extras)}", file=sys.stderr)
        return 2

    if args.command in _STATEFUL_COMMANDS:
        dispatched = _dispatch_stateful_to_active(
            args_list,
            command=args.command,
            json_mode=bool(getattr(args, "json", False)),
        )
        if dispatched is not None:
            return dispatched

    if args.command is None:
        if args.version:
            print(f"aether {product_version()}")
            return 0
        return _run_launch(args_list)

    if args.command == "init":
        from aether_agents.commands.init import run_init

        envelope = run_init(args)
        human = (
            f"error: {envelope.errors[0].message}"
            if envelope.errors
            else f"{envelope.result}: Aether project {envelope.data.get('project_id')}"
        )
        return _emit(envelope, json_mode=args.json, human=human)

    if args.command == "observe":
        from aether_agents.commands.observe import run_observe

        # Bind streams at invocation time.  ``commands.observe`` is imported while
        # parsers are built, and test/embedding stream objects may be replaced later.
        return run_observe(args, stdout=sys.stdout, stderr=sys.stderr)

    if args.command == "knowledge":
        from aether_agents.commands.knowledge import run_knowledge

        return run_knowledge(args)

    if args.command == "monitor":
        from aether_agents.monitor.commands import run_monitor

        return run_monitor(args)

    if args.command == "version":
        return _run_version(args.json)

    if args.command == "doctor":
        return _run_doctor(json_mode=args.json)

    if args.command == "setup":
        return _run_setup(args)

    if args.command == "update":
        return _run_transition(args, rollback=False)

    if args.command == "rollback":
        return _run_transition(args, rollback=True)

    if args.command == "reconcile":
        return _run_reconcile(args)

    if args.command == "uninstall":
        return _run_uninstall(args)

    return _run_unsupported(args.command, json_mode=getattr(args, "json", False))


if __name__ == "__main__":  # pragma: no cover - exercised via the installed console script
    sys.exit(main())
