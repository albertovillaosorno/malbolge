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
#   - Independent proof checks for conservative transcendental exact cases.
# - Must-Not:
#   - Use host sin, cos, or atan2 as expected-value authority.
# - Allows:
#   - Inputs: exact rational threshold geometry and tracked raw-bit constants.
#   - Outputs: proof that admitted small-angle rounding margins are sufficient.
#   - Side effects: none.
# - Split-When:
#   - Numerical kernels require approximation-error or range-reduction proofs.
# - Merge-When:
#   - Complete transcendental proof evidence subsumes these exact edge checks.
# - Summary:
#   - Proves the binary64 2^-27 sin/cos exact-result preclassification margin.
# - Description:
#   - Uses rational Taylor bounds and binary64 midpoint spacing only.
# - Usage:
#   - Runs with the guest-libc transcendental preclassification regression lane.
# - Defaults:
#   - No host libm result is accepted as a semantic oracle.
#

"""Exact proof checks for conservative transcendental preclassification."""

from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/runtime/guest-c-library/domain/math_transcendental_bits.c"
SMALL_ANGLE_MAX_BITS = 0x3E40000000000000
SMALL_ANGLE = Fraction(1, 1 << 27)
SIN_TOWARD_ZERO_MIDPOINT = SMALL_ANGLE / (1 << 54)
COS_ONE_MIDPOINT = Fraction(1, 1 << 54)
MAX_SUBNORMAL_MAGNITUDE = Fraction((1 << 52) - 1, 1 << 1074)
SUBNORMAL_MIDPOINT = Fraction(1, 1 << 1075)
EXPECTED_CONSTANTS = {
    "BINARY64_SMALL_ANGLE_MAX": SMALL_ANGLE_MAX_BITS,
    "BINARY64_PI_OVER_FOUR": 0x3FE921FB54442D18,
    "BINARY64_PI_OVER_TWO": 0x3FF921FB54442D18,
    "BINARY64_PI": 0x400921FB54442D18,
    "BINARY64_THREE_PI_OVER_FOUR": 0x4002D97C7F3321D2,
}


def test_small_angle_taylor_bounds_fit_binary64_midpoints() -> None:
    """Keep the conservative sin/cos exact-result threshold formally inside."""
    sin_error_upper = SMALL_ANGLE**3 / 6
    cos_error_upper = SMALL_ANGLE**2 / 2

    assert sin_error_upper < SIN_TOWARD_ZERO_MIDPOINT
    assert cos_error_upper < COS_ONE_MIDPOINT
    assert MAX_SUBNORMAL_MAGNITUDE**3 / 6 < SUBNORMAL_MIDPOINT


def test_transcendental_classifier_constants_are_locked() -> None:
    """Keep the reviewed raw binary64 constants byte-exact in the C boundary."""
    text = SOURCE.read_text(encoding="utf-8")

    for name, bits in EXPECTED_CONSTANTS.items():
        assert f"#define {name} UINT64_C(0x{bits:016x})" in text
