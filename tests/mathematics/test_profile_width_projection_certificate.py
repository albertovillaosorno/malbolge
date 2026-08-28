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
#   - Executable evidence for checked profile-width projection and certificates.
# - Must-Not:
#   - Treat value bounds or source size alone as a semantic narrowing proof.
# - Allows:
#   - Inputs: width pairs 10 through 14 and finite deterministic certificates.
#   - Outputs: exact projection identities and fail-closed certificate results.
#   - Side effects: none.
# - Split-When:
#   - Product width selection or an unbounded proof system gains its own owner.
# - Merge-When:
#   - Another test owns the same width-projection and finite-relation evidence.
# - Summary:
#   - Check exact width projection laws and finite bisimulation certificates.
# - Description:
#   - Separates commuting primitives from width-sensitive counterexamples.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Missing states, edges, observations, or inputs invalidate a certificate.
#

"""Evidence for checked profile-width projection and narrowing certificates."""

from __future__ import annotations

from itertools import combinations
from itertools import product

from algorithms.profile_width.certificate import CANONICAL_WIDTH
from algorithms.profile_width.certificate import FiniteSystem
from algorithms.profile_width.certificate import MINIMUM_WIDTH
from algorithms.profile_width.certificate import certificate_valid
from algorithms.profile_width.certificate import minimum_certified_width

_RADIX = 3
_BYTE_MODULUS = 256


def _power(exponent: int) -> int:
    value = 1
    for _ in range(exponent):
        value *= _RADIX
    return value


def _modulus(width: int) -> int:
    return _power(width)


def _project(value: int, width: int) -> int:
    return value % _modulus(width)


def _rotate(value: int, width: int) -> int:
    modulus = _modulus(width)
    return value // _RADIX + value % _RADIX * (modulus // _RADIX)


def _successor(value: int, width: int) -> int:
    return (value + 1) % _modulus(width)


def _representative_residues(modulus: int) -> tuple[int, ...]:
    return (0, 1, 2, modulus - 3, modulus - 2, modulus - 1)


def _width_pairs() -> list[tuple[int, int]]:
    return [
        (narrow, wide)
        for narrow in range(MINIMUM_WIDTH, CANONICAL_WIDTH)
        for wide in range(narrow + 1, CANONICAL_WIDTH + 1)
    ]


