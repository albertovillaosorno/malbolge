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
#   - The deterministic pre-lowering guest-C validation entrypoint.
# - Must-Not:
#   - Claim complete C-to-Malbolge lowerability before the compiler contract
#     does.
#   - Infer guest semantics from host headers, host ABI, or ambient toolchains.
# - Allows:
#   - Inputs: explicit C translation units and the sole recursive doom
#     convenience.
#   - Outputs: pinned-Clang diagnostics plus canonical ABI/libc/tidy
#     diagnostics.
#   - Side effects: repository-pinned Clang and validator subprocess execution.
# - Split-When:
#   - A validation family gains an independently versioned semantic authority.
# - Merge-When:
#   - The complete tools/tidy lowerability contract subsumes this orchestration.
# - Summary:
#   - Reject C already known to be unsafe or nonportable before lowering.
# - Description:
#   - Closes the include universe, enables deterministic/UB diagnostics, then
#     delegates ABI, libc, and clang-tidy policy to the existing validator.
# - Usage:
#   - python -m scripts.validate.validate_c_before_malbolge file.c [...]
# - Defaults:
#   - Invalid inputs, wrong Clang identity, or any hard diagnostic fail closed.
#

"""Validate C for deterministic Malbolge guest compilation before lowering."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Never

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_abi
from scripts.validate import c_abi_source
from scripts.validate import c_libc
from scripts.validate import main as guest_validator

ROOT = repository_root(Path(__file__))
PINNED_CLANG = c_abi_source.PINNED_CLANG
PINNED_LLVM_VERSION = c_abi_source.PINNED_LLVM_VERSION
CLANG_RESOURCE_INCLUDE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22/include"
GUEST_LIBC_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
MANUAL_VALIDATOR = Path(guest_validator.__file__).resolve()
C_SUFFIX = ".c"
DOOM_DIRECTORY = "doom"
CONFIGURATION_ERROR = 2

# These diagnostics correspond to deterministic C semantics or source behavior,
# not style. Do not grow this list merely because a warning is convenient.
HARD_WARNING_FLAGS = (
    "-Werror=implicit-function-declaration",
    "-Werror=incompatible-pointer-types",
    "-Werror=int-conversion",
    "-Werror=return-type",
    "-Werror=uninitialized",
    "-Werror=unsequenced",
    "-Werror=shift-count-negative",
    "-Werror=shift-count-overflow",
    "-Werror=division-by-zero",
    "-Werror=date-time",
    "-Werror=null-dereference",
    "-Werror=array-bounds",
    "-Werror=return-stack-address",
)


class ValidationInputError(ValueError):
    """Invalid explicit pre-Malbolge input or tool configuration."""


class _Arguments(argparse.Namespace):
    inputs: list[str]
    preflight_only: bool

    def __init__(self) -> None:
        """Initialize typed defaults before argparse mutates the namespace."""
        super().__init__()
        self.inputs = []
        self.preflight_only = False


def _fail(message: str) -> Never:
    raise ValidationInputError(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reject guest C that is already known to violate deterministic "
            "pre-lowering Malbolge requirements, then run the canonical "
            "ABI/libc/tools-tidy validator."
        )
    )
    _ = parser.add_argument(
        "inputs",
        nargs="+",
        metavar="INPUT",
        help=(
            "explicit .c translation units; recursive directory validation is "
            "reserved for an explicitly named doom directory"
        ),
    )
    _ = parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="run deterministic pinned-Clang preflight without tools/tidy",
    )
    return parser


def _parse_arguments() -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(namespace=arguments)
    return arguments


def _expand_directory(path: Path) -> tuple[Path, ...]:
    if path.name.casefold() != DOOM_DIRECTORY:
        _fail(f"only an explicitly named doom directory is recursive: {path}")
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


def _expand_file(path: Path) -> tuple[Path, ...]:
    if not path.is_file():
        _fail(f"input is not a regular file: {path}")
    if path.suffix.casefold() != C_SUFFIX:
        _fail(f"guest validation accepts C translation units only: {path}")
    return (path.resolve(),)


def _expand_input(raw: str) -> tuple[Path, ...]:
    path = Path(raw)
    if not path.exists():
        _fail(f"input does not exist: {path}")
    return _expand_directory(path) if path.is_dir() else _expand_file(path)


def _validated_files(raw_inputs: list[str]) -> tuple[Path, ...]:
    expanded = (
        source for raw in raw_inputs for source in _expand_input(raw)
    )
    files = tuple(dict.fromkeys(expanded))
    if not files:
        _fail("no C translation units were selected")
    return files


def _tool_output(command: list[str]) -> sp.CompletedProcess[str]:
    try:
        return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute {command[0]}: {error}")


def _require_directory(path: Path, label: str) -> None:
    if not path.is_dir():
        _fail(f"{label} is unavailable: {path}")


def _require_pinned_clang() -> None:
    if not PINNED_CLANG.is_file():
        _fail(f"repository-pinned Clang is unavailable: {PINNED_CLANG}")
    version = _tool_output([str(PINNED_CLANG), "--version"])
    expected = f"clang version {PINNED_LLVM_VERSION}"
    observed = version.stdout + version.stderr
    if version.returncode != 0 or expected not in observed:
        _fail(f"Clang must report {expected}: {PINNED_CLANG}")


def _canonical_abi() -> c_abi.CAbiProjection:
    try:
        abi = c_abi.canonical_projection()
        _ = c_libc.canonical_projection()
    except ValueError as error:
        _fail(f"invalid canonical guest-C contract: {error}")
    return abi


def _require_canonical_inputs() -> c_abi.CAbiProjection:
    _require_pinned_clang()
    _require_directory(CLANG_RESOURCE_INCLUDE, "pinned Clang resource headers")
    _require_directory(GUEST_LIBC_INCLUDE, "guest libc include root")
    return _canonical_abi()


def strict_clang_command(source: Path, abi: c_abi.CAbiProjection) -> list[str]:
    """Build the deterministic pre-lowering Clang command for one source.

    Returns:
        Explicit argv using only repository-owned guest/compiler headers.

    """
    return [
        str(PINNED_CLANG),
        f"--target={abi.clang_target}",
        "-x",
        "c",
        "-std=c23",
        "-ffreestanding",
        "-fno-builtin",
        "-pedantic-errors",
        "-nostdinc",
        "-isystem",
        str(CLANG_RESOURCE_INCLUDE),
        "-I",
        str(GUEST_LIBC_INCLUDE),
        *HARD_WARNING_FLAGS,
        "-fsyntax-only",
        str(source),
    ]


def _write_tool_output(completed: sp.CompletedProcess[str]) -> None:
    if completed.stdout:
        _ = sys.stdout.write(completed.stdout)
    if completed.stderr:
        _ = sys.stderr.write(completed.stderr)


def _strict_preflight(
    sources: tuple[Path, ...],
    abi: c_abi.CAbiProjection,
) -> int:
    status = 0
    for source in sources:
        completed = _tool_output(strict_clang_command(source, abi))
        if completed.returncode != 0:
            message = " ".join((
                f"{source}: error:",
                "MALBOLGE-PRE-001",
                "deterministic pre-lowering Clang validation failed\n",
            ))
            _ = sys.stderr.write(message)
            _write_tool_output(completed)
            status = 1
    return status


def _canonical_validator(sources: tuple[Path, ...]) -> int:
    command = [
        sys.executable,
        str(MANUAL_VALIDATOR),
        *(str(item) for item in sources),
    ]
    completed = _tool_output(command)
    _write_tool_output(completed)
    return completed.returncode


def _success_message(label: str, count: int) -> None:
    _ = sys.stdout.write(
        f"{label}: {count} translation unit(s)\n"
    )


def _run_validation(arguments: _Arguments) -> int:
    sources = _validated_files(arguments.inputs)
    abi = _require_canonical_inputs()
    status = _strict_preflight(sources, abi)
    if status == 0 and arguments.preflight_only:
        _success_message("pre-Malbolge Clang preflight clean", len(sources))
    elif status == 0:
        status = _canonical_validator(sources)
        if status == 0:
            _success_message(
                "pre-Malbolge guest-C validation clean",
                len(sources),
            )
    return status


def main() -> int:
    """Run deterministic preflight and canonical guest-C validation.

    Returns:
        Zero only when every selected translation unit passes all requested
        validation phases.

    """
    try:
        arguments = _parse_arguments()
        status = _run_validation(arguments)
    except ValidationInputError as error:
        _ = sys.stderr.write(f"error: {error}\n")
        status = CONFIGURATION_ERROR
    return status


if __name__ == "__main__":
    raise SystemExit(main())
