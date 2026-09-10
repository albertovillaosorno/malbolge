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
#   - Q512 periodic Taylor composition from certified Payne-Hanek residuals.
# - Must-Not:
#   - Recompute range reduction or use host trigonometric functions as
#     authority.
# - Allows:
#   - Inputs: retained finite raw binary64 words with magnitude at least four.
#   - Outputs: directed Q512 intervals and unique binary64 results when
#     available.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - A staged Q256-to-Q512 handoff owns retry policy and storage negotiation.
# - Merge-When:
#   - A wider adaptive periodic evaluator subsumes this fixed Q512 layer.
# - Summary:
#   - Checks Q512 Taylor/quadrant transport against exact rational arithmetic.
# - Description:
#   - Fraction consumes the separately certified C residual enclosure.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Fixed Q512 is refinement evidence, not a full-domain precision ceiling.
#

"""Independent composition authority for periodic Q512 sine/cosine."""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SCALE = 1 << 512
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
EXPONENT_BIAS = 1023
ORACLE_TERMS = 64
SIN = 1
COS = 2
QUADRANT_TWO = 2
CASES = (
    0x4010000000000000,
    0x4010000000000001,
    0x4024000000000000,
    0x41D0000000000000,
    0x43EFFFFFFFFFFFFF,
    0x43F0000000000000,
    0x43F0000000000001,
    0x5DC123456789ABCD,
    0x7D0123456789ABCD,
    0x7FEFFFFFFFFFFFFF,
    0xC3F0000000000000,
    0xFFEFFFFFFFFFFFFF,
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


@cache
def _factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def test_q512_taylor_depth_leaves_subcell_remainder() -> None:
    """Keep the fixed 48-term policy below one Q512 omitted-term cell."""
    cell = Fraction(1, 1 << 512)
    radius = Fraction(4, 5)
    assert radius**96 / _factorial(96) < cell
    assert radius**97 / _factorial(97) < cell


def _sin_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = value
    total = Fraction(0)
    for index in range(ORACLE_TERMS):
        contribution = term / _factorial(2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * ORACLE_TERMS + 1)
    if ORACLE_TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _cos_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1)
    total = Fraction(0)
    for index in range(ORACLE_TERMS):
        contribution = term / _factorial(2 * index)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * ORACLE_TERMS)
    if ORACLE_TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _sin_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    if value >= 0:
        return _sin_positive(value)
    lower, upper = _sin_positive(-value)
    return -upper, -lower


def _cos_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    return _cos_positive(abs(value))