def _check_projection_point(
    widths: tuple[int, int],
    point: tuple[int, int],
) -> None:
    narrow, wide = widths
    quotient, residue = point
    narrow_modulus = _modulus(narrow)
    value = quotient * narrow_modulus + residue
    projected_successor = _project(_successor(value, wide), narrow)
    assert projected_successor == _successor(residue, narrow)
    projected_rotate = _project(_rotate(value, wide), narrow)
    expected_rotate = (
        residue // _RADIX
        + quotient % _RADIX * (narrow_modulus // _RADIX)
    )
    assert projected_rotate == expected_rotate
    assert (projected_rotate == _rotate(residue, narrow)) == (
        quotient % _RADIX == residue % _RADIX
    )


def _check_width_pair(widths: tuple[int, int]) -> None:
    narrow, wide = widths
    narrow_modulus = _modulus(narrow)
    wide_modulus = _modulus(wide)
    ratio = wide_modulus // narrow_modulus
    assert ratio == _power(wide - narrow)
    residues = _representative_residues(narrow_modulus)
    for point in product(range(ratio), residues):
        _check_projection_point(widths, point)
    for quotient in range(ratio):
        high_part = quotient * narrow_modulus
        assert (high_part % _BYTE_MODULUS == 0) == (quotient == 0)
    wide_eof = wide_modulus - 1
    narrow_eof = narrow_modulus - 1
    assert _project(wide_eof, narrow) == narrow_eof
    assert wide_eof % _BYTE_MODULUS != narrow_eof % _BYTE_MODULUS


def test_checked_width_projection_laws_and_counterexamples() -> None:
    """Audit exact radix projection laws for every checked narrowing pair."""
    for widths in _width_pairs():
        _check_width_pair(widths)


def test_output_compatible_word_count_for_checked_width_pairs() -> None:
    """Only words with zero discarded quotient preserve byte output."""
    for narrow, wide in _width_pairs():
        narrow_modulus = _modulus(narrow)
        ratio = _modulus(wide) // narrow_modulus
        compatible_quotients = sum(
            quotient * narrow_modulus % _BYTE_MODULUS == 0
            for quotient in range(ratio)
        )
        assert compatible_quotients == 1
        assert compatible_quotients * narrow_modulus == _power(narrow)


def test_rotate_projection_compatibility_is_not_monotone_in_width() -> None:
    """Each candidate width compares a distinct high trit with trit zero."""
    wide = CANONICAL_WIDTH
    value = 1 + _power(10) + _power(12)
    observed: dict[int, bool] = {}
    for narrow in range(MINIMUM_WIDTH, CANONICAL_WIDTH):
        residue = _project(value, narrow)
        observed[narrow] = (
            _project(_rotate(value, wide), narrow) == _rotate(residue, narrow)
        )
    assert observed == {10: True, 11: False, 12: True, 13: False}


_CANDIDATE_WIDTHS = tuple(range(MINIMUM_WIDTH, CANONICAL_WIDTH))
_RELEVANT_TRITS = (0, *_CANDIDATE_WIDTHS)
_FREE_TRITS = CANONICAL_WIDTH - len(_RELEVANT_TRITS)


def _candidate_subsets() -> list[tuple[int, ...]]:
    return [
        subset
        for size in range(len(_CANDIDATE_WIDTHS) + 1)
        for subset in combinations(_CANDIDATE_WIDTHS, size)
    ]


def _compatible_relevant_assignments(subset: tuple[int, ...]) -> int:
    positions = {
        position: index for index, position in enumerate(_RELEVANT_TRITS)
    }
    return sum(
        all(digits[positions[width]] == digits[0] for width in subset)
        for digits in product(range(_RADIX), repeat=len(_RELEVANT_TRITS))
    )


def test_rotate_compatible_word_count_for_checked_width_sets() -> None:
    """Each required candidate width removes exactly two thirds of words."""
    free_factor = _power(_FREE_TRITS)
    for subset in _candidate_subsets():
        compatible = _compatible_relevant_assignments(subset) * free_factor
        assert compatible == _power(CANONICAL_WIDTH - len(subset))
    all_widths = _compatible_relevant_assignments(_CANDIDATE_WIDTHS)
    assert all_widths * free_factor == _power(10)


def _equivalent_fixture() -> tuple[
    FiniteSystem,
    FiniteSystem,
    frozenset[tuple[str, str]],
]:
    wide = FiniteSystem(
        initial={"empty": "w0", "byte": "w1"},
        observation={"w0": (0,), "w1": (1,), "w2": (2,)},
        successor={"w0": "w1", "w1": "w2", "w2": None},
    )
    narrow = FiniteSystem(
        initial={"empty": "n0", "byte": "n1"},
        observation={"n0": (0,), "n1": (1,), "n2": (2,)},
        successor={"n0": "n1", "n1": "n2", "n2": None},
    )
    relation = frozenset({("w0", "n0"), ("w1", "n1"), ("w2", "n2")})
    return wide, narrow, relation


def test_finite_bisimulation_certificate_accepts_closed_relation() -> None:
    """A complete observation-preserving transition relation is accepted."""
    wide, narrow, relation = _equivalent_fixture()
    assert certificate_valid(wide, narrow, relation)


def test_finite_bisimulation_certificate_rejects_missing_obligation() -> None:
    """Missing initial, observation, transition, or termination data fails."""
    wide, narrow, relation = _equivalent_fixture()
    assert not certificate_valid(wide, narrow, relation - {("w1", "n1")})

    wrong_observation = FiniteSystem(
        initial=narrow.initial,
        observation={**narrow.observation, "n1": (9,)},
        successor=narrow.successor,
    )
    assert not certificate_valid(wide, wrong_observation, relation)

    wrong_transition = FiniteSystem(
        initial=narrow.initial,
        observation=narrow.observation,
        successor={**narrow.successor, "n1": "n1"},
    )
    assert not certificate_valid(wide, wrong_transition, relation)

    wrong_termination = FiniteSystem(
        initial=narrow.initial,
        observation=narrow.observation,
        successor={**narrow.successor, "n2": "n2"},
    )
    assert not certificate_valid(wide, wrong_termination, relation)


def test_minimum_certified_width_is_independent_and_fail_closed() -> None:
    """Select the minimum proved width without a monotonicity assumption."""
    rejected = dict.fromkeys(range(MINIMUM_WIDTH, CANONICAL_WIDTH), False)
    assert minimum_certified_width(rejected) == CANONICAL_WIDTH

    nonmonotone = {10: False, 11: True, 12: False, 13: True}
    assert minimum_certified_width(nonmonotone) == MINIMUM_WIDTH + 1

    several = {10: True, 11: False, 12: True, 13: True}
    assert minimum_certified_width(several) == MINIMUM_WIDTH

    missing = {10: True, 11: True, 12: True}
    assert minimum_certified_width(missing) == CANONICAL_WIDTH

    extra = {10: True, 11: True, 12: True, 13: True, 14: True}
    assert minimum_certified_width(extra) == CANONICAL_WIDTH

    invalid_type: dict[int, bool] = {10: True, 11: True, 12: True, 13: True}
    # Intentional invalid runtime fixture for fail-closed checking.
    invalid_type[13] = 1  # pyright: ignore[reportArgumentType]
    assert minimum_certified_width(invalid_type) == CANONICAL_WIDTH
