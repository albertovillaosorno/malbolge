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
#   - Independent generic endpoint-unordered quotient evidence for ordered
#     crazy preimage-cube tuples under endpoint and coordinate permutations.
# - Must-Not:
#   - Apply endpoint symmetry to direction-sensitive analyses or claim an
#     unbounded endpoint arity.
# - Allows:
#   - Inputs: endpoint arities three through eight and ambiguity dimensions
#     zero through fourteen.
#   - Outputs: exact Burnside class counts and global reachable-pair counts.
#   - Side effects: none.
# - Split-When:
#   - A different endpoint group or arity beyond eight is required.
# - Merge-When:
#   - Another theorem owns the same S_k coordinate and S_m endpoint actions.
# - Summary:
#   - Generalize endpoint-unordered cube tuple quotients through arity eight.
# - Description:
#   - Derives conjugacy classes from integer partitions and independently
#     checks local and global Burnside arithmetic.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Endpoint arities stop at eight; ambiguity arithmetic reaches fourteen.
#

"""Evidence for generic endpoint-unordered crazy preimage-cube quotients."""

from __future__ import annotations

from collections import Counter
from itertools import combinations_with_replacement
from itertools import permutations
from math import comb
from math import factorial

_MINIMUM_ARITY = 3
_MAXIMUM_ARITY = 8
_MAXIMUM_TRITS = 14
_EXPECTED_PARTITION_COUNTS = {3: 3, 4: 5, 5: 7, 6: 11, 7: 15, 8: 22}
_WIDTH_FOURTEEN_LOCAL_COUNTS = {
    3: 21_323,
    4: 3_419_552,
    5: 1_426_354_541,
    6: 1_179_940_653_635,
    7: 1_442_705_743_162_885,
    8: 2_103_669_236_921_739_401,
}
_WIDTH_FOURTEEN_GLOBAL_COUNTS = {
    3: 124_279_218_052_677,
    4: 1_409_733_897_288_413,
    5: 34_995_940_605_821_849,
    6: 2_361_488_883_978_006_005,
    7: 432_496_703_839_294_883_265,
    8: 178_151_458_860_093_866_748_569,
}


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _integer_partitions(
    total: int,
    minimum: int = 1,
) -> tuple[tuple[int, ...], ...]:
    if total == 0:
        return ((),)
    result: list[tuple[int, ...]] = []
    for first in range(minimum, total + 1):
        result.extend(
            (first, *rest)
            for rest in _integer_partitions(total - first, first)
        )
    return tuple(result)


def _cycle_type(permutation: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(len(permutation)))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _partition_representative(partition: tuple[int, ...]) -> tuple[int, ...]:
    result: list[int] = []
    start = 0
    for length in partition:
        result.extend(
            start + ((offset + 1) % length) for offset in range(length)
        )
        start += length
    return tuple(result)


def _conjugacy_class_weight(partition: tuple[int, ...]) -> int:
    multiplicities = Counter(partition)
    denominator = 1
    for cycle_length, multiplicity in multiplicities.items():
        denominator *= _integer_power(cycle_length, multiplicity)
        denominator *= factorial(multiplicity)
    return factorial(sum(partition)) // denominator


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    arity = len(endpoint_order)
    result = 0
    for source in endpoint_order:
        result = (result << 1) | ((symbol >> (arity - source - 1)) & 1)
    return result


