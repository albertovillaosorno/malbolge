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
from typing import TYPE_CHECKING, Any, cast, override

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


@pytest.mark.parametrize("invalid", [False, True, 0, b"sent"])
def test_foreign_group_signal_acknowledgement_cannot_claim_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Only native os.kill's void result can confirm group signaling."""
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> int:
            events.append("poll")
            return 0

        def wait(self) -> int:
            events.append("wait")
            return 0

    def forged_group_acknowledgement(_group: int, _signal: int) -> object:
        events.append("group")
        return invalid

    monkeypatch.setattr(target_process.os, "kill", forged_group_acknowledgement)
    with pytest.raises(target_process.TargetProcessError, match="group signal"):
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert events == ["group", "poll", "wait"]


@pytest.mark.parametrize("invalid", [False, True, 0, b"sent"])
def test_foreign_direct_kill_acknowledgement_cannot_claim_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """An invalid child.kill receipt still permits direct reaping."""
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> object:
            events.append("kill")
            return invalid

        def wait(self) -> int:
            events.append("wait")
            return 0

    monkeypatch.setattr(target_process.os, "kill", lambda *_args: None)
    with pytest.raises(target_process.TargetProcessError, match="kill"):
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert events == ["poll", "kill", "wait"]


@pytest.mark.parametrize("invalid", [False, True, "exited", 0.0])
def test_foreign_child_poll_receipt_cannot_skip_direct_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Boolean and foreign poll results must not prove child termination."""
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> object:
            events.append("poll")
            return invalid

        def kill(self) -> None:
            events.append("kill")

        def wait(self) -> int:
            events.append("wait")
            return 0

    monkeypatch.setattr(target_process.os, "kill", lambda *_args: None)
    with pytest.raises(target_process.TargetProcessError, match="poll"):
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert events == ["poll", "kill", "wait"]


@pytest.mark.parametrize("invalid", [None, False, "0", 0.0])
def test_foreign_child_wait_receipt_cannot_claim_reaped_child(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """A non-native wait receipt cannot prove that cleanup completed."""
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> int:
            events.append("poll")
            return 0

        def kill(self) -> None:
            events.append("kill")

        def wait(self) -> object:
            events.append("wait")
            return invalid

    monkeypatch.setattr(target_process.os, "kill", lambda *_args: None)
    with pytest.raises(target_process.TargetProcessError, match="wait"):
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert events == ["poll", "wait"]


class _ForeignMissingProcessGroup(ProcessLookupError):
    """Caller-owned absence subclasses cannot assert OS process-group state."""

    @override
    def __str__(self) -> str:
        raise AssertionError("foreign process-group failure was formatted")


def test_foreign_process_group_absence_cannot_claim_completed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only a native ESRCH confirms no group remained to signal."""
    original_kill = os.kill
    fault = _ForeignMissingProcessGroup("injected false group absence")

    def forge_group_absence(group: int, signal: int) -> None:
        if group < 0:
            raise fault
        original_kill(group, signal)

    monkeypatch.setattr(target_process.os, "kill", forge_group_absence)
    with pytest.raises(target_process.TargetProcessError, match="cleanup") as caught:
        target_process.invoke(
            _child("print('produced')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert caught.value.__cause__ is fault


def test_foreign_group_absence_still_attempts_direct_child_reap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An untrusted ESRCH subclass cannot skip fallback direct cleanup."""
    fault = _ForeignMissingProcessGroup("injected false group absence")
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")

        def wait(self) -> int:
            events.append("wait")
            return 0

    def forge_group_absence(_group: int, _signal: int) -> None:
        events.append("group")
        raise fault

    monkeypatch.setattr(target_process.os, "kill", forge_group_absence)
    with pytest.raises(_ForeignMissingProcessGroup) as caught:
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value is fault
    assert events == ["group", "poll", "kill", "wait"]


def test_foreign_direct_child_absence_cannot_claim_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged child.kill ESRCH cannot bypass a required direct reap."""
    fault = _ForeignMissingProcessGroup("injected false direct absence")
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")
            raise fault

        def wait(self) -> int:
            events.append("wait")
            return 0

    monkeypatch.setattr(target_process.os, "kill", lambda *_args: None)
    with pytest.raises(_ForeignMissingProcessGroup) as caught:
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value is fault
    assert events == ["poll", "kill"]


def test_native_process_group_and_direct_absence_are_admitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual native ESRCH still permits the completed child to be reaped."""
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")
            raise ProcessLookupError("native direct process is already gone")

        def wait(self) -> int:
            events.append("wait")
            return 0

    def missing_group(_group: int, _signal: int) -> None:
        events.append("group")
        raise ProcessLookupError("native process group is already gone")

    monkeypatch.setattr(target_process.os, "kill", missing_group)
    target_process._terminate_group(  # ruff: ignore[private-member-access]
        cast("sp.Popen[bytes]", ChildProbe())
    )
    assert events == ["group", "poll", "kill", "wait"]


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


class _HostileCleanupFault(RuntimeError):
    """A foreign exception's string method must never be called."""

    def __str__(self) -> str:
        raise AssertionError("foreign target cleanup exception formatted")


class _HostileCleanupArg:
    """Even native exception arguments may run arbitrary formatters."""

    def __str__(self) -> str:
        raise AssertionError("foreign target cleanup argument formatted")


class _UnexpectedTargetHostFault(Exception):
    """Foreign host adapter failures must not reach their formatter."""

    def __str__(self) -> str:
        raise AssertionError("foreign target host error formatter executed")


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_unexpected_group_signal_failure_still_reaps_direct_child(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """An opaque group signal failure must still reach direct-child fallback."""
    fault = fault_class("unexpected group signal fault")
    events: list[str] = []

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")

        def wait(self) -> int:
            events.append("wait")
            return 0

    def signal_group(_group: int, _signal: int) -> None:
        events.append("group")
        raise fault

    monkeypatch.setattr(target_process.os, "kill", signal_group)
    with pytest.raises(fault_class) as caught:
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value is fault
    assert events == ["group", "poll", "kill", "wait"]


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_unexpected_direct_poll_failure_remains_typed_in_finish_child(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unexpected direct poll faults cannot claim clean child cleanup."""
    fault = fault_class("unexpected child poll fault")

    class ChildProbe:
        pid = 123456
        stdin = None
        stdout = None
        stderr = None

        def poll(self) -> None:
            raise fault

    monkeypatch.setattr(target_process.os, "kill", lambda *_args: None)
    with pytest.raises(
        target_process.TargetProcessError, match="cleanup"
    ) as caught:
        target_process._finish_child(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value.__cause__ is fault


def test_target_cleanup_native_oserror_with_hostile_filename_is_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a native OSError can interpolate foreign filename metadata."""
    cleanup_error = OSError(5, "native file cleanup failure")
    cleanup_error.filename = _HostileCleanupArg()

    class FaultyStream:
        closed = False

        def close(self) -> None:
            raise cleanup_error

    class ChildProbe:
        stdin = FaultyStream()
        stdout = None
        stderr = None

    monkeypatch.setattr(target_process, "_terminate_group", lambda _child: None)
    with pytest.raises(target_process.TargetProcessError, match="primary") as raised:
        try:
            raise target_process.TargetProcessError("primary output rejection")
        finally:
            target_process._finish_child(  # ruff: ignore[private-member-access]
                cast("sp.Popen[bytes]", ChildProbe())
            )
    assert any(
        "native file cleanup failure" in note for note in raised.value.__notes__
    )


@pytest.mark.parametrize(
    "cleanup_error",
    [
        _HostileCleanupFault("foreign stream failure"),
        RuntimeError(_HostileCleanupArg()),
    ],
)
def test_target_cleanup_failure_never_formats_foreign_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: RuntimeError,
) -> None:
    """Stream cleanup cannot replace a primary error or forge a clean exit."""

    class FaultyStream:
        closed = False

        def close(self) -> None:
            raise cleanup_error

    class ChildProbe:
        stdin = FaultyStream()
        stdout = None
        stderr = None

    monkeypatch.setattr(target_process, "_terminate_group", lambda _child: None)
    child = cast("sp.Popen[bytes]", ChildProbe())
    with pytest.raises(target_process.TargetProcessError, match="primary") as raised:
        try:
            raise target_process.TargetProcessError("primary output rejection")
        finally:
            target_process._finish_child(child)  # ruff: ignore[private-member-access]
    assert any("cleanup also failed" in note for note in raised.value.__notes__)

    with pytest.raises(target_process.TargetProcessError, match="cleanup") as final:
        target_process._finish_child(child)  # ruff: ignore[private-member-access]
    assert final.value.__cause__ is cleanup_error


@pytest.mark.parametrize(
    "cleanup_error",
    [
        _HostileCleanupFault("foreign stream failure"),
        RuntimeError(_HostileCleanupArg()),
    ],
)
def test_input_cleanup_preserves_delivery_fault_with_hostile_close(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: RuntimeError,
) -> None:
    """A hostile input close exception cannot replace the write failure."""

    class FaultyStream:
        def fileno(self) -> int:
            return 1

        def close(self) -> None:
            raise cleanup_error

    class ChildProbe:
        stdin = FaultyStream()

    def fail_write(descriptor: int, data: bytes) -> int:
        del descriptor, data
        raise OSError("primary delivery failed")

    monkeypatch.setattr(target_process.os, "set_blocking", lambda *_args: None)
    monkeypatch.setattr(target_process.os, "write", fail_write)
    with pytest.raises(target_process.TargetProcessError, match="delivery") as raised:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b"x"
        )
    assert type(raised.value.__cause__) is OSError
    assert any("input close also failed" in note for note in raised.value.__notes__)


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
    "forgery", ["swapped-stream", "boolean-slot", "copied-key", "write-mask"]
)
def test_output_selector_rejects_forged_readiness_receipts(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A selector cannot relabel a ready stdout fd or invent its read mask."""
    original_selector = target_process.selectors.DefaultSelector
    injected = False

    def forged_selector() -> target_process.selectors.BaseSelector:
        selector = original_selector()
        real_select = selector.select

        def forged_select(timeout: float | None = None):
            nonlocal injected
            ready = real_select(timeout)
            if injected or not ready:
                return ready
            injected = True
            key, mask = ready[0]
            if forgery == "swapped-stream":
                key = key._replace(data=1 if key.data == 0 else 0)
            elif forgery == "boolean-slot":
                key = key._replace(data=bool(key.data))
            elif forgery == "copied-key":
                key = key._replace()
            else:
                mask = target_process.selectors.EVENT_WRITE
            return [(key, mask), *ready[1:]]

        monkeypatch.setattr(selector, "select", forged_select)
        return selector

    monkeypatch.setattr(
        target_process.selectors, "DefaultSelector", forged_selector
    )
    with pytest.raises(target_process.TargetProcessError, match="readiness"):
        target_process.invoke(
            _child("import os; os.write(1, b'only-stdout')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert injected


def test_output_capture_requires_both_real_eof_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fabricated empty selector map cannot silently discard child stdout."""
    original_selector = target_process.selectors.DefaultSelector

    def empty_map_selector() -> target_process.selectors.BaseSelector:
        selector = original_selector()
        monkeypatch.setattr(selector, "get_map", dict)
        return selector

    monkeypatch.setattr(
        target_process.selectors, "DefaultSelector", empty_map_selector
    )
    result = target_process.invoke(
        _child("import os; os.write(1, b'complete-record')"),
        timeout_seconds=LARGE_TIMEOUT_SECONDS,
    )
    assert result.returncode == 0
    assert result.stdout == b"complete-record"
    assert result.stderr == b""


@pytest.mark.parametrize(
    "forgery",
    [
        "foreign-fd",
        "foreign-stream",
        "wrong-events",
        "swapped-slot",
        "boolean-slot",
        "absent-key",
    ],
)
def test_output_selector_rejects_forged_registration_receipts(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """Only registered stdout/stderr read keys can authorize future reads."""
    original_selector = target_process.selectors.DefaultSelector

    def forged_selector() -> target_process.selectors.BaseSelector:
        selector = original_selector()
        real_register = selector.register
        injected = False

        def forged_register(fileobj: Any, events: int, data: object = None):
            nonlocal injected
            key = real_register(fileobj, events, data)
            if injected:
                return key
            injected = True
            if forgery == "foreign-fd":
                return key._replace(fd=key.fd + 1)
            if forgery == "foreign-stream":
                return key._replace(fileobj=object())
            if forgery == "wrong-events":
                return key._replace(events=target_process.selectors.EVENT_WRITE)
            if forgery == "swapped-slot":
                return key._replace(data=1)
            if forgery == "boolean-slot":
                return key._replace(data=False)
            return None

        monkeypatch.setattr(selector, "register", forged_register)
        return selector

    monkeypatch.setattr(
        target_process.selectors, "DefaultSelector", forged_selector
    )
    with pytest.raises(target_process.TargetProcessError, match="registration"):
        target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


def test_output_selector_requires_exact_eof_unregistration_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged unregister result cannot certify that both pipes closed."""
    original_selector = target_process.selectors.DefaultSelector

    def forged_selector() -> target_process.selectors.BaseSelector:
        selector = original_selector()
        real_unregister = selector.unregister

        def forged_unregister(fileobj: Any) -> None:
            real_unregister(fileobj)

        monkeypatch.setattr(selector, "unregister", forged_unregister)
        return selector

    monkeypatch.setattr(
        target_process.selectors, "DefaultSelector", forged_selector
    )
    with pytest.raises(
        target_process.TargetProcessError, match="unregister receipt"
    ):
        target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )


class _HostileSelectorFault(Exception):
    """A failed selector may originate in a foreign dependency wrapper."""

    def __str__(self) -> str:
        raise AssertionError("foreign target selector formatter executed")


@pytest.mark.parametrize("stage", ["construct", "select"])
@pytest.mark.parametrize(
    "fault_class", [IndexError, OverflowError, _HostileSelectorFault]
)
def test_unexpected_selector_fault_is_typed_without_foreign_formatters(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault_class: type[Exception],
) -> None:
    """Unexpected ordinary selector failures cannot escape the output boundary."""
    original_selector = target_process.selectors.DefaultSelector
    fault = fault_class("untrusted selector failure")

    def broken_selector() -> target_process.selectors.BaseSelector:
        if stage == "construct":
            raise fault
        selector = original_selector()

        def broken_select(timeout: float | None = None) -> None:
            del timeout
            raise fault

        monkeypatch.setattr(selector, "select", broken_select)
        return selector

    monkeypatch.setattr(target_process.selectors, "DefaultSelector", broken_selector)
    with pytest.raises(
        target_process.TargetProcessError, match="output capture"
    ) as caught:
        target_process.invoke(
            _child("import os; os.write(1, b'output')"),
            timeout_seconds=LARGE_TIMEOUT_SECONDS,
        )
    assert caught.value.__cause__ is fault


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


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_measured_rss_workspace_unexpected_host_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unanticipated workspace stat errors cannot escape resource admission."""
    workspace = tmp_path / ".temp"
    fault = fault_class("unexpected workspace inspection")
    real_lstat = type(tmp_path).lstat

    def broken_lstat(path: Path) -> os.stat_result:
        if path == workspace:
            raise fault
        return real_lstat(path)

    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(type(tmp_path), "lstat", broken_lstat)
    with pytest.raises(
        target_process.TargetProcessError, match="RSS workspace"
    ) as caught:
        target_process.invoke_limited_measured(_child("pass"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("phase", ["constructor", "enter", "exit"])
@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_measured_rss_unexpected_directory_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    fault_class: type[Exception],
) -> None:
    """Unexpected temp-directory setup and close faults remain typed."""
    fault = fault_class("unexpected temporary directory failure")

    class BrokenDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            if phase == "constructor":
                raise fault

        def __enter__(self) -> str:
            if phase == "enter":
                raise fault
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            del args
            if phase == "exit":
                raise fault

    def completed(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        del kwargs
        return sp.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", BrokenDirectory
    )
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", lambda: None
    )
    monkeypatch.setattr(
        target_process, "_system_tool", lambda _name: "/usr/bin/time"
    )
    monkeypatch.setattr(target_process, "_run", completed)
    monkeypatch.setattr(
        target_process, "_rss_report_bytes", lambda _path: b"10\n"
    )
    with pytest.raises(
        target_process.TargetProcessError, match="RSS directory"
    ) as caught:
        target_process.invoke_limited_measured(_child("pass"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_measured_rss_unexpected_cleanup_preserves_primary_child_failure(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unexpected RSS cleanup faults cannot replace the child failure."""
    fault = fault_class("unexpected RSS cleanup")
    primary = target_process.TargetProcessError("original RSS child error")

    class BrokenDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> str:
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            del args
            raise fault

    def rejected_child(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise primary

    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", BrokenDirectory
    )
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", lambda: None
    )
    monkeypatch.setattr(
        target_process, "_system_tool", lambda _name: "/usr/bin/time"
    )
    monkeypatch.setattr(target_process, "_run", rejected_child)
    with pytest.raises(
        target_process.TargetProcessError, match="original RSS child error"
    ) as caught:
        target_process.invoke_limited_measured(_child("pass"))
    assert caught.value is primary
    assert caught.value.__cause__ is fault
    assert any("RSS cleanup also failed" in note for note in primary.__notes__)


@pytest.mark.parametrize("kind", ["typed", "timeout"])
def test_measured_rss_transparent_directory_preserves_primary_child_exception(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """RSS directory admission cannot relabel a normal child rejection."""
    primary: Exception = (
        target_process.TargetProcessError("original target child failure")
        if kind == "typed"
        else sp.TimeoutExpired([sys.executable], 1)
    )

    class TransparentDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> str:
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            del args

    def rejected_child(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise primary

    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", TransparentDirectory
    )
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", lambda: None
    )
    monkeypatch.setattr(
        target_process, "_system_tool", lambda _name: "/usr/bin/time"
    )
    monkeypatch.setattr(target_process, "_run", rejected_child)
    with pytest.raises(type(primary)) as caught:
        target_process.invoke_limited_measured(_child("pass"))
    assert caught.value is primary


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

    def completed(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        del kwargs
        return sp.CompletedProcess(command, 0, b"", b"")

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
    "cleanup_error",
    [
        _HostileCleanupFault("foreign RSS cleanup"),
        RuntimeError(_HostileCleanupArg()),
    ],
)
def test_measured_rss_cleanup_preserves_primary_under_hostile_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: RuntimeError,
) -> None:
    """Foreign cleanup errors cannot mask a primary limited-child failure."""

    class BrokenCleanupDirectory:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def __enter__(self) -> str:
            return "/ignored-test-receipt-directory"

        def __exit__(self, *args: object) -> None:
            del args
            raise cleanup_error

    def failed_child(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise target_process.TargetProcessError("primary child capture failure")

    monkeypatch.setattr(
        target_process.tempfile, "TemporaryDirectory", BrokenCleanupDirectory
    )
    monkeypatch.setattr(target_process, "require_child_rss_measurement", lambda: None)
    monkeypatch.setattr(target_process, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(target_process, "_run", failed_child)
    with pytest.raises(target_process.TargetProcessError, match="primary child") as raised:
        target_process.invoke_limited_measured(_child("pass"))
    assert any("RSS cleanup also failed" in note for note in raised.value.__notes__)


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


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_unexpected_launch_host_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unexpected subprocess construction faults retain typed launch errors."""
    fault = fault_class("foreign launch fault")

    def fail_launch(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(target_process.sp, "Popen", fail_launch)
    with pytest.raises(
        target_process.TargetProcessError, match="launch"
    ) as caught:
        target_process.invoke(_child("print('never')"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_unexpected_child_wait_host_fault_preserves_cause_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unexpected child wait failures cannot claim a verified child status."""
    fault = fault_class("foreign child wait fault")
    real_wait = target_process.sp.Popen.wait
    calls = 0

    def fail_once(child: sp.Popen[bytes], timeout: float | None = None) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise fault
        return real_wait(child, timeout=timeout)

    monkeypatch.setattr(target_process.sp.Popen, "wait", fail_once)
    with pytest.raises(
        target_process.TargetProcessError, match="child wait"
    ) as caught:
        target_process.invoke(_child("print('finished')"), timeout_seconds=3)
    assert caught.value.__cause__ is fault
    assert calls >= 2


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
def test_unexpected_input_delivery_host_fault_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Host pipe setup failures cannot evade the binary input contract."""
    fault = fault_class("foreign input delivery fault")
    closes = 0

    class InputProbe:
        def fileno(self) -> int:
            return 1

        def close(self) -> None:
            nonlocal closes
            closes += 1

    class ChildProbe:
        stdin = InputProbe()

    def fail_blocking(_fd: int, _enabled: bool) -> None:
        raise fault

    monkeypatch.setattr(target_process.os, "set_blocking", fail_blocking)
    with pytest.raises(
        target_process.TargetProcessError, match="input delivery"
    ) as caught:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b""
        )
    assert caught.value.__cause__ is fault
    assert closes == 1


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
@pytest.mark.parametrize("kind", ["symlink", "directory", "missing", "non-executable"])
def test_resource_preflight_requires_physical_executable_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    kind: str,
) -> None:
    """Only real executable system files may provide child resource controls."""
    fake = tmp_path / "fake-resource-tool"
    if kind == "symlink":
        fake.symlink_to(sys.executable)
    elif kind == "directory":
        fake.mkdir()
    elif kind == "non-executable":
        _ = fake.write_bytes(b"no execution")
        fake.chmod(0o644)
    original = target_process.shutil.which

    def fake_resolver(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            return str(fake)
        return original(name, path=path)

    monkeypatch.setattr(target_process.shutil, "which", fake_resolver)
    probe = (
        target_process.require_child_resource_controls
        if tool == target_process.LIMITER_NAME
        else target_process.require_child_rss_measurement
    )
    diagnostic = "inspection" if kind == "missing" else "physical executable"
    with pytest.raises(target_process.TargetProcessError, match=diagnostic):
        probe()


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="uses Linux tools")
@pytest.mark.parametrize("tool", [target_process.LIMITER_NAME, target_process.RSS_TOOL])
@pytest.mark.parametrize("operation", ["lstat", "access"])
@pytest.mark.parametrize(
    "failure_type", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_resource_preflight_types_executable_inspection_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    operation: str,
    failure_type: type[Exception],
) -> None:
    """Unexpected host metadata failures must retain typed child preflight errors."""
    fake = tmp_path / "fake-resource-tool"
    _ = fake.write_bytes(b"dummy executable")
    fake.chmod(0o755)
    fault = failure_type("injected system executable inspection failure")
    original_resolver = target_process.shutil.which
    original_lstat = type(fake).lstat
    original_access = target_process.os.access

    def fake_resolver(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            return str(fake)
        return original_resolver(name, path=path)

    def fail_lstat(path: Path) -> object:
        if path == fake:
            raise fault
        return original_lstat(path)

    def fail_access(path: str, mode: int) -> bool:
        if path == str(fake):
            raise fault
        return original_access(path, mode)

    monkeypatch.setattr(target_process.shutil, "which", fake_resolver)
    if operation == "lstat":
        monkeypatch.setattr(type(fake), "lstat", fail_lstat)
    else:
        monkeypatch.setattr(target_process.os, "access", fail_access)
    probe = (
        target_process.require_child_resource_controls
        if tool == target_process.LIMITER_NAME
        else target_process.require_child_rss_measurement
    )
    with pytest.raises(target_process.TargetProcessError, match="inspection") as caught:
        probe()
    assert caught.value.__cause__ is fault


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


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetHostFault]
)
@pytest.mark.parametrize("site", ["lookup", "lstat", "access"])
def test_resource_tool_unexpected_dependency_fault_remains_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
    site: str,
) -> None:
    """Unexpected tool resolver and metadata errors retain their cause."""
    fake = tmp_path / "fake-resource-tool"
    _ = fake.write_bytes(b"test executable")
    fake.chmod(0o755)
    fault = fault_class("unexpected system tool failure")
    real_lstat = type(fake).lstat
    real_access = target_process.os.access

    def resolve(_name: str, *, path: str | None = None) -> str:
        del path
        if site == "lookup":
            raise fault
        return str(fake)

    def inspect(path: Path) -> os.stat_result:
        if site == "lstat" and path == fake:
            raise fault
        return real_lstat(path)

    def executable(path: str, mode: int) -> bool:
        if site == "access" and path == str(fake):
            raise fault
        return real_access(path, mode)

    monkeypatch.setattr(target_process.shutil, "which", resolve)
    monkeypatch.setattr(type(fake), "lstat", inspect)
    monkeypatch.setattr(target_process.os, "access", executable)
    expected = "lookup" if site == "lookup" else "inspection"
    with pytest.raises(
        target_process.TargetProcessError, match=expected
    ) as caught:
        target_process._system_tool(  # ruff: ignore[private-member-access]
            target_process.LIMITER_NAME
        )
    assert caught.value.__cause__ is fault


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


class _HostilePrimaryTargetError(target_process.TargetProcessError):
    """A foreign primary error must not control secondary note attachment."""

    @override
    def add_note(self, note: str) -> None:
        del note
        raise AssertionError("foreign primary target add_note hook was invoked")


def test_target_finish_child_bypasses_foreign_primary_add_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Closing a broken process stream cannot replace the primary failure."""

    class BrokenStream:
        closed = False

        def close(self) -> None:
            raise OSError("secondary target stream close failure")

    class ChildProbe:
        stdin = BrokenStream()
        stdout = None
        stderr = None

    monkeypatch.setattr(target_process, "_terminate_group", lambda _child: None)
    failure = _HostilePrimaryTargetError("original target process failure")
    with pytest.raises(_HostilePrimaryTargetError, match="original target") as caught:
        try:
            raise failure
        finally:
            target_process._finish_child(  # ruff: ignore[private-member-access]
                cast("sp.Popen[bytes]", ChildProbe())
            )
    assert caught.value is failure
    assert failure.__notes__ == [
        "bounded target cleanup also failed: secondary target stream close failure"
    ]


def test_target_input_close_bypasses_foreign_primary_add_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed input close cannot mask a foreign typed delivery failure."""

    class InputProbe:
        def fileno(self) -> int:
            return 1

        def close(self) -> None:
            raise OSError("secondary target input close failure")

    class ChildProbe:
        stdin = InputProbe()

    failure = _HostilePrimaryTargetError("original input delivery failure")

    def reject_blocking(_descriptor: int, _blocking: bool) -> None:
        raise failure

    monkeypatch.setattr(target_process.os, "set_blocking", reject_blocking)
    with pytest.raises(_HostilePrimaryTargetError, match="original input") as caught:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b""
        )
    assert caught.value is failure
    assert failure.__notes__ == [
        "bounded target input close also failed: secondary target input close failure"
    ]


class _UnexpectedTargetCleanupError(Exception):
    """Foreign cleanup code may throw outside the usual I/O error family."""

    def __str__(self) -> str:
        raise AssertionError("unexpected target cleanup formatter executed")


@pytest.mark.parametrize("stage", ["group", "stream-closed", "stream-close"])
@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetCleanupError]
)
def test_unexpected_child_cleanup_preserves_primary_failure(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault_class: type[Exception],
) -> None:
    """Unexpected cleanup errors never replace an existing child rejection."""
    fault = fault_class("unexpected child cleanup")
    attempts: list[str] = []

    class BrokenStream:
        @property
        def closed(self) -> bool:
            if stage == "stream-closed":
                raise fault
            return False

        def close(self) -> None:
            attempts.append("close")
            if stage == "stream-close":
                raise fault

    class ChildProbe:
        stdin = BrokenStream()
        stdout = None
        stderr = None

    def broken_termination(_child: object) -> None:
        attempts.append("terminate")
        if stage == "group":
            raise fault

    monkeypatch.setattr(target_process, "_terminate_group", broken_termination)
    primary = _HostilePrimaryTargetError("primary child output rejection")
    with pytest.raises(
        _HostilePrimaryTargetError, match="primary child"
    ) as caught:
        try:
            raise primary
        finally:
            target_process._finish_child(  # ruff: ignore[private-member-access]
                cast("sp.Popen[bytes]", ChildProbe())
            )
    assert caught.value is primary
    assert any("cleanup also failed" in note for note in primary.__notes__)
    assert attempts == (
        ["terminate"] if stage == "stream-closed" else ["terminate", "close"]
    )


@pytest.mark.parametrize(
    "fault_class", [IndexError, _UnexpectedTargetCleanupError]
)
def test_unexpected_input_close_preserves_primary_failure(
    monkeypatch: pytest.MonkeyPatch,
    fault_class: type[Exception],
) -> None:
    """Unexpected input close cannot conceal the delivery rejection."""
    fault = fault_class("unexpected input close")

    class InputProbe:
        def fileno(self) -> int:
            return 1

        def close(self) -> None:
            raise fault

    class ChildProbe:
        stdin = InputProbe()

    primary = _HostilePrimaryTargetError("primary input delivery rejection")

    def reject_blocking(_descriptor: int, _blocking: bool) -> None:
        raise primary

    monkeypatch.setattr(target_process.os, "set_blocking", reject_blocking)
    with pytest.raises(
        _HostilePrimaryTargetError, match="primary input"
    ) as caught:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b""
        )
    assert caught.value is primary
    assert any("input close also failed" in note for note in primary.__notes__)


@pytest.mark.parametrize("stage", ["group", "stream-closed", "stream-close"])
def test_unexpected_cleanup_without_primary_is_typed_and_causal(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Standalone cleanup faults cannot escape as foreign exceptions."""
    fault = _UnexpectedTargetCleanupError("unexpected standalone cleanup")

    class BrokenStream:
        @property
        def closed(self) -> bool:
            if stage == "stream-closed":
                raise fault
            return False

        def close(self) -> None:
            if stage == "stream-close":
                raise fault

    class ChildProbe:
        stdin = BrokenStream()
        stdout = None
        stderr = None

    def terminate(_child: object) -> None:
        if stage == "group":
            raise fault

    monkeypatch.setattr(target_process, "_terminate_group", terminate)
    with pytest.raises(
        target_process.TargetProcessError, match="cleanup"
    ) as caught:
        target_process._finish_child(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value.__cause__ is fault


def test_unexpected_input_close_without_primary_is_typed_and_causal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unsuccessful input close cannot claim exact EOF delivery."""
    fault = _UnexpectedTargetCleanupError("unexpected input close")

    class InputProbe:
        def fileno(self) -> int:
            return 0

        def close(self) -> None:
            raise fault

    class ChildProbe:
        stdin = InputProbe()

    monkeypatch.setattr(target_process.os, "set_blocking", lambda *_args: None)
    with pytest.raises(
        target_process.TargetProcessError, match="input pipe close"
    ) as caught:
        target_process._send_input(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), b""
        )
    assert caught.value.__cause__ is fault


def test_target_group_cleanup_bypasses_hostile_primary_and_direct_formatters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refused group signal survives an untrusted direct-child failure."""

    class HostileGroupError(OSError):
        @override
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign group add_note hook invoked")

    class HostileDirectError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign direct-child formatter invoked")

    class ChildProbe:
        pid = 123456

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            raise HostileDirectError("secondary direct child failure")

    failure = HostileGroupError("primary process group failure")

    def reject_group(_group: int, _signal: int) -> None:
        raise failure

    monkeypatch.setattr(target_process.os, "kill", reject_group)
    with pytest.raises(HostileGroupError, match="primary process group") as caught:
        target_process._terminate_group(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe())
        )
    assert caught.value is failure
    assert failure.__notes__ == [
        "direct child cleanup also failed: HostileDirectError"
    ]


class _ForeignTargetStat:
    """A fake stat record must not control resource or executable admission."""

    def __getattribute__(self, name: str) -> object:
        if name.startswith("st_"):
            pytest.fail("foreign target stat field was accessed")
        return super().__getattribute__(name)


class _ForeignRssBytes(bytes):
    """A foreign report may override data length or parsing behavior."""

    def __len__(self) -> int:
        pytest.fail("foreign GNU-time byte length was accessed")


@pytest.mark.parametrize("kind", ["foreign", "oversized"])
def test_rss_report_reader_rejects_invalid_dependency_bytes_before_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A substituted report reader cannot assert an admitted GNU time receipt."""
    report = tmp_path / "rss.txt"
    report.write_bytes(b"10\n")
    forged = (
        cast("bytes", _ForeignRssBytes(b"10\n"))
        if kind == "foreign"
        else b"10\n" + b"0" * target_process.RSS_REPORT_LIMIT
    )
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: forged
    )
    with pytest.raises(target_process.TargetProcessError, match="invalid bytes"):
        target_process._rss_report_bytes(report)


