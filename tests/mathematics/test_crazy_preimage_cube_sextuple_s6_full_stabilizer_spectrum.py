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
#   - Exact subgroup-conjugacy and automorphism-stabilizer evidence for the
#     all-equal top-level S6 residual stratum.
# - Must-Not:
#   - Claim dense rank/unrank for the full-S6 residual quotient.
# - Allows:
#   - Inputs: 52-label residual scalar assignments of mass zero through
#     fourteen.
#   - Outputs: exact stabilizer spectra, rooted-view multiplicities, and
#     normalizer-quotient bounds.
#   - Side effects: none.
# - Split-When:
#   - Dense exact-stabilizer rank/unrank is added for one or more subgroup
#     types.
# - Merge-When:
#   - Complete full-S6 ranking owns the same stabilizer lattice evidence.
# - Summary:
#   - Invert the 56 S6 subgroup conjugacy classes on the 52 residual labels.
# - Description:
#   - Uses conjugate-containment incidence instead of enumerating all subgroups
#     independently during inversion.
# - Usage:
#   - Exact symmetric-exception prerequisite for the top-level `(6)` rank.
# - Defaults:
#   - Stabilizer and rooted-view spectra are checked through residual mass 14.
#

"""Exact stabilizer spectrum for the all-equal full-S6 residual quotient."""

from __future__ import annotations

from collections import defaultdict
from collections import deque
from functools import cache
from itertools import permutations
from math import comb
from typing import cast

_ARITY = 6
_S6_ORDER = 720
_MAXIMUM_MASS = 14
_EXPECTED_SUBGROUP_CONJUGACY_CLASSES = 56
_EXPECTED_SUBGROUPS = 1_455
_EXPECTED_UNROOTED_COUNTS = (
    1,
    5,
    28,
    178,
    1_268,
    9_476,
    70_922,
    511_459,
    3_480_079,
    22_130_232,
    131_252_006,
    727_284_758,
    3_778_300_228,
    18_478_372_801,
    85_431_118_919,
)
_EXPECTED_ROOTED_COUNTS = (
    1,
    8,
    67,
    588,
    5_257,
    45_642,
    374_027,
    2_845_008,
    19_961_731,
    129_216_492,
    774_402_196,
    4_317_877_538,
    22_516_940_260,
    110_382_248_928,
    511_090_971_734,
)
_EXPECTED_ORDER_SPECTRUM = {
    1: 84_008_008_841,
    2: 1_393_126_516,
    3: 4_348,
    4: 28_256_324,
    6: 1_062_763,
    8: 432_963,
    10: 155,
    12: 208_830,
    16: 10_731,
    24: 2_119,
    36: 2_745,
    48: 2_374,
    60: 5,
    72: 135,
    120: 55,
    720: 15,
}
_EXPECTED_ROOTED_TRIVIAL_COUNTS = (
    0,
    0,
    0,
    40,
    1_340,
    21_462,
    242_629,
    2_204_012,
    17_109_191,
    117_488_832,
    729_410_921,
    4_155_525_962,
    21_962_281_262,
    108_578_479_120,
    505_481_889_514,
)
_EXPECTED_PAIR_TRIVIAL_COUNTS = (
    0,
    0,
    0,
    0,
    10,
    156,
    1_315,
    8_260,
    42_975,
    195_100,
    796_976,
    2_987_812,
    10_420_165,
    34_143_362,
    105_908_244,
)
_EXPECTED_PAIR_TRIVIAL_FULL_COUNTS = (
    0,
    0,
    0,
    0,
    10,
    376,
    7_277,
    96_898,
    999_634,
    8_523_090,
    62_536_621,
    405_870_644,
    2_376_530_747,
    12_741_994_672,
    63_276_927_716,
)
_EXPECTED_PAIR_SYMMETRY_REMAINDER = 20_731_081_125
_EXPECTED_TRIVIAL_S6_COUNTS = (
    0,
    0,
    0,
    1,
    140,
    2_862,
    35_852,
    342_833,
    2_736_824,
    19_096_210,
    119_677_202,
    685_705_809,
    3_636_776_469,
    18_019_551_259,
    84_008_008_841,
)
_EXPECTED_ROOTED_TRIVIAL_SYMMETRIC = (
    0,
    0,
    0,
    34,
    500,
    4_290,
    27_517,
    147_014,
    688_247,
    2_911_572,
    11_347_709,
    41_291_108,
    141_622_448,
    461_171_566,
    1_433_836_468,
)
_EXPECTED_ROOTED_VIEW_SPECTRUM = {
    1: 1_046,
    2: 91_227,
    3: 4_215_311,
    4: 63_923_215,
    5: 1_354_879_279,
    6: 84_008_008_841,
}
_EXPECTED_NORMALIZER_QUOTIENT_TYPE_COUNTS = {
    1: 8,
    2: 11,
    4: 5,
    6: 4,
    8: 1,
    12: 3,
    24: 2,
}
_EXPECTED_SYMMETRIC_CLASSES = 1_423_110_078
_EXPECTED_ROOT_DEFICIT = 1_495_741_780
_MAX_NORMALIZER_QUOTIENT = 24
_MASS_FIFTEEN = 15
_EXPECTED_MASS_FIFTEEN_UNROOTED = 374_868_922_598
_EXPECTED_MASS_FIFTEEN_ORDER_SPECTRUM = {
    1: 370_630_073_601,
    2: 4_171_439_245,
    3: 8_433,
    4: 64_079_419,
    6: 2_142_281,
    8: 798_444,
    10: 286,
    12: 354_004,
    16: 16_282,
    24: 3_226,
    36: 3_891,
    48: 3_220,
    60: 6,
    72: 168,
    120: 74,
    720: 18,
}
_EXPECTED_MASS_FIFTEEN_ROOTED_VIEW_SPECTRUM = {
    1: 1_528,
    2: 156_417,
    3: 9_408_998,
    4: 156_173_192,
    5: 4_073_108_862,
    6: 370_630_073_601,
}
_EXPECTED_POPULATED_STABILIZER_TYPES = 35


