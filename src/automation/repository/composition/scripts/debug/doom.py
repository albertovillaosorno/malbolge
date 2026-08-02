# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Build and run the local DOOM artifact with sanitizers or LLDB.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Build and run the local DOOM artifact with sanitizers or LLDB."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
import os
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import] - local argv
import sys
from typing import Never
from typing import TYPE_CHECKING

from scripts.repository_root import repository_root

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = repository_root(Path(__file__))
DEFAULT_SOURCE = (
    ROOT / "src/research/algorithms/domain/algorithms/doom/amalgamate/in/doom.c"
)
ADAPTER = (
    ROOT / "src/interface/command-line/adapter-outbound/adapters/doom/windows.c"
)
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
LLDB = ROOT / ".dependencies/llvm/22.1.8/bin/lldb.exe"
ZIG = ROOT / ".dependencies/zig/0.16.0/zig.exe"
WINDOWS_OS_NAME = "nt"
ARGUMENT_SEPARATOR = "--"
IWAD_ARGUMENT = "-iwad"
CONFIGURATION_ERROR = 2
IWAD_NAMES = (
    "freedoom1.wad",
    "freedoom2.wad",
    "doom2.wad",
    "doomu.wad",
    "doom.wad",
    "doom1.wad",
    "plutonia.wad",
    "tnt.wad",
)
STRICT_FLAGS = (
    "-std=c23",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wundef",
    "-Wcast-qual",
    "-Wcast-align",
    "-Wswitch-enum",
    "-Wswitch-default",
    "-Wvla",
    "-Wimplicit-fallthrough",
    "-Wstrict-prototypes",
    "-Wmissing-prototypes",
    "-Wmissing-variable-declarations",
    "-Wnull-dereference",
    "-Werror",
    "-fsyntax-only",
)
WINDOWS_LIBRARIES = (
    "-luser32",
    "-lgdi32",
    "-lwinmm",
    "-lws2_32",
    "-lole32",
    "-luuid",
    "-ldsound",
    "-ldxguid",
    "-lshell32",
)


class DoomDebugError(RuntimeError):
    """The sanitizer/debug launch contract could not be satisfied."""


class _Arguments(argparse.Namespace):
    """Typed command-line arguments."""

    build_only: bool
    forwarded: list[str]
    iwad: Path | None
    lldb: bool
    source: Path

    def __init__(self) -> None:
        """Initialize defaults before argparse mutates the namespace."""
        super().__init__()
        self.build_only = False
        self.forwarded = []
        self.iwad = None
        self.lldb = False
        self.source = DEFAULT_SOURCE


@dataclass(frozen=True, slots=True)
class LaunchConfiguration:
    """Resolved process launch state."""

    arguments: tuple[str, ...]
    environment: dict[str, str]
    executable: Path
    source: Path


def _fail(message: str) -> Never:
    raise DoomDebugError(message)


def _write_standard_output(text: str) -> None:
    _ = sys.stdout.write(text)
    _ = sys.stdout.flush()


