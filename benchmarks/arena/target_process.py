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
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISREG
from time import monotonic
from typing import TYPE_CHECKING, Never

if TYPE_CHECKING:
    from collections.abc import Iterator

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STDOUT_LIMIT = 4 * 1024
DEFAULT_STDERR_LIMIT = 16 * 1024
MAX_STDIN_BYTES = 256
MAX_COMMAND_ARGUMENTS = 512
MAX_COMMAND_BYTES = 16 * 1024
MAX_NATIVE_DESCRIPTOR = 2**31 - 1
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


def _admit_pipe_descriptor(receipt: object, *, channel: str) -> int:
    """Admit native signed C-int descriptors before any host pipe operation."""
    if type(receipt) is not int or not 0 <= receipt <= MAX_NATIVE_DESCRIPTOR:
        _fail(f"bounded target {channel} requires a native pipe descriptor")
    return receipt


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
    except Exception as error:
        # Host tool resolvers may raise unexpected ordinary dependency errors.
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
        metadata = Path(resolved).lstat()
        if type(metadata) is not os.stat_result:
            _fail(f"bounded target system tool path inspection invalid: {name}")
        mode = metadata.st_mode
        executable = os.access(resolved, os.X_OK)
        if type(executable) is not bool:
            _fail(f"bounded target system tool access inspection invalid: {name}")
    except TargetProcessError:
        raise
    except Exception as error:
        # Preserve an opaque host inspection fault without formatting it.
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
    # A foreign Popen PID could be zero (our own process group), negative
    # (an unrelated process), or a bool. Do not invoke ANY signal or poll
    # hook before admitting its native positive process identity.
    try:
        pid = child.pid
    except Exception as error:
        message = "bounded target cleanup requires a positive native PID"
        raise TargetProcessError(message) from error
    if type(pid) is not int or pid <= 0:
        _fail("bounded target cleanup requires a positive native PID")
    # A positive forged child PID could still equal our own process group.
    # Signaling -pid in that case kills the caller and its ordinary peers.
    group_error: Exception | None = None
    caller_lookup_error: Exception | None = None
    try:
        # getpgid is available only on POSIX; cross-platform stubs omit it.
        caller_group = os.getpgid(0)  # pyright: ignore[reportAttributeAccessIssue]
    except Exception as error:
        # Unknown group identity prohibits group signaling, but not the
        # direct-child kill/reap fallback. Retain the lookup fault as cause.
        group_error = TargetProcessError(
            "bounded target cleanup cannot inspect caller process group"
        )
        caller_lookup_error = error
    else:
        if type(caller_group) is not int or caller_group <= 0:
            group_error = TargetProcessError(
                "bounded target cleanup has invalid caller process group"
            )
        elif pid == caller_group:
            # Never invoke even a child wrapper's kill() when its PID names
            # our own process group: the child identity itself is suspect.
            _fail("bounded target cleanup refuses caller process group")

    if group_error is None:
        try:
            signal_receipt: object = os.kill(-pid, GROUP_KILL_SIGNAL)
            if signal_receipt is not None:
                group_error = TargetProcessError(
                    "bounded target cleanup has invalid group signal receipt"
                )
        except ProcessLookupError as error:
            # Only the native kernel ESRCH exception proves group absence.
            # A foreign subclass must not forge a successful cleanup receipt.
            if type(error) is not ProcessLookupError:
                group_error = error
        except Exception as error:
            # Unexpected host signaling faults must not bypass the direct reap.
            group_error = error

    # A refused group signal must not skip direct-child termination and reap.
    direct_error: Exception | None = None
    invalid_poll = False
    invalid_kill = False
    try:
        polled = child.poll()
        invalid_poll = polled is not None and type(polled) is not int
        # A forged non-integer poll must not skip the direct kill fallback.
        # Reap the child even when the poll receipt itself must be rejected.
        if polled is None or invalid_poll:
            try:
                kill_receipt: object = child.kill()
                invalid_kill = kill_receipt is not None
            except ProcessLookupError as error:
                if type(error) is not ProcessLookupError:
                    raise
    except Exception as error:
        direct_error = error
    if direct_error is None:
        try:
            reaped = child.wait()
            if type(reaped) is not int:
                direct_error = TargetProcessError(
                    "bounded target child cleanup has invalid wait receipt"
                )
        except Exception as error:
            direct_error = error
    if invalid_poll and direct_error is None:
        direct_error = TargetProcessError(
            "bounded target child cleanup has invalid poll receipt"
        )
    if invalid_kill and direct_error is None:
        direct_error = TargetProcessError(
            "bounded target child cleanup has invalid kill receipt"
        )
    if group_error is not None:
        if direct_error is not None:
            BaseException.add_note(
                group_error,
                "direct child cleanup also failed: " + _cleanup_error_detail(direct_error),
            )
        if caller_lookup_error is not None:
            raise group_error from caller_lookup_error
        raise group_error
    if direct_error is not None:
        raise direct_error


