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
#   - Independent constructive evidence for exact crazy preimage ranking.
# - Must-Not:
#   - Import production crazy helpers or infer incomplete-corpus membership.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs at widths one to
#     fourteen.
#   - Outputs: exact mixed-radix rank/unrank and brute-force equality
#     assertions.
#   - Side effects: none.
# - Split-When:
#   - Another inverse canonical form needs independent executable state.
# - Merge-When:
#   - A shared crazy inverse proof owns the same full-domain bijection.
# - Summary:
#   - Rank every complete-domain crazy preimage without scanning all data words.
# - Description:
#   - Uses singleton/doubleton local inverse sets as exact mixed-radix digits.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Structural checks stop at width fourteen; brute force stops at width four.
#

"""Independent evidence for constructive crazy preimage ranking."""

from __future__ import annotations

_MAXIMUM_TRITS = 14
_EXHAUSTIVE_TRITS = 4
_RADIX = 3
_REACHABLE_LOCAL_PAIRS = 7
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _local_preimages(accumulator: int, target: int) -> tuple[int, ...]:
    return tuple(
        data
        for data in range(_RADIX)
        if _INDEPENDENT_CRAZY_TRIT[data][accumulator] == target
    )


def _choice_sets(
    target: int,
    accumulator: int,
    trit_count: int,
) -> tuple[tuple[int, ...], ...]:
    choices: list[tuple[int, ...]] = []
    for _ in range(trit_count):
        choices.append(
            _local_preimages(accumulator % _RADIX, target % _RADIX)
        )
        target //= _RADIX
        accumulator //= _RADIX
    return tuple(choices)


def _preimage_count(
    target: int,
    accumulator: int,
    trit_count: int,
) -> int:
    result = 1
    for choices in _choice_sets(target, accumulator, trit_count):
        result *= len(choices)
    return result


def _unrank(
    target: int,
    accumulator: int,
    *,
    trit_count: int,
    rank: int,
) -> int:
    choices_by_position = _choice_sets(target, accumulator, trit_count)
    total = _preimage_count(target, accumulator, trit_count)
    if rank < 0 or rank >= total:
        raise ValueError
    data = 0
    place = 1
    remaining = rank
    for choices in choices_by_position:
        radix = len(choices)
        digit = remaining % radix
        remaining //= radix
        data += choices[digit] * place
        place *= _RADIX
    return data


def _rank(
    data: int,
    target: int,
    accumulator: int,
    *,
    trit_count: int,
) -> int:
    choices_by_position = _choice_sets(target, accumulator, trit_count)
    result = 0
    place = 1
    for choices in choices_by_position:
        data_trit = data % _RADIX
        if data_trit not in choices:
            raise ValueError
        result += choices.index(data_trit) * place
        place *= len(choices)
        data //= _RADIX
    if data != 0:
        raise ValueError
    return result


def _crazy(data: int, accumulator: int, trit_count: int) -> int:
    result = 0
    place = 1
    for _ in range(trit_count):
        result += (
            _INDEPENDENT_CRAZY_TRIT[data % _RADIX][accumulator % _RADIX]
            * place
        )
        data //= _RADIX
        accumulator //= _RADIX
        place *= _RADIX
    return result


def _brute_preimages(
    target: int,
    accumulator: int,
    trit_count: int,
) -> tuple[int, ...]:
    domain = _integer_power(_RADIX, trit_count)
    return tuple(
        data
        for data in range(domain)
        if _crazy(data, accumulator, trit_count) == target
    )


def test_local_inverse_sets_are_only_empty_singleton_or_doubleton() -> None:
    """The independent one-trit relation admits no inverse radix above two."""
    observed = {
        len(_local_preimages(accumulator, target))
        for accumulator in range(_RADIX)
        for target in range(_RADIX)
    }
    assert observed == {0, 1, 2}


def test_preimage_rank_is_structurally_exact_through_width_fourteen() -> None:
    """Every checked width composes exact singleton/doubleton inverse digits."""
    reachable = tuple(
        (accumulator, target)
        for accumulator in range(_RADIX)
        for target in range(_RADIX)
        if _local_preimages(accumulator, target)
    )
    assert len(reachable) == _REACHABLE_LOCAL_PAIRS
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        for local_accumulator, local_target in reachable:
            accumulator = sum(
                local_accumulator * _integer_power(_RADIX, position)
                for position in range(trit_count)
            )
            target = sum(
                local_target * _integer_power(_RADIX, position)
                for position in range(trit_count)
            )
            count = _preimage_count(target, accumulator, trit_count)
            assert count in {
                _integer_power(2, exponent)
                for exponent in range(trit_count + 1)
            }
            assert _rank(
                _unrank(target, accumulator, trit_count=trit_count, rank=0),
                target,
                accumulator,
                trit_count=trit_count,
            ) == 0
            assert _rank(
                _unrank(
                    target,
                    accumulator,
                    trit_count=trit_count,
                    rank=count - 1,
                ),
                target,
                accumulator,
                trit_count=trit_count,
            ) == count - 1


def _check_small_pair(
    target: int,
    accumulator: int,
    trit_count: int,
) -> None:
    expected = _brute_preimages(target, accumulator, trit_count)
    count = _preimage_count(target, accumulator, trit_count)
    assert count == len(expected)
    if not expected:
        return
    observed = tuple(
        _unrank(
            target,
            accumulator,
            trit_count=trit_count,
            rank=rank,
        )
        for rank in range(count)
    )
    assert observed == expected
    assert tuple(
        _rank(
            data,
            target,
            accumulator,
            trit_count=trit_count,
        )
        for data in expected
    ) == tuple(range(count))


def test_preimage_rank_matches_brute_force_for_every_small_pair() -> None:
    """Widths one to four reproduce every brute-force preimage exactly once."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_small_pair(target, accumulator, trit_count)


def test_preimage_rank_exhausts_maximum_checked_preimage() -> None:
    """The width-fourteen doubleton case enumerates all 16,384 preimages."""
    trit_count = _MAXIMUM_TRITS
    accumulator = 0
    target = sum(
        _integer_power(_RADIX, position)
        for position in range(trit_count)
    )
    count = _preimage_count(target, accumulator, trit_count)
    expected_count = _integer_power(2, trit_count)
    assert count == expected_count
    observed = tuple(
        _unrank(
            target,
            accumulator,
            trit_count=trit_count,
            rank=rank,
        )
        for rank in range(count)
    )
    assert len(set(observed)) == expected_count
    assert all(
        _crazy(data, accumulator, trit_count) == target
        for data in observed
    )
    assert all(
        _rank(
            data,
            target,
            accumulator,
            trit_count=trit_count,
        ) == rank
        for rank, data in enumerate(observed)
    )
