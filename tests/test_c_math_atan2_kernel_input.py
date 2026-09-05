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
#   - Differential evidence for exact finite atan2 ratio normalization.
# - Must-Not:
#   - Use host atan2, floating division, or approximate expected values.
# - Allows:
#   - Inputs: deterministic finite nonzero binary64 word pairs.
#   - Outputs: native C agreement with exact Fraction-derived kernel geometry.
#   - Side effects: temporary C harness compilation and execution only.
# - Split-When:
#   - Numerical atan approximation requires independent accuracy evidence.
# - Merge-When:
#   - Complete atan2 differential evidence subsumes exact input reduction.
# - Summary:
#   - Cross-checks finite atan2 kernel inputs over broad binary64 geometry.
# - Description:
#   - Expected ratios are reconstructed exactly as rational powers of two.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Public atan2 remains unavailable; this proves only kernel-input geometry.
#

"""Differential exact-ratio evidence for future binary64 atan2 kernels."""

from __future__ import annotations

from fractions import Fraction
from itertools import starmap
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN_BIT = 1 << 63
FRACTION_MASK = (1 << 52) - 1
HIDDEN_BIT = 1 << 52
SIGNIFICAND_BITS = 53
EXPONENT_MASK = 0x7FF
ALL_BITS = (1 << 64) - 1
VECTOR_COUNT = 512
LCG_MULTIPLIER = 6364136223846793005
LCG_INCREMENT = 1442695040888963407
LCG_SEED = 0x4154414E325F5631
EDGE_PAIRS = (
    (0x0000000000000001, 0x3FF0000000000000),
    (0x000FFFFFFFFFFFFF, 0x0010000000000000),
    (0x0010000000000000, 0x7FEFFFFFFFFFFFFF),
    (0x3FF0000000000000, 0x3FF0000000000000),
    (0x4000000000000000, 0x3FF0000000000000),
    (0xBFF8000000000000, 0x4004000000000000),
    (0x7FEFFFFFFFFFFFFF, 0x0000000000000001),
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


def _finite_nonzero(bits: int) -> bool:
    magnitude = bits & ~SIGN_BIT
    return magnitude != 0 and (magnitude >> 52) & EXPONENT_MASK != EXPONENT_MASK


def _deterministic_pairs() -> tuple[tuple[int, int], ...]:
    state = LCG_SEED
    pairs = list(EDGE_PAIRS)
    while len(pairs) < VECTOR_COUNT + len(EDGE_PAIRS):
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        y_bits = state
        state = (state * LCG_MULTIPLIER + LCG_INCREMENT) & ALL_BITS
        x_bits = state
        if _finite_nonzero(y_bits) and _finite_nonzero(x_bits):
            pairs.append((y_bits, x_bits))
    return tuple(pairs)


def _raw_fraction(bits: int) -> Fraction:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        return Fraction(fraction, 1 << 1074)
    significand = HIDDEN_BIT | fraction
    exponent = raw_exponent - 1023 - 52
    if exponent >= 0:
        return Fraction(significand << exponent, 1)
    return Fraction(significand, 1 << -exponent)


def _normalized(bits: int) -> tuple[int, int]:
    magnitude = bits & ~SIGN_BIT
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    significand = magnitude & FRACTION_MASK
    if raw_exponent == 0:
        exponent = -1074
    else:
        significand |= HIDDEN_BIT
        exponent = raw_exponent - 1023 - 52
    while significand.bit_length() < SIGNIFICAND_BITS:
        significand <<= 1
        exponent -= 1
    return significand, exponent


def _ordered_bits(y_bits: int, x_bits: int) -> tuple[int, int, int]:
    y_magnitude = y_bits & ~SIGN_BIT
    x_magnitude = x_bits & ~SIGN_BIT
    if y_magnitude > x_magnitude:
        return x_bits, y_bits, 1
    return y_bits, x_bits, 0


def _geometry_ratio(geometry: tuple[int, int, int, int, int, int]) -> Fraction:
    ratio = Fraction(geometry[0], geometry[1])
    if geometry[2] >= 0:
        return ratio * (1 << geometry[2])
    return ratio / (1 << -geometry[2])


def _expected(y_bits: int, x_bits: int) -> tuple[int, int, int, int, int, int]:
    numerator_bits, denominator_bits, swapped = _ordered_bits(y_bits, x_bits)
    numerator = _normalized(numerator_bits)
    denominator = _normalized(denominator_bits)
    result = (
        numerator[0],
        denominator[0],
        numerator[1] - denominator[1],
        swapped,
        int(bool(y_bits & SIGN_BIT)),
        int(bool(x_bits & SIGN_BIT)),
    )
    exact_ratio = min(_raw_fraction(y_bits), _raw_fraction(x_bits)) / max(
        _raw_fraction(y_bits), _raw_fraction(x_bits)
    )
    assert _geometry_ratio(result) == exact_ratio
    assert exact_ratio <= 1
    return result


def _row(y_bits: int, x_bits: int) -> str:
    numerator, denominator, delta, swapped, y_negative, x_negative = _expected(
        y_bits, x_bits
    )
    return (
        "  {"
        f"UINT64_C(0x{y_bits:016x}), UINT64_C(0x{x_bits:016x}), "
        f"UINT64_C(0x{numerator:016x}), UINT64_C(0x{denominator:016x}), "
        f"INT32_C({delta}), UINT32_C({swapped}), UINT32_C({y_negative}), "
        f"UINT32_C({x_negative})"
        "}"
    )


def _harness_source() -> str:
    rows = ",\n".join(starmap(_row, _deterministic_pairs()))
    return f"""#include \"math_transcendental_bits.h\"
#include <stdint.h>
typedef struct Vector {{
  uint64_t y_bits, x_bits, numerator, denominator;
  int32_t delta;
  uint32_t swapped, y_negative, x_negative;
}} Vector;
static const Vector vectors[] = {{
{rows}
}};
int main(void) {{
  uint32_t i = 0;
  while (i < (uint32_t)(sizeof(vectors) / sizeof(vectors[0]))) {{
    MalbolgeGuestMathAtan2KernelInput result;
    const Vector *v = &vectors[i];
    if (!malbolge_guest_math_atan2_kernel_input(
            v->y_bits, v->x_bits, &result) ||
        result.numerator_significand != v->numerator ||
        result.denominator_significand != v->denominator ||
        result.exponent_delta != v->delta || result.swapped != v->swapped ||
        result.y_negative != v->y_negative ||
        result.x_negative != v->x_negative) {{
      return 10;
    }}
    ++i;
  }}
  return 0;
}}
"""


def test_atan2_kernel_input_matches_exact_fraction_geometry(
    tmp_path: Path,
) -> None:
    """Match 519 finite pairs without host floating arithmetic or atan2."""
    harness = tmp_path / "atan2-kernel-input.c"
    executable = tmp_path / "atan2-kernel-input"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{CONTRACT}",
            str(SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
