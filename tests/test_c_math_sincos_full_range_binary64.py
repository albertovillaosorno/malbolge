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
#   - Composition of certified Payne-Hanek residuals through Q256 final bits.
# - Must-Not:
#   - Recompute pi, use host trig, or claim Q256 suffices for every input.
# - Allows:
#   - Inputs: retained finite binary64 words from 2^64 through max-finite.
#   - Outputs: rational-Taylor binary64 checks over the whole residual interval.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Adaptive post-reduction refinement replaces the fixed Q256 gate.
# - Merge-When:
#   - A public full-domain sin/cos availability test subsumes this evidence.
# - Summary:
#   - Proves retained Payne-Hanek residuals round to the published bits.
# - Description:
#   - Exact Q256 residual endpoints feed independent rational Taylor bounds.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Q256 ambiguity remains a nonpublishing failure outside retained evidence.
#

"""Compose Payne-Hanek residual authority through final binary64 bits."""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SCALE = 1 << 256
SIGN = 1 << 63
FRACTION_MASK = (1 << 52) - 1
EXPONENT_BIAS = 1023
TRIG_TERMS = 40
SIN = 1
COS = 2
QUADRANT_TWO = 2
CASES = (
    0x43F0000000000000,
    0x43F0000000000001,
    0x44C123456789ABCD,
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


def _sin_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = value
    total = Fraction(0)
    for index in range(TRIG_TERMS):
        contribution = term / _factorial(2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * TRIG_TERMS + 1)
    if TRIG_TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _cos_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    square = value * value
    term = Fraction(1)
    total = Fraction(0)
    for index in range(TRIG_TERMS):
        contribution = term / _factorial(2 * index)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * TRIG_TERMS)
    if TRIG_TERMS % 2 == 0:
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
    twice = 2 * remainder
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


def _expected_from_residual(row: tuple[str, ...]) -> tuple[int, int]:
    quadrant = int(row[1])
    input_negative = bool(int(row[2]))
    residual_lower = _signed_fixed(row[4], row[3])
    residual_upper = _signed_fixed(row[6], row[5])
    sin_interval, cos_interval = _residual_trig(residual_lower, residual_upper)
    sin_out, cos_out = _rotate(quadrant, sin_interval, cos_interval)
    if input_negative:
        sin_out = (-sin_out[1], -sin_out[0])
    sin_bits = {_binary64_bits(value) for value in sin_out}
    cos_bits = {_binary64_bits(value) for value in cos_out}
    assert len(sin_bits) == 1
    assert len(cos_bits) == 1
    return sin_bits.pop(), cos_bits.pop()


def _source() -> str:
    rows = ",\n".join(f"  UINT64_C(0x{bits:016x})" for bits in CASES)
    return f"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
static const uint64_t cases[] = {{
{rows}
}};
static void print_fixed(const MalbolgeGuestMathFixed256 *value) {{
  uint32_t limb = MALBOLGE_GUEST_MATH_FIXED_256_LIMBS;
  while (limb != UINT32_C(0)) {{
    --limb;
    (void)printf("%08x", value->limbs[limb]);
  }}
}}
int main(void) {{
  uint32_t scratch[90];
  uint32_t index = UINT32_C(0);
  while (index < (uint32_t)(sizeof(cases) / sizeof(cases[0]))) {{
    MalbolgeGuestMathSincosPayneHanek256 reduced;
    uint64_t sin_bits = UINT64_C(0), cos_bits = UINT64_C(0);
    if (!malbolge_guest_math_sincos_payne_hanek_reduce256(
            cases[index], &reduced) ||
        !malbolge_guest_math_sincos_range_unique_binary64(
            MALBOLGE_GUEST_MATH_SIN, cases[index], &sin_bits,
            scratch, UINT32_C(90)) ||
        !malbolge_guest_math_sincos_range_unique_binary64(
            MALBOLGE_GUEST_MATH_COS, cases[index], &cos_bits,
            scratch, UINT32_C(90))) return 80;
    (void)printf("%016" PRIx64 " %u %u %u ", cases[index],
                 reduced.quadrant, reduced.input_negative,
                 reduced.residual_lower_negative);
    print_fixed(&reduced.residual_lower);
    (void)printf(" %u ", reduced.residual_upper_negative);
    print_fixed(&reduced.residual_upper);
    (void)printf(" %016" PRIx64 " %016" PRIx64 "\\n", sin_bits, cos_bits);
    ++index;
  }}
  return 0;
}}
"""


def test_full_range_binary64_rounds_whole_certified_residual(
    tmp_path: Path,
) -> None:
    """Round the full certified Payne-Hanek residual interval to final bits."""
    source = tmp_path / "full-range-binary64.c"
    binary = tmp_path / "full-range-binary64"
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
    records = tuple(
        tuple(line.split()) for line in executed.stdout.splitlines()
    )
    assert len(records) == len(CASES)
    for bits, row in zip(CASES, records, strict=True):
        assert int(row[0], 16) == bits
        expected_sin, expected_cos = _expected_from_residual(row)
        assert int(row[7], 16) == expected_sin
        assert int(row[8], 16) == expected_cos