def test_rss_parser_rejects_foreign_bytes_before_using_parse_hooks() -> None:
    """Direct RSS parser callers cannot substitute their own byte semantics."""
    with pytest.raises(target_process.TargetProcessError, match="malformed"):
        target_process._parse_rss_report(cast("bytes", _ForeignRssBytes(b"10\n")))


def test_rss_workspace_rejects_foreign_stat_before_directory_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report directory cannot be admitted from forged filesystem fields."""
    workspace = tmp_path / ".temp"
    workspace.mkdir()
    original_lstat = type(workspace).lstat

    def injected_lstat(path: Path) -> os.stat_result:
        if path == workspace:
            return cast("os.stat_result", _ForeignTargetStat())
        return original_lstat(path)

    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(type(workspace), "lstat", injected_lstat)
    with pytest.raises(target_process.TargetProcessError, match="workspace"):
        target_process._rss_workspace()


@pytest.mark.parametrize("phase", ["metadata", "access"])
def test_resource_tool_preflight_rejects_foreign_host_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Host executable admission requires native metadata and bool access."""
    tool = tmp_path / "system-tool"
    tool.write_bytes(b"test executable")
    tool.chmod(0o755)
    real_lstat = type(tool).lstat
    real_access = target_process.os.access

    def injected_lstat(path: Path) -> os.stat_result:
        if phase == "metadata" and path == tool:
            return cast("os.stat_result", _ForeignTargetStat())
        return real_lstat(path)

    def injected_access(path: str, mode: int) -> bool:
        if phase == "access" and path == str(tool):
            return cast("bool", 1)
        return real_access(path, mode)

    monkeypatch.setattr(target_process.shutil, "which", lambda *_args, **_kwargs: str(tool))
    monkeypatch.setattr(type(tool), "lstat", injected_lstat)
    monkeypatch.setattr(target_process.os, "access", injected_access)
    with pytest.raises(target_process.TargetProcessError, match="inspection|physical"):
        target_process._system_tool(target_process.RSS_TOOL)


