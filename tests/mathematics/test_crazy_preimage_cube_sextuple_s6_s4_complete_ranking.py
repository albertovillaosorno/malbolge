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
#   - Dense composition of all five nested (4,1,1) S6 second-layer strata.
# - Must-Not:
#   - Re-prove any local second-layer rank or claim another top-level stratum.
# - Allows:
#   - Inputs: one proved second-layer kind and its local dense rank.
#   - Outputs: one exact dense rank/unrank for the full (4,1,1) S6 stratum.
#   - Side effects: none.
# - Split-When:
#   - A local second-layer rank changes its domain contract.
# - Merge-When:
#   - Complete dense S6 ranking owns all eleven top-level Young strata.
# - Summary:
#   - Prefix the five proved second-layer dense intervals by fixed offsets.
# - Description:
#   - Concatenates identity, S2, S3, V4, and full-S4 bundle strata.
# - Usage:
#   - Completes one dense (4,1,1) interval through total mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at total mass six; arithmetic reaches 14.
#

"""Dense composition of all nested S6 (4,1,1) second-layer strata."""

from __future__ import annotations

_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 6
_KIND_COUNT = 5
_WIDTH_FOURTEEN_COUNT = 302_650_855_156
_STRATUM_COUNTS = (
    (
        0, 0, 0, 0, 0, 20, 1_010, 25_440, 429_836, 5_510_840,
        57_384_447, 506_639_280, 3_906_048_544, 26_865_475_458,
        167_523_430_983,
    ),
    (
        0, 0, 0, 0, 15, 546, 10_443, 140_568, 1_488_547, 13_128_302,
        99_872_114, 671_354_392, 4_059_716_439, 22_392_012_768,
        113_906_741_533,
    ),
    (
        0, 0, 0, 6, 129, 1_622, 15_945, 132_412, 958_607, 6_164_874,
        35_715_856, 188_567_946, 916_308_892, 4_133_308_028,
        17_436_163_856,
    ),
    (
        0, 0, 0, 0, 6, 132, 1_674, 16_128, 128_774, 888_452,
        5_423_910, 29_795_952, 149_220_534, 688_626_036, 2_954_772_356,
    ),
    (
        0, 0, 1, 14, 115, 808, 5_128, 29_832, 159_834, 791_464,
        3_633_671, 15_532_486, 62_115_104, 233_555_344, 829_746_428,
    ),
)
_EXPECTED_COUNTS = (
    0,
    0,
    1,
    20,
    265,
    3_128,
    34_200,
    344_380,
    3_165_598,
    26_483_932,
    202_029_998,
    1_411_890_056,
    9_093_409_513,
    54_312_977_634,
    302_650_855_156,
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


def test_s6_s4_complete_rank_sums_all_five_second_layer_strata() -> None:
    """Five reviewed local cardinalities reconstruct the full outer stratum."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[_MAXIMUM_MASS] == _WIDTH_FOURTEEN_COUNT


def test_s6_s4_complete_rank_exhausts_small_abstract_domains() -> None:
    """Local-stratum offsets form one contiguous rank through mass six."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4_complete_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks dispatch to the correct local block."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        probes = {0, count // 4, count // 2, (3 * count) // 4, count - 1}
        for rank in probes:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
        _assert_kind_boundaries(total)
