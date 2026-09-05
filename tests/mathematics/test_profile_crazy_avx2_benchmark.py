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
#   - Build, SIMD-codegen, and exact validation checks for the AVX2 CRAZY study.
# - Must-Not:
#   - Require AVX2 on every host or treat benchmark code as semantic authority.
# - Allows:
#   - Inputs: benchmark C source and repository-pinned Clang 22.1.8.
#   - Outputs: strict compile, AVX2 assembly, and complete corpus validation.
#   - Side effects: test-local compiler outputs only.
# - Split-When:
#   - Split when another SIMD ISA gains an independent benchmark source.
# - Merge-When:
#   - Merge when one test owns the same SIMD benchmark protocol and codegen.
# - Summary:
#   - Proves the N10-N14 AVX2 benchmark is real SIMD and exact on capable hosts.
# - Description:
#   - Requires gather/YMM codegen and all-output equality against scalar CRAZY.
# - Usage:
#   - Collected with mathematics tests; AVX2 execution skips when unsupported.
# - Defaults:
#   - Compilation is strict C23 with the repository-pinned Clang toolchain.
#

"""Regression checks for the benchmark-only AVX2 CRAZY implementation."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final

import pytest

WINDOWS_OS_NAME: Final = "nt"
ROOT = Path(__file__).resolve().parents[2]
CLANG_NAME = "clang.exe" if os.name == WINDOWS_OS_NAME else "clang"
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin" / CLANG_NAME
SOURCE = (
    ROOT
    / "src/performance/benchmarking/composition/interpreter"
    / "profile_crazy_avx2.c"
)
X86_MACHINES = frozenset({"amd64", "i386", "i686", "x86", "x86_64"})
EXPECTED_BENCHMARK_ID = "cpu-profile-crazy-avx2-v1"
EXPECTED_VALIDATION = "validation,ok\n"
AVX2_UNAVAILABLE = 77
SOURCE_MARKERS: Final = (
    "#define CORPUS_SIZE UINT32_C(59049)",
    "#define CORPUS_STRIDE UINT32_C(104729)",
    "#define REPETITIONS UINT32_C(16)",
    "#define SAMPLE_COUNT UINT32_C(15)",
    "#define SIMD_LANES UINT32_C(8)",
    '__attribute__((target("avx2")))',
)
GATHER_INSTRUCTION: Final = "vpgatherdd"
MINIMUM_GATHER_INSTRUCTIONS: Final = 2
YMM_REGISTER_FRAGMENT: Final = "ymm"
VECTOR_MULTIPLY_INSTRUCTION: Final = "vpmulld"
VECTOR_ADD_INSTRUCTION: Final = "vpaddd"
STRICT_FLAGS = (
    "-std=c23",
    "-O3",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Werror",
)


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=60,
    )


def _require_clang() -> None:
    if not CLANG.is_file():
        pytest.skip("repository-pinned Clang 22.1.8 is unavailable")


def _require_x86() -> None:
    if platform.machine().lower() not in X86_MACHINES:
        pytest.skip("AVX2 benchmark codegen is x86-specific")


def test_avx2_benchmark_identity_and_frozen_corpus_are_explicit() -> None:
    """The experimental source identifies the reviewed workload and ISA."""
    text = SOURCE.read_text(encoding="utf-8")
    assert f'#define BENCHMARK_ID "{EXPECTED_BENCHMARK_ID}"' in text
    for marker in SOURCE_MARKERS:
        assert marker in text


def test_avx2_benchmark_compiles_and_validates_every_corpus_output(
    tmp_path: Path,
) -> None:
    """Capable x86 hosts match scalar output and canonical checksums exactly."""
    _require_clang()
    _require_x86()
    executable_name = (
        "profile-crazy-avx2.exe"
        if os.name == WINDOWS_OS_NAME
        else "profile-crazy-avx2"
    )
    executable = tmp_path / executable_name
    compiled = _run(
        [str(CLANG), *STRICT_FLAGS, str(SOURCE), "-o", str(executable)],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stderr
    executed = _run([str(executable), "--validate-only"], tmp_path)
    if executed.returncode == AVX2_UNAVAILABLE:
        pytest.skip("host CPU does not expose AVX2")
    assert executed.returncode == 0, executed.stderr
    assert executed.stdout == EXPECTED_VALIDATION


def test_avx2_benchmark_release_codegen_contains_gathers_and_ymm(
    tmp_path: Path,
) -> None:
    """The named SIMD route must compile to AVX2 gather/vector instructions."""
    _require_clang()
    _require_x86()
    assembly = tmp_path / "profile-crazy-avx2.s"
    compiled = _run(
        [
            str(CLANG),
            *STRICT_FLAGS,
            "-S",
            "-masm=intel",
            str(SOURCE),
            "-o",
            str(assembly),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stderr
    text = assembly.read_text(encoding="utf-8")
    assert text.count(GATHER_INSTRUCTION) >= MINIMUM_GATHER_INSTRUCTIONS
    assert YMM_REGISTER_FRAGMENT in text
    assert VECTOR_MULTIPLY_INSTRUCTION in text
    assert VECTOR_ADD_INSTRUCTION in text
