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
#   - Independent correctly-rounded vectors for canonical guest binary64 sqrt.
# - Must-Not:
#   - Use host sqrt/libm output as expected authority or weaken NaN policy.
# - Allows:
#   - Inputs: fixed edges and deterministic pseudo-random binary64 encodings.
#   - Outputs: native evidence against Python arbitrary-precision integer sqrt.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Another inexact binary64 routine needs an independently proved reference.
# - Merge-When:
#   - Guest-libc conformance owns equivalent correctly-rounded sqrt evidence.
# - Summary:
#   - Cross-checks guest sqrt over broad binary64 bit patterns.
# - Description:
#   - Expected bits use unbounded integer square root, never host floating math.
# - Usage:
#   - Collected on Windows with repository-pinned Clang.
# - Defaults:
#   - The guest ABI fixes nearest-ties-even and canonical quiet NaN publication.
#

"""Independent deterministic differential vectors for guest binary64 sqrt."""

from __future__ import annotations

from math import isqrt
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
LLVM_NM = ROOT / ".dependencies/llvm/22.1.8/bin/llvm-nm.exe"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
SQRT_SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_sqrt.c"
WINDOWS_OS_NAME = "nt"
SIGN_BIT = 1 << 63
FRACTION_MASK = 0x000FFFFFFFFFFFFF
CANONICAL_NAN = 0x7FF8000000000000
MAX_EXPONENT = 0x7FF
EXPONENT_BIAS = 1023
FRACTION_BITS = 52
HIDDEN_BIT = 1 << FRACTION_BITS
ALL_BITS = (1 << 64) - 1
VECTOR_COUNT = 512
LCG_MULTIPLIER = 2862933555777941757
LCG_INCREMENT = 3037000493
LCG_SEED = 0x535152545F563100
WINDOWS_ABI_TARGETS = (
    ("i686-pc-windows-msvc", frozenset({"__fltused"})),
    ("x86_64-pc-windows-msvc", frozenset({"_fltused"})),
    ("aarch64-pc-windows-msvc", frozenset[str]()),
)
WASM_TARGET = "wasm32-unknown-unknown"
WASM_TARGET_MACHINERY = frozenset({"__stack_pointer"})

EDGE_CASES = (
    0x0000000000000000,
    0x8000000000000000,
    0x0000000000000001,
    0x000FFFFFFFFFFFFF,
    0x0010000000000000,
    0x0010000000000001,
    0x3FD0000000000000,
    0x3FE0000000000000,
    0x3FF0000000000000,
    0x4000000000000000,
    0x4010000000000000,
    0x7FEFFFFFFFFFFFFF,
    0x8000000000000001,
    0xBFF0000000000000,
    0xFFEFFFFFFFFFFFFF,
    0x7FF0000000000000,
    0xFFF0000000000000,
    0x7FF0000000000001,
    0x7FF8123456789ABC,
    0xFFF8123456789ABC,
)


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )


def _deterministic_bits() -> tuple[int, ...]:
    state = LCG_SEED
    generated: list[int] = []
    for _ in range(VECTOR_COUNT):
        state = ((state * LCG_MULTIPLIER) + LCG_INCREMENT) & ALL_BITS
        generated.append(state)
    return (*EDGE_CASES, *generated)


def _special_sqrt(bits: int) -> int | None:
    raw_exponent = (bits >> FRACTION_BITS) & MAX_EXPONENT
    fraction = bits & FRACTION_MASK
    if raw_exponent == MAX_EXPONENT:
        return CANONICAL_NAN if fraction != 0 or bits & SIGN_BIT else bits
    if bits & ~SIGN_BIT == 0:
        return bits
    return CANONICAL_NAN if bits & SIGN_BIT else None