def _existing_file(path: Path, description: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        _fail(f"{description} is missing: {resolved}")
    return resolved


def _run_checked(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        rendered = subprocess.list2cmdline(list(command))
        _fail(f"command failed with status {completed.returncode}: {rendered}")


def _clang_validation_commands(
    source: Path,
) -> tuple[tuple[str, ...], ...]:
    common = (
        str(CLANG),
        "--target=x86_64-pc-windows-msvc",
        *STRICT_FLAGS,
    )
    return (
        (*common, str(source)),
        (*common, str(ADAPTER)),
    )


def _configured_iwad(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return _existing_file(explicit, "IWAD")
    configured = os.environ.get("MALBOLGE_DOOM_IWAD")
    if configured is None:
        return None
    candidate = Path(configured).expanduser().resolve()
    return candidate if candidate.is_file() else None


def _iwad_directories(source_directory: Path) -> tuple[Path, ...]:
    return (
        source_directory,
        source_directory / "data/wad",
        ROOT / "doom/data/wad",
        ROOT
        / "src/research/algorithms/domain/algorithms/doom/quality/out"
        / "doom_fixed/data/wad",
    )


def _search_iwad(source_directory: Path) -> Path | None:
    for directory in _iwad_directories(source_directory):
        for name in IWAD_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate.resolve()
    return None


def _discover_iwad(source_directory: Path, explicit: Path | None) -> Path:
    candidate = _configured_iwad(explicit)
    if candidate is None:
        candidate = _search_iwad(source_directory)
    if candidate is None:
        _fail("no compatible IWAD found; pass --iwad or set MALBOLGE_DOOM_IWAD")
    return candidate


def _debug_directory(source: Path) -> Path:
    directory = source.parent / ".debug"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _build_sanitized(source: Path, output: Path) -> None:
    command = (
        str(ZIG),
        "cc",
        "-std=c23",
        "-O1",
        "-g",
        "-fno-omit-frame-pointer",
        "-fsanitize=address,undefined",
        "-Dmain=DoomGuestMain",
        str(source),
        str(ADAPTER),
        "-o",
        str(output),
        *WINDOWS_LIBRARIES,
    )
    _run_checked(command)


def _guest_arguments(
    iwad: Path,
    forwarded: Sequence[str],
) -> tuple[str, ...]:
    arguments = tuple(forwarded)
    if arguments and arguments[0] == ARGUMENT_SEPARATOR:
        arguments = arguments[1:]
    if IWAD_ARGUMENT in arguments:
        return arguments
    return (IWAD_ARGUMENT, str(iwad), *arguments)


def _debug_environment(source: Path, iwad: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update({
        "ASAN_OPTIONS": (
            "abort_on_error=1:halt_on_error=1:symbolize=1:detect_leaks=0"
        ),
        "UBSAN_OPTIONS": "print_stacktrace=1:halt_on_error=1",
        "MALBOLGE_DOOM_EXECUTION_SOURCE": source.name,
        "MALBOLGE_DOOM_FALLBACK_IWAD": str(iwad),
    })
    return environment


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _run_direct(configuration: LaunchConfiguration) -> int:
    log_directory = configuration.executable.parent / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / f"doom-sanitize-{_timestamp()}.log"
    _write_standard_output(f"sanitizer log: {log_path}\n")
    with log_path.open("wb") as log_file:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            (str(configuration.executable), *configuration.arguments),
            cwd=configuration.source.parent,
            env=configuration.environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
            shell=False,
        )
    if log_path.stat().st_size:
        _write_standard_output(
            log_path.read_text(encoding="utf-8", errors="replace")
        )
    return completed.returncode


def _run_lldb(configuration: LaunchConfiguration) -> int:
    command = (
        str(LLDB),
        "-o",
        "run",
        ARGUMENT_SEPARATOR,
        str(configuration.executable),
        *configuration.arguments,
    )
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=configuration.source.parent,
        env=configuration.environment,
        check=False,
        shell=False,
    )
    return completed.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate doom.c with standalone Clang, build an ASan/UBSan "
            "Windows executable, and run it directly or under LLDB."
        )
    )
    _ = parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE,
        help="amalgamated DOOM C file",
    )
    _ = parser.add_argument("--iwad", type=Path, help="external IWAD path")
    _ = parser.add_argument(
        "--build-only",
        action="store_true",
        help="validate and build without launching",
    )
    _ = parser.add_argument(
        "--lldb",
        action="store_true",
        help="launch under LLDB and stop at a crash",
    )
    _ = parser.add_argument(
        "forwarded",
        nargs=argparse.REMAINDER,
        help="DOOM arguments after --",
    )
    return parser


def _parse_arguments(argv: Sequence[str] | None) -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(argv, namespace=arguments)
    return arguments


def _validate_tools(*, needs_lldb: bool) -> None:
    _ = _existing_file(ADAPTER, "Windows debug adapter")
    _ = _existing_file(CLANG, "Clang")
    _ = _existing_file(ZIG, "Zig")
    if needs_lldb:
        _ = _existing_file(LLDB, "LLDB")


def _validate_with_clang(source: Path) -> None:
    for command in _clang_validation_commands(source):
        _run_checked(command)
    _write_standard_output("standalone Clang validation: PASS\n")


def _launch_configuration(
    source: Path,
    executable: Path,
    iwad: Path,
    *,
    forwarded: Sequence[str],
) -> LaunchConfiguration:
    return LaunchConfiguration(
        arguments=_guest_arguments(iwad, forwarded),
        environment=_debug_environment(source, iwad),
        executable=executable,
        source=source,
    )


def _launch(options: _Arguments, source: Path, executable: Path) -> int:
    iwad = _discover_iwad(source.parent, options.iwad)
    configuration = _launch_configuration(
        source,
        executable,
        iwad,
        forwarded=options.forwarded,
    )
    if options.lldb:
        return _run_lldb(configuration)
    return _run_direct(configuration)


def main(argv: Sequence[str] | None = None) -> int:
    """Validate, build, and optionally launch the local DOOM debug artifact.

    Returns:
        The sanitizer or debugger process exit status, or zero for build-only.

    """
    if os.name != WINDOWS_OS_NAME:
        _fail("the current DOOM debug adapter supports Windows only")

    options = _parse_arguments(argv)
    source = _existing_file(options.source, "DOOM source")
    _validate_tools(needs_lldb=options.lldb)
    _validate_with_clang(source)

    executable = _debug_directory(source) / "doom-sanitize.exe"
    _build_sanitized(source, executable)
    _write_standard_output(f"sanitizer executable: {executable}\n")
    if options.build_only:
        return 0
    return _launch(options, source, executable)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DoomDebugError as error:
        _ = sys.stderr.write(f"doom debug error: {error}\n")
        raise SystemExit(CONFIGURATION_ERROR) from error