type _Permutation = tuple[int, int, int, int, int, int]
type _Subgroup = frozenset[int]
type _OrbitSizes = tuple[int, ...]
type _SpectrumRow = tuple[
    int,
    int,
    int,
    int,
    _OrbitSizes,
    _OrbitSizes,
    int,
]

_PERMUTATIONS = cast(
    "tuple[_Permutation, ...]",
    tuple(permutations(range(_ARITY))),
)
_PERMUTATION_INDEX = {
    permutation: index for index, permutation in enumerate(_PERMUTATIONS)
}
_IDENTITY = _PERMUTATION_INDEX[0, 1, 2, 3, 4, 5]
_MULTIPLICATION = tuple(
    tuple(
        _PERMUTATION_INDEX[
            cast(
                "_Permutation",
                tuple(
                    _PERMUTATIONS[left][_PERMUTATIONS[right][index]]
                    for index in range(_ARITY)
                ),
            )
        ]
        for right in range(_S6_ORDER)
    )
    for left in range(_S6_ORDER)
)


def _inverse(element: int) -> int:
    permutation = _PERMUTATIONS[element]
    result = [0] * _ARITY
    for source, destination in enumerate(permutation):
        result[destination] = source
    return _PERMUTATION_INDEX[cast("_Permutation", tuple(result))]


_INVERSES = tuple(_inverse(element) for element in range(_S6_ORDER))


def _products(left: int, generators: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        product
        for right in generators
        for product in (
            _MULTIPLICATION[left][right],
            _MULTIPLICATION[right][left],
        )
    )


