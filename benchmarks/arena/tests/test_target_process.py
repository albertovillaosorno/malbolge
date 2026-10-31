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
#   - Bounded external emitter/VM subprocess behavior for real-target studies.
# - Must-Not:
#   - Claim that process containment proves full study resource budgets.
# - Allows:
#   - Inputs: controlled children and ordinary descendants.
#   - Outputs: bounded exact streams or failure without partial success.
#   - Side effects: spawned and reaped disposable child process groups.
# - Split-When:
#   - A general research process supervisor subsumes this narrow boundary.
# - Merge-When:
#   - The arena uses a shared verified subprocess lifecycle.
# - Summary:
#   - Fail closed on output floods, deadlines, and inherited-pipe descendants.
# - Description:
#   - Exercises complete captured stdout/stderr without unbounded communicate.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_process.py.
# - Defaults:
#   - All child transport tests require the supported POSIX platform.
#

"""Bounded process transport tests for the real Malbolge target pilot."""

# ruff: file-ignore[assert]

from __future__ import annotations

import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from contextlib import contextmanager
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import evidence, target_process

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from typing import IO

POSIX_PLATFORM = "posix"
LINUX_PLATFORM = "linux"
PRLIMIT_AVAILABLE = shutil.which("prlimit") is not None
ADDRESS_LIMIT_OUTPUT = b"blocked"
pytestmark = pytest.mark.skipif(
    os.name != POSIX_PLATFORM, reason="bounded target subprocess requires POSIX"
)
STDOUT_NAME = "stdout"
EXPECTED_EXIT_CODE = 7
EXPECTED_DIAGNOSTIC = b"problem"
NO_STDOUT = b""
EMPTY_INPUT_LENGTH = b"0\n"
STDOUT_LIMIT = 256
STDERR_LIMIT = 512
SMALL_TIMEOUT_SECONDS = 0.2
LARGE_TIMEOUT_SECONDS = 3
REPEAT_COUNT = 99
MEASURED_BINARY_INPUT_MODE = "bytes"


