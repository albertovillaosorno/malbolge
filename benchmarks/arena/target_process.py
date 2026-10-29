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
#   - Assert study-wide memory or full descendant containment.
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
#   - One cumulative wall deadline, exact output quotas, isolated child group.
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
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from time import monotonic
from typing import Never

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_STDOUT_LIMIT = 4 * 1024
DEFAULT_STDERR_LIMIT = 16 * 1024
READ_CHUNK_BYTES = 64 * 1024
POSIX_PLATFORM = "posix"
GROUP_KILL_SIGNAL = 9


@dataclass(frozen=True, slots=True)
class _ProcessLimits:
    timeout_seconds: float
    stdout_limit: int
    stderr_limit: int


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


def invoke(
    command: list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    stdout_limit: int = DEFAULT_STDOUT_LIMIT,
    stderr_limit: int = DEFAULT_STDERR_LIMIT,
) -> sp.CompletedProcess[bytes]:
    """Run one child, returning complete bounded streams or typed failure.

    Returns:
        Captured complete stdout/stderr and child exit status.

    Raises:
        TimeoutExpired: The shared wall deadline was exceeded.

    """
    _admit_limits(timeout_seconds, stdout_limit, stderr_limit)
    started = monotonic()
    child = sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        shell=False,
        cwd=_ROOT,
        stdin=sp.DEVNULL,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        start_new_session=True,
        close_fds=True,
    )
    try:
        deadline = started + timeout_seconds
        stdout, stderr = _collect(
            child,
            _ProcessLimits(timeout_seconds, stdout_limit, stderr_limit),
            deadline=deadline,
        )
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise sp.TimeoutExpired(command, timeout_seconds)
        status = child.wait(timeout=remaining)
        return sp.CompletedProcess(command, status, stdout, stderr)
    finally:
        _terminate_group(child)
        if child.stdout is not None:
            child.stdout.close()
        if child.stderr is not None:
            child.stderr.close()
