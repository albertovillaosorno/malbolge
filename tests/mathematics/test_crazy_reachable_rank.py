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
#   - Independent constructive correspondence for reachable crazy pair ranking.
# - Must-Not:
#   - Import production crazy-search helpers or equate distinct reachable pairs.
# - Allows:
#   - Inputs: checked trit widths one through fourteen and reachable pair
#     digits.
#   - Outputs: exact base-seven rank/unrank and rejection assertions.
#   - Side effects: none.
# - Split-When:
#   - Another canonical search domain needs independent executable state.
# - Merge-When:
#   - A shared crazy-pair correspondence test owns the same bijection.
# - Summary:
#   - Prove a constructive base-seven form for every reachable crazy pair.
# - Description:
#   - Lifts the seven reachable per-trit pairs to exact width-indexed ranking.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Widths are checked only across the admitted one-through-fourteen family.
#

"""Independent evidence for exact reachable crazy-pair ranking."""

from __future__ import annotations

_MAXIMUM_TRITS = 14
_EXHAUSTIVE_TRITS = 6
_RADIX = 3
_RANK_RADIX = 7
_UNREACHABLE_LOCAL_PAIRS = 2
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _local_pairs() -> tuple[tuple[int, int], ...]:
    return tuple(
        (accumulator, target)
        for accumulator in range(_RADIX)
        for target in range(_RADIX)
        if any(
            row[accumulator] == target
            for row in _INDEPENDENT_CRAZY_TRIT
        )
    )


def _rank(pairs: tuple[tuple[int, int], ...]) -> int:
    local = _local_pairs()
    result = 0
    place = 1
    for pair in pairs:
        if pair not in local:
            raise ValueError
        result += local.index(pair) * place
        place *= _RANK_RADIX
    return result


def _unrank(rank: int, trit_count: int) -> tuple[tuple[int, int], ...]:
    if rank < 0 or rank >= _integer_power(_RANK_RADIX, trit_count):
        raise ValueError
    local = _local_pairs()
    digits: list[tuple[int, int]] = []
    remaining = rank
    for _ in range(trit_count):
        digit = remaining % _RANK_RADIX
        remaining //= _RANK_RADIX
        digits.append(local[digit])
    return tuple(digits)


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _rank_rejects(pair: tuple[int, int]) -> bool:
    try:
        _ = _rank((pair,))
    except ValueError:
        return True
    return False


def test_local_reachable_crazy_pair_alphabet_is_exact() -> None:
    """Independent crazy semantics expose seven and only seven local pairs."""
    local = _local_pairs()
    assert len(local) == _RANK_RADIX
    assert len(set(local)) == _RANK_RADIX
    unreachable = {
        (accumulator, target)
        for accumulator in range(_RADIX)
        for target in range(_RADIX)
    } - set(local)
    assert len(unreachable) == _UNREACHABLE_LOCAL_PAIRS
    assert all(_rank_rejects(pair) for pair in unreachable)


def test_reachable_crazy_pair_rank_is_exact_for_checked_widths() -> None:
    """Every local symbol/position maps to one exact base-seven rank digit."""
    local = _local_pairs()
    zero = local[0]
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        maximum = _integer_power(_RANK_RADIX, trit_count)
        assert _rank((zero,) * trit_count) == 0
        assert _rank((local[-1],) * trit_count) == maximum - 1
        assert _unrank(0, trit_count) == (zero,) * trit_count
        assert _unrank(maximum - 1, trit_count) == (local[-1],) * trit_count
        for position in range(trit_count):
            place = _integer_power(_RANK_RADIX, position)
            for digit, pair in enumerate(local):
                values = [zero] * trit_count
                values[position] = pair
                encoded = digit * place
                assert _rank(tuple(values)) == encoded
                assert _unrank(encoded, trit_count) == tuple(values)


def test_reachable_crazy_pair_rank_exhausts_small_widths() -> None:
    """Widths one through six exhaust every canonical code exactly once."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        size = _integer_power(_RANK_RADIX, trit_count)
        observed = {
            _rank(_unrank(rank, trit_count))
            for rank in range(size)
        }
        assert observed == set(range(size))
