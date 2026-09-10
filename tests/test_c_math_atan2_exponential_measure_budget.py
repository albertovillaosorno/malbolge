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
#   - Resource viability of the direct Fischler-Rivoal Proposition 1 atan2
#     bridge.
# - Must-Not:
#   - Claim actual midpoint separation or a lower bound on required precision.
# - Allows:
#   - Inputs: one retained deep kernel cell and the explicit theorem factors.
#   - Outputs: a conservative lower bound on the theorem denominator exponent.
#   - Side effects: none.
# - Split-When:
#   - A stronger quantitative theorem replaces the direct exponential route.
# - Merge-When:
#   - Full-domain atan2 resource proof subsumes theorem-selection evidence.
# - Summary:
#   - Shows direct Proposition 1 is too weak for the finite guest scratch
#     ceiling.
# - Description:
#   - Exact Fraction geometry pins 2*q*t at 2^107 for both retained cell edges.
# - Usage:
#   - Pure Python integer/rational proof; no host transcendental arithmetic.
# - Defaults:
#   - The comparison grants the theorem the entire maximum guest block as bits.
#

"""Resource-budget evidence for the explicit exponential atan2 route."""

from __future__ import annotations

from fractions import Fraction

SIGN_BIT = 1 << 63
MAGNITUDE_MASK = SIGN_BIT - 1
FRACTION_MASK = (1 << 52) - 1
HIDDEN_BIT = 1 << 52
EXPONENT_MASK = 0x7FF
DEEP_CANDIDATE = 0x3CA8000000000000
NORMALIZED_MAX_GUEST_BYTES = 0xFFFFFFC0
THEOREM_LOG2_DENOMINATOR_BIT_LENGTH = 438
EHLM_MIN_EXPONENTIAL_COUNT = 2
EHLM_ALPHA_DENOMINATOR_SHIFT = 105
EHLM_LOG_GAMMA_BASE2_LOWER = 34020


def _binary64_fraction(bits: int) -> Fraction:
    negative = bool(bits & SIGN_BIT)
    magnitude = bits & MAGNITUDE_MASK
    raw_exponent = (magnitude >> 52) & EXPONENT_MASK
    fraction = magnitude & FRACTION_MASK
    assert raw_exponent != EXPONENT_MASK
    if raw_exponent == 0:
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = HIDDEN_BIT | fraction
        shift = raw_exponent - 1023 - 52
        value = (
            Fraction(significand << shift, 1)
            if shift >= 0
            else Fraction(significand, 1 << -shift)
        )
    return -value if negative else value


def _cell_midpoints(candidate: int) -> tuple[Fraction, Fraction]:
    value = _binary64_fraction(candidate)
    lower = (_binary64_fraction(candidate - 1) + value) / 2
    upper = (value + _binary64_fraction(candidate + 1)) / 2
    return lower, upper


def _p2_two_q_t(midpoint: Fraction) -> int:
    alpha = 2 * abs(midpoint)
    assert alpha.denominator & (alpha.denominator - 1) == 0
    inverse_denominator = alpha.numerator
    inverse_house = max(
        Fraction(1), Fraction(alpha.denominator, alpha.numerator)
    )
    # Proposition 1 has q=lcm(1,2)*d(1/alpha)=2*d(1/alpha).
    two_q_t = 4 * inverse_denominator * inverse_house
    assert two_q_t.denominator == 1
    return two_q_t.numerator


def test_direct_fischler_rivoal_bound_exceeds_guest_resource_budget() -> None:
    """Rule out direct Proposition 1 as the finite guest resource proof."""
    lower, upper = _cell_midpoints(DEEP_CANDIDATE)
    assert _p2_two_q_t(lower) == 1 << 107
    assert _p2_two_q_t(upper) == 1 << 107

    # For d=2, delta=1 and every p>=2, let S=2*q*t. Proposition 1 has
    # b=S^(p+1), v=e*b^(2/(p-1)), and a denominator factor
    # (b^(2+4/(p-1)))^(1+v^2). Since S>=2^107, p+1>=3,
    # v^2>b^(4/(p-1))>=S^4, and 2+4/(p-1)>2, its base-2
    # logarithm is strictly greater than 6*107*2^428 for every p.
    theorem_log2_denominator_lower = 6 * 107 * (1 << 428)
    assert (
        theorem_log2_denominator_lower.bit_length()
        == THEOREM_LOG2_DENOMINATOR_BIT_LENGTH
    )
    assert theorem_log2_denominator_lower > 1 << 437

    # Give the theorem the entire largest representable guest allocation as
    # precision storage. It is still more than 2^402 times too small in the
    # exponent-budget comparison; actual separation may of course be larger.
    guest_storage_bits = NORMALIZED_MAX_GUEST_BYTES * 8
    assert guest_storage_bits < 1 << 35
    assert theorem_log2_denominator_lower > guest_storage_bits


def test_imaginary_quadratic_baker_threshold_exceeds_guest_budget() -> None:
    """Reject the published m>=2 Baker threshold for the deep guest cell."""
    lower, upper = _cell_midpoints(DEEP_CANDIDATE)
    for midpoint in (lower, upper):
        alpha = 2 * abs(midpoint)
        assert alpha.denominator == 1 << EHLM_ALPHA_DENOMINATOR_SHIFT

    # Pad the guest two-term form with a distinct exponential whose coefficient
    # is zero. Theorem 2.1 permits zero coefficients but requires m>=2. Its
    # g2 is at least the denominator 2^105 of alpha=2im. Since
    # e0 >= 3*sqrt(log(g2)) and log(gamma)=(3*m*e0)^2,
    # log(gamma) >= 81*m^2*105*log(2) = 34020*log(2).
    m = EHLM_MIN_EXPONENTIAL_COUNT
    log_gamma_base2_lower = 81 * m * m * EHLM_ALPHA_DENOMINATOR_SHIFT
    assert log_gamma_base2_lower == EHLM_LOG_GAMMA_BASE2_LOWER

    # H0 >= exp(gamma*log(gamma)/2). From gamma>=2^34020,
    # log2(H0) >= 17010*2^34020, so even the threshold factor alone
    # requires enormously more separation bits than one guest allocation.
    log2_h0_lower = (log_gamma_base2_lower // 2) << log_gamma_base2_lower
    guest_storage_bits = NORMALIZED_MAX_GUEST_BYTES * 8
    assert log2_h0_lower > 1 << EHLM_LOG_GAMMA_BASE2_LOWER
    assert guest_storage_bits < 1 << 35
    assert log2_h0_lower > guest_storage_bits
