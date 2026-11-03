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
#   - Synthetic tests for portable behavior-probe process programs.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for portable behavior-probe process programs."""

from __future__ import annotations

import builtins
import gc
import hashlib
import io
import os
import shutil
import signal
import stat
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import threading
import time
from collections import UserString
from contextlib import suppress
from dataclasses import fields as dataclass_fields
from dataclasses import replace
from pathlib import Path, PurePath
from types import MemberDescriptorType, SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast, override

import pytest
from algorithms.diff import probe_exec as probe_exec_module
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.probe_exec import (
    PathArgument,
    ProbeCommand,
    ProbeExecutionError,
    ProbeProgram,
    ProbeProgramError,
    ProbeRoot,
    ProbeRunContext,
    ProbeTranscript,
    RootedExecutable,
    ToolExecutable,
    run_probe_program,
    run_probe_programs,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from subprocess import Popen
    from typing import IO

_PYTHON_TOOL = "python"
_WINDOWS_OS_NAME = "nt"
_ORIGINAL_TEXT = "before"
_EXTERNAL_DATA = b"external-data"
_OUTSIDE_BYTES = b"outside"
_ADMITTED_INPUT = b"admitted"
_STDOUT_NAME = "stdout"
_STDERR_NAME = "stderr"
_POSIX_OS_NAME = "posix"
_PROBE_WRITER_THREAD_NAME = "probe-stdin-writer"
_SHORT_STDIN_MESSAGE = "short or invalid"
_GROUP_CLEANUP_FAILURE = "group cleanup failed"
_PROBE_BATCH_PREFIX = "diff-probe-batch-"
_PROBE_SCRATCH_PREFIX = "diff-probe-"
_SECOND_RESOLUTION = 2
_POSIX_WAIT_NOHANG = cast("int", getattr(os, "WNOHANG", 1))
_LINK_CREATE_CODE = (
    "import pathlib,sys;pathlib.Path(sys.argv[1]).symlink_to(sys.argv[2])"
)
_READ_BYTES_CODE = (
    "import pathlib,sys;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
)
_MUTATE_CODE = "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('after')"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class _ProbeStdinWriter(Protocol):
    def __call__(
        self,
        stream: IO[bytes],
        data: bytes,
        errors: list[Exception],
        *,
        completed: threading.Event,
    ) -> None: ...


class _ShortStdinStream:
    def __init__(self, reported: object, *, partial: bool) -> None:
        self.stream: io.BytesIO = io.BytesIO()
        self.reported: object = reported
        self.partial: bool = partial

    def write(self, data: bytes) -> int:
        written = self.stream.write(data[:1] if self.partial else data)
        return written if self.partial else cast("int", self.reported)

    def close(self) -> None:
        self.stream.close()

    @property
    def closed(self) -> bool:
        return self.stream.closed


class _ForgedCloseStream(io.BytesIO):
    def __init__(self, receipt: object) -> None:
        super().__init__()
        self.receipt = receipt

    def close(self) -> None:
        super().close()
        return cast("None", self.receipt)


def _context(source_root: Path, repository_root: Path) -> ProbeRunContext:
    return ProbeRunContext(
        source_root=source_root,
        repository_root=repository_root,
        tools=((_PYTHON_TOOL, Path(sys.executable)),),
    )


def _program(probe_id: str, code: str, *, digest_stdout: bool = True) -> ProbeProgram:
    return ProbeProgram(
        probe_id=probe_id,
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", code),
                digest_stdout=digest_stdout,
            ),
        ),
    )


def test_selected_stdout_produces_deterministic_transcript(
    tmp_path: Path,
) -> None:
    """Hash only explicitly selected deterministic process stdout."""
    source = tmp_path / "source"
    source.mkdir()
    program = _program("identity", "print('stable')")
    context = _context(source, tmp_path)

    first = run_probe_program(program, context)
    second = run_probe_program(program, context)

    _expect(first == second, "repeated process transcript changed")
    _expect(first.digested_commands == 1, "selected stdout was not digested")


def test_selected_commands_ignore_late_enumerate_suppression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A callback cannot hide authenticated probe commands."""
    source = tmp_path / "source"
    source.mkdir()
    context = _context(source, tmp_path)
    program = _program("identity", "print('stable')")
    expected = run_probe_program(program, context)
    assert expected.digested_commands == 1
    native_enumerate = builtins.enumerate
    calls = 0

    def suppress_commands(values: tuple[ProbeCommand, ...]) -> object:
        nonlocal calls
        if values is program.commands:
            calls += 1
            return ()
        return native_enumerate(values)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "enumerate", suppress_commands)
        observed = run_probe_program(program, context)
    assert observed == expected, "late enumerate omitted an authenticated probe"
    assert calls == 0, "host enumerate controlled authenticated probe execution"


def test_probe_transcripts_ignore_replaced_global_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted hash cannot give distinct probe outputs identical digests."""
    source = tmp_path / "source"
    source.mkdir()
    context = _context(source, tmp_path)
    calls = 0

    class _ForgedHash:
        def update(self, _data: bytes) -> None:
            _ = _data

        def digest(self) -> bytes:
            return bytes(32)

    def forged_sha256(_data: bytes = b"") -> _ForgedHash:
        nonlocal calls
        calls += 1
        return _ForgedHash()

    monkeypatch.setattr(hashlib, "sha256", forged_sha256)
    first = run_probe_program(_program("first", "print('alpha')"), context)
    second = run_probe_program(_program("second", "print('bravo')"), context)
    assert first.digest != second.digest
    assert calls == 0


def test_structured_source_path_is_passed_without_shell(tmp_path: Path) -> None:
    """Resolve source paths as argv entries without shell interpolation."""
    source = tmp_path / "source"
    source.mkdir()
    unusual_name = "semi;colon.txt"
    _ = (source / unusual_name).write_bytes(b"payload")
    program = ProbeProgram(
        probe_id="path",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, unusual_name),
                ),
                digest_stdout=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    expected = hashlib.sha256()
    expected.update(b"O")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update(len(b"payload").to_bytes(8, byteorder="big"))
    expected.update(b"payload")
    _expect(transcript.digest == expected.digest(), "structured argv changed bytes")


def _standalone_fixture(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    if os.name == _WINDOWS_OS_NAME:
        executable = Path(os.environ.get("COMSPEC", ""))
        arguments = ("/d", "/c", "echo ran")
    else:
        located = shutil.which("echo")
        executable = Path(located) if located is not None else Path()
        arguments = ("ran",)
    if not executable.is_file():
        pytest.skip("no standalone executable fixture is available")
    fixture = tmp_path / f"fixture{executable.suffix}"
    _ = shutil.copy2(executable, fixture)
    return fixture, arguments


def test_scratch_executable_can_be_produced_then_run(tmp_path: Path) -> None:
    """Run an executable artifact produced beneath the scratch root."""
    source = tmp_path / "source"
    source.mkdir()
    fixture, run_arguments = _standalone_fixture(tmp_path)
    scratch_name = f"probe{fixture.suffix}"
    writer = (
        "import pathlib,shutil,sys;"
        "shutil.copy2(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))"
    )
    program = ProbeProgram(
        probe_id="scratch-executable",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    writer,
                    PathArgument(ProbeRoot.REPOSITORY, fixture.name),
                    PathArgument(ProbeRoot.SCRATCH, scratch_name),
                ),
            ),
            ProbeCommand(
                executable=RootedExecutable(
                    ProbeRoot.SCRATCH,
                    scratch_name,
                ),
                arguments=run_arguments,
                digest_stdout=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    _expect(transcript.digested_commands == 1, "scratch executable did not run")


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_repository_root_resolution_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Wrap an inaccessible authorized root in the probe execution boundary."""
    source = tmp_path / "source"
    source.mkdir()
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked repository root"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(probe_exec_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    program = ProbeProgram(
        "root-resolution",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, "input.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="repository root resolution"):
        _ = run_probe_program(program, _context(source, tmp_path))


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_rooted_argument_resolution_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Wrap an inaccessible rooted argument before process launch."""
    source = tmp_path / "source"
    source.mkdir()
    candidate = tmp_path / "input.txt"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == candidate:
            message = "blocked rooted argument"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(probe_exec_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    program = ProbeProgram(
        "argument-resolution",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, "input.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="probe path resolution failed"):
        _ = run_probe_program(program, _context(source, tmp_path))


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_repository_alias_second_resolution_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Reject a repository path that fails its second preflight resolve."""
    source = tmp_path / "source"
    source.mkdir()
    candidate = tmp_path / "unrelated.txt"
    _ = candidate.write_text("outside", encoding="utf-8")
    original_resolve = Path.resolve
    resolved_paths: list[Path] = []

    def fail_second_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == candidate:
            resolved_paths.append(path)
            if len(resolved_paths) == _SECOND_RESOLUTION:
                message = "repository alias changed during preflight"
                raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(probe_exec_module, "_NATIVE_PATH_RESOLVE", fail_second_resolve)
    program = ProbeProgram(
        "alias-resolution",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, candidate.name),
                ),
            ),
        ),
    )
    with pytest.raises(
        ProbeExecutionError, match="repository argument resolution failed"
    ):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(
        len(resolved_paths) == _SECOND_RESOLUTION,
        "repository alias preflight did not perform both checks",
    )


def test_missing_tool_executable_fails_closed(tmp_path: Path) -> None:
    """A missing tool binding cannot fall through to process launch."""
    source = tmp_path / "source"
    source.mkdir()
    context = ProbeRunContext(
        source_root=source,
        repository_root=tmp_path,
        tools=((_PYTHON_TOOL, tmp_path / "missing-tool.exe"),),
    )

    with pytest.raises(ProbeExecutionError, match="executable is unavailable"):
        _ = run_probe_program(_program("missing-tool", "pass"), context)


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_tool_executable_status_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Preserve an inaccessible executable as a probe status failure."""
    source = tmp_path / "source"
    source.mkdir()
    tool = tmp_path / "tool.exe"
    _ = tool.write_bytes(b"not executed")
    context = ProbeRunContext(source, tmp_path, ((_PYTHON_TOOL, tool),))
    resolved_tool = tool.resolve()
    original_stat = Path.stat

    def fail_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == resolved_tool:
            message = "blocked tool executable"
            raise failure_type(message)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fail_stat
    )
    with pytest.raises(ProbeExecutionError, match="status failed"):
        _ = run_probe_program(_program("blocked-tool", "pass"), context)


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_tool_resolution_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Wrap tool-path resolution failures in the probe execution boundary."""
    source = tmp_path / "source"
    source.mkdir()
    tool = tmp_path / "tool.exe"
    _ = tool.write_bytes(b"not executed")
    context = ProbeRunContext(source, tmp_path, ((_PYTHON_TOOL, tool),))
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tool:
            message = "blocked tool resolution"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(probe_exec_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(ProbeExecutionError, match="tool resolution failed"):
        _ = run_probe_program(_program("blocked-resolution", "pass"), context)


def test_exit_code_can_be_observed_instead_of_required(tmp_path: Path) -> None:
    """Allow behavior probes to digest a nonzero process result as evidence."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="exit-observation",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "raise SystemExit(37)"),
                expected_exit_code=None,
                digest_exit_code=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    expected = hashlib.sha256()
    expected.update(b"E")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update((37).to_bytes(8, byteorder="big", signed=True))
    _expect(transcript.digest == expected.digest(), "exit-code transcript changed")
    _expect(transcript.digested_commands == 1, "exit code was not selected")


def test_unexpected_exit_code_fails_closed(tmp_path: Path) -> None:
    """Reject a process that violates its declared success contract."""
    source = tmp_path / "source"
    source.mkdir()
    program = _program("exit", "raise SystemExit(7)", digest_stdout=False)

    with pytest.raises(ProbeExecutionError, match="unexpected exit code"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_failed_probe_still_checks_original_source_mutation(
    tmp_path: Path,
) -> None:
    """Failed child cannot suppress original-source immutability diagnostics."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    code = (
        "import pathlib,sys;"
        "pathlib.Path(sys.argv[1]).write_text('after');"
        "raise SystemExit(7)"
    )
    program = ProbeProgram(
        "failed-original-mutator",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", code, str(target)),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="modified candidate source"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(
        target.read_text(encoding="utf-8") != _ORIGINAL_TEXT,
        "the injected unstructured-argv source write did not execute",
    )


def test_unrepresentable_timeout_is_probe_execution_error(
    tmp_path: Path,
) -> None:
    """Extreme positive timeout values must not leak arithmetic errors."""
    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "pass"),
        timeout_ms=10**1000,
    )
    with pytest.raises(ProbeExecutionError, match="unrepresentable timeout"):
        _ = run_probe_program(
            ProbeProgram("unrepresentable-timeout", (command,)),
            _context(source, tmp_path),
        )


def test_timeout_fails_closed(tmp_path: Path) -> None:
    """Bound probe execution time rather than permitting a hung transform."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="timeout",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "import time;time.sleep(1)"),
                timeout_ms=20,
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="timeout"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_timeout_terminates_probe_descendants_on_posix(tmp_path: Path) -> None:
    """Probe timeout must not leave an inherited child process running."""
    if os.name != _POSIX_OS_NAME:
        pytest.skip("POSIX process groups unavailable")
    source = tmp_path / "source"
    source.mkdir()
    started = tmp_path / "descendant-started"
    late = tmp_path / "descendant-finished"
    child_code = (
        "import pathlib,sys,time;"
        "pathlib.Path(sys.argv[1]).write_bytes(b'yes');"
        "time.sleep(1.4);"
        "pathlib.Path(sys.argv[2]).write_bytes(b'escaped')"
    )
    parent_code = (
        "import subprocess,sys,time,pathlib;"
        "subprocess.Popen([sys.executable,'-c',sys.argv[1],"
        "sys.argv[2],sys.argv[3]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL);"
        "p=pathlib.Path(sys.argv[2]);"
        "exec('while not p.exists(): time.sleep(0.005)');"
        "time.sleep(3)"
    )
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=(
            "-c",
            parent_code,
            child_code,
            PathArgument(ProbeRoot.REPOSITORY, started.name),
            PathArgument(ProbeRoot.REPOSITORY, late.name),
        ),
        timeout_ms=650,
    )
    with pytest.raises(ProbeExecutionError, match="timeout"):
        _ = run_probe_program(
            ProbeProgram("descendant-timeout", (command,)),
            _context(source, tmp_path),
        )
    _expect(started.exists(), "child had not started before timeout")
    time.sleep(1.5)
    _expect(not late.exists(), "probe descendant survived parent timeout")


def test_successful_probe_reaps_remaining_posix_descendants(
    tmp_path: Path,
) -> None:
    """A successful leader cannot leave a still-running helper behind."""
    if os.name != _POSIX_OS_NAME:
        pytest.skip("POSIX process groups unavailable")
    source = tmp_path / "source"
    source.mkdir()
    started = tmp_path / "helper-started"
    late = tmp_path / "helper-finished"
    child_code = (
        "import pathlib,sys,time;"
        "pathlib.Path(sys.argv[1]).write_bytes(b'yes');"
        "time.sleep(0.8);"
        "pathlib.Path(sys.argv[2]).write_bytes(b'escaped')"
    )
    parent_code = (
        "import pathlib,subprocess,sys,time;"
        "subprocess.Popen([sys.executable,'-c',sys.argv[1],"
        "sys.argv[2],sys.argv[3]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL);"
        "p=pathlib.Path(sys.argv[2]);"
        "exec('while not p.exists(): time.sleep(0.005)');"
        "print('parent complete')"
    )
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=(
            "-c",
            parent_code,
            child_code,
            PathArgument(ProbeRoot.REPOSITORY, started.name),
            PathArgument(ProbeRoot.REPOSITORY, late.name),
        ),
        timeout_ms=2_000,
        digest_stdout=True,
    )
    _ = run_probe_program(
        ProbeProgram("success-descendant", (command,)),
        _context(source, tmp_path),
    )
    _expect(started.exists(), "probe did not start its child")
    time.sleep(1.0)
    _expect(not late.exists(), "successful probe left descendant running")


def _reject_group_kill_for_test(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[int], Callable[[int, int], None]]:
    real_kill = os.kill
    blocked_groups: list[int] = []

    def reject_group_kill(pid: int, signum: int) -> None:
        if pid < 0:
            blocked_groups.append(-pid)
            message = "injected denied process-group signal"
            raise PermissionError(message)
        real_kill(pid, signum)

    monkeypatch.setattr(os, "kill", reject_group_kill)
    return blocked_groups, real_kill


def _ensure_probe_child_was_reaped(pid: int) -> None:
    with suppress(ChildProcessError):
        _ = os.waitpid(pid, _POSIX_WAIT_NOHANG)
        message = "probe child was not reaped after denied group signal"
        raise AssertionError(message)


def _cleanup_probe_group_test(
    blocked_groups: list[int], real_kill: Callable[[int, int], None]
) -> None:
    for pid in blocked_groups:
        try:
            waited, _ = os.waitpid(pid, _POSIX_WAIT_NOHANG)
        except ChildProcessError:
            waited = -1
        if waited == 0:
            with suppress(ProcessLookupError):
                real_kill(pid, int(signal.Signals["SIGKILL"]))
            with suppress(ChildProcessError):
                _ = os.waitpid(pid, 0)


@pytest.mark.parametrize("expires", [False, True])
def test_failed_group_signal_reaps_probe_and_preserves_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    expires: bool,
) -> None:
    """An unpermitted group kill must not mask a timeout or leak its child."""
    if os.name != _POSIX_OS_NAME:
        pytest.skip("POSIX process groups unavailable")
    source = tmp_path / "source"
    source.mkdir()
    blocked_groups, real_kill = _reject_group_kill_for_test(monkeypatch)
    code = "import time;time.sleep(4)" if expires else "print('complete')"
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", code),
        timeout_ms=60 if expires else 2_000,
        digest_stdout=True,
    )
    try:
        with pytest.raises(
            ProbeExecutionError,
            match="timeout" if expires else _GROUP_CLEANUP_FAILURE,
        ) as failure:
            _ = run_probe_program(
                ProbeProgram("group-kill-denied", (command,)),
                _context(source, tmp_path),
            )
        _expect(bool(blocked_groups), "failed group signal was not exercised")
        if expires:
            notes = cast("list[str]", getattr(failure.value, "__notes__", []))
            _expect(
                any(_GROUP_CLEANUP_FAILURE in note for note in notes),
                "the original timeout lost its secondary cleanup diagnostic",
            )
        _ensure_probe_child_was_reaped(blocked_groups[0])
    finally:
        _cleanup_probe_group_test(blocked_groups, real_kill)


