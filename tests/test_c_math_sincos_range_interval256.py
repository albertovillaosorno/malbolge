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
#   - Directed Q256 sin/cos evaluation after bounded periodic reduction.
# - Must-Not:
#   - Use host trigonometric functions or rounded pi as authority.
#   - Treat bounded Q256 success as a full-domain rounding proof.
# - Allows:
#   - Inputs: retained finite binary64 values with 4 <= |x| < 2^31.
#   - Outputs: independent Fraction enclosure checks for both sin and cos.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Final binary64 publication needs a separate unique-rounding gate.
# - Merge-When:
#   - A full range-reduced handoff subsumes this interval-only boundary.
# - Summary:
#   - Checks residual Taylor and quadrant transport against rational authority.
# - Description:
#   - Machin bounds pi; 40-term alternating series bounds reduced sin/cos.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Exercises exact neighbors of selected pi/2 multiples in both signs.
#

"""Independent rational authority for bounded Q256 sin/cos intervals."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import struct
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SCALE = 1 << 256
SIGN = 1 << 63
MAGNITUDE = SIGN - 1
EXPONENT_MASK = 0x7FF
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
FOUR = 0x4010000000000000
TWO31 = 0x41E0000000000000
MAX_FINITE = 0x7FEFFFFFFFFFFFFF
TERMS = 40
QUADRANT_TWO = 2


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


def _atan_bounds(denominator: int, terms: int) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    x = Fraction(1, denominator)
    square = x * x
    term = x
    for index in range(terms):
        contribution = term / (2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / (2 * terms + 1)
    if terms % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _quarter_pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_bounds(5, 90)
    a239_lo, a239_hi = _atan_bounds(239, 30)
    return 4 * a5_lo - a239_hi, 4 * a5_hi - a239_lo


def _binary64(bits: int) -> Fraction:
    negative = bool(bits & SIGN)
    magnitude = bits & MAGNITUDE
    exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert exponent != EXPONENT_MASK
    if exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN | fraction
        power = exponent - 1023 - 52
        value = (
            Fraction(significand << power, 1)
            if power >= 0
            else Fraction(significand, 1 << -power)
        )
    return -value if negative else value


def _nearest_bits(value: Fraction) -> int:
    proposal = int.from_bytes(struct.pack(">d", float(value)), "big")
    choices = [proposal]
    if proposal > 0:
        choices.append(proposal - 1)
    if proposal < MAX_FINITE:
        choices.append(proposal + 1)
    ranked = tuple((abs(_binary64(bits) - value), bits) for bits in choices)
    distance = min(delta for delta, _ in ranked)
    tied = tuple(bits for delta, bits in ranked if delta == distance)
    return min(tied, key=lambda bits: bits & 1)


def _nearest_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder * 2
    if twice > value.denominator or (
        twice == value.denominator and bool(quotient & 1)
    ):
        quotient += 1
    return quotient


def _sin_bounds_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    square = value * value
    term = value
    for index in range(TERMS):
        contribution = term / _factorial(2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * TERMS + 1)
    if TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _cos_bounds_positive(value: Fraction) -> tuple[Fraction, Fraction]:
    total = Fraction(0)
    square = value * value
    term = Fraction(1)
    for index in range(TERMS):
        contribution = term / _factorial(2 * index)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / _factorial(2 * TERMS)
    if TERMS % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _sin_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    if value >= 0:
        return _sin_bounds_positive(value)
    lower, upper = _sin_bounds_positive(-value)
    return -upper, -lower


def _cos_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    return _cos_bounds_positive(abs(value))


def _residual_bounds(bits: int) -> tuple[int, Fraction, Fraction]:
    quarter_lo, quarter_hi = _quarter_pi_bounds()
    half_lo = 2 * quarter_lo
    half_hi = 2 * quarter_hi
    x = abs(_binary64(bits))
    q_lo = _nearest_integer(x / half_hi)
    q_hi = _nearest_integer(x / half_lo)
    assert q_lo == q_hi
    return q_lo, x - q_lo * half_hi, x - q_lo * half_lo


def _residual_trig(
    residual_lo: Fraction,
    residual_hi: Fraction,
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    sin_interval = (_sin_bounds(residual_lo)[0], _sin_bounds(residual_hi)[1])
    lower_is_larger = abs(residual_lo) >= abs(residual_hi)
    largest = residual_lo if lower_is_larger else residual_hi
    smallest = residual_hi if lower_is_larger else residual_lo
    cos_lower = _cos_bounds(largest)[0]
    cos_upper = (
        Fraction(1)
        if residual_lo <= 0 <= residual_hi
        else _cos_bounds(smallest)[1]
    )
    return sin_interval, (cos_lower, cos_upper)


def _rotate(
    multiple: int,
    sin_interval: tuple[Fraction, Fraction],
    cos_interval: tuple[Fraction, Fraction],
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    quadrant = multiple & 3
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


def _reduced_trig(bits: int) -> tuple[tuple[Fraction, Fraction], ...]:
    multiple, residual_lo, residual_hi = _residual_bounds(bits)
    sin_interval, cos_interval = _residual_trig(residual_lo, residual_hi)
    sin_out, cos_out = _rotate(multiple, sin_interval, cos_interval)
    if bits & SIGN:
        sin_out = (-sin_out[1], -sin_out[0])
    return sin_out, cos_out


def _cases() -> tuple[int, ...]:
    quarter_lo, quarter_hi = _quarter_pi_bounds()
    half_mid = quarter_lo + quarter_hi
    rows: set[int] = {FOUR, FOUR + 1, TWO31 - 1}
    for multiple in (3, 4, 5, 7, 17, 1000, 1_000_000, 1_000_000_000):
        center = _nearest_bits(multiple * half_mid)
        for delta in (-2, -1, 0, 1, 2):
            magnitude = center + delta
            if FOUR <= magnitude < TWO31:
                rows.add(magnitude)
                rows.add(magnitude | SIGN)
    return tuple(sorted(rows))


CASES = _cases()


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
    MalbolgeGuestMathSincosInterval256 out;
    if (!malbolge_guest_math_sincos_range_interval256(
            cases[index], UINT32_C(24), &out, scratch, UINT32_C(90))) return 80;
    (void)printf("%016" PRIx64 " %u ", cases[index], out.sin.lower_negative);
    print_fixed(&out.sin.lower); (void)printf(" %u ", out.sin.upper_negative);
    print_fixed(&out.sin.upper); (void)printf(" %u ", out.cos.lower_negative);
    print_fixed(&out.cos.lower); (void)printf(" %u ", out.cos.upper_negative);
    print_fixed(&out.cos.upper); (void)printf("\\n");
    ++index;
  }}
  return 0;
}}
"""


