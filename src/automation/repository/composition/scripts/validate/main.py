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

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed executable argv, never a shell command.
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Never, cast, override

if TYPE_CHECKING:
    from typing import TextIO

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_abi, c_abi_source, c_libc, c_libc_source, tidy_toolchain

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


def _safe_error_detail(error: object) -> str:
    """Describe native errors without invoking arbitrary formatter hooks.

    Returns:
        Trusted built-in diagnostics, or the foreign object's type name.

    """
    if type(error) in (
        str,
        InputError,
        c_abi.CAbiValidationError,
        c_libc.CLibcValidationError,
        c_abi_source.SourceAnalysisError,
        c_libc_source.LibcSourceError,
        OSError,
        FileNotFoundError,
        PermissionError,
        FileExistsError,
        IsADirectoryError,
        NotADirectoryError,
        TimeoutError,
        TypeError,
        ValueError,
        RuntimeError,
    ):
        return str(error)
    return type(error).__name__


def _checked_process_receipt[OutputT: (str, bytes)](
    completed: subprocess.CompletedProcess[OutputT],
    arguments: list[str],
    *,
    context: str,
    capture_output: bool,
) -> subprocess.CompletedProcess[OutputT]:
    """Admit a native subprocess result matching its invoked tool and I/O mode.

    Returns:
        The typed, exact command receipt after all checks pass.

    """
    if (
        type(completed) is not subprocess.CompletedProcess
        or type(completed.returncode) is not int
        or type(completed.args) is not list
        or len(completed.args) != len(arguments)
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != arguments
        or (
            capture_output
            and (type(completed.stdout) is not str or type(completed.stderr) is not str)
        )
        or (
            not capture_output
            and (completed.stdout is not None or completed.stderr is not None)
        )
    ):
        _fail(f"invalid {context} process receipt")
    return completed


def _default_clang_tidy() -> Path:
    if _native_path_status(PLUGIN_HOST.is_file(), "plugin host file") and (
        _native_path_status(PLUGIN_LIBRARY.is_file(), "plugin library file")
    ):
        return PLUGIN_HOST
    return PINNED_CLANG_TIDY


