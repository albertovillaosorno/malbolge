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
#   - Windows DOOM debug log publication regressions.
# - Must-Not:
#   - Launch the native DOOM executable or require Windows runtime.
# - Allows:
#   - Inputs: temporary paths and mocked direct process output.
#   - Outputs: deterministic log safety and replay assertions.
#   - Side effects: temporary log files only.
# - Split-When:
#   - Split when independent native integration evidence is introduced.
# - Merge-When:
#   - Merge with an owning debug-runner test suite if one appears.
# - Summary:
#   - Guard physical sanitizer logs from redirects and unbounded echo.
# - Description:
#   - Test the direct Windows DOOM debugger without executing guest binaries.
# - Usage:
#   - Runs under the repository's Python test configuration.
# - Defaults:
#   - Unexpected file redirects and mutation fail closed.
#

"""Adversarial Windows DOOM direct-debug logging regressions."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts.debug import doom

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

FIXED_TIMESTAMP = "20261030T214500Z"
OUTSIDE_BYTES = b"preserve this external file"
EXPECTED_OUTPUT = b"sanitizer result\n"
EXPECTED_EXIT = 7
EXPECTED_LOG_COUNT = 2
ECHO_PREFIX = "ABCD"
ECHO_OMITTED = "EFG"
ECHO_NOTICE = "truncated"
RUN_DIRECT = cast(
    "Callable[[doom.LaunchConfiguration], int]", vars(doom)["_run_direct"]
)
DEBUG_DIRECTORY = cast("Callable[[Path], Path]", vars(doom)["_debug_directory"])


def _configuration(tmp_path: Path) -> doom.LaunchConfiguration:
    source_root = tmp_path / "game"
    source_root.mkdir()
    source = source_root / "doom.c"
    _ = source.write_text("int main(void) { return 0; }", encoding="ascii")
    executable_root = source_root / ".debug"
    executable_root.mkdir()
    executable = executable_root / "doom-sanitize.exe"
    _ = executable.write_bytes(b"synthetic")
    return doom.LaunchConfiguration(
        arguments=("--probe",),
        environment={},
        executable=executable,
        source=source,
    )


def _write_process_output(
    kwargs: dict[str, object],
    *,
    payload: bytes = EXPECTED_OUTPUT,
    status: int = EXPECTED_EXIT,
) -> sp.CompletedProcess[str]:
    output = cast("BinaryIO", kwargs["stdout"])
    _ = output.write(payload)
    output.flush()
    return sp.CompletedProcess(args=("fake",), returncode=status, stdout="")


def test_doom_debug_log_never_overwrites_predictable_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A preexisting second-resolution logfile link never truncates outside."""
    config = _configuration(tmp_path)
    logs = config.executable.parent / "logs"
    logs.mkdir()
    outside = tmp_path / "outside.txt"
    _ = outside.write_bytes(OUTSIDE_BYTES)
    chosen = logs / f"doom-sanitize-{FIXED_TIMESTAMP}.log"
    try:
        _ = chosen.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    monkeypatch.setattr(doom, "_timestamp", lambda: FIXED_TIMESTAMP)

    def run_process(
        *_args: object, **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = _args
        return _write_process_output(kwargs)

    monkeypatch.setattr(sp, "run", run_process)
    assert RUN_DIRECT(config) == EXPECTED_EXIT
    assert outside.read_bytes() == OUTSIDE_BYTES
    assert EXPECTED_OUTPUT.decode("ascii") in capsys.readouterr().out
    assert len(tuple(logs.glob("doom-sanitize-*"))) == EXPECTED_LOG_COUNT


def test_doom_debug_log_directory_must_not_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A linked log parent cannot redirect sanitizer bytes elsewhere."""
    config = _configuration(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    logs = config.executable.parent / "logs"
    try:
        _ = logs.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")

    def unexpected_run(*_args: object, **_kwargs: object) -> None:
        _ = (_args, _kwargs)
        pytest.fail("redirected log directory reached subprocess")

    monkeypatch.setattr(sp, "run", unexpected_run)
    with pytest.raises(doom.DoomDebugError, match="redirect"):
        _ = RUN_DIRECT(config)
    assert tuple(outside.iterdir()) == ()


def test_doom_debug_log_path_change_after_process_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The output reader never opens a substituted pathname after execution."""
    config = _configuration(tmp_path)
    outside = tmp_path / "outside.txt"
    _ = outside.write_bytes(OUTSIDE_BYTES)

    def substitute_log(
        *_args: object, **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = _args
        output = cast("BinaryIO", kwargs["stdout"])
        _ = output.write(EXPECTED_OUTPUT)
        output.flush()
        name = Path(output.name)
        name.unlink()
        _ = name.symlink_to(outside)
        return sp.CompletedProcess(args=("fake",), returncode=0, stdout="")

    monkeypatch.setattr(sp, "run", substitute_log)
    with pytest.raises(doom.DoomDebugError, match="changed"):
        _ = RUN_DIRECT(config)
    assert outside.read_bytes() == OUTSIDE_BYTES


def test_doom_debug_logs_use_unique_paths_per_same_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated runs sharing one timestamp preserve both complete logs."""
    config = _configuration(tmp_path)
    monkeypatch.setattr(doom, "_timestamp", lambda: FIXED_TIMESTAMP)

    def run_process(
        *_args: object, **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = _args
        return _write_process_output(kwargs, status=0)

    monkeypatch.setattr(sp, "run", run_process)
    assert RUN_DIRECT(config) == 0
    assert RUN_DIRECT(config) == 0
    logged = tuple((config.executable.parent / "logs").glob("doom-sanitize-*"))
    assert len(logged) == EXPECTED_LOG_COUNT
    assert all(path.read_bytes() == EXPECTED_OUTPUT for path in logged)


def test_doom_debug_console_echo_is_bounded_but_log_is_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Long diagnostics do not force the whole log into console memory."""
    config = _configuration(tmp_path)
    monkeypatch.setattr(doom, "MAX_LOG_ECHO_BYTES", 4, raising=False)
    payload = b"ABCDEFGHIJKLM"

    def run_process(
        *_args: object, **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = _args
        return _write_process_output(kwargs, payload=payload, status=0)

    monkeypatch.setattr(sp, "run", run_process)
    assert RUN_DIRECT(config) == 0
    console = capsys.readouterr().out
    assert ECHO_PREFIX in console
    assert ECHO_OMITTED not in console
    assert ECHO_NOTICE in console
    logs = tuple((config.executable.parent / "logs").glob("doom-sanitize-*"))
    assert len(logs) == 1
    assert logs[0].read_bytes() == payload


def test_doom_debug_refuses_redirected_executable_parent(
    tmp_path: Path,
) -> None:
    """A linked .debug parent never redirects the default logs directory."""
    config = _configuration(tmp_path)
    source_parent = config.executable.parent
    relocated = tmp_path / "real-debug"
    _ = source_parent.rename(relocated)
    try:
        _ = source_parent.symlink_to(relocated, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(doom.DoomDebugError, match="redirect"):
        _ = RUN_DIRECT(config)
    assert not (relocated / "logs").exists()


def test_doom_debug_detects_equal_content_inode_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacing the log with identical bytes does not retain file identity."""
    config = _configuration(tmp_path)

    def replace_log(
        *_args: object, **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = _args
        output = cast("BinaryIO", kwargs["stdout"])
        _ = output.write(EXPECTED_OUTPUT)
        output.flush()
        path = Path(output.name)
        other = tmp_path / "other-log.txt"
        _ = other.write_bytes(EXPECTED_OUTPUT)
        try:
            _ = other.replace(path)
        except PermissionError as error:
            pytest.skip(f"cannot replace open log on this host: {error}")
        return sp.CompletedProcess(args=("fake",), returncode=0, stdout="")

    monkeypatch.setattr(sp, "run", replace_log)
    with pytest.raises(doom.DoomDebugError, match="changed"):
        _ = RUN_DIRECT(config)


def test_doom_debug_build_rejects_linked_build_directory(
    tmp_path: Path,
) -> None:
    """The Zig output directory must not redirect into another tree."""
    config = _configuration(tmp_path)
    debug_root = config.executable.parent
    relocated = tmp_path / "relocated-build"
    _ = debug_root.rename(relocated)
    try:
        _ = debug_root.symlink_to(relocated, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(doom.DoomDebugError, match="redirect"):
        _ = DEBUG_DIRECTORY(config.source)
    assert not (relocated / "logs").exists()


def test_doom_debug_build_rejects_linked_binary_output(
    tmp_path: Path,
) -> None:
    """A prior executable symlink cannot select another Zig output file."""
    config = _configuration(tmp_path)
    outside = tmp_path / "outside.exe"
    _ = outside.write_bytes(OUTSIDE_BYTES)
    config.executable.unlink()
    try:
        _ = config.executable.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(doom.DoomDebugError, match="redirect"):
        _ = DEBUG_DIRECTORY(config.source)
    assert outside.read_bytes() == OUTSIDE_BYTES


def test_doom_debug_build_rejects_nonregular_binary_output(
    tmp_path: Path,
) -> None:
    """A directory at the output name is never a build-ready executable."""
    config = _configuration(tmp_path)
    config.executable.unlink()
    config.executable.mkdir()
    with pytest.raises(doom.DoomDebugError, match="regular"):
        _ = DEBUG_DIRECTORY(config.source)


def test_doom_debug_build_accepts_physical_existing_or_missing_output(
    tmp_path: Path,
) -> None:
    """Build may replace a regular file or create an absent executable."""
    config = _configuration(tmp_path)
    debug_root = config.executable.parent
    assert DEBUG_DIRECTORY(config.source) == debug_root
    config.executable.unlink()
    assert DEBUG_DIRECTORY(config.source) == debug_root
    assert not config.executable.exists()
