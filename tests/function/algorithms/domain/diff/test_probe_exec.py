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

from contextlib import suppress
from dataclasses import replace
import gc
import hashlib
import io
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import threading
import time
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import probe_exec as probe_exec_module
from algorithms.diff.probe_exec import PathArgument
from algorithms.diff.probe_exec import ProbeCommand
from algorithms.diff.probe_exec import ProbeExecutionError
from algorithms.diff.probe_exec import ProbeProgram
from algorithms.diff.probe_exec import ProbeProgramError
from algorithms.diff.probe_exec import ProbeRoot
from algorithms.diff.probe_exec import ProbeRunContext
from algorithms.diff.probe_exec import ProbeTranscript
from algorithms.diff.probe_exec import RootedExecutable
from algorithms.diff.probe_exec import ToolExecutable
from algorithms.diff.probe_exec import run_probe_program
from algorithms.diff.probe_exec import run_probe_programs
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
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
    "import pathlib,sys;"
    "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
)
_MUTATE_CODE = (
    "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('after')"
)


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


def _context(source_root: Path, repository_root: Path) -> ProbeRunContext:
    return ProbeRunContext(
        source_root=source_root,
        repository_root=repository_root,
        tools=((_PYTHON_TOOL, Path(sys.executable)),),
    )


def _program(
    probe_id: str, code: str, *, digest_stdout: bool = True
) -> ProbeProgram:
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
    _expect(
        transcript.digest == expected.digest(), "structured argv changed bytes"
    )


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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
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

    monkeypatch.setattr(Path, "resolve", fail_resolve)
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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
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

    monkeypatch.setattr(Path, "resolve", fail_resolve)
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
    with pytest.raises(
        ProbeExecutionError, match="probe path resolution failed"
    ):
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

    monkeypatch.setattr(Path, "resolve", fail_second_resolve)
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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
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

    monkeypatch.setattr(Path, "stat", fail_stat)
    with pytest.raises(ProbeExecutionError, match="status failed"):
        _ = run_probe_program(_program("blocked-tool", "pass"), context)


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
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

    monkeypatch.setattr(Path, "resolve", fail_resolve)
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
    _expect(
        transcript.digest == expected.digest(), "exit-code transcript changed"
    )
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
            message = "unanticipated capture failure"
            raise TypeError(message)
        return read(fd, count)

    monkeypatch.setattr(threading, "excepthook", record_uncaught)
    monkeypatch.setattr(os, "read", crashing_read)
    program = _program("uncaught-output-reader", "pass")
    with pytest.raises(ProbeExecutionError, match="pipe communication failed"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(bool(uncaught), "worker exception fixture was not exercised")


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
    _expect(
        transcript.digest == expected.digest(), "stdin/stdout transcript drift"
    )


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
    mutation = (
        "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('during');"
    )
    if mutator_fails:
        mutation += "raise SystemExit(7)"
    restore = (
        "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
    )
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
    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
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
    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
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

    monkeypatch.setattr(Path, "stat", fail_stat)
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
    with pytest.raises(
        ProbeExecutionError, match="repository path status failed"
    ):
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

    monkeypatch.setattr(Path, "stat", fail_stat)
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
                executable=RootedExecutable(
                    ProbeRoot.REPOSITORY, "source/tool.bin"
                ),
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

    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
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
        copied = actual_copytree(
            source_root, destination_root, symlinks=symlinks
        )
        _ = (copied / "input.txt").write_bytes(b"injected")
        return copied

    monkeypatch.setattr(shutil, "copytree", mutate_mirror_after_copy)
    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
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


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
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

    monkeypatch.setattr(shutil, "copytree", denied_copy)
    with pytest.raises(
        ProbeExecutionError, match="source mirror creation failed"
    ):
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
        *, prefix: str
    ) -> tempfile.TemporaryDirectory[str]:
        if prefix == failed_prefix:
            message = "temporary root host failure"
            raise failure_type(message)
        return original_temporary_root(prefix=prefix)

    monkeypatch.setattr(tempfile, "TemporaryDirectory", denied_temporary_root)
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
    context = replace(
        _context(missing, tmp_path), enforce_source_immutable=False
    )
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
