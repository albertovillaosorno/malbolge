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
#   - Bounded POSIX child process capture for target emitters and VM replay.
# - Must-Not:
#   - Assert study-wide memory/RSS or full descendant containment.
# - Allows:
#   - Inputs: explicit child arguments, deadline and stream limits.
#   - Outputs: complete stdout/stderr/status, or a typed failure.
#   - Side effects: a child session and best-effort ordinary-group cleanup.
# - Split-When:
#   - Generic arena execution requires resource cgroups or Windows pipes.
# - Merge-When:
#   - A strict common research subprocess adapter replaces this POSIX slice.
# - Summary:
#   - Bounded dual-stream capture without unbounded communicate allocations.
# - Description:
#   - One wall deadline, output quotas, isolated child group, optional prlimit.
# - Usage:
#   - invoke([absolute_program, *args], timeout_seconds=15).
# - Defaults:
#   - Fifteen seconds, bounded output, 512 argv entries/16 KiB, POSIX only.
#

"""Fail-closed, bounded POSIX subprocess transport for target research."""

from __future__ import annotations

import os
import selectors
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISREG
from time import monotonic
from typing import Never

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STDOUT_LIMIT = 4 * 1024
DEFAULT_STDERR_LIMIT = 16 * 1024
MAX_STDIN_BYTES = 256
MAX_COMMAND_ARGUMENTS = 512
MAX_COMMAND_BYTES = 16 * 1024
READ_CHUNK_BYTES = 64 * 1024
POSIX_PLATFORM = "posix"
GROUP_KILL_SIGNAL = 9
LINUX_PLATFORM = "linux"
LIMITER_NAME = "prlimit"
CHILD_VIRTUAL_MEMORY_BYTES = 1024 * 1024 * 1024
CHILD_CPU_SECONDS = 8
CHILD_OUTPUT_FILE_BYTES = 8 * 1024 * 1024
RSS_TOOL = "time"
RSS_REPORT_LIMIT = 32
KIB_BYTES = 1024
SYSTEM_TOOL_SEARCH_PATH = os.defpath
NUL_CHARACTER = "\0"


@dataclass(frozen=True, slots=True)
class _ProcessLimits:
    timeout_seconds: float
    stdout_limit: int
    stderr_limit: int
    enforce_child_limits: bool = False


class TargetProcessError(sp.SubprocessError):
    """A child violates its bounded output or platform contract."""


def _fail(message: str) -> Never:
    raise TargetProcessError(message)


def _admit_limits(
    timeout_seconds: float, stdout_limit: int, stderr_limit: int
) -> None:
    if os.name != POSIX_PLATFORM:
        _fail("bounded target process requires POSIX pipe admission")
    # Comparing against small policy ceilings first also rejects enormous
    # Python integers without an overflowing int-to-float conversion.
    if type(timeout_seconds) not in {int, float} or not (
        0 < timeout_seconds <= DEFAULT_TIMEOUT_SECONDS
    ):
        _fail("bounded target process requires a deadline within 15 seconds")
    if type(stdout_limit) is not int or not (
        0 <= stdout_limit <= DEFAULT_STDOUT_LIMIT
    ):
        _fail("bounded target process requires stdout limit at most 4 KiB")
    if type(stderr_limit) is not int or not (
        0 <= stderr_limit <= DEFAULT_STDERR_LIMIT
    ):
        _fail("bounded target process requires stderr limit at most 16 KiB")


def _admit_command(command: list[str]) -> None:
    if type(command) is not list or not command:
        _fail("bounded target command requires a nonempty argument list")
    if len(command) > MAX_COMMAND_ARGUMENTS:
        _fail("bounded target command exceeds argument count limit")
    if type(command[0]) is not str or not command[0]:
        _fail("bounded target command requires a nonempty executable string")
    # Reject host PATH lookup and relative cwd resolution: the caller must
    # select the exact binary path before the bounded process is launched.
    if not Path(command[0]).is_absolute():
        _fail("bounded target command requires an absolute executable path")
    total_bytes = 0
    for argument in command:
        if type(argument) is not str or NUL_CHARACTER in argument:
            _fail("bounded target command has nonstring or NUL arguments")
        # Bound both Python-side argv allocation and the actual exec byte
        # payload. The NUL terminator counts toward the cumulative budget.
        if len(argument) > MAX_COMMAND_BYTES:
            _fail("bounded target command exceeds argument bytes limit")
        try:
            total_bytes += len(os.fsencode(argument)) + 1
        except UnicodeError as error:
            message = "bounded target command requires encodable filesystem text"
            raise TargetProcessError(message) from error
        if total_bytes > MAX_COMMAND_BYTES:
            _fail("bounded target command exceeds argument bytes limit")


