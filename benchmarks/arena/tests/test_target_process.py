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
from time import monotonic, sleep
from typing import TYPE_CHECKING, cast

import pytest

from benchmarks.arena import target_process

if TYPE_CHECKING:
    from pathlib import Path

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
