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
#   - Dense concatenation of all nine widened exact-S5 edge rank strata.
# - Must-Not:
#   - Re-prove a local stabilizer rank or alter its canonical ordering.
# - Allows:
#   - Inputs: one exact stabilizer kind and its proved local dense rank.
#   - Outputs: one complete dense widened full-S5 edge rank and inverse
#     dispatch.
#   - Side effects: none.
# - Split-When:
#   - Another endpoint arity needs a separate finite-stratum composition.
# - Merge-When:
#   - The outer all-equal bundle rank owns this complete residual interval.
# - Summary:
#   - Prefix all nine exact local S5 rank intervals by their cardinalities.
# - Description:
#   - Trivial and eight symmetric local bijections compose without gaps.
# - Usage:
#   - Complete 20,103,708,128-class mass-fourteen widened full-S5 hard core.
# - Defaults:
#   - Exhaustive abstract dispatch reaches every mass through fourteen.
#

"""Dense composition of all widened exact-S5 K5 edge rank strata."""

from __future__ import annotations

_MAXIMUM_MASS = 14
_KIND_COUNT = 11
_STRATA = (
    "trivial",
    "transposition",
    "double-transposition",
    "disjoint-v4",
    "transitive-v4",
    "s3",
    "d8",
    "s3xs2",
    "s4",
    "d10",
    "full-s5",
)
_STRATUM_COUNTS = (
    (
        0,
        0,
        0,
        28,
        608,
        6_896,
        58_532,
        409_700,
        2_492_068,
        13_554_716,
        67_188_884,
        307_526_548,
        1_312_575_006,
        5_264_371_340,
        19_963_566_552,
    ),
    (
        0,
        0,
        6,
        80,
        607,
        3_380,
        15_602,
        62_956,
        229_096,
        766_508,
        2_391_636,
        7_029_316,
        19_609_430,
        52_237_020,
        133_525_016,
    ),
    (
        0,
        0,
        0,
        16,
        80,
        428,
        1_600,
        5_792,
        17_792,
        52_576,
        141_488,
        366_784,
        893_664,
        2_105_792,
        4_743_872,
    ),
    (
        0,
        0,
        10,
        68,
        269,
        940,
        2_770,
        7_576,
        19_055,
        45_472,
        102_676,
        222_784,
        464_268,
        937_152,
        1_833_336,
    ),
    (0, 0, 0, 0, 6, 0, 44, 0, 209, 0, 816, 0, 2_694, 0, 7_992),
    (
        0,
        0,
        0,
        4,
        12,
        40,
        108,
        268,
        534,
        1_140,
        2_244,
        4_092,
        7_458,
        13_284,
        22_280,
    ),
    (0, 0, 4, 0, 14, 0, 48, 0, 141, 0, 344, 0, 814, 0, 1_728),
    (
        0,
        4,
        10,
        24,
        51,
        96,
        178,
        316,
        529,
        872,
        1_396,
        2_168,
        3_316,
        4_984,
        7_312,
    ),
    (0, 0, 0, 0, 4, 0, 4, 0, 10, 0, 12, 0, 30, 0, 40),
    (0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 16, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0),
)
_EXPECTED_COUNTS = (
    1,
    4,
    30,
    220,
    1_651,
    11_784,
    78_886,
    486_608,
    2_759_434,
    14_421_284,
    69_829_516,
    315_151_692,
    1_333_556_680,
    5_319_669_572,
    20_103_708_128,
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


def test_complete_s5_rank_sums_all_eleven_exact_strata() -> None:
    """Eleven local cardinalities reconstruct the full widened S5 core."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT
    assert len(_STRATA) == _KIND_COUNT


def test_complete_s5_rank_dispatches_without_gaps_through_fourteen() -> None:
    """Every nonempty local interval has exact global boundary dispatch."""
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


def test_complete_s5_rank_roundtrips_sampled_global_ranks() -> None:
    """Complete-S5 rank samples roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
