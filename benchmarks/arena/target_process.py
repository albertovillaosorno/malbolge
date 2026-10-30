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
#   - Fifteen seconds, four KiB stdout, sixteen KiB stderr, POSIX only.
#

"""Fail-closed, bounded POSIX subprocess transport for target research."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import math
import os
from pathlib import Path
import selectors
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from time import monotonic
from typing import Never

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STDOUT_LIMIT = 4 * 1024
DEFAULT_STDERR_LIMIT = 16 * 1024
MAX_STDIN_BYTES = 256
READ_CHUNK_BYTES = 64 * 1024
POSIX_PLATFORM = "posix"
GROUP_KILL_SIGNAL = 9
LINUX_PLATFORM = "linux"
LIMITER_NAME = "prlimit"
CHILD_VIRTUAL_MEMORY_BYTES = 1024 * 1024 * 1024
CHILD_CPU_SECONDS = 8
CHILD_OUTPUT_FILE_BYTES = 8 * 1024 * 1024


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
    if (
        type(timeout_seconds) not in {int, float}
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        _fail("bounded target process requires a positive finite deadline")
    if type(stdout_limit) is not int or stdout_limit < 0:
        _fail("bounded target process requires nonnegative stdout limit")
    if type(stderr_limit) is not int or stderr_limit < 0:
        _fail("bounded target process requires nonnegative stderr limit")


def _limited_command(command: list[str], *, enforce: bool) -> list[str]:
    if type(enforce) is not bool:
        _fail("bounded child limits require a boolean selection")
    if not enforce:
        return command
    if sys.platform != LINUX_PLATFORM:
        _fail("bounded target child resource controls require Linux")
    utility = shutil.which(LIMITER_NAME)
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
    with suppress(ProcessLookupError):
        os.kill(-child.pid, GROUP_KILL_SIGNAL)
    if child.poll() is None:
        with suppress(ProcessLookupError):
            child.kill()
    _ = child.wait()


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
    chunk = os.read(key.fd, min(READ_CHUNK_BYTES, admitted + 1))
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
    with selectors.DefaultSelector() as watched:
        watched.register(child.stdout, selectors.EVENT_READ, 0)
        watched.register(child.stderr, selectors.EVENT_READ, 1)
        while watched.get_map():
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise sp.TimeoutExpired(child.args, limits.timeout_seconds)
            for key, _ in watched.select(remaining):
                _read_ready(key, watched, buffers=buffers, limits=limits)
    return bytes(buffers[0]), bytes(buffers[1])


def _send_input(child: sp.Popen[bytes], data: bytes) -> None:
    if child.stdin is None:
        _fail("bounded target input requires an owned pipe")
    try:
        # At most 256 bytes fit in an initially empty POSIX pipe. Nonblocking
        # prevents a broken child from extending the same wall deadline.
        os.set_blocking(child.stdin.fileno(), False)
        if data and os.write(child.stdin.fileno(), data) != len(data):
            _fail("bounded target input could not be delivered completely")
    except BrokenPipeError as error:
        message = "bounded target input pipe closed before delivery"
        raise TargetProcessError(message) from error
    finally:
        child.stdin.close()


def _finish_child(child: sp.Popen[bytes]) -> None:
    _terminate_group(child)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None and not stream.closed:
            stream.close()


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
    prepared = _limited_command(command, enforce=limits.enforce_child_limits)
    started = monotonic()
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
    try:
        deadline = started + limits.timeout_seconds
        if input_bytes is not None:
            _send_input(child, input_bytes)
        stdout, stderr = _collect(child, limits, deadline=deadline)
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise sp.TimeoutExpired(command, limits.timeout_seconds)
        status = child.wait(timeout=remaining)
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
