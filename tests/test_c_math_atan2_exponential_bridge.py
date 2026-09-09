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
#   - Algebraic-size bounds for an exponential transcendence route to atan2.
# - Must-Not:
#   - Claim a transcendence measure or a finite correct-rounding precision
#     bound.
# - Allows:
#   - Inputs: reduced dyadic midpoints plus real candidate cells from guest C.
#   - Outputs: strict power-of-two height bounds and inverse-alpha size bounds.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A sourced explicit transcendence measure consumes these bounds directly.
# - Merge-When:
#   - Full-domain atan2 resource proof subsumes the exponential bridge.
# - Summary:
#   - Bounds the Gaussian linear polynomial and alpha=2*i*midpoint inputs.
# - Description:
#   - Python integer arithmetic independently verifies every published exponent.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Bounds are strict structural ceilings, never separation claims.
#

"""Structural bounds for an exponential-transcendence atan2 bridge."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SIGN = 1 << 63
MAGNITUDE_MASK = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
HEIGHT_LIMIT = 2098
POLYNOMIAL_HEIGHT_EXPONENT_LIMIT = HEIGHT_LIMIT + 1
ALPHA_HEIGHT_EXPONENT_LIMIT = 218
INVERSE_DENOMINATOR_BITS_LIMIT = 109
INVERSE_HOUSE_EXPONENT_LIMIT = 106
CASES = (
    (0x3FEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0xBFEE19FA869EA9FC, 0x3FF197DD31B21770),
    (0x0000000000000001, 0xFFEFFFFFFFFFFFFF),
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


def _binary64(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & MAGNITUDE_MASK
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert raw_exponent != EXPONENT_MASK
    if raw_exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN | fraction
        shift = raw_exponent - 1023 - 52
        value = (
            Fraction(significand << shift, 1)
            if shift >= 0
            else Fraction(significand, 1 << -shift)
        )
    return -value if negative else value


def _next_up(bits: int) -> int:
    return bits - 1 if bits & SIGN else bits + 1


def _next_down(bits: int) -> int:
    return bits + 1 if bits & SIGN else bits - 1


def _argument_bounds(midpoint: Fraction) -> tuple[int, int, int]:
    magnitude = abs(midpoint)
    numerator = magnitude.numerator
    denominator = magnitude.denominator
    assert denominator & (denominator - 1) == 0
    shift = denominator.bit_length() - 1
    numerator_bits = numerator.bit_length()
    if shift == 0:
        alpha_numerator_bits = numerator_bits + 1
        alpha_denominator_exponent = 0
    else:
        alpha_numerator_bits = numerator_bits
        alpha_denominator_exponent = shift - 1
    height_exponent = max(
        2 * alpha_numerator_bits,
        2 * alpha_denominator_exponent + 1,
    )
    return height_exponent, alpha_numerator_bits, alpha_denominator_exponent


def _ratio_height(y_bits: int, x_bits: int) -> int:
    ratio = abs(_binary64(y_bits) / _binary64(x_bits))
    return max(ratio.numerator.bit_length(), ratio.denominator.bit_length())


def _cell_bounds(candidate: int) -> tuple[tuple[int, int, int], ...]:
    value = _binary64(candidate)
    lower = (_binary64(_next_down(candidate)) + value) / 2
    upper = (value + _binary64(_next_up(candidate))) / 2
    return _argument_bounds(lower), _argument_bounds(upper)


def _harness_source() -> str:
    rows = ",\n".join(
        f"  {{UINT64_C(0x{y:016x}), UINT64_C(0x{x:016x})}}" for y, x in CASES
    )
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Pair {{ uint64_t y, x; }} Pair;
static const Pair pairs[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(pairs) / sizeof(pairs[0]))) {{
    uint64_t candidate = UINT64_C(0);
    MalbolgeGuestMathAtan2ExponentialBridgeBounds bounds;
    if (!malbolge_guest_math_atan2_unique_binary64(
            pairs[index].y, pairs[index].x, &candidate) ||
        !malbolge_guest_math_atan2_exponential_bridge_bounds(
            pairs[index].y, pairs[index].x, candidate, &bounds)) return 81;
    (void)printf(
        "%016" PRIx64 " %" PRIu32 " %" PRIu32 " %" PRIu32 " %" PRIu32
        " %" PRIu32 " %" PRIu32 " %" PRIu32 " %" PRIu32 " %" PRIu32
        "\\n",
        candidate, bounds.linear_polynomial_height_pow2_exponent_upper,
        bounds.lower_midpoint.alpha_height_pow2_exponent_upper,
        bounds.lower_midpoint.inverse_denominator_bits,
        bounds.lower_midpoint.inverse_house_pow2_exponent_upper,
        bounds.upper_midpoint.alpha_height_pow2_exponent_upper,
        bounds.upper_midpoint.inverse_denominator_bits,
        bounds.upper_midpoint.inverse_house_pow2_exponent_upper,
        bounds.alpha_height_pow2_exponent_upper,
        bounds.inverse_denominator_bits_max);
    ++index;
  }}
  {{
    MalbolgeGuestMathDyadic bad = {{UINT64_C(2), UINT32_C(5), UINT32_C(0)}};
    MalbolgeGuestMathExponentialArgumentBounds sentinel = {{
        UINT32_C(91), UINT32_C(92), UINT32_C(93)}};
    if (malbolge_guest_math_dyadic_exponential_argument_bounds(
            &bad, &sentinel) ||
        sentinel.alpha_height_pow2_exponent_upper != UINT32_C(91) ||
        sentinel.inverse_denominator_bits != UINT32_C(92) ||
        sentinel.inverse_house_pow2_exponent_upper != UINT32_C(93)) return 82;
  }}
  return 0;
}}
"""


def _assert_bridge_row(pair: tuple[int, int], row: list[str]) -> None:
    candidate = int(row[0], 16)
    values = tuple(map(int, row[1:]))
    lower, upper = _cell_bounds(candidate)
    polynomial_exponent = _ratio_height(*pair) + 1
    assert values[0] == polynomial_exponent
    assert values[1:4] == lower
    assert values[4:7] == upper
    assert values[7] == max(lower[0], upper[0])
    assert values[8] == max(lower[1], upper[1])
    assert values[0] <= POLYNOMIAL_HEIGHT_EXPONENT_LIMIT
    assert values[7] <= ALPHA_HEIGHT_EXPONENT_LIMIT
    assert values[8] <= INVERSE_DENOMINATOR_BITS_LIMIT
    assert max(lower[2], upper[2]) <= INVERSE_HOUSE_EXPONENT_LIMIT


def test_exponential_bridge_bounds_match_integer_geometry(
    tmp_path: Path,
) -> None:
    """Match every structural exponent without invoking transcendental math."""
    harness = tmp_path / "atan2-exponential-bridge.c"
    executable = tmp_path / "atan2-exponential-bridge"
    _ = harness.write_text(_harness_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
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
    rows = tuple(line.split() for line in executed.stdout.splitlines())
    assert len(rows) == len(CASES)
    for pair, row in zip(CASES, rows, strict=True):
        _assert_bridge_row(pair, row)
