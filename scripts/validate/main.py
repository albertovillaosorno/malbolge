# File:
#   - main.py
# Path:
#   - scripts/validate/main.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Validate explicitly selected C files against the Malbolge guest profile.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Validate explicitly selected C files against the Malbolge guest profile."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed executable argv, never a shell command.
import sys
from typing import Never

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "tools" / "tidy" / "malbolge-clang-tidy.yaml"
PINNED_LLVM = ROOT / ".dependencies" / "llvm" / "22.1.8" / "bin"
DOOM_DIRECTORY = "doom"
C_SUFFIX = ".c"
CONFIGURATION_ERROR = 2


class InputError(ValueError):
    """Invalid explicit guest-C validator input or local tool configuration."""


class _Arguments(argparse.Namespace):
    files: list[str]
    profile: Path
    clang_tidy: Path
    plugin: Path | None

    def __init__(self) -> None:
        """Initialize typed defaults before argparse mutates this namespace."""
        super().__init__()
        self.files = []
        self.profile = DEFAULT_PROFILE
        self.clang_tidy = _default_clang_tidy()
        self.plugin = None


@dataclass(frozen=True, slots=True)
class _Configuration:
    clang_tidy: Path
    files: tuple[Path, ...]
    plugin: Path | None
    profile: Path


def _fail(message: str) -> Never:
    raise InputError(message)


def _default_clang_tidy() -> Path:
    for name in ("clang-tidy.exe", "clang-tidy"):
        candidate = PINNED_LLVM / name
        if candidate.is_file():
            return candidate
    return PINNED_LLVM / "clang-tidy"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate only named C translation units against the Malbolge "
            "guest-C compatibility profile."
        )
    )
    _ = parser.add_argument(
        "files",
        nargs="+",
        metavar="INPUT",
        help=(
            "explicit .c units; a directory is accepted only when its "
            "basename is doom"
        ),
    )
    _ = parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="clang-tidy profile (default: tools/tidy profile)",
    )
    _ = parser.add_argument(
        "--clang-tidy",
        type=Path,
        default=_default_clang_tidy(),
        help="clang-tidy executable (default: pinned LLVM 22.1.8)",
    )
    _ = parser.add_argument(
        "--plugin",
        type=Path,
        help="optional built tools/tidy clang-tidy plugin to load",
    )
    return parser


def _parse_arguments() -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(namespace=arguments)
    return arguments


def _doom_files(path: Path) -> tuple[Path, ...]:
    files = tuple(
        sorted(
            candidate.resolve()
            for candidate in path.rglob("*")
            if candidate.is_file() and candidate.suffix.casefold() == C_SUFFIX
        )
    )
    if not files:
        _fail(f"doom directory contains no C translation units: {path}")
    return files


def _expand_directory(path: Path) -> tuple[Path, ...]:
    if path.name.casefold() != DOOM_DIRECTORY:
        _fail(f"only an explicitly named doom directory is accepted: {path}")
    return _doom_files(path)


def _expand_file(path: Path) -> tuple[Path, ...]:
    if not path.is_file():
        _fail(f"input is not a regular file: {path}")
    if path.suffix.casefold() != C_SUFFIX:
        _fail(f"guest validation accepts C translation units only: {path}")
    return (path.resolve(),)


def _expand_input(path: Path) -> tuple[Path, ...]:
    if not path.exists():
        _fail(f"input does not exist: {path}")
    if path.is_dir():
        return _expand_directory(path)
    return _expand_file(path)


def _validated_files(raw_files: list[str]) -> tuple[Path, ...]:
    expanded = (
        candidate for raw in raw_files for candidate in _expand_input(Path(raw))
    )
    return tuple(dict.fromkeys(expanded))


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        _fail(f"{label} not found: {path}")


def _configuration(arguments: _Arguments) -> _Configuration:
    clang_tidy = arguments.clang_tidy.resolve()
    profile = arguments.profile.resolve()
    plugin = (
        arguments.plugin.resolve() if arguments.plugin is not None else None
    )
    _require_file(clang_tidy, "clang-tidy")
    _require_file(profile, "Malbolge guest profile")
    if plugin is not None:
        _require_file(plugin, "clang-tidy plugin")
    return _Configuration(
        clang_tidy=clang_tidy,
        files=_validated_files(arguments.files),
        plugin=plugin,
        profile=profile,
    )


def _run(command: list[str]) -> int:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - no shell; argv is explicit.
        command,
        cwd=ROOT,
        check=False,
        shell=False,
    )
    return completed.returncode


def _verify_profile(configuration: _Configuration) -> bool:
    command = [
        str(configuration.clang_tidy),
        "--verify-config",
        f"--config-file={configuration.profile}",
    ]
    return _run(command) == 0


def _source_command(
    configuration: _Configuration,
    source: Path,
) -> list[str]:
    plugin = (
        []
        if configuration.plugin is None
        else [f"--load={configuration.plugin}"]
    )
    return [
        str(configuration.clang_tidy),
        f"--config-file={configuration.profile}",
        *plugin,
        str(source),
        "--",
        "-x",
        "c",
    ]


def _validate_sources(configuration: _Configuration) -> int:
    status = 0
    for source in configuration.files:
        result = _run(_source_command(configuration, source))
        if result != 0:
            status = result
    return status


def _write_error(error: object) -> None:
    _ = sys.stderr.write(f"error: {error}\n")


def main() -> int:
    """Validate explicitly selected guest C and return the tool exit status.

    Returns:
        Zero when every selected unit passes, otherwise a nonzero status.

    """
    try:
        configuration = _configuration(_parse_arguments())
    except InputError as error:
        _write_error(error)
        return CONFIGURATION_ERROR
    if not _verify_profile(configuration):
        _write_error("Malbolge clang-tidy profile failed self-verification")
        return CONFIGURATION_ERROR
    return _validate_sources(configuration)


if __name__ == "__main__":
    raise SystemExit(main())