class _ForeignMeasuredCompletion(sp.CompletedProcess[bytes]):
    """An injected result must not execute foreign status accessors."""

    def __getattribute__(self, name: str) -> object:
        if name == "returncode":
            pytest.fail("foreign measured returncode was accessed")
        return super().__getattribute__(name)


class _ForgedExitStatus(int):
    """An integer subtype may pretend a failed process exited zero."""

    def __ne__(self, other: object) -> bool:
        del other
        pytest.fail("foreign measured status comparison executed")


@pytest.mark.parametrize(
    "forgery", ["wrong-command", "copied-command", "mutated-command"]
)
def test_measured_rss_refuses_substituted_completed_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A successful RSS receipt must bind to the exact launched command."""
    (tmp_path / ".temp").mkdir()
    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_process, "require_child_rss_measurement", lambda: None
    )
    monkeypatch.setattr(
        target_process, "_system_tool", lambda _name: "/usr/bin/time"
    )
    monkeypatch.setattr(
        target_process, "_rss_report_bytes", lambda _path: b"10\n"
    )

    def forged_run(
        command: list[str], **_options: object
    ) -> sp.CompletedProcess[bytes]:
        if forgery == "wrong-command":
            receipt = ["/unrelated/executable"]
        elif forgery == "copied-command":
            receipt = command.copy()
        else:
            command[0] = "/unrelated/executable"
            receipt = command
        return sp.CompletedProcess(receipt, 0, b"", b"")

    monkeypatch.setattr(target_process, "_run", forged_run)
    with pytest.raises(
        target_process.TargetProcessError, match="child completion"
    ):
        target_process.invoke_limited_measured(_child("print('never')"))


@pytest.mark.parametrize(
    "kind",
    [
        "foreign-completion",
        "bool-status",
        "foreign-status",
        "foreign-stdout",
        "oversized-stdout",
        "foreign-stderr",
        "oversized-stderr",
    ],
)
def test_measured_rss_requires_exact_bounded_native_child_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A substituted child cannot attest successful bounded RSS execution."""
    (tmp_path / ".temp").mkdir()
    monkeypatch.setattr(target_process, "_ROOT", tmp_path)
    monkeypatch.setattr(target_process, "require_child_rss_measurement", lambda: None)
    monkeypatch.setattr(target_process, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(target_process, "_rss_report_bytes", lambda _path: b"10\n")
    def forged_run(
        command: list[str], **_options: object
    ) -> sp.CompletedProcess[bytes]:
        if kind == "foreign-completion":
            return _ForeignMeasuredCompletion(command, 0, b"", b"")
        status = (
            cast("int", False)
            if kind == "bool-status"
            else _ForgedExitStatus(7)
            if kind == "foreign-status"
            else 0
        )
        stdout = (
            cast("bytes", _ForeignRssBytes(b""))
            if kind == "foreign-stdout"
            else b"x" * (target_process.DEFAULT_STDOUT_LIMIT + 1)
            if kind == "oversized-stdout"
            else b""
        )
        stderr = (
            cast("bytes", _ForeignRssBytes(b""))
            if kind == "foreign-stderr"
            else b"x" * (target_process.DEFAULT_STDERR_LIMIT + 1)
            if kind == "oversized-stderr"
            else b""
        )
        return sp.CompletedProcess(command, status, stdout, stderr)

    monkeypatch.setattr(target_process, "_run", forged_run)
    with pytest.raises(
        target_process.TargetProcessError, match="invalid child completion"
    ):
        target_process.invoke_limited_measured(_child("print('never')"))
