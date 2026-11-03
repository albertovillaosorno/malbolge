# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic tests for authoring and observing portable behavior programs.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for authoring and observing portable behavior programs."""

from __future__ import annotations

import builtins
import math
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override
from unittest.mock import patch

import pytest
from algorithms.diff import behavior_programs as behavior_module
from algorithms.diff.behavior import (
    BehaviorObservations,
    BehaviorProfile,
    BugObservation,
    BugProbe,
    BugState,
    CompatibilityObservation,
    CompatibilityProbe,
    IdentityObservation,
    IdentityProbe,
)
from algorithms.diff.behavior_programs import (
    AuthoredBehaviorPrograms,
    AuthoredBugProgram,
    BehaviorProgramError,
    BehaviorPrograms,
    BugProgram,
    author_behavior_programs,
    evaluate_behavior_programs,
    observe_behavior_programs,
)
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.probe_exec import (
    PathArgument,
    ProbeCommand,
    ProbeExecutionError,
    ProbeProgram,
    ProbeRoot,
    ProbeRunContext,
    ProbeTranscript,
    ToolExecutable,
    run_probe_program,
    run_probe_programs,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sized
    from types import MemberDescriptorType

    from algorithms.diff.model import TreeSnapshot

_PYTHON_TOOL = "python"
_REPOSITORY_ROLE = "repository"
_TOOL_ROLE = "tool"
_IDENTITY_A = "identity-a"
_IDENTITY_B = "identity-b"
_CHANGED_SECOND_BYTES = b"different"
_STABLE_IDENTITY_BYTES = b"stable"
_READ_BYTES = (
    "import pathlib,sys;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
)
_REQUIRE_FILE = (
    "import pathlib,sys;"
    "raise SystemExit(0 if pathlib.Path(sys.argv[1]).is_file() else 9)"
)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, name: str, data: bytes) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _ = (root / name).write_bytes(data)


def _context(root: Path, repository_root: Path) -> ProbeRunContext:
    return ProbeRunContext(
        source_root=root,
        repository_root=repository_root,
        tools=((_PYTHON_TOOL, Path(sys.executable)),),
    )


def _read_program(probe_id: str, relative_path: str) -> ProbeProgram:
    return ProbeProgram(
        probe_id=probe_id,
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES,
                    PathArgument(ProbeRoot.SOURCE, relative_path),
                ),
                digest_stdout=True,
            ),
        ),
    )


def _compatibility_program() -> ProbeProgram:
    return ProbeProgram(
        probe_id="runtime-capability",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _REQUIRE_FILE,
                    PathArgument(ProbeRoot.SOURCE, "runtime.flag"),
                ),
            ),
        ),
    )


def _programs() -> BehaviorPrograms:
    return BehaviorPrograms(
        identity=(_read_program("identity-stable", "identity.txt"),),
        compatibility=(_compatibility_program(),),
        bugs=(
            BugProgram(
                program=_read_program("historical-bug", "bug-state.txt"),
                correction_id="fix-historical-bug",
            ),
        ),
    )


def _trees(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    for root in (source, oracle):
        _write(root, "identity.txt", b"stable")
        _write(root, "runtime.flag", b"available")
    _write(source, "bug-state.txt", b"present")
    _write(oracle, "bug-state.txt", b"fixed")
    return source, oracle


def _authored(
    tmp_path: Path,
) -> tuple[AuthoredBehaviorPrograms, Path, Path]:
    source, oracle = _trees(tmp_path)
    authored = author_behavior_programs(
        _programs(),
        _context(source, tmp_path),
        _context(oracle, tmp_path),
    )
    return authored, source, oracle


class _HostileBehaviorHostError(RuntimeError):
    """A host error must not execute its custom formatter."""

    @override
    def __str__(self) -> str:
        message = "hostile behavior host formatter executed"
        raise AssertionError(message)


class _HostileBehaviorTreeError(ExactTreeError):
    """Delegated source snapshots cannot format foreign error types."""

    @override
    def __str__(self) -> str:
        message = "hostile behavior tree formatter executed"
        raise AssertionError(message)


class _HostileBehaviorProbeError(ProbeExecutionError):
    """Cross-stage execution errors may also carry foreign callbacks."""

    @override
    def __str__(self) -> str:
        message = "hostile probe formatter executed"
        raise AssertionError(message)


def test_context_resolution_error_ignores_late_path_string_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Path diagnostic formatting must not invoke post-import host hooks."""
    failure = PermissionError("blocked context root")

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        del path, strict
        raise failure

    def hostile_path_string(path: Path) -> str:
        del path
        message = "hostile path formatter executed"
        raise AssertionError(message)

    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    oracle_context = _context(oracle, tmp_path)
    caught: BehaviorProgramError | None = None
    with monkeypatch.context() as patch:
        patch.setattr(behavior_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
        patch.setattr(Path, "__str__", hostile_path_string)
        try:
            _ = author_behavior_programs(
                _programs(), source_context, oracle_context
            )
        except BehaviorProgramError as error:
            caught = error

    assert caught is not None, "context failure lost its typed boundary"
    _expect(caught.__cause__ is failure, "context failure lost original cause")


def test_behavior_context_error_does_not_format_foreign_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Path resolution must retain a typed error with original cause."""
    source, oracle = _trees(tmp_path)
    original_resolve = Path.resolve
    failure = _HostileBehaviorHostError("foreign root")

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            raise failure
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(behavior_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(
        BehaviorProgramError, match="repository resolution failed"
    ) as caught:
        _ = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )
    _expect(caught.value.__cause__ is failure, "host failure cause was lost")


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("mirror", "candidate mirror failed"),
        ("temporary", "temporary root failed"),
        ("snapshot", "candidate tree changed between probes"),
    ],
)
def test_behavior_observation_does_not_format_foreign_host_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    expected: str,
) -> None:
    """Admitted probes cannot run formatter hooks from filesystem faults."""
    authored, source, _ = _authored(tmp_path)
    failure = (
        _HostileBehaviorTreeError("foreign snapshot")
        if operation == "snapshot"
        else _HostileBehaviorHostError("foreign host")
    )
    if operation == "mirror":

        def fail_copy(
            source_root: Path, destination: Path, *, symlinks: bool = False
        ) -> Path:
            _ = source_root, destination, symlinks
            raise failure

        monkeypatch.setattr(behavior_module, "_NATIVE_COPYTREE", fail_copy)
    elif operation == "temporary":

        def fail_temporary(*, prefix: str) -> tempfile.TemporaryDirectory[str]:
            _ = prefix
            raise failure

        monkeypatch.setattr(
            behavior_module, "_NATIVE_TEMPORARY_DIRECTORY", fail_temporary
        )
    else:
        original_snapshot = cast(
            "Callable[[Path], TreeSnapshot]",
            vars(behavior_module)["snapshot_tree"],
        )

        def fail_snapshot(path: Path) -> TreeSnapshot:
            if path == source:
                raise failure
            return original_snapshot(path)

        monkeypatch.setattr(behavior_module, "snapshot_tree", fail_snapshot)

    with pytest.raises(ProbeExecutionError, match=expected) as caught:
        _ = observe_behavior_programs(authored, _context(source, tmp_path))
    _expect(caught.value.__cause__ is failure, "original host cause was lost")
    _expect(
        (source / "identity.txt").read_bytes() == _STABLE_IDENTITY_BYTES,
        "a hostile observation changed the original source",
    )


