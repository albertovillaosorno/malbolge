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
#   - Independent evidence for black-box verifier-call lower bounds over finite
#     canonical candidate domains and checked crazy preimage tuple quotients.
# - Must-Not:
#   - Apply the lower bound to searches using richer candidate information,
#     direction-sensitive searches after endpoint quotienting, or runtime cost.
# - Allows:
#   - Inputs: finite candidate counts plus checked tuple arities/dimensions.
#   - Outputs: exact worst-case and expected verifier-call lower bounds.
#   - Side effects: none.
# - Split-When:
#   - A verifier exposes more than candidate-local binary validity evidence.
# - Merge-When:
#   - Another theorem owns the same finite black-box candidate-search model.
# - Summary:
#   - Lower-bound candidate-by-candidate verification after canonicalization.
# - Description:
#   - Exhausts small query orders and substitutes exact ordered/unordered tuple
#     quotient cardinalities through the checked mathematical domain.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Tuple arity reaches eight and ambiguity dimension reaches fourteen.
#

"""Evidence for finite canonical-search verifier-call lower bounds."""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from itertools import permutations
from itertools import product
from math import comb
from math import factorial

_MAXIMUM_ARITY = 8
_MAXIMUM_TRITS = 14
_MINIMUM_UNORDERED_ARITY = 3
_EXPECTED_ORDERED_ARITY_EIGHT = 84_466_573_066_471_253_216_128
_EXPECTED_UNORDERED_ARITY_EIGHT = 2_103_669_236_921_739_401
_EXPECTED_GLOBAL_ORDERED_ARITY_EIGHT = 7_093_373_076_831_030_274_633_041_897
_EXPECTED_GLOBAL_UNORDERED_ARITY_EIGHT = 178_151_458_860_093_866_748_569


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
    unseen = set(range(1 << len(endpoint_order)))
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


def _ordered_classes(arity: int, dimension: int) -> int:
    symbol_count = 1 << arity
    return comb(dimension + symbol_count - 1, symbol_count - 1)


def _unordered_classes(arity: int, dimension: int) -> int:
    numerator = 0
    for partition in _integer_partitions(arity):
        representative = _partition_representative(partition)
        numerator += _conjugacy_class_weight(partition) * (
            _fixed_count_from_cycles(
                _label_cycle_lengths(representative),
                dimension,
            )
        )
    order = factorial(arity)
    assert numerator % order == 0
    return numerator // order


def _calls_to_unique_target(order: tuple[int, ...], target: int) -> int:
    return order.index(target) + 1


def _mean_unique_target_calls(order: tuple[int, ...]) -> Fraction:
    size = len(order)
    return Fraction(
        sum(_calls_to_unique_target(order, target) for target in order),
        size,
    )


def _expected_calls(size: int) -> Fraction:
    return Fraction(size + 1, 2)


def test_every_small_deterministic_order_has_exact_black_box_bounds() -> None:
    """Every small candidate order has worst case R and mean (R+1)/2."""
    for size in range(1, 8):
        candidates = tuple(range(size))
        for order in permutations(candidates):
            calls = tuple(
                _calls_to_unique_target(order, target) for target in candidates
            )
            assert max(calls) == size
            assert _mean_unique_target_calls(order) == _expected_calls(size)


def test_uniform_random_order_attains_minimax_expectation() -> None:
    """Uniform random ordering attains the minimax averaging bound."""
    for size in range(1, 7):
        candidates = tuple(range(size))
        orders = tuple(permutations(candidates))
        expected = _expected_calls(size)
        for target in candidates:
            observed = Fraction(
                sum(_calls_to_unique_target(order, target) for order in orders),
                len(orders),
            )
            assert observed == expected


def test_negative_prefix_cannot_certify_absence_before_full_domain() -> None:
    """Any unqueried candidate remains a valid unique-solution adversary."""
    for size in range(1, 9):
        candidates = tuple(range(size))
        for queried_count in range(size):
            queried = set(candidates[:queried_count])
            unqueried = set(candidates) - queried
            assert unqueried
            for adversary_target in unqueried:
                assert adversary_target not in queried
        assert set(candidates[:size]) == set(candidates)


