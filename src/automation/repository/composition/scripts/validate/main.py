# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
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
#   - Validate explicitly selected C files against the Malbolge guest profile.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate explicitly selected C files against the Malbolge guest profile."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed executable argv, never a shell command.
import sys
from typing import Never

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_abi
from scripts.validate import c_abi_source
from scripts.validate import c_libc
from scripts.validate import c_libc_source
from scripts.validate import tidy_toolchain

ROOT = repository_root(Path(__file__))
DEFAULT_PROFILE = (
    ROOT / "src/tooling/native-analysis/contract" / "malbolge-clang-tidy.yaml"
)
PINNED_LLVM = ROOT / ".dependencies" / "llvm" / tidy_toolchain.LLVM_VERSION
PINNED_CLANG_RESOURCE = PINNED_LLVM / "lib" / "clang" / "22"


def _native_toolchain_identity() -> tidy_toolchain.ToolchainIdentity | None:
    try:
        return tidy_toolchain.load_identity(
            platform_id=tidy_toolchain.host_platform_id()
        )
    except tidy_toolchain.ToolchainError:
        return None


_NATIVE_TOOLCHAIN = _native_toolchain_identity()
PLUGIN_HOST = (
    _NATIVE_TOOLCHAIN.plugin_host
    if _NATIVE_TOOLCHAIN is not None
    else PINNED_LLVM / "jig-bin" / "clang-tidy.bin"
)
PLUGIN_LIBRARY = (
    _NATIVE_TOOLCHAIN.plugin_library
    if _NATIVE_TOOLCHAIN is not None
    else ROOT / ".dependencies/tools-tidy/22.1.8/bin/malbolge-tidy.so"
)
PINNED_CLANG_TIDY = (
    _NATIVE_TOOLCHAIN.clang_tidy
    if _NATIVE_TOOLCHAIN is not None
    else PINNED_LLVM / "jig-bin" / "clang-tidy.bin"
)
PLUGIN_CHECKS = tidy_toolchain.PLUGIN_CHECKS
DOOM_DIRECTORY = "doom"
C_SUFFIX = ".c"
PINNED_LLVM_VERSION = c_abi_source.PINNED_LLVM_VERSION
CONFIGURATION_ERROR = 2


class InputError(ValueError):
    """Invalid explicit guest-C validator input or local tool configuration."""


class _Arguments(argparse.Namespace):
    files: list[str]
    profile: Path
    clang_tidy: Path
    clang: Path
    plugin: Path | None

    def __init__(self) -> None:
        """Initialize typed defaults before argparse mutates this namespace."""
        super().__init__()
        self.files = []
        self.profile = DEFAULT_PROFILE
        self.clang_tidy = _default_clang_tidy()
        self.clang = c_abi_source.PINNED_CLANG
        self.plugin = None


@dataclass(frozen=True, slots=True)
class _Configuration:
    abi: c_abi.CAbiProjection
    clang: Path
    libc: c_libc.CLibcProjection
    clang_tidy: Path
    files: tuple[Path, ...]
    plugin: Path | None
    profile: Path


def _fail(message: str) -> Never:
    raise InputError(message)


def _default_clang_tidy() -> Path:
    if PLUGIN_HOST.is_file() and PLUGIN_LIBRARY.is_file():
        return PLUGIN_HOST
    return PINNED_CLANG_TIDY


def _default_plugin(clang_tidy: Path) -> Path | None:
    """Pair the canonical project host with its reviewed plugin by default.

    Returns:
        Canonical plugin path for the project host, otherwise ``None``.

    """
    try:
        canonical_host = PLUGIN_HOST.resolve()
        selected_host = clang_tidy.resolve()
    except OSError:
        return None
    if selected_host != canonical_host or not PLUGIN_LIBRARY.is_file():
        return None
    return PLUGIN_LIBRARY.resolve()


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
        "--clang",
        type=Path,
        default=c_abi_source.PINNED_CLANG,
        help=(
            "Clang executable for ABI AST preflight "
            "(default: pinned LLVM 22.1.8)"
        ),
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


def _tool_version_output(path: Path, label: str) -> str:
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(path), "--version"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute {label} version query {path}: {error}")
    if completed.returncode != 0:
        _fail(f"{label} version query failed: {path}")
    return completed.stdout + chr(10) + completed.stderr


