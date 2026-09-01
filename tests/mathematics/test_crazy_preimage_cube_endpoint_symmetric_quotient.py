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
#   - Independent evidence for endpoint-symmetric crazy preimage-cube pair
#     orbits.
# - Must-Not:
#   - Apply endpoint-swap equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact endpoint-symmetric pair classes and representatives.
#   - Side effects: none.
# - Split-When:
#   - A larger pair-symmetry group needs a distinct orbit classification.
# - Merge-When:
#   - Another proof owns simultaneous coordinate permutation plus endpoint swap.
# - Summary:
#   - Quotient coordinate-symmetric ordered pairs further by endpoint swap.
# - Description:
#   - Exhausts small pairs and independently lifts canonical representatives.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Pair enumeration stops at dimension eight; lifting stops at width four.
#

"""Evidence for endpoint-symmetric crazy preimage-cube pair quotients."""

from __future__ import annotations

from collections import Counter

_BINARY_RADIX = 2
_EXHAUSTIVE_DIMENSION = 8
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


def _integer_factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _integer_binomial(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for index in range(1, k + 1):
        result = result * (n - k + index) // index
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


def _swap_counts(
    counts: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    n00, n01, n10, n11 = counts
    return n00, n10, n01, n11


def _canonical_counts(
    counts: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if counts[1] <= counts[2]:
        return counts
    return _swap_counts(counts)


def _canonicalizing_order(
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


def _permute(code: int, order: tuple[int, ...]) -> int:
    result = 0
    for destination, source in enumerate(order):
        result |= ((code >> source) & 1) << destination
    return result


def _bit_mask(width: int) -> int:
    return (1 << width) - 1


def _canonical_pair(
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


def _ordered_orbit_size(counts: tuple[int, int, int, int]) -> int:
    result = _integer_factorial(sum(counts))
    for count in counts:
        result //= _integer_factorial(count)
    return result


def _endpoint_symmetric_orbit_size(
    counts: tuple[int, int, int, int],
) -> int:
    result = _ordered_orbit_size(counts)
    if counts[1] != counts[2]:
        result *= 2
    return result


def _swap_fixed_class_count(dimension: int) -> int:
    return ((dimension + 2) * (dimension + 2)) // 4


def _endpoint_symmetric_class_count(dimension: int) -> int:
    ordered = _integer_binomial(dimension + 3, 3)
    return (ordered + _swap_fixed_class_count(dimension)) // 2


def _canonicalize_pair(
    left: int,
    right: int,
    dimension: int,
) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    counts = _joint_counts(left, right, dimension)
    if counts[1] > counts[2]:
        left, right = right, left
        counts = _swap_counts(counts)
    order = _canonicalizing_order(left, right, dimension)
    return (_permute(left, order), _permute(right, order)), counts


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


def _trit_distance(left: int, right: int, trit_count: int) -> int:
    distance = 0
    for _ in range(trit_count):
        distance += left % _RADIX != right % _RADIX
        left //= _RADIX
        right //= _RADIX
    return distance


def _check_endpoint_pair(
    left: int,
    right: int,
    dimension: int,
) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    canonical, counts = _canonicalize_pair(left, right, dimension)
    swapped, swapped_counts = _canonicalize_pair(right, left, dimension)
    assert swapped == canonical
    assert swapped_counts == counts
    assert counts == _canonical_counts(_joint_counts(left, right, dimension))
    assert canonical == _canonical_pair(counts)
    weights = left.bit_count(), right.bit_count()
    distance = (left ^ right).bit_count()
    assert (max(weights), min(weights), distance) == (
        counts[2] + counts[3],
        counts[1] + counts[3],
        counts[1] + counts[2],
    )
    return canonical, counts


def test_endpoint_symmetric_pair_orbits_are_exact_through_dimension_eight() -> (
    None
):
    """Small pair orbits collapse exactly under coordinate and endpoint swap."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        observed: Counter[tuple[int, int, int, int]] = Counter()
        representatives: set[tuple[int, int]] = set()
        for left in range(size):
            for right in range(size):
                canonical, counts = _check_endpoint_pair(
                    left,
                    right,
                    dimension,
                )
                observed[counts] += 1
                representatives.add(canonical)
        canonical_counts = {
            _canonical_counts(counts)
            for counts in _joint_count_vectors(dimension)
        }
        expected = Counter({
            counts: _endpoint_symmetric_orbit_size(counts)
            for counts in canonical_counts
        })
        assert observed == expected
        assert len(representatives) == _endpoint_symmetric_class_count(
            dimension
        )


def test_endpoint_symmetric_counts_cover_through_dimension_fourteen() -> None:
    """Closed-form class and orbit counts cover every checked ordered pair."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        vectors = _joint_count_vectors(dimension)
        fixed = sum(counts[1] == counts[2] for counts in vectors)
        assert fixed == _swap_fixed_class_count(dimension)
        canonical_counts = {_canonical_counts(counts) for counts in vectors}
        assert len(canonical_counts) == _endpoint_symmetric_class_count(
            dimension
        )
        assert (
            sum(
                _endpoint_symmetric_orbit_size(counts)
                for counts in canonical_counts
            )
            == 4**dimension
        )


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
    for left in range(1 << dimension):
        for right in range(1 << dimension):
            distance = _trit_distance(words[left], words[right], trit_count)
            canonical, counts = _canonicalize_pair(left, right, dimension)
            canonical_left = _cube_data(choices, canonical[0])
            canonical_right = _cube_data(choices, canonical[1])
            assert _crazy(canonical_left, accumulator, trit_count) == target
            assert _crazy(canonical_right, accumulator, trit_count) == target
            assert (
                _trit_distance(
                    canonical_left,
                    canonical_right,
                    trit_count,
                )
                == distance
                == counts[1] + counts[2]
            )


def test_endpoint_symmetric_quotient_lifts_to_small_reachable_pairs() -> None:
    """Endpoint-symmetric canonical pairs remain valid fixed-pair preimages."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_fixed_pair_lifting(target, accumulator, trit_count)


def _canonical_count_block_size(residual: int) -> int:
    return ((residual + 2) * (residual + 2)) // 4


def _canonical_count_prefix(dimension: int, n00: int) -> int:
    return sum(
        _canonical_count_block_size(dimension - earlier_n00)
        for earlier_n00 in range(n00)
    )


def _canonical_count_rank(
    counts: tuple[int, int, int, int],
) -> int | None:
    n00, n01, n10, _ = counts
    if min(counts) < 0 or n01 > n10:
        return None
    dimension = sum(counts)
    residual = dimension - n00
    return (
        _canonical_count_prefix(dimension, n00)
        + n01 * (residual - n01 + 2)
        + (n10 - n01)
    )


def _unrank_canonical_count_row(
    residual: int,
    rank: int,
) -> tuple[int, int, int]:
    residual_rank = rank
    for n01 in range((residual // 2) + 1):
        row_size = residual - 2 * n01 + 1
        if residual_rank >= row_size:
            residual_rank -= row_size
            continue
        n10 = n01 + residual_rank
        return n01, n10, residual - n01 - n10
    raise AssertionError


def _canonical_count_unrank(
    dimension: int,
    rank: int,
) -> tuple[int, int, int, int] | None:
    class_count = _endpoint_symmetric_class_count(dimension)
    if rank < 0 or rank >= class_count:
        return None
    residual_rank = rank
    for n00 in range(dimension + 1):
        residual = dimension - n00
        block_size = _canonical_count_block_size(residual)
        if residual_rank >= block_size:
            residual_rank -= block_size
            continue
        n01, n10, n11 = _unrank_canonical_count_row(residual, residual_rank)
        return n00, n01, n10, n11
    raise AssertionError


def test_endpoint_symmetric_count_rank_is_dense() -> None:
    """Every checked endpoint-symmetric class receives one dense rank."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        canonical = tuple(
            counts
            for counts in _joint_count_vectors(dimension)
            if counts[1] <= counts[2]
        )
        ranks = tuple(_canonical_count_rank(counts) for counts in canonical)
        assert len(canonical) == _endpoint_symmetric_class_count(dimension)
        assert ranks == tuple(range(len(canonical)))
        assert tuple(
            _canonical_count_unrank(dimension, rank)
            for rank in range(len(canonical))
        ) == canonical


def test_endpoint_symmetric_count_rank_rejects_noncanonical_inputs() -> None:
    """Rank and unrank fail closed outside the checked canonical domain."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        class_count = _endpoint_symmetric_class_count(dimension)
        assert _canonical_count_unrank(dimension, -1) is None
        assert _canonical_count_unrank(dimension, class_count) is None
        if dimension == 0:
            continue
        assert _canonical_count_rank((-1, 0, 0, dimension + 1)) is None
        assert _canonical_count_rank((0, 1, 0, dimension - 1)) is None


def test_endpoint_symmetric_rank_preserves_canonical_pair_identity() -> None:
    """Raw swapped/coordinate-equivalent pairs land on the same dense rank."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        cube_size = 1 << dimension
        observed: dict[tuple[int, int], int] = {}
        for left in range(cube_size):
            for right in range(cube_size):
                canonical_pair, counts = _canonicalize_pair(
                    left,
                    right,
                    dimension,
                )
                rank = _canonical_count_rank(counts)
                assert rank is not None
                assert _canonical_count_unrank(dimension, rank) == counts
                previous = observed.setdefault(canonical_pair, rank)
                assert previous == rank
        assert set(observed.values()) == set(
            range(_endpoint_symmetric_class_count(dimension))
        )
