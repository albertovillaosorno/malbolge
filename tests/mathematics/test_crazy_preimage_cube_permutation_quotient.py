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
#   - Independent evidence for permutation orbits of crazy preimage cube
#     words and ordered pairs.
# - Must-Not:
#   - Treat permutation orbits as position-sensitive semantic equivalence.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact word/pair orbit counts and canonical representatives.
#   - Side effects: none.
# - Split-When:
#   - A weaker symmetry group needs a distinct orbit classification.
# - Merge-When:
#   - Another cube-canonicalization proof owns the same symmetric-group action.
# - Summary:
#   - Quotient coordinate-symmetric cube words and ordered pairs.
# - Description:
#   - Exhausts bounded cube words/pairs and independently lifts canonical
#     choices to preimages.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Word enumeration reaches dimension fourteen; ordered pairs stop at
#     dimension eight; fixed-pair lifting stops at width four.
#

"""Independent evidence for the permutation quotient of crazy preimage cubes."""

from __future__ import annotations

from collections import Counter

_BINARY_RADIX = 2
_EXHAUSTIVE_PAIR_DIMENSION = 8
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
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


def _integer_binomial(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for index in range(1, k + 1):
        result = result * (n - k + index) // index
    return result


def _integer_factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _canonical_code(code: int) -> int:
    return (1 << code.bit_count()) - 1


def _canonicalizing_order(code: int, dimension: int) -> tuple[int, ...]:
    ones = tuple(
        coordinate
        for coordinate in range(dimension)
        if code & (1 << coordinate)
    )
    zeros = tuple(
        coordinate
        for coordinate in range(dimension)
        if not code & (1 << coordinate)
    )
    return (*ones, *zeros)


def _permute_code(code: int, order: tuple[int, ...]) -> int:
    result = 0
    for destination, source in enumerate(order):
        result |= ((code >> source) & 1) << destination
    return result


def _joint_symbol(left: int, right: int, coordinate: int) -> int:
    return (((left >> coordinate) & 1) << 1) | ((right >> coordinate) & 1)


def _joint_counts(
    left: int,
    right: int,
    dimension: int,
) -> tuple[int, int, int, int]:
    counts = [0, 0, 0, 0]
    for coordinate in range(dimension):
        counts[_joint_symbol(left, right, coordinate)] += 1
    return counts[0], counts[1], counts[2], counts[3]


def _ordered_pair_order(
    left: int,
    right: int,
    dimension: int,
) -> tuple[int, ...]:
    buckets: tuple[list[int], list[int], list[int], list[int]] = (
        [],
        [],
        [],
        [],
    )
    for coordinate in range(dimension):
        buckets[_joint_symbol(left, right, coordinate)].append(coordinate)
    return tuple(
        coordinate for symbol in (3, 2, 1, 0) for coordinate in buckets[symbol]
    )


def _bit_mask(width: int) -> int:
    return (1 << width) - 1


def _canonical_ordered_pair(
    counts: tuple[int, int, int, int],
) -> tuple[int, int]:
    _, n01, n10, n11 = counts
    left = _bit_mask(n11 + n10)
    right = _bit_mask(n11) | (_bit_mask(n01) << (n11 + n10))
    return left, right


def _joint_count_vectors(
    dimension: int,
) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (n00, n01, n10, dimension - n00 - n01 - n10)
        for n00 in range(dimension + 1)
        for n01 in range(dimension - n00 + 1)
        for n10 in range(dimension - n00 - n01 + 1)
    )


def _orbit_size(counts: tuple[int, int, int, int]) -> int:
    result = _integer_factorial(sum(counts))
    for count in counts:
        result //= _integer_factorial(count)
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
        choices.append(_local_preimages(accumulator % _RADIX, target % _RADIX))
        target //= _RADIX
        accumulator //= _RADIX
    return tuple(choices)


def _cube_data(
    choices: tuple[tuple[int, ...], ...],
    cube_code: int,
) -> int:
    data = 0
    place = 1
    bit_position = 0
    for local in choices:
        if not local:
            raise ValueError
        choice_index = 0
        if len(local) == _BINARY_RADIX:
            choice_index = (cube_code >> bit_position) & 1
            bit_position += 1
        data += local[choice_index] * place
        place *= _RADIX
    return data


def _crazy(data: int, accumulator: int, trit_count: int) -> int:
    target = 0
    place = 1
    for _ in range(trit_count):
        target += (
            _INDEPENDENT_CRAZY_TRIT[data % _RADIX][accumulator % _RADIX] * place
        )
        data //= _RADIX
        accumulator //= _RADIX
        place *= _RADIX
    return target


def _trit_distance(left: int, right: int, trit_count: int) -> int:
    distance = 0
    for _ in range(trit_count):
        distance += left % _RADIX != right % _RADIX
        left //= _RADIX
        right //= _RADIX
    return distance