@cache
def _generated(generators: tuple[int, ...]) -> _Subgroup:
    generators = tuple(sorted(set(generators)))
    subgroup = {_IDENTITY}
    frontier = deque([_IDENTITY])
    while frontier:
        left = frontier.popleft()
        for product in _products(left, generators):
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return frozenset(subgroup)


def _conjugate(subgroup: _Subgroup, element: int) -> _Subgroup:
    inverse = _INVERSES[element]
    return frozenset(
        _MULTIPLICATION[_MULTIPLICATION[element][item]][inverse]
        for item in subgroup
    )


@cache
def _canonical_subgroup(subgroup: _Subgroup) -> _Subgroup:
    canonical = min(
        tuple(sorted(_conjugate(subgroup, element)))
        for element in range(_S6_ORDER)
    )
    return frozenset(canonical)


@cache
def _subgroup_generators(subgroup: _Subgroup) -> tuple[int, ...]:
    generators: list[int] = []
    generated = frozenset({_IDENTITY})
    for element in sorted(subgroup):
        if element in generated:
            continue
        generators.append(element)
        generated = _generated(tuple(generators))
        if generated == subgroup:
            break
    return tuple(generators)


@cache
def _subgroup_conjugacy_classes() -> tuple[_Subgroup, ...]:
    identity = _canonical_subgroup(frozenset({_IDENTITY}))
    known = {identity}
    frontier = [identity]
    while frontier:
        subgroup = frontier.pop()
        generators = _subgroup_generators(subgroup)
        for element in range(_S6_ORDER):
            if element in subgroup:
                continue
            candidate = _canonical_subgroup(_generated((*generators, element)))
            if candidate in known:
                continue
            known.add(candidate)
            frontier.append(candidate)
    return tuple(sorted(known, key=lambda group: (-len(group), tuple(group))))


@cache
def _conjugates(subgroup: _Subgroup) -> tuple[_Subgroup, ...]:
    return tuple({
        _conjugate(subgroup, element) for element in range(_S6_ORDER)
    })


@cache
def _containment_incidence(contained: _Subgroup, container: _Subgroup) -> int:
    if len(container) < len(contained):
        return 0
    return sum(
        1 for conjugate in _conjugates(container) if contained <= conjugate
    )


_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)


def _permuted_symbol(symbol: int, element: int) -> int:
    order = _PERMUTATIONS[element]
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


@cache
def _label_orbit_sizes(subgroup: _Subgroup) -> _OrbitSizes:
    unseen = set(_RESIDUAL_LABELS)
    sizes: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_permuted_symbol(seed, element) for element in subgroup}
        unseen -= orbit
        sizes.append(len(orbit))
    return tuple(sorted(sizes))


@cache
def _vertex_orbit_sizes(subgroup: _Subgroup) -> _OrbitSizes:
    unseen = set(range(_ARITY))
    sizes: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_PERMUTATIONS[element][seed] for element in subgroup}
        unseen -= orbit
        sizes.append(len(orbit))
    return tuple(sorted(sizes, reverse=True))


@cache
def _fixed_count(subgroup: _Subgroup, total: int) -> int:
    coefficients = [1] + [0] * total
    for orbit_size in _label_orbit_sizes(subgroup):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, orbit_size):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


@cache
def _exact_assignment_counts(total: int) -> dict[_Subgroup, int]:
    exact: dict[_Subgroup, int] = {}
    for subgroup in _subgroup_conjugacy_classes():
        value = _fixed_count(subgroup, total)
        for larger, exact_value in exact.items():
            if len(larger) <= len(subgroup):
                continue
            value -= _containment_incidence(subgroup, larger) * exact_value
        assert value >= 0
        exact[subgroup] = value
    return exact


