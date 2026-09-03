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
#   - Exact repeated-six vertex-prefix composition for the free and exact
#     single-transposition residual sequences in the top-level `(6)` stratum.
# - Must-Not:
#   - Claim dense exact-transposition rank/unrank.
# - Allows:
#   - Inputs: reviewed free-transposition, exact-transposition, and exact-S3
#     residual sequences through mass fourteen.
#   - Outputs: complete outer count sequences and exact subtraction identity.
#   - Side effects: none.
# - Split-When:
#   - Dense exact-transposition rank/unrank owns the same outer prefix.
# - Merge-When:
#   - Complete dense full-S6 ranking owns every exact stabilizer interval.
# - Summary:
#   - Lift residual transposition counts through the repeated-six vertex pair.
# - Description:
#   - The free-minus-exact outer difference is exactly the exact-S3 interval.
# - Usage:
#   - Complete-count target for the remaining exact-transposition rank.
# - Defaults:
#   - Arithmetic is checked at every total mass through fourteen.
#

"""Outer count composition for the exact full-S6 transposition stratum."""

_MAXIMUM_MASS = 14
_REPEAT_COUNT = 6
_FREE_RESIDUAL = (
    0,
    0,
    1,
    34,
    431,
    3_584,
    23_151,
    125_700,
    599_644,
    2_583_332,
    10_236_354,
    37_793_678,
    131_270_971,
    432_112_216,
    1_355_933_156,
)
_EXACT_RESIDUAL = (
    0,
    0,
    0,
    24,
    377,
    3_356,
    22_352,
    123_220,
    592_648,
    2_565_032,
    10_191_319,
    37_688_418,
    131_035_614,
    431_605_710,
    1_354_879_279,
)
_EXACT_S3_COMPLETE = (
    0,
    0,
    1,
    10,
    54,
    228,
    799,
    2_480,
    6_998,
    18_320,
    45_143,
    105_716,
    236_955,
    511_466,
    1_067_872,
)
_EXPECTED_FREE_COMPLETE = (
    0,
    0,
    1,
    34,
    431,
    3_584,
    23_151,
    125_700,
    599_646,
    2_583_400,
    10_237_216,
    37_800_846,
    131_317_273,
    432_363_616,
    1_357_132_447,
)
_EXPECTED_EXACT_COMPLETE = (
    0,
    0,
    0,
    24,
    377,
    3_356,
    22_352,
    123_220,
    592_648,
    2_565_080,
    10_192_073,
    37_695_130,
    131_080_318,
    431_852_150,
    1_356_064_575,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_EXACT_COMPLETE[-1]


def _lift(residual: tuple[int, ...], total: int) -> int:
    return sum(
        (vertex_mass + 1) * residual[total - _REPEAT_COUNT * vertex_mass]
        for vertex_mass in range(total // _REPEAT_COUNT + 1)
    )


def test_transposition_outer_free_and_exact_counts_are_exact() -> None:
    """Repeated-six vertex pairs reconstruct both transposition counts."""
    free = tuple(
        _lift(_FREE_RESIDUAL, total) for total in range(_MAXIMUM_MASS + 1)
    )
    exact = tuple(
        _lift(_EXACT_RESIDUAL, total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert free == _EXPECTED_FREE_COMPLETE
    assert exact == _EXPECTED_EXACT_COMPLETE
    assert exact[-1] == _WIDTH_FOURTEEN_COUNT


def test_transposition_outer_difference_is_exact_s3_interval() -> None:
    """Free-minus-exact counts equal the exact-S3 exception interval."""
    difference = tuple(
        free - exact
        for free, exact in zip(
            _EXPECTED_FREE_COMPLETE,
            _EXPECTED_EXACT_COMPLETE,
            strict=True,
        )
    )
    assert difference == _EXACT_S3_COMPLETE
