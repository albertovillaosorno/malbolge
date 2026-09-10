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
NW_LOG_A = 109
NW_LOG_B = 107
NW_FIRST_FACTOR_UPPER = 134
NW_SECOND_FACTOR_UPPER = 272
NW_THIRD_FACTOR_UPPER = 11
NW_NATURAL_EXPONENT_UPPER = 169_191_616
NW_BINARY_EXPONENT_UPPER = 338_383_232
NW_STAGE_MARGIN_BITS = 512
NW_DIRECT_STAGE = 10_574_490
NW_DIRECT_FRACTION_BITS = 338_383_744
NW_DIRECT_TERMS = 42_297_968
NW_DIRECT_SCRATCH_BYTES = 634_469_580
NW_REQUIRED_GUARD_BITS = 140
NW_FIELD_DEGREE = 2
NW_MAIN_THEOREM_CONSTANT = 211
NW_RATIO_NUMERATOR_BITS_MAX = 108
NW_RATIO_DENOMINATOR_BITS_MAX = 106
NW_THIRD_FACTOR_FLOOR = 10


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


def test_nesterenko_waldschmidt_bound_fits_direct_refinement_budget() -> None:
    """Place the explicit exponential separation inside guest capacity."""
    # For t=a/b with bitlen(a)<=108 and bitlen(b)<=106, the target
    # alpha=-(a-ib)/(a+ib) has both conjugates on the unit circle and a
    # primitive quadratic leading coefficient no larger than a^2+b^2<2^217.
    # Thus h(alpha)<109 because log(2)<1.  For beta=2*i*m, a midpoint shift
    # <=107 gives h(beta)<107.  Hence log(A)=109 and log(B)=107 are valid.
    assert NW_LOG_A > NW_RATIO_NUMERATOR_BITS_MAX
    assert NW_LOG_B > NW_RATIO_DENOMINATOR_BITS_MAX

    # Use E=e.  The elementary series gives e>2.7, hence log(109)<5,
    # log(2)<0.7, log(4)<1.4, and log(e*8)<4; also e<3.
    assert 27**7 > (2**10) * (10**7)
    assert NW_FIRST_FACTOR_UPPER == NW_LOG_B + 5 + 4 + 8 + 10
    assert NW_SECOND_FACTOR_UPPER == NW_FIELD_DEGREE * NW_LOG_A + 48 + 6
    assert NW_THIRD_FACTOR_UPPER > NW_THIRD_FACTOR_FLOOR
    natural_exponent = (
        NW_MAIN_THEOREM_CONSTANT
        * NW_FIELD_DEGREE
        * NW_FIRST_FACTOR_UPPER
        * NW_SECOND_FACTOR_UPPER
        * NW_THIRD_FACTOR_UPPER
    )
    assert natural_exponent == NW_NATURAL_EXPONENT_UPPER

    # log(2)>1/2 follows from integral_1^2 dx/x > 1/2.  Therefore an
    # exp(-C) lower bound is stronger than 2^(-2C).
    assert 2 * natural_exponent == NW_BINARY_EXPONENT_UPPER

    # The direct scheduler has P=32*(stage+2), T=4*stage+8=P/8.  At |m|<4,
    # exact Taylor terms are below 11.  Directed multiplication/division gives
    # <=16 QP ulps of width per retained term under a conservative interval
    # recurrence, so the complete Taylor enclosure is <(16*T+17) ulps.  The
    # selected T is large enough that the omitted term is below one QP ulp.
    stage = NW_DIRECT_STAGE
    fraction_bits = 32 * (stage + 2)
    terms = 4 * stage + 8
    assert fraction_bits == NW_DIRECT_FRACTION_BITS
    assert terms == NW_DIRECT_TERMS == fraction_bits // 8
    assert terms >= 1 << 16
    assert 16 * terms + 17 < 1 << 30

    # Both reduced cross-product coefficients sum to <2^109.  Thus the final
    # comparator uncertainty is <2^139 QP ulps.  The exponential identity gives
    # |a*cos(m)-b*sin(m)| > 2^-(B+1), leaving far more than the required 140
    # guard bits.  The same theorem with alpha=+/-1 proves the sin/cos signs.
    assert fraction_bits - NW_BINARY_EXPONENT_UPPER == NW_STAGE_MARGIN_BITS
    assert NW_STAGE_MARGIN_BITS > NW_REQUIRED_GUARD_BITS

    scratch_limbs = 15 * (stage + 3)
    scratch_bytes = 4 * scratch_limbs
    assert scratch_bytes == NW_DIRECT_SCRATCH_BYTES
    assert scratch_bytes < NORMALIZED_MAX_GUEST_BYTES