def _run_records(tmp_path: Path) -> tuple[tuple[str, ...], ...]:
    harness = tmp_path / "range-interval.c"
    executable = tmp_path / "range-interval"
    _ = harness.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG), "-std=c23", "-O2", "-ffreestanding", "-fno-builtin",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", f"-I{CONTRACT}",
            str(SOURCE), str(harness), "-o", str(executable),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    return tuple(tuple(line.split()) for line in executed.stdout.splitlines())


def _signed_fixed(magnitude: str, negative: str) -> Fraction:
    value = Fraction(int(magnitude, 16), SCALE)
    return -value if int(negative) else value


def test_range_interval256_encloses_independent_fraction_authority(
    tmp_path: Path,
) -> None:
    """Enclose reduced sin/cos after independent Machin/Taylor transport."""
    records = _run_records(tmp_path)
    assert len(records) == len(CASES)
    for bits, row in zip(CASES, records, strict=True):
        assert int(row[0], 16) == bits
        sin_expected, cos_expected = _reduced_trig(bits)
        sin_lower = _signed_fixed(row[2], row[1])
        sin_upper = _signed_fixed(row[4], row[3])
        cos_lower = _signed_fixed(row[6], row[5])
        cos_upper = _signed_fixed(row[8], row[7])
        assert sin_lower <= sin_expected[0] <= sin_expected[1] <= sin_upper
        assert cos_lower <= cos_expected[0] <= cos_expected[1] <= cos_upper