def _read_ready(
    key: selectors.SelectorKey,
    watched: selectors.BaseSelector,
    *,
    buffers: list[bytearray],
    limits: _ProcessLimits,
) -> bool:
    """Capture bytes or return an exact EOF receipt for one registered pipe."""
    slot: int = key.data
    limit = limits.stdout_limit if slot == 0 else limits.stderr_limit
    admitted = limit - len(buffers[slot])
    requested = min(READ_CHUNK_BYTES, admitted + 1)
    chunk = os.read(key.fd, requested)
    if type(chunk) is not bytes or len(chunk) > requested:
        _fail("bounded target output read returned invalid bytes")
    if not chunk:
        if watched.unregister(key.fileobj) is not key:
            _fail("bounded target output selector unregister receipt invalid")
        return True
    if len(chunk) > admitted:
        label = "stdout" if slot == 0 else "stderr"
        _fail(f"bounded target {label} exceeded byte limit")
    buffers[slot].extend(chunk)
    return False


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
        # Selector registration already performs a host descriptor operation.
        # Inspect both independent fileno receipts *before* registering either
        # pipe so a forged bool/negative/non-C-int or aliased handle cannot
        # reach the OS selector even transiently.
        streams = (child.stdout, child.stderr)
        stream_fds = tuple(
            _admit_pipe_descriptor(stream.fileno(), channel="output")
            for stream in streams
        )
        if stream_fds[0] == stream_fds[1]:
            _fail("bounded target output requires distinct pipe descriptors")
        with selectors.DefaultSelector() as watched:
            # Register the already validated integer snapshots, not mutable
            # stream objects whose fileno() could change during registration.
            # A forged readiness key must not relabel or redirect the pipes.
            registered = tuple(
                watched.register(descriptor, selectors.EVENT_READ, slot)
                for slot, descriptor in enumerate(stream_fds)
            )
            for slot, (stream, key) in enumerate(
                zip(streams, registered, strict=True)
            ):
                # SelectorKey.fd is not sufficient evidence of the stream's
                # descriptor: a foreign fileno() integer subclass can compare
                # equal while running caller-owned comparison hooks. Admit the
                # independent stream receipt before comparing descriptor IDs.
                stream_fd = stream.fileno()
                if (
                    type(key) is not selectors.SelectorKey
                    or key.fileobj is not stream_fds[slot]
                    or type(key.fd) is not int
                    or not 0 <= key.fd <= MAX_NATIVE_DESCRIPTOR
                    or type(stream_fd) is not int
                    or stream_fd != stream_fds[slot]
                    or key.fd != stream_fd
                    or type(key.events) is not int
                    or key.events != selectors.EVENT_READ
                    or type(key.data) is not int
                    or key.data != slot
                ):
                    _fail("bounded target output selector registration invalid")
            # The selector's mutable map cannot testify that both child pipes
            # reached EOF. Track exactly two confirmed EOFs instead.
            open_streams = {0, 1}
            while open_streams:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise sp.TimeoutExpired(child.args, limits.timeout_seconds)
                for key, mask in watched.select(remaining):
                    if (
                        (key is not registered[0] and key is not registered[1])
                        or type(mask) is not int
                        or mask != selectors.EVENT_READ
                    ):
                        _fail(
                            "bounded target output selector readiness invalid"
                        )
                    slot = 0 if key is registered[0] else 1
                    if slot not in open_streams:
                        _fail(
                            "bounded target output selector repeated EOF"
                        )
                    reached_eof = _read_ready(
                        key, watched, buffers=buffers, limits=limits
                    )
                    if reached_eof:
                        open_streams.remove(slot)
    except (TargetProcessError, sp.TimeoutExpired):
        # Preserve exact quota and deadline failures from our own transport.
        raise
    except Exception as error:
        # Selector and stream dependencies may raise any ordinary exception.
        # Never format foreign hooks or publish a partially captured stream.
        message = "bounded target output capture failed"
        raise TargetProcessError(message) from error
    return bytes(buffers[0]), bytes(buffers[1])