def _residual_trig(
    lower: Fraction,
    upper: Fraction,
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    sin_interval = (_sin_bounds(lower)[0], _sin_bounds(upper)[1])
    largest, smallest = (
        (lower, upper) if abs(lower) >= abs(upper) else (upper, lower)
    )
    cos_lower = _cos_bounds(largest)[0]
    cos_upper = Fraction(1) if lower <= 0 <= upper else _cos_bounds(smallest)[1]
    return sin_interval, (cos_lower, cos_upper)


def _rotate(
    quadrant: int,
    sin_interval: tuple[Fraction, Fraction],
    cos_interval: tuple[Fraction, Fraction],
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    if quadrant == 0:
        result = (sin_interval, cos_interval)
    elif quadrant == 1:
        result = (cos_interval, (-sin_interval[1], -sin_interval[0]))
    elif quadrant == QUADRANT_TWO:
        result = (
            (-sin_interval[1], -sin_interval[0]),
            (-cos_interval[1], -cos_interval[0]),
        )
    else:
        result = ((-cos_interval[1], -cos_interval[0]), sin_interval)
    return result


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent, 1)
    return Fraction(1, 1 << -exponent)


def _floor_log2(value: Fraction) -> int:
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    return exponent if value >= _pow2(exponent) else exponent - 1


def _round_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder * 2
    if twice > value.denominator or (
        twice == value.denominator and bool(quotient & 1)
    ):
        quotient += 1
    return quotient


def _binary64_bits(value: Fraction) -> int:
    negative = value < 0
    magnitude = abs(value)
    if not magnitude:
        return 0
    if magnitude < _pow2(-1022):
        bits = _round_integer(magnitude / _pow2(-1074))
    else:
        exponent = _floor_log2(magnitude)
        quantized = _round_integer(magnitude / _pow2(exponent - 52))
        if quantized == 1 << 53:
            quantized >>= 1
            exponent += 1
        bits = ((exponent + EXPONENT_BIAS) << 52) | (quantized & FRACTION_MASK)
    return bits | (SIGN if negative else 0)


def _signed_fixed(hex_value: str, negative: str) -> Fraction:
    value = Fraction(int(hex_value, 16), SCALE)
    return -value if int(negative) else value


def _source() -> str:
    rows = ",\n".join(f"  UINT64_C(0x{bits:016x})" for bits in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
static const uint64_t cases[] = {{
{rows}
}};
static void print_fixed(const MalbolgeGuestMathFixed512 *value) {{
  uint32_t limb = MALBOLGE_GUEST_MATH_FIXED_512_LIMBS;
  while (limb != UINT32_C(0)) {{
    --limb;
    (void)printf("%08" PRIx32, value->limbs[limb]);
  }}
}}
int main(void) {{
  uint32_t scratch[MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS];
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosPayneHanek512 reduced;
    MalbolgeGuestMathSincosInterval512 interval;
    uint64_t sin_bits = UINT64_C(0), cos_bits = UINT64_C(0);
    if (!malbolge_guest_math_sincos_payne_hanek_reduce512(
            cases[index], &reduced) ||
        !malbolge_guest_math_sincos_range_interval512(
            cases[index], MALBOLGE_GUEST_MATH_PERIODIC_Q512_TAYLOR_TERMS,
            &interval, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS) ||
        !malbolge_guest_math_sincos_range_unique_binary64_q512(
            MALBOLGE_GUEST_MATH_SIN, cases[index], &sin_bits, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS) ||
        !malbolge_guest_math_sincos_range_unique_binary64_q512(
            MALBOLGE_GUEST_MATH_COS, cases[index], &cos_bits, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS)) return 80;
    (void)printf("%016" PRIx64 " %u %u %u ", cases[index],
                 reduced.quadrant, reduced.input_negative,
                 reduced.residual_lower_negative);
    print_fixed(&reduced.residual_lower);
    (void)printf(" %u ", reduced.residual_upper_negative);
    print_fixed(&reduced.residual_upper);
    (void)printf(" %u ", interval.sin.lower_negative);
    print_fixed(&interval.sin.lower);
    (void)printf(" %u ", interval.sin.upper_negative);
    print_fixed(&interval.sin.upper);
    (void)printf(" %u ", interval.cos.lower_negative);
    print_fixed(&interval.cos.lower);
    (void)printf(" %u ", interval.cos.upper_negative);
    print_fixed(&interval.cos.upper);
    (void)printf(" %016" PRIx64 " %016" PRIx64 "\\n", sin_bits, cos_bits);
    ++index;
  }}
  {{
    MalbolgeGuestMathSincosInterval512 sentinel = {{0}};
    sentinel.sin.lower.limbs[0] = UINT32_C(9);
    if (malbolge_guest_math_sincos_range_interval512(
            UINT64_C(0x400fffffffffffff), UINT32_C(48), &sentinel, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS) ||
        sentinel.sin.lower.limbs[0] != UINT32_C(9)) return 81;
    if (malbolge_guest_math_sincos_range_interval512(
            cases[0], UINT32_C(48), &sentinel, scratch,
            MALBOLGE_GUEST_MATH_PERIODIC_Q512_SCRATCH_LIMBS - UINT32_C(1)) ||
        sentinel.sin.lower.limbs[0] != UINT32_C(9)) return 82;
  }}
  return 0;
}}
"""


def _compile_and_run(tmp_path: Path) -> tuple[tuple[str, ...], ...]:
    source = tmp_path / "range-interval512.c"
    binary = tmp_path / "range-interval512"
    _ = source.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(source), "-o", str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    return tuple(tuple(line.split()) for line in executed.stdout.splitlines())


def _expected_intervals(
    row: tuple[str, ...],
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    residual = (
        _signed_fixed(row[4], row[3]),
        _signed_fixed(row[6], row[5]),
    )
    sin_expected, cos_expected = _residual_trig(*residual)
    sin_expected, cos_expected = _rotate(
        int(row[1]), sin_expected, cos_expected
    )
    if int(row[2]):
        sin_expected = (-sin_expected[1], -sin_expected[0])
    return sin_expected, cos_expected


def _actual_intervals(
    row: tuple[str, ...],
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    return (
        (_signed_fixed(row[8], row[7]), _signed_fixed(row[10], row[9])),
        (_signed_fixed(row[12], row[11]), _signed_fixed(row[14], row[13])),
    )


def _assert_record(bits: int, row: tuple[str, ...]) -> None:
    assert int(row[0], 16) == bits
    expected = _expected_intervals(row)
    actual = _actual_intervals(row)
    assert actual[0][0] <= expected[0][0] <= expected[0][1] <= actual[0][1]
    assert actual[1][0] <= expected[1][0] <= expected[1][1] <= actual[1][1]
    expected_bits = tuple(
        {_binary64_bits(value) for value in interval} for interval in expected
    )
    assert all(len(values) == 1 for values in expected_bits)
    assert int(row[15], 16) == expected_bits[0].pop()
    assert int(row[16], 16) == expected_bits[1].pop()


def test_q512_periodic_interval_and_rounding_match_fraction(
    tmp_path: Path,
) -> None:
    """Enclose exact rational Taylor images and publish their unique cells."""
    records = _compile_and_run(tmp_path)
    assert len(records) == len(CASES)
    for bits, row in zip(CASES, records, strict=True):
        _assert_record(bits, row)