def test_behavior_authoring_does_not_format_foreign_probe_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cross-stage source rechecks cannot invoke foreign error formatters."""
    source, oracle = _trees(tmp_path)
    original = cast(
        "Callable[[Path], TreeSnapshot]",
        vars(behavior_module)["_snapshot_observed_source"],
    )
    reads = 0
    failure = _HostileBehaviorProbeError("foreign baseline recheck")

    def fail_recheck(path: Path) -> TreeSnapshot:
        nonlocal reads
        if path == source:
            reads += 1
            if reads == 2:
                raise failure
        return original(path)

    monkeypatch.setattr(
        behavior_module, "_snapshot_observed_source", fail_recheck
    )
    with pytest.raises(
        ProbeExecutionError, match="tree changed during authoring"
    ) as caught:
        _ = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )
    _expect(caught.value.__cause__ is failure, "recheck cause was lost")


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_context_repository_resolution_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Keep repository resolution failures inside behavior authoring."""
    source, oracle = _trees(tmp_path)
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked behavior repository"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(behavior_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(BehaviorProgramError, match="repository resolution failed"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_context_tool_resolution_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Keep tool resolution failures inside behavior authoring."""
    source, oracle = _trees(tmp_path)
    tool = Path(sys.executable)
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tool:
            message = "blocked behavior tool"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(behavior_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(BehaviorProgramError, match="tool resolution failed"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


@pytest.mark.parametrize("role", ["repository", "tool"])
def test_behavior_authoring_rejects_foreign_resolved_context_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """Foreign Path equality cannot forge matching repository/tool bindings."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    foreign_path = tmp_path / "other-binding"
    oracle_context = ProbeRunContext(
        source_root=oracle,
        repository_root=foreign_path if role == "repository" else tmp_path,
        tools=(
            ((_PYTHON_TOOL, foreign_path),)
            if role == "tool"
            else source_context.tools
        ),
    )
    programs = BehaviorPrograms(
        identity=(_read_program("identity-stable", "identity.txt"),),
        compatibility=(),
        bugs=(),
    )
    native_resolve = Path.resolve

    class ForgedResolvedPath(type(Path())):
        @override
        def __eq__(self, other: object) -> bool:
            _ = other
            return True

    def return_foreign_path(path: Path, *, strict: bool = False) -> Path:
        if path == foreign_path:
            return ForgedResolvedPath(path)
        return native_resolve(path, strict=strict)

    monkeypatch.setattr(behavior_module, "_NATIVE_PATH_RESOLVE", return_foreign_path)
    with pytest.raises(BehaviorProgramError, match="native resolved Path"):
        _ = author_behavior_programs(programs, source_context, oracle_context)


@pytest.mark.parametrize("role", [_REPOSITORY_ROLE, _TOOL_ROLE])
def test_behavior_authoring_ignores_late_path_equality_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """A late Path equality hook cannot unify distinct probe bindings."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    other = tmp_path / "unrelated-binding"
    oracle_context = ProbeRunContext(
        source_root=oracle,
        repository_root=other if role == _REPOSITORY_ROLE else tmp_path,
        tools=(
            ((_PYTHON_TOOL, other),)
            if role == _TOOL_ROLE
            else source_context.tools
        ),
    )
    original_equal = Path.__eq__
    base = tmp_path if role == _REPOSITORY_ROLE else Path(sys.executable)
    calls = 0

    def forged_equal(left: Path, right: object) -> bool:
        nonlocal calls
        if isinstance(right, Path) and (
            original_equal(left, base)
            and original_equal(right, other)
            or original_equal(left, other)
            and original_equal(right, base)
        ):
            calls += 1
            return True
        return original_equal(left, right)

    def unexpected_execution(*_args: object) -> tuple[ProbeTranscript, ...]:
        del _args
        raise AssertionError("mismatched context reached probe execution")

    monkeypatch.setattr(
        behavior_module, "run_probe_programs", unexpected_execution
    )
    with monkeypatch.context() as patched:
        patched.setattr(Path, "__eq__", forged_equal)
        with pytest.raises(BehaviorProgramError, match="same tool bindings"):
            _ = author_behavior_programs(
                _programs(), source_context, oracle_context
            )
    assert calls == 0, "mutable Path equality influenced context admission"


@pytest.mark.parametrize("role", [_REPOSITORY_ROLE, _TOOL_ROLE])
def test_behavior_authoring_ignores_late_realpath_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """Late host path hooks must not hide different authoring bindings."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    other = tmp_path / "different-binding"
    oracle_context = ProbeRunContext(
        source_root=oracle,
        repository_root=other if role == _REPOSITORY_ROLE else tmp_path,
        tools=(
            ((_PYTHON_TOOL, other),)
            if role == _TOOL_ROLE
            else source_context.tools
        ),
    )
    disguised = tmp_path if role == _REPOSITORY_ROLE else Path(sys.executable)
    native_realpath = os.path.realpath
    calls = 0

    def forged_realpath(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        strict: bool = False,
    ) -> str:
        nonlocal calls
        if os.fspath(path) == os.fspath(other):
            calls += 1
            return str(disguised)
        return os.fsdecode(native_realpath(path, strict=strict))

    def unexpected_execution(*_args: object) -> tuple[ProbeTranscript, ...]:
        del _args
        raise AssertionError("mismatched context reached probe execution")

    monkeypatch.setattr(
        behavior_module, "run_probe_programs", unexpected_execution
    )
    with monkeypatch.context() as patched:
        patched.setattr(os.path, "realpath", forged_realpath)
        with pytest.raises(BehaviorProgramError, match="same tool bindings"):
            _ = author_behavior_programs(
                _programs(), source_context, oracle_context
            )
    assert calls == 0, "context resolution consulted late realpath hook"


@pytest.mark.parametrize("role", [_REPOSITORY_ROLE, _TOOL_ROLE])
def test_behavior_authoring_rejects_forged_native_context_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """A post-import host hook cannot hide distinct baseline tool bindings."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    other = tmp_path / "unrelated-binding"
    oracle_context = ProbeRunContext(
        source_root=oracle,
        repository_root=other if role == _REPOSITORY_ROLE else tmp_path,
        tools=(
            ((_PYTHON_TOOL, other),)
            if role == _TOOL_ROLE
            else source_context.tools
        ),
    )
    original_resolve = Path.resolve
    disguised = tmp_path if role == _REPOSITORY_ROLE else Path(sys.executable)

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == other:
            return original_resolve(disguised, strict=strict)
        return original_resolve(path, strict=strict)

    def unexpected_execution(*_args: object) -> tuple[ProbeTranscript, ...]:
        del _args
        message = "mismatched context reached probe execution"
        raise AssertionError(message)

    monkeypatch.setattr(Path, "resolve", forged_resolve)
    monkeypatch.setattr(
        behavior_module, "run_probe_programs", unexpected_execution
    )
    with pytest.raises(BehaviorProgramError, match="same tool bindings"):
        _ = author_behavior_programs(
            _programs(), source_context, oracle_context
        )


def test_behavior_program_records_reject_foreign_mutable_inputs() -> None:
    """Validate metadata before dereferencing program records."""
    program = _read_program("identity", "identity.txt")
    with pytest.raises(BehaviorProgramError, match="exact ProbeProgram"):
        _ = BugProgram(cast("ProbeProgram", object()), "fix")
    with pytest.raises(BehaviorProgramError, match="correction identifier"):
        _ = BugProgram(program, cast("str", object()))
    with pytest.raises(BehaviorProgramError, match="immutable tuple"):
        _ = BehaviorPrograms(
            identity=cast(
                "tuple[ProbeProgram, ...]",
                cast("object", [program]),
            ),
            compatibility=(),
            bugs=(),
        )
    with pytest.raises(BehaviorProgramError, match="foreign probe program"):
        _ = BehaviorPrograms(
            identity=(cast("ProbeProgram", object()),),
            compatibility=(),
            bugs=(),
        )
    with pytest.raises(BehaviorProgramError, match="foreign bug record"):
        _ = BehaviorPrograms(
            identity=(program,),
            compatibility=(),
            bugs=(cast("BugProgram", object()),),
        )


@pytest.mark.parametrize("invalid", ["fix\x00bug", "fix" + chr(0xD800)])
def test_correction_identifiers_must_be_portable_utf8(invalid: str) -> None:
    """Bug correction labels must remain portable before authoring."""
    program = _read_program("historical-bug", "bug-state.txt")
    with pytest.raises(BehaviorProgramError, match="correction identifier"):
        _ = BugProgram(program, invalid)
    with pytest.raises(BehaviorProgramError, match="correction identifier"):
        _ = AuthoredBugProgram(program, invalid, b"present", b"fixed")


def test_authored_behavior_records_reject_foreign_incoherent_inputs(
    tmp_path: Path,
) -> None:
    """Reject direct authored records that bypass profile coherence."""
    program = _read_program("identity-stable", "identity.txt")
    with pytest.raises(BehaviorProgramError, match="exact ProbeProgram"):
        _ = AuthoredBugProgram(
            cast("ProbeProgram", object()),
            "fix",
            b"present",
            b"fixed",
        )
    with pytest.raises(BehaviorProgramError, match="non-empty exact bytes"):
        _ = AuthoredBugProgram(
            program,
            "fix",
            cast("bytes", cast("object", bytearray(b"present"))),
            b"fixed",
        )
    with pytest.raises(BehaviorProgramError, match="distinguish"):
        _ = AuthoredBugProgram(program, "fix", b"same", b"same")

    authored, _, _ = _authored(tmp_path)
    with pytest.raises(BehaviorProgramError, match="exact BehaviorProfile"):
        _ = AuthoredBehaviorPrograms(
            profile=cast("BehaviorProfile", object()),
            identity=authored.identity,
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )
    with pytest.raises(BehaviorProgramError, match="immutable tuple"):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=cast(
                "tuple[ProbeProgram, ...]",
                cast("object", list(authored.identity)),
            ),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )
    with pytest.raises(
        BehaviorProgramError,
        match="do not match behavior profile",
    ):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=(_read_program("other", "identity.txt"),),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )


@pytest.mark.parametrize("location", ["bug", "identity"])
def test_behavior_programs_reject_late_type_spoofed_programs(
    monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    """Reject a forged consumer program before accessing its commands."""
    foreign = object()
    program = cast("ProbeProgram", foreign)
    native_type = type
    calls = 0

    def spoof_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return ProbeProgram
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", spoof_type)
        try:
            if location == "bug":
                _ = BugProgram(program, "fix-forged-program")
            else:
                _ = BehaviorPrograms((program,), (), ())
        except BehaviorProgramError:
            rejected = True
    assert rejected, "foreign behavior program was admitted"
    assert calls == 0, "late type hook was consulted during admission"


def test_behavior_programs_reject_late_tuple_alias_for_mutable_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable identity group must not become authenticated probe metadata."""
    identity = [_read_program("identity", "identity.txt")]
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        try:
            _ = BehaviorPrograms(
                identity=cast(
                    "tuple[ProbeProgram, ...]", cast("object", identity)
                ),
                compatibility=cast(
                    "tuple[ProbeProgram, ...]", cast("object", [])
                ),
                bugs=cast("tuple[BugProgram, ...]", cast("object", [])),
            )
        except BehaviorProgramError:
            rejected = True
    assert rejected, "late tuple alias admitted mutable behavior groups"


def test_authored_bug_rejects_late_bytes_alias_for_mutable_digests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer type aliases cannot certify mutable bug baseline digests."""
    program = _read_program("bug", "bug.txt")
    present = bytearray(b"present")
    fixed = bytearray(b"fixed")
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            _ = AuthoredBugProgram(
                program=program,
                correction_id="fix",
                present_digest=cast("bytes", cast("object", present)),
                fixed_digest=cast("bytes", cast("object", fixed)),
            )
        except BehaviorProgramError:
            rejected = True
    assert rejected, "late bytes alias admitted mutable bug digests"


class _ForeignCorrectionLabel:
    """Non-string correction ID with potentially side-effectful hooks."""

    def __init__(self) -> None:
        self.calls: int = 0

    def __contains__(self, _item: object) -> bool:
        self.calls += 1
        return False

    def encode(self, _encoding: str) -> bytes:
        self.calls += 1
        return b"fix"


def test_bug_program_rejects_late_str_alias_before_foreign_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer string alias cannot execute a foreign correction ID."""
    foreign = _ForeignCorrectionLabel()
    program = _read_program("bug", "bug.txt")
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignCorrectionLabel)
        try:
            _ = BugProgram(program, cast("str", cast("object", foreign)))
        except BehaviorProgramError:
            rejected = True
    assert rejected, "late str alias admitted foreign correction ID"
    assert foreign.calls == 0, "foreign correction hooks executed before rejection"


@pytest.mark.parametrize("kind", ["program", "correction"])
def test_behavior_programs_reject_late_len_spoof_of_duplicates(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A host length override cannot suppress duplicate evidence policy."""
    identity = (_read_program("same-id", "identity.txt"),)
    compatibility: tuple[ProbeProgram, ...] = ()
    bugs: tuple[BugProgram, ...] = ()
    repeated = ("same-id", "same-id")
    if kind == "program":
        compatibility = (_read_program("same-id", "identity.txt"),)
    else:
        bugs = (
            BugProgram(_read_program("bug-a", "bug.txt"), "same-id"),
            BugProgram(_read_program("bug-b", "bug.txt"), "same-id"),
        )
    native_len = builtins.len
    calls = 0

    def spoof_len(value: object) -> int:
        nonlocal calls
        if type(value) is tuple and value == repeated:
            calls += 1
            return 1
        return native_len(cast("Sized", value))

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", spoof_len)
        try:
            _ = BehaviorPrograms(identity, compatibility, bugs)
        except BehaviorProgramError:
            rejected = True
    assert rejected, f"late len spoof admitted duplicate {kind} IDs"
    assert calls == 0, "host len override was consulted for evidence"


def test_valid_behavior_programs_resist_late_type_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admitted native records remain usable after consumer type aliases."""
    program = _read_program("identity", "identity.txt")
    valid = BehaviorPrograms((program,), (), ())
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        assert BehaviorPrograms((program,), (), ()) == valid
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        _ = AuthoredBugProgram(program, "fix", b"present", b"fixed")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", bytes)
        _ = BugProgram(program, "fix")


@pytest.mark.parametrize("authored", [False, True])
def test_bug_program_selector_rejects_late_any_hook(
    monkeypatch: pytest.MonkeyPatch,
    *,
    authored: bool,
) -> None:
    """Late host truth hooks cannot admit a selector-free bug probe."""
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('unselected')"),
    )
    unselected = ProbeProgram("historical-bug", (command,))

    def construct_after_hook_swap() -> None:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "any", lambda values: True)
            if authored:
                _ = AuthoredBugProgram(unselected, "fix", b"old", b"new")
            else:
                _ = BugProgram(unselected, "fix")

    with pytest.raises(BehaviorProgramError, match="selected observation"):
        construct_after_hook_swap()


def test_behavior_programs_reject_late_sort_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A global sorter cannot approve noncanonical program ordering."""
    programs = (
        _read_program("identity-z", "identity.txt"),
        _read_program("identity-a", "identity.txt"),
    )
    native_sorted = builtins.sorted

    def forged_sorted(values: set[str]) -> list[str]:
        observed = tuple(values)
        if frozenset(observed) == frozenset(("identity-a", "identity-z")):
            return ["identity-z", "identity-a"]
        return list(native_sorted(observed))

    def construct_after_hook_swap() -> BehaviorPrograms:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "sorted", forged_sorted)
            return BehaviorPrograms(
                identity=programs, compatibility=(), bugs=()
            )

    with pytest.raises(BehaviorProgramError, match="unique sorted identifiers"):
        _ = construct_after_hook_swap()


@pytest.mark.parametrize("duplicate_kind", ["probe", "correction"])
def test_behavior_programs_reject_late_set_hook(
    monkeypatch: pytest.MonkeyPatch,
    duplicate_kind: str,
) -> None:
    """A global set shim cannot approve duplicate program or correction IDs."""
    identity = (_read_program("identity-a", "identity.txt"),)
    compatibility: tuple[ProbeProgram, ...] = ()
    bugs: tuple[BugProgram, ...] = ()
    if duplicate_kind == "probe":
        compatibility = (_read_program("identity-a", "identity.txt"),)
        message = "globally unique"
    else:
        bugs = (
            BugProgram(_read_program("bug-a", "bug.txt"), "shared-fix"),
            BugProgram(_read_program("bug-b", "bug.txt"), "shared-fix"),
        )
        message = "correction identifiers must be unique"

    def construct_after_hook_swap() -> BehaviorPrograms:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "set", lambda values: list(values))
            return BehaviorPrograms(
                identity=identity,
                compatibility=compatibility,
                bugs=bugs,
            )

    with pytest.raises(BehaviorProgramError, match=message):
        _ = construct_after_hook_swap()


def test_identity_and_bug_programs_require_selected_transcripts(
    tmp_path: Path,
) -> None:
    """Admit transcript selectors before any authoring process executes."""
    unselected = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('unselected output')"),
    )
    identity = ProbeProgram("identity-stable", (unselected,))
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = BehaviorPrograms(identity=(identity,), compatibility=(), bugs=())

    bug = ProbeProgram("historical-bug", (unselected,))
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = BehaviorPrograms(
            identity=(_read_program("identity-stable", "identity.txt"),),
            compatibility=(),
            bugs=(BugProgram(bug, "fix-historical-bug"),),
        )
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = AuthoredBugProgram(bug, "fix-historical-bug", b"present", b"fixed")

    authored, _, _ = _authored(tmp_path)
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=(identity,),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )

    _ = BehaviorPrograms(
        identity=(_read_program("identity-stable", "identity.txt"),),
        compatibility=(ProbeProgram("runtime-capability", (unselected,)),),
        bugs=(),
    )
    exit_only = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "raise SystemExit(7)"),
        digest_exit_code=True,
        expected_exit_code=None,
    )
    _ = BehaviorPrograms(
        identity=(ProbeProgram("exit-identity", (exit_only,)),),
        compatibility=(),
        bugs=(
            BugProgram(
                ProbeProgram("exit-bug", (exit_only,)),
                "fix-exit-bug",
            ),
        ),
    )