def test_checked_tuple_quotients_substitute_exact_verifier_bounds() -> None:
    """Checked tuple quotients provide exact finite-domain call bounds."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        for dimension in range(_MAXIMUM_TRITS + 1):
            ordered = _ordered_classes(arity, dimension)
            assert ordered >= 1
            assert _expected_calls(ordered) == Fraction(ordered + 1, 2)
            if arity < _MINIMUM_UNORDERED_ARITY:
                continue
            unordered = _unordered_classes(arity, dimension)
            assert 1 <= unordered <= ordered
            assert _expected_calls(unordered) == Fraction(unordered + 1, 2)
    assert _ordered_classes(8, 14) == _EXPECTED_ORDERED_ARITY_EIGHT
    assert _unordered_classes(8, 14) == _EXPECTED_UNORDERED_ARITY_EIGHT


def _fixed_pair_class_count(trit_count: int, dimension: int) -> int:
    return (
        comb(trit_count, dimension)
        * _integer_power(2, dimension)
        * _integer_power(5, trit_count - dimension)
    )


def _global_ordered_classes(arity: int, trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _ordered_classes(arity, dimension)
        for dimension in range(trit_count + 1)
    )


def _global_unordered_classes(arity: int, trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _unordered_classes(arity, dimension)
        for dimension in range(trit_count + 1)
    )


def _global_expected_calls(global_classes: int, pair_count: int) -> Fraction:
    return Fraction(global_classes + pair_count, 2)


def test_product_candidate_families_have_exact_aggregate_call_bounds() -> None:
    """Add worst and expected call bounds across finite domains."""
    for sizes in ((1,), (1, 2), (2, 3), (1, 2, 4)):
        orders = tuple(tuple(range(size)) for size in sizes)
        totals = tuple(
            sum(
                map(
                    _calls_to_unique_target,
                    orders,
                    targets,
                    strict=True,
                )
            )
            for targets in product(*(range(size) for size in sizes))
        )
        assert max(totals) == sum(sizes)
        assert Fraction(sum(totals), len(totals)) == sum(
            (_expected_calls(size) for size in sizes),
            start=Fraction(),
        )


def test_checked_global_tuple_counts_give_exact_aggregate_bounds() -> None:
    """Global quotient sums substitute exactly into aggregate call bounds."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        pair_count = _integer_power(7, trit_count)
        for arity in range(1, _MAXIMUM_ARITY + 1):
            ordered = _global_ordered_classes(arity, trit_count)
            assert ordered >= pair_count
            assert _global_expected_calls(ordered, pair_count) == Fraction(
                ordered + pair_count,
                2,
            )
            if arity < _MINIMUM_UNORDERED_ARITY:
                continue
            unordered = _global_unordered_classes(arity, trit_count)
            assert pair_count <= unordered <= ordered
            assert _global_expected_calls(unordered, pair_count) == Fraction(
                unordered + pair_count,
                2,
            )
    assert _global_ordered_classes(8, 14) == (
        _EXPECTED_GLOBAL_ORDERED_ARITY_EIGHT
    )
    assert _global_unordered_classes(8, 14) == (
        _EXPECTED_GLOBAL_UNORDERED_ARITY_EIGHT
    )


def _floor_log_two(value: int) -> int:
    assert value >= 1
    return value.bit_length() - 1


def _minimum_binary_worst_queries(hypotheses: int) -> int:
    if hypotheses <= 1:
        return 0
    return (hypotheses - 1).bit_length()


def _minimum_uniform_binary_mean(hypotheses: int) -> Fraction:
    assert hypotheses >= 1
    height = _floor_log_two(hypotheses)
    return Fraction(
        height * hypotheses
        + 2 * hypotheses
        - _integer_power(2, height + 1),
        hypotheses,
    )


def _optimal_uniform_binary_total_depth(hypotheses: int) -> int:
    totals = [0] * (hypotheses + 1)
    for size in range(2, hypotheses + 1):
        totals[size] = size + min(
            totals[left] + totals[size - left]
            for left in range(1, size)
        )
    return totals[hypotheses]


def test_binary_decision_tree_worst_depth_matches_leaf_capacity() -> None:
    """Binary identification needs exactly ceil(log2 R) worst-case questions."""
    for hypotheses in range(1, 257):
        depth = _minimum_binary_worst_queries(hypotheses)
        assert _integer_power(2, depth) >= hypotheses
        if depth > 0:
            assert _integer_power(2, depth - 1) < hypotheses


def test_uniform_binary_mean_matches_optimal_small_decision_trees() -> None:
    """Closed uniform mean matches split dynamic programs."""
    for hypotheses in range(1, 65):
        total_depth = _optimal_uniform_binary_total_depth(hypotheses)
        assert Fraction(total_depth, hypotheses) == (
            _minimum_uniform_binary_mean(hypotheses)
        )


def test_balanced_binary_leaf_depths_realize_exact_uniform_mean() -> None:
    """Depth h/h+1 leaf counts satisfy Kraft equality and the exact mean."""
    for hypotheses in range(1, 257):
        height = _floor_log_two(hypotheses)
        short = _integer_power(2, height + 1) - hypotheses
        long = 2 * hypotheses - _integer_power(2, height + 1)
        assert short >= 0
        assert long >= 0
        assert short + long == hypotheses
        kraft = Fraction(short, _integer_power(2, height))
        kraft += Fraction(long, _integer_power(2, height + 1))
        assert kraft == 1
        mean = Fraction(short * height + long * (height + 1), hypotheses)
        assert mean == _minimum_uniform_binary_mean(hypotheses)


def test_checked_tuple_counts_substitute_binary_information_bounds() -> None:
    """Tuple quotient sizes give exact checked binary-question lower bounds."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        for dimension in range(_MAXIMUM_TRITS + 1):
            ordered = _ordered_classes(arity, dimension)
            assert _minimum_binary_worst_queries(ordered) <= ordered - 1
            ordered_binary_mean = _minimum_uniform_binary_mean(ordered)
            assert ordered_binary_mean <= _expected_calls(ordered)
            if arity < _MINIMUM_UNORDERED_ARITY:
                continue
            unordered = _unordered_classes(arity, dimension)
            assert _minimum_binary_worst_queries(unordered) <= unordered - 1
            assert _minimum_uniform_binary_mean(unordered) <= (
                _expected_calls(unordered)
            )
