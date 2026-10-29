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
#   - POSIX process-group tests require Unix; basic stream tests are portable.
#

"""Bounded process transport tests for the real Malbolge target pilot."""

# ruff: file-ignore[assert]

from __future__ import annotations

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from time import monotonic
from time import sleep
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import target_process

if TYPE_CHECKING:
    from pathlib import Path

POSIX_PLATFORM = "posix"
STDOUT_NAME = "stdout"
EXPECTED_EXIT_CODE = 7
EXPECTED_DIAGNOSTIC = b"problem"
NO_STDOUT = b""
STDOUT_LIMIT = 256
STDERR_LIMIT = 512
SMALL_TIMEOUT_SECONDS = 0.2
LARGE_TIMEOUT_SECONDS = 3
REPEAT_COUNT = 99


def _child(source: str) -> list[str]:
    return [sys.executable, "-c", source]


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


def test_nonreading_child_is_killed_after_wall_deadline() -> None:
    """A blocked or idle child never extends the caller's wall deadline."""
    started = monotonic()
    with pytest.raises(sp.TimeoutExpired):
        target_process.invoke(
            _child("import time; time.sleep(5)"),
            timeout_seconds=SMALL_TIMEOUT_SECONDS,
        )
    assert monotonic() - started < LARGE_TIMEOUT_SECONDS


@pytest.mark.skipif(
    os.name != POSIX_PLATFORM, reason="requires POSIX process groups"
)
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


@pytest.mark.skipif(
    os.name != POSIX_PLATFORM, reason="requires POSIX process groups"
)
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
    """No child should start with zero or invalid stream budgets."""
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
    ):
        with pytest.raises(target_process.TargetProcessError, match="requires"):
            target_process.invoke(
                _child("print('hello')"),
                timeout_seconds=time_value,
                stdout_limit=out,
                stderr_limit=err,
            )
    assert not launched
