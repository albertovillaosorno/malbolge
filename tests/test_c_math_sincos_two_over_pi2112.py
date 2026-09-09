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
#   - Q2112 two-over-pi table provenance and full-binary64 quotient certificate.
# - Must-Not:
#   - Use host pi/libm as numerical authority or claim final sin/cos rounding.
# - Allows:
#   - Inputs: the runtime's directed Q2112 table.
#   - Outputs: exact Machin table words plus Legendre separation evidence.
#   - Side effects: temporary native C compilation and execution only.
# - Split-When:
#   - Payne-Hanek quotient extraction needs independent algorithmic evidence.
# - Merge-When:
#   - A generated-constant pipeline subsumes this static-table provenance.
# - Summary:
#   - Proves the Q2112 reciprocal table is wide enough for every binary64 tie.
# - Description:
#   - Exact rational Machin bounds and continued fractions certify the margin.
# - Usage:
#   - Collected with repository-pinned native Clang on supported hosts.
# - Defaults:
#   - Full-domain reduction begins at magnitude 2^31; smaller inputs use Q256.
#

"""Q2112 two-over-pi table and full-domain quotient separation evidence."""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CONTRACT = ROOT / "src/runtime/guest-c-library/contract"
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
LIMBS = 66
FRACTION_BITS = 2112
DENOMINATOR_LIMIT_BITS = 1044
HALF_BOUNDARY_FACTOR = 20
ATAN5_TERMS = 1400
ATAN239_TERMS = 400
EXPECTED_CONVERGENTS = 626
RECIPROCAL_ULPS = 2


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
    x = Fraction(1, denominator)
    square = x * x
    term = x
    total = Fraction(0)
    for index in range(terms):
        contribution = term / (2 * index + 1)
        total = total + contribution if index % 2 == 0 else total - contribution
        term *= square
    omitted = term / (2 * terms + 1)
    if terms % 2 == 0:
        return total, total + omitted
    return total - omitted, total


def _pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_bounds(5, ATAN5_TERMS)
    a239_lo, a239_hi = _atan_bounds(239, ATAN239_TERMS)
    return 16 * a5_lo - 4 * a239_hi, 16 * a5_hi - 4 * a239_lo


def _continued_fraction(value: Fraction) -> Iterator[int]:
    numerator = value.numerator
    denominator = value.denominator
    while denominator:
        quotient, remainder = divmod(numerator, denominator)
        yield quotient
        numerator, denominator = denominator, remainder


def _common_cf(pi_lower: Fraction, pi_upper: Fraction) -> tuple[int, ...]:
    common: list[int] = []
    for lower_term, upper_term in zip(
        _continued_fraction(pi_lower),
        _continued_fraction(pi_upper),
        strict=False,
    ):
        if lower_term != upper_term:
            break
        common.append(lower_term)
    return tuple(common)


def _distance_from_interval(
    rational: Fraction,
    lower: Fraction,
    upper: Fraction,
) -> Fraction:
    if rational < lower:
        return lower - rational
    if rational > upper:
        return rational - upper
    return Fraction(0)


def _convergent_distance(
    terms: tuple[int, ...],
    pi_lower: Fraction,
    pi_upper: Fraction,
) -> tuple[Fraction, int]:
    limit = 1 << DENOMINATOR_LIMIT_BITS
    previous_num, numerator = 0, 1
    previous_den, denominator = 1, 0
    distances: list[Fraction] = []
    for term in terms:
        next_num = term * numerator + previous_num
        next_den = term * denominator + previous_den
        previous_num, numerator = numerator, next_num
        previous_den, denominator = denominator, next_den
        if denominator > limit:
            break
        rational = Fraction(numerator, denominator)
        distances.append(_distance_from_interval(rational, pi_lower, pi_upper))
    assert denominator > limit
    assert distances
    minimum = min(distances)
    assert minimum > 0
    return minimum, len(distances)


def _separation(pi_lower: Fraction, pi_upper: Fraction) -> tuple[Fraction, int]:
    limit = 1 << DENOMINATOR_LIMIT_BITS
    minimum, count = _convergent_distance(
        _common_cf(pi_lower, pi_upper),
        pi_lower,
        pi_upper,
    )
    legendre_floor = Fraction(1, 2 * limit * limit)
    return min(legendre_floor, minimum), count


def _expected_table() -> tuple[int, int]:
    pi_lower, pi_upper = _pi_bounds()
    scale = 1 << FRACTION_BITS
    pi_floor = pi_lower.numerator * scale // pi_lower.denominator
    assert pi_upper <= Fraction(pi_floor + 1, scale)
    reciprocal_lower = (2 * scale * scale) // (pi_floor + 1)
    reciprocal_upper = (2 * scale * scale + pi_floor - 1) // pi_floor
    return reciprocal_lower, reciprocal_upper


def _source() -> str:
    return r"""#include "math_transcendental_bits.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
int main(void) {
  MalbolgeGuestMathFixed2112Interval value;
  uint32_t index = UINT32_C(0);
  if (!malbolge_guest_math_two_over_pi_interval2112(&value)) return 80;
  while (index < MALBOLGE_GUEST_MATH_FIXED_2112_LIMBS) {
    (void)printf("%08" PRIx32 " %08" PRIx32 "\n",
                 value.lower.limbs[index], value.upper.limbs[index]);
    ++index;
  }
  if (malbolge_guest_math_two_over_pi_interval2112(0)) return 81;
  return 0;
}
"""


def _actual_table(tmp_path: Path) -> tuple[int, int]:
    source = tmp_path / "two-over-pi2112.c"
    binary = tmp_path / "two-over-pi2112"
    _ = source.write_text(_source(), encoding="utf-8")
    compiled = _run(
        [
            str(CLANG),
            "-std=c23",
            "-O2",
            "-ffreestanding",
            "-fno-builtin",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-Werror",
            f"-I{CONTRACT}",
            str(SOURCE),
            str(source),
            "-o",
            str(binary),
        ],
        ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    executed = _run([str(binary)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr
    rows = tuple(
        tuple(int(word, 16) for word in line.split())
        for line in executed.stdout.splitlines()
    )
    assert len(rows) == LIMBS
    lower = sum(row[0] << (32 * index) for index, row in enumerate(rows))
    upper = sum(row[1] << (32 * index) for index, row in enumerate(rows))
    return lower, upper


def _assert_full_domain_margin() -> None:
    pi_lower, pi_upper = _pi_bounds()
    separation, convergents = _separation(pi_lower, pi_upper)
    assert convergents == EXPECTED_CONVERGENTS
    # For |x| >= 2^31, p >= -21. The reduced denominator of 4*x/(2*q+1)
    # is therefore < 2^(1025+19) = 2^1044. Legendre says any closer rational
    # must be one of the certified convergents above. A relevant half-boundary
    # has 4*x/(2*q+1) < 5 and pi < 4, so the two-ulp reciprocal interval cannot
    # straddle it when 20*2^-2112 is below the certified separation.
    table_uncertainty = Fraction(HALF_BOUNDARY_FACTOR, 1 << FRACTION_BITS)
    assert table_uncertainty < separation


def test_q2112_table_matches_machin_and_proves_full_domain_margin(
    tmp_path: Path,
) -> None:
    """Regenerate all limbs and prove the binary64 half-boundary margin."""
    actual_lower, actual_upper = _actual_table(tmp_path)
    expected_lower, expected_upper = _expected_table()
    assert actual_lower == expected_lower
    assert actual_upper == expected_upper
    assert actual_upper - actual_lower == RECIPROCAL_ULPS
    _assert_full_domain_margin()