def test_probe_deadline_includes_pipe_setup_delay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wall budget starts before launch, not after pipe threads start."""
    source = tmp_path / "source"
    source.mkdir()
    original_start = threading.Thread.start

    def delayed_thread_start(thread: threading.Thread) -> None:
        original_start(thread)
        time.sleep(0.10)

    monkeypatch.setattr(threading.Thread, "start", delayed_thread_start)
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('done')"),
        timeout_ms=40,
        digest_stdout=True,
    )
    with pytest.raises(ProbeExecutionError, match="timeout"):
        _ = run_probe_program(
            ProbeProgram("delayed-setup", (command,)),
            _context(source, tmp_path),
        )


def test_output_limit_fails_closed(tmp_path: Path) -> None:
    """Bound captured output before transform-controlled memory growth."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="output-limit",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "print('x' * 1000)"),
                max_stdout_bytes=16,
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="stdout limit"):
        _ = run_probe_program(program, _context(source, tmp_path))


@pytest.mark.parametrize("receipt", ["subclass", "oversized", "foreign"])
def test_probe_raw_capture_rejects_non_native_read_evidence(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A forged raw chunk cannot evade the verified byte quota."""

    class DeceptiveBytes(bytes):
        def __len__(self) -> int:
            return 1

    raw: object
    if receipt == "subclass":
        raw = DeceptiveBytes(b"x" * 4096)
    elif receipt == "oversized":
        raw = b"x" * (probe_exec_module._READ_CHUNK_BYTES + 1)
    else:
        raw = memoryview(b"x")

    monkeypatch.setattr(probe_exec_module.os, "read", lambda *_: raw)
    with tempfile.TemporaryFile() as stream:
        capture = probe_exec_module._PipeCapture(limit=1024 * 1024)
        with pytest.raises(ValueError, match="raw read"):
            _ = probe_exec_module._capture_fragment(stream, capture)
    assert capture.fragments == []
    assert capture.size == 0


@pytest.mark.parametrize("receipt", [True, -1, 2**31, "1", 1.0])
def test_probe_raw_capture_rejects_foreign_file_descriptors(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A forged pipe descriptor cannot redirect process transcript reads."""
    read_calls: list[object] = []

    class ForgedDescriptor:
        def fileno(self) -> object:
            return receipt

    def raw_read(fd: object, count: int) -> bytes:
        read_calls.append((fd, count))
        return b"synthetic"

    monkeypatch.setattr(probe_exec_module.os, "read", raw_read)
    capture = probe_exec_module._PipeCapture(limit=32)
    with pytest.raises(ValueError, match="raw read descriptor"):
        _ = probe_exec_module._capture_fragment(
            cast("IO[bytes]", cast("object", ForgedDescriptor())),
            capture,
        )
    assert read_calls == []
    assert capture.fragments == []


def test_unexpected_pipe_reader_failure_rejects_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dead capture workers must not silently accept a partial transcript."""
    source = tmp_path / "source"
    source.mkdir()
    read = os.read

    def crashing_read(fd: int, count: int) -> bytes:
        if threading.current_thread() is not threading.main_thread():
            message = "synthetic reader failure"
            raise ValueError(message)
        return read(fd, count)

    monkeypatch.setattr(os, "read", crashing_read)
    program = _program("failed-output-reader", "pass")
    with pytest.raises(ProbeExecutionError, match="pipe communication failed"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_uncaught_reader_thread_failure_rejects_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected worker exits must not produce a valid empty transcript."""
    source = tmp_path / "source"
    source.mkdir()
    read = os.read
    uncaught: list[BaseException | None] = []

    def record_uncaught(args: threading.ExceptHookArgs) -> None:
        uncaught.append(args.exc_value)

    def crashing_read(fd: int, count: int) -> bytes:
        if threading.current_thread() is not threading.main_thread():
            # BaseException is not an ordinary adapter fault: an uncaught
            # cancellation must still leave the worker incomplete.
            raise KeyboardInterrupt
        return read(fd, count)

    monkeypatch.setattr(threading, "excepthook", record_uncaught)
    monkeypatch.setattr(os, "read", crashing_read)
    program = _program("uncaught-output-reader", "pass")
    with pytest.raises(ProbeExecutionError, match="pipe communication failed"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(bool(uncaught), "worker exception fixture was not exercised")


def _hostile_primary_probe_fault() -> RuntimeError:
    """Foreign primary which forbids overridden notes while unwinding."""

    def reject_note(self: BaseException, note: str) -> None:
        del self, note
        raise AssertionError("foreign probe primary note hook executed")

    foreign = type("ForeignProbePrimary", (RuntimeError,), {"add_note": reject_note})
    return foreign("original probe operation failed")


@pytest.mark.parametrize("cleanup_kind", ["native", "foreign", "hostile-args"])
def test_unowned_probe_pipe_close_keeps_foreign_primary(
    cleanup_kind: str,
) -> None:
    """Cleanup notes cannot invoke untrusted error text or primary hooks."""
    primary = _hostile_primary_probe_fault()

    class ForeignCloseError(OSError):
        def __str__(self) -> str:
            raise AssertionError("foreign pipe close text executed")

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("pipe close argument text executed")

    secondary = {
        "native": OSError("native pipe close denied"),
        "foreign": ForeignCloseError("foreign pipe close denied"),
        "hostile-args": OSError(HostileArgument()),
    }[cleanup_kind]

    class CloseFault(io.BytesIO):
        def close(self) -> None:
            super().close()
            raise secondary

    stream = CloseFault(b"payload")
    probe_exec_module._close_unowned_pipe(stream, None, primary)
    _expect(stream.closed, "unowned pipe was not closed")
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    _expect(len(notes) == 1 and "pipe close failed" in notes[0], "cleanup note missing")
    if cleanup_kind == "native":
        _expect("native pipe close denied" in notes[0], "native note detail lost")


@pytest.mark.parametrize(
    "failure_type", [TypeError, AttributeError, IndexError, OverflowError]
)
def test_unowned_pipe_unexpected_close_fault_preserves_primary(
    failure_type: type[Exception],
) -> None:
    """Unexpected native cleanup faults must not replace the body failure."""
    primary = RuntimeError("primary probe worker failure")
    secondary = failure_type("unowned descriptor close failed")

    class CloseFault(io.BytesIO):
        def close(self) -> None:
            super().close()
            raise secondary

    stream = CloseFault(b"unused")
    probe_exec_module._close_unowned_pipe(stream, None, primary)
    assert stream.closed
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    assert len(notes) == 1
    assert "pipe close failed" in notes[0]


@pytest.mark.parametrize("receipt", [False, 1, "done"])
def test_unowned_pipe_forged_close_completion_records_secondary(
    receipt: object,
) -> None:
    """Unowned cleanup cannot silently attest a foreign close receipt."""
    primary = RuntimeError("original probe failure")
    stream = _ForgedCloseStream(receipt)
    probe_exec_module._close_unowned_pipe(stream, None, primary)
    assert stream.closed
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    assert len(notes) == 1 and "pipe close failed" in notes[0]


@pytest.mark.parametrize("cleanup_kind", ["native", "foreign", "hostile-args"])
def test_probe_child_cleanup_keeps_foreign_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_kind: str,
) -> None:
    """A secondary child-stop fault cannot replace worker failure."""
    primary = _hostile_primary_probe_fault()

    class ForeignStopError(ProbeExecutionError):
        def __str__(self) -> str:
            raise AssertionError("foreign child-stop text executed")

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("child-stop argument text executed")

    secondary = {
        "native": ProbeExecutionError("native child cleanup denied"),
        "foreign": ForeignStopError("foreign child cleanup denied"),
        "hostile-args": ProbeExecutionError(HostileArgument()),
    }[cleanup_kind]
    process = object()

    def fail_worker(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise primary

    def fail_stop(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(probe_exec_module, "_spawn_probe", lambda *_args: process)
        patch.setattr(probe_exec_module, "_start_capture_checked", fail_worker)
        patch.setattr(probe_exec_module, "_stop_child", fail_stop)
        command = ProbeCommand(ToolExecutable(_PYTHON_TOOL))
        with pytest.raises(RuntimeError) as caught:
            probe_exec_module._launch_command(["probe"], command, tmp_path)

    _expect(caught.value is primary, "child cleanup replaced original failure")
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    _expect(len(notes) == 1 and "child cleanup" in notes[0], "cleanup note missing")
    if cleanup_kind == "native":
        _expect("native child cleanup denied" in notes[0], "native note detail lost")


@pytest.mark.skipif(os.name != _POSIX_OS_NAME, reason="POSIX child group branch")
@pytest.mark.parametrize("site", ["reap", "group", "direct", "group-note"])
@pytest.mark.parametrize("fault_kind", ["foreign", "hostile-args", "native"])
def test_probe_child_stop_never_formats_foreign_host_faults(
    monkeypatch: pytest.MonkeyPatch,
    site: str,
    fault_kind: str,
) -> None:
    """Reaping, group and child kill diagnostics remain typed and causal."""

    class ForeignStopError(OSError):
        def __str__(self) -> str:
            raise AssertionError("foreign stop formatter executed")

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign stop argument formatter executed")

    fault = {
        "foreign": ForeignStopError("foreign stop denied"),
        "hostile-args": OSError(HostileArgument()),
        "native": OSError("native stop denied"),
    }[fault_kind]
    group_error = fault if site in ("group", "group-note") else None
    direct_error = fault if site == "direct" else None
    if site == "direct":
        group_error = OSError("native group stop denied")
    if site == "group-note":
        direct_error = OSError("native child stop denied")

    class FakeChild:
        def wait(self, *, timeout: float | None = None) -> int:
            del timeout
            if site == "reap":
                raise fault
            return 0

    with monkeypatch.context() as patch:
        patch.setattr(probe_exec_module, "_signal_probe_group", lambda *_: group_error)
        patch.setattr(
            probe_exec_module, "_kill_direct_probe_child", lambda *_: direct_error
        )
        with pytest.raises(ProbeExecutionError) as caught:
            probe_exec_module._stop_child(cast("Popen[bytes]", FakeChild()))

    if site == "group-note":
        _expect(caught.value.__cause__ is direct_error, "direct failure lost")
        notes = cast("list[str]", getattr(caught.value, "__notes__", []))
        _expect(len(notes) == 1 and "group cleanup" in notes[0], "group note lost")
        if fault_kind == "native":
            _expect("native stop denied" in notes[0], "native group note lost")
    else:
        _expect(caught.value.__cause__ is fault, "host stop failure cause lost")
        if fault_kind == "native":
            _expect("native stop denied" in str(caught.value), "native detail lost")


@pytest.mark.parametrize(
    "failure_type",
    [ValueError, RuntimeError, TypeError, AttributeError, IndexError, OverflowError],
)
def test_probe_spawn_unexpected_host_fault_remains_typed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_type: type[Exception],
) -> None:
    """Native subprocess launch faults must preserve typed probe admission."""
    primary = failure_type("synthetic subprocess startup failure")

    def fail_launch(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise primary

    monkeypatch.setattr(probe_exec_module.subprocess, "Popen", fail_launch)
    with pytest.raises(ProbeExecutionError, match="command launch failed") as caught:
        _ = probe_exec_module._spawn_probe(["probe"], tmp_path)
    assert caught.value.__cause__ is primary


@pytest.mark.parametrize(
    "failure_type", [TypeError, AttributeError, IndexError, OverflowError]
)
def test_probe_reap_unexpected_host_fault_remains_typed(
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A foreign child-wait adapter cannot leave an untyped teardown error."""
    primary = failure_type("synthetic wait failure")

    class FakeProcess:
        def wait(self, *, timeout: float | None = None) -> int:
            del timeout
            raise primary

    monkeypatch.setattr(probe_exec_module, "_signal_probe_group", lambda *_: None)
    monkeypatch.setattr(
        probe_exec_module, "_kill_direct_probe_child", lambda *_: None
    )
    with pytest.raises(ProbeExecutionError, match="reaping failed") as caught:
        probe_exec_module._stop_child(
            cast("Popen[bytes]", cast("object", FakeProcess()))
        )
    assert caught.value.__cause__ is primary


@pytest.mark.parametrize("site", ["launch", "worker"])
@pytest.mark.parametrize("fault_kind", ["foreign", "hostile-args", "native"])
def test_probe_host_launch_and_worker_failures_reject_foreign_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    site: str,
    fault_kind: str,
) -> None:
    """Host launch and worker errors reject without untrusted formatting."""
    fault_class: type[Exception] = OSError if site == "launch" else RuntimeError

    def unsafe_format(self: BaseException) -> str:
        del self
        raise AssertionError("foreign probe host formatter executed")

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign probe host argument formatter executed")

    foreign_type = type(
        "ForeignProbeHostError", (fault_class,), {"__str__": unsafe_format}
    )
    fault = {
        "foreign": foreign_type("foreign host fault"),
        "hostile-args": fault_class(HostileArgument()),
        "native": fault_class("native host fault"),
    }[fault_kind]

    def reject_host(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault

    with monkeypatch.context() as patch:
        if site == "launch":
            patch.setattr(probe_exec_module.subprocess, "Popen", reject_host)
            call = lambda: probe_exec_module._spawn_probe(["probe"], tmp_path)
            label = "command launch failed"
        else:
            patch.setattr(probe_exec_module, "_start_capture", reject_host)
            call = lambda: probe_exec_module._start_capture_checked(
                cast("Popen[bytes]", object()),
                ProbeCommand(ToolExecutable(_PYTHON_TOOL)),
            )
            label = "worker startup failed"
        with pytest.raises(ProbeExecutionError, match=label) as caught:
            _ = call()

    _expect(caught.value.__cause__ is fault, "foreign probe host cause was lost")
    if fault_kind == "native":
        _expect("native host fault" in str(caught.value), "native reason was lost")


@pytest.mark.parametrize(
    "failure_type", [TypeError, AttributeError, IndexError, OverflowError]
)
def test_unexpected_worker_setup_fault_is_typed(
    failure_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host worker setup failure must retain the probe exception boundary."""
    primary = failure_type("worker setup unavailable")

    def fail_setup(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise primary

    monkeypatch.setattr(probe_exec_module, "_start_capture", fail_setup)
    with pytest.raises(ProbeExecutionError, match="worker startup failed") as caught:
        _ = probe_exec_module._start_capture_checked(
            cast("Popen[bytes]", object()),
            ProbeCommand(ToolExecutable(_PYTHON_TOOL)),
        )
    assert caught.value.__cause__ is primary


@pytest.mark.parametrize("receipt", [False, 1, "done"])
def test_capture_reader_forged_close_completion_rejects(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A reader cannot declare a complete transcript after forged close."""
    stream = _ForgedCloseStream(receipt)
    capture = probe_exec_module._PipeCapture(limit=32)
    monkeypatch.setattr(probe_exec_module, "_capture_fragment", lambda *_: False)
    probe_exec_module._drain_pipe(stream, capture)
    assert stream.closed and capture.finished
    assert isinstance(capture.error, ValueError)


@pytest.mark.parametrize("failure_type", [TypeError, OverflowError])
def test_capture_preserves_read_fault_over_failed_close(
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """The original read failure wins over unexpected stream teardown."""
    primary = ValueError("capture read failed")
    secondary = failure_type("capture close failed")

    class CloseFault(io.BytesIO):
        def close(self) -> None:
            super().close()
            raise secondary

    def fail_read(*_args: object) -> bool:
        raise primary

    stream = CloseFault()
    capture = probe_exec_module._PipeCapture(limit=32)
    monkeypatch.setattr(probe_exec_module, "_capture_fragment", fail_read)
    probe_exec_module._drain_pipe(stream, capture)
    assert stream.closed and capture.finished and capture.error is primary
    notes = cast("list[str]", getattr(primary, "__notes__", []))
    assert len(notes) == 1 and "capture pipe close" in notes[0]


@pytest.mark.parametrize("receipt", [False, 1, "done"])
def test_empty_stdin_forged_close_receipt_rejects(
    receipt: object,
) -> None:
    """Closing unused stdin must require native completion as well."""
    stream = _ForgedCloseStream(receipt)

    class FakeProcess:
        stdin = stream

    with pytest.raises(ValueError, match="stdin close"):
        _ = probe_exec_module._start_writer(
            cast("Popen[bytes]", FakeProcess()),
            b"",
            [],
            completed=threading.Event(),
        )
    assert stream.closed


@pytest.mark.parametrize("fail_writer", [False, True])
def test_probe_worker_startup_failures_are_wrapped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_writer: bool,
) -> None:
    """Reader and writer start errors must stay inside the probe boundary."""
    source = tmp_path / "source"
    source.mkdir()
    original_start = threading.Thread.start
    triggered = [False]

    def failing_start(thread: threading.Thread) -> None:
        is_writer = thread.name == _PROBE_WRITER_THREAD_NAME
        if is_writer is fail_writer:
            triggered[0] = True
            message = "synthetic OS thread resource exhaustion"
            raise RuntimeError(message)
        original_start(thread)

    monkeypatch.setattr(threading.Thread, "start", failing_start)
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "pass"),
        stdin=b"nonempty",
        digest_stdout=True,
    )
    with pytest.raises(ProbeExecutionError, match="worker startup failed"):
        _ = run_probe_program(
            ProbeProgram("worker-startup", (command,)),
            _context(source, tmp_path),
        )
    _expect(triggered[0], "worker start failure was not injected")
    # Force unowned Popen pipe finalizers to run inside the strict warning gate.
    _ = gc.collect()


@pytest.mark.parametrize(
    "case",
    [(True, None), (False, None), (False, True), (False, -1), (False, 999)],
)
def test_stdin_worker_rejects_short_or_foreign_write_counts(
    case: tuple[bool, object],
) -> None:
    """The writer must not acknowledge partial stdin as fully delivered."""
    partial, reported = case
    stream = _ShortStdinStream(reported, partial=partial)
    errors: list[Exception] = []
    completed = threading.Event()
    feed = cast("_ProbeStdinWriter", vars(probe_exec_module)["_feed_stdin"])
    feed(
        cast("IO[bytes]", cast("object", stream)),
        b"required-input",
        errors,
        completed=completed,
    )
    assert not completed.is_set()
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)
    assert _SHORT_STDIN_MESSAGE in str(errors[0])
    assert stream.closed


@pytest.mark.parametrize(
    "failure_type", [TypeError, AttributeError, IndexError, OverflowError]
)
def test_stdin_worker_close_fault_does_not_complete(
    failure_type: type[Exception],
) -> None:
    """A foreign stream-close fault cannot attest full stdin delivery."""
    secondary = failure_type("stdin close failed")

    class CloseFault(io.BytesIO):
        def close(self) -> None:
            super().close()
            raise secondary

    stream = CloseFault()
    failures: list[Exception] = []
    completed = threading.Event()
    feed = cast("_ProbeStdinWriter", vars(probe_exec_module)["_feed_stdin"])
    feed(stream, b"full-input", failures, completed=completed)
    assert stream.closed
    assert failures == [secondary]
    assert not completed.is_set()


@pytest.mark.parametrize("receipt", [False, 1, "done"])
def test_stdin_worker_forged_close_receipt_does_not_complete(
    receipt: object,
) -> None:
    """A nonempty stdin writer cannot attest an untrusted pipe close."""
    stream = _ForgedCloseStream(receipt)
    errors: list[Exception] = []
    completed = threading.Event()
    feed = cast("_ProbeStdinWriter", vars(probe_exec_module)["_feed_stdin"])
    feed(stream, b"all-bytes", errors, completed=completed)
    assert stream.closed
    assert len(errors) == 1 and isinstance(errors[0], ValueError)
    assert not completed.is_set()


def test_uncaught_stdin_writer_failure_rejects_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An aborted stdin worker must not leave an admitted observation."""
    source = tmp_path / "source"
    source.mkdir()
    original_run = threading.Thread.run
    uncaught: list[BaseException | None] = []

    def record_uncaught(args: threading.ExceptHookArgs) -> None:
        uncaught.append(args.exc_value)

    def crashing_writer(thread: threading.Thread) -> None:
        if thread.name == _PROBE_WRITER_THREAD_NAME:
            message = "unanticipated stdin failure"
            raise TypeError(message)
        original_run(thread)

    monkeypatch.setattr(threading, "excepthook", record_uncaught)
    monkeypatch.setattr(threading.Thread, "run", crashing_writer)
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "pass"),
        stdin=b"input",
        digest_stdout=True,
    )
    program = ProbeProgram("uncaught-stdin-writer", (command,))
    with pytest.raises(ProbeExecutionError, match="pipe communication failed"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(bool(uncaught), "stdin worker failure was not exercised")
    _ = gc.collect()


@pytest.mark.parametrize("stream", [_STDOUT_NAME, _STDERR_NAME])
def test_live_pipe_quota_interrupts_unbounded_output(
    tmp_path: Path, stream: str
) -> None:
    """An overflowing child must fail by byte quota, not delayed timeout."""
    source = tmp_path / "source"
    source.mkdir()
    descriptor = 1 if stream == _STDOUT_NAME else 2
    code = f"import os;exec('while True: os.write({descriptor}, bytes(4096))')"
    program = ProbeProgram(
        "live-output-cap",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", code),
                timeout_ms=600,
                max_stdout_bytes=32,
                max_stderr_bytes=32,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match=f"{stream} limit"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_full_duplex_stdin_and_stdout_preserves_transcript(
    tmp_path: Path,
) -> None:
    """Concurrent stdin delivery must not deadlock a writing child."""
    source = tmp_path / "source"
    source.mkdir()
    payload = b"q" * 131_072
    prefix = b"w" * 16_384
    code = (
        "import sys;"
        "sys.stdout.buffer.write(b'w'*16384);"
        "sys.stdout.buffer.flush();"
        "data=sys.stdin.buffer.read();"
        "sys.stdout.buffer.write(data[:8])"
    )
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", code),
        stdin=payload,
        timeout_ms=2_000,
        max_stdout_bytes=16_392,
        digest_stdout=True,
    )
    transcript = run_probe_program(
        ProbeProgram("full-duplex", (command,)), _context(source, tmp_path)
    )
    expected_data = prefix + payload[:8]
    expected = hashlib.sha256()
    expected.update(b"O")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update(len(expected_data).to_bytes(8, byteorder="big"))
    expected.update(expected_data)
    _expect(transcript.digest == expected.digest(), "stdin/stdout transcript drift")


def test_source_mutation_is_isolated_from_user_source(tmp_path: Path) -> None:
    """Run source-mutating probes only against an isolated mirror."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    mutator = ProbeProgram(
        probe_id="mutator",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _MUTATE_CODE,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="isolated source mirror"):
        _ = run_probe_programs((mutator,), _context(source, tmp_path))
    _expect(
        target.read_text(encoding="utf-8") == _ORIGINAL_TEXT,
        "source was mutated",
    )


@pytest.mark.parametrize("mutator_fails", [False, True])
def test_source_mirror_checked_after_each_command(
    tmp_path: Path, *, mutator_fails: bool
) -> None:
    """Do not digest intermediate mutated bytes or lose failure diagnostics."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    mutation = "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('during');"
    if mutator_fails:
        mutation += "raise SystemExit(7)"
    restore = "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
    program = ProbeProgram(
        "transient-source-mutation",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    mutation,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
            ),
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
                digest_stdout=True,
            ),
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    restore,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                    _ORIGINAL_TEXT,
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="isolated source mirror"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(
        target.read_text(encoding="utf-8") == _ORIGINAL_TEXT,
        "source mirror mutation escaped into original source",
    )


@pytest.mark.parametrize("via_alias", [False, True])
def test_repository_rooted_argument_cannot_modify_original_source(
    tmp_path: Path, *, via_alias: bool
) -> None:
    """A repository-root path may not bypass the isolated source mirror."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    relative = "source/input.txt"
    if via_alias:
        alias = tmp_path / "alias"
        try:
            alias.symlink_to(source, target_is_directory=True)
        except OSError, NotImplementedError:
            pytest.skip("directory symlinks unavailable")
        relative = "alias/input.txt"
    context = replace(_context(source, tmp_path), enforce_source_immutable=False)
    program = ProbeProgram(
        "repository-source-alias",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _MUTATE_CODE,
                    PathArgument(ProbeRoot.REPOSITORY, relative),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="overlaps original source"):
        _ = run_probe_program(program, context)
    _expect(
        target.read_text(encoding="utf-8") == _ORIGINAL_TEXT,
        "repository-rooted argument modified original source",
    )


@pytest.mark.parametrize("via_directory", [False, True])
def test_repository_alias_rejects_forged_native_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, via_directory: bool
) -> None:
    """A post-import resolver swap cannot launder a source symlink alias."""
    source = tmp_path / "source"
    source.mkdir()
    leaf = source / "input.txt"
    _ = leaf.write_bytes(b"private source bytes")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(
            source if via_directory else leaf,
            target_is_directory=via_directory,
        )
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    relative = "alias/input.txt" if via_directory else "alias"
    aliased_leaf = alias / "input.txt" if via_directory else alias
    original_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == aliased_leaf:
            calls += 1
            return path
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", forged_resolve)
    program = ProbeProgram(
        "forged-repository-alias",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.REPOSITORY, relative),
                ),
                digest_stdout=True,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="overlaps original source"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(calls == 0, "mutable host resolver was consulted")


@pytest.mark.parametrize("as_executable", [False, True])
def test_repository_hardlink_to_original_source_is_rejected(
    tmp_path: Path, *, as_executable: bool
) -> None:
    """Distinct canonical paths can still refer to one writable source inode."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    hardlink = tmp_path / "external-alias.txt"
    try:
        os.link(target, hardlink)
    except OSError, NotImplementedError:
        pytest.skip("hard links are unavailable")
    context = replace(_context(source, tmp_path), enforce_source_immutable=False)
    command = (
        ProbeCommand(
            executable=RootedExecutable(ProbeRoot.REPOSITORY, hardlink.name),
        )
        if as_executable
        else ProbeCommand(
            executable=ToolExecutable(_PYTHON_TOOL),
            arguments=(
                "-c",
                _MUTATE_CODE,
                PathArgument(ProbeRoot.REPOSITORY, hardlink.name),
            ),
        )
    )
    program = ProbeProgram("hardlink-to-original-source", (command,))
    with pytest.raises(ProbeExecutionError, match="source inode"):
        _ = run_probe_program(program, context)
    _expect(
        target.read_text(encoding="utf-8") == _ORIGINAL_TEXT,
        "external hardlink modified the original protected source",
    )


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_repository_path_status_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Reject a repository argument when its inode metadata is unavailable."""
    source = tmp_path / "source"
    source.mkdir()
    candidate = tmp_path / "external-data.txt"
    _ = candidate.write_bytes(_EXTERNAL_DATA)
    original_stat = Path.stat

    def fail_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == candidate:
            message = "repository inode inspection failed"
            raise failure_type(message)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fail_stat
    )
    program = ProbeProgram(
        "repository-inode-failure",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, candidate.name),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="repository path status failed"):
        _ = run_probe_program(program, _context(source, tmp_path))


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_source_inode_status_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Reject a linked repository file when source inode metadata fails."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    hardlink = tmp_path / "external-alias.txt"
    try:
        os.link(target, hardlink)
    except OSError, NotImplementedError:
        pytest.skip("hard links are unavailable")
    original_stat = Path.stat

    def fail_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == target:
            message = "source inode inspection failed"
            raise failure_type(message)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fail_stat
    )
    program = ProbeProgram(
        "source-inode-failure",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, hardlink.name),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="source inode status failed"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_repository_hardlink_unrelated_to_source_is_allowed(
    tmp_path: Path,
) -> None:
    """Unrelated hardlinks remain valid repository inputs."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "input.txt").write_text(_ORIGINAL_TEXT, encoding="utf-8")
    content = tmp_path / "external-data.txt"
    _ = content.write_bytes(_EXTERNAL_DATA)
    hardlink = tmp_path / "external-alias.txt"
    try:
        os.link(content, hardlink)
    except OSError, NotImplementedError:
        pytest.skip("hard links are unavailable")
    program = ProbeProgram(
        "unrelated-repository-hardlink",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.REPOSITORY, hardlink.name),
                ),
                digest_stdout=True,
            ),
        ),
    )
    transcript = run_probe_program(program, _context(source, tmp_path))
    _expect(transcript.digested_commands == 1, "hardlink output was not read")
    _expect(hardlink.read_bytes() == _EXTERNAL_DATA, "hardlink content changed")