def _system_tool(name: str) -> str | None:
    """Resolve OS-owned resource tools without trusting a caller's PATH."""
    try:
        resolved = shutil.which(name, path=SYSTEM_TOOL_SEARCH_PATH)
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        message = f"bounded target system tool lookup failed: {name}"
        raise TargetProcessError(message) from error
    if resolved is None:
        return None
    if (
        type(resolved) is not str
        or not resolved
        or NUL_CHARACTER in resolved
        or not Path(resolved).is_absolute()
    ):
        _fail(f"bounded target system tool has invalid executable path: {name}")
    try:
        _ = os.fsencode(resolved)
    except UnicodeError as error:
        message = f"bounded target system tool has unencodable path: {name}"
        raise TargetProcessError(message) from error
    try:
        mode = Path(resolved).lstat().st_mode
        executable = os.access(resolved, os.X_OK)
    except (
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
    ) as error:
        message = f"bounded target system tool path inspection failed: {name}"
        raise TargetProcessError(message) from error
    if not S_ISREG(mode) or not executable:
        _fail(f"bounded target system tool requires a physical executable: {name}")
    return resolved


def _limited_command(command: list[str], *, enforce: bool) -> list[str]:
    if type(enforce) is not bool:
        _fail("bounded child limits require a boolean selection")
    if not enforce:
        return command
    if sys.platform != LINUX_PLATFORM:
        _fail("bounded target child resource controls require Linux")
    utility = _system_tool(LIMITER_NAME)
    if utility is None:
        _fail("bounded target child resource controls require prlimit")
    return [
        utility,
        f"--as={CHILD_VIRTUAL_MEMORY_BYTES}:{CHILD_VIRTUAL_MEMORY_BYTES}",
        f"--cpu={CHILD_CPU_SECONDS}:{CHILD_CPU_SECONDS}",
        f"--fsize={CHILD_OUTPUT_FILE_BYTES}:{CHILD_OUTPUT_FILE_BYTES}",
        "--",
        *command,
    ]


def require_child_resource_controls() -> None:
    """Refuse a limited study when Linux or mandatory prlimit is missing."""
    _ = _limited_command([], enforce=True)


def _terminate_group(child: sp.Popen[bytes]) -> None:
    # Never signal an unrelated process: each child owns a fresh session.
    group_error: OSError | None = None
    try:
        os.kill(-child.pid, GROUP_KILL_SIGNAL)
    except ProcessLookupError:
        pass
    except OSError as error:
        group_error = error

    # A refused group signal must not skip direct-child termination and reap.
    direct_error: OSError | None = None
    try:
        if child.poll() is None:
            with suppress(ProcessLookupError):
                child.kill()
    except OSError as error:
        direct_error = error
    if direct_error is None:
        try:
            _ = child.wait()
        except OSError as error:
            direct_error = error
    if group_error is not None:
        if direct_error is not None:
            group_error.add_note(f"direct child cleanup also failed: {direct_error}")
        raise group_error
    if direct_error is not None:
        raise direct_error


def _read_ready(
    key: selectors.SelectorKey,
    watched: selectors.BaseSelector,
    *,
    buffers: list[bytearray],
    limits: _ProcessLimits,
) -> None:
    slot: int = key.data
    limit = limits.stdout_limit if slot == 0 else limits.stderr_limit
    admitted = limit - len(buffers[slot])
    requested = min(READ_CHUNK_BYTES, admitted + 1)
    chunk = os.read(key.fd, requested)
    if type(chunk) is not bytes or len(chunk) > requested:
        _fail("bounded target output read returned invalid bytes")
    if not chunk:
        watched.unregister(key.fileobj)
        return
    if len(chunk) > admitted:
        label = "stdout" if slot == 0 else "stderr"
        _fail(f"bounded target {label} exceeded byte limit")
    buffers[slot].extend(chunk)