def _cleanup_error_detail(error: BaseException) -> str:
    # Cleanup failures may be provided by foreign stream and process wrappers.
    # Only read inert message arguments from exact native exception types.
    native = (
        OSError,
        PermissionError,
        ProcessLookupError,
        BrokenPipeError,
        FileNotFoundError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        sp.SubprocessError,
        TargetProcessError,
    )
    if type(error) in native and type(error.args) is tuple:
        # OSError.__str__ can also interpolate its mutable filename fields.
        # Extract only an inert native message argument, never the exception.
        for argument in error.args:
            if type(argument) is str and len(argument) <= 256:
                return argument
    return type(error).__name__


def _send_input(child: sp.Popen[bytes], data: bytes) -> None:
    if child.stdin is None:
        _fail("bounded target input requires an owned pipe")
    try:
        # At most 256 bytes fit in an initially empty POSIX pipe. Nonblocking
        # prevents a broken child from extending the same wall deadline.
        descriptor = _admit_pipe_descriptor(
            child.stdin.fileno(), channel="input"
        )
        if os.set_blocking(descriptor, False) is not None:
            _fail("bounded target input nonblocking setup returned invalid receipt")
        if data:
            written = os.write(descriptor, data)
            if type(written) is not int or written != len(data):
                _fail("bounded target input could not be delivered completely")
    except BrokenPipeError as error:
        message = "bounded target input pipe closed before delivery"
        raise TargetProcessError(message) from error
    except TargetProcessError:
        # Keep our own exact input-budget rejection rather than rewrapping it.
        raise
    except Exception as error:
        message = "bounded target input delivery failed"
        raise TargetProcessError(message) from error
    finally:
        primary = sys.exception()
        try:
            if child.stdin.close() is not None:
                _fail(
                    "bounded target input pipe close returned invalid receipt"
                )
        except Exception as error:
            # Foreign stream adapters can fail with any ordinary exception.
            if primary is not None:
                BaseException.add_note(
                    primary,
                    "bounded target input close also failed: "
                + _cleanup_error_detail(error)
                )
            else:
                message = "bounded target input pipe close failed"
                raise TargetProcessError(message) from error


def _finish_child(child: sp.Popen[bytes]) -> None:
    primary = sys.exception()
    cleanup_errors: list[Exception] = []
    try:
        _terminate_group(child)
    except Exception as error:
        cleanup_errors.append(error)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None:
            try:
                # Foreign wrappers cannot claim cleanup with truthy/falsey
                # state or a non-void close receipt. Real pipe APIs return
                # native booleans for closed and None from close().
                closed = stream.closed
                if type(closed) is not bool:
                    _fail("bounded target stream closed state invalid")
                if not closed and stream.close() is not None:
                    _fail("bounded target stream close returned invalid receipt")
            except Exception as error:
                # Preserve the primary failure even if close or its state
                # inspection raises an unexpected ordinary exception.
                cleanup_errors.append(error)
    if not cleanup_errors:
        return
    if primary is not None:
        for error in cleanup_errors:
            BaseException.add_note(
                primary,
                "bounded target cleanup also failed: "
                + _cleanup_error_detail(error)
            )
            # Only native errors have trustworthy, inert note containers.
            if type(error) in (OSError, PermissionError, TargetProcessError):
                notes = getattr(error, "__notes__", ())
                if type(notes) is list:
                    for detail in notes:
                        if type(detail) is str:
                            BaseException.add_note(primary, f"bounded target cleanup detail: {detail}")
        return
    message = "bounded target cleanup failed: " + _cleanup_error_detail(
        cleanup_errors[0]
    )
    failure = TargetProcessError(message)
    for error in cleanup_errors[1:]:
        failure.add_note(
            f"additional cleanup failure: {_cleanup_error_detail(error)}"
        )
    raise failure from cleanup_errors[0]


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
    except Exception as error:
        # No child handle exists yet; retain the opaque launch fault as cause.
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
        except (sp.TimeoutExpired, TargetProcessError):
            # An actual deadline or our own rejection remains authoritative.
            raise
        except Exception as error:
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
    except Exception as error:
        # A reader dependency can raise any ordinary exception, not only its
        # documented EvidenceError. Never format a foreign failure's hooks.
        message = "bounded target GNU time RSS report missing or unsafe"
        raise TargetProcessError(message) from error
    if type(raw) is not bytes or not 1 <= len(raw) <= RSS_REPORT_LIMIT:
        _fail("bounded target GNU time RSS report returned invalid bytes")
    return raw