def _child(source: str) -> list[str]:
    return [sys.executable, "-c", source]


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_measured_rss_reader_close_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Unexpected evidence cleanup faults must not bypass typed tool failure."""
    report = tmp_path / "rss.txt"
    _ = report.write_bytes(b"10\n")
    original_open = evidence._open_evidence

    @contextmanager
    def fail_after_close(path: Path) -> Iterator[IO[bytes]]:
        with original_open(path) as stream:
            yield stream
        raise fault("injected RSS receipt close failure")

    monkeypatch.setattr(evidence, "_open_evidence", fail_after_close)
    with pytest.raises(target_process.TargetProcessError, match="RSS report") as error:
        target_process._rss_report_bytes(report)
    evidence_failure = error.value.__cause__
    assert isinstance(evidence_failure, evidence.EvidenceError)
    assert type(evidence_failure.__cause__) is fault


def test_group_cleanup_signal_error_is_typed_after_child_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure to signal descendants cannot be misreported as success."""

    original_kill = os.kill

    def refuse_group_signal(group: int, signal: int) -> None:
        if group < 0:
            raise PermissionError("injected group signal refusal")
        original_kill(group, signal)

    monkeypatch.setattr(target_process.os, "kill", refuse_group_signal)
    with pytest.raises(target_process.TargetProcessError, match="cleanup") as error:
        target_process.invoke(
            _child("print('produced')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert isinstance(error.value.__cause__, PermissionError)


def test_group_cleanup_failure_preserves_primary_output_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup exceptions must not erase the observed output-budget breach."""

    original_kill = os.kill

    def refuse_group_signal(group: int, signal: int) -> None:
        if group < 0:
            raise PermissionError("injected group signal refusal")
        original_kill(group, signal)

    monkeypatch.setattr(target_process.os, "kill", refuse_group_signal)
    with pytest.raises(target_process.TargetProcessError, match="stdout") as error:
        target_process.invoke(
            _child("import os;os.write(1,b'x'*4096)"),
            stdout_limit=STDOUT_LIMIT,
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert any("cleanup also failed" in note for note in error.value.__notes__)


def test_refused_group_signal_still_reaps_direct_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A denied group signal must not bypass the direct-child fallback."""

    class ChildProbe:
        pid = 123456

        def __init__(self) -> None:
            self.events: list[str] = []

        def poll(self) -> None:
            self.events.append("poll")

        def kill(self) -> None:
            self.events.append("kill")

        def wait(self) -> int:
            self.events.append("wait")
            return 0

    def refuse_group_signal(group: int, signal: int) -> None:
        del group, signal
        raise PermissionError("injected group signal refusal")

    monkeypatch.setattr(target_process.os, "kill", refuse_group_signal)
    probe = ChildProbe()
    with pytest.raises(PermissionError, match="group signal refusal"):
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", probe)
        )
    assert probe.events == ["poll", "kill", "wait"]


def test_stream_close_faults_preserve_primary_failure_and_attempt_all_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected cleanup errors cannot mask an output-budget failure."""
    closed: list[str] = []

    class RejectingStream:
        closed = False

        def __init__(self, label: str) -> None:
            self.label = label

        def close(self) -> None:
            closed.append(self.label)
            raise OSError(f"injected {self.label} close failure")

    class ChildProbe:
        stdin = RejectingStream("stdin")
        stdout = RejectingStream("stdout")
        stderr = RejectingStream("stderr")

    monkeypatch.setattr(target_process, "_terminate_group", lambda _child: None)
    with pytest.raises(target_process.TargetProcessError, match="primary") as error:
        try:
            raise target_process.TargetProcessError("primary output rejection")
        finally:
            target_process._finish_child(  # ruff: ignore[private-member-access]
                cast("sp.Popen[bytes]", ChildProbe())
            )
    assert closed == ["stdin", "stdout", "stderr"]
    assert sum(
        "cleanup also failed" in note for note in error.value.__notes__
    ) == 3


def test_secondary_direct_reap_failure_remains_in_primary_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both a refused group signal and direct kill refusal remain observable."""

    class ChildProbe:
        pid = 123456
        stdin = None
        stdout = None
        stderr = None

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            raise PermissionError("direct kill denied")

    def refuse_group_signal(group: int, signal: int) -> None:
        del group, signal
        raise PermissionError("group signal denied")

    monkeypatch.setattr(target_process.os, "kill", refuse_group_signal)
    with pytest.raises(target_process.TargetProcessError, match="primary") as error:
        try:
            raise target_process.TargetProcessError("primary output rejection")
        finally:
            target_process._finish_child(  # ruff: ignore[private-member-access]
                cast("sp.Popen[bytes]", ChildProbe())
            )
    assert any("group signal denied" in note for note in error.value.__notes__)
    assert any("direct kill denied" in note for note in error.value.__notes__)


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_output_pipe_read_fault_is_typed_and_retains_cause(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """An unreadable pipe never escapes as an untyped partial capture."""

    def fail_read(descriptor: int, count: int) -> bytes:
        del descriptor, count
        raise fault("injected output pipe read failure")

    # subprocess.Popen reads its own exec-status pipe before returning.
    # Inject only after launch to exercise our capture boundary instead.
    original_popen = target_process.sp.Popen

    def launch(*args: Any, **kwargs: Any) -> sp.Popen[bytes]:
        child = cast("sp.Popen[bytes]", original_popen(*args, **kwargs))
        monkeypatch.setattr(target_process.os, "read", fail_read)
        return child

    monkeypatch.setattr(target_process.sp, "Popen", launch)
    with pytest.raises(target_process.TargetProcessError, match="capture") as error:
        target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_output_selector_failure_is_typed_and_retains_cause(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """A broken selector cannot turn incomplete capture into success."""
    original_selector = target_process.selectors.DefaultSelector

    def fail_select() -> target_process.selectors.BaseSelector:
        selector = original_selector()

        def broken_select(timeout: float | None = None) -> None:
            del timeout
            raise fault("injected output selector failure")

        monkeypatch.setattr(selector, "select", broken_select)
        return selector

    monkeypatch.setattr(target_process.selectors, "DefaultSelector", fail_select)
    with pytest.raises(target_process.TargetProcessError, match="capture") as error:
        target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_binary_input_delivery_fault_is_typed_and_retains_cause(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Input pipe write errors cannot surface as untyped transport faults."""

    def fail_write(descriptor: int, data: bytes) -> int:
        del descriptor, data
        raise fault("injected input pipe write failure")

    monkeypatch.setattr(target_process.os, "write", fail_write)
    with pytest.raises(target_process.TargetProcessError, match="input") as error:
        target_process.invoke_with_input(
            _child("import sys; sys.stdin.buffer.read()"),
            b"x",
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize("written", [None, True, False, 0, 2])
def test_binary_input_rejects_nonexact_write_counts(
    monkeypatch: pytest.MonkeyPatch,
    written: int | bool | None,
) -> None:
    """A synthetic write return never proves an exact byte delivery."""

    def report_write(descriptor: int, data: bytes) -> int | bool | None:
        del descriptor, data
        return written

    monkeypatch.setattr(target_process.os, "write", report_write)
    with pytest.raises(target_process.TargetProcessError, match="completely"):
        target_process.invoke_with_input(
            _child("import sys; sys.stdin.buffer.read()"),
            b"x",
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


@pytest.mark.parametrize("delivery_fails", [False, True])
def test_binary_input_close_fault_preserves_delivery_evidence(
    monkeypatch: pytest.MonkeyPatch,
    *,
    delivery_fails: bool,
) -> None:
    """An input pipe close failure is typed and never masks a prior write."""

    class FaultyStream:
        def fileno(self) -> int:
            return 1

        def close(self) -> None:
            raise RuntimeError("injected input stream close fault")

    class ChildProbe:
        stdin = FaultyStream()

    def no_op_set_blocking(descriptor: int, blocking: bool) -> None:
        del descriptor, blocking

    def deliver(descriptor: int, data: bytes) -> int:
        del descriptor
        if delivery_fails:
            raise OSError("injected input delivery failure")
        return len(data)

    monkeypatch.setattr(target_process.os, "set_blocking", no_op_set_blocking)
    monkeypatch.setattr(target_process.os, "write", deliver)
    with pytest.raises(target_process.TargetProcessError, match="input") as error:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b"x"
        )
    if delivery_fails:
        assert type(error.value.__cause__) is OSError
        assert any("input close also failed" in note for note in error.value.__notes__)
    else:
        assert type(error.value.__cause__) is RuntimeError


@pytest.mark.parametrize(
    "invalid",
    [None, False, 0, b"bad".decode(), bytearray(b"bad"), memoryview(b"bad"), [98, 97, 100]],
    ids=["none", "false", "zero", "text", "bytearray", "memoryview", "list"],
)
def test_invalid_output_read_value_cannot_fake_eof_or_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """A malformed read return cannot become EOF or fabricated host bytes."""
    unregistered: list[object] = []

    class SelectorProbe:
        def unregister(self, fileobj: object) -> None:
            unregistered.append(fileobj)

    key = target_process.selectors.SelectorKey(
        fileobj=12345,
        fd=12345,
        events=target_process.selectors.EVENT_READ,
        data=0,
    )
    buffers = [bytearray(), bytearray()]

    def read_invalid(descriptor: int, requested: int) -> object:
        assert descriptor == key.fd
        assert 0 < requested <= target_process.READ_CHUNK_BYTES
        return invalid

    monkeypatch.setattr(target_process.os, "read", read_invalid)
    with pytest.raises(target_process.TargetProcessError, match="output read"):
        target_process._read_ready(  # ruff: ignore[private-member-access]
            key,
            cast("target_process.selectors.BaseSelector", SelectorProbe()),
            buffers=buffers,
            limits=target_process._ProcessLimits(  # ruff: ignore[private-member-access]
                timeout_seconds=LARGE_TIMEOUT_SECONDS,
                stdout_limit=STDOUT_LIMIT,
                stderr_limit=STDERR_LIMIT,
            ),
        )
    assert buffers == [bytearray(), bytearray()]
    assert unregistered == []


@pytest.mark.parametrize("invalid", [None, memoryview(b"fabricated")])
def test_bounded_target_never_reports_success_from_invalid_output_reader(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """A broken stream cannot be recorded as a valid child observation."""
    original_popen = target_process.sp.Popen

    def launch(*args: Any, **kwargs: Any) -> sp.Popen[bytes]:
        child = cast("sp.Popen[bytes]", original_popen(*args, **kwargs))
        monkeypatch.setattr(target_process.os, "read", lambda _fd, _count: invalid)
        return child

    monkeypatch.setattr(target_process.sp, "Popen", launch)
    with pytest.raises(target_process.TargetProcessError, match="output read"):
        _ = target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


@pytest.mark.parametrize(
    "launcher", [target_process.invoke, target_process.invoke_limited]
)
@pytest.mark.parametrize(
    "command",
    [
        [],
        None,
        "echo",
        [""],
        [sys.executable, None],
        [sys.executable, b"bytes"],
        [sys.executable, "NUL\x00arg"],
    ],
)
def test_invalid_child_command_rejects_before_launch(
    monkeypatch: pytest.MonkeyPatch,
    launcher: Callable[..., sp.CompletedProcess[bytes]],
    command: object,
) -> None:
    """Malformed executable/argument vectors do not reach host process APIs."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        _ = (args, kwargs)
        launched = True
        message = "malformed child command launched"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="command"):
        launcher(
            cast("list[str]", command), timeout_seconds=LARGE_TIMEOUT_SECONDS
        )
    assert not launched


@pytest.mark.parametrize(
    ("command", "reason"),
    [
        ([sys.executable, *(["x"] * 513)], "argument count"),
        ([sys.executable, "x" * 32768], "argument bytes"),
        ([sys.executable, *(["x" * 512] * 32)], "argument bytes"),
        ([sys.executable, "☃" * 6000], "argument bytes"),
        ([sys.executable, "\ud800"], "filesystem text"),
    ],
)
@pytest.mark.parametrize(
    ("launcher", "input_mode"),
    [
        (target_process.invoke, "null"),
        (target_process.invoke_limited, "null"),
        (target_process.invoke_with_input, MEASURED_BINARY_INPUT_MODE),
        (target_process.invoke_limited_measured, "null"),
        (
            target_process.invoke_with_input_limited_measured_raw,
            MEASURED_BINARY_INPUT_MODE,
        ),
    ],
)
def test_child_command_argument_budget_rejects_before_host_work(
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    reason: str,
    launcher: Callable[..., object],
    input_mode: str,
) -> None:
    """A huge or unencodable argv cannot trigger launches or host probes."""
    host_calls: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        host_calls.append("host")
        message = "oversized command reached host APIs"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    monkeypatch.setattr(target_process, "_system_tool", forbidden)
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", forbidden
    )
    input_args = (b"input",) if input_mode == MEASURED_BINARY_INPUT_MODE else ()
    with pytest.raises(target_process.TargetProcessError, match=reason):
        launcher(command, *input_args)
    assert not host_calls


def test_child_command_budget_accepts_bounded_utf8_and_maximum_argv() -> None:
    """Byte-count admission must not discard real maximum-length argv runs."""
    command = [
        sys.executable,
        "-c",
        "import sys; print(len(sys.argv))",
        "☃" * 4900,
        *(["x"] * 508),
    ]
    assert len(command) == target_process.MAX_COMMAND_ARGUMENTS
    result = target_process.invoke(
        command, timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    assert result.returncode == 0
    assert result.stdout == b"510\n"
    assert result.stderr == b""


@pytest.mark.parametrize("executable", ["python3", "./compiler", "../compiler"])
def test_relative_child_executable_refused_before_launch(
    executable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process capture may not resolve relative executables through host PATH."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        del args, kwargs
        launched = True
        message = "relative child was launched"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="absolute"):
        target_process.invoke([executable], timeout_seconds=LARGE_TIMEOUT_SECONDS)
    assert not launched


def test_poisoned_path_executable_cannot_impersonate_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching basename in untrusted PATH cannot become a guest runner."""
    injected = tmp_path / "target-compiler"
    injected.write_text("#!/bin/sh\nprintf 'INJECTED'\n", encoding="ascii")
    injected.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(target_process.TargetProcessError, match="absolute"):
        target_process.invoke(["target-compiler"], timeout_seconds=LARGE_TIMEOUT_SECONDS)


@pytest.mark.parametrize(
    ("launcher", "input_mode"),
    [
        (target_process.invoke_limited_measured, "null"),
        (target_process.invoke_limited_measured_raw, "null"),
        (
            target_process.invoke_with_input_limited_measured,
            MEASURED_BINARY_INPUT_MODE,
        ),
        (
            target_process.invoke_with_input_limited_measured_raw,
            MEASURED_BINARY_INPUT_MODE,
        ),
    ],
)
@pytest.mark.parametrize(
    "command",
    [
        [],
        None,
        "echo",
        [""],
        [sys.executable, None],
        [sys.executable, "NUL\x00arg"],
    ],
)
def test_measured_child_rejects_malformed_original_command_before_tools(
    monkeypatch: pytest.MonkeyPatch,
    *,
    launcher: Callable[..., object],
    input_mode: str,
    command: object,
) -> None:
    """Measured wrappers must validate original argv before host probes."""
    tools_called = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal tools_called
        _ = (args, kwargs)
        tools_called = True
        message = "invalid measured command queried host tools"
        raise AssertionError(message)

    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", forbidden
    )
    input_args = (b"input",) if input_mode == MEASURED_BINARY_INPUT_MODE else ()
    with pytest.raises(target_process.TargetProcessError, match="command"):
        launcher(cast("list[str]", command), *input_args)
    assert not tools_called


@pytest.mark.parametrize("workspace_kind", ["symlink", "file", "missing"])
def test_measured_rss_workspace_refuses_redirected_or_non_directory_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_kind: str,
) -> None:
    """GNU time cannot allocate its private receipts outside physical .temp."""
    workspace = tmp_path / ".temp"
    if workspace_kind == "symlink":
        outside = tmp_path / "outside"
        outside.mkdir()
        workspace.symlink_to(outside, target_is_directory=True)
    elif workspace_kind == "file":
        workspace.write_bytes(b"not a directory")

    def forbidden_directory(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("RSS report workspace admitted untrusted storage")

    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", lambda: None
    )
    monkeypatch.setattr(target_process, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", forbidden_directory
    )
    with pytest.raises(target_process.TargetProcessError, match="RSS workspace"):
        target_process.invoke_limited_measured(_child("pass"))


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_measured_rss_workspace_host_inspection_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A broken host stat must not leak outside bounded RSS admission."""
    workspace = tmp_path / ".temp"
    original_lstat = type(tmp_path).lstat

    def fail_workspace(path: Path) -> os.stat_result:
        if path == workspace:
            raise failure_type("injected workspace inspection failure")
        return original_lstat(path)

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("RSS workspace inspection failure still launched tools")

    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(type(tmp_path), "lstat", fail_workspace)
    monkeypatch.setattr(target_process, "require_child_rss_measurement", forbidden)
    with pytest.raises(
        target_process.TargetProcessError, match="RSS workspace cannot be inspected"
    ) as rejected:
        target_process.invoke_limited_measured(_child("pass"))
    assert isinstance(rejected.value.__cause__, failure_type)


@pytest.mark.parametrize("phase", ["constructor", "enter", "exit"])
def test_measured_rss_directory_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Storage setup/cleanup failures cannot escape raw host exceptions."""

    class BrokenDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = (args, kwargs)
            if phase == "constructor":
                raise OSError("injected RSS directory creation failure")

        def __enter__(self) -> str:
            if phase == "enter":
                raise OSError("injected RSS directory entry failure")
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            _ = args
            if phase == "exit":
                raise OSError("injected RSS directory cleanup failure")

    def completed(*args: object, **kwargs: object) -> sp.CompletedProcess[bytes]:
        _ = (args, kwargs)
        return sp.CompletedProcess([sys.executable], 0, b"", b"")

    monkeypatch.setattr(target_process.tempfile, "TemporaryDirectory", BrokenDirectory)
    monkeypatch.setattr(target_process, "require_child_rss_measurement", lambda: None)
    monkeypatch.setattr(target_process, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(target_process, "_run", completed)
    monkeypatch.setattr(target_process, "_rss_report_bytes", lambda _path: b"10\n")
    with pytest.raises(target_process.TargetProcessError, match="RSS directory") as failure:
        target_process.invoke_limited_measured(_child("pass"))
    assert isinstance(failure.value.__cause__, OSError)


def test_measured_rss_cleanup_preserves_primary_child_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A secondary temp cleanup error cannot hide a primary subprocess error."""

    class BrokenCleanupDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = (args, kwargs)

        def __enter__(self) -> str:
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            _ = args
            raise OSError("injected secondary RSS cleanup failure")

    def failed_child(*args: object, **kwargs: object) -> sp.CompletedProcess[bytes]:
        _ = (args, kwargs)
        raise target_process.TargetProcessError("primary child capture failure")

    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", BrokenCleanupDirectory
    )
    monkeypatch.setattr(target_process, "require_child_rss_measurement", lambda: None)
    monkeypatch.setattr(target_process, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(target_process, "_run", failed_child)
    with pytest.raises(target_process.TargetProcessError, match="primary child") as failure:
        target_process.invoke_limited_measured(_child("pass"))
    assert any("RSS cleanup also failed" in note for note in failure.value.__notes__)


@pytest.mark.parametrize(
    ("launcher", "uses_input"),
    [
        (target_process.invoke_limited_measured, False),
        (target_process.invoke_limited_measured_raw, False),
        (target_process.invoke_with_input_limited_measured, True),
        (target_process.invoke_with_input_limited_measured_raw, True),
    ],
)
@pytest.mark.parametrize(
    "invalid_deadline", [None, False, True, 0, -1, 15.5, float("nan"), "3"]
)
def test_measured_child_invalid_deadline_rejects_before_host_tools(
    monkeypatch: pytest.MonkeyPatch,
    launcher: Callable[..., object],
    *,
    uses_input: bool,
    invalid_deadline: object,
) -> None:
    """Bad measured deadlines must not probe tools or create output folders."""

    def forbidden_tool_probe() -> None:
        message = "invalid measured deadline reached host tools"
        raise AssertionError(message)

    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", forbidden_tool_probe
    )
    arguments = (b"input",) if uses_input else ()
    with pytest.raises(target_process.TargetProcessError, match="deadline"):
        launcher(
            _child("print('never')"),
            *arguments,
            timeout_seconds=cast("float", invalid_deadline),
        )


def test_real_child_launch_errors_are_typed_and_preserve_cause(
    tmp_path: Path,
) -> None:
    """Missing and non-executable files must not leak host launch errors."""
    missing = tmp_path / "missing-executable"
    denied = tmp_path / "not-executable"
    denied.write_text("#!/bin/sh\nexit 0\n")
    denied.chmod(0o600)
    for executable, expected in (
        (missing, FileNotFoundError),
        (denied, PermissionError),
    ):
        with pytest.raises(
            target_process.TargetProcessError, match="launch"
        ) as error:
            target_process.invoke(
                [str(executable)], timeout_seconds=LARGE_TIMEOUT_SECONDS
            )
        assert isinstance(error.value.__cause__, expected)


def test_exact_bounded_output_and_stderr_roundtrip() -> None:
    """Both separately bounded streams retain complete exact bytes."""
    result = target_process.invoke(
        _child("import os; os.write(1, b'a'*256); os.write(2, b'b'*512)"),
        stdout_limit=STDOUT_LIMIT,
        stderr_limit=STDERR_LIMIT,
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == b"a" * STDOUT_LIMIT
    assert result.stderr == b"b" * STDERR_LIMIT


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_single_byte_beyond_limit_fails_closed(stream: str) -> None:
    """A successful exit cannot make oversized output into an admission."""
    descriptor = 1 if stream == STDOUT_NAME else 2
    limit = STDOUT_LIMIT if stream == STDOUT_NAME else STDERR_LIMIT
    source = f"import os; os.write({descriptor}, b'x'*{limit + 1})"
    with pytest.raises(target_process.TargetProcessError, match=stream):
        target_process.invoke(
            _child(source),
            stdout_limit=STDOUT_LIMIT,
            stderr_limit=STDERR_LIMIT,
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


def test_alternating_fragmented_output_does_not_truncate() -> None:
    """Chunk boundaries and concurrent pipes cannot scramble captured bytes."""
    result = target_process.invoke(
        _child(
            "import os; "
            "[(os.write(1,b'xy'), os.write(2,b'Z')) for _ in range(99)]"
        ),
        stdout_limit=STDOUT_LIMIT,
        stderr_limit=STDERR_LIMIT,
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.stdout == b"xy" * REPEAT_COUNT
    assert result.stderr == b"Z" * REPEAT_COUNT


def test_external_nonzero_status_is_not_hidden() -> None:
    """The producer can retain an external process failure as failure."""
    result = target_process.invoke(
        _child("import sys; sys.stderr.write('problem'); sys.exit(7)"),
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == EXPECTED_EXIT_CODE
    assert result.stdout == NO_STDOUT
    assert result.stderr == EXPECTED_DIAGNOSTIC


def test_explicit_binary_input_roundtrips_all_256_byte_values() -> None:
    """Binary pipe input is exact, including NUL, 0xA8 and 0xFF."""
    data = bytes(range(256))
    result = target_process.invoke_with_input(
        _child("import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"),
        data,
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == NO_STDOUT


@pytest.mark.parametrize("invalid", [bytes(257), bytearray(b"x"), "hi"])
def test_invalid_binary_input_is_rejected_before_launch(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Input is a bounded byte blob, never an untrusted streaming source."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        _ = (args, kwargs)
        launched = True

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="input"):
        target_process.invoke_with_input(
            _child("print('no')"), cast("bytes", invalid)
        )
    assert not launched


def test_empty_explicit_input_closes_stdin_to_trigger_guest_eof() -> None:
    """An explicit empty byte blob delivers immediate EOF, not a live pipe."""
    result = target_process.invoke_with_input(
        _child("import sys; print(len(sys.stdin.buffer.read()))"),
        b"",
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == EMPTY_INPUT_LENGTH


def test_input_pipe_that_is_never_read_still_obeys_wall_deadline() -> None:
    """The bounded tiny input must not block before the output deadline."""
    started = monotonic()
    with pytest.raises(sp.TimeoutExpired):
        target_process.invoke_with_input(
            _child("import time; time.sleep(5)"),
            bytes(range(256)),
            timeout_seconds=SMALL_TIMEOUT_SECONDS,
        )
    assert monotonic() - started < LARGE_TIMEOUT_SECONDS


def test_nonreading_child_is_killed_after_wall_deadline() -> None:
    """A blocked or idle child never extends the caller's wall deadline."""
    started = monotonic()
    with pytest.raises(sp.TimeoutExpired):
        target_process.invoke(
            _child("import time; time.sleep(5)"),
            timeout_seconds=SMALL_TIMEOUT_SECONDS,
        )
    assert monotonic() - started < LARGE_TIMEOUT_SECONDS


def test_inherited_pipe_descendant_cannot_delay_completion() -> None:
    """The group is terminated if a child leaks a pipe through descendants."""
    started = monotonic()
    source = (
        "import subprocess, sys; "
        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)']); "
        "sys.exit(0)"
    )
    with pytest.raises(sp.TimeoutExpired):
        target_process.invoke(
            _child(source),
            timeout_seconds=SMALL_TIMEOUT_SECONDS,
        )
    assert monotonic() - started < LARGE_TIMEOUT_SECONDS


def test_output_flood_kills_ordinary_descendants(tmp_path: Path) -> None:
    """A violating process and its ordinary descendants lose write access."""
    marker = tmp_path / "late-marker"
    descendant = (
        "import pathlib,time; time.sleep(1); "
        f"pathlib.Path({str(marker)!r}).write_text('leaked')"
    )
    source = (
        "import os, subprocess,sys; "
        f"subprocess.Popen([sys.executable,'-c',{descendant!r}]); "
        "os.write(1,b'X'*4096)"
    )
    with pytest.raises(target_process.TargetProcessError, match="stdout"):
        target_process.invoke(
            _child(source),
            stdout_limit=STDOUT_LIMIT,
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    # This regression deliberately waits past the marker's one-second delay.
    # The original child's return is not enough proof of descendant cleanup.
    sleep(1.2)
    assert not marker.exists()


def test_invalid_deadline_and_limits_reject_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject malformed, overflowing and over-policy budgets before spawn."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        _ = (args, kwargs)
        launched = True
        message = "child launched"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    for time_value, out, err in (
        (0, STDOUT_LIMIT, STDERR_LIMIT),
        (1, -1, STDERR_LIMIT),
        (1, STDOUT_LIMIT, -1),
        (float("nan"), STDOUT_LIMIT, STDERR_LIMIT),
        (float("inf"), STDOUT_LIMIT, STDERR_LIMIT),
        (float("-inf"), STDOUT_LIMIT, STDERR_LIMIT),
        (10**400, STDOUT_LIMIT, STDERR_LIMIT),
        (1e308, STDOUT_LIMIT, STDERR_LIMIT),
        (
            target_process.DEFAULT_TIMEOUT_SECONDS + 1,
            STDOUT_LIMIT,
            STDERR_LIMIT,
        ),
        (1, target_process.DEFAULT_STDOUT_LIMIT + 1, STDERR_LIMIT),
        (1, STDOUT_LIMIT, target_process.DEFAULT_STDERR_LIMIT + 1),
    ):
        with pytest.raises(target_process.TargetProcessError, match="requires"):
            target_process.invoke(
                _child("print('hello')"),
                timeout_seconds=time_value,
                stdout_limit=out,
                stderr_limit=err,
            )
    assert not launched


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_limited_child_inherits_strict_kernel_resource_ceiling() -> None:
    """The actual child sees Linux-enforced address, CPU and file ceilings."""
    source = (
        "import resource; "
        "limits=(resource.RLIMIT_AS,resource.RLIMIT_CPU,"
        "resource.RLIMIT_FSIZE); "
        "print(','.join(str(resource.getrlimit(key)[0]) for key in limits))"
    )
    result = target_process.invoke_limited(
        _child(source),
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    actual = tuple(int(value) for value in result.stdout.strip().split(b","))
    assert actual == (
        target_process.CHILD_VIRTUAL_MEMORY_BYTES,
        target_process.CHILD_CPU_SECONDS,
        target_process.CHILD_OUTPUT_FILE_BYTES,
    )


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_limited_child_output_file_size_is_kernel_enforced(
    tmp_path: Path,
) -> None:
    """A process cannot create a file beyond its configured hard RLIMIT."""
    large = target_process.CHILD_OUTPUT_FILE_BYTES + 1
    file = tmp_path / "overlarge"
    source = (
        "import pathlib; "
        f"pathlib.Path({str(file)!r}).write_bytes(bytes({large}))"
    )
    result = target_process.invoke_limited(
        _child(source),
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode != 0
    assert file.stat().st_size <= target_process.CHILD_OUTPUT_FILE_BYTES


def test_child_limit_opt_in_rejects_nonboolean_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No falsey aliases may silently disable claimed child enforcement."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        _ = (args, kwargs)
        launched = True

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="boolean"):
        target_process._limited_command(  # ruff: ignore[private-member-access]
            _child("print('never')"), enforce=cast("bool", 1)
        )
    assert not launched


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux prlimit")
def test_missing_limiter_cannot_launch_limited_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing mandatory Linux limiter is failure, not an unbounded run."""

    def unavailable(name: str, *, path: str | None = None) -> None:
        _ = name, path

    monkeypatch.setattr(target_process.shutil, "which", unavailable)
    with pytest.raises(target_process.TargetProcessError, match="prlimit"):
        target_process.invoke_limited(_child("print('never')"))


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux tools")
@pytest.mark.parametrize("tool", [target_process.LIMITER_NAME, target_process.RSS_TOOL])
@pytest.mark.parametrize(
    "invalid_path",
    [
        True,
        0,
        b"/usr/bin/prlimit",
        "",
        "prlimit",
        "../prlimit",
        "/usr/bin/prlimit\0bad",
        "\ud800",
    ],
    ids=[
        "boolean",
        "integer",
        "bytes",
        "empty",
        "relative",
        "parent",
        "nul",
        "unicode",
    ],
)
def test_resource_preflight_rejects_invalid_tool_resolution(
    monkeypatch: pytest.MonkeyPatch, tool: str, invalid_path: object
) -> None:
    """A fabricated resolver return cannot claim resource control readiness."""
    original = target_process.shutil.which

    def malformed(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            return cast("str", invalid_path)
        return original(name, path=path)

    monkeypatch.setattr(target_process.shutil, "which", malformed)
    probe = (
        target_process.require_child_resource_controls
        if tool == target_process.LIMITER_NAME
        else target_process.require_child_rss_measurement
    )
    with pytest.raises(target_process.TargetProcessError, match="system tool"):
        probe()


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux tools")
@pytest.mark.parametrize("tool", [target_process.LIMITER_NAME, target_process.RSS_TOOL])
@pytest.mark.parametrize(
    "failure_type", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_resource_preflight_types_host_tool_resolution_faults(
    monkeypatch: pytest.MonkeyPatch, tool: str, failure_type: type[Exception]
) -> None:
    """Host resolver faults remain typed tool failures before any child work."""
    original = target_process.shutil.which

    def failing(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            raise failure_type("injected host tool lookup failure")
        return original(name, path=path)

    monkeypatch.setattr(target_process.shutil, "which", failing)
    probe = (
        target_process.require_child_resource_controls
        if tool == target_process.LIMITER_NAME
        else target_process.require_child_rss_measurement
    )
    with pytest.raises(target_process.TargetProcessError, match="system tool") as error:
        probe()
    assert isinstance(error.value.__cause__, failure_type)


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_limited_binary_input_survives_kernel_resource_admission() -> None:
    """The limited child still receives exact binary stdin and EOF."""
    data = bytes(range(target_process.MAX_STDIN_BYTES))
    result = target_process.invoke_with_input_limited(
        _child("import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"),
        data,
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == NO_STDOUT


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux prlimit")
def test_missing_limiter_cannot_launch_binary_input_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No silent fallback to an unbounded runner when prlimit is absent."""
    monkeypatch.setattr(target_process.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(target_process.TargetProcessError, match="prlimit"):
        target_process.invoke_with_input_limited(_child("print('never')"), b"x")


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux prlimit")
def test_missing_limiter_is_admitted_before_target_process_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Limiter preflight must run before creating any child process."""
    launched = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal launched
        _ = (args, kwargs)
        launched = True

    monkeypatch.setattr(target_process.sp, "Popen", forbidden)
    monkeypatch.setattr(target_process.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(target_process.TargetProcessError, match="prlimit"):
        target_process.invoke_limited(_child("print('never')"))
    assert not launched


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_limited_child_virtual_address_space_cannot_exceed_kernel_ceiling() -> (
    None
):
    """A private virtual mapping beyond the hard address cap fails closed."""
    beyond = target_process.CHILD_VIRTUAL_MEMORY_BYTES + 1
    source = (
        "import mmap,sys\n"
        "try:\n"
        f"    mapping=mmap.mmap(-1,{beyond})\n"
        "except (OSError,MemoryError):\n"
        "    sys.stdout.write('blocked')\n"
        "else:\n"
        "    mapping.close()\n"
        "    sys.stdout.write('unbounded')\n"
    )
    result = target_process.invoke_limited(
        _child(source), timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    assert result.returncode == 0
    assert result.stdout == ADDRESS_LIMIT_OUTPUT


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_measured_limited_child_reports_actual_peak_rss_bytes() -> None:
    """GNU time reports positive max-RSS bytes while preserving guest output."""
    data = bytes(range(target_process.MAX_STDIN_BYTES))
    result, peak = target_process.invoke_with_input_limited_measured(
        _child("import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"),
        data,
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == data
    assert result.stderr == NO_STDOUT
    assert 1 <= peak <= target_process.CHILD_VIRTUAL_MEMORY_BYTES
    assert peak % target_process.KIB_BYTES == 0


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux tools")
def test_measured_limited_child_refuses_missing_gnu_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No measurement instrument means no successful measured experiment."""
    original = target_process.shutil.which

    def no_time(name: str, *, path: str | None = None) -> str | None:
        return None if name == target_process.RSS_TOOL else original(name, path=path)

    monkeypatch.setattr(target_process.shutil, "which", no_time)
    with pytest.raises(target_process.TargetProcessError, match="GNU time"):
        target_process.require_child_rss_measurement()


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_measured_limited_child_rejects_nonzero_exit_without_rss_credit() -> (
    None
):
    """A valid usage stamp cannot turn failed child execution into success."""
    with pytest.raises(target_process.TargetProcessError, match="successful"):
        target_process.invoke_limited_measured(
            _child("import sys;sys.exit(7)"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM or not PRLIMIT_AVAILABLE,
    reason="requires Linux with util-linux prlimit",
)
def test_successful_fake_meter_without_rss_receipt_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A zero-exit fake recorder cannot certify a missing resource sample."""
    fake = tmp_path / "time"
    fake.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
    fake.chmod(0o700)
    original = target_process.shutil.which

    def redirected(name: str, *, path: str | None = None) -> str | None:
        return str(fake) if name == target_process.RSS_TOOL else original(name, path=path)

    monkeypatch.setattr(target_process.shutil, "which", redirected)
    with pytest.raises(target_process.TargetProcessError, match="RSS"):
        target_process.invoke_limited_measured(
            _child("print('never')"), timeout_seconds=LARGE_TIMEOUT_SECONDS
        )


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or not PRLIMIT_AVAILABLE
    or shutil.which(target_process.RSS_TOOL) is None,
    reason="requires Linux prlimit and GNU time",
)
def test_measured_child_rss_increases_with_real_touched_private_pages() -> None:
    """GNU time captures physical demand pages, not a fixed fabricated cost."""
    _, baseline = target_process.invoke_limited_measured(
        _child("pass"), timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    touch = (
        "pages=bytearray(32*1024*1024); "
        "[(pages.__setitem__(n,1)) for n in range(0,len(pages),4096)]"
    )
    _, observed = target_process.invoke_limited_measured(
        _child(touch), timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    assert observed > baseline + 16 * 1024 * 1024

@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or shutil.which("prlimit", path=os.defpath) is None
    or shutil.which("time", path=os.defpath) is None,
    reason="requires system Linux prlimit and GNU time",
)
def test_hostile_path_cannot_replace_limiter_or_peak_rss_meter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untrusted PATH executables cannot impersonate resource enforcement."""
    for name in (target_process.LIMITER_NAME, target_process.RSS_TOOL):
        fake = tmp_path / name
        fake.write_text("#!/bin/sh\nprintf 'FORGED\n'\nexit 0\n", encoding="ascii")
        fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    expected = b"genuine child\n"
    child = _child("print('genuine child')")
    resolved = target_process._limited_command(  # ruff: ignore[private-member-access]
        child, enforce=True
    )
    assert resolved[0] != str(tmp_path / target_process.LIMITER_NAME)
    assert resolved[0].startswith(("/usr/bin/", "/bin/"))
    limited = target_process.invoke_limited(
        child, timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    assert limited.returncode == 0
    assert limited.stdout == expected
    measured, peak = target_process.invoke_limited_measured(
        child, timeout_seconds=LARGE_TIMEOUT_SECONDS
    )
    assert measured.returncode == 0
    assert measured.stdout == expected
    assert 0 < peak <= target_process.CHILD_VIRTUAL_MEMORY_BYTES


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_child_wait_host_failure_is_typed_without_success_receipt(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """A completed pipe cannot turn a failed wait into a verified child exit."""
    real_wait = target_process.sp.Popen.wait
    calls = 0

    def fail_first_wait(child: sp.Popen[bytes], timeout: float | None = None) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise fault("injected child exit wait failure")
        return real_wait(child, timeout=timeout)

    monkeypatch.setattr(target_process.sp.Popen, "wait", fail_first_wait)
    with pytest.raises(target_process.TargetProcessError, match="child wait") as failure:
        target_process.invoke(_child("print('completed')"), timeout_seconds=3)
    assert type(failure.value.__cause__) is fault
    assert calls >= 2  # The direct child was still reaped during cleanup.


@pytest.mark.parametrize("status", [None, False, True, "0", 0.0, object()])
def test_child_wait_noncanonical_status_cannot_claim_completion(
    monkeypatch: pytest.MonkeyPatch,
    status: object,
) -> None:
    """A fabricated zero-like status cannot impersonate a successful exit."""
    real_wait = target_process.sp.Popen.wait
    calls = 0

    def forge_first_wait(child: sp.Popen[bytes], timeout: float | None = None) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            return status
        return real_wait(child, timeout=timeout)

    monkeypatch.setattr(target_process.sp.Popen, "wait", forge_first_wait)
    with pytest.raises(target_process.TargetProcessError, match="exit status"):
        target_process.invoke(_child("print('completed')"), timeout_seconds=3)
    assert calls >= 2


@pytest.mark.parametrize("reported", [0, 1, -9])
def test_wait_integer_receipt_must_match_actual_reaped_child(
    monkeypatch: pytest.MonkeyPatch,
    reported: int,
) -> None:
    """A native integer is not proof of the actual reaped child exit status."""
    original_wait = target_process.sp.Popen.wait
    real_statuses: list[int] = []

    def wrong_wait(child: sp.Popen[bytes], timeout: float | None = None) -> int:
        real_status = original_wait(child, timeout=timeout)
        real_statuses.append(real_status)
        return reported

    monkeypatch.setattr(target_process.sp.Popen, "wait", wrong_wait)
    with pytest.raises(target_process.TargetProcessError, match="exit status"):
        target_process.invoke(_child("import sys; sys.exit(7)"), timeout_seconds=3)
    assert real_statuses == [7, 7]


@pytest.mark.parametrize("recorded", [None, False, "7", 0, object()])
def test_wait_requires_native_matching_recorded_child_status(
    monkeypatch: pytest.MonkeyPatch,
    recorded: object,
) -> None:
    """The returned exit code must agree with Popen's internal reaped value."""
    original_wait = target_process.sp.Popen.wait

    def forged_record(child: sp.Popen[bytes], timeout: float | None = None) -> int:
        status = original_wait(child, timeout=timeout)
        child.returncode = cast("int", recorded)
        return status

    monkeypatch.setattr(target_process.sp.Popen, "wait", forged_record)
    with pytest.raises(target_process.TargetProcessError, match="exit status"):
        target_process.invoke(_child("import sys; sys.exit(7)"), timeout_seconds=3)
