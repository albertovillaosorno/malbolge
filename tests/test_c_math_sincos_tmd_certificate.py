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
#   - Finite binary64 sine/cosine TMD precision composition evidence.
# - Must-Not:
#   - Generalize the univariate result to atan2 or use host libm as authority.
# - Allows:
#   - Inputs: published TMD maxima and the source-owned CORE-MATH wc algorithm.
#   - Outputs: periodic near-zero and rounding-boundary precision ceilings.
#   - Side effects: none.
# - Split-When:
#   - Another floating format or bivariate function needs independent TMD data.
# - Merge-When:
#   - A generated external-certificate pipeline subsumes this finite proof.
# - Summary:
#   - Composes exhaustive binary64 TMD data with the Q256 runtime error bound.
# - Description:
#   - Reproduces closest-per-binade candidates with exact Machin arithmetic.
# - Usage:
#   - Collected by the pinned Python validation suite.
# - Defaults:
#   - External exhaustiveness is source-owned and snapshot-provenanced.
#

"""Finite Table Maker's Dilemma certificate for periodic sine and cosine."""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

SIN_MAX_IDENTICAL_BITS = 68
COS_MAX_IDENTICAL_BITS = 66
BINARY64_PRECISION = 53
PERIODIC_FIRST_BINADE = 3
PERIODIC_LAST_BINADE = 1024
SIGNIFICAND_MIN = 1 << 52
SIGNIFICAND_LIMIT = 1 << 53
Q256_FINAL_ULPS_MAX = 74
Q256_BITS = 256
ATAN5_TERMS = 1500
ATAN239_TERMS = 450
SIN_WORST_BITS = 0x7506AC5B262CA1FF
COS_WORST_BITS = 0x7516AC5B262CA1FF
PERIODIC_RESIDUAL_FLOOR_BITS = 61
OUTPUT_MAGNITUDE_FLOOR_BITS = 62
OUTPUT_ULP_FLOOR_BITS = 114
SIN_BOUNDARY_BITS = 184
COS_BOUNDARY_BITS = 182
Q256_WIDTH_BITS = 7
Q256_ERROR_BITS = 249
SIN_MARGIN_BITS = 65
COS_MARGIN_BITS = 67
SIN_PRECISION_BOUND_BITS = 123
COS_PRECISION_BOUND_BITS = 121


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


def _convergents(value: Fraction) -> Iterator[tuple[int, int]]:
    previous_num, numerator = 0, 1
    previous_den, denominator = 1, 0
    while value.denominator != 1:
        term = value.numerator // value.denominator
        next_num = term * numerator + previous_num
        next_den = term * denominator + previous_den
        yield next_num, next_den
        previous_num, numerator = numerator, next_num
        previous_den, denominator = denominator, next_den
        value = 1 / (value - term)


def _wc_candidate(
    exponent: int,
    parity: int,
    half_pi: Fraction,
) -> tuple[int, int] | None:
    scale = Fraction(
        1 << max(exponent - BINARY64_PRECISION, 0),
        1 << max(BINARY64_PRECISION - exponent, 0),
    )
    best = None
    for candidate_num, candidate_den in _convergents(scale / half_pi):
        numerator = candidate_num
        denominator = candidate_den
        while denominator < SIGNIFICAND_MIN:
            numerator *= 2
            denominator *= 2
        if numerator % 2 != parity:
            continue
        if denominator < SIGNIFICAND_LIMIT:
            best = (numerator, denominator)
        else:
            break
    return best


def _absolute_residual_lower(
    exponent: int,
    multiple: int,
    significand: int,
    *,
    pi_bounds: tuple[Fraction, Fraction],
) -> Fraction:
    pi_lower, pi_upper = pi_bounds
    scale = Fraction(
        1 << max(exponent - BINARY64_PRECISION, 0),
        1 << max(BINARY64_PRECISION - exponent, 0),
    )
    value = significand * scale
    lower = value - multiple * pi_upper / 2
    upper = value - multiple * pi_lower / 2
    if lower > 0:
        return lower
    if upper < 0:
        return -upper
    return Fraction(0)


def test_core_math_wc_reproduction_keeps_periodic_outputs_away_from_zero(
) -> None:
    """Reproduce the source-owned closest-per-binade construction."""
    pi_lower, pi_upper = _pi_bounds()
    half_pi = (pi_lower + pi_upper) / 4
    minimum: Fraction | None = None
    witnesses: set[int] = set()
    for exponent in range(PERIODIC_FIRST_BINADE, PERIODIC_LAST_BINADE + 1):
        for parity in (0, 1):
            candidate = _wc_candidate(exponent, parity, half_pi)
            if candidate is None:
                continue
            multiple, significand = candidate
            residual = _absolute_residual_lower(
                exponent,
                multiple,
                significand,
                pi_bounds=(pi_lower, pi_upper),
            )
            assert residual > 0
            if minimum is None or residual < minimum:
                minimum = residual
            raw_exponent = exponent - 1 + 1023
            witnesses.add(
                (raw_exponent << 52) | (significand - SIGNIFICAND_MIN)
            )
    assert minimum is not None
    assert minimum > Fraction(1, 1 << PERIODIC_RESIDUAL_FLOOR_BITS)
    assert SIN_WORST_BITS in witnesses
    assert COS_WORST_BITS in witnesses


def test_exhaustive_tmd_bound_dominates_q256_periodic_error() -> None:
    """Translate published m maxima to absolute periodic boundary margins."""
    # CORE-MATH's closest-per-binade result gives |r| > 2^-61. On the reduced
    # interval |r| <= pi/4, |sin(r)| > |r|/2, hence a near-zero periodic result
    # has magnitude > 2^-62 and therefore binary64 ulp >= 2^-114.
    assert OUTPUT_MAGNITUDE_FLOOR_BITS == PERIODIC_RESIDUAL_FLOOR_BITS + 1
    assert OUTPUT_ULP_FLOOR_BITS == OUTPUT_MAGNITUDE_FLOOR_BITS + 52
    sin_boundary_bits = SIN_MAX_IDENTICAL_BITS + 2 + OUTPUT_ULP_FLOOR_BITS
    cos_boundary_bits = COS_MAX_IDENTICAL_BITS + 2 + OUTPUT_ULP_FLOOR_BITS
    assert sin_boundary_bits == SIN_BOUNDARY_BITS
    assert cos_boundary_bits == COS_BOUNDARY_BITS
    # The directed Q256/32 interval is at most 74 cells: 74 < 2^7, so its
    # absolute width is <2^-249, at least 65 bits below the sine boundary floor.
    q256_error_bits = Q256_BITS - Q256_WIDTH_BITS
    assert Q256_FINAL_ULPS_MAX < 1 << Q256_WIDTH_BITS
    assert q256_error_bits == Q256_ERROR_BITS
    assert q256_error_bits - sin_boundary_bits >= SIN_MARGIN_BITS
    assert q256_error_bits - cos_boundary_bits >= COS_MARGIN_BITS
    assert (
        BINARY64_PRECISION + SIN_MAX_IDENTICAL_BITS + 2
        == SIN_PRECISION_BOUND_BITS
    )
    assert (
        BINARY64_PRECISION + COS_MAX_IDENTICAL_BITS + 2
        == COS_PRECISION_BOUND_BITS
    )
