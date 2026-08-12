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
#   - Exhaustive evidence for pure history-residue canonicalization.
# - Must-Not:
#   - Promote research results or duplicate Malbolge encryption authority.
# - Allows:
#   - Inputs: research canonicalizer plus repository classic verifier successor.
#   - Outputs: exact residue, orbit-period, and fail-closed assertions.
#   - Side effects: dynamic import of repository-owned pure Python modules.
# - Split-When:
#   - A measured canonicalization challenge gains independent evidence.
# - Merge-When:
#   - Another test owns these exact history-residue invariants.
# - Summary:
#   - Canonicalization substrate evidence below semantic authority.
# - Description:
#   - Checks all historical encryption cells and classic rotate visit residues.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Applicability and malformed injected orbits fail closed.
#

"""Exhaustive evidence for exact history-residue canonicalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

_ROOT = Path(__file__).resolve().parents[5]
_HISTORY = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/history.py"
)
_CLASSIC = _ROOT / "verifier/emitted_malbolge_classic.py"
_GRAPHICAL_START = 33
_GRAPHICAL_END = 126
_EXPECTED_PERIODS = {2, 4, 5, 6, 9, 68}
_HISTORY_ID = "exact-history-residue-state-v1"
_ROTATE_PERIOD = 10


class _Applicability(Protocol):
    same_address_identity: bool
    intervening_write: bool


class _ApplicabilityFactory(Protocol):
    def __call__(
        self,
        *,
        same_address_identity: bool,
        intervening_write: bool,
    ) -> _Applicability: ...


class _HistoryModule(Protocol):
    HISTORY_CANONICALIZATION_ID: str
    CLASSIC_ROTATE_PERIOD: int
    InvalidHistoryCanonicalizationError: type[ValueError]
    HistoryApplicability: _ApplicabilityFactory

    def canonical_rotate_visits(
        self,
        visits: int,
        applicability: _Applicability,
    ) -> int: ...

    def canonical_encryption_visits(
        self,
        start_cell: int,
        visits: int,
        *,
        applicability: _Applicability,
        successor: Callable[[int], int | None],
    ) -> int: ...


class _ClassicModule(Protocol):
    def encrypt(self, value: int) -> int | None: ...


def _load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        message = f"research test module cannot be loaded: {path.name}"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_HISTORY_MODULE = cast(
    "_HistoryModule",
    _load_module(_HISTORY, "superoptimization_history_test"),
)
_CLASSIC_MODULE = cast(
    "_ClassicModule",
    _load_module(_CLASSIC, "superoptimization_classic_test"),
)
_ADMITTED = _HISTORY_MODULE.HistoryApplicability(
    same_address_identity=True,
    intervening_write=False,
)


def _independent_period(start: int) -> int:
    current = start
    for period in range(1, (_GRAPHICAL_END - _GRAPHICAL_START) + 2):
        following = _CLASSIC_MODULE.encrypt(current)
        if following is None:
            message = "classic verifier rejected a graphical orbit cell"
            raise AssertionError(message)
        if following == start:
            return period
        current = following
    message = "classic encryption orbit did not close"
    raise AssertionError(message)


def test_historical_encryption_visits_reduce_over_every_graphical_cell(
) -> None:
    """All 94 historical cells reduce by their independently walked orbit."""
    observed_periods: set[int] = set()
    for start in range(_GRAPHICAL_START, _GRAPHICAL_END + 1):
        period = _independent_period(start)
        observed_periods.add(period)
        for visits in (0, 1, period, period + 1, (2 * period) + 3):
            residue = _HISTORY_MODULE.canonical_encryption_visits(
                start,
                visits,
                applicability=_ADMITTED,
                successor=_CLASSIC_MODULE.encrypt,
            )
            assert residue == visits % period
    assert observed_periods == _EXPECTED_PERIODS


def test_rotate_visits_reduce_modulo_classic_trit_count() -> None:
    """Classic rotate history has the safe modulo-ten canonical bound."""
    assert _HISTORY_MODULE.HISTORY_CANONICALIZATION_ID == _HISTORY_ID
    assert _HISTORY_MODULE.CLASSIC_ROTATE_PERIOD == _ROTATE_PERIOD
    for visits in range((_ROTATE_PERIOD * 3) + 1):
        assert (
            _HISTORY_MODULE.canonical_rotate_visits(visits, _ADMITTED)
            == visits % _ROTATE_PERIOD
        )


@pytest.mark.parametrize(
    "applicability",
    [
        pytest.param((False, False), id="changed-address"),
        pytest.param((True, True), id="intervening-write"),
    ],
)
def test_history_reduction_rejects_unproved_applicability(
    applicability: tuple[bool, bool],
) -> None:
    """Either failed applicability proof blocks both history reductions."""
    proof = _HISTORY_MODULE.HistoryApplicability(
        same_address_identity=applicability[0],
        intervening_write=applicability[1],
    )
    with pytest.raises(_HISTORY_MODULE.InvalidHistoryCanonicalizationError):
        _ = _HISTORY_MODULE.canonical_rotate_visits(10, proof)
    with pytest.raises(_HISTORY_MODULE.InvalidHistoryCanonicalizationError):
        _ = _HISTORY_MODULE.canonical_encryption_visits(
            _GRAPHICAL_START,
            2,
            applicability=proof,
            successor=_CLASSIC_MODULE.encrypt,
        )


@pytest.mark.parametrize("visits", [-1, True])
def test_history_reduction_rejects_invalid_visit_counts(visits: int) -> None:
    """Negative and bool visit counts cannot enter canonical state."""
    with pytest.raises(_HISTORY_MODULE.InvalidHistoryCanonicalizationError):
        _ = _HISTORY_MODULE.canonical_rotate_visits(visits, _ADMITTED)


def test_encryption_reduction_rejects_invalid_orbit_evidence() -> None:
    """Injected successor must remain graphical and close back to the start."""
    def escaped(cell: int) -> int | None:
        assert cell >= _GRAPHICAL_START
        return None

    with pytest.raises(_HISTORY_MODULE.InvalidHistoryCanonicalizationError):
        _ = _HISTORY_MODULE.canonical_encryption_visits(
            _GRAPHICAL_START,
            1,
            applicability=_ADMITTED,
            successor=escaped,
        )
