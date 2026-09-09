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
#   - Resource viability of direct Fischler-Rivoal Proposition 1 for sin/cos.
# - Must-Not:
#   - Claim actual midpoint separation or required numerical precision.
# - Allows:
#   - Inputs: max-finite binary64 geometry and explicit theorem factors.
#   - Outputs: lower bound on the theorem guarantee's denominator exponent.
#   - Side effects: none.
# - Split-When:
#   - A stronger quantitative theorem replaces the direct exponential route.
# - Merge-When:
#   - Full-domain sin/cos table-maker resource proof subsumes theorem selection.
# - Summary:
#   - Rules out direct Proposition 1 as a finite guest resource proof.
# - Description:
#   - Uses only integer inequalities from the explicit degree-two
#     specialization.
# - Usage:
#   - Pure Python; no host transcendental arithmetic.
# - Defaults:
#   - Grants the theorem the entire uint32 byte addressable block as precision.
#

"""Resource-budget evidence for the explicit exponential sin/cos route."""

MAX_FINITE_SIGNIFICAND = (1 << 53) - 1
MAX_FINITE_POWER = 971
MINIMUM_P = 4
INPUT_DEGREE = 2
POLYNOMIAL_DEGREE = 2
S_LOG2_STRICT_LOWER = 1024
V_SQUARED_LOG2_STRICT_LOWER = 8192
DENOMINATOR_LOG2_BIT_LENGTH = 8207
MAX_GUEST_BYTES = (1 << 32) - 1


def test_direct_fischler_rivoal_sincos_bound_exceeds_guest_budget() -> None:
    """Rule out direct degree-two Proposition 1 as the finite resource proof."""
    # max-finite is the integer N=(2^53-1)*2^971. For alpha=i*N over Q(i),
    # d(1/alpha)=N and t=max(1,|1/alpha|)=1. Thus for every admissible
    # p>=d*delta=4, S=2*q*t >= 2*N > 2^1024.
    integer_input = MAX_FINITE_SIGNIFICAND << MAX_FINITE_POWER
    assert integer_input.bit_length() == S_LOG2_STRICT_LOWER
    assert 2 * integer_input > 1 << S_LOG2_STRICT_LOWER
    assert MINIMUM_P == INPUT_DEGREE * POLYNOMIAL_DEGREE

    # Proposition 1 has b=S^((p+1)*delta) and
    # v=e*b^(d/(p-d*delta+1)). Hence for every p>=4,
    # v^2>b^(4/(p-3))=S^(8*(p+1)/(p-3))>S^8>2^8192.
    assert V_SQUARED_LOG2_STRICT_LOWER == 8 * S_LOG2_STRICT_LOWER

    # Its denominator contains
    # (b^(d + delta*d^2/(p-d*delta+1)))^(1+v^2).
    # Dropping the positive second term in the base exponent gives
    # The resulting base-log lower bound exceeds 2^14 already at p=4.
    base_log2_lower = (
        INPUT_DEGREE
        * (MINIMUM_P + 1)
        * POLYNOMIAL_DEGREE
        * S_LOG2_STRICT_LOWER
    )
    assert base_log2_lower == 20 * S_LOG2_STRICT_LOWER
    assert base_log2_lower > 1 << 14

    theorem_log2_denominator_lower = (
        1 << V_SQUARED_LOG2_STRICT_LOWER
    ) * base_log2_lower
    assert theorem_log2_denominator_lower > 1 << 8206
    assert (
        theorem_log2_denominator_lower.bit_length()
        == DENOMINATOR_LOG2_BIT_LENGTH
    )

    # This comparison is deliberately favorable to the theorem: treat every bit
    # in the largest uint32-sized allocation as precision storage.
    guest_storage_bits = MAX_GUEST_BYTES * 8
    assert guest_storage_bits < 1 << 35
    assert theorem_log2_denominator_lower > guest_storage_bits