def _collect(
    child: sp.Popen[bytes],
    limits: _ProcessLimits,
    *,
    deadline: float,
) -> tuple[bytes, bytes]:
    if child.stdout is None or child.stderr is None:
        _fail("bounded target process requires separate output pipes")
    buffers = [bytearray(), bytearray()]
    try:
        with selectors.DefaultSelector() as watched:
            watched.register(child.stdout, selectors.EVENT_READ, 0)
            watched.register(child.stderr, selectors.EVENT_READ, 1)
            while watched.get_map():
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise sp.TimeoutExpired(child.args, limits.timeout_seconds)
                for key, _ in watched.select(remaining):
                    _read_ready(key, watched, buffers=buffers, limits=limits)
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        message = "bounded target output capture failed"
        raise TargetProcessError(message) from error
    return bytes(buffers[0]), bytes(buffers[1])


def _send_input(child: sp.Popen[bytes], data: bytes) -> None:
    if child.stdin is None:
        _fail("bounded target input requires an owned pipe")
    try:
        # At most 256 bytes fit in an initially empty POSIX pipe. Nonblocking
        # prevents a broken child from extending the same wall deadline.
        os.set_blocking(child.stdin.fileno(), False)
        if data:
            written = os.write(child.stdin.fileno(), data)
            if type(written) is not int or written != len(data):
                _fail("bounded target input could not be delivered completely")
    except BrokenPipeError as error:
        message = "bounded target input pipe closed before delivery"
        raise TargetProcessError(message) from error
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        message = "bounded target input delivery failed"
        raise TargetProcessError(message) from error
    finally:
        primary = sys.exception()
        try:
            child.stdin.close()
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
            if primary is not None:
                primary.add_note(f"bounded target input close also failed: {error}")
            else:
                message = "bounded target input pipe close failed"
                raise TargetProcessError(message) from error


def _finish_child(child: sp.Popen[bytes]) -> None:
    primary = sys.exception()
    cleanup_errors: list[Exception] = []
    try:
        _terminate_group(child)
    except (OSError, ValueError, RuntimeError, sp.SubprocessError) as error:
        cleanup_errors.append(error)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except (OSError, ValueError, RuntimeError) as error:
                cleanup_errors.append(error)
    if not cleanup_errors:
        return
    if primary is not None:
        for error in cleanup_errors:
            primary.add_note(f"bounded target cleanup also failed: {error}")
            for detail in getattr(error, "__notes__", ()):
                primary.add_note(f"bounded target cleanup detail: {detail}")
        return
    for error in cleanup_errors[1:]:
        cleanup_errors[0].add_note(f"additional cleanup failure: {error}")
    message = f"bounded target cleanup failed: {cleanup_errors[0]}"
    raise TargetProcessError(message) from cleanup_errors[0]


def _run(
    command: list[str],
    *,
    limits: _ProcessLimits,
    input_bytes: bytes | None,
) -> sp.CompletedProcess[bytes]:
    _admit_limits(
        limits.timeout_seconds,
        limits.stdout_limit,
        limits.stderr_limit,
    )
    _admit_command(command)
    prepared = _limited_command(command, enforce=limits.enforce_child_limits)
    started = monotonic()
    try:
        child = sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
            prepared,
            shell=False,
            cwd=_ROOT,
            stdin=sp.PIPE if input_bytes is not None else sp.DEVNULL,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            start_new_session=True,
            close_fds=True,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        AttributeError,
        sp.SubprocessError,
    ) as error:
        message = "bounded target child launch failed"
        raise TargetProcessError(message) from error
    try:
        deadline = started + limits.timeout_seconds
        if input_bytes is not None:
            _send_input(child, input_bytes)
        stdout, stderr = _collect(child, limits, deadline=deadline)
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise sp.TimeoutExpired(command, limits.timeout_seconds)
        try:
            status = child.wait(timeout=remaining)
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
            message = "bounded target child wait failed"
            raise TargetProcessError(message) from error
        if (
            type(status) is not int
            or type(child.returncode) is not int
            or status != child.returncode
        ):
            _fail("bounded target child wait returned unverified exit status")
        return sp.CompletedProcess(command, status, stdout, stderr)
    finally:
        _finish_child(child)


