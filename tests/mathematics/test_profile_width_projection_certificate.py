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

from dataclasses import dataclass
from itertools import product

_MINIMUM_WIDTH = 10
_MAXIMUM_WIDTH = 14
_RADIX = 3
_BYTE_MODULUS = 256
_CANONICAL_WIDTH = 14


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
        for narrow in range(_MINIMUM_WIDTH, _MAXIMUM_WIDTH)
        for wide in range(narrow + 1, _MAXIMUM_WIDTH + 1)
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


@dataclass(frozen=True)
class _FiniteSystem:
    initial: dict[str, str]
    observation: dict[str, tuple[int, ...]]
    successor: dict[str, str | None]


type _Relation = set[tuple[str, str]]


def _initial_coverage(
    wide: _FiniteSystem,
    narrow: _FiniteSystem,
    relation: _Relation,
) -> bool:
    if set(wide.initial) != set(narrow.initial):
        return False
    return all(
        (wide_state, narrow.initial[input_id]) in relation
        for input_id, wide_state in wide.initial.items()
    )


def _state_present(system: _FiniteSystem, state: str) -> bool:
    return state in system.observation and state in system.successor


def _successors_match(
    successors: tuple[str | None, str | None],
    relation: _Relation,
) -> bool:
    wide_next, narrow_next = successors
    if wide_next is None or narrow_next is None:
        return wide_next is None and narrow_next is None
    return (wide_next, narrow_next) in relation


def _pair_obligation(
    systems: tuple[_FiniteSystem, _FiniteSystem],
    relation: _Relation,
    pair: tuple[str, str],
) -> bool:
    wide, narrow = systems
    wide_state, narrow_state = pair
    if not (
        _state_present(wide, wide_state)
        and _state_present(narrow, narrow_state)
    ):
        return False
    observations_equal = (
        wide.observation[wide_state] == narrow.observation[narrow_state]
    )
    successors = (
        wide.successor[wide_state],
        narrow.successor[narrow_state],
    )
    return observations_equal and _successors_match(successors, relation)


def _certificate_valid(
    wide: _FiniteSystem,
    narrow: _FiniteSystem,
    relation: _Relation,
) -> bool:
    return _initial_coverage(wide, narrow, relation) and all(
        _pair_obligation((wide, narrow), relation, pair) for pair in relation
    )


def _equivalent_fixture() -> tuple[_FiniteSystem, _FiniteSystem, _Relation]:
    wide = _FiniteSystem(
        initial={"empty": "w0", "byte": "w1"},
        observation={"w0": (0,), "w1": (1,), "w2": (2,)},
        successor={"w0": "w1", "w1": "w2", "w2": None},
    )
    narrow = _FiniteSystem(
        initial={"empty": "n0", "byte": "n1"},
        observation={"n0": (0,), "n1": (1,), "n2": (2,)},
        successor={"n0": "n1", "n1": "n2", "n2": None},
    )
    relation = {("w0", "n0"), ("w1", "n1"), ("w2", "n2")}
    return wide, narrow, relation


def test_finite_bisimulation_certificate_accepts_closed_relation() -> None:
    """A complete observation-preserving transition relation is accepted."""
    wide, narrow, relation = _equivalent_fixture()
    assert _certificate_valid(wide, narrow, relation)


def test_finite_bisimulation_certificate_rejects_missing_obligation() -> None:
    """Missing initial, observation, transition, or termination data fails."""
    wide, narrow, relation = _equivalent_fixture()
    assert not _certificate_valid(wide, narrow, relation - {("w1", "n1")})

    wrong_observation = _FiniteSystem(
        initial=narrow.initial,
        observation={**narrow.observation, "n1": (9,)},
        successor=narrow.successor,
    )
    assert not _certificate_valid(wide, wrong_observation, relation)

    wrong_transition = _FiniteSystem(
        initial=narrow.initial,
        observation=narrow.observation,
        successor={**narrow.successor, "n1": "n1"},
    )
    assert not _certificate_valid(wide, wrong_transition, relation)

    wrong_termination = _FiniteSystem(
        initial=narrow.initial,
        observation=narrow.observation,
        successor={**narrow.successor, "n2": "n2"},
    )
    assert not _certificate_valid(wide, wrong_termination, relation)


def _minimum_certified_width(results: dict[int, bool]) -> int:
    candidates = set(range(_MINIMUM_WIDTH, _CANONICAL_WIDTH))
    if set(results) != candidates:
        return _CANONICAL_WIDTH
    certified = {width for width, accepted in results.items() if accepted}
    return min(certified, default=_CANONICAL_WIDTH)


def test_minimum_certified_width_is_independent_and_fail_closed() -> None:
    """Select the minimum proved width without a monotonicity assumption."""
    rejected = dict.fromkeys(range(_MINIMUM_WIDTH, _CANONICAL_WIDTH), False)
    assert _minimum_certified_width(rejected) == _CANONICAL_WIDTH

    nonmonotone = {10: False, 11: True, 12: False, 13: True}
    assert _minimum_certified_width(nonmonotone) == _MINIMUM_WIDTH + 1

    several = {10: True, 11: False, 12: True, 13: True}
    assert _minimum_certified_width(several) == _MINIMUM_WIDTH

    missing = {10: True, 11: True, 12: True}
    assert _minimum_certified_width(missing) == _CANONICAL_WIDTH

    extra = {10: True, 11: True, 12: True, 13: True, 14: True}
    assert _minimum_certified_width(extra) == _CANONICAL_WIDTH