def _default_plugin(clang_tidy: Path) -> Path | None:
    """Pair the canonical project host with its reviewed plugin by default.

    Returns:
        Canonical plugin path for the project host, otherwise ``None``.

    """
    try:
        canonical_host = _native_resolved_path(
            PLUGIN_HOST, context="canonical plugin host"
        )
        selected_host = _native_resolved_path(clang_tidy, context="clang-tidy host")
    except OSError:
        return None
    if selected_host != canonical_host or not _native_path_status(
        PLUGIN_LIBRARY.is_file(), "default plugin library file"
    ):
        return None
    return _native_resolved_path(PLUGIN_LIBRARY, context="plugin library")


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Accept only a complete native write and successful output flush.

    Returns:
        Whether the entire text record was delivered.

    """
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


class _ManualArgumentParser(argparse.ArgumentParser):
    """Authenticate argparse output before allowing successful help exits."""

    @override
    def _print_message(self, message: str, file: object = None) -> None:
        if not message:
            return
        stream = sys.stderr if file is None else file
        if not _write_cli_record(cast("TextIO", stream), message):
            _fail("guest-C argument output write or flush failed")


def _parser() -> argparse.ArgumentParser:
    parser = _ManualArgumentParser(
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
            "explicit .c units; a directory is accepted only when its basename is doom"
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
        help=("Clang executable for ABI AST preflight (default: pinned LLVM 22.1.8)"),
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


def _native_path_status(value: object, context: str) -> bool:
    """Return an admitted native filesystem boolean, never foreign truthiness.

    Returns:
        The validated boolean status value.

    """
    if type(value) is not bool:
        _fail(f"invalid {context} status receipt")
    return cast("bool", value)


def _native_resolved_path(path: Path, *, context: str = "C source") -> Path:
    """Preserve native path flavor before using any resolved validation file.

    Returns:
        A native resolved file path.

    """
    resolved = path.resolve()
    if type(resolved) is not type(path):
        _fail(f"invalid {context} resolved-path receipt")
    return resolved


def _reject_recursive_redirect(path: Path, context: str) -> None:
    if _native_path_status(path.is_symlink(), f"{context} redirect"):
        _fail(f"{context} must not redirect: {path}")
    if _native_path_status(path.is_junction(), f"{context} redirect"):
        _fail(f"{context} must not redirect: {path}")


def _doom_files(path: Path) -> tuple[Path, ...]:
    sources: list[Path] = []
    for candidate in path.rglob("*"):
        if type(candidate) is not type(path):
            _fail("invalid recursive doom entry path receipt")
        _reject_recursive_redirect(candidate, "recursive doom entry")
        if (
            _native_path_status(candidate.is_file(), "recursive C source")
            and candidate.suffix.casefold() == C_SUFFIX
        ):
            sources.append(_native_resolved_path(candidate))
    files = tuple(sorted(sources))
    if not files:
        _fail(f"doom directory contains no C translation units: {path}")
    return files


def _expand_directory(path: Path) -> tuple[Path, ...]:
    if path.name.casefold() != DOOM_DIRECTORY:
        _fail(f"only an explicitly named doom directory is accepted: {path}")
    _reject_recursive_redirect(path, "recursive doom directory")
    return _doom_files(path)


def _expand_file(path: Path) -> tuple[Path, ...]:
    if not _native_path_status(path.is_file(), "C source file"):
        _fail(f"input is not a regular file: {path}")
    if path.suffix.casefold() != C_SUFFIX:
        _fail(f"guest validation accepts C translation units only: {path}")
    return (_native_resolved_path(path),)


def _expand_input(path: Path) -> tuple[Path, ...]:
    if not _native_path_status(path.exists(), "C input existence"):
        _fail(f"input does not exist: {path}")
    if _native_path_status(path.is_dir(), "C input directory"):
        return _expand_directory(path)
    return _expand_file(path)


def _validated_files(raw_files: list[str]) -> tuple[Path, ...]:
    expanded = (
        candidate for raw in raw_files for candidate in _expand_input(Path(raw))
    )
    return tuple(dict.fromkeys(expanded))


def _require_file(path: Path, label: str) -> None:
    if not _native_path_status(path.is_file(), f"{label} file"):
        _fail(f"{label} not found: {path}")


def _tool_version_output(path: Path, label: str) -> str:
    arguments = [str(path), "--version"]
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            arguments.copy(),
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=15,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as error:
        message = (
            f"failed to execute {label} version query {path}: "
            f"{_safe_error_detail(error)}"
        )
        raise InputError(message) from error
    completed = _checked_process_receipt(
        completed, arguments, context=f"{label} version", capture_output=True
    )
    if completed.returncode != 0:
        _fail(f"{label} version query failed: {path}")
    return completed.stdout + chr(10) + completed.stderr


def _require_llvm_version(path: Path, label: str) -> None:
    expected = f"version {PINNED_LLVM_VERSION}"
    if expected not in _tool_version_output(path, label):
        _fail(f"{label} must report LLVM {PINNED_LLVM_VERSION}: {path}")


def _require_plugin_registration(clang_tidy: Path, plugin: Path) -> None:
    arguments = [
        str(clang_tidy),
        f"--load={plugin}",
        "--checks=-*,malbolge-*",
        "--list-checks",
    ]
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            arguments.copy(),
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=15,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as error:
        message = (
            "failed to probe clang-tidy plugin registration: "
            f"{_safe_error_detail(error)}"
        )
        raise InputError(message) from error
    completed = _checked_process_receipt(
        completed, arguments, context="clang-tidy plugin", capture_output=True
    )
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
    clang_tidy = _native_resolved_path(arguments.clang_tidy, context="clang-tidy")
    clang = _native_resolved_path(arguments.clang, context="Clang")
    profile = _native_resolved_path(arguments.profile, context="guest profile")
    plugin = (
        _native_resolved_path(arguments.plugin, context="clang-tidy plugin")
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
        message = f"invalid canonical guest-C contract: {_safe_error_detail(error)}"
        raise InputError(message) from error
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
            command.copy(),
            cwd=ROOT,
            check=False,
            shell=False,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = (
            f"failed to execute validation tool {command[0]}: "
            f"{_safe_error_detail(error)}"
        )
        raise InputError(message) from error
    completed = _checked_process_receipt(
        completed, command, context="guest-C validation", capture_output=False
    )
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
    diagnostic = f"error: {_safe_error_detail(error)}\n"
    _ = _write_cli_record(sys.stderr, diagnostic)


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
