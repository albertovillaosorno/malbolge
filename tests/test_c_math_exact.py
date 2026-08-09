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
#   - Deterministic bit-pattern checks for exact guest binary64 math.
# - Must-Not:
#   - Use host libm results as expected authority or admit inexact routines.
# - Allows:
#   - Inputs: fixed edges and deterministic pseudo-random binary64 encodings.
#   - Outputs: native evidence against an independent rational reference.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Another floating format or inexact math family needs independent vectors.
# - Merge-When:
#   - Guest-libc conformance owns equivalent broad bit-pattern evidence.
# - Summary:
#   - Cross-checks fabs/floor/ceil/trunc over broad binary64 encodings.
# - Description:
#   - Python rational arithmetic derives exact expected result bit patterns.
# - Usage:
#   - Collected on Windows with repository-pinned Clang.
# - Defaults:
#   - NaNs canonicalize to the ABI quiet payload-zero representation.
#

"""Broad deterministic differential vectors for exact guest binary64 math."""

from __future__ import annotations

from fractions import Fraction
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
MATH_SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_exact.c"
WINDOWS_OS_NAME = "nt"
SIGN_BIT = 1 << 63
EXPONENT_MASK = 0x7FF0000000000000
FRACTION_MASK = 0x000FFFFFFFFFFFFF
CANONICAL_NAN = 0x7FF8000000000000
MAX_EXPONENT = 0x7FF
EXPONENT_BIAS = 1023
FRACTION_BITS = 52
ALL_BITS = (1 << 64) - 1
VECTOR_COUNT = 256
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4D414C424F4C4745

EDGE_CASES = (
    0x0000000000000000,
    0x8000000000000000,
    0x0000000000000001,
    0x8000000000000001,
    0x3FE0000000000000,
    0xBFE0000000000000,
    0x3FF0000000000000,
    0xBFF0000000000000,
    0x3FF8000000000000,
    0xBFF8000000000000,
    0x4330000000000000,
    0xC330000000000000,
    0x7FEFFFFFFFFFFFFF,
    0xFFEFFFFFFFFFFFFF,
    0x7FF0000000000000,
    0xFFF0000000000000,
    0x7FF0000000000001,
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


def _exponent(bits: int) -> int:
    return (bits & EXPONENT_MASK) >> FRACTION_BITS


def _is_nan(bits: int) -> bool:
    return _exponent(bits) == MAX_EXPONENT and (bits & FRACTION_MASK) != 0


def _is_passthrough_integer(bits: int) -> bool:
    exponent = _exponent(bits)
    magnitude = bits & ~SIGN_BIT
    return (
        exponent == MAX_EXPONENT
        or magnitude == 0
        or exponent >= EXPONENT_BIAS + FRACTION_BITS
    )


def _decode_fraction(bits: int) -> Fraction:
    exponent = _exponent(bits)
    fraction = bits & FRACTION_MASK
    significand = fraction if exponent == 0 else (1 << FRACTION_BITS) | fraction
    power = (
        1 - EXPONENT_BIAS - FRACTION_BITS
        if exponent == 0
        else exponent - EXPONENT_BIAS - FRACTION_BITS
    )
    numerator = significand
    denominator = 1
    if power >= 0:
        numerator <<= power
    else:
        denominator <<= -power
    if bits & SIGN_BIT:
        numerator = -numerator
    return Fraction(numerator, denominator)


def _integer_bits(value: int, *, negative_zero: bool = False) -> int:
    if value == 0:
        return SIGN_BIT if negative_zero else 0
    sign = SIGN_BIT if value < 0 else 0
    magnitude = abs(value)
    exponent = magnitude.bit_length() - 1
    assert exponent <= FRACTION_BITS
    significand = magnitude << (FRACTION_BITS - exponent)
    fraction = significand & FRACTION_MASK
    return sign | ((exponent + EXPONENT_BIAS) << FRACTION_BITS) | fraction


def _expected_fabs(bits: int) -> int:
    return CANONICAL_NAN if _is_nan(bits) else bits & ~SIGN_BIT


def _expected_trunc(bits: int) -> int:
    if _is_nan(bits):
        return CANONICAL_NAN
    if _is_passthrough_integer(bits):
        return bits
    integer = int(_decode_fraction(bits))
    return _integer_bits(
        integer,
        negative_zero=integer == 0 and (bits & SIGN_BIT) != 0,
    )


def _expected_floor(bits: int) -> int:
    if _is_nan(bits):
        return CANONICAL_NAN
    if _is_passthrough_integer(bits):
        return bits
    exact = _decode_fraction(bits)
    integer = exact.numerator // exact.denominator
    return _integer_bits(integer)


def _expected_ceil(bits: int) -> int:
    if _is_nan(bits):
        return CANONICAL_NAN
    if _is_passthrough_integer(bits):
        return bits
    exact = _decode_fraction(bits)
    integer = -((-exact.numerator) // exact.denominator)
    return _integer_bits(
        integer,
        negative_zero=integer == 0 and (bits & SIGN_BIT) != 0,
    )


def _vector_row(bits: int) -> str:
    values = (
        bits,
        _expected_fabs(bits),
        _expected_floor(bits),
        _expected_ceil(bits),
        _expected_trunc(bits),
    )
    encoded = ", ".join(f"UINT64_C(0x{value:016x})" for value in values)
    return "    {" + encoded + "}"


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
  uint64_t absolute;
  uint64_t floor_value;
  uint64_t ceil_value;
  uint64_t trunc_value;
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
    TestValue absolute = {{.value = fabs(input.value)}};
    TestValue floor_result = {{.value = floor(input.value)}};
    TestValue ceil_result = {{.value = ceil(input.value)}};
    TestValue trunc_result = {{.value = trunc(input.value)}};

    if (absolute.bits != vectors[index].absolute) {{
      return 10;
    }}
    if (floor_result.bits != vectors[index].floor_value) {{
      return 20;
    }}
    if (ceil_result.bits != vectors[index].ceil_value) {{
      return 30;
    }}
    if (trunc_result.bits != vectors[index].trunc_value) {{
      return 40;
    }}
    ++index;
  }}
  return 0;
}}
"""


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="repository-pinned native Clang execution is Windows-only",
)
def test_exact_math_rational_vectors(tmp_path: Path) -> None:
    """Match 274 binary64 vectors without using host libm as authority."""
    source = tmp_path / "math-vectors.c"
    executable = tmp_path / "math-vectors.exe"
    _ = source.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            f"-I{INCLUDE}",
            str(MATH_SOURCE),
            str(source),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