@cache
def _spectrum_rows(total: int) -> tuple[_SpectrumRow, ...]:
    rows: list[_SpectrumRow] = []
    for subgroup, exact_per_subgroup in _exact_assignment_counts(total).items():
        if exact_per_subgroup == 0:
            continue
        normalizer = _S6_ORDER // len(_conjugates(subgroup))
        numerator = exact_per_subgroup * len(subgroup)
        assert numerator % normalizer == 0
        orbit_count = numerator // normalizer
        if orbit_count == 0:
            continue
        rows.append((
            orbit_count,
            len(subgroup),
            normalizer,
            normalizer // len(subgroup),
            _vertex_orbit_sizes(subgroup),
            _label_orbit_sizes(subgroup),
            exact_per_subgroup,
        ))
    return tuple(rows)


def _order_spectrum(total: int) -> dict[int, int]:
    result: defaultdict[int, int] = defaultdict(int)
    for orbit_count, order, *_ in _spectrum_rows(total):
        result[order] += orbit_count
    return dict(sorted(result.items()))


def _rooted_view_spectrum(total: int) -> dict[int, int]:
    result: defaultdict[int, int] = defaultdict(int)
    for orbit_count, _, _, _, vertex_orbits, _, _ in _spectrum_rows(total):
        result[len(vertex_orbits)] += orbit_count
    return dict(sorted(result.items()))


_K6_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_K6_EDGE_INDEX = {edge: index for index, edge in enumerate(_K6_EDGES)}


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


_K6_EDGE_MAPS = tuple(
    tuple(
        _K6_EDGE_INDEX[
            _ordered_edge(
                _PERMUTATIONS[element][left],
                _PERMUTATIONS[element][right],
            )
        ]
        for left, right in _K6_EDGES
    )
    for element in range(_S6_ORDER)
)


@cache
def _pair_edge_orbit_sizes(subgroup: _Subgroup) -> tuple[int, ...]:
    unseen = set(range(len(_K6_EDGES)))
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_K6_EDGE_MAPS[element][seed] for element in subgroup}
        unseen -= orbit
        result.append(len(orbit))
    return tuple(sorted(result))