def _label_cycle_lengths(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    pattern_count = 1 << len(endpoint_order)
    unseen = set(range(pattern_count))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = _permuted_symbol(current, endpoint_order)
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _endpoint_type_data(
    arity: int,
) -> tuple[tuple[tuple[int, ...], int, tuple[int, ...]], ...]:
    return tuple(
        (
            partition,
            _conjugacy_class_weight(partition),
            _label_cycle_lengths(_partition_representative(partition)),
        )
        for partition in _integer_partitions(arity)
    )


def _fixed_count_from_cycles(cycles: tuple[int, ...], dimension: int) -> int:
    coefficients = [1] + [0] * dimension
    for cycle_length in cycles:
        next_coefficients = [0] * (dimension + 1)
        for total, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, dimension - total + 1, cycle_length):
                next_coefficients[total + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[dimension]


def _unordered_tuple_classes(arity: int, dimension: int) -> int:
    numerator = sum(
        weight * _fixed_count_from_cycles(cycles, dimension)
        for _, weight, cycles in _endpoint_type_data(arity)
    )
    order = factorial(arity)
    assert numerator % order == 0
    return numerator // order


def _fixed_pair_class_count(trit_count: int, dimension: int) -> int:
    return (
        comb(trit_count, dimension)
        * _integer_power(2, dimension)
        * _integer_power(5, trit_count - dimension)
    )


def _direct_global_count(arity: int, trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _unordered_tuple_classes(arity, dimension)
        for dimension in range(trit_count + 1)
    )


def _polynomial_product(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for left_degree, left_value in enumerate(left):
        for right_degree, right_value in enumerate(right):
            result[left_degree + right_degree] += left_value * right_value
    return result


def _inverse_polynomial(polynomial: list[int], degree: int) -> list[int]:
    assert polynomial[0] == 1
    result = [0] * (degree + 1)
    result[0] = 1
    for index in range(1, degree + 1):
        result[index] = -sum(
            polynomial[offset] * result[index - offset]
            for offset in range(1, min(index, len(polynomial) - 1) + 1)
        )
    return result


def _cycle_transform_factor(cycle_length: int) -> list[int]:
    factor = [
        comb(cycle_length, degree) * _integer_power(-5, degree)
        for degree in range(cycle_length + 1)
    ]
    factor[cycle_length] -= _integer_power(2, cycle_length)
    return factor


def _global_fixed_count_from_transform(
    cycles: tuple[int, ...],
    trit_count: int,
) -> int:
    pattern_count = sum(cycles)
    denominator = [1]
    for cycle_length in cycles:
        denominator = _polynomial_product(
            denominator,
            _cycle_transform_factor(cycle_length),
        )
    inverse = _inverse_polynomial(denominator, trit_count)
    numerator = [
        comb(pattern_count - 1, degree) * _integer_power(-5, degree)
        for degree in range(min(pattern_count - 1, trit_count) + 1)
    ]
    return sum(
        value * inverse[trit_count - degree]
        for degree, value in enumerate(numerator)
    )


def _transformed_global_count(arity: int, trit_count: int) -> int:
    numerator = sum(
        weight * _global_fixed_count_from_transform(cycles, trit_count)
        for _, weight, cycles in _endpoint_type_data(arity)
    )
    order = factorial(arity)
    assert numerator % order == 0
    return numerator // order


def test_endpoint_partitions_match_all_permutation_cycle_types() -> None:
    """Classify every checked endpoint permutation by integer partition."""
    for arity in range(_MINIMUM_ARITY, _MAXIMUM_ARITY + 1):
        expected = {
            partition: _conjugacy_class_weight(partition)
            for partition in _integer_partitions(arity)
        }
        observed = Counter(
            _cycle_type(permutation)
            for permutation in permutations(range(arity))
        )
        assert len(expected) == _EXPECTED_PARTITION_COUNTS[arity]
        assert observed == Counter(expected)
        assert sum(expected.values()) == factorial(arity)
        for partition in expected:
            representative = _partition_representative(partition)
            assert _cycle_type(representative) == partition


def test_generic_unordered_tuple_burnside_counts_through_dimension_fourteen(
) -> None:
    """Reproduce and extend checked endpoint counts by generic Burnside."""
    for arity in range(_MINIMUM_ARITY, _MAXIMUM_ARITY + 1):
        pattern_count = 1 << arity
        for dimension in range(_MAXIMUM_TRITS + 1):
            unordered = _unordered_tuple_classes(arity, dimension)
            ordered = comb(dimension + pattern_count - 1, pattern_count - 1)
            assert 1 <= unordered <= ordered
        assert _unordered_tuple_classes(
            arity,
            _MAXIMUM_TRITS,
        ) == _WIDTH_FOURTEEN_LOCAL_COUNTS[arity]


def test_generic_global_unordered_tuple_transform_matches_direct_sum() -> None:
    """The generic binomial transform equals direct reachable-pair summation."""
    for arity in range(_MINIMUM_ARITY, _MAXIMUM_ARITY + 1):
        raw_local_mass = 5 + 2 * (1 << arity)
        for trit_count in range(1, _MAXIMUM_TRITS + 1):
            direct = _direct_global_count(arity, trit_count)
            transformed = _transformed_global_count(arity, trit_count)
            assert direct == transformed
            assert direct <= _integer_power(raw_local_mass, trit_count)
        assert _transformed_global_count(
            arity,
            _MAXIMUM_TRITS,
        ) == _WIDTH_FOURTEEN_GLOBAL_COUNTS[arity]


def _endpoint_label_orbit(
    labels: tuple[int, ...],
    arity: int,
) -> set[tuple[int, ...]]:
    return {
        tuple(sorted(_permuted_symbol(label, order) for label in labels))
        for order in permutations(range(arity))
    }


def _coordinate_orbit_mass(labels: tuple[int, ...]) -> int:
    multiplicities = Counter(labels)
    result = factorial(len(labels))
    for multiplicity in multiplicities.values():
        result //= factorial(multiplicity)
    return result


def _combined_orbit_mass(labels: tuple[int, ...], arity: int) -> int:
    return _coordinate_orbit_mass(labels) * len(
        _endpoint_label_orbit(labels, arity)
    )


def _check_small_combined_mass(arity: int, maximum_dimension: int) -> None:
    pattern_count = 1 << arity
    for dimension in range(maximum_dimension + 1):
        canonical: dict[tuple[int, ...], int] = {}
        for labels in combinations_with_replacement(
            range(pattern_count),
            dimension,
        ):
            orbit = _endpoint_label_orbit(labels, arity)
            representative = min(orbit)
            mass = _coordinate_orbit_mass(labels) * len(orbit)
            if representative not in canonical:
                canonical[representative] = mass
            assert canonical[representative] == mass
        assert sum(canonical.values()) == _integer_power(
            pattern_count,
            dimension,
        )


def test_generic_combined_orbit_mass_covers_small_tuple_domains() -> None:
    """Reconstruct small raw domains from exact combined orbit masses."""
    maximum_dimensions = {3: 3, 4: 2, 5: 2, 6: 2}
    for arity, maximum_dimension in maximum_dimensions.items():
        _check_small_combined_mass(arity, maximum_dimension)


def test_generic_combined_orbit_mass_reaches_checked_arity_eight() -> None:
    """Single-coordinate endpoint orbits have exact binomial mass through S8."""
    for arity in range(_MINIMUM_ARITY, _MAXIMUM_ARITY + 1):
        total = 0
        for weight in range(arity + 1):
            label = (1 << weight) - 1
            labels = (label,)
            assert _coordinate_orbit_mass(labels) == 1
            endpoint_mass = len(_endpoint_label_orbit(labels, arity))
            assert endpoint_mass == comb(arity, weight)
            assert _combined_orbit_mass(labels, arity) == endpoint_mass
            total += endpoint_mass
        assert total == 1 << arity


def _counts_from_labels(
    labels: tuple[int, ...],
    pattern_count: int,
) -> tuple[int, ...]:
    observed = Counter(labels)
    return tuple(observed.get(label, 0) for label in range(pattern_count))


def _ordered_class_rank(counts: tuple[int, ...]) -> int:
    separator_count = len(counts) - 1
    prefix = 0
    rank = 0
    for index in range(separator_count):
        prefix += counts[index]
        separator = prefix + index
        rank += comb(separator, index + 1)
    return rank


def _endpoint_canonical_rank(labels: tuple[int, ...], arity: int) -> int:
    pattern_count = 1 << arity
    return min(
        _ordered_class_rank(_counts_from_labels(image, pattern_count))
        for image in _endpoint_label_orbit(labels, arity)
    )


def _check_small_canonical_rank(arity: int, maximum_dimension: int) -> None:
    pattern_count = 1 << arity
    for dimension in range(maximum_dimension + 1):
        observed: dict[int, tuple[int, ...]] = {}
        for labels in combinations_with_replacement(
            range(pattern_count),
            dimension,
        ):
            representative = min(_endpoint_label_orbit(labels, arity))
            key = _endpoint_canonical_rank(labels, arity)
            if key not in observed:
                observed[key] = representative
            assert observed[key] == representative
        assert len(observed) == _unordered_tuple_classes(arity, dimension)


def test_endpoint_canonical_rank_is_exact_on_small_tuple_domains() -> None:
    """Canonical ordered ranks collide exactly on small endpoint orbits."""
    maximum_dimensions = {3: 3, 4: 2, 5: 2, 6: 2}
    for arity, maximum_dimension in maximum_dimensions.items():
        _check_small_canonical_rank(arity, maximum_dimension)


def test_endpoint_canonical_rank_reaches_checked_arity_eight() -> None:
    """One-coordinate canonical keys quotient labels by weight through S8."""
    for arity in range(_MINIMUM_ARITY, _MAXIMUM_ARITY + 1):
        keys_by_weight: dict[int, set[int]] = {}
        for label in range(1 << arity):
            weight = label.bit_count()
            key = _endpoint_canonical_rank((label,), arity)
            keys_by_weight.setdefault(weight, set()).add(key)
        assert set(keys_by_weight) == set(range(arity + 1))
        assert all(len(keys) == 1 for keys in keys_by_weight.values())
        assert len({next(iter(keys)) for keys in keys_by_weight.values()}) == (
            arity + 1
        )