def test_weight_classes_are_exact_orbits_through_dimension_fourteen() -> None:
    """Each checked cube has one symmetric-group orbit per Hamming weight."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        histogram = Counter(code.bit_count() for code in range(size))
        expected = Counter({
            weight: _integer_binomial(dimension, weight)
            for weight in range(dimension + 1)
        })
        assert histogram == expected
        assert {_canonical_code(code) for code in range(size)} == {
            (1 << weight) - 1 for weight in range(dimension + 1)
        }


def test_every_checked_cube_word_has_a_constructive_canonical_permutation() -> (
    None
):
    """Sort coordinates to each word's unique weight representative."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        for code in range(size):
            order = _canonicalizing_order(code, dimension)
            assert sorted(order) == list(range(dimension))
            canonical = _permute_code(code, order)
            assert canonical == _canonical_code(code)
            assert canonical.bit_count() == code.bit_count()


def test_ordered_pair_orbits_are_joint_classes_through_dimension_eight() -> (
    None
):
    """Joint counts classify every small simultaneous permutation orbit."""
    for dimension in range(_EXHAUSTIVE_PAIR_DIMENSION + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        observed: Counter[tuple[int, int, int, int]] = Counter()
        representatives: set[tuple[int, int]] = set()
        for left in range(size):
            for right in range(size):
                counts = _joint_counts(left, right, dimension)
                order = _ordered_pair_order(left, right, dimension)
                canonical = (
                    _permute_code(left, order),
                    _permute_code(right, order),
                )
                assert canonical == _canonical_ordered_pair(counts)
                left_weight = left.bit_count()
                right_weight = right.bit_count()
                distance = (left ^ right).bit_count()
                assert (
                    left_weight,
                    right_weight,
                    distance,
                ) == (
                    counts[2] + counts[3],
                    counts[1] + counts[3],
                    counts[1] + counts[2],
                )
                assert counts == (
                    dimension - (left_weight + right_weight + distance) // 2,
                    (-left_weight + right_weight + distance) // 2,
                    (left_weight - right_weight + distance) // 2,
                    (left_weight + right_weight - distance) // 2,
                )
                observed[counts] += 1
                representatives.add(canonical)
        expected = Counter({
            counts: _orbit_size(counts)
            for counts in _joint_count_vectors(dimension)
        })
        assert observed == expected
        assert len(representatives) == _integer_binomial(dimension + 3, 3)
        for code in range(size):
            canonical = _canonical_code(code)
            assert _canonical_ordered_pair(
                _joint_counts(0, code, dimension)
            ) == (0, canonical)
            assert _canonical_ordered_pair(
                _joint_counts(code, 0, dimension)
            ) == (canonical, 0)
            assert _canonical_ordered_pair(
                _joint_counts(code, code, dimension)
            ) == (canonical, canonical)


def test_ordered_pair_class_sizes_cover_through_dimension_fourteen() -> None:
    """Exact orbit sizes account for every checked ordered cube pair."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        classes = _joint_count_vectors(dimension)
        assert len(classes) == _integer_binomial(dimension + 3, 3)
        assert sum(_orbit_size(counts) for counts in classes) == 4**dimension


def _check_pair_canonicalization(
    target: int,
    accumulator: int,
    trit_count: int,
) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = sum(len(local) == _BINARY_RADIX for local in choices)
    for code in range(1 << dimension):
        data = _cube_data(choices, code)
        canonical_data = _cube_data(choices, _canonical_code(code))
        assert _crazy(data, accumulator, trit_count) == target
        assert _crazy(canonical_data, accumulator, trit_count) == target


def test_permutation_canonicalization_lifts_to_every_small_reachable_pair() -> (
    None
):
    """Canonical abstract cube choices remain valid fixed-pair preimages."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_pair_canonicalization(
                    target,
                    accumulator,
                    trit_count,
                )


def _check_ordered_pair_lifting(
    target: int,
    accumulator: int,
    trit_count: int,
) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = sum(len(local) == _BINARY_RADIX for local in choices)
    words = tuple(_cube_data(choices, code) for code in range(1 << dimension))
    assert all(
        _crazy(word, accumulator, trit_count) == target for word in words
    )
    for left in range(1 << dimension):
        for right in range(1 << dimension):
            counts = _joint_counts(left, right, dimension)
            order = _ordered_pair_order(left, right, dimension)
            canonical = (
                _permute_code(left, order),
                _permute_code(right, order),
            )
            assert canonical == _canonical_ordered_pair(counts)
            assert (
                _trit_distance(
                    words[left],
                    words[right],
                    trit_count,
                )
                == counts[1] + counts[2]
            )


def test_ordered_pair_quotient_lifts_to_small_reachable_pairs() -> None:
    """Canonical ordered cube pairs remain valid fixed-pair preimages."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_ordered_pair_lifting(target, accumulator, trit_count)
