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
#   - Algebraic-size inputs for a sin/cos exponential midpoint-separation route.
# - Must-Not:
#   - Claim a quantitative separation or a finite correct-rounding ceiling.
# - Allows:
#   - Inputs: kernel-required binary64 arguments and proposed result cells.
#   - Outputs: exact cell dyadics and strict/closed power-of-two size ceilings.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A sourced quantitative theorem consumes these bounds directly.
# - Merge-When:
#   - Full-domain sin/cos table-maker proof subsumes this bridge.
# - Summary:
#   - Verifies the quadratic P(exp(i*x)) bridge geometry with Fraction.
# - Description:
#   - Covers tight input, signed-zero-cell, and polynomial-height extremes.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Structural bounds are not treated as separation claims.
#

"""Structural exponential-transcendence bounds for sin/cos midpoint cells."""

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
SIN = 1
COS = 2
SIN_SMALL_MAX = 0x3E57000000000000
COS_SMALL_MAX = 0x3E46A00000000000
MAX_FINITE = 0x7FEFFFFFFFFFFFFF
ONE = 0x3FF0000000000000
HALF = 0x3FE0000000000000
INPUT_NUMERATOR_BITS_MAX = 1024
INPUT_DENOMINATOR_SHIFT_MAX = 79
ALPHA_HEIGHT_EXPONENT_MAX = 2048
INVERSE_DENOMINATOR_BITS_MAX = 1024
INVERSE_HOUSE_EXPONENT_MAX = 27
INVERSE_PRODUCT_EXPONENT_MAX = 1024
MIDPOINT_NUMERATOR_BITS_MAX = 54
MIDPOINT_SHIFT_MAX = 1075
POLYNOMIAL_HEIGHT_EXPONENT_MAX = 1076
CASES = (
    (COS, COS_SMALL_MAX + 1, ONE),
    (SIN, MAX_FINITE, 0),
    (COS, MAX_FINITE | SIGN, SIGN),
    (SIN, 0x4010000000000000, HALF),
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
        power = raw_exponent - 1023 - 52
        value = (
            Fraction(significand << power, 1)
            if power >= 0
            else Fraction(significand, 1 << -power)
        )
    return -value if negative else value


def _next_up(bits: int) -> int:
    if (bits & MAGNITUDE_MASK) == 0:
        return 1
    return bits - 1 if bits & SIGN else bits + 1


def _next_down(bits: int) -> int:
    if (bits & MAGNITUDE_MASK) == 0:
        return SIGN | 1
    return bits + 1 if bits & SIGN else bits - 1


def _cell_midpoints(candidate: int) -> tuple[Fraction, Fraction]:
    value = _binary64(candidate)
    if (candidate & MAGNITUDE_MASK) == 0:
        if candidate & SIGN:
            return Fraction(-1, 1 << 1075), Fraction(0)
        return Fraction(0), Fraction(1, 1 << 1075)
    lower = (_binary64(_next_down(candidate)) + value) / 2
    upper = (value + _binary64(_next_up(candidate))) / 2
    return lower, upper


def _ceil_log2(value: Fraction) -> int:
    assert value > 0
    if value <= 1:
        return 0
    exponent = max(
        0, value.numerator.bit_length() - value.denominator.bit_length()
    )
    while Fraction(1 << exponent) < value:
        exponent += 1
    return exponent


def _input_bounds(bits: int) -> tuple[int, int, int, int, int, int]:
    value = abs(_binary64(bits))
    numerator = value.numerator
    denominator = value.denominator
    assert numerator > 0
    assert denominator & (denominator - 1) == 0
    numerator_bits = numerator.bit_length()
    denominator_shift = denominator.bit_length() - 1
    height_exponent = max(
        2 * numerator_bits,
        2 * denominator_shift + (1 if denominator_shift else 0),
    )
    inverse_house = max(Fraction(1), Fraction(denominator, numerator))
    product = numerator * inverse_house
    assert product.denominator == 1
    return (
        numerator_bits,
        denominator_shift,
        height_exponent,
        numerator_bits,
        _ceil_log2(inverse_house),
        _ceil_log2(product),
    )


def _dyadic_tuple(value: Fraction) -> tuple[int, int, int]:
    denominator = value.denominator
    assert denominator & (denominator - 1) == 0
    return (
        abs(value.numerator),
        denominator.bit_length() - 1,
        int(value < 0),
    )


def _cell_bounds(candidate: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(_dyadic_tuple(value) for value in _cell_midpoints(candidate))


def _polynomial_height_exponent(midpoint: Fraction) -> int:
    numerator_bits = abs(midpoint.numerator).bit_length()
    shift = midpoint.denominator.bit_length() - 1
    return max(numerator_bits, shift) + 1


def _harness_source() -> str:
    rows = ",\n".join(
        "".join(
            (
                f"  {{UINT32_C({op}), UINT64_C(0x{input_bits:016x}), ",
                f"UINT64_C(0x{candidate:016x})}}",
            )
        )
        for op, input_bits, candidate in CASES
    )
    return f"""#include \"math_transcendental_bits.h\"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
typedef struct Case {{ uint32_t op; uint64_t input; uint64_t candidate; }} Case;
static const Case cases[] = {{
{rows}
}};
int main(void) {{
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosExponentialBridgeBounds b;
    if (!malbolge_guest_math_sincos_exponential_bridge_bounds(
            (MalbolgeGuestMathUnaryOperation)cases[index].op,
            cases[index].input, cases[index].candidate, &b)) return 80;
    (void)printf(
        "%u %u %u %u %u %u %" PRIu64 " %u %u %" PRIu64
        " %u %u %u %u %u\\n",
        b.input_numerator_bits, b.input_denominator_shift,
        b.input_argument.alpha_height_pow2_exponent_upper,
        b.input_argument.inverse_denominator_bits,
        b.input_argument.inverse_house_pow2_exponent_upper,
        b.input_argument.inverse_denominator_house_product_pow2_exponent_upper,
        b.output_cell.lower.numerator, b.output_cell.lower.denominator_shift,
        b.output_cell.lower.negative, b.output_cell.upper.numerator,
        b.output_cell.upper.denominator_shift, b.output_cell.upper.negative,
        b.midpoint_numerator_bits_max, b.midpoint_denominator_shift_max,
        b.quadratic_polynomial_height_pow2_exponent_upper);
    ++index;
  }}
  {{
    MalbolgeGuestMathSincosExponentialBridgeBounds b;
    b.input_numerator_bits = UINT32_C(91);
    b.input_denominator_shift = UINT32_C(92);
    b.quadratic_polynomial_height_pow2_exponent_upper = UINT32_C(93);
    if (malbolge_guest_math_sincos_exponential_bridge_bounds(
            MALBOLGE_GUEST_MATH_COS, UINT64_C(0x3e46a00000000000),
            UINT64_C(0x3ff0000000000000), &b) ||
        b.input_numerator_bits != UINT32_C(91) ||
        b.input_denominator_shift != UINT32_C(92) ||
        b.quadratic_polynomial_height_pow2_exponent_upper != UINT32_C(93))
      return 81;
    if (malbolge_guest_math_sincos_exponential_bridge_bounds(
            MALBOLGE_GUEST_MATH_SIN, UINT64_C(0x4010000000000000),
            UINT64_C(0x3ff0000000000001), &b)) return 82;
    if (malbolge_guest_math_sincos_exponential_bridge_bounds(
            (MalbolgeGuestMathUnaryOperation)99,
            UINT64_C(0x4010000000000000), UINT64_C(0), &b)) return 83;
  }}
  return 0;
}}
"""


def _assert_row(case: tuple[int, int, int], row: list[str]) -> None:
    _, input_bits, candidate = case
    expected_input = _input_bounds(input_bits)
    lower, upper = _cell_midpoints(candidate)
    lower_tuple, upper_tuple = _cell_bounds(candidate)
    values = tuple(map(int, row))
    assert values[:6] == expected_input
    assert values[6:9] == lower_tuple
    assert values[9:12] == upper_tuple
    assert values[12] == max(
        abs(lower.numerator).bit_length(), abs(upper.numerator).bit_length()
    )
    assert values[13] == max(
        lower.denominator.bit_length() - 1,
        upper.denominator.bit_length() - 1,
    )
    assert values[14] == max(
        _polynomial_height_exponent(lower),
        _polynomial_height_exponent(upper),
    )
    assert values[0] <= INPUT_NUMERATOR_BITS_MAX
    assert values[1] <= INPUT_DENOMINATOR_SHIFT_MAX
    assert values[2] <= ALPHA_HEIGHT_EXPONENT_MAX
    assert values[3] <= INVERSE_DENOMINATOR_BITS_MAX
    assert values[4] <= INVERSE_HOUSE_EXPONENT_MAX
    assert values[5] <= INVERSE_PRODUCT_EXPONENT_MAX
    assert values[12] <= MIDPOINT_NUMERATOR_BITS_MAX
    assert values[13] <= MIDPOINT_SHIFT_MAX
    assert values[14] <= POLYNOMIAL_HEIGHT_EXPONENT_MAX


def test_sincos_exponential_bridge_matches_fraction_geometry(
    tmp_path: Path,
) -> None:
    """Match exact dyadics and every structural exponent independently."""
    harness = tmp_path / "sincos-exponential-bridge.c"
    executable = tmp_path / "sincos-exponential-bridge"
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
    for case, row in zip(CASES, rows, strict=True):
        _assert_row(case, row)


def test_sincos_exponential_bridge_extrema_are_tight() -> None:
    """Pin independent witnesses for each full-domain structural ceiling."""
    cos_first = _input_bounds(COS_SMALL_MAX + 1)
    max_finite = _input_bounds(MAX_FINITE)
    assert cos_first[1] == INPUT_DENOMINATOR_SHIFT_MAX
    assert cos_first[4] == INVERSE_HOUSE_EXPONENT_MAX
    assert max_finite[0] == INPUT_NUMERATOR_BITS_MAX
    assert max_finite[2] == ALPHA_HEIGHT_EXPONENT_MAX
    assert max_finite[3] == INVERSE_DENOMINATOR_BITS_MAX
    assert max_finite[5] == INVERSE_PRODUCT_EXPONENT_MAX
    zero_lower, zero_upper = _cell_midpoints(0)
    assert zero_lower == 0
    assert zero_upper == Fraction(1, 1 << MIDPOINT_SHIFT_MAX)
    assert (
        _polynomial_height_exponent(zero_upper)
        == POLYNOMIAL_HEIGHT_EXPONENT_MAX
    )
    one_lower, one_upper = _cell_midpoints(ONE)
    assert max(
        abs(one_lower.numerator).bit_length(),
        abs(one_upper.numerator).bit_length(),
    ) == MIDPOINT_NUMERATOR_BITS_MAX