def test_repository_rooted_executable_cannot_alias_original_source(
    tmp_path: Path,
) -> None:
    """Rooted executable records cannot bypass the source mirror."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "tool.bin").write_bytes(b"not launched")
    program = ProbeProgram(
        "repository-source-tool",
        (
            ProbeCommand(
                executable=RootedExecutable(ProbeRoot.REPOSITORY, "source/tool.bin"),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="overlaps original source"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_source_symlink_fails_before_mirror_even_without_immutability(
    tmp_path: Path,
) -> None:
    """Reject external source links before mirroring content."""
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    _ = secret.write_bytes(_EXTERNAL_DATA)
    linked = source / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("directory symlinks unavailable")

    context = replace(_context(source, tmp_path), enforce_source_immutable=False)
    program = ProbeProgram(
        "linked-input",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, "linked/secret.txt"),
                ),
                digest_stdout=True,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="symlinks"):
        _ = run_probe_program(program, context)
    _expect(secret.read_bytes() == _EXTERNAL_DATA, "external input changed")


def test_probe_created_symlink_is_rejected_inside_execution_boundary(
    tmp_path: Path,
) -> None:
    """Probe-created links are rejected through ProbeExecutionError."""
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside.txt"
    _ = outside.write_bytes(_OUTSIDE_BYTES)
    probe = tmp_path / "probe"
    try:
        probe.symlink_to(outside)
    except OSError, NotImplementedError:
        pytest.skip("file symlinks unavailable")
    probe.unlink()
    program = ProbeProgram(
        "link-mirror",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _LINK_CREATE_CODE,
                    PathArgument(ProbeRoot.SOURCE, "created.txt"),
                    PathArgument(ProbeRoot.REPOSITORY, "outside.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="isolated source mirror"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(outside.read_bytes() == _OUTSIDE_BYTES, "external file changed")


@pytest.mark.parametrize(
    "hook", ["gettempdir", "TemporaryDirectory", "copytree"]
)
def test_probe_mirror_ignores_post_import_workspace_provider_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A consumer must not redirect native probe roots or source mirroring."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "input.txt").write_bytes(_ADMITTED_INPUT)
    calls = 0

    def forged_provider(*args: object, **kwargs: object) -> object:
        nonlocal calls
        _ = args, kwargs
        calls += 1
        message = "late workspace provider was invoked"
        raise AssertionError(message)

    module = shutil if hook == "copytree" else tempfile
    with monkeypatch.context() as patched:
        patched.setattr(module, hook, forged_provider)
        result = run_probe_program(
            _program("native-workspace", "print('trusted')"),
            _context(source, tmp_path),
        )
    assert result.digested_commands == 1
    assert calls == 0
    assert (source / "input.txt").read_bytes() == _ADMITTED_INPUT


@pytest.mark.parametrize("location", ["direct", "nested", "symlink"])
def test_probe_rejects_temporary_parent_inside_source_before_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    """TMPDIR inside source must not trigger recursive mirror copying."""
    source = tmp_path / "source"
    source.mkdir()
    input_file = source / "input.txt"
    _ = input_file.write_bytes(_ADMITTED_INPUT)
    temporary_parent = source
    if location == "nested":
        temporary_parent = source / "nested-temp"
        temporary_parent.mkdir()
    elif location == "symlink":
        temporary_parent = tmp_path / "temp-alias"
        try:
            temporary_parent.symlink_to(source, target_is_directory=True)
        except OSError, NotImplementedError:
            pytest.skip("temporary-parent symlink creation unavailable")
    before = sorted(path.relative_to(source) for path in source.rglob("*"))
    context = replace(_context(source, tmp_path), enforce_source_immutable=False)

    def reject_copy(*_args: object, **_kwargs: object) -> Path:
        message = "source-rooted temporary directory reached recursive copy"
        raise AssertionError(message)

    with monkeypatch.context() as patch:
        patch.setattr(tempfile, "tempdir", str(temporary_parent))
        patch.setattr(probe_exec_module, "_NATIVE_COPYTREE", reject_copy)
        with pytest.raises(ProbeExecutionError, match="temporary.*source"):
            _ = run_probe_program(
                _program("source-tempdir", "print('unreachable')"), context
            )

    _expect(input_file.read_bytes() == _ADMITTED_INPUT, "input changed")
    _expect(
        sorted(path.relative_to(source) for path in source.rglob("*")) == before,
        "unsafe probe scratch root was created inside the source",
    )


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_probe_temporary_parent_resolution_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A broken temporary parent must reject before source mirroring."""
    source = tmp_path / "source"
    source.mkdir()
    input_file = source / "input.txt"
    _ = input_file.write_bytes(_ADMITTED_INPUT)

    def fail_temporary_parent() -> str:
        message = "temporary parent unavailable"
        raise failure_type(message)

    def reject_copy(*_args: object, **_kwargs: object) -> Path:
        message = "failed temporary-parent admission reached source copy"
        raise AssertionError(message)

    with monkeypatch.context() as patch:
        patch.setattr(
            probe_exec_module, "_NATIVE_GETTEMPDIR", fail_temporary_parent
        )
        patch.setattr(probe_exec_module, "_NATIVE_COPYTREE", reject_copy)
        with pytest.raises(
            ProbeExecutionError, match="temporary parent resolution failed"
        ):
            _ = run_probe_program(
                _program("failed-tempdir", "print('unreachable')"),
                replace(_context(source, tmp_path), enforce_source_immutable=False),
            )

    _expect(input_file.read_bytes() == _ADMITTED_INPUT, "source changed")