def invoke(
    command: list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    stdout_limit: int = DEFAULT_STDOUT_LIMIT,
    stderr_limit: int = DEFAULT_STDERR_LIMIT,
) -> sp.CompletedProcess[bytes]:
    """Run one child with null stdin and strictly bounded output streams.

    Returns:
        Captured complete stdout/stderr and child exit status.

    """
    return _run(
        command,
        limits=_ProcessLimits(timeout_seconds, stdout_limit, stderr_limit),
        input_bytes=None,
    )


def invoke_with_input(
    command: list[str],
    input_bytes: bytes,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> sp.CompletedProcess[bytes]:
    """Send at most 256 exact binary bytes, closing stdin before observation.

    Returns:
        Complete stdout/stderr and exit status for one child.

    """
    if type(input_bytes) is not bytes or len(input_bytes) > MAX_STDIN_BYTES:
        _fail("bounded target input requires up to 256 exact bytes")
    return _run(
        command,
        limits=_ProcessLimits(
            timeout_seconds,
            DEFAULT_STDOUT_LIMIT,
            DEFAULT_STDERR_LIMIT,
        ),
        input_bytes=input_bytes,
    )


def invoke_limited(
    command: list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    stdout_limit: int = DEFAULT_STDOUT_LIMIT,
    stderr_limit: int = DEFAULT_STDERR_LIMIT,
) -> sp.CompletedProcess[bytes]:
    """Run one Linux child with inherited enforced RLIMIT_AS/CPU/FSIZE.

    Returns:
        Exact bounded child output/exit status under physical per-child caps.

    """
    return _run(
        command,
        limits=_ProcessLimits(
            timeout_seconds,
            stdout_limit,
            stderr_limit,
            enforce_child_limits=True,
        ),
        input_bytes=None,
    )


def invoke_with_input_limited(
    command: list[str],
    input_bytes: bytes,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> sp.CompletedProcess[bytes]:
    """Run one Linux resource-limited child with exact bounded binary stdin.

    Returns:
        Complete bounded captured output and child return code.

    """
    if type(input_bytes) is not bytes or len(input_bytes) > MAX_STDIN_BYTES:
        _fail("bounded target input requires up to 256 exact bytes")
    return _run(
        command,
        limits=_ProcessLimits(
            timeout_seconds,
            DEFAULT_STDOUT_LIMIT,
            DEFAULT_STDERR_LIMIT,
            enforce_child_limits=True,
        ),
        input_bytes=input_bytes,
    )


def require_child_rss_measurement() -> None:
    """Require Linux prlimit and GNU time before measured study creation."""
    require_child_resource_controls()
    path = _system_tool(RSS_TOOL)
    if path is None:
        _fail("bounded target peak RSS requires GNU time")


def _rss_report_bytes(path: Path) -> bytes:
    from benchmarks.arena import evidence  # ruff: ignore[import-outside-top-level]

    try:
        raw = evidence.read_bounded_regular(
            path.parent, path.name, limit=RSS_REPORT_LIMIT
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        evidence.EvidenceError,
    ) as error:
        message = "bounded target GNU time RSS report missing or unsafe"
        raise TargetProcessError(message) from error
    return raw


def _parse_rss_report(raw: bytes) -> int:
    if (
        not 1 <= len(raw) <= RSS_REPORT_LIMIT
        or not raw.endswith(b"\n")
        or not raw[:-1].isdigit()
    ):
        _fail("bounded target GNU time RSS report missing or malformed")
    kib = int(raw[:-1])
    if kib <= 0 or kib > CHILD_VIRTUAL_MEMORY_BYTES // KIB_BYTES:
        _fail("bounded target GNU time RSS observation outside child limits")
    return kib * KIB_BYTES


def _rss_report(path: Path) -> int:
    return _parse_rss_report(_rss_report_bytes(path))


def _rss_workspace() -> Path:
    """Admit a physical repository scratch directory before RSS reporting.

    This rejects a stable symlink redirect, not an atomic filesystem race.
    """
    workspace = _ROOT / ".temp"
    try:
        details = workspace.lstat()
    except (OSError, ValueError, RuntimeError) as error:
        message = "bounded target RSS workspace cannot be inspected"
        raise TargetProcessError(message) from error
    if not S_ISDIR(details.st_mode):
        _fail("bounded target RSS workspace must be a physical directory")
    return workspace


def _measured_limited(
    command: list[str],
    *,
    input_bytes: bytes | None,
    timeout_seconds: float,
) -> tuple[sp.CompletedProcess[bytes], int, bytes]:
    # Reject invalid deadlines before probing host tools or creating a
    # temporary RSS report directory. _run repeats admission at launch.
    _admit_limits(timeout_seconds, DEFAULT_STDOUT_LIMIT, DEFAULT_STDERR_LIMIT)
    _admit_command(command)
    workspace = _rss_workspace()
    require_child_rss_measurement()
    time_executable = _system_tool(RSS_TOOL)
    if time_executable is None:
        _fail("bounded target peak RSS requires GNU time")
    primary: BaseException | None = None
    try:
        with tempfile.TemporaryDirectory(
            dir=workspace, prefix="arena-child-rss-"
        ) as folder:
            try:
                report = Path(folder) / "rss.txt"
                result = _run(
                    [
                        time_executable,
                        "--format=%M",
                        "--output",
                        str(report),
                        "--",
                        *_limited_command(command, enforce=True),
                    ],
                    limits=_ProcessLimits(
                        timeout_seconds,
                        DEFAULT_STDOUT_LIMIT,
                        DEFAULT_STDERR_LIMIT,
                    ),
                    input_bytes=input_bytes,
                )
                if result.returncode != 0:
                    _fail("bounded target GNU time requires successful child exit")
                raw = _rss_report_bytes(report)
                return result, _parse_rss_report(raw), raw
            except BaseException as error:
                primary = error
                raise
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        if primary is not None and error is not primary:
            # Directory cleanup must not replace the original child failure.
            primary.add_note(f"bounded target RSS cleanup also failed: {error}")
            raise primary from error
        message = "bounded target RSS directory access failed"
        raise TargetProcessError(message) from error


def invoke_limited_measured(
    command: list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[sp.CompletedProcess[bytes], int]:
    """Run a physically limited child and report its GNU-time peak RSS.

    Returns:
        Exact guest streams/status and observed per-child peak RSS bytes.

    """
    result, peak, _ = _measured_limited(
        command,
        input_bytes=None,
        timeout_seconds=timeout_seconds,
    )
    return result, peak


def invoke_with_input_limited_measured(
    command: list[str],
    input_bytes: bytes,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[sp.CompletedProcess[bytes], int]:
    """Run one limited binary-input child and obtain its peak RSS bytes.

    Returns:
        Exact guest streams/status and observed per-child peak RSS bytes.

    """
    if type(input_bytes) is not bytes or len(input_bytes) > MAX_STDIN_BYTES:
        _fail("bounded target input requires up to 256 exact bytes")
    result, peak, _ = _measured_limited(
        command,
        input_bytes=input_bytes,
        timeout_seconds=timeout_seconds,
    )
    return result, peak


def invoke_limited_measured_raw(
    command: list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[sp.CompletedProcess[bytes], int, bytes]:
    """Run limited child and retain the actual GNU-time report bytes.

    Returns:
        Child status and stdout/stderr, integer RSS bytes and raw GNU time.

    """
    return _measured_limited(
        command, input_bytes=None, timeout_seconds=timeout_seconds
    )


def invoke_with_input_limited_measured_raw(
    command: list[str],
    input_bytes: bytes,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[sp.CompletedProcess[bytes], int, bytes]:
    """Run limited binary-input child and retain its raw GNU-time report.

    Returns:
        Child status, measured RSS bytes and original GNU time file bytes.

    """
    if type(input_bytes) is not bytes or len(input_bytes) > MAX_STDIN_BYTES:
        _fail("bounded target input requires up to 256 exact bytes")
    return _measured_limited(
        command, input_bytes=input_bytes, timeout_seconds=timeout_seconds
    )
