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
#   - Tracked POSIX execution of frozen x86-64 direct-template native text.
# - Must-Not:
#   - Call unsafe Rust, execute unfrozen native bytes, or claim production load.
# - Allows:
#   - Inputs: tracked COFF fixture, C harness, and pinned repository Clang.
#   - Outputs: one passing or failing pytest result.
#   - Side effects: generated fixture include and executable under pytest temp.
# - Split-When:
#   - Another ISA or host execution policy needs an independent native harness.
# - Merge-When:
#   - A tracked production adapter owns this exact execution evidence.
# - Summary:
#   - Proves W^X plus Windows-x64 ABI execution of frozen direct-template text.
# - Description:
#   - Extracts .text directly from COFF and compiles POSIX ms_abi C harnesses.
# - Usage:
#   - Collected by the repository Python test suite on Linux x86-64.
# - Defaults:
#   - Skips on hosts that cannot execute x86-64 POSIX native code.
#

"""Execute frozen Windows-x64 direct text through POSIX W^X harnesses."""

from __future__ import annotations

from pathlib import Path
import platform
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
NATIVE_INCLUDE = ROOT / "src/runtime/tiered-execution/adapter-outbound/native"
INITIAL_HALT_FIXTURE = (
    ROOT / "tests/execution/fixtures/native-initial-halt-x86_64-coff.hex"
)
INITIAL_HALT_HARNESS = ROOT / "tests/execution/native_initial_halt_posix.c"
INITIAL_HALT_INCLUDE = "native_initial_halt_text.inc"
INITIAL_HALT_TEXT_SIZE = 56
NO_OPERATION_FIXTURE = (
    ROOT / "tests/execution/fixtures/native-no-operation-x86_64-coff.hex"
)
NO_OPERATION_HARNESS = ROOT / "tests/execution/native_no_operation_posix.c"
NO_OPERATION_INCLUDE = "native_no_operation_text.inc"
NO_OPERATION_TEXT_SIZE = 147
TEXT_SECTION = b".text"
COFF_SECTION_HEADER_SIZE = 40
X86_64_COFF_MACHINE = 0x8664
X86_64_HOST_NAMES = frozenset({"amd64", "x86_64"})
STRICT_WARNINGS = (
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
)


def read_u16(data: bytes, offset: int) -> int:
    """Decode one little-endian COFF u16 field.

    Returns:
        The decoded unsigned integer.

    """
    return int.from_bytes(data[offset : offset + 2], "little")


def read_u32(data: bytes, offset: int) -> int:
    """Decode one little-endian COFF u32 field.

    Returns:
        The decoded unsigned integer.

    """
    return int.from_bytes(data[offset : offset + 4], "little")


def assert_entry_symbol(object_bytes: bytes) -> None:
    """Require the fixture entry symbol to begin at the first section byte."""
    symbol_table = read_u32(object_bytes, 8)
    assert read_u32(object_bytes, 12) == 1
    assert read_u32(object_bytes, symbol_table + 8) == 0
    assert read_u16(object_bytes, symbol_table + 12) == 1


def text_section(object_bytes: bytes) -> bytes:
    """Extract relocation-free text from the tracked COFF object.

    Returns:
        The exact raw text-section bytes.

    """
    section_count = read_u16(object_bytes, 2)
    optional_size = read_u16(object_bytes, 16)
    section_table = 20 + optional_size
    text_offsets = tuple(
        section_table + index * COFF_SECTION_HEADER_SIZE
        for index in range(section_count)
        if object_bytes[
            section_table
            + index * COFF_SECTION_HEADER_SIZE : section_table
            + index * COFF_SECTION_HEADER_SIZE
            + 8
        ].rstrip(b"\0")
        == TEXT_SECTION
    )
    assert len(text_offsets) == 1
    offset = text_offsets[0]
    raw_size = read_u32(object_bytes, offset + 16)
    raw_offset = read_u32(object_bytes, offset + 20)
    assert read_u16(object_bytes, offset + 32) == 0
    return object_bytes[raw_offset : raw_offset + raw_size]


def fixture_text(fixture: Path, expected_size: int) -> bytes:
    """Return exact entry text from one tracked x86-64 COFF fixture.

    Returns:
        Relocation-free bytes beginning at the tracked entry symbol.

    """
    encoded = fixture.read_text(encoding="utf-8")
    object_bytes = bytes.fromhex("".join(encoded.split()))
    assert read_u16(object_bytes, 0) == X86_64_COFF_MACHINE
    assert_entry_symbol(object_bytes)
    text = text_section(object_bytes)
    assert len(text) == expected_size
    return text


def write_text_include(path: Path, text: bytes) -> None:
    """Write fixture text as a temporary C initializer include."""
    lines: list[str] = []
    for offset in range(0, len(text), 8):
        chunk = text[offset : offset + 8]
        initializer = ", ".join(f"0x{byte:02x}" for byte in chunk)
        lines.append(f"    {initializer},")
    _ = path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(
    command: tuple[str, ...],
    cwd: Path,
) -> sp.CompletedProcess[str]:
    """Run one fixed compiler or harness command without a shell.

    Returns:
        The completed process with captured diagnostics.

    """
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=30,
    )


@pytest.mark.skipif(
    not sys.platform.startswith("linux")
    or platform.machine().lower() not in X86_64_HOST_NAMES,
    reason="tracked W^X execution harness requires Linux x86-64",
)
def test_direct_initial_halt_posix_execution(tmp_path: Path) -> None:
    """Execute fixture text under W^X and the exact Windows-x64 call ABI."""
    assert CLANG.is_file(), f"pinned Clang missing: {CLANG}"
    write_text_include(
        tmp_path / INITIAL_HALT_INCLUDE,
        fixture_text(INITIAL_HALT_FIXTURE, INITIAL_HALT_TEXT_SIZE),
    )
    executable = tmp_path / "native-initial-halt-posix"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            *STRICT_WARNINGS,
            f"-I{tmp_path}",
            f"-I{NATIVE_INCLUDE}",
            str(INITIAL_HALT_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    not sys.platform.startswith("linux")
    or platform.machine().lower() not in X86_64_HOST_NAMES,
    reason="tracked W^X execution harness requires Linux x86-64",
)
def test_direct_no_operation_posix_execution(tmp_path: Path) -> None:
    """Execute memory-writing no-op text with exact hit and atomic misses."""
    assert CLANG.is_file(), f"pinned Clang missing: {CLANG}"
    write_text_include(
        tmp_path / NO_OPERATION_INCLUDE,
        fixture_text(NO_OPERATION_FIXTURE, NO_OPERATION_TEXT_SIZE),
    )
    executable = tmp_path / "native-no-operation-posix"
    compiled = run_command(
        (
            str(CLANG),
            "-std=c23",
            *STRICT_WARNINGS,
            f"-I{tmp_path}",
            f"-I{NATIVE_INCLUDE}",
            str(NO_OPERATION_HARNESS),
            "-o",
            str(executable),
        ),
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = run_command((str(executable),), tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