def test_probe_pins_temporary_parent_for_nested_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed global TMPDIR cannot redirect later scratch into source."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "input.txt").write_bytes(_ADMITTED_INPUT)
    safe_parent = tmp_path / "safe-temp"
    safe_parent.mkdir()
    original_copytree = shutil.copytree
    original_temporary_root = tempfile.TemporaryDirectory
    created_parents: list[Path] = []

    def change_tempdir_after_copy(
        root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        copied = original_copytree(root, destination, symlinks=symlinks)
        tempfile.tempdir = str(source)
        return copied

    def record_temporary_root(
        *, prefix: str, dir: Path
    ) -> tempfile.TemporaryDirectory[str]:
        del prefix
        created_parents.append(dir)
        return original_temporary_root(dir=dir)

    with monkeypatch.context() as patch:
        patch.setattr(tempfile, "tempdir", str(safe_parent))
        patch.setattr(
            probe_exec_module, "_NATIVE_COPYTREE", change_tempdir_after_copy
        )
        patch.setattr(
            probe_exec_module,
            "_NATIVE_TEMPORARY_DIRECTORY",
            record_temporary_root,
        )
        result = run_probe_program(
            _program("tempdir-stable", "print('stable')"),
            replace(_context(source, tmp_path), enforce_source_immutable=False),
        )

    _expect(result.digested_commands == 1, "probe did not execute")
    _expect(
        created_parents == [safe_parent, safe_parent],
        "nested scratch followed a changed global temp directory",
    )
    _expect(
        sorted(entry.name for entry in source.iterdir()) == ["input.txt"],
        "probe scratch redirected into candidate source",
    )


def test_mirror_snapshot_catches_copy_time_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not execute a mirror whose bytes differ from the admitted source."""
    source = tmp_path / "source"
    source.mkdir()
    input_file = source / "input.txt"
    _ = input_file.write_bytes(_ADMITTED_INPUT)
    actual_copytree = shutil.copytree

    def mutate_mirror_after_copy(
        source_root: Path, destination_root: Path, *, symlinks: bool = False
    ) -> Path:
        copied = actual_copytree(source_root, destination_root, symlinks=symlinks)
        _ = (copied / "input.txt").write_bytes(b"injected")
        return copied

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_COPYTREE", mutate_mirror_after_copy
    )
    context = replace(_context(source, tmp_path), enforce_source_immutable=False)
    program = ProbeProgram(
        "copy-time-drift",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
                digest_stdout=True,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="changed while creating"):
        _ = run_probe_program(program, context)
    _expect(input_file.read_bytes() == _ADMITTED_INPUT, "source was modified")


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_probe_mirror_copy_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Mirror copy host errors cannot escape public probe execution."""
    source = tmp_path / "source"
    source.mkdir()

    def denied_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        del source_root, destination, symlinks
        message = "copytree host failure"
        raise failure_type(message)

    monkeypatch.setattr(probe_exec_module, "_NATIVE_COPYTREE", denied_copy)
    with pytest.raises(ProbeExecutionError, match="source mirror creation failed"):
        _ = run_probe_program(
            _program("mirror-failure", "print('unreachable')"),
            _context(source, tmp_path),
        )


@pytest.mark.parametrize(
    "case",
    [
        (prefix, failure_type)
        for prefix in (_PROBE_BATCH_PREFIX, _PROBE_SCRATCH_PREFIX)
        for failure_type in (PermissionError, ValueError, RuntimeError)
    ],
)
def test_probe_temporary_workspace_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[Exception]],
) -> None:
    """Batch and scratch workspace creation must use typed probe errors."""
    failed_prefix, failure_type = case
    source = tmp_path / "source"
    source.mkdir()
    original_temporary_root = tempfile.TemporaryDirectory

    def denied_temporary_root(
        *, prefix: str, dir: Path
    ) -> tempfile.TemporaryDirectory[str]:
        if prefix == failed_prefix:
            message = "temporary root host failure"
            raise failure_type(message)
        return original_temporary_root(prefix=prefix, dir=dir)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_TEMPORARY_DIRECTORY", denied_temporary_root
    )
    with pytest.raises(ProbeExecutionError, match="temporary root failed"):
        _ = run_probe_program(
            _program("temporary-failure", "print('unreachable')"),
            _context(source, tmp_path),
        )


def test_missing_source_rejected_before_copy_without_immutability(
    tmp_path: Path,
) -> None:
    """Optional post-run immutability does not disable source admission."""
    missing = tmp_path / "missing"
    context = replace(_context(missing, tmp_path), enforce_source_immutable=False)
    with pytest.raises(ProbeExecutionError, match="source snapshot rejected"):
        _ = run_probe_program(_program("missing", "pass"), context)


def test_probe_records_reject_foreign_runtime_metadata() -> None:
    """Probe roots, paths, tool IDs, and executable records use exact types."""
    with pytest.raises(ProbeProgramError, match="exact ProbeRoot"):
        _ = PathArgument(cast("ProbeRoot", object()), "input.c")
    with pytest.raises(ProbeProgramError, match="exact string"):
        _ = PathArgument(ProbeRoot.SOURCE, cast("str", object()))
    with pytest.raises(ProbeProgramError, match="non-empty string"):
        _ = ToolExecutable(cast("str", object()))
    with pytest.raises(ProbeProgramError, match="exact ProbeRoot"):
        _ = RootedExecutable(cast("ProbeRoot", object()), "tool.exe")


def test_probe_transcript_rejects_malformed_direct_evidence() -> None:
    """Transcript records must preserve exact digest and selection metadata."""
    digest = hashlib.sha256(b"observed").digest()
    baseline = ProbeTranscript("probe", digest, 0)
    assert baseline.digest == digest
    malformed = (
        lambda: replace(baseline, probe_id=cast("str", object())),
        lambda: replace(baseline, probe_id=""),
        lambda: replace(
            baseline, digest=cast("bytes", cast("object", bytearray(digest)))
        ),
        lambda: replace(baseline, digest=b"short"),
        lambda: replace(baseline, digested_commands=True),
        lambda: replace(baseline, digested_commands=-1),
    )
    for build in malformed:
        with pytest.raises(ProbeProgramError, match="transcript"):
            _ = build()


def test_probe_command_rejects_boolean_aliases_and_mutable_inputs() -> None:
    """Process limits and selectors cannot rely on Python coercions."""
    base = ProbeCommand(executable=ToolExecutable(_PYTHON_TOOL))
    invalid = (
        lambda: replace(base, executable=cast("ToolExecutable", object())),
        lambda: replace(
            base,
            arguments=cast(
                "tuple[str | PathArgument, ...]",
                cast("object", ["-V"]),
            ),
        ),
        lambda: replace(base, arguments=(cast("str", object()),)),
        lambda: replace(base, stdin=cast("bytes", cast("object", bytearray()))),
        lambda: replace(base, expected_exit_code=True),
        lambda: replace(base, timeout_ms=True),
        lambda: replace(base, max_stdout_bytes=True),
        lambda: replace(base, max_stderr_bytes=True),
        lambda: replace(base, digest_stdout=cast("bool", cast("object", 1))),
        lambda: replace(base, digest_exit_code=cast("bool", cast("object", 1))),
    )
    for build in invalid:
        with pytest.raises(ProbeProgramError, match="probe"):
            _ = build()


def test_probe_argv_rejects_late_any_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late truth helper cannot approve NUL-bearing process arguments."""

    def construct_after_hook_swap() -> ProbeCommand:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "any", lambda values: False)
            return ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("--flag=\x00invalid",),
            )

    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = construct_after_hook_swap()


def test_probe_commands_reject_late_any_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late truth helper cannot authorize foreign probe command records."""
    commands = (cast("ProbeCommand", object()),)

    def construct_after_hook_swap() -> ProbeProgram:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "any", lambda values: False)
            return ProbeProgram("identity", commands)

    with pytest.raises(ProbeProgramError, match="foreign command"):
        _ = construct_after_hook_swap()


@pytest.mark.parametrize("helper", ["sorted", "set"])
def test_probe_tool_bindings_reject_late_order_hook(
    monkeypatch: pytest.MonkeyPatch,
    helper: str,
) -> None:
    """Late global sort or set hooks cannot admit duplicate tool bindings."""
    tools = (
        (_PYTHON_TOOL, Path(sys.executable)),
        (_PYTHON_TOOL, Path(sys.executable)),
    )

    def construct_after_hook_swap() -> ProbeRunContext:
        with monkeypatch.context() as patch:
            if helper == "sorted":
                patch.setattr(
                    builtins, "sorted", lambda values: list(tools_ids)
                )
            else:
                patch.setattr(builtins, "set", lambda values: list(values))
            return ProbeRunContext(Path("source"), Path("repo"), tools)

    tools_ids = (_PYTHON_TOOL, _PYTHON_TOOL)
    with pytest.raises(ProbeProgramError, match="unique and sorted"):
        _ = construct_after_hook_swap()


@pytest.mark.parametrize("helper", ["any", "sorted", "set"])
def test_probe_batch_rejects_late_global_validation_hooks(
    monkeypatch: pytest.MonkeyPatch,
    helper: str,
) -> None:
    """Batch validation cannot admit foreign or repeated probe programs."""
    batch = cast(
        "Callable[[object, object], tuple[ProbeProgram, ...]]",
        vars(probe_exec_module)["_validate_probe_batch"],
    )
    context = _context(Path("source"), Path("repo"))
    original = _program("identity-a", "pass")
    if helper == "any":
        invalid = (cast("ProbeProgram", object()),)
        message = "foreign program"
    else:
        invalid = (original, original)
        message = "unique sorted identifiers"

    def validate_after_hook_swap() -> tuple[ProbeProgram, ...]:
        with monkeypatch.context() as patch:
            if helper == "any":
                patch.setattr(builtins, "any", lambda values: False)
            elif helper == "sorted":
                patch.setattr(
                    builtins, "sorted", lambda values: [original.probe_id] * 2
                )
            else:
                patch.setattr(builtins, "set", lambda values: list(values))
            return batch(invalid, context)

    with pytest.raises(ProbeProgramError, match=message):
        _ = validate_after_hook_swap()


def test_probe_rejects_nul_command_and_rooted_path_arguments() -> None:
    """Malformed argv must fail at record admission, before process launch."""
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeCommand(
            executable=ToolExecutable(_PYTHON_TOOL),
            arguments=("--flag=" + chr(0),),
        )
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = PathArgument(ProbeRoot.SOURCE, "bad" + chr(0) + "file.txt")
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ToolExecutable("bad" + chr(0) + "tool")
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeRunContext(
            Path("bad" + chr(0) + "source"),
            Path("repo"),
            (),
        )
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeRunContext(
            Path("source"),
            Path("repo"),
            (("bad" + chr(0) + "tool", Path("tool")),),
        )


@pytest.mark.parametrize("unsafe", ["C:/outside", "C:relative"])
def test_rooted_probe_arguments_reject_windows_drive_paths(
    unsafe: str,
) -> None:
    """Windows drive paths cannot escape authorized rooted probe trees."""
    with pytest.raises(ProbeProgramError, match="unsafe probe relative path"):
        _ = PathArgument(ProbeRoot.SOURCE, unsafe)
    with pytest.raises(ProbeProgramError, match="unsafe probe relative path"):
        _ = RootedExecutable(ProbeRoot.REPOSITORY, unsafe)


@pytest.mark.parametrize(
    "unsafe",
    [
        "CON",
        "nested/AUX.txt",
        "nested/COM1",
        "nested/LPT².log",
        "nested/file:stream",
        "nested/trailing.",
        "nested/trailing ",
        "nested/bad|name",
    ],
)
def test_rooted_probe_paths_reject_reserved_windows_components(
    unsafe: str,
) -> None:
    """A portable probe path must never name a Windows device or stream."""
    with pytest.raises(ProbeProgramError, match="unsafe probe relative path"):
        _ = PathArgument(ProbeRoot.SOURCE, unsafe)
    with pytest.raises(ProbeProgramError, match="unsafe probe relative path"):
        _ = RootedExecutable(ProbeRoot.REPOSITORY, unsafe)


