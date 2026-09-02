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
#   - Dense composition of all five S6 (5,1)/(4,1) S4 spoke strata.
# - Must-Not:
#   - Re-prove any local spoke rank or claim the outer (5,1;4,1) prefix rank.
# - Allows:
#   - Inputs: one proved spoke-stabilizer kind and its local dense rank.
#   - Outputs: one dense rank/unrank for the complete widened S4 edge payload.
#   - Side effects: none.
# - Split-When:
#   - A local spoke-stratum rank changes its domain contract.
# - Merge-When:
#   - The outer (5,1;4,1) rank owns this complete residual interval.
# - Summary:
#   - Prefix the five proved spoke-stratum dense intervals by fixed offsets.
# - Description:
#   - Concatenates identity, S2, V4, S3, and full-S4 spoke strata.
# - Usage:
#   - Completes the widened residual S4 edge rank through mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at mass six; arithmetic reaches fourteen.
#

"""Dense composition of all S6 (5,1)/(4,1) S4 spoke strata."""

from __future__ import annotations

_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 6
_KIND_COUNT = 5
_SAMPLE_DIVISOR = 4
_WIDTH_FOURTEEN_COUNT = 100_371_765_432
_STRATUM_COUNTS = (
    (
        0,
        0,
        0,
        4,
        157,
        3_004,
        38_340,
        371_536,
        2_933_147,
        19_711_788,
        116_176_354,
        613_489_840,
        2_949_599_617,
        13_073_057_984,
        53_942_379_546,
    ),
    (
        0,
        0,
        6,
        148,
        2_041,
        20_708,
        168_194,
        1_147_672,
        6_789_551,
        35_641_020,
        168_969_046,
        733_547_104,
        2_948_627_389,
        11_073_644_648,
        39_143_536_686,
    ),
    (
        0,
        0,
        4,
        48,
        448,
        3_344,
        21_300,
        117_728,
        577_024,
        2_547_744,
        10_278_504,
        38_322_752,
        133_320_320,
        436_182_336,
        1_350_964_200,
    ),
    (
        0,
        4,
        42,
        392,
        3_071,
        20_488,
        119_118,
        613_740,
        2_844_515,
        12_018_480,
        46_817_108,
        169_745_760,
        577_433_044,
        1_855_393_032,
        5_663_416_324,
    ),
    (
        1,
        4,
        30,
        180,
        984,
        4_876,
        22_098,
        91_188,
        346_408,
        1_219_888,
        4_014_332,
        12_429_864,
        36_442_258,
        101_705_432,
        271_468_676,
    ),
)
_EXPECTED_COUNTS = (
    1,
    8,
    82,
    772,
    6_701,
    52_420,
    369_050,
    2_341_864,
    13_490_645,
    71_138_920,
    346_255_344,
    1_567_535_320,
    6_645_422_628,
    26_539_983_432,
    100_371_765_432,
)

type _State = tuple[int, int]


def _local_count(kind: int, total: int) -> int:
    if kind < 0 or kind >= _KIND_COUNT:
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


def _assert_kind_boundaries(total: int) -> None:
    for kind in range(_KIND_COUNT):
        local = _local_count(kind, total)
        if local == 0:
            continue
        start = _offset(kind, total)
        assert _unrank(total, start) == (kind, 0)
        assert _unrank(total, start + local - 1) == (kind, local - 1)


def _sample_ranks(count: int) -> tuple[int, ...]:
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            (3 * count) // _SAMPLE_DIVISOR,
            count - 1,
        })
    )


def test_s6_s5_s4_complete_spoke_rank_sums_all_five_strata() -> None:
    """Five proved local cardinalities reconstruct the full S4 edge quotient."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[_MAXIMUM_MASS] == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_s4_complete_spoke_rank_exhausts_small_domains() -> None:
    """Local spoke-stratum offsets form one contiguous rank through mass six."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s4_complete_spoke_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks dispatch to the correct local spoke block."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
        _assert_kind_boundaries(total)
