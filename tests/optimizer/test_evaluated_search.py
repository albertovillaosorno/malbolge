# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Contract tests for search backed by candidate evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import final

from accelerator.cpu import CpuCandidateEvaluationAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import EvaluatedSearchStrategy
from accelerator.evaluated_search import PreparedCandidateExecution
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


@final
class _CountingBatchBuilder:
    calls: int

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: SearchRequest) -> CandidateEvaluationBatch:
        self.calls += 1
        return _one_item(request)


def _two_items(request: SearchRequest) -> CandidateEvaluationBatch:
    _ = request
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(
            CandidateWorkItem(logical_id="one", payload=b"one"),
            CandidateWorkItem(logical_id="two", payload=b"two"),
        ),
    )


def _prepare_identity_batch(batch: CandidateEvaluationBatch) -> object:
    return batch


def _prepare_identity_batch_other(batch: CandidateEvaluationBatch) -> object:
    return batch


def _evaluate_identity_state(state: object) -> CandidateEvaluationResult:
    if not isinstance(state, CandidateEvaluationBatch):
        message = "identity prepared state must be a candidate batch"
        raise InvalidAcceleratorWorkError(message)
    return CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity).evaluate(
        state
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


def _select_none(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    _ = (request, batch, evidence)
    return ()


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
        EvaluatedSearchStrategy(
            batch_builder=batch_builder,
            proposal_selector=selector,
        ),
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


def test_prepared_state_builds_once_and_reuses_exact_result() -> None:
    """Prepared immutable state removes repeated strategy batch construction."""
    builder = _CountingBatchBuilder()
    adapter = _adapter(builder, _select_first)
    request = _request(budget=1)

    prepared = adapter.prepare(request)
    assert adapter.prepared_membership_count(prepared) == 1
    first = adapter.search_prepared(prepared)
    second = adapter.search_prepared(prepared)

    assert builder.calls == 1
    assert first == second
    calls_before_ordinary = builder.calls
    assert first == adapter.search(request)
    assert builder.calls == calls_before_ordinary + 1


def test_prepared_profile_matches_prepared_execution() -> None:
    """Prepared diagnostics preserve the amortized execution result."""
    adapter = _adapter(_one_item, _select_first)
    prepared = adapter.prepare(_request(budget=1))

    ordinary = adapter.search_prepared(prepared)
    profiled = adapter.profile_prepared_search(prepared)

    assert profiled.result == ordinary
    phases = profiled.phases
    assert phases.prepared_validation_ns >= 0
    assert phases.backend_evaluation_ns >= 0
    assert phases.proposal_selection_ns >= 0
    assert phases.result_validation_ns >= 0
    assert phases.total_ns >= sum((
        phases.prepared_validation_ns,
        phases.backend_evaluation_ns,
        phases.proposal_selection_ns,
        phases.result_validation_ns,
    ))


def test_prepared_state_rejects_different_strategy_functions() -> None:
    """Algorithm identity alone cannot authorize another strategy binding."""
    prepared = _adapter(_one_item, _select_first).prepare(_request(budget=1))
    different = _adapter(_one_item, _select_none)

    _expect_error(
        "prepared search state belongs to a different strategy",
        lambda: different.search_prepared(prepared),
    )


def test_prepared_candidate_execution_reuses_explicit_state() -> None:
    """A strategy-owned prepared state drives repeated candidate execution."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    adapter = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_first,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=_prepare_identity_batch,
                evaluator=_evaluate_identity_state,
            ),
        ),
    )
    request = _request(budget=1)

    prepared = adapter.prepare(request)
    result = adapter.search_prepared(prepared)

    assert result == adapter.search(request)


def test_prepared_candidate_preparer_is_strategy_identity() -> None:
    """Distinct preparers cannot consume another strategy proof."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    first = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_first,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=_prepare_identity_batch,
                evaluator=_evaluate_identity_state,
            ),
        ),
    )
    different = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_first,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=_prepare_identity_batch_other,
                evaluator=_evaluate_identity_state,
            ),
        ),
    )
    prepared = first.prepare(_request(budget=1))

    _expect_error(
        "prepared search state belongs to a different strategy",
        lambda: different.search_prepared(prepared),
    )


def test_selector_cannot_fabricate_candidate_payload() -> None:
    """Selection cannot change payloads after candidate evaluation."""
    _expect_error(
        "proposal was not in evaluated candidate batch",
        lambda: _adapter(_one_item, _fabricate).search(_request(budget=1)),
    )


def test_prepared_index_rejects_fabricated_candidate_payload() -> None:
    """Prepared membership proof rejects selector payload substitution."""
    adapter = _adapter(_one_item, _fabricate)
    prepared = adapter.prepare(_request(budget=1))

    _expect_error(
        "proposal was not in evaluated candidate batch",
        lambda: adapter.search_prepared(prepared),
    )


def test_budget_rejects_oversized_evaluation_batch_before_execution() -> None:
    """Search budget bounds candidate evaluation count, not only proposals."""
    _expect_error(
        "evaluated search batch exceeds declared evaluation budget",
        lambda: _adapter(_two_items, _select_first).search(_request(budget=1)),
    )
