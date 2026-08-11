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
#   - Replay and admission evidence for preregistered pilot candidate schedules.
# - Must-Not:
#   - Claim search quality, candidate semantics, or benchmark performance.
# - Allows:
#   - Inputs: the research schedule module and finite synthetic candidate sets.
#   - Outputs: exact order, replay, uniqueness, and fail-closed assertions.
#   - Side effects: dynamic import of one repository-owned pure Python module.
# - Split-When:
#   - Recorded pilot runs gain independent result/evidence tests.
# - Merge-When:
#   - Another test owns this exact schedule replay contract.
# - Summary:
#   - Candidate-order substrate evidence below the semantic verifier boundary.
# - Description:
#   - Locks enumeration and seeded sparse Fisher-Yates order independently.
# - Usage:
#   - Collected by the research algorithm test surface.
# - Defaults:
#   - Schedule ordering alone never counts as a superoptimization result.
#

"""Replay evidence for preregistered superoptimization candidate schedules."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_SCHEDULE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/schedule.py"
)
_CANDIDATE_COUNT = 10
_EXPECTED_ENUMERATION_ID = "deterministic-enumeration-v1"
_EXPECTED_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"
_KNOWN_SEEDED_ORDER = (5, 1, 9, 7, 0, 4)
_MAX_U64 = (1 << 64) - 1
_SPARSE_BUDGET = 4


class _ScheduleModule(Protocol):
    """Typed view of the pure research schedule module."""

    ENUMERATION_SCHEDULE_ID: str
    SEEDED_PROPOSAL_SCHEDULE_ID: str
    InvalidCandidateScheduleError: type[ValueError]

    def enumeration_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
    ) -> tuple[int, ...]: ...

    def seeded_proposal_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
        seed: int,
    ) -> tuple[int, ...]: ...


def _load_schedule() -> _ScheduleModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_pilot_schedule",
        _SCHEDULE,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization schedule module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_ScheduleModule", cast("object", module))


_SCHEDULE_MODULE = _load_schedule()


def test_schedule_algorithm_identities_are_stable() -> None:
    """Run manifests can bind exact versioned candidate-order algorithms."""
    assert (
        _SCHEDULE_MODULE.ENUMERATION_SCHEDULE_ID
        == _EXPECTED_ENUMERATION_ID
    )
    assert (
        _SCHEDULE_MODULE.SEEDED_PROPOSAL_SCHEDULE_ID
        == _EXPECTED_SEEDED_ID
    )


def test_enumeration_order_is_budget_bounded_natural_prefix() -> None:
    """The preregistered baseline is stable natural enumeration."""
    assert _SCHEDULE_MODULE.enumeration_order(10, 6) == tuple(range(6))
    assert _SCHEDULE_MODULE.enumeration_order(3, 6) == (0, 1, 2)
    assert _SCHEDULE_MODULE.enumeration_order(0, 6) == ()


def test_seeded_order_is_replayable_unique_budget_prefix() -> None:
    """Seeded proposals replay exactly without replacement."""
    first = _SCHEDULE_MODULE.seeded_proposal_order(_CANDIDATE_COUNT, 6, 0)
    second = _SCHEDULE_MODULE.seeded_proposal_order(_CANDIDATE_COUNT, 6, 0)
    assert first == second == _KNOWN_SEEDED_ORDER
    assert len(first) == len(set(first))
    assert all(0 <= value < _CANDIDATE_COUNT for value in first)
    assert _SCHEDULE_MODULE.seeded_proposal_order(3, 6, 0) == (1, 0, 2)


def test_seed_changes_order_without_changing_candidate_membership() -> None:
    """A different seed changes order but not a complete finite permutation."""
    baseline = _SCHEDULE_MODULE.seeded_proposal_order(16, 16, 0)
    changed = _SCHEDULE_MODULE.seeded_proposal_order(16, 16, 1)
    assert baseline != changed
    assert sorted(baseline) == sorted(changed) == list(range(16))


def test_seeded_order_is_sparse_over_maximum_logical_corpus() -> None:
    """A tiny budget never requires materializing the logical u64 corpus."""
    order = _SCHEDULE_MODULE.seeded_proposal_order(_MAX_U64, _SPARSE_BUDGET, 0)
    assert len(order) == _SPARSE_BUDGET
    assert len(set(order)) == len(order)
    assert all(0 <= value < _MAX_U64 for value in order)


@pytest.mark.parametrize(
    ("candidate_count", "budget", "seed"),
    [
        (-1, 1, 0),
        (1, -1, 0),
        (1, 1, -1),
    ],
)
def test_schedule_rejects_negative_dimensions(
    candidate_count: int,
    budget: int,
    seed: int,
) -> None:
    """Negative candidate, budget, or seed dimensions fail closed."""
    with pytest.raises(_SCHEDULE_MODULE.InvalidCandidateScheduleError):
        _ = _SCHEDULE_MODULE.seeded_proposal_order(
            candidate_count,
            budget,
            seed,
        )