def _normalized_positive(bits: int) -> tuple[int, int]:
    raw_exponent = (bits >> FRACTION_BITS) & MAX_EXPONENT
    fraction = bits & FRACTION_MASK
    if raw_exponent != 0:
        return HIDDEN_BIT | fraction, raw_exponent - EXPONENT_BIAS
    significand = fraction
    exponent = -1022
    while significand & HIDDEN_BIT == 0:
        significand <<= 1
        exponent -= 1
    return significand, exponent


def _rounded_scaled_root(significand: int) -> int:
    radicand = significand << FRACTION_BITS
    root = isqrt(radicand)
    remainder = radicand - (root * root)
    return root + int(remainder > root)


def _expected_sqrt(bits: int) -> int:
    special = _special_sqrt(bits)
    if special is not None:
        return special
    significand, exponent = _normalized_positive(bits)
    if exponent % 2 != 0:
        significand <<= 1
        exponent -= 1
    root = _rounded_scaled_root(significand)
    result_exponent = exponent // 2
    if root == HIDDEN_BIT << 1:
        root >>= 1
        result_exponent += 1
    return ((result_exponent + EXPONENT_BIAS) << FRACTION_BITS) | (
        root - HIDDEN_BIT
    )


def _vector_row(bits: int) -> str:
    expected = _expected_sqrt(bits)
    return f"    {{UINT64_C(0x{bits:016x}), UINT64_C(0x{expected:016x})}}"


def _harness_source() -> str:
    rows = ",\n".join(_vector_row(bits) for bits in _deterministic_bits())
    return f"""#include <math.h>
#include <stdint.h>

typedef union TestValue {{
  double value;
  uint64_t bits;
}} TestValue;

typedef struct TestVector {{
  uint64_t input;
  uint64_t expected;
}} TestVector;

#if defined(_MSC_VER)
int _fltused = 0;
#endif

static const TestVector vectors[] = {{
{rows}
}};

int main(void) {{
  uint32_t index = 0U;
  const uint32_t count =
      (uint32_t)(sizeof(vectors) / sizeof(vectors[0]));

  while (index < count) {{
    TestValue input = {{.bits = vectors[index].input}};
    TestValue result = {{.value = sqrt(input.value)}};
    if (result.bits != vectors[index].expected) {{
      return 10;
    }}
    ++index;
  }}
  return 0;
}}
"""


def _undefined_symbols(object_file: Path) -> frozenset[str]:
    completed = _run([str(LLVM_NM), "-u", str(object_file)], ROOT)
    assert completed.returncode == 0, completed.stderr
    return frozenset(
        line.split()[-1]
        for line in completed.stdout.splitlines()
        if line.split()
    )


def _compile_object(tmp_path: Path, target: str) -> Path:
    object_file = tmp_path / f"sqrt-{target}.o"
    completed = _run(
        [
            str(CLANG),
            f"--target={target}",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{INCLUDE}",
            "-c",
            str(SQRT_SOURCE),
            "-o",
            str(object_file),
        ],
        ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    return object_file


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="repository-pinned native Clang execution is Windows-only",
)
def test_sqrt_matches_arbitrary_precision_integer_reference(
    tmp_path: Path,
) -> None:
    """Match 532 binary64 patterns without using host sqrt as authority."""
    source = tmp_path / "sqrt-vectors.c"
    executable = tmp_path / "sqrt-vectors.exe"
    _ = source.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            f"-I{INCLUDE}",
            str(SQRT_SOURCE),
            str(source),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="repository-pinned LLVM object inspection is Windows-only",
)
def test_sqrt_has_no_callable_host_or_compiler_helpers(tmp_path: Path) -> None:
    """Keep sqrt self-contained across every compiler ABI projection."""
    for target, expected in WINDOWS_ABI_TARGETS:
        object_file = _compile_object(tmp_path, target)
        assert _undefined_symbols(object_file) == expected
    wasm_object = _compile_object(tmp_path, WASM_TARGET)
    assert _undefined_symbols(wasm_object) == WASM_TARGET_MACHINERY