def test_behavior_program_apis_reject_foreign_records_before_execution(
    tmp_path: Path,
) -> None:
    """Validate public records before authoring or observation dereference."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    oracle_context = _context(oracle, tmp_path)
    with pytest.raises(BehaviorProgramError, match="exact BehaviorPrograms"):
        _ = author_behavior_programs(
            cast("BehaviorPrograms", object()),
            source_context,
            oracle_context,
        )
    with pytest.raises(BehaviorProgramError, match="exact ProbeRunContext"):
        _ = author_behavior_programs(
            _programs(),
            cast("ProbeRunContext", object()),
            oracle_context,
        )

    authored = author_behavior_programs(_programs(), source_context, oracle_context)
    with pytest.raises(
        BehaviorProgramError,
        match="exact AuthoredBehaviorPrograms",
    ):
        _ = observe_behavior_programs(
            cast("AuthoredBehaviorPrograms", object()),
            source_context,
        )
    with pytest.raises(BehaviorProgramError, match="exact ProbeRunContext"):
        _ = observe_behavior_programs(
            authored,
            cast("ProbeRunContext", object()),
        )


@pytest.mark.parametrize("mutate_after_source", [False, True])
@pytest.mark.parametrize("mutate_source", [False, True])
def test_authoring_rejects_cross_tree_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    mutate_after_source: bool,
    mutate_source: bool,
) -> None:
    """Neither source nor oracle can drift between authoring probe batches."""
    source, oracle = _trees(tmp_path)
    changed = source if mutate_source else oracle
    phase_root = source if mutate_after_source else oracle

    def modifying_batch(
        programs: tuple[ProbeProgram, ...], context: ProbeRunContext
    ) -> tuple[ProbeTranscript, ...]:
        transcripts = run_probe_programs(programs, context)
        if context.source_root == phase_root:
            _write(changed, "identity.txt", b"changed after probe")
        return transcripts

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_programs", modifying_batch
    )
    with pytest.raises(ProbeExecutionError, match="changed during authoring"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


def test_failed_oracle_authoring_still_detects_source_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed oracle probe cannot suppress source-drift diagnostics."""
    source, oracle = _trees(tmp_path)

    def failing_oracle(
        programs: tuple[ProbeProgram, ...], context: ProbeRunContext
    ) -> tuple[ProbeTranscript, ...]:
        if context.source_root == oracle:
            _write(source, "identity.txt", b"changed before failed oracle")
            message = "synthetic oracle execution error"
            raise ProbeExecutionError(message)
        return run_probe_programs(programs, context)

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_programs", failing_oracle
    )
    with pytest.raises(ProbeExecutionError, match="changed during authoring"):
        _ = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )


def test_identity_only_authoring_does_not_require_oracle_tree(
    tmp_path: Path,
) -> None:
    """Without a bug baseline, oracle files are not required."""
    source, _ = _trees(tmp_path)
    missing_oracle = tmp_path / "missing-oracle"
    identity = _read_program("identity-stable", "identity.txt")
    programs = BehaviorPrograms(identity=(identity,), compatibility=(), bugs=())
    authored = author_behavior_programs(
        programs,
        _context(source, tmp_path),
        _context(missing_oracle, tmp_path),
    )
    _expect(authored.profile.identity[0].probe_id == identity.probe_id, "ID drift")
    _expect(not authored.bugs, "identity-only authoring gained a bug baseline")


def test_authoring_derives_identity_and_distinct_bug_baselines(
    tmp_path: Path,
) -> None:
    """Generate source identity plus present/fixed bug transcript baselines."""
    authored, _, _ = _authored(tmp_path)
    bug = authored.bugs[0]

    _expect(bool(authored.profile.identity[0].expected_digest), "identity is empty")
    _expect(bug.present_digest != bug.fixed_digest, "bug baselines are ambiguous")


def test_original_bug_state_routes_correction_to_apply(tmp_path: Path) -> None:
    """Classify a source-like candidate as defect present."""
    authored, source, _ = _authored(tmp_path)
    evidence = evaluate_behavior_programs(
        authored,
        _context(source, tmp_path),
        minimum_similarity=0.80,
    )

    _expect(evidence.admitted, "source behavior was rejected")
    _expect(
        evidence.corrections_to_apply == ("fix-historical-bug",),
        "present bug did not route correction",
    )


def test_oracle_bug_state_routes_correction_to_skip(tmp_path: Path) -> None:
    """Classify an already-corrected candidate as fixed without rejection."""
    authored, _, oracle = _authored(tmp_path)
    evidence = evaluate_behavior_programs(
        authored,
        _context(oracle, tmp_path),
        minimum_similarity=0.80,
    )

    _expect(evidence.admitted, "fixed behavior was rejected")
    _expect(
        evidence.corrections_to_skip == ("fix-historical-bug",),
        "fixed bug did not skip correction",
    )


def test_unknown_bug_transcript_fails_closed(tmp_path: Path) -> None:
    """Classify behavior matching neither source nor oracle as unknown."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-unknown"
    for name in ("identity.txt", "runtime.flag"):
        _write(candidate, name, (source / name).read_bytes())
    _write(candidate, "bug-state.txt", b"third-state")

    observations = observe_behavior_programs(
        authored,
        _context(candidate, tmp_path),
    )
    _expect(observations.bugs[0].state is BugState.UNKNOWN, "bug was guessed")
    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(not evidence.admitted, "unknown bug state was admitted")


@pytest.mark.parametrize(
    "changed_after",
    ["identity-stable", "runtime-capability", "historical-bug"],
)
def test_observation_rejects_source_changed_between_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_after: str,
) -> None:
    """Identity from one source must not combine with a later bug state."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "switching-source"
    for name in ("identity.txt", "runtime.flag", "bug-state.txt"):
        _write(candidate, name, (source / name).read_bytes())

    def switching_run(
        program: ProbeProgram, run_context: ProbeRunContext
    ) -> ProbeTranscript:
        transcript = run_probe_program(program, run_context)
        if program.probe_id == changed_after:
            _write(candidate, "bug-state.txt", b"fixed")
        return transcript

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_program", switching_run
    )
    with pytest.raises(ProbeExecutionError, match="changed between probes"):
        _ = evaluate_behavior_programs(
            authored,
            _context(candidate, tmp_path),
            minimum_similarity=0.80,
        )


def test_observation_keeps_one_source_view_across_identity_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A flip-and-restore candidate cannot blend separate identity snapshots."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    candidate = tmp_path / "candidate"
    for root in (source, oracle):
        _write(root, "first.txt", b"first")
        _write(root, "second.txt", b"second")
    _write(candidate, "first.txt", b"first")
    _write(candidate, "second.txt", _CHANGED_SECOND_BYTES)
    programs = BehaviorPrograms(
        identity=(
            _read_program(_IDENTITY_A, "first.txt"),
            _read_program(_IDENTITY_B, "second.txt"),
        ),
        compatibility=(),
        bugs=(),
    )
    authored = author_behavior_programs(
        programs, _context(source, tmp_path), _context(oracle, tmp_path)
    )

    def flip_during_identity(
        program: ProbeProgram, run_context: ProbeRunContext
    ) -> ProbeTranscript:
        transcript = run_probe_program(program, run_context)
        if program.probe_id == _IDENTITY_A:
            _write(candidate, "second.txt", b"second")
        elif program.probe_id == _IDENTITY_B:
            _write(candidate, "second.txt", _CHANGED_SECOND_BYTES)
        return transcript

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_program",
        flip_during_identity,
    )
    evidence = evaluate_behavior_programs(
        authored, _context(candidate, tmp_path), minimum_similarity=1.0
    )
    _expect(not evidence.admitted, "interleaved source versions were admitted")
    _expect(
        (candidate / "second.txt").read_bytes() == _CHANGED_SECOND_BYTES,
        "candidate was not restored by interleaving fixture",
    )