def _parse_rss_report(raw: bytes) -> int:
    if (
        type(raw) is not bytes
        or not 1 <= len(raw) <= RSS_REPORT_LIMIT
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
    except Exception as error:
        # An unexpected host stat fault must not escape resource admission.
        message = "bounded target RSS workspace cannot be inspected"
        raise TargetProcessError(message) from error
    if type(details) is not os.stat_result:
        _fail("bounded target RSS workspace returned invalid metadata")
    if not S_ISDIR(details.st_mode):
        _fail("bounded target RSS workspace must be a physical directory")
    return workspace


def _admit_rss_directory_receipt(receipt: object, workspace: Path) -> Path:
    """Admit a fresh physical RSS directory before process launch or cleanup.

    This checks the current pathname, not race-free filesystem ownership.
    """
    if type(receipt) is not str or not receipt:
        _fail("bounded target RSS directory returned invalid path receipt")
    folder = Path(receipt)
    prefix = "arena-child-rss-"
    if (
        not folder.is_absolute()
        or str(folder) != receipt
        or folder.parent != workspace
        or not folder.name.startswith(prefix)
        or folder.name == prefix
    ):
        _fail("bounded target RSS directory returned foreign path receipt")
    try:
        details = folder.lstat()
        if type(details) is not os.stat_result or not S_ISDIR(details.st_mode):
            _fail("bounded target RSS directory must be physical")
        with os.scandir(folder) as entries:
            if next(entries, None) is not None:
                _fail("bounded target RSS directory must be initially empty")
    except TargetProcessError:
        raise
    except Exception as error:
        message = "bounded target RSS directory receipt inspection failed"
        raise TargetProcessError(message) from error
    return folder


@contextmanager
def _rss_report_directory(workspace: Path) -> Iterator[Path]:
    """Never pass an unadmitted temp path to recursive context cleanup."""
    temporary = tempfile.TemporaryDirectory(dir=workspace, prefix="arena-child-rss-")
    receipt = temporary.__enter__()
    folder = _admit_rss_directory_receipt(receipt, workspace)
    # TemporaryDirectory removes its own name in __exit__, not the name
    # yielded by __enter__. Both must identify the same admitted directory.
    cleanup_target = temporary.name
    if type(cleanup_target) is not str or cleanup_target != receipt:
        _fail("bounded target RSS directory cleanup target mismatches receipt")
    try:
        yield folder
    except BaseException as primary:
        cleanup = temporary.__exit__(type(primary), primary, primary.__traceback__)
        if cleanup is not None:
            BaseException.add_note(
                primary, "bounded target RSS directory cleanup returned invalid receipt"
            )
        raise
    else:
        if temporary.__exit__(None, None, None) is not None:
            _fail("bounded target RSS directory cleanup returned invalid receipt")


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
        with _rss_report_directory(workspace) as folder:
            try:
                report = Path(folder) / "rss.txt"
                measured_command = [
                    time_executable,
                    "--format=%M",
                    "--output",
                    str(report),
                    "--",
                    *_limited_command(command, enforce=True),
                ]
                expected_command = tuple(measured_command)
                result = _run(
                    measured_command,
                    limits=_ProcessLimits(
                        timeout_seconds,
                        DEFAULT_STDOUT_LIMIT,
                        DEFAULT_STDERR_LIMIT,
                    ),
                    input_bytes=input_bytes,
                )
                # The transport is a dependency: only native, quota-bounded
                # completion can support an RSS measurement. Compare status
                # only after exact integer admission (bool is not an exit code).
                if (
                    type(result) is not sp.CompletedProcess
                    or type(result.args) is not list
                    or result.args is not measured_command
                    or len(result.args) != len(expected_command)
                    or any(
                        type(argument) is not str or argument != expected
                        for argument, expected in zip(
                            result.args, expected_command, strict=True
                        )
                    )
                    or type(result.returncode) is not int
                    or type(result.stdout) is not bytes
                    or type(result.stderr) is not bytes
                    or len(result.stdout) > DEFAULT_STDOUT_LIMIT
                    or len(result.stderr) > DEFAULT_STDERR_LIMIT
                ):
                    _fail("bounded target GNU time returned invalid child completion")
                if result.returncode != 0:
                    _fail("bounded target GNU time requires successful child exit")
                raw = _rss_report_bytes(report)
                return result, _parse_rss_report(raw), raw
            except BaseException as error:
                primary = error
                raise
    except Exception as error:
        if error is primary and isinstance(
            error, (TargetProcessError, sp.TimeoutExpired)
        ):
            # Without a secondary directory fault, preserve the child verdict.
            raise
        if primary is not None and error is not primary:
            # An unexpected directory cleanup fault cannot replace the child.
            BaseException.add_note(
                primary,
                "bounded target RSS cleanup also failed: "
                + _cleanup_error_detail(error)
            )
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