@pytest.mark.parametrize("kind", ["argv-path", "executable"])
def test_probe_rooted_execution_ignores_late_posix_parts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Accepted rooted paths cannot be redirected to a different file."""
    from pathlib import PurePosixPath

    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    _ = (nested / "admitted.bin").write_bytes(b"admitted")
    _ = (source / "decoy.bin").write_bytes(b"decoy")
    context = _context(source, tmp_path)
    argument = (
        PathArgument(ProbeRoot.SOURCE, "nested/admitted.bin")
        if kind == "argv-path"
        else RootedExecutable(ProbeRoot.SOURCE, "nested/admitted.bin")
    )
    native_parts = PurePosixPath.parts

    def forged_parts(value: PurePosixPath) -> tuple[str, ...]:
        if type(value) is PurePosixPath:
            return ("decoy.bin",)
        return cast("tuple[str, ...]", native_parts.__get__(value))

    resolved = cast(
        "Callable[[PathArgument | RootedExecutable, "
        "ProbeRunContext, Path], Path]",
        vars(probe_exec_module)["_rooted_path"],
    )
    with monkeypatch.context() as patch:
        patch.setattr(PurePosixPath, "parts", property(forged_parts))
        assert resolved(argument, context, tmp_path) == nested / "admitted.bin"


@pytest.mark.parametrize("unsafe", ["C:relative", "C:/outside"])
def test_rooted_probe_paths_ignore_late_ntpath_splitroot_spoof(
    unsafe: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer cannot redefine Windows drive names after module import."""
    import ntpath

    with monkeypatch.context() as patch:
        patch.setattr(ntpath, "splitroot", lambda path: ("", "", path))
        with pytest.raises(
            ProbeProgramError, match="unsafe probe relative path"
        ):
            _ = PathArgument(ProbeRoot.SOURCE, unsafe)
        with pytest.raises(
            ProbeProgramError, match="unsafe probe relative path"
        ):
            _ = RootedExecutable(ProbeRoot.SCRATCH, unsafe)


@pytest.mark.parametrize("kind", ["rooted-path", "rooted-tool", "raw-argv"])
def test_probe_rejects_surrogateescape_text_from_portable_records(
    kind: str,
) -> None:
    """Host-encodable byte escapes cannot form cross-host probe programs."""
    malformed = "nonutf8" + chr(0xDCFF)
    try:
        _ = os.fsencode(malformed)
    except UnicodeError:
        pytest.skip("host does not admit surrogateescape filesystem text")
    with pytest.raises(ProbeProgramError, match="portable UTF-8"):
        if kind == "rooted-path":
            _ = PathArgument(ProbeRoot.SOURCE, malformed)
        elif kind == "rooted-tool":
            _ = RootedExecutable(ProbeRoot.SCRATCH, malformed)
        else:
            _ = ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(malformed,),
            )


def test_probe_paths_reject_host_unencodable_metadata() -> None:
    """Process and filesystem paths must fail typed before any launch."""
    malformed = "unencodable" + chr(0xD800)
    host_encodable = True
    try:
        _ = os.fsencode(malformed)
    except UnicodeError:
        host_encodable = False
    if host_encodable:
        pytest.skip("host filesystem codec accepts the test surrogate")

    unsafe_path = Path(malformed)
    for build in (
        lambda: PathArgument(ProbeRoot.SOURCE, malformed),
        lambda: RootedExecutable(ProbeRoot.REPOSITORY, malformed),
        lambda: ProbeCommand(
            executable=ToolExecutable(_PYTHON_TOOL),
            arguments=(malformed,),
        ),
        lambda: ProbeRunContext(unsafe_path, Path("repository"), ()),
        lambda: ProbeRunContext(Path("source"), unsafe_path, ()),
        lambda: ProbeRunContext(
            Path("source"),
            Path("repository"),
            ((_PYTHON_TOOL, unsafe_path),),
        ),
    ):
        with pytest.raises(ProbeProgramError, match="filesystem-encodable"):
            _ = build()


class _ForeignProbePath(type(Path())):
    """A subclass could redirect probe path observations or execution."""

    def __str__(self) -> str:
        message = "foreign probe path conversion was evaluated"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("path_context", "build_context"),
    [
        (
            "probe source root",
            lambda foreign: ProbeRunContext(foreign, Path("repository"), ()),
        ),
        (
            "probe repository root",
            lambda foreign: ProbeRunContext(Path("source"), foreign, ()),
        ),
        (
            "probe tool path",
            lambda foreign: ProbeRunContext(
                Path("source"), Path("repository"), ((_PYTHON_TOOL, foreign),)
            ),
        ),
    ],
)
def test_probe_context_rejects_foreign_path_subclasses_before_conversion(
    path_context: str, build_context: Callable[[Path], ProbeRunContext]
) -> None:
    """Reject user-defined path hooks before admitting any execution root."""
    foreign = _ForeignProbePath("foreign")
    with pytest.raises(
        ProbeProgramError, match=f"{path_context} must use exact pathlib Path"
    ):
        _ = build_context(foreign)


def _hardlink_spoof_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    original = source / "input.txt"
    _ = original.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    alias = tmp_path / "alias.txt"
    try:
        os.link(original, alias)
    except OSError, NotImplementedError:
        pytest.skip("hard links unavailable")
    decoy = tmp_path / "decoy.txt"
    _ = decoy.write_text("unrelated", encoding="utf-8")
    return source, original, alias, decoy


def _assert_hardlink_disjoint(source: Path, alias: Path) -> None:
    check = cast(
        "Callable[[Path, Path], None]",
        vars(probe_exec_module)["_require_disjoint_source_inode"],
    )
    with pytest.raises(
        ProbeExecutionError, match="aliases original source inode"
    ):
        check(source, alias)


def test_probe_source_inode_set_ignores_late_frozenset_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late set hooks cannot hide source hardlinks during probe preflight."""
    source, original, alias, _ = _hardlink_spoof_fixture(tmp_path)
    native_frozenset = frozenset
    rejected = False
    guard = cast(
        "Callable[[Path, Path], None]",
        vars(probe_exec_module)["_require_disjoint_source_inode"],
    )
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "frozenset", lambda _: native_frozenset())
        try:
            guard(source, alias)
        except ProbeExecutionError:
            rejected = True
    assert rejected, "late frozenset hook hid source inode alias"
    assert original.read_text(encoding="utf-8") == _ORIGINAL_TEXT


def test_probe_disjoint_inode_rejects_post_import_path_stat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late pathlib hook cannot conceal a source hardlink."""
    source, original, alias, decoy = _hardlink_spoof_fixture(tmp_path)
    native_stat = Path.stat

    def forged_stat(
        path: Path, *, follow_symlinks: bool = True
    ) -> os.stat_result:
        if path == alias:
            return native_stat(decoy)
        return native_stat(path, follow_symlinks=follow_symlinks)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "stat", forged_stat)
        _assert_hardlink_disjoint(source, alias)
    assert original.read_text(encoding="utf-8") == _ORIGINAL_TEXT


def test_probe_disjoint_inode_rejects_post_import_os_stat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late os.stat hook cannot conceal a source hardlink."""
    source, original, alias, decoy = _hardlink_spoof_fixture(tmp_path)
    native_stat = os.stat

    def forged_stat(
        path: str | os.PathLike[str], *, follow_symlinks: bool = True
    ) -> os.stat_result:
        if Path(path) == alias:
            return native_stat(decoy)
        return native_stat(path, follow_symlinks=follow_symlinks)

    with monkeypatch.context() as patched:
        patched.setattr(os, "stat", forged_stat)
        _assert_hardlink_disjoint(source, alias)
    assert original.read_text(encoding="utf-8") == _ORIGINAL_TEXT


def test_probe_executable_rejects_foreign_status_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tool execution cannot be authorized by duck-typed file status."""
    tool = tmp_path / "tool.bin"
    _ = tool.write_bytes(b"synthetic tool")
    original_stat = Path.stat
    native = original_stat(tool)
    foreign = SimpleNamespace(st_mode=native.st_mode)

    def forged_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path == tool:
            return cast("os.stat_result", cast("object", foreign))
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", forged_stat
    )
    require_executable = cast(
        "Callable[[Path], None]",
        vars(probe_exec_module)["_require_executable"],
    )
    with pytest.raises(ProbeExecutionError, match="native filesystem status"):
        require_executable(tool)


@pytest.mark.parametrize("role", ["source", "repository"])
def test_probe_inode_status_rejects_forged_foreign_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """A forgeable status cannot attest the inode-disjointness boundary."""
    source = tmp_path / "source"
    source.mkdir()
    leaf = source / "input.bin"
    _ = leaf.write_bytes(b"trusted original source")
    repository_path = tmp_path / "external.bin"
    _ = repository_path.write_bytes(b"external data")
    target = leaf if role == "source" else repository_path
    original_stat = Path.stat
    forged = SimpleNamespace(
        st_dev=12345,
        st_ino=56789,
        st_mode=0o100644,
        st_nlink=1,
    )
    consumed = False

    def fake_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal consumed
        if path == target:
            consumed = True
            return cast("os.stat_result", cast("object", forged))
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fake_stat
    )
    if role == "source":
        source_inodes = cast(
            "Callable[[Path], frozenset[tuple[int, int]]]",
            vars(probe_exec_module)["_source_file_inode_keys"],
        )
        verify: Callable[[], object] = lambda: source_inodes(source)
    else:
        repository_status = cast(
            "Callable[[Path], os.stat_result | None]",
            vars(probe_exec_module)["_repository_inode_status"],
        )
        verify = lambda: repository_status(repository_path)
    with pytest.raises(ProbeExecutionError, match="native.*inode|inode.*native"):
        _ = verify()
    _expect(consumed, "forged inode status was not tested")


class _HostileProbeFilesystemError(OSError):
    """Host callback errors must not execute their display hooks."""

    @override
    def __str__(self) -> str:
        message = "hostile probe host formatter executed"
        raise AssertionError(message)

    @override
    def __repr__(self) -> str:
        message = "hostile probe host representation executed"
        raise AssertionError(message)


class _HostileProbeSnapshotError(ExactTreeError):
    """Delegated source snapshots may return foreign error subclasses."""

    @override
    def __str__(self) -> str:
        message = "hostile probe snapshot formatter executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("root", "root resolution failed"),
        ("rooted_path", "path resolution failed"),
        ("tool", "tool resolution failed"),
        ("temporary", "temporary root failed"),
        ("snapshot", "snapshot rejected"),
        ("source_inode", "source inode status failed"),
        ("repository_inode", "repository path status failed"),
        ("repository_argument", "repository argument resolution failed"),
    ],
)
def test_probe_host_boundaries_reject_foreign_formatters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    expected: str,
) -> None:
    """Reject malicious filesystem exceptions while retaining their cause."""
    source = tmp_path / "source"
    source.mkdir()
    source_leaf = source / "input.txt"
    _ = source_leaf.write_bytes(b"trusted")
    external = tmp_path / "external.txt"
    _ = external.write_bytes(b"repository bytes")
    context = _context(source, tmp_path)
    failure = (
        _HostileProbeSnapshotError("foreign tree snapshot")
        if operation == "snapshot"
        else _HostileProbeFilesystemError("foreign host status")
    )
    invoke: Callable[[], object]
    if operation in {"root", "rooted_path", "tool", "repository_argument"}:
        original = Path.resolve
        target = {
            "root": tmp_path,
            "rooted_path": external,
            "tool": Path(sys.executable),
            "repository_argument": external,
        }[operation]
        resolutions = 0

        def fail_resolve(path: Path, *, strict: bool = False) -> Path:
            nonlocal resolutions
            if path == target:
                resolutions += 1
                if operation != "repository_argument" or resolutions == 2:
                    raise failure
            return original(path, strict=strict)

        monkeypatch.setattr(
            probe_exec_module, "_NATIVE_PATH_RESOLVE", fail_resolve
        )
        if operation == "root":
            require_root = cast(
                "Callable[[Path, str], Path]",
                vars(probe_exec_module)["_resolved_root"],
            )
            invoke = lambda: require_root(tmp_path, "repository")
        elif operation == "rooted_path":
            rooted_path = cast(
                "Callable[[PathArgument, ProbeRunContext, Path], Path]",
                vars(probe_exec_module)["_rooted_path"],
            )
            invoke = lambda: rooted_path(
                PathArgument(ProbeRoot.REPOSITORY, external.name),
                context,
                tmp_path / "scratch",
            )
        elif operation == "tool":
            tool_path = cast(
                "Callable[[Path], Path]",
                vars(probe_exec_module)["_resolved_tool_path"],
            )
            invoke = lambda: tool_path(target)
        else:
            require_disjoint = cast(
                "Callable[[PathArgument, ProbeRunContext, Path], None]",
                vars(probe_exec_module)["_require_repository_argument_disjoint"],
            )
            invoke = lambda: require_disjoint(
                PathArgument(ProbeRoot.REPOSITORY, external.name),
                context,
                source,
            )
    elif operation == "temporary":

        def fail_temp(*, prefix: str, dir: Path) -> tempfile.TemporaryDirectory[str]:
            _ = prefix, dir
            raise failure

        monkeypatch.setattr(
            probe_exec_module, "_NATIVE_TEMPORARY_DIRECTORY", fail_temp
        )
        temp_root = cast(
            "Callable[..., tempfile.TemporaryDirectory[str]]",
            vars(probe_exec_module)["_temporary_probe_root"],
        )
        invoke = lambda: temp_root("test-probe-", parent=tmp_path)
    elif operation == "snapshot":

        def fail_snapshot(root: Path) -> object:
            _ = root
            raise failure

        monkeypatch.setattr(probe_exec_module, "snapshot_tree", fail_snapshot)
        snapshot = cast(
            "Callable[[Path, str], object]",
            vars(probe_exec_module)["_snapshot_probe_tree"],
        )
        invoke = lambda: snapshot(source, "source")
    else:
        original_stat = Path.stat
        target = source_leaf if operation == "source_inode" else external

        def fail_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            if path == target:
                raise failure
            return original_stat(path, follow_symlinks=follow_symlinks)

        monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fail_stat
    )
        if operation == "source_inode":
            source_inodes = cast(
                "Callable[[Path], frozenset[tuple[int, int]]]",
                vars(probe_exec_module)["_source_file_inode_keys"],
            )
            invoke = lambda: source_inodes(source)
        else:
            repo_stat = cast(
                "Callable[[Path], os.stat_result | None]",
                vars(probe_exec_module)["_repository_inode_status"],
            )
            invoke = lambda: repo_stat(external)
    with pytest.raises(ProbeExecutionError, match=expected) as caught:
        _ = invoke()
    _expect(caught.value.__cause__ is failure, "foreign failure cause was lost")


def test_probe_mirror_host_failure_does_not_format_foreign_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hostile mirror provider cannot authorize probe execution."""
    source = tmp_path / "source"
    source.mkdir()
    failure = _HostileProbeFilesystemError("foreign mirror failure")

    def fail_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        _ = source_root, destination, symlinks
        raise failure

    monkeypatch.setattr(probe_exec_module, "_NATIVE_COPYTREE", fail_copy)
    with pytest.raises(
        ProbeExecutionError, match="source mirror creation failed"
    ) as caught:
        _ = run_probe_program(
            _program("hostile-mirror", "print('unreachable')"),
            _context(source, tmp_path),
        )
    _expect(caught.value.__cause__ is failure, "mirror failure cause was lost")


def test_probe_executable_status_error_does_not_format_foreign_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hostile host fault cannot escape through its string formatter."""
    tool = tmp_path / "tool.bin"
    _ = tool.write_bytes(b"synthetic tool")
    original_stat = Path.stat

    class HostileStatusError(OSError):
        @override
        def __str__(self) -> str:
            message = "hostile status formatter executed"
            raise AssertionError(message)

    failure = HostileStatusError("untrusted filesystem fault")

    def fail_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path == tool:
            raise failure
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_STAT", fail_stat
    )
    require_executable = cast(
        "Callable[[Path], None]",
        vars(probe_exec_module)["_require_executable"],
    )
    with pytest.raises(ProbeExecutionError, match="status failed") as caught:
        require_executable(tool)
    assert caught.value.__cause__ is failure