def test_observation_rejects_copy_time_mirror_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed copied byte tree is rejected before any probe executes."""
    authored, source, _ = _authored(tmp_path)
    copied_tree = shutil.copytree

    def changed_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        copied = copied_tree(source_root, destination, symlinks=symlinks)
        _write(copied, "identity.txt", b"drift during copy")
        return copied

    monkeypatch.setattr(behavior_module, "_NATIVE_COPYTREE", changed_copy)
    with pytest.raises(ProbeExecutionError, match="changed while creating mirror"):
        _ = observe_behavior_programs(authored, _context(source, tmp_path))
    _expect(
        (source / "identity.txt").read_bytes() == _STABLE_IDENTITY_BYTES,
        "authoring source changed during mirror rejection",
    )


@pytest.mark.parametrize(
    "failure_type",
    [
        PermissionError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        OverflowError,
    ],
)
def test_observation_mirror_creation_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Host mirror-copy failures cannot leak outside the probe boundary."""
    authored, source, _ = _authored(tmp_path)

    def denied_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        del source_root, destination, symlinks
        message = "copytree host failure"
        raise failure_type(message)

    monkeypatch.setattr(behavior_module, "_NATIVE_COPYTREE", denied_copy)
    with pytest.raises(ProbeExecutionError, match="candidate mirror failed"):
        _ = observe_behavior_programs(authored, _context(source, tmp_path))
    _expect(
        (source / "identity.txt").read_bytes() == _STABLE_IDENTITY_BYTES,
        "mirror rejection changed the source",
    )


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_observation_temporary_root_creation_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Probe observation cannot leak temp-root initialization errors."""
    authored, source, _ = _authored(tmp_path)

    def denied_temporary_root(*, prefix: str) -> tempfile.TemporaryDirectory[str]:
        del prefix
        message = "temporary root host failure"
        raise failure_type(message)

    monkeypatch.setattr(
        behavior_module, "_NATIVE_TEMPORARY_DIRECTORY", denied_temporary_root
    )
    with pytest.raises(ProbeExecutionError, match="temporary root failed"):
        _ = observe_behavior_programs(authored, _context(source, tmp_path))


def test_failed_compatibility_program_rejects_candidate(tmp_path: Path) -> None:
    """Turn a failed portable precondition program into behavior rejection."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-incompatible"
    _write(candidate, "identity.txt", (source / "identity.txt").read_bytes())
    _write(candidate, "bug-state.txt", (source / "bug-state.txt").read_bytes())

    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(not evidence.admitted, "missing compatibility capability was admitted")


def test_changed_identity_program_output_reduces_similarity(
    tmp_path: Path,
) -> None:
    """Derive identity mismatch from executable probe output."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-different"
    _write(candidate, "identity.txt", b"different")
    _write(candidate, "runtime.flag", b"available")
    _write(candidate, "bug-state.txt", (source / "bug-state.txt").read_bytes())

    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(not evidence.admitted, "changed identity behavior was admitted")
    _expect(
        math.isclose(evidence.similarity, 0.0),
        "identity mismatch score changed",
    )


def test_bug_probe_must_distinguish_source_from_oracle(tmp_path: Path) -> None:
    """Reject a bug program that cannot tell defect presence from correction."""
    source, oracle = _trees(tmp_path)
    _write(oracle, "bug-state.txt", b"present")

    with pytest.raises(BehaviorProgramError, match="cannot distinguish"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


@pytest.mark.parametrize("receipt_kind", ["none", "false", "other", "foreign-path"])
def test_observation_mirror_requires_native_copy_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt_kind: str
) -> None:
    """A mirror cannot be authorized by a non-native copytree receipt."""
    authored, source, _ = _authored(tmp_path)
    native_copy = shutil.copytree

    class ForeignReceipt(type(Path())):
        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign mirror receipt equality evaluated")

        @override
        def __hash__(self) -> int:
            return Path.__hash__(self)

    def forged_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> object:
        _ = native_copy(source_root, destination, symlinks=symlinks)
        if receipt_kind == "none":
            return None
        if receipt_kind == "false":
            return False
        if receipt_kind == "other":
            return destination.parent / "other"
        return ForeignReceipt(destination)

    monkeypatch.setattr(behavior_module, "_NATIVE_COPYTREE", forged_copy)
    with pytest.raises(ProbeExecutionError, match="non-native completion"):
        _ = observe_behavior_programs(authored, _context(source, tmp_path))
    _expect(
        (source / "identity.txt").read_bytes() == _STABLE_IDENTITY_BYTES,
        "foreign mirror receipt modified authoring source",
    )


@pytest.mark.parametrize("wrong_completion", [False, True])
def test_mirror_copy_completion_ignores_late_path_equality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wrong_completion: bool
) -> None:
    """Mirror copy attestation cannot be forged or denied by Path equality."""
    source, _ = _trees(tmp_path)
    context = _context(source, tmp_path)
    admitted = behavior_module._snapshot_observed_source(source)
    mirror = tmp_path / "mirror"
    forged_receipt = tmp_path / "other-mirror"
    original_copy = shutil.copytree
    original_equal = Path.__eq__
    calls = 0

    def forged_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        _ = original_copy(source_root, destination, symlinks=symlinks)
        return forged_receipt if wrong_completion else destination

    def forged_equal(left: Path, right: object) -> bool:
        nonlocal calls
        if left is forged_receipt and right is mirror:
            calls += 1
            return True
        if left is mirror and right is mirror:
            calls += 1
            return False
        return original_equal(left, right)

    with monkeypatch.context() as patched:
        patched.setattr(behavior_module, "_NATIVE_COPYTREE", forged_copy)
        patched.setattr(Path, "__eq__", forged_equal)
        if wrong_completion:
            with pytest.raises(
                ProbeExecutionError, match="non-native completion"
            ):
                _ = behavior_module._admit_observation_mirror(
                    context, mirror, admitted
                )
        else:
            verified = behavior_module._admit_observation_mirror(
                context, mirror, admitted
            )
            assert verified.source_root is mirror
    assert calls == 0, "mirror attestation consulted late path equality"
    assert mirror.joinpath("identity.txt").read_bytes() == b"stable"


@pytest.mark.parametrize(
    "mutation", ["missing-compatibility", "duplicate", "extra", "foreign"]
)
def test_authoring_rejects_incomplete_or_foreign_transcript_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A transcript map must reflect every requested policy probe once."""
    source, oracle = _trees(tmp_path)
    native_run = run_probe_programs
    source_batch_mutated = False

    def misreport_batch(
        programs: tuple[ProbeProgram, ...], context: ProbeRunContext
    ) -> tuple[ProbeTranscript, ...]:
        nonlocal source_batch_mutated
        reported = native_run(programs, context)
        if context.source_root != source:
            return reported
        source_batch_mutated = True
        if mutation == "missing-compatibility":
            return tuple(
                item for item in reported if item.probe_id != "runtime-capability"
            )
        if mutation == "duplicate":
            return (*reported, reported[0])
        if mutation == "extra":
            return (*reported, ProbeTranscript("not-requested", bytes(32), 1))
        foreign = SimpleNamespace(
            probe_id=reported[0].probe_id,
            digest=reported[0].digest,
            digested_commands=reported[0].digested_commands,
        )
        return (cast("ProbeTranscript", cast("object", foreign)), *reported[1:])

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_programs", misreport_batch
    )
    with pytest.raises(BehaviorProgramError, match="transcript"):
        _ = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )
    _expect(source_batch_mutated, "the transcript mutation did not run")


def test_behavior_mirror_ignores_late_shutil_copytree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer cannot replace the host source-mirror copier."""
    source, _ = _trees(tmp_path)
    context = _context(source, tmp_path)
    admitted = behavior_module._snapshot_observed_source(source)
    mirror = tmp_path / "isolated-mirror"
    calls = 0

    def forged_copy(*args: object, **kwargs: object) -> Path:
        nonlocal calls
        del args, kwargs
        calls += 1
        raise AssertionError("consumer source mirror copier executed")

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "copytree", forged_copy)
        mirrored = behavior_module._admit_observation_mirror(
            context, mirror, admitted
        )
    assert mirrored.source_root == mirror
    assert mirrored.enforce_source_immutable
    assert mirror.joinpath("identity.txt").read_bytes() == b"stable"
    assert calls == 0, "consumer mirror copier received host authority"


def test_behavior_observation_root_ignores_late_tempfile_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admitted mirror must not use a swapped temporary root provider."""
    calls = 0

    def forged_temporary(*, prefix: str) -> tempfile.TemporaryDirectory[str]:
        nonlocal calls
        del prefix
        calls += 1
        raise AssertionError("consumer temporary directory provider executed")

    with monkeypatch.context() as patch:
        patch.setattr(tempfile, "TemporaryDirectory", forged_temporary)
        with behavior_module._temporary_observation_root() as root:
            assert Path(root).is_dir()
    assert calls == 0, "consumer temporary root provider was invoked"


