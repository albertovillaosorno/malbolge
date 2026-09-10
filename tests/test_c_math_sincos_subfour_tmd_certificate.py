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
#   - Finite sub-four binary64 sine/cosine TMD resource composition evidence.
# - Must-Not:
#   - Generalize the univariate certificate to atan2 or use host libm.
# - Allows:
#   - Inputs: global TMD maxima, exact binary64 cells, and Machin pi bounds.
#   - Outputs: a fixed Q512/64 sub-four correct-rounding precision ceiling.
# - Side effects: none.
# - Split-When:
#   - Another format or function needs an independent hard-case certificate.
# - Merge-When:
#   - One full-domain sin/cos proof owns periodic and sub-four budgets together.
# - Summary:
#   - Proves the Q512 direct-Taylor interval beats every sub-four TMD boundary.
# - Description:
#   - Bounds zeros at pi and pi/2, Taylor remainder, and directed roundoff.
# - Usage:
#   - Collected by the pinned Python validation suite.
# - Defaults:
#   - The external TMD maxima remain source-owned exhaustive finite evidence.
#

"""Sub-four binary64 sine/cosine Table Maker's Dilemma certificate."""

from __future__ import annotations

from fractions import Fraction

SIN_MAX_IDENTICAL_BITS = 68
COS_MAX_IDENTICAL_BITS = 66
Q512_BITS = 512
POLICY_TERMS = 64
SIN_ROUNDOFF_ULPS = 135
COS_ROUNDOFF_ULPS = 139
WIDTH_ULP_BITS_MAX = 52
SIN_CUTOFF_BITS = 0x3E57000000000000
PI_BITS = 0x400921FB54442D18
HALF_PI_BITS = 0x3FF921FB54442D18
FRACTION_MASK = (1 << 52) - 1
HIDDEN = 1 << 52
EXPONENT_BIAS = 1023
ATAN5_TERMS = 180
ATAN239_TERMS = 60


def _factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent, 1)
    return Fraction(1, 1 << -exponent)


def _binary64(bits: int) -> Fraction:
    raw_exponent = (bits >> 52) & 0x7FF
    significand = HIDDEN | (bits & FRACTION_MASK)
    return Fraction(significand) * _pow2(raw_exponent - EXPONENT_BIAS - 52)


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
    return (total, total + omitted) if terms % 2 == 0 else (
        total - omitted,
        total,
    )


def _pi_bounds() -> tuple[Fraction, Fraction]:
    a5_lo, a5_hi = _atan_bounds(5, ATAN5_TERMS)
    a239_lo, a239_hi = _atan_bounds(239, ATAN239_TERMS)
    return 16 * a5_lo - 4 * a239_hi, 16 * a5_hi - 4 * a239_lo


def _ceil_fraction(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    return quotient + int(remainder != 0)


def _divide_width(width: int, divisor: int) -> int:
    return _ceil_fraction(Fraction(width, divisor) + 2) - 1


def _roundoff_widths(*, cosine: bool) -> tuple[int, ...]:
    widths = [0]
    for index in range(1, POLICY_TERMS + 1):
        prior_power = 2 * (index - 1) if cosine else 2 * (index - 1) + 1
        prior_magnitude = Fraction(
            1 << (2 * prior_power),
            _factorial(prior_power),
        )
        product_width = 16 * widths[-1] + _ceil_fraction(prior_magnitude) + 2
        left = 2 * index - 1 if cosine else 2 * index
        right = 2 * index if cosine else 2 * index + 1
        widths.append(
            _divide_width(_divide_width(product_width, left), right),
        )
    return tuple(widths)


def test_q512_64_subfour_interval_has_fixed_absolute_width_ceiling() -> None:
    """Bound directed roundoff plus the first omitted alternating term."""
    sin_widths = _roundoff_widths(cosine=False)
    cos_widths = _roundoff_widths(cosine=True)
    assert sum(sin_widths[:POLICY_TERMS]) + sin_widths[POLICY_TERMS] == 135
    assert sum(cos_widths[:POLICY_TERMS]) + cos_widths[POLICY_TERMS] == 139
    assert SIN_ROUNDOFF_ULPS == 135
    assert COS_ROUNDOFF_ULPS == 139

    q512_ulp = Fraction(1, 1 << Q512_BITS)
    sin_tail = Fraction(1 << (2 * 129), _factorial(129))
    cos_tail = Fraction(1 << (2 * 128), _factorial(128))
    assert sin_tail + SIN_ROUNDOFF_ULPS * q512_ulp < Fraction(1, 1 << 465)
    assert cos_tail + COS_ROUNDOFF_ULPS * q512_ulp < Fraction(1, 1 << 460)
    assert WIDTH_ULP_BITS_MAX == Q512_BITS - 460


def test_subfour_zero_separation_and_global_tmd_leave_large_margin() -> None:
    """Compose binary64 distance-to-zero geometry with global TMD maxima."""
    pi_lower, pi_upper = _pi_bounds()
    pi_value = _binary64(PI_BITS)
    half_pi_value = _binary64(HALF_PI_BITS)
    assert pi_value < pi_lower
    assert half_pi_value < pi_lower / 2
    assert pi_lower - pi_value > Fraction(1, 1 << 53)
    assert pi_lower / 2 - half_pi_value > Fraction(1, 1 << 54)
    assert _binary64(SIN_CUTOFF_BITS) > Fraction(1, 1 << 27)

    # For sine, the only positive zeros below four are 0 and pi. The nearest
    # binary64 input to pi is still more than 2^-53 away. For cosine, pi/2 is
    # the only zero below four and the nearest input is more than 2^-54 away.
    # On a distance below one, |sin(r)| > |r|/2 by r-r^3/6. Farther from the
    # cosine zero the magnitude is vastly larger, so 2^-55 is a shared floor.
    assert (pi_upper / 2) ** 2 < 3
    assert pi_lower - Fraction(5, 2) > Fraction(1, 2)
    output_magnitude_floor_bits = 55
    output_ulp_floor_bits = output_magnitude_floor_bits + 52
    assert output_ulp_floor_bits == 107

    sin_boundary_bits = output_ulp_floor_bits + SIN_MAX_IDENTICAL_BITS + 2
    cos_boundary_bits = output_ulp_floor_bits + COS_MAX_IDENTICAL_BITS + 2
    assert sin_boundary_bits == 177
    assert cos_boundary_bits == 175
    q512_error_bits = Q512_BITS - WIDTH_ULP_BITS_MAX
    assert q512_error_bits == 460
    assert q512_error_bits - sin_boundary_bits >= 283
    assert q512_error_bits - cos_boundary_bits >= 285