def test_probe_executable_launch_failure_is_wrapped(tmp_path: Path) -> None:
    """Regular but non-executable tool files remain inside probe errors."""
    source = tmp_path / "source"
    source.mkdir()
    bad_executable = tmp_path / "text-only.exe"
    _ = bad_executable.write_bytes(b"not an executable")
    program = _program("bad-tool", "pass")
    context = ProbeRunContext(
        source_root=source,
        repository_root=tmp_path,
        tools=((_PYTHON_TOOL, bad_executable),),
    )
    with pytest.raises(ProbeExecutionError, match="launch failed"):
        _ = run_probe_program(program, context)


@pytest.mark.parametrize("invalid", ["bad\x00id", "bad" + chr(0xD800)])
def test_probe_logical_identifiers_require_portable_utf8(invalid: str) -> None:
    """Reject unencodable or NUL-bearing probe identifiers."""
    command = ProbeCommand(executable=ToolExecutable(_PYTHON_TOOL))
    digest = hashlib.sha256(b"probe transcript").digest()
    for build in (
        lambda: ToolExecutable(invalid),
        lambda: ProbeProgram(invalid, (command,)),
        lambda: ProbeTranscript(invalid, digest, 0),
        lambda: ProbeRunContext(
            Path("source"),
            Path("repository"),
            ((invalid, Path(sys.executable)),),
        ),
    ):
        with pytest.raises(ProbeProgramError, match="probe"):
            _ = build()


@pytest.mark.parametrize("role", ["rooted-escape", "repository-overlap"])
def test_probe_rejects_mutated_containment_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """A replaced pathlib containment hook cannot authorize unsafe inputs."""
    source = tmp_path / "source"
    _ = (source / "victim.txt").parent.mkdir()
    _ = (source / "victim.txt").write_bytes(b"source bytes")
    repository = tmp_path / "repository"
    repository.mkdir()
    context = _context(
        source, tmp_path if role == "repository-overlap" else repository
    )
    if role == "rooted-escape":
        outside = tmp_path / "outside"
        outside.mkdir()
        _ = (outside / "private.txt").write_bytes(b"unrelated bytes")
        try:
            (repository / "alias").symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
        native_relative = Path.relative_to

        def forged_relative(
            path: Path, other: object, *, walk_up: bool = False
        ) -> Path:
            if path == outside / "private.txt":
                return Path(".")
            return native_relative(path, other, walk_up=walk_up)

        monkeypatch.setattr(Path, "relative_to", forged_relative)
        rooted_path = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], Path]",
            vars(probe_exec_module)["_rooted_path"],
        )
        with pytest.raises(
            ProbeExecutionError, match="escapes authorized root"
        ):
            _ = rooted_path(
                PathArgument(ProbeRoot.REPOSITORY, "alias/private.txt"),
                context,
                tmp_path / "scratch",
            )
    else:
        native_is_relative = Path.is_relative_to

        def forged_inside(path: Path, other: object) -> bool:
            if path == source / "victim.txt" and other == source:
                return False
            return native_is_relative(path, other)

        monkeypatch.setattr(Path, "is_relative_to", forged_inside)
        require_disjoint = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], None]",
            vars(probe_exec_module)["_require_repository_argument_disjoint"],
        )
        with pytest.raises(
            ProbeExecutionError, match="overlaps original source"
        ):
            require_disjoint(
                PathArgument(ProbeRoot.REPOSITORY, "source/victim.txt"),
                context,
                source,
            )


@pytest.mark.parametrize(
    "role", ["root", "rooted", "tool", "repository-second", "temporary"]
)
def test_probe_rejects_foreign_resolved_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """No foreign path result may attest containment, tools or temp roots."""
    source = tmp_path / "source"
    source.mkdir()
    repository_file = tmp_path / "repository.txt"
    _ = repository_file.write_bytes(b"repository bytes")
    context = _context(source, tmp_path)
    native_resolve = Path.resolve
    targeted = {
        "root": tmp_path,
        "rooted": repository_file,
        "tool": Path(sys.executable),
        "repository-second": repository_file,
        "temporary": Path(tempfile.gettempdir()),
    }[role]
    calls = 0

    class ForgedResolvedPath(type(Path())):
        """Foreign subclass may override containment or command rendering."""

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        result = native_resolve(path, strict=strict)
        if path == targeted:
            calls += 1
            if role != "repository-second" or calls == 2:
                return ForgedResolvedPath(result)
        return result

    monkeypatch.setattr(
        probe_exec_module, "_NATIVE_PATH_RESOLVE", forged_resolve
    )
    if role == "root":
        require_root = cast(
            "Callable[[Path, str], Path]",
            vars(probe_exec_module)["_resolved_root"],
        )
        invoke: Callable[[], object] = lambda: require_root(
            tmp_path, "repository"
        )
    elif role == "rooted":
        rooted_path = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], Path]",
            vars(probe_exec_module)["_rooted_path"],
        )
        invoke = lambda: rooted_path(
            PathArgument(ProbeRoot.REPOSITORY, repository_file.name),
            context,
            tmp_path / "scratch",
        )
    elif role == "tool":
        require_tool = cast(
            "Callable[[Path], Path]",
            vars(probe_exec_module)["_resolved_tool_path"],
        )
        invoke = lambda: require_tool(targeted)
    elif role == "repository-second":
        require_disjoint = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], None]",
            vars(probe_exec_module)["_require_repository_argument_disjoint"],
        )
        invoke = lambda: require_disjoint(
            PathArgument(ProbeRoot.REPOSITORY, repository_file.name),
            context,
            source,
        )
    else:
        invoke = lambda: run_probe_program(
            _program("foreign-temporary-root", "pass"), context
        )
    with pytest.raises(ProbeExecutionError, match="native resolved Path"):
        _ = invoke()
    assert calls >= 1


@pytest.mark.parametrize(
    "case", ["root", "tool", "rooted-escape", "repository-source-alias"]
)
def test_probe_rejects_late_host_realpath_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Pinned Path.resolve must not consume a late host realpath callback."""
    source = tmp_path / "source"
    source.mkdir()
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "private.txt").write_bytes(b"outside")
    _ = (source / "private.txt").write_bytes(b"source")
    alias = repository / "alias"
    try:
        alias.symlink_to(
            source if case == "repository-source-alias" else outside,
            target_is_directory=True,
        )
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks unavailable")
    context = _context(source, repository)
    original_realpath = os.path.realpath
    forged_calls = 0
    targeted = {
        "root": source,
        "tool": outside / "private.txt",
        "rooted-escape": alias / "private.txt",
        "repository-source-alias": alias / "private.txt",
    }[case]

    def forged_realpath(path: str | os.PathLike[str], *, strict: bool = False) -> str:
        nonlocal forged_calls
        if os.fspath(path) == os.fspath(targeted):
            forged_calls += 1
            if case == "root":
                return os.fspath(outside)
            if case == "tool":
                return os.fspath(source / "private.txt")
            return os.fspath(targeted)
        return cast("str", original_realpath(path, strict=strict))

    if case == "root":
        require_root = cast(
            "Callable[[Path, str], Path]", vars(probe_exec_module)["_resolved_root"]
        )
        invoke: Callable[[], object] = lambda: require_root(source, "source")
    elif case == "tool":
        require_tool = cast(
            "Callable[[Path], Path]", vars(probe_exec_module)["_resolved_tool_path"]
        )
        invoke = lambda: require_tool(targeted)
    elif case == "rooted-escape":
        rooted = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], Path]",
            vars(probe_exec_module)["_rooted_path"],
        )
        invoke = lambda: rooted(
            PathArgument(ProbeRoot.REPOSITORY, "alias/private.txt"),
            context,
            tmp_path / "scratch",
        )
    else:
        require_disjoint = cast(
            "Callable[[PathArgument, ProbeRunContext, Path], None]",
            vars(probe_exec_module)["_require_repository_argument_disjoint"],
        )
        invoke = lambda: require_disjoint(
            PathArgument(ProbeRoot.REPOSITORY, "alias/private.txt"),
            context,
            source,
        )

    with monkeypatch.context() as patch:
        patch.setattr(os.path, "realpath", forged_realpath)
        with pytest.raises(ProbeExecutionError, match="native host resolver changed"):
            _ = invoke()
    assert forged_calls == 0, "late host realpath callback was consulted"


def test_probe_rejects_host_resolver_mutation_during_native_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host resolver changed mid-preflight cannot survive attestation."""
    source = tmp_path / "source"
    source.mkdir()
    native_resolve = Path.resolve
    native_realpath = os.path.realpath
    changed = False

    def replace_host_resolver(path: Path, *, strict: bool = False) -> Path:
        nonlocal changed
        resolved = native_resolve(path, strict=strict)
        patch.setattr(os.path, "realpath", lambda value, **_: value)
        changed = True
        return resolved

    with monkeypatch.context() as patch:
        patch.setattr(probe_exec_module, "_NATIVE_PATH_RESOLVE", replace_host_resolver)
        require_root = cast(
            "Callable[[Path, str], Path]", vars(probe_exec_module)["_resolved_root"]
        )
        with pytest.raises(ProbeExecutionError, match="native host resolver changed"):
            _ = require_root(source, "source")
    assert changed, "native resolution hook was not exercised"
    assert os.path.realpath is native_realpath


def _probe_host_alias(tmp_path: Path) -> tuple[Path, Path]:
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks unavailable")
    return alias, outside


@pytest.mark.parametrize(
    "dependency", ["lstat", "readlink", "getcwd", "symlink-classifier"]
)
def test_probe_rejects_late_host_resolver_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dependency: str
) -> None:
    """Original realpath still calls replaceable host filesystem helpers."""
    alias, outside = _probe_host_alias(tmp_path)
    native_lstat = os.lstat

    def forged_lstat(path: str | os.PathLike[str]) -> os.stat_result:
        selected = tmp_path if os.fspath(path) == os.fspath(alias) else path
        return native_lstat(selected)

    def forged_readlink(path: str | os.PathLike[str]) -> str:
        return f"missing-{os.fspath(path)}"

    def forged_getcwd() -> str:
        return os.fspath(outside)

    def forged_islink(mode: int) -> bool:
        return mode < 0

    owner, attribute, replacement = {
        "lstat": (os, "lstat", forged_lstat),
        "readlink": (os, "readlink", forged_readlink),
        "getcwd": (os, "getcwd", forged_getcwd),
        "symlink-classifier": (stat, "S_ISLNK", forged_islink),
    }[dependency]
    with monkeypatch.context() as patch:
        patch.setattr(owner, attribute, replacement)
        require_root = cast(
            "Callable[[Path, str], Path]",
            vars(probe_exec_module)["_resolved_root"],
        )
        with pytest.raises(
            ProbeExecutionError, match="native host resolver changed"
        ):
            _ = require_root(alias, "repository")
    assert alias.resolve() == outside


def test_probe_rejects_host_dependency_mutation_during_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dependency replaced while native Path.resolve runs fails closed."""
    root = tmp_path / "root"
    root.mkdir()
    native_resolve = Path.resolve
    native_readlink = os.readlink
    changed = False

    def forged_readlink(path: str | os.PathLike[str]) -> str:
        return f"forged-{os.fspath(path)}"

    def replace_readlink(path: Path, *, strict: bool = False) -> Path:
        nonlocal changed
        result = native_resolve(path, strict=strict)
        patch.setattr(os, "readlink", forged_readlink)
        changed = True
        return result

    with monkeypatch.context() as patch:
        patch.setattr(
            probe_exec_module, "_NATIVE_PATH_RESOLVE", replace_readlink
        )
        require_root = cast(
            "Callable[[Path, str], Path]",
            vars(probe_exec_module)["_resolved_root"],
        )
        with pytest.raises(
            ProbeExecutionError, match="native host resolver changed"
        ):
            _ = require_root(root, "repository")
    assert changed, "native resolve was not exercised"
    assert os.readlink is native_readlink


@pytest.mark.parametrize(
    "case",
    [(root, executable) for root in ProbeRoot for executable in (False, True)],
)
def test_probe_rooted_path_rejects_late_joinpath_redirection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[ProbeRoot, bool],
) -> None:
    """A later joinpath hook cannot redirect an admitted structured path."""
    root, executable = case
    source = tmp_path / "source"
    source.mkdir()
    repository = tmp_path / "repository"
    repository.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    context = _context(source, repository)
    selected = {
        ProbeRoot.SOURCE: source,
        ProbeRoot.REPOSITORY: repository,
        ProbeRoot.SCRATCH: scratch,
    }[root]
    _ = (selected / "requested.txt").write_bytes(b"approved")
    _ = (selected / "other.txt").write_bytes(b"other")
    native_joinpath = Path.joinpath
    calls = 0

    def forged_joinpath(path: Path, *parts: str) -> Path:
        nonlocal calls
        if path == selected and parts == ("requested.txt",):
            calls += 1
            return native_joinpath(path, "other.txt")
        return native_joinpath(path, *parts)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "joinpath", forged_joinpath)
        with pytest.raises(
            ProbeExecutionError, match="native path hooks changed"
        ):
            _ = cast(
                "Callable[..., Path]", vars(probe_exec_module)["_rooted_path"]
            )(
                RootedExecutable(root, "requested.txt")
                if executable
                else PathArgument(root, "requested.txt"),
                context,
                scratch,
            )
    assert calls == 0, "late joinpath hook was consulted"


@pytest.mark.parametrize("hook", ["getattribute", "cached-descriptor"])
def test_probe_context_rejects_late_path_cache_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Original Path.__str__ must not trust consumer-replaceable cache hooks."""
    invalid = tmp_path / "bad\x00root"
    forged_spelling = str(tmp_path / "valid-root")
    original_getter = Path.__getattribute__
    calls = 0

    def forged_getter(path: Path, name: str) -> object:
        nonlocal calls
        if path is invalid and name == "_str":
            calls += 1
            return forged_spelling
        return original_getter(path, name)

    native_cached = cast("MemberDescriptorType", PurePath.__dict__["_str"])

    def forged_cached(path: PurePath) -> str:
        nonlocal calls
        if path is invalid:
            calls += 1
            return forged_spelling
        return cast("str", native_cached.__get__(path, PurePath))

    with monkeypatch.context() as patch:
        if hook == "getattribute":
            patch.setattr(Path, "__getattribute__", forged_getter)
        else:
            patch.setattr(PurePath, "_str", property(forged_cached))
        with pytest.raises(ProbeProgramError, match="path hooks changed|NUL"):
            _ = ProbeRunContext(invalid, tmp_path, ())
    assert calls == 0, "consumer path-cache hook was consulted"


@pytest.mark.parametrize("hook", ["getattribute", "cached-descriptor"])
def test_probe_executable_status_rejects_late_path_cache_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Executable status cannot be obtained from a forged native path cache."""
    missing = tmp_path / "missing-executable"
    admitted = Path(sys.executable)
    admitted_spelling = str(admitted)
    original_getter = Path.__getattribute__
    calls = 0

    def forged_getter(path: Path, name: str) -> object:
        nonlocal calls
        if path is missing and name == "_str":
            calls += 1
            return admitted_spelling
        return original_getter(path, name)

    native_cached = cast("MemberDescriptorType", PurePath.__dict__["_str"])

    def forged_cached(path: PurePath) -> str:
        nonlocal calls
        if path is missing:
            calls += 1
            return admitted_spelling
        return cast("str", native_cached.__get__(path, PurePath))

    with monkeypatch.context() as patch:
        if hook == "getattribute":
            patch.setattr(Path, "__getattribute__", forged_getter)
        else:
            patch.setattr(PurePath, "_str", property(forged_cached))
        require_executable = cast(
            "Callable[[Path], None]", vars(probe_exec_module)["_require_executable"]
        )
        with pytest.raises(ProbeExecutionError, match="path hooks changed"):
            require_executable(missing)
    assert calls == 0, "consumer path-cache hook authorized a foreign tool"


@pytest.mark.parametrize("operation", ["resolve-tool", "executable-status"])
def test_probe_execution_rejects_late_path_str_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Launch preflight must reject substituted host path string methods."""
    tool = tmp_path / "selected-tool"
    foreign = Path(sys.executable)
    _ = tool.write_bytes(b"untrusted")
    foreign_spelling = str(foreign)
    original_str = Path.__str__
    calls = 0

    def forged_str(path: Path) -> str:
        nonlocal calls
        if path is tool:
            calls += 1
            return foreign_spelling
        return original_str(path)

    if operation == "resolve-tool":
        require_path = cast(
            "Callable[[Path], Path]", vars(probe_exec_module)["_resolved_tool_path"]
        )
        invoke: Callable[[], object] = lambda: require_path(tool)
    else:
        require_status = cast(
            "Callable[[Path], None]", vars(probe_exec_module)["_require_executable"]
        )
        invoke = lambda: require_status(tool)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "__str__", forged_str)
        with pytest.raises(ProbeExecutionError, match="native path hooks changed"):
            _ = invoke()
    assert calls == 0, "late host path-string callback was consulted"


