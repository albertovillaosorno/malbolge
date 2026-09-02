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
#   - Dense concatenation of all seven S6 (5,1) second-layer bundle strata.
# - Must-Not:
#   - Re-prove a local bundle/edge rank or alter its canonical ordering.
# - Allows:
#   - Inputs: one second-layer bundle stratum and its proved local dense rank.
#   - Outputs: one complete dense rank and inverse dispatch for S6 partition
#     5,1.
#   - Side effects: none.
# - Split-When:
#   - Another top-level S6 partition needs its own finite-stratum composition.
# - Merge-When:
#   - A complete dense S6 rank directly owns all top-level Young strata.
# - Summary:
#   - Prefix all seven proved second-layer dense intervals by cardinality.
# - Description:
#   - Seven bundle multiplicity shapes partition the nested full-S5 quotient.
# - Usage:
#   - Completes all 310,719,486,939 mass-fourteen S6 (5,1) classes.
# - Defaults:
#   - Abstract dispatch is checked at every mass through fourteen.
#

"""Dense composition of all nested S6 (5,1) second-layer bundle strata."""

from __future__ import annotations

_MAXIMUM_MASS = 14
_KIND_COUNT = 7
_STRATA = (
    "distinct",
    "s2",
    "s3",
    "s4",
    "v4",
    "s3xs2",
    "s5",
)
_STRATUM_COUNTS = (
    (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        6,
        289,
        7_118,
        119_456,
        1_535_898,
        16_129_864,
        144_057_980,
        1_124_927_130,
    ),
    (
        0,
        0,
        0,
        0,
        0,
        6,
        221,
        4_642,
        71_127,
        868_666,
        8_857_824,
        77_732_592,
        600_189_773,
        4_147_764_698,
        26_007_971_192,
    ),
    (
        0,
        0,
        0,
        2,
        51,
        816,
        10_539,
        115_984,
        1_108_835,
        9_334_420,
        70_042_924,
        473_845_602,
        2_920_184_587,
        16_546_299_256,
        86_903_339_017,
    ),
    (
        0,
        0,
        4,
        52,
        549,
        5_366,
        48_769,
        406_312,
        3_081_909,
        21_264_190,
        133_946_584,
        774_882_350,
        4_144_350_885,
        20_628_064_168,
        96_141_721_711,
    ),
    (
        0,
        0,
        0,
        0,
        4,
        108,
        1_837,
        24_420,
        270_857,
        2_577_950,
        21_448_844,
        158_417_802,
        1_052_663_577,
        6_366_535_156,
        35_397_909_316,
    ),
    (
        0,
        0,
        0,
        4,
        66,
        804,
        8_609,
        82_880,
        715_037,
        5_527_610,
        38_467_687,
        242_819_402,
        1_402_054_650,
        7_466_507_322,
        36_950_581_606,
    ),
    (
        0,
        2,
        15,
        104,
        744,
        5_494,
        39_840,
        275_326,
        1_778_332,
        10_651_292,
        59_107_031,
        304_780_354,
        1_466_931_408,
        6_623_409_906,
        28_193_036_967,
    ),
)
_EXPECTED_COUNTS = (
    0,
    2,
    19,
    162,
    1_414,
    12_594,
    109_815,
    909_570,
    7_026_386,
    50_231_246,
    331_990_350,
    2_034_014_000,
    11_602_504_744,
    61_922_638_486,
    310_719_486_939,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]

type _State = tuple[int, int]


def _local_count(kind: int, total: int) -> int:
    valid_kind = 0 <= kind < _KIND_COUNT
    valid_total = 0 <= total <= _MAXIMUM_MASS
    if not valid_kind or not valid_total:
        return 0
    return _STRATUM_COUNTS[kind][total]


def _class_count(total: int) -> int:
    return sum(_local_count(kind, total) for kind in range(_KIND_COUNT))


def _offset(kind: int, total: int) -> int:
    return sum(_local_count(candidate, total) for candidate in range(kind))


def _rank(total: int, state: _State) -> int | None:
    kind, local_rank = state
    count = _local_count(kind, total)
    if count == 0 or local_rank < 0 or local_rank >= count:
        return None
    return _offset(kind, total) + local_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for kind in range(_KIND_COUNT):
        count = _local_count(kind, total)
        if remaining >= count:
            remaining -= count
            continue
        return kind, remaining
    raise AssertionError


def test_complete_s5_bundle_rank_sums_all_seven_strata() -> None:
    """Seven local branch counts reconstruct the parent nested S5 sequence."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT
    assert len(_STRATA) == _KIND_COUNT


def test_complete_s5_bundle_rank_dispatches_without_gaps() -> None:
    """Every nonempty second-layer interval has exact global boundaries."""
    for total in range(_MAXIMUM_MASS + 1):
        for kind in range(_KIND_COUNT):
            count = _local_count(kind, total)
            if count == 0:
                continue
            start = _offset(kind, total)
            end = start + count - 1
            assert _rank(total, (kind, 0)) == start
            assert _rank(total, (kind, count - 1)) == end
            assert _unrank(total, start) == (kind, 0)
            assert _unrank(total, end) == (kind, count - 1)


def test_complete_s5_bundle_rank_roundtrips_through_fourteen() -> None:
    """Complete nested-S5 rank samples roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