@pytest.mark.parametrize(
    "record_type",
    [BugProgram, BehaviorPrograms, AuthoredBugProgram, AuthoredBehaviorPrograms],
)
def test_behavior_record_constructor_ignores_late_post_init_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record_type: type[object]
) -> None:
    """Original validation cannot be skipped by a late dataclass hook."""
    good_program = _read_program("identity-stable", "identity.txt")
    cases: dict[type[object], tuple[dict[str, object], str]] = {
        BugProgram: (
            {"program": object(), "correction_id": "fix"},
            "exact ProbeProgram",
        ),
        BehaviorPrograms: (
            {"identity": [good_program], "compatibility": (), "bugs": ()},
            "immutable tuple",
        ),
        AuthoredBugProgram: (
            {
                "program": object(),
                "correction_id": "fix",
                "present_digest": b"a",
                "fixed_digest": b"b",
            },
            "exact ProbeProgram",
        ),
        AuthoredBehaviorPrograms: (
            {"profile": object(), "identity": (), "compatibility": (), "bugs": ()},
            "exact BehaviorProfile",
        ),
    }
    arguments, diagnostic = cases[record_type]
    calls = 0

    def skip_validation(_value: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(record_type, "__post_init__", skip_validation)
        with pytest.raises(BehaviorProgramError, match=diagnostic):
            _ = record_type(**arguments)
    assert calls == 0, "late class hook replaced the original validator"


@pytest.mark.parametrize(
    "record_type",
    [BugProgram, BehaviorPrograms, AuthoredBugProgram, AuthoredBehaviorPrograms],
)
def test_behavior_record_validator_reads_original_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record_type: type[object]
) -> None:
    """A late class descriptor cannot forge a valid stored probe or profile."""
    program = _read_program("identity-stable", "identity.txt")
    valid: object
    field: str
    if record_type is BugProgram:
        valid = BugProgram(program, "fix")
        field = "program"
    elif record_type is BehaviorPrograms:
        valid = BehaviorPrograms((program,), (), ())
        field = "identity"
    elif record_type is AuthoredBugProgram:
        valid = AuthoredBugProgram(program, "fix", b"a", b"b")
        field = "present_digest"
    else:
        valid, _, _ = _authored(tmp_path)
        field = "profile"
    forged = {
        "program": object(),
        "identity": [program],
        "present_digest": bytearray(b"a"),
        "profile": object(),
    }[field]
    original = getattr(valid, field)
    object.__setattr__(valid, field, forged)
    calls = 0

    def spoof(_self: object) -> object:
        nonlocal calls
        calls += 1
        return original

    with monkeypatch.context() as patched:
        patched.setattr(record_type, field, property(spoof))
        with pytest.raises(BehaviorProgramError):
            validator = cast(
                "Callable[[object], None]", vars(record_type)["__post_init__"]
            )
            validator(valid)
    assert calls == 0, "late class getter spoofed the stored field"


@pytest.mark.parametrize("field", ["identity", "compatibility", "bugs"])
def test_observation_uses_stored_authored_probe_groups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A late class getter cannot omit mandatory observed program groups."""
    authored, source, _oracle = _authored(tmp_path)
    calls = 0

    def hide_group(_value: object) -> tuple[()]:
        nonlocal calls
        calls += 1
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(AuthoredBehaviorPrograms, field, property(hide_group))
        observed = observe_behavior_programs(authored, _context(source, tmp_path))
    assert len(getattr(observed, field)) == 1
    assert calls == 0, "late getter suppressed an authored probe group"


def test_bug_state_uses_stored_authored_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late getter cannot rewrite known present/fixed classification."""
    program = _read_program("historical-bug", "bug-state.txt")
    present = bytes(range(32))
    fixed = bytes(reversed(range(32)))
    authored = AuthoredBugProgram(program, "fix", present, fixed)
    transcript = ProbeTranscript(program.probe_id, present, 1)
    calls = 0

    def forge_present(_value: object) -> bytes:
        nonlocal calls
        calls += 1
        return fixed

    with monkeypatch.context() as patched:
        patched.setattr(AuthoredBugProgram, "present_digest", property(forge_present))
        assert behavior_module._bug_state(authored, transcript) is BugState.PRESENT
    assert calls == 0, "late getter diverted bug state classification"


def test_all_programs_uses_original_groups_and_bug_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer getters cannot shrink requested source/oracle probes."""
    programs = _programs()
    calls = 0

    def hide_group(_value: object) -> tuple[()]:
        nonlocal calls
        calls += 1
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(BehaviorPrograms, "identity", property(hide_group))
        observed = behavior_module._all_programs(programs)
    assert {item.probe_id for item in observed} == {
        "historical-bug",
        "identity-stable",
        "runtime-capability",
    }
    assert calls == 0, "late getter removed a mandatory identity program"


_BEHAVIOR_RECORD_FIELDS: tuple[tuple[type[object], str, object], ...] = (
    (BugProgram, "program", object()),
    (BugProgram, "correction_id", ""),
    (BehaviorPrograms, "identity", []),
    (BehaviorPrograms, "compatibility", []),
    (BehaviorPrograms, "bugs", []),
    (AuthoredBugProgram, "program", object()),
    (AuthoredBugProgram, "correction_id", ""),
    (AuthoredBugProgram, "present_digest", bytearray(b"a")),
    (AuthoredBugProgram, "fixed_digest", b"a"),
    (AuthoredBehaviorPrograms, "profile", object()),
    (AuthoredBehaviorPrograms, "identity", []),
    (AuthoredBehaviorPrograms, "compatibility", []),
    (AuthoredBehaviorPrograms, "bugs", []),
)


def _valid_behavior_record(record_type: type[object], tmp_path: Path) -> object:
    program = _read_program("identity-stable", "identity.txt")
    if record_type is BugProgram:
        return BugProgram(program, "fix")
    if record_type is BehaviorPrograms:
        return BehaviorPrograms((program,), (), ())
    if record_type is AuthoredBugProgram:
        return AuthoredBugProgram(program, "fix", b"a", b"b")
    authored, _, _ = _authored(tmp_path)
    return authored


@pytest.mark.parametrize(("record_type", "field", "invalid"), _BEHAVIOR_RECORD_FIELDS)
def test_behavior_constructor_rejects_forged_field_setter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[object],
    field: str,
    invalid: object,
) -> None:
    """A substituted setter cannot launder an invalid program record."""
    valid = cast(
        "BugProgram | BehaviorPrograms | AuthoredBugProgram | AuthoredBehaviorPrograms",
        _valid_behavior_record(record_type, tmp_path),
    )
    original_slot = record_type.__dict__[field]
    repaired = getattr(valid, field)
    calls = 0

    def sanitize(self: object, _value: object) -> None:
        nonlocal calls
        calls += 1
        original_slot.__set__(self, repaired)

    with monkeypatch.context() as patched:
        patched.setattr(record_type, field, property(fset=sanitize))
        with pytest.raises(BehaviorProgramError):
            _ = replace(valid, **{field: invalid})
    assert calls == 0, "late setter changed trusted behavior program input"


@pytest.mark.parametrize(("record_type", "field", "_"), _BEHAVIOR_RECORD_FIELDS)
def test_behavior_constructor_writes_original_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_type: type[object],
    field: str,
    _: object,
) -> None:
    """Valid program metadata construction never calls late setters."""
    valid = cast(
        "BugProgram | BehaviorPrograms | AuthoredBugProgram | AuthoredBehaviorPrograms",
        _valid_behavior_record(record_type, tmp_path),
    )
    original_field = getattr(valid, field)
    calls = 0

    def forbidden_setter(_self: object, _value: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("behavior constructor invoked foreign setter")

    with monkeypatch.context() as patched:
        patched.setattr(record_type, field, property(fset=forbidden_setter))
        reconstructed = replace(valid, **{field: original_field})
    assert type(reconstructed) is record_type
    assert calls == 0, "valid behavior constructor invoked late setter"


def test_behavior_transcript_map_rejects_late_id_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign transcript cannot spoof a requested probe after construction."""
    expected = _read_program("expected", "identity.txt")
    foreign = ProbeTranscript("foreign", bytes(range(32)), 1)
    calls = 0

    def forged_id(_transcript: object) -> str:
        nonlocal calls
        calls += 1
        return "expected"

    with monkeypatch.context() as patched:
        patched.setattr(ProbeTranscript, "probe_id", property(forged_id))
        with pytest.raises(BehaviorProgramError, match="transcript batch"):
            _ = behavior_module._transcript_map((foreign,), (expected,))
    assert calls == 0, "late transcript ID getter admitted foreign evidence"