@pytest.mark.parametrize("role", ["root", "tool"])
def test_probe_rejects_late_path_with_segments_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """Captured Path.resolve must not invoke a late path-constructor hook."""
    selected = tmp_path / "admitted"
    foreign = tmp_path / "foreign"
    selected.mkdir()
    foreign.mkdir()
    original_with_segments = Path.with_segments
    called = 0

    def forged_segments(path: Path, *segments: str | os.PathLike[str]) -> Path:
        nonlocal called
        if path is selected:
            called += 1
            return foreign
        return original_with_segments(path, *segments)

    if role == "root":
        require_root = cast(
            "Callable[[Path, str], Path]", vars(probe_exec_module)["_resolved_root"]
        )
        invoke: Callable[[], object] = lambda: require_root(selected, "source")
    else:
        require_tool = cast(
            "Callable[[Path], Path]", vars(probe_exec_module)["_resolved_tool_path"]
        )
        invoke = lambda: require_tool(selected)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "with_segments", forged_segments)
        with pytest.raises(ProbeExecutionError, match="native path hooks changed"):
            _ = invoke()
    assert called == 0, "late path-constructor hook was consulted"


def test_probe_program_and_context_require_immutable_exact_records(
    tmp_path: Path,
) -> None:
    """Batch metadata is validated before filesystem or process work."""
    command = ProbeCommand(executable=ToolExecutable(_PYTHON_TOOL))
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = ProbeProgram(
            "probe",
            cast("tuple[ProbeCommand, ...]", cast("object", [command])),
        )
    with pytest.raises(ProbeProgramError, match="foreign command"):
        _ = ProbeProgram("probe", (cast("ProbeCommand", object()),))

    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = ProbeRunContext(
            source,
            tmp_path,
            cast(
                "tuple[tuple[str, Path], ...]",
                cast("object", [(_PYTHON_TOOL, Path(sys.executable))]),
            ),
        )
    with pytest.raises(ProbeProgramError, match="exact boolean"):
        _ = ProbeRunContext(
            source,
            tmp_path,
            ((_PYTHON_TOOL, Path(sys.executable)),),
            enforce_source_immutable=cast("bool", cast("object", 1)),
        )

    context = _context(source, tmp_path)
    program = ProbeProgram("probe", (command,))
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = run_probe_programs(
            cast("tuple[ProbeProgram, ...]", cast("object", [program])),
            context,
        )
    with pytest.raises(ProbeProgramError, match="foreign program"):
        _ = run_probe_programs((cast("ProbeProgram", object()),), context)
    with pytest.raises(ProbeProgramError, match="exact ProbeRunContext"):
        _ = run_probe_programs((program,), cast("ProbeRunContext", object()))


def test_probe_command_rejects_late_type_spoofed_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type verdict cannot admit mutable process stdin."""
    foreign = bytearray(b"input")
    native_type = type
    rejected = False
    executable = ToolExecutable(_PYTHON_TOOL)

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = ProbeCommand(
                executable=executable,
                stdin=cast("bytes", cast("object", foreign)),
            )
        except ProbeProgramError:
            rejected = True
    assert rejected, "late type hook admitted mutable process stdin"


def test_probe_command_rejects_late_type_spoofed_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type verdict cannot admit fractional process timeouts."""
    foreign = 1.5
    native_type = type
    rejected = False
    executable = ToolExecutable(_PYTHON_TOOL)

    def forged_type(value: object) -> type:
        return int if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = ProbeCommand(
                executable=executable,
                timeout_ms=cast("int", cast("object", foreign)),
            )
        except ProbeProgramError:
            rejected = True
    assert rejected, "late type hook admitted a fractional timeout"


def test_probe_transcript_rejects_late_len_spoofed_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged digest length cannot admit a truncated probe transcript."""
    foreign = b"short"
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is foreign:
            return hashlib.sha256().digest_size
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = ProbeTranscript("probe", foreign, 1)
        except ProbeProgramError:
            rejected = True
    assert rejected, "late len hook admitted a truncated transcript digest"


def test_probe_stdout_digest_ignores_late_len_framing_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transcript frames must use native output length after tool hooks."""
    update = cast(
        "Callable[[object, int, bytes], None]",
        vars(probe_exec_module)["_update_stdout_digest"],
    )
    stdout = b"stable output"
    original = hashlib.sha256()
    update(original, 0, stdout)
    expected = original.digest()
    native_len = len

    def forged_len(value: object) -> int:
        if value is stdout:
            return native_len(stdout) + 1
        return native_len(cast("bytes", value))

    altered = hashlib.sha256()
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        update(altered, 0, stdout)
    assert altered.digest() == expected, (
        "late len hook changed transcript framing"
    )


def test_probe_tool_identifier_rejects_late_string_type_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign string-compatible identifiers cannot masquerade as exact str."""
    foreign = cast("str", cast("object", UserString("python")))
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", UserString)
        try:
            _ = ToolExecutable(foreign)
        except ProbeProgramError:
            rejected = True
    assert rejected, "late str class swap admitted a foreign tool identifier"


def test_probe_exit_digest_ignores_late_int_framing_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """External integer conversion cannot rewrite selected exit status."""
    update = cast(
        "Callable[[object, int, int], None]",
        vars(probe_exec_module)["_update_exit_digest"],
    )
    original = hashlib.sha256()
    update(original, 0, 37)
    expected = original.digest()

    def forged_int(value: object) -> int:
        del value
        return 0

    altered = hashlib.sha256()
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", forged_int)
        update(altered, 0, 37)
    assert altered.digest() == expected, "late int hook rewrote exit framing"


@pytest.mark.parametrize(
    "role", ["raw-argv", "relative-path", "source-root", "tool-path"]
)
def test_probe_admission_ignores_late_fsencode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    role: str,
) -> None:
    """A post-import filesystem codec hook cannot change probe admission."""
    constructors = {
        "raw-argv": lambda: ProbeCommand(
            ToolExecutable(_PYTHON_TOOL), arguments=("stable-argument",)
        ),
        "relative-path": lambda: PathArgument(ProbeRoot.SOURCE, "src/a.c"),
        "source-root": lambda: ProbeRunContext(tmp_path, tmp_path, ()),
        "tool-path": lambda: ProbeRunContext(
            tmp_path, tmp_path, ((_PYTHON_TOOL, tmp_path / "tool"),)
        ),
    }
    baseline = constructors[role]()
    calls = 0

    def forged_fsencode(value: object) -> bytes:
        nonlocal calls
        del value
        calls += 1
        raise AssertionError("consumer filesystem-codec hook executed")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsencode", forged_fsencode)
        observed = constructors[role]()
    assert observed == baseline
    assert calls == 0, "consumer filesystem-codec hook was consulted"


@pytest.mark.parametrize("invalid", [False, True])
def test_probe_root_admission_ignores_late_path_string_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: bool,
) -> None:
    """Native probe root admission ignores later Path formatter hooks."""
    source = tmp_path / ("bad\x00root" if invalid else "safe-root")

    def forged_path_string(value: Path) -> str:
        del value
        return "safe-root" if invalid else "bad\x00root"

    with monkeypatch.context() as patch:
        patch.setattr(Path, "__str__", forged_path_string)
        if invalid:
            with pytest.raises(ProbeProgramError, match="NUL"):
                _ = ProbeRunContext(source, tmp_path, ())
        else:
            _ = ProbeRunContext(source, tmp_path, ())


def test_native_filesystem_encoding_captures_platform_errors() -> None:
    """All native admission codecs capture the host's error policy."""
    # A separate interpreter avoids reloading imported dataclass identities.
    script = (
        "import sys\n"
        "sys.getfilesystemencodeerrors = lambda: 'surrogatepass'\n"
        "from algorithms.diff import exact, probe_exec, provenance\n"
        "assert all(m._FILESYSTEM_ERRORS == 'surrogatepass' "
        "for m in (exact, probe_exec, provenance))\n"
    )
    result = subprocess.run(
        (sys.executable, "-c", script),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "record", ["path", "tool", "rooted", "command", "program", "context", "transcript"]
)
def test_probe_record_constructor_rejects_late_validator_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Late class post-init hooks cannot admit invalid portable probe records."""
    tool = ToolExecutable(_PYTHON_TOOL)
    command = ProbeCommand(executable=tool)
    base = {
        "path": PathArgument(ProbeRoot.SOURCE, "source.bin"),
        "tool": tool,
        "rooted": RootedExecutable(ProbeRoot.SCRATCH, "tool.exe"),
        "command": command,
        "program": ProbeProgram("probe", (command,)),
        "context": _context(tmp_path / "source", tmp_path),
        "transcript": ProbeTranscript("probe", bytes(32), 1),
    }[record]
    invalid = cast("dict[str, object]", {
        "path": {"relative_path": "../unsafe"},
        "tool": {"tool_id": ""},
        "rooted": {"root": object()},
        "command": {"timeout_ms": 0},
        "program": {"commands": ()},
        "context": {"enforce_source_immutable": 1},
        "transcript": {"digest": b"short"},
    }[record])
    calls = 0

    def skip_validation(_value: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patch:
        patch.setattr(type(base), "__post_init__", skip_validation)
        with pytest.raises(ProbeProgramError):
            _ = replace(base, **invalid)
    assert calls == 0, "late class hook admitted invalid probe evidence"


@pytest.mark.parametrize(
    "record", ["path", "tool", "rooted", "command", "program", "context", "transcript"]
)
def test_probe_record_constructor_preserves_valid_after_validator_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Late class post-init hooks cannot reject valid portable probe metadata."""
    tool = ToolExecutable(_PYTHON_TOOL)
    command = ProbeCommand(executable=tool)
    base = {
        "path": PathArgument(ProbeRoot.SOURCE, "source.bin"),
        "tool": tool,
        "rooted": RootedExecutable(ProbeRoot.SCRATCH, "tool.exe"),
        "command": command,
        "program": ProbeProgram("probe", (command,)),
        "context": _context(tmp_path / "source", tmp_path),
        "transcript": ProbeTranscript("probe", bytes(32), 1),
    }[record]
    calls = 0

    def reject_valid(_value: object) -> None:
        nonlocal calls
        calls += 1
        raise ProbeProgramError("forged rejection")

    with monkeypatch.context() as patch:
        patch.setattr(type(base), "__post_init__", reject_valid)
        clone = replace(base)
    assert clone == base
    assert calls == 0, "late class hook rejected valid probe evidence"


@pytest.mark.parametrize(
    ("record", "field", "invalid", "repaired"),
    [
        ("path", "relative_path", "../unsafe", "safe"),
        ("tool", "tool_id", "", "python"),
        ("rooted", "root", object(), ProbeRoot.SCRATCH),
        ("command", "timeout_ms", 0, 1000),
        ("program", "commands", (), "default"),
        ("context", "enforce_source_immutable", 1, True),
        ("transcript", "digest", b"short", bytes(32)),
    ],
)
def test_probe_constructor_rejects_forged_property_setter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
    invalid: object,
    repaired: object,
) -> None:
    """A post-import property setter cannot launder invalid probe metadata."""
    tool = ToolExecutable(_PYTHON_TOOL)
    command = ProbeCommand(tool)
    baseline = {
        "path": PathArgument(ProbeRoot.SOURCE, "safe"),
        "tool": tool,
        "rooted": RootedExecutable(ProbeRoot.SCRATCH, "tool.exe"),
        "command": command,
        "program": ProbeProgram("probe", (command,)),
        "context": ProbeRunContext(tmp_path, tmp_path, ()),
        "transcript": ProbeTranscript("probe", bytes(32), 1),
    }[record]
    owner = type(baseline)
    slot = owner.__dict__[field]
    valid_value = (command,) if repaired == "default" else repaired
    calls = 0

    def original_getter(value: object) -> object:
        return slot.__get__(value, owner)

    def repairing_setter(value: object, _ignored: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(value, valid_value)

    with monkeypatch.context() as patch:
        patch.setattr(owner, field, property(original_getter, repairing_setter))
        with pytest.raises(ProbeProgramError):
            _ = replace(baseline, **{field: invalid})
    assert calls == 0, f"forged {record}.{field} setter executed"


@pytest.mark.parametrize(
    ("record", "field"),
    [
        ("path", "root"),
        ("path", "relative_path"),
        ("tool", "tool_id"),
        ("rooted", "root"),
        ("rooted", "relative_path"),
        ("command", "executable"),
        ("command", "arguments"),
        ("command", "stdin"),
        ("command", "expected_exit_code"),
        ("command", "timeout_ms"),
        ("command", "max_stdout_bytes"),
        ("command", "max_stderr_bytes"),
        ("command", "digest_stdout"),
        ("command", "digest_exit_code"),
        ("program", "probe_id"),
        ("program", "commands"),
        ("context", "source_root"),
        ("context", "repository_root"),
        ("context", "tools"),
        ("context", "enforce_source_immutable"),
        ("transcript", "probe_id"),
        ("transcript", "digest"),
        ("transcript", "digested_commands"),
    ],
)
def test_probe_valid_constructor_uses_original_field_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
) -> None:
    """Every admitted field bypasses a substituted class property setter."""
    tool = ToolExecutable(_PYTHON_TOOL)
    command = ProbeCommand(tool)
    baseline = {
        "path": PathArgument(ProbeRoot.SOURCE, "safe"),
        "tool": tool,
        "rooted": RootedExecutable(ProbeRoot.SCRATCH, "tool.exe"),
        "command": command,
        "program": ProbeProgram("probe", (command,)),
        "context": ProbeRunContext(tmp_path, tmp_path, ()),
        "transcript": ProbeTranscript("probe", bytes(32), 1),
    }[record]
    owner = type(baseline)
    slot = owner.__dict__[field]
    calls = 0

    def original_getter(value: object) -> object:
        return slot.__get__(value, owner)

    def forbidden_setter(_value: object, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("forged probe field setter reached construction")

    with monkeypatch.context() as patch:
        patch.setattr(owner, field, property(original_getter, forbidden_setter))
        clone = replace(baseline)
    assert clone == baseline
    assert calls == 0, f"valid {record}.{field} invoked forged setter"


@pytest.mark.parametrize(
    ("record", "field", "invalid"),
    [
        ("path", "root", object()),
        ("path", "relative_path", "../unsafe"),
        ("tool", "tool_id", ""),
        ("rooted", "root", object()),
        ("rooted", "relative_path", "../unsafe"),
        ("command", "executable", object()),
        ("command", "arguments", ["-c"]),
        ("command", "stdin", "invalid"),
        ("command", "expected_exit_code", -1),
        ("command", "timeout_ms", 0),
        ("command", "max_stdout_bytes", -1),
        ("command", "max_stderr_bytes", -1),
        ("command", "digest_stdout", 1),
        ("command", "digest_exit_code", 1),
        ("program", "probe_id", ""),
        ("program", "commands", ()),
        ("context", "source_root", "invalid"),
        ("context", "repository_root", "invalid"),
        ("context", "tools", []),
        ("context", "enforce_source_immutable", 1),
        ("transcript", "probe_id", ""),
        ("transcript", "digest", b"short"),
        ("transcript", "digested_commands", -1),
    ],
)
def test_probe_record_validation_uses_original_fields_not_late_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
    invalid: object,
) -> None:
    """A forged class getter must not sanitize malformed stored probe evidence."""
    tool = ToolExecutable(_PYTHON_TOOL)
    command = ProbeCommand(tool)
    baseline = {
        "path": PathArgument(ProbeRoot.SOURCE, "safe"),
        "tool": tool,
        "rooted": RootedExecutable(ProbeRoot.SCRATCH, "tool.exe"),
        "command": command,
        "program": ProbeProgram("probe", (command,)),
        "context": ProbeRunContext(tmp_path, tmp_path, ()),
        "transcript": ProbeTranscript("probe", bytes(32), 1),
    }[record]
    owner = type(baseline)
    slot = owner.__dict__[field]
    valid = slot.__get__(baseline, owner)
    calls = 0

    def forged_getter(_record: object) -> object:
        nonlocal calls
        calls += 1
        return valid

    with monkeypatch.context() as patch:
        patch.setattr(owner, field, property(forged_getter))
        with pytest.raises(ProbeProgramError):
            _ = replace(baseline, **{field: invalid})
    assert calls == 0, f"late {record}.{field} getter affected record admission"


