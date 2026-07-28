# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Contract tests for search backed by candidate evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accelerator.cpu import CpuCandidateEvaluationAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchRequest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.evaluated_search import SearchProposalSelector
    from accelerator.work_ports import CandidateEvaluationResult

ALGORITHM_ID = "evaluated-search-test-v1"
EVALUATOR_ID = "identity-evaluator-v1"
CPU_BACKEND = "cpu-reference"


def _identity(payload: bytes) -> bytes:
    return payload


def _request(*, budget: int) -> SearchRequest:
    return SearchRequest(
        algorithm_id=ALGORITHM_ID,
        evaluation_budget=budget,
        problem=b"test",
        seed=0,
    )


def _one_item(request: SearchRequest) -> CandidateEvaluationBatch:
    _ = request
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(CandidateWorkItem(logical_id="one", payload=b"payload"),),
    )


def _two_items(request: SearchRequest) -> CandidateEvaluationBatch:
    _ = request
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(
            CandidateWorkItem(logical_id="one", payload=b"one"),
            CandidateWorkItem(logical_id="two", payload=b"two"),
        ),
    )


def _select_first(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    _ = (request, evidence)
    item = batch.items[0]
    return (
        CandidateProposal(logical_id=item.logical_id, payload=item.payload),
    )


def _fabricate(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    _ = (request, batch, evidence)
    return (CandidateProposal(logical_id="one", payload=b"tampered"),)


def _expect_error(message: str, action: Callable[[], object]) -> None:
    try:
        _ = action()
    except InvalidAcceleratorWorkError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


def _adapter(
    batch_builder: Callable[[SearchRequest], CandidateEvaluationBatch],
    selector: SearchProposalSelector,
) -> EvaluatedSearchExecutionAdapter:
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    return EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        batch_builder=batch_builder,
        proposal_selector=selector,
    )


def test_valid_selector_returns_only_evaluated_candidate() -> None:
    """A valid evaluated candidate can become an untrusted proposal."""
    result = _adapter(_one_item, _select_first).search(_request(budget=1))

    assert result.capability.backend_id == CPU_BACKEND
    assert result.proposals == (
        CandidateProposal(logical_id="one", payload=b"payload"),
    )


def test_profiled_search_matches_ordinary_result_and_retains_phases() -> None:
    """Diagnostics preserve ordinary search semantics and phase identity."""
    adapter = _adapter(_one_item, _select_first)
    request = _request(budget=1)

    ordinary = adapter.search(request)
    profiled = adapter.profile_search(request)

    assert profiled.result == ordinary
    phases = profiled.phases
    assert phases.total_ns >= 0
    assert phases.request_validation_ns >= 0
    assert phases.batch_build_ns >= 0
    assert phases.batch_validation_ns >= 0
    assert phases.backend_evaluation_ns >= 0
    assert phases.proposal_selection_ns >= 0
    assert phases.result_validation_ns >= 0
    assert phases.total_ns >= sum((
        phases.request_validation_ns,
        phases.batch_build_ns,
        phases.batch_validation_ns,
        phases.backend_evaluation_ns,
        phases.proposal_selection_ns,
        phases.result_validation_ns,
    ))


def test_selector_cannot_fabricate_candidate_payload() -> None:
    """Selection cannot change payloads after candidate evaluation."""
    _expect_error(
        "proposal was not in evaluated candidate batch",
        lambda: _adapter(_one_item, _fabricate).search(_request(budget=1)),
    )


def test_budget_rejects_oversized_evaluation_batch_before_execution() -> None:
    """Search budget bounds candidate evaluation count, not only proposals."""
    _expect_error(
        "evaluated search batch exceeds declared evaluation budget",
        lambda: _adapter(_two_items, _select_first).search(_request(budget=1)),
    )