@pytest.mark.parametrize("field", ("digest", "digested_commands", "probe_id"))
def test_behavior_digest_reader_uses_original_transcript_slots(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """A late class getter cannot forge transcript hash or selection count."""
    digest = bytes(range(32))
    transcript = ProbeTranscript("identity", digest, 1)
    calls = 0

    def forged(_transcript: object) -> object:
        nonlocal calls
        calls += 1
        return {
            "digest": bytes(reversed(range(32))),
            "digested_commands": 0,
            "probe_id": "foreign",
        }[field]

    with monkeypatch.context() as patched:
        patched.setattr(ProbeTranscript, field, property(forged))
        observed = behavior_module._require_digest(transcript)
    assert observed == digest
    assert calls == 0, f"late transcript {field} getter changed selected digest"


def test_behavior_digest_reader_rejects_hidden_empty_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unselected transcript cannot become identity evidence via a getter."""
    transcript = ProbeTranscript("identity", bytes(range(32)), 0)
    calls = 0

    def forged_count(_transcript: object) -> int:
        nonlocal calls
        calls += 1
        return 1

    with monkeypatch.context() as patched:
        patched.setattr(
            ProbeTranscript, "digested_commands", property(forged_count)
        )
        with pytest.raises(BehaviorProgramError, match="selects no stdout"):
            behavior_module._require_digest(transcript)
    assert calls == 0


def test_behavior_bug_state_uses_original_transcript_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late digest getter cannot classify a present bug as already fixed."""
    program = _read_program("historical-bug", "bug-state.txt")
    present = bytes(range(32))
    fixed = bytes(reversed(range(32)))
    authored = AuthoredBugProgram(program, "fix", present, fixed)
    transcript = ProbeTranscript("historical-bug", present, 1)
    calls = 0

    def forged_digest(_transcript: object) -> bytes:
        nonlocal calls
        calls += 1
        return fixed

    with monkeypatch.context() as patched:
        patched.setattr(ProbeTranscript, "digest", property(forged_digest))
        observed = behavior_module._bug_state(authored, transcript)
    assert observed is BugState.PRESENT
    assert calls == 0


def test_behavior_program_ids_ignore_late_program_id_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late program getter cannot redefine the selected probe identity."""
    program = _read_program("original", "identity.txt")
    calls = 0

    def forged_id(_program: object) -> str:
        nonlocal calls
        calls += 1
        return "substituted"

    with monkeypatch.context() as patched:
        patched.setattr(ProbeProgram, "probe_id", property(forged_id))
        observed = behavior_module._program_ids((program,))
    assert observed == ("original",)
    assert calls == 0


def _isolate_late_receipt_new(test_name: str, record_type: type[object]) -> bool:
    """Do not poison CPython's cached native __new__ slots in other tests."""
    if os.environ.get("_DIFF_BEHAVIOR_RECEIPT_CHILD") == "1":
        return False
    environment = os.environ.copy()
    environment["_DIFF_BEHAVIOR_RECEIPT_CHILD"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        [*sys.path, "tests/function/algorithms/domain/diff"]
    )
    node = f"{__file__}::{test_name}[{record_type.__name__}-__new__]"
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", node, "-q"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return True


@pytest.mark.parametrize("hook", ["__init__", "__new__"])
@pytest.mark.parametrize(
    "record_type",
    [
        IdentityProbe,
        CompatibilityProbe,
        BugProbe,
        BehaviorProfile,
        AuthoredBugProgram,
        AuthoredBehaviorPrograms,
    ],
)
def test_behavior_authoring_ignores_late_receipt_constructors(
    tmp_path: Path, hook: str, record_type: type[object]
) -> None:
    """A completed source/oracle probe must not forge authored evidence."""
    if hook == "__new__" and _isolate_late_receipt_new(
        "test_behavior_authoring_ignores_late_receipt_constructors", record_type
    ):
        return
    source, oracle = _trees(tmp_path)
    original_run = run_probe_programs
    calls = 0
    installed = False

    def forbidden_constructor(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late authored receipt constructor executed")

    with ExitStack() as stack:

        def run_then_replace(
            programs: tuple[ProbeProgram, ...], context: ProbeRunContext
        ) -> tuple[ProbeTranscript, ...]:
            nonlocal installed
            results = original_run(programs, context)
            if context.source_root == oracle and not installed:
                _ = stack.enter_context(
                    patch.object(record_type, hook, forbidden_constructor)
                )
                installed = True
            return results

        _ = stack.enter_context(
            patch.object(behavior_module, "run_probe_programs", run_then_replace)
        )
        authored = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )
        assert authored.profile.identity[0].probe_id == "identity-stable"
        assert authored.bugs[0].present_digest != authored.bugs[0].fixed_digest
    assert installed and calls == 0


@pytest.mark.parametrize("hook", ["__init__", "__new__"])
@pytest.mark.parametrize(
    "record_type",
    [
        IdentityObservation,
        CompatibilityObservation,
        BugObservation,
        BehaviorObservations,
    ],
)
def test_behavior_observation_ignores_late_receipt_constructors(
    tmp_path: Path, hook: str, record_type: type[object]
) -> None:
    """An executed probe cannot swap observations used for admission."""
    if hook == "__new__" and _isolate_late_receipt_new(
        "test_behavior_observation_ignores_late_receipt_constructors", record_type
    ):
        return
    authored, source, _ = _authored(tmp_path)
    original_run = run_probe_program
    calls = 0
    installed = False

    def forbidden_constructor(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late observation receipt constructor executed")

    with ExitStack() as stack:

        def run_then_replace(
            program: ProbeProgram, context: ProbeRunContext
        ) -> ProbeTranscript:
            nonlocal installed
            result = original_run(program, context)
            if not installed:
                _ = stack.enter_context(
                    patch.object(record_type, hook, forbidden_constructor)
                )
                installed = True
            return result

        _ = stack.enter_context(
            patch.object(behavior_module, "run_probe_program", run_then_replace)
        )
        observations = observe_behavior_programs(authored, _context(source, tmp_path))
        assert observations.bugs[0].state is BugState.PRESENT
    assert installed and calls == 0


@pytest.mark.parametrize("hook", ["__init__", "__new__"])
@pytest.mark.parametrize("record_type", [ProbeRunContext])
def test_behavior_mirror_context_ignores_late_constructor(
    tmp_path: Path, hook: str, record_type: type[object]
) -> None:
    """Mirror copy callbacks cannot substitute the admitted execution context."""
    if hook == "__new__" and _isolate_late_receipt_new(
        "test_behavior_mirror_context_ignores_late_constructor", record_type
    ):
        return
    source, _ = _trees(tmp_path)
    context = _context(source, tmp_path)
    admitted = behavior_module._snapshot_observed_source(source)
    mirror = tmp_path / "mirror"
    native_copy = shutil.copytree
    calls = 0

    def forbidden_constructor(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late mirror context constructor executed")

    with ExitStack() as stack:

        def copy_then_replace(
            source_root: Path, destination: Path, *, symlinks: bool = False
        ) -> Path:
            completed = native_copy(source_root, destination, symlinks=symlinks)
            _ = stack.enter_context(
                patch.object(record_type, hook, forbidden_constructor)
            )
            return completed

        _ = stack.enter_context(
            patch.object(behavior_module, "_NATIVE_COPYTREE", copy_then_replace)
        )
        mirrored = behavior_module._admit_observation_mirror(
            context, mirror, admitted
        )
        assert mirrored.source_root == mirror
        assert mirrored.repository_root == tmp_path
        assert mirrored.enforce_source_immutable
    assert calls == 0


@pytest.mark.parametrize("field", ["repository_root", "tools"])
def test_behavior_mirror_context_preserves_stored_tool_bindings(
    tmp_path: Path, field: str
) -> None:
    """A mirror-copy callback cannot forge the original tool authority."""
    source, _ = _trees(tmp_path)
    context = _context(source, tmp_path)
    admitted = behavior_module._snapshot_observed_source(source)
    mirror = tmp_path / "mirror"
    native_copy = shutil.copytree
    original_slot = ProbeRunContext.__dict__[field]
    original = original_slot.__get__(context, ProbeRunContext)
    forged: object = (
        tmp_path / "other-repository"
        if field == "repository_root"
        else ((_PYTHON_TOOL, tmp_path / "other-python"),)
    )
    calls = 0

    def forged_getter(_context: object) -> object:
        nonlocal calls
        calls += 1
        return forged

    with ExitStack() as stack:

        def copy_then_replace(
            source_root: Path, destination: Path, *, symlinks: bool = False
        ) -> Path:
            completed = native_copy(source_root, destination, symlinks=symlinks)
            _ = stack.enter_context(
                patch.object(ProbeRunContext, field, property(forged_getter))
            )
            return completed

        _ = stack.enter_context(
            patch.object(behavior_module, "_NATIVE_COPYTREE", copy_then_replace)
        )
        mirrored = behavior_module._admit_observation_mirror(
            context, mirror, admitted
        )
        observed = original_slot.__get__(mirrored, ProbeRunContext)
    assert observed == original
    assert calls == 0, "late class getter redirected original tool bindings"


def test_behavior_observation_rejects_original_drift_under_late_root_getter(
    tmp_path: Path
) -> None:
    """A copy callback cannot hide original-source drift with a fake root."""
    authored, source, _ = _authored(tmp_path)
    native_copy = shutil.copytree
    calls = 0

    def forged_root(_context: object) -> Path:
        nonlocal calls
        calls += 1
        return destination

    with ExitStack() as stack:
        destination = tmp_path / "observation-target"

        def copy_then_mutate(
            source_root: Path, mirror: Path, *, symlinks: bool = False
        ) -> Path:
            nonlocal destination
            completed = native_copy(source_root, mirror, symlinks=symlinks)
            destination = mirror
            _write(source_root, "identity.txt", b"mutated outside mirror")
            _ = stack.enter_context(
                patch.object(ProbeRunContext, "source_root", property(forged_root))
            )
            return completed

        _ = stack.enter_context(
            patch.object(behavior_module, "_NATIVE_COPYTREE", copy_then_mutate)
        )
        with pytest.raises(ProbeExecutionError, match="changed between probes"):
            _ = observe_behavior_programs(authored, _context(source, tmp_path))
    assert calls == 0, "late source getter concealed original-tree drift"


@pytest.mark.parametrize("forgery", ["missing", "foreign", "unselected"])
def test_behavior_bundle_revalidates_exact_native_bug(forgery: str) -> None:
    """Exact native bug records must still satisfy their original validator."""
    baseline = _programs()
    authentic = baseline.bugs[0]
    bug = object.__new__(BugProgram)
    fields: dict[str, object] = {
        "program": authentic.program,
        "correction_id": authentic.correction_id,
    }
    match forgery:
        case "missing":
            del fields["correction_id"]
        case "foreign":
            fields["correction_id"] = 8
        case _:
            fields["program"] = _compatibility_program()
    for name, value in fields.items():
        slot = cast("MemberDescriptorType", BugProgram.__dict__[name])
        slot.__set__(bug, value)
    with pytest.raises(BehaviorProgramError, match="bug"):
        _ = BehaviorPrograms(baseline.identity, baseline.compatibility, (bug,))


@pytest.mark.parametrize("forgery", ["missing", "empty", "equal", "mutable"])
def test_authored_bundle_revalidates_exact_native_bug(
    tmp_path: Path, forgery: str
) -> None:
    """Native bug transcripts cannot bypass digest or missing-slot guards."""
    baseline, _, _ = _authored(tmp_path)
    authentic = baseline.bugs[0]
    bug = object.__new__(AuthoredBugProgram)
    fields: dict[str, object] = {
        "program": authentic.program,
        "correction_id": authentic.correction_id,
        "present_digest": authentic.present_digest,
        "fixed_digest": authentic.fixed_digest,
    }
    match forgery:
        case "missing":
            del fields["fixed_digest"]
        case "empty":
            fields["present_digest"] = b""
        case "equal":
            fields["present_digest"] = fields["fixed_digest"]
        case _:
            fields["present_digest"] = bytearray(b"foreign")
    for name, value in fields.items():
        slot = cast("MemberDescriptorType", AuthoredBugProgram.__dict__[name])
        slot.__set__(bug, value)
    with pytest.raises(BehaviorProgramError, match="authored"):
        _ = AuthoredBehaviorPrograms(
            baseline.profile, baseline.identity, baseline.compatibility, (bug,)
        )


def test_authoring_rejects_empty_native_program_bundle_before_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native program groups are revalidated before running source probes."""
    source, oracle = _trees(tmp_path)
    baseline = _programs()
    forged = object.__new__(BehaviorPrograms)
    for name, value in (
        ("identity", ()),
        ("compatibility", baseline.compatibility),
        ("bugs", baseline.bugs),
    ):
        slot = cast("MemberDescriptorType", BehaviorPrograms.__dict__[name])
        slot.__set__(forged, value)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        del _args, _kwargs
        message = "invalid behavior bundle executed untrusted probes"
        raise AssertionError(message)

    monkeypatch.setattr(behavior_module, "_run_authored_baselines", forbidden)
    with pytest.raises(BehaviorProgramError, match="identity"):
        _ = author_behavior_programs(
            forged, _context(source, tmp_path), _context(oracle, tmp_path)
        )


@pytest.mark.parametrize("forgery", ["missing", "empty"])
def test_observation_rejects_native_authored_bundle_before_source_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forgery: str
) -> None:
    """Uninitialized authored metadata must not trigger source observation."""
    baseline, source, _ = _authored(tmp_path)
    forged = object.__new__(AuthoredBehaviorPrograms)
    fields: dict[str, object] = {
        "profile": baseline.profile,
        "identity": baseline.identity,
        "compatibility": baseline.compatibility,
        "bugs": baseline.bugs,
    }
    match forgery:
        case "missing":
            del fields["profile"]
        case _:
            fields["identity"] = ()
    for name, value in fields.items():
        slot = cast(
            "MemberDescriptorType", AuthoredBehaviorPrograms.__dict__[name]
        )
        slot.__set__(forged, value)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        del _args, _kwargs
        message = "invalid authored bundle entered source observation"
        raise AssertionError(message)

    monkeypatch.setattr(behavior_module, "_snapshot_observed_source", forbidden)
    with pytest.raises(
        BehaviorProgramError, match=r"authored|identity|profile"
    ):
        _ = observe_behavior_programs(forged, _context(source, tmp_path))


@pytest.mark.parametrize("owner", ["identity", "bug", "authored-bug"])
@pytest.mark.parametrize("hook", ["commands", "selector", "exit-selector"])
@pytest.mark.parametrize("selected", [False, True])
def test_behavior_selector_ignores_late_probe_class_getters(
    monkeypatch: pytest.MonkeyPatch,
    owner: str,
    hook: str,
    *,
    selected: bool,
) -> None:
    """Selected observations must reflect the stored probe, not late getters."""
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('status')"),
        digest_stdout=selected if hook != "exit-selector" else False,
        digest_exit_code=selected if hook == "exit-selector" else False,
    )
    program = ProbeProgram("identity", (command,))
    forged_command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('foreign')"),
        digest_stdout=not selected,
    )
    getter_calls = 0

    def forged_commands(_program: ProbeProgram) -> tuple[ProbeCommand, ...]:
        nonlocal getter_calls
        getter_calls += 1
        return (forged_command,)

    def forged_selector(_command: ProbeCommand) -> bool:
        nonlocal getter_calls
        getter_calls += 1
        return not selected

    def author() -> object:
        if owner == "identity":
            return BehaviorPrograms((program,), (), ())
        if owner == "bug":
            return BugProgram(program, "fix")
        return AuthoredBugProgram(program, "fix", b"present", b"fixed")

    with monkeypatch.context() as patched:
        if hook == "commands":
            patched.setattr(ProbeProgram, "commands", property(forged_commands))
        elif hook == "selector":
            patched.setattr(ProbeCommand, "digest_stdout", property(forged_selector))
        else:
            patched.setattr(ProbeCommand, "digest_exit_code", property(forged_selector))
        if selected:
            assert author() is not None
        else:
            with pytest.raises(BehaviorProgramError, match="selected observation"):
                _ = author()
    assert getter_calls == 0, "late probe getter influenced selector admission"


@pytest.mark.parametrize("stored_selector", [1, "selected", None])
def test_behavior_selector_rejects_fabricated_nonboolean_evidence(
    stored_selector: object,
) -> None:
    """A constructor-bypassed exact probe cannot use truthy selector aliases."""
    command = object.__new__(ProbeCommand)
    stdout_slot = cast(
        "MemberDescriptorType", ProbeCommand.__dict__["digest_stdout"]
    )
    exit_slot = cast(
        "MemberDescriptorType", ProbeCommand.__dict__["digest_exit_code"]
    )
    stdout_slot.__set__(command, stored_selector)
    exit_slot.__set__(command, False)
    program = ProbeProgram("identity", (command,))
    with pytest.raises(BehaviorProgramError, match="native boolean selectors"):
        _ = BehaviorPrograms((program,), (), ())


@pytest.mark.parametrize("missing", ["digest_stdout", "digest_exit_code"])
def test_behavior_selector_rejects_uninitialized_probe_slots(missing: str) -> None:
    """A missing selector field must fail through the typed behavior boundary."""
    command = object.__new__(ProbeCommand)
    for name in ("digest_stdout", "digest_exit_code"):
        if name == missing:
            continue
        slot = cast("MemberDescriptorType", ProbeCommand.__dict__[name])
        slot.__set__(command, True)
    program = ProbeProgram("identity", (command,))
    with pytest.raises(BehaviorProgramError, match="incomplete command selectors"):
        _ = BehaviorPrograms((program,), (), ())