def _require_llvm_version(path: Path, label: str) -> None:
    expected = f"version {PINNED_LLVM_VERSION}"
    if expected not in _tool_version_output(path, label):
        _fail(f"{label} must report LLVM {PINNED_LLVM_VERSION}: {path}")


def _require_plugin_registration(clang_tidy: Path, plugin: Path) -> None:
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [
                str(clang_tidy),
                f"--load={plugin}",
                "--checks=-*,malbolge-*",
                "--list-checks",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to probe clang-tidy plugin registration: {error}")
    observed = tuple(
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().startswith("malbolge-")
    )
    if completed.returncode != 0 or set(observed) != set(PLUGIN_CHECKS):
        expected = ", ".join(sorted(PLUGIN_CHECKS))
        actual = ", ".join(sorted(observed)) if observed else "none"
        prefix = "clang-tidy plugin registration mismatch: expected "
        _fail(f"{prefix}{expected}; observed {actual}")


def _configuration(arguments: _Arguments) -> _Configuration:
    clang_tidy = arguments.clang_tidy.resolve()
    clang = arguments.clang.resolve()
    profile = arguments.profile.resolve()
    plugin = (
        arguments.plugin.resolve()
        if arguments.plugin is not None
        else _default_plugin(clang_tidy)
    )
    _require_file(clang_tidy, "clang-tidy")
    _require_file(clang, "Clang")
    _require_llvm_version(clang_tidy, "clang-tidy")
    _require_llvm_version(clang, "Clang")
    _require_file(profile, "Malbolge guest profile")
    if plugin is not None:
        _require_file(plugin, "clang-tidy plugin")
        _require_plugin_registration(clang_tidy, plugin)
    try:
        abi = c_abi.canonical_projection()
        libc = c_libc.canonical_projection()
    except ValueError as error:
        _fail(f"invalid canonical guest-C contract: {error}")
    return _Configuration(
        abi=abi,
        clang=clang,
        libc=libc,
        clang_tidy=clang_tidy,
        files=_validated_files(arguments.files),
        plugin=plugin,
        profile=profile,
    )


def _run(command: list[str]) -> int:
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - no shell; argv is explicit.
            command,
            cwd=ROOT,
            check=False,
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute validation tool {command[0]}: {error}")
    return completed.returncode


def _plugin_arguments(configuration: _Configuration) -> list[str]:
    if configuration.plugin is None:
        return []
    checks = ",".join(PLUGIN_CHECKS)
    return [
        f"--load={configuration.plugin}",
        f"--checks={checks}",
        f"--warnings-as-errors={checks}",
    ]


def _verify_profile(configuration: _Configuration) -> bool:
    command = [
        str(configuration.clang_tidy),
        *_plugin_arguments(configuration),
        "--verify-config",
        f"--config-file={configuration.profile}",
    ]
    return _run(command) == 0


def _source_command(
    configuration: _Configuration,
    source: Path,
) -> list[str]:
    return [
        str(configuration.clang_tidy),
        f"--config-file={configuration.profile}",
        *_plugin_arguments(configuration),
        str(source),
        "--",
        f"-resource-dir={PINNED_CLANG_RESOURCE}",
        f"-I{configuration.libc.include_root}",
        "-x",
        "c",
        f"--target={configuration.abi.clang_target}",
    ]


def _preflight_source(
    configuration: _Configuration,
    source: Path,
) -> bool:
    abi_clean = c_abi_source.validate_source(
        source,
        clang=configuration.clang,
        projection=configuration.abi,
    )
    return abi_clean and c_libc_source.validate_source(
        source,
        clang=configuration.clang,
        abi=configuration.abi,
        libc=configuration.libc,
    )


def _validate_source(
    configuration: _Configuration,
    source: Path,
) -> int:
    result = 0
    try:
        clean = _preflight_source(configuration, source)
        result = _run(_source_command(configuration, source)) if clean else 1
    except (
        c_abi_source.SourceAnalysisError,
        c_libc_source.LibcSourceError,
    ) as error:
        _write_error(error)
        result = CONFIGURATION_ERROR
    return result


def _validate_sources(configuration: _Configuration) -> int:
    status = 0
    for source in configuration.files:
        result = _validate_source(configuration, source)
        if result == CONFIGURATION_ERROR:
            return result
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
        if not _verify_profile(configuration):
            _write_error("Malbolge clang-tidy profile failed self-verification")
            return CONFIGURATION_ERROR
        return _validate_sources(configuration)
    except InputError as error:
        _write_error(error)
        return CONFIGURATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