@pytest.mark.parametrize(
    ("record", "field", "forged"),
    [
        ("command", "digest_stdout", False),
        ("command", "digest_exit_code", True),
        ("program", "commands", ()),
        ("program", "probe_id", "redirected"),
        ("context", "enforce_source_immutable", False),
    ],
)
def test_probe_execution_ignores_late_metadata_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
    forged: object,
) -> None:
    """Admitted probe commands and source checks must use stored metadata."""
    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('trusted')"),
        digest_stdout=True,
    )
    program = ProbeProgram("identity", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    target = {"command": command, "program": program, "context": context}[record]
    calls = 0

    def spoof(_record: object) -> object:
        nonlocal calls
        calls += 1
        return forged

    owner = type(target)
    with monkeypatch.context() as patched:
        patched.setattr(owner, field, property(spoof))
        observed = run_probe_program(program, context)
    assert observed == baseline
    assert calls == 0, f"late {record}.{field} getter controlled probe runtime"


@pytest.mark.parametrize(
    ("record", "field"),
    [
        ("command", "executable"),
        ("command", "arguments"),
        ("command", "stdin"),
        ("command", "expected_exit_code"),
        ("command", "timeout_ms"),
        ("command", "max_stdout_bytes"),
        ("command", "max_stderr_bytes"),
        ("tool", "tool_id"),
        ("path", "root"),
        ("path", "relative_path"),
        ("context", "source_root"),
        ("context", "repository_root"),
        ("context", "tools"),
    ],
)
def test_probe_runtime_ignores_late_executable_and_path_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
) -> None:
    """Runtime preflight, spawning, and source resolution use native storage."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "trusted.txt").write_bytes(b"trusted bytes")
    tool = ToolExecutable(_PYTHON_TOOL)
    path = PathArgument(ProbeRoot.SOURCE, "trusted.txt")
    command = ProbeCommand(
        executable=tool,
        arguments=("-c", _READ_BYTES_CODE, path),
        digest_stdout=True,
    )
    program = ProbeProgram("identity", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    target = {"command": command, "tool": tool, "path": path, "context": context}[
        record
    ]
    calls = 0

    def forbidden_getter(_record: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("late probe getter changed admitted runtime evidence")

    with monkeypatch.context() as patched:
        patched.setattr(type(target), field, property(forbidden_getter))
        observed = run_probe_program(program, context)
    assert observed == baseline
    assert calls == 0, f"probe runtime consulted late {record}.{field} getter"


@pytest.mark.parametrize("field", ("stdout", "returncode"))
@pytest.mark.parametrize("hook", ("setter", "getter"))
def test_probe_command_result_ignores_late_class_field_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    hook: str,
) -> None:
    """An internal result cannot change authenticated process observations."""
    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('trusted')"),
        digest_stdout=True,
        digest_exit_code=True,
    )
    program = ProbeProgram("identity", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    owner = cast("type[object]", vars(probe_exec_module)["_CommandResult"])
    slot = owner.__dict__[field]
    forged = b"forged bytes" if field == "stdout" else 99
    calls = 0

    def forged_getter(record: object) -> object:
        nonlocal calls
        if hook == "getter":
            calls += 1
            return forged
        return slot.__get__(record, owner)

    def forged_setter(record: object, supplied: object) -> None:
        nonlocal calls
        if hook == "setter":
            calls += 1
            slot.__set__(record, forged)
        else:
            slot.__set__(record, supplied)

    with monkeypatch.context() as patched:
        patched.setattr(owner, field, property(forged_getter, forged_setter))
        observed = run_probe_program(program, context)
    assert observed == baseline
    assert calls == 0, f"late _CommandResult.{field} {hook} changed transcript"


@pytest.mark.parametrize("hook", ("getter", "setter"))
@pytest.mark.parametrize(
    ("record", "field"),
    [
        *(
            ("capture", name)
            for name in ("limit", "fragments", "size", "exceeded", "error", "finished")
        ),
        *(
            ("running", name)
            for name in (
                "process",
                "stdout",
                "stderr",
                "readers",
                "writer",
                "stdin_errors",
                "stdin_complete",
            )
        ),
    ],
)
def test_probe_transient_runtime_ignores_late_class_field_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record: str,
    field: str,
    hook: str,
) -> None:
    """Capture quotas and worker observations must use original state slots."""
    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=(
            "-c",
            "import sys; data=sys.stdin.buffer.read(); "
            + "sys.stdout.buffer.write(data); sys.stderr.buffer.write(b'err')",
        ),
        stdin=b"trusted",
        max_stdout_bytes=7,
        max_stderr_bytes=3,
        digest_stdout=True,
        digest_exit_code=True,
    )
    program = ProbeProgram("transient-slots", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    owner = cast(
        "type[object]",
        vars(probe_exec_module)[
            "_PipeCapture" if record == "capture" else "_RunningProbe"
        ],
    )
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    calls = 0

    def forged_getter(obj: object) -> object:
        nonlocal calls
        if hook == "getter":
            calls += 1
            raise AssertionError("late transient getter controlled probe runtime")
        return cast("object", slot.__get__(obj, owner))

    def forged_setter(obj: object, value: object) -> None:
        nonlocal calls
        if hook == "setter":
            calls += 1
            raise AssertionError("late transient setter controlled probe runtime")
        slot.__set__(obj, value)

    with monkeypatch.context() as patched:
        patched.setattr(owner, field, property(forged_getter, forged_setter))
        observed = run_probe_program(program, context)
    assert observed == baseline
    assert calls == 0, f"late {record}.{field} {hook} changed probe runtime"


def test_probe_capture_quota_ignores_late_limit_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged quota getter must not retain bytes above the original limit."""
    capture_type = cast("Callable[[int], object]", vars(probe_exec_module)["_PipeCapture"])
    capture = capture_type(2)
    original_limit = cast("MemberDescriptorType", type(capture).__dict__["limit"])
    fragment = cast(
        "Callable[[IO[bytes], object], bool]",
        vars(probe_exec_module)["_capture_fragment"],
    )

    def forged_limit(_record: object) -> int:
        return 100

    with tempfile.TemporaryFile() as stream:
        _ = stream.write(b"12345")
        _ = stream.seek(0)
        with monkeypatch.context() as patched:
            patched.setattr(type(capture), "limit", property(forged_limit))
            assert not fragment(stream, capture)
    assert original_limit.__get__(capture, type(capture)) == 2

    def original_value(name: str) -> object:
        slot = cast("MemberDescriptorType", type(capture).__dict__[name])
        return cast("object", slot.__get__(capture, type(capture)))

    assert original_value("exceeded") is True
    assert original_value("size") == 0
    assert original_value("fragments") == []


@pytest.mark.parametrize("hook", ("__init__", "__new__"))
@pytest.mark.parametrize(
    ("record", "callback"),
    (
        ("_CommandResult", "_launch_command"),
        ("_CapturedProcess", "_wait_for_bounded_pipes"),
        ("_PipeCapture", "_capture_pipes"),
        ("_RunningProbe", "_start_writer"),
        ("ProbeTranscript", "_run_command"),
    ),
)
def test_probe_execution_ignores_late_receipt_constructors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    record: str,
    callback: str,
    hook: str,
) -> None:
    """Completed process callbacks cannot replace authenticated receipts."""
    child_marker = "MALBOLGE_PROBE_CONSTRUCTOR_CHILD"
    if hook == "__new__" and os.environ.get(child_marker) != "1":
        # Rebinding a dataclass's native tp_new can outlive Python restoration.
        environment = os.environ.copy()
        environment[child_marker] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", request.node.nodeid],
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
            env=environment,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return

    source = tmp_path / "source"
    source.mkdir()
    program = _program("constructor", "print('real observation')")
    context = _context(source, tmp_path)
    expected = run_probe_program(program, context)
    owner = cast("type[object]", vars(probe_exec_module)[record])
    original = cast("Callable[..., object]", getattr(probe_exec_module, callback))
    calls = 0
    installed = False

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late probe receipt constructor executed")

    with monkeypatch.context() as patched:

        def install_after_callback(*args: object, **kwargs: object) -> object:
            nonlocal installed
            result = original(*args, **kwargs)
            if not installed:
                patched.setattr(owner, hook, forbidden)
                installed = True
            return result

        patched.setattr(probe_exec_module, callback, install_after_callback)
        observed = run_probe_program(program, context)
        assert observed == expected
    assert installed and calls == 0


@pytest.mark.parametrize(
    "attack",
    (
        "replace_class",
        "replace_init",
        "replace_new",
        "forge_stdout",
        "forge_stderr",
        "forge_returncode",
    ),
)
def test_probe_completed_process_cannot_rewrite_captured_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    attack: str,
) -> None:
    """An executed child must not trust mutable subprocess result hooks."""
    child_marker = "MALBOLGE_PROBE_COMPLETED_CHILD"
    if attack == "replace_new" and os.environ.get(child_marker) != "1":
        environment = os.environ.copy()
        environment[child_marker] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", request.node.nodeid],
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
            env=environment,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return

    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "import sys; print('trusted'); sys.stderr.write('stderr')"),
        digest_stdout=True,
        digest_exit_code=True,
    )
    program = ProbeProgram("completed-receipt", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    original_wait = cast(
        "Callable[..., None]", vars(probe_exec_module)["_wait_for_bounded_pipes"]
    )
    owner = subprocess.CompletedProcess
    installed = False
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late subprocess result constructor executed")

    def forged_getter(_record: object) -> object:
        nonlocal calls
        calls += 1
        return {"stdout": b"forged", "stderr": b"unexpected"}.get(
            attack.removeprefix("forge_"), 99
        )

    def stored_setter(record: object, value: object) -> None:
        vars(record)[attack.removeprefix("forge_")] = value

    with monkeypatch.context() as patched:

        def after_capture(*args: object, **kwargs: object) -> None:
            nonlocal installed
            original_wait(*args, **kwargs)
            if not installed:
                if attack == "replace_class":
                    patched.setattr(subprocess, "CompletedProcess", forbidden)
                elif attack == "replace_init":
                    patched.setattr(owner, "__init__", forbidden)
                elif attack == "replace_new":
                    patched.setattr(owner, "__new__", forbidden)
                else:
                    patched.setattr(
                        owner,
                        attack.removeprefix("forge_"),
                        property(forged_getter, stored_setter),
                        raising=False,
                    )
                installed = True

        patched.setattr(probe_exec_module, "_wait_for_bounded_pipes", after_capture)
        observed = run_probe_program(program, context)
        assert observed == baseline
    assert installed and calls == 0


@pytest.mark.parametrize("field", ("stdout", "stderr", "returncode"))
def test_probe_captured_process_ignores_late_field_getters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Digest and bounds checks read the pinned process receipt storage."""
    source = tmp_path / "source"
    source.mkdir()
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "import sys; print('trusted'); sys.stderr.write('error')"),
        digest_stdout=True,
        digest_exit_code=True,
    )
    program = ProbeProgram("captured-fields", (command,))
    context = _context(source, tmp_path)
    baseline = run_probe_program(program, context)
    owner = cast("type[object]", vars(probe_exec_module)["_CapturedProcess"])
    original = cast("Callable[..., object]", vars(probe_exec_module)["_launch_command"])
    calls = 0

    def forbidden_getter(_receipt: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("late captured process getter executed")

    with monkeypatch.context() as patched:

        def install_after_launch(*args: object, **kwargs: object) -> object:
            result = original(*args, **kwargs)
            patched.setattr(owner, field, property(forbidden_getter))
            return result

        patched.setattr(probe_exec_module, "_launch_command", install_after_launch)
        observed = run_probe_program(program, context)
        assert observed == baseline
    assert calls == 0


def _forged_native_probe_record(
    record: object,
    overrides: dict[str, object] | None = None,
    *,
    missing: tuple[str, ...] = (),
) -> object:
    """Bypass constructor admission but preserve native record identity."""
    owner = type(record)
    forged = object.__new__(owner)
    for field in dataclass_fields(cast("ProbeProgram", record)):
        name = field.name
        if name in missing:
            continue
        slot = cast("MemberDescriptorType", owner.__dict__[name])
        value = (overrides or {}).get(name, slot.__get__(record, owner))
        slot.__set__(forged, value)
    return forged


@pytest.mark.parametrize(
    ("forgery", "field", "invalid"),
    [
        ("program", "commands", ()),
        ("command", "timeout_ms", 0),
        ("command", "digest_stdout", 1),
        ("tool", "tool_id", ""),
        ("argument", "relative_path", "../escape"),
        ("context", "enforce_source_immutable", 1),
        ("rooted", "root", "foreign"),
    ],
)
def test_probe_batch_revalidates_native_nested_metadata_before_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
    field: str,
    invalid: object,
) -> None:
    """Constructor-bypassed probe metadata cannot reach file or process work."""
    source = tmp_path / "source"
    source.mkdir()
    context = _context(source, tmp_path)
    command = ProbeCommand(
        ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('trusted')", PathArgument(ProbeRoot.SOURCE, "input")),
        digest_stdout=True,
    )
    program = ProbeProgram("native-identity", (command,))
    if forgery == "context":
        context = cast(
            "ProbeRunContext",
            _forged_native_probe_record(context, {field: invalid}),
        )
    elif forgery == "program":
        program = cast(
            "ProbeProgram",
            _forged_native_probe_record(program, {field: invalid}),
        )
    else:
        if forgery == "command":
            command = cast(
                "ProbeCommand",
                _forged_native_probe_record(command, {field: invalid}),
            )
        elif forgery == "tool":
            tool = cast(
                "ToolExecutable",
                _forged_native_probe_record(command.executable, {field: invalid}),
            )
            command = replace(command, executable=tool)
        elif forgery == "rooted":
            rooted = RootedExecutable(ProbeRoot.SCRATCH, "run")
            forged = _forged_native_probe_record(rooted, {field: invalid})
            command = replace(command, executable=cast("RootedExecutable", forged))
        else:
            path = cast("PathArgument", command.arguments[-1])
            forged = _forged_native_probe_record(path, {field: invalid})
            command = replace(
                command,
                arguments=(*command.arguments[:-1], cast("PathArgument", forged)),
            )
        program = cast(
            "ProbeProgram",
            _forged_native_probe_record(program, {"commands": (command,)}),
        )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("invalid probe metadata entered host preflight")

    monkeypatch.setattr(probe_exec_module, "_require_repository_paths_disjoint", forbidden)
    with pytest.raises(ProbeProgramError):
        _ = run_probe_program(program, context)


@pytest.mark.parametrize("missing", ["commands", "probe_id"])
def test_probe_batch_rejects_missing_native_program_slots(
    tmp_path: Path, missing: str,
) -> None:
    """Absent native program storage produces a typed error before execution."""
    original = _program("identity", "print('ok')")
    forged = _forged_native_probe_record(original, missing=(missing,))
    with pytest.raises(ProbeProgramError):
        _ = run_probe_program(
            cast("ProbeProgram", forged), _context(tmp_path / "source", tmp_path)
        )
