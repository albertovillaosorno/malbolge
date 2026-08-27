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
#   - Independent evidence for crazy preimage-cube triple orbits under shared
#     coordinate permutation and triple-endpoint permutation.
# - Must-Not:
#   - Apply endpoint-permutation equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact endpoint-unordered triple classes and representatives.
#   - Side effects: none.
# - Split-When:
#   - A larger tuple arity or a different endpoint symmetry group is required.
# - Merge-When:
#   - Another proof owns the same simultaneous S_k coordinate and S_3 endpoint
#     action on cube-word triples.
# - Summary:
#   - Quotient coordinate-symmetric triples further by endpoint permutation.
# - Description:
#   - Exhausts small triples and checks the bounded Burnside count exactly.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Raw triple enumeration stops at dimension four; arithmetic reaches 14;
#     fixed-pair lifting stops at width four.
#

"""Evidence for endpoint-unordered crazy preimage-cube triple quotients."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from itertools import permutations
from itertools import product
from math import comb

_BINARY_RADIX = 2
_EXHAUSTIVE_DIMENSION = 4
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_RADIX = 3
_TRIPLE_ARITY = 3
_TRIPLE_PATTERN_COUNT = 1 << _TRIPLE_ARITY
_TRIPLE_SEPARATOR_COUNT = _TRIPLE_PATTERN_COUNT - 1
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_TRIPLE_ARITY)))
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


def _integer_factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _tuple_symbol(codes: tuple[int, int, int], coordinate: int) -> int:
    result = 0
    for code in codes:
        result = (result << 1) | ((code >> coordinate) & 1)
    return result


def _tuple_counts(
    codes: tuple[int, int, int],
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * _TRIPLE_PATTERN_COUNT
    for coordinate in range(dimension):
        counts[_tuple_symbol(codes, coordinate)] += 1
    return tuple(counts)


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    bits = tuple(
        (symbol >> (_TRIPLE_ARITY - index - 1)) & 1
        for index in range(_TRIPLE_ARITY)
    )
    result = 0
    for source in endpoint_order:
        result = (result << 1) | bits[source]
    return result


def _permute_endpoint_counts(
    counts: tuple[int, ...],
    endpoint_order: tuple[int, ...],
) -> tuple[int, ...]:
    result = [0] * _TRIPLE_PATTERN_COUNT
    for symbol, count in enumerate(counts):
        result[_permuted_symbol(symbol, endpoint_order)] = count
    return tuple(result)


def _canonical_counts(counts: tuple[int, ...]) -> tuple[int, ...]:
    return min(
        _permute_endpoint_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )


def _canonical_tuple(counts: tuple[int, ...]) -> tuple[int, int, int]:
    result = [0] * _TRIPLE_ARITY
    destination = 0
    for symbol in reversed(range(_TRIPLE_PATTERN_COUNT)):
        for _ in range(counts[symbol]):
            for index in range(_TRIPLE_ARITY):
                shift = _TRIPLE_ARITY - index - 1
                result[index] |= ((symbol >> shift) & 1) << destination
            destination += 1
    return result[0], result[1], result[2]


def _canonicalize_triple(
    codes: tuple[int, int, int],
    dimension: int,
) -> tuple[tuple[int, int, int], tuple[int, ...]]:
    counts = _canonical_counts(_tuple_counts(codes, dimension))
    return _canonical_tuple(counts), counts


def _count_vectors(dimension: int) -> tuple[tuple[int, ...], ...]:
    vectors: list[tuple[int, ...]] = []
    for bars in combinations(
        range(dimension + _TRIPLE_SEPARATOR_COUNT),
        _TRIPLE_SEPARATOR_COUNT,
    ):
        positions = (-1, *bars, dimension + _TRIPLE_SEPARATOR_COUNT)
        vectors.append(tuple(
            positions[index + 1] - positions[index] - 1
            for index in range(_TRIPLE_PATTERN_COUNT)
        ))
    return tuple(vectors)


def _coordinate_orbit_size(counts: tuple[int, ...]) -> int:
    result = _integer_factorial(sum(counts))
    for count in counts:
        result //= _integer_factorial(count)
    return result


def _endpoint_orbit_size(counts: tuple[int, ...]) -> int:
    return len({
        _permute_endpoint_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    })


def _combined_orbit_size(counts: tuple[int, ...]) -> int:
    return _coordinate_orbit_size(counts) * _endpoint_orbit_size(counts)


def _transposition_fixed_count(dimension: int) -> int:
    return sum(
        comb(dimension - 2 * paired_total + 3, 3) * (paired_total + 1)
        for paired_total in range(dimension // 2 + 1)
    )


def _three_cycle_fixed_count(dimension: int) -> int:
    return sum(
        (dimension - 3 * cycled_total + 1) * (cycled_total + 1)
        for cycled_total in range(dimension // 3 + 1)
    )


def _unordered_triple_class_count(dimension: int) -> int:
    identity = comb(dimension + 7, 7)
    transpositions = 3 * _transposition_fixed_count(dimension)
    three_cycles = 2 * _three_cycle_fixed_count(dimension)
    return (identity + transpositions + three_cycles) // 6


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
        if len(local) == 1:
            data_trit = local[0]
        else:
            data_trit = local[(cube_code >> bit_position) & 1]
            bit_position += 1
        data += data_trit * place
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


def test_unordered_triple_orbits_are_exact_through_dimension_four() -> None:
    """Small triples collapse exactly under coordinate and endpoint actions."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        observed: Counter[tuple[int, ...]] = Counter()
        representatives: set[tuple[int, int, int]] = set()
        for codes in product(range(size), repeat=_TRIPLE_ARITY):
            triple = codes[0], codes[1], codes[2]
            canonical, counts = _canonicalize_triple(triple, dimension)
            for endpoint_order in _ENDPOINT_PERMUTATIONS:
                permuted = (
                    triple[endpoint_order[0]],
                    triple[endpoint_order[1]],
                    triple[endpoint_order[2]],
                )
                assert _canonicalize_triple(permuted, dimension) == (
                    canonical,
                    counts,
                )
            observed[counts] += 1
            representatives.add(canonical)
        canonical_counts = {
            _canonical_counts(counts) for counts in _count_vectors(dimension)
        }
        expected = Counter({
            counts: _combined_orbit_size(counts) for counts in canonical_counts
        })
        assert observed == expected
        assert len(representatives) == _unordered_triple_class_count(dimension)


def test_unordered_triple_counts_cover_through_dimension_fourteen() -> None:
    """Burnside and exact orbit masses cover every checked ordered triple."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        vectors = _count_vectors(dimension)
        canonical_counts = {_canonical_counts(counts) for counts in vectors}
        assert len(canonical_counts) == _unordered_triple_class_count(dimension)
        assert sum(
            _combined_orbit_size(counts) for counts in canonical_counts
        ) == _integer_power(_TRIPLE_PATTERN_COUNT, dimension)


def _check_fixed_pair_lifting(
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
    representatives: set[tuple[int, int, int]] = set()
    for codes in product(range(1 << dimension), repeat=_TRIPLE_ARITY):
        triple = codes[0], codes[1], codes[2]
        canonical, _ = _canonicalize_triple(triple, dimension)
        representatives.add(canonical)
        assert all(
            _crazy(words[code], accumulator, trit_count) == target
            for code in canonical
        )
    assert len(representatives) == _unordered_triple_class_count(dimension)


def test_unordered_triple_quotient_lifts_to_small_reachable_pairs() -> None:
    """Canonical unordered triples remain valid fixed-pair preimages."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_fixed_pair_lifting(target, accumulator, trit_count)
