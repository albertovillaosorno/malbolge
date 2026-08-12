# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Pure fail-closed history-residue canonicalization for research state.
# - Must-Not:
#   - Own Malbolge encryption semantics or infer applicability from mutable
#     state.
# - Allows:
#   - Inputs: explicit applicability, visit counts, and encryption successor.
#   - Outputs: exact canonical visit residues for admitted histories.
#   - Side effects: none.
# - Split-When:
#   - A benchmark runner or search-state graph gains independent lifecycle.
# - Merge-When:
#   - Another research substrate owns the exact same canonical history identity.
# - Summary:
#   - Exact history residues below independent semantic authority.
# - Description:
#   - Reduces rotate and encryption visits only under explicit preconditions.
# - Usage:
#   - Future challenges inject their trusted encryption successor.
# - Defaults:
#   - Invalid dimensions, applicability, or encryption orbits fail closed.
#

"""Pure exact history-residue canonicalization for research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

HISTORY_CANONICALIZATION_ID = "exact-history-residue-state-v1"
CLASSIC_ROTATE_PERIOD = 10
_GRAPHICAL_START = 33
_GRAPHICAL_END = 126
_GRAPHICAL_COUNT = _GRAPHICAL_END - _GRAPHICAL_START + 1


class EncryptionSuccessor(Protocol):
    """One caller-owned exact graphical encryption transition."""

    def __call__(self, cell: int) -> int | None:
        """Return the exact encrypted successor or ``None`` when invalid."""
        ...


class InvalidHistoryCanonicalizationError(ValueError):
    """History canonicalization input or applicability is invalid."""


@dataclass(frozen=True, slots=True)
class HistoryApplicability:
    """Explicit proof obligations required before reducing visit history."""

    same_address_identity: bool
    intervening_write: bool


def _require_exact_nonnegative(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        message = f"{label} must be a nonnegative exact integer"
        raise InvalidHistoryCanonicalizationError(message)


def _require_applicability(applicability: HistoryApplicability) -> None:
    if type(applicability) is not HistoryApplicability:
        message = "history applicability must use the exact immutable type"
        raise InvalidHistoryCanonicalizationError(message)
    if type(applicability.same_address_identity) is not bool or type(
        applicability.intervening_write
    ) is not bool:
        message = "history applicability flags must use the exact bool type"
        raise InvalidHistoryCanonicalizationError(message)
    if (
        not applicability.same_address_identity
        or applicability.intervening_write
    ):
        message = "history canonicalization applicability is not proved"
        raise InvalidHistoryCanonicalizationError(message)


def canonical_rotate_visits(
    visits: int,
    applicability: HistoryApplicability,
) -> int:
    """Return the exact classic rotate-history residue modulo ten.

    Returns:
        Canonical visit residue in ``0..9``.

    """
    _require_exact_nonnegative(visits, "rotate visits")
    _require_applicability(applicability)
    return visits % CLASSIC_ROTATE_PERIOD


def _encryption_orbit_period(
    start_cell: int,
    successor: EncryptionSuccessor,
) -> int:
    seen: set[int] = set()
    current = start_cell
    for period in range(1, _GRAPHICAL_COUNT + 1):
        if current in seen:
            message = "encryption successor merged before returning to start"
            raise InvalidHistoryCanonicalizationError(message)
        seen.add(current)
        following = successor(current)
        if type(following) is not int or not (
            _GRAPHICAL_START <= following <= _GRAPHICAL_END
        ):
            message = "encryption successor escaped the graphical domain"
            raise InvalidHistoryCanonicalizationError(message)
        if following == start_cell:
            return period
        current = following
    message = "encryption successor did not close within the graphical domain"
    raise InvalidHistoryCanonicalizationError(message)


def canonical_encryption_visits(
    start_cell: int,
    visits: int,
    *,
    applicability: HistoryApplicability,
    successor: EncryptionSuccessor,
) -> int:
    """Return exact committed-encryption residue for one closed orbit.

    Returns:
        Canonical visit residue modulo the caller-supplied orbit period.

    Raises:
        InvalidHistoryCanonicalizationError: If inputs, applicability, or the
            injected encryption orbit fail closed validation.

    """
    if type(start_cell) is not int or not (
        _GRAPHICAL_START <= start_cell <= _GRAPHICAL_END
    ):
        message = "encryption start cell must be an exact graphical integer"
        raise InvalidHistoryCanonicalizationError(message)
    _require_exact_nonnegative(visits, "encryption visits")
    _require_applicability(applicability)
    period = _encryption_orbit_period(start_cell, successor)
    return visits % period