@cache
def _pair_fixed_count(subgroup: _Subgroup, total: int) -> int:
    coefficients = [1] + [0] * total
    for orbit_size in _pair_edge_orbit_sizes(subgroup):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for pair_mass in range((total - degree) // orbit_size + 1):
                addition = pair_mass * orbit_size
                next_coefficients[degree + addition] += coefficient * (
                    pair_mass + 1
                )
        coefficients = next_coefficients
    return coefficients[total]


@cache
def _pair_exact_assignment_counts(total: int) -> dict[_Subgroup, int]:
    exact: dict[_Subgroup, int] = {}
    for subgroup in _subgroup_conjugacy_classes():
        value = _pair_fixed_count(subgroup, total)
        for larger, exact_value in exact.items():
            if len(larger) > len(subgroup):
                value -= _containment_incidence(subgroup, larger) * exact_value
        assert value >= 0
        exact[subgroup] = value
    return exact


def _pair_trivial_count(total: int) -> int:
    identity = next(
        subgroup
        for subgroup in _subgroup_conjugacy_classes()
        if len(subgroup) == 1
    )
    exact = _pair_exact_assignment_counts(total)[identity]
    assert exact % _S6_ORDER == 0
    return exact // _S6_ORDER


def _pair_trivial_full_count(total: int) -> int:
    return sum(
        (fixed_mass + 1)
        * _pair_trivial_count(pair_mass)
        * comb(total - fixed_mass - pair_mass + 19, 19)
        for fixed_mass in range(total + 1)
        for pair_mass in range(total - fixed_mass + 1)
    )


def _trivial_point_orbit_count(subgroup: _Subgroup) -> int:
    unseen = set(range(_ARITY))
    result = 0
    while unseen:
        root = min(unseen)
        orbit = {_PERMUTATIONS[element][root] for element in subgroup}
        unseen -= orbit
        point_stabilizer = sum(
            _PERMUTATIONS[element][root] == root for element in subgroup
        )
        if point_stabilizer == 1:
            result += 1
    return result


def _rooted_trivial_counts(total: int) -> tuple[int, int]:
    rooted = 0
    symmetric = 0
    for subgroup, exact_per_subgroup in _exact_assignment_counts(total).items():
        if exact_per_subgroup == 0:
            continue
        normalizer = _S6_ORDER // len(_conjugates(subgroup))
        numerator = exact_per_subgroup * len(subgroup)
        assert numerator % normalizer == 0
        orbit_count = numerator // normalizer
        contribution = orbit_count * _trivial_point_orbit_count(subgroup)
        rooted += contribution
        if len(subgroup) != 1:
            symmetric += contribution
    return rooted, symmetric


def _stabilizer_signature(row: _SpectrumRow) -> tuple[object, ...]:
    _, order, normalizer, quotient, vertex_orbits, label_orbits, _ = row
    return order, normalizer, quotient, vertex_orbits, label_orbits


def test_s6_has_exact_subgroup_conjugacy_lattice() -> None:
    """S6 has 56 subgroup conjugacy classes containing 1,455 subgroups."""
    classes = _subgroup_conjugacy_classes()
    assert len(classes) == _EXPECTED_SUBGROUP_CONJUGACY_CLASSES
    assert (
        sum(len(_conjugates(group)) for group in classes) == _EXPECTED_SUBGROUPS
    )
    all_subgroups = {
        subgroup
        for representative in classes
        for subgroup in _conjugates(representative)
    }
    assert len(all_subgroups) == _EXPECTED_SUBGROUPS
    assert all(_containment_incidence(group, group) == 1 for group in classes)


def test_s6_stabilizer_inversion_reconstructs_reviewed_counts() -> None:
    """Exact stabilizers recover both unrooted S6 and rooted S5 sequences."""
    unrooted: list[int] = []
    rooted: list[int] = []
    for total in range(_MAXIMUM_MASS + 1):
        rows = _spectrum_rows(total)
        unrooted.append(sum(row[0] for row in rows))
        rooted.append(sum(row[0] * len(row[4]) for row in rows))
    assert tuple(unrooted) == _EXPECTED_UNROOTED_COUNTS
    assert tuple(rooted) == _EXPECTED_ROOTED_COUNTS


def test_s6_rooted_trivial_classes_split_full_s6_trivial_and_symmetric() -> (
    None
):
    """Trivial point stabilizers split into full-S6 free and symmetric roots."""
    observed = tuple(_rooted_trivial_counts(total) for total in range(15))
    assert (
        tuple(value[0] for value in observed) == _EXPECTED_ROOTED_TRIVIAL_COUNTS
    )
    assert (
        tuple(value[1] for value in observed)
        == _EXPECTED_ROOTED_TRIVIAL_SYMMETRIC
    )
    for total, (rooted, symmetric) in enumerate(observed):
        full_free = rooted - symmetric
        assert full_free == _ARITY * _order_spectrum(total).get(1, 0)


def test_s6_pair_trivial_factor_covers_most_free_mass_fourteen() -> None:
    """A trivial pair-valued K6 edge graph fixes all endpoint orientation."""
    pair = tuple(_pair_trivial_count(total) for total in range(15))
    full = tuple(_pair_trivial_full_count(total) for total in range(15))
    assert pair == _EXPECTED_PAIR_TRIVIAL_COUNTS
    assert full == _EXPECTED_PAIR_TRIVIAL_FULL_COUNTS
    assert all(
        covered <= trivial
        for covered, trivial in zip(
            full, _EXPECTED_TRIVIAL_S6_COUNTS, strict=True
        )
    )
    assert (
        _EXPECTED_TRIVIAL_S6_COUNTS[-1] - full[-1]
        == _EXPECTED_PAIR_SYMMETRY_REMAINDER
    )


def test_s6_six_distinct_rooted_trivial_views_select_exactly_free_orbits() -> (
    None
):
    """Exactly trivial S6 stabilizers have six distinct rooted-trivial views."""
    classes = _subgroup_conjugacy_classes()
    assert all(
        (_trivial_point_orbit_count(group) == _ARITY) == (len(group) == 1)
        for group in classes
    )
    observed = tuple(_order_spectrum(total).get(1, 0) for total in range(15))
    assert observed == _EXPECTED_TRIVIAL_S6_COUNTS
    for total, selected in enumerate(observed):
        rooted, symmetric = _rooted_trivial_counts(total)
        assert rooted - symmetric == _ARITY * selected


def test_s6_mass_fourteen_exact_stabilizer_order_spectrum() -> None:
    """Mass fourteen has the reviewed exact automorphism-order spectrum."""
    assert _order_spectrum(_MAXIMUM_MASS) == _EXPECTED_ORDER_SPECTRUM
    assert (
        sum(_EXPECTED_ORDER_SPECTRUM.values()) == _EXPECTED_UNROOTED_COUNTS[-1]
    )
    assert (
        _EXPECTED_UNROOTED_COUNTS[-1] - _EXPECTED_ORDER_SPECTRUM[1]
        == _EXPECTED_SYMMETRIC_CLASSES
    )


def test_s6_mass_fourteen_rooted_view_multiplicity_spectrum() -> None:
    """Automorphism vertex orbits reconstruct the rooted quotient exactly."""
    spectrum = _rooted_view_spectrum(_MAXIMUM_MASS)
    assert spectrum == _EXPECTED_ROOTED_VIEW_SPECTRUM
    assert sum(spectrum.values()) == _EXPECTED_UNROOTED_COUNTS[-1]
    assert (
        sum(multiplicity * count for multiplicity, count in spectrum.items())
        == _EXPECTED_ROOTED_COUNTS[-1]
    )
    assert (
        sum(
            (_ARITY - multiplicity) * count
            for multiplicity, count in spectrum.items()
        )
        == _EXPECTED_ROOT_DEFICIT
    )
    assert spectrum[_ARITY] == _EXPECTED_ORDER_SPECTRUM[1]


def test_s6_mass_fifteen_preserves_populated_stabilizer_types() -> None:
    """Mass 15 changes multiplicities but introduces no new stabilizer type."""
    rows_fourteen = _spectrum_rows(_MAXIMUM_MASS)
    rows_fifteen = _spectrum_rows(_MASS_FIFTEEN)
    assert len(rows_fourteen) == _EXPECTED_POPULATED_STABILIZER_TYPES
    assert len(rows_fifteen) == _EXPECTED_POPULATED_STABILIZER_TYPES
    assert {_stabilizer_signature(row) for row in rows_fifteen} == {
        _stabilizer_signature(row) for row in rows_fourteen
    }
    assert (
        sum(row[0] for row in rows_fifteen) == _EXPECTED_MASS_FIFTEEN_UNROOTED
    )
    assert (
        _order_spectrum(_MASS_FIFTEEN) == _EXPECTED_MASS_FIFTEEN_ORDER_SPECTRUM
    )
    assert _rooted_view_spectrum(_MASS_FIFTEEN) == (
        _EXPECTED_MASS_FIFTEEN_ROOTED_VIEW_SPECTRUM
    )


def test_s6_symmetric_normalizer_quotients_are_bounded() -> None:
    """Symmetric mass-14 types use normalizer quotients of order at most 24."""
    observed: defaultdict[int, int] = defaultdict(int)
    for _, order, _, quotient, *_ in _spectrum_rows(_MAXIMUM_MASS):
        if order != 1:
            observed[quotient] += 1
    assert (
        dict(sorted(observed.items()))
        == _EXPECTED_NORMALIZER_QUOTIENT_TYPE_COUNTS
    )
    assert max(observed) == _MAX_NORMALIZER_QUOTIENT
