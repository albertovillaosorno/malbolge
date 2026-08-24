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
#   - Independent evidence for exact Gray traversal of crazy preimage cubes.
# - Must-Not:
#   - Import production crazy helpers or infer incomplete-corpus membership.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs at widths one to
#     fourteen.
#   - Outputs: exact hypercube and one-trit Gray-adjacency assertions.
#   - Side effects: none.
# - Split-When:
#   - Another inverse traversal needs independent executable state.
# - Merge-When:
#   - A shared crazy inverse proof owns the same hypercube traversal.
# - Summary:
#   - Traverse every complete-domain crazy preimage by one-trit Gray steps.
# - Description:
#   - Treats doubleton local inverse sets as binary cube coordinates.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - All-pair brute force stops at width four; structural masks reach fourteen.
#

"""Independent evidence for Gray traversal of crazy preimage hypercubes."""

from __future__ import annotations

from itertools import pairwise

_MAXIMUM_TRITS = 14
_EXHAUSTIVE_TRITS = 4
_BINARY_RADIX = 2
_RADIX = 3
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


def _gray_code(rank: int) -> int:
    return rank ^ (rank >> 1)


def _cube_dimension(choices_by_position: tuple[tuple[int, ...], ...]) -> int:
    return sum(
        len(choices) == _BINARY_RADIX
        for choices in choices_by_position
    )


def _cube_data(
    target: int,
    accumulator: int,
    *,
    trit_count: int,
    cube_code: int,
) -> int:
    choices_by_position = _choice_sets(target, accumulator, trit_count)
    dimension = _cube_dimension(choices_by_position)
    if cube_code < 0 or cube_code >= _integer_power(_BINARY_RADIX, dimension):
        raise ValueError
    data = 0
    place = 1
    bit_position = 0
    for choices in choices_by_position:
        if not choices:
            raise ValueError
        if len(choices) == 1:
            data_trit = choices[0]
        else:
            data_trit = choices[(cube_code >> bit_position) & 1]
            bit_position += 1
        data += data_trit * place
        place *= _RADIX
    return data


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


def _trit_distance(left: int, right: int, trit_count: int) -> int:
    distance = 0
    for _ in range(trit_count):
        distance += left % _RADIX != right % _RADIX
        left //= _RADIX
        right //= _RADIX
    return distance


def _pair_from_ambiguity_mask(mask: int) -> tuple[int, int]:
    accumulator = 0
    target = 0
    place = 1
    for position in range(_MAXIMUM_TRITS):
        if mask & (1 << position):
            local_accumulator, local_target = 0, 1
        else:
            local_accumulator, local_target = 2, 0
        accumulator += local_accumulator * place
        target += local_target * place
        place *= _RADIX
    return accumulator, target


def test_gray_code_is_single_bit_through_width_fourteen() -> None:
    """Every checked binary cube has a complete one-bit Gray traversal."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        codes = tuple(_gray_code(rank) for rank in range(size))
        assert set(codes) == set(range(size))
        for left, right in pairwise(codes):
            difference = left ^ right
            assert difference != 0
            assert difference & (difference - 1) == 0


def _check_small_pair_gray(
    target: int,
    accumulator: int,
    trit_count: int,
) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = _cube_dimension(choices)
    size = _integer_power(_BINARY_RADIX, dimension)
    observed = tuple(
        _cube_data(
            target,
            accumulator,
            trit_count=trit_count,
            cube_code=_gray_code(rank),
        )
        for rank in range(size)
    )
    expected = _brute_preimages(target, accumulator, trit_count)
    assert set(observed) == set(expected)
    assert len(observed) == len(set(observed)) == size
    assert all(
        _trit_distance(left, right, trit_count) == 1
        for left, right in pairwise(observed)
    )


def test_gray_preimages_match_brute_force_for_every_small_pair() -> None:
    """Every reachable pair through width four is exactly one Gray cube."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_small_pair_gray(target, accumulator, trit_count)


def test_every_width_fourteen_ambiguity_mask_has_exact_cube_dimension() -> None:
    """All 16,384 ambiguity masks induce the predicted binary dimension."""
    for mask in range(_integer_power(_BINARY_RADIX, _MAXIMUM_TRITS)):
        accumulator, target = _pair_from_ambiguity_mask(mask)
        choices = _choice_sets(target, accumulator, _MAXIMUM_TRITS)
        observed_mask = sum(
            (1 << position) if len(local) == _BINARY_RADIX else 0
            for position, local in enumerate(choices)
        )
        assert observed_mask == mask
        dimension = mask.bit_count()
        assert _integer_power(_BINARY_RADIX, dimension) == _integer_power(
            _BINARY_RADIX,
            _cube_dimension(choices),
        )


def test_maximum_preimage_cube_is_exhausted_by_one_trit_gray_steps() -> None:
    """The dimension-fourteen case visits all 16,384 preimages exactly once."""
    mask = _integer_power(_BINARY_RADIX, _MAXIMUM_TRITS) - 1
    accumulator, target = _pair_from_ambiguity_mask(mask)
    size = _integer_power(_BINARY_RADIX, _MAXIMUM_TRITS)
    observed = tuple(
        _cube_data(
            target,
            accumulator,
            trit_count=_MAXIMUM_TRITS,
            cube_code=_gray_code(rank),
        )
        for rank in range(size)
    )
    assert len(set(observed)) == size
    assert all(
        _crazy(data, accumulator, _MAXIMUM_TRITS) == target
        for data in observed
    )
    assert all(
        _trit_distance(left, right, _MAXIMUM_TRITS) == 1
        for left, right in pairwise(observed)
    )
