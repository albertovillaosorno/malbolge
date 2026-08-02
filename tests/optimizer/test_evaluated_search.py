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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Contract tests for search backed by candidate evaluation.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Contract tests for search backed by candidate evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import final

from accelerator.cpu import CpuCandidateEvaluationAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import EvaluatedSearchStrategy
from accelerator.evaluated_search import PreparedCandidateExecution
from accelerator.evaluated_search import PreparedCandidateMembershipIndex
from accelerator.evaluated_search import PreparedCandidateProjection
from accelerator.evaluated_search import PreparedProposalSelection
from accelerator.evaluated_search import prepare_candidate_projection
from accelerator.evaluated_search import prepared_membership_index_id
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import PreparedCandidateSubset
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import indexed_candidate_items_from_unique_u32
from accelerator.work_ports import prepare_candidate_subset

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.evaluated_search import SearchProposalSelector
    from accelerator.work_ports import CandidateEvaluationResult

ALGORITHM_ID = "evaluated-search-test-v1"
EVALUATOR_ID = "identity-evaluator-v1"
CPU_BACKEND = "cpu-reference"
TWO_ITEM_COUNT = 2
EXPECTED_MEMBERSHIP_INDEX_ID = (
    "u32-rotation-or-pair-or-reference-binary-search-v1"
)


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


def _count_invalid_identity_state(state: object) -> int:
    _ = state
    return -1


def _identity_state_batch(state: object) -> CandidateEvaluationBatch:
    if isinstance(state, CandidateEvaluationBatch):
        return state
    if isinstance(state, PreparedCandidateSubset):
        batch, _ = state.for_batch(state.full_batch)
        return batch
    message = "identity prepared state must carry a candidate batch"
    raise InvalidAcceleratorWorkError(message)


def _count_identity_state(state: object) -> int:
    return len(_identity_state_batch(state).items)


def _evaluate_identity_state(state: object) -> CandidateEvaluationResult:
    return CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity).evaluate(
        _identity_state_batch(state)
    )


def _prepare_first_selection(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> object:
    _ = request
    return batch


def _prepare_first_selection_other(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> object:
    _ = request
    return batch


def _select_prepared_first(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
    *,
    state: object,
) -> tuple[CandidateProposal, ...]:
    if state is not batch:
        message = "prepared selector state changed candidate batch"
        raise InvalidAcceleratorWorkError(message)
    return _select_first(request, batch, evidence)


def _count_prepared_selection(state: object) -> int:
    if not isinstance(state, CandidateEvaluationBatch):
        message = "prepared selector state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    return len(state.items)


def _project_first_candidate(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    if selection_state is not batch:
        message = "projection selector state changed candidate batch"
        raise InvalidAcceleratorWorkError(message)
    _ = request
    subset = prepare_candidate_subset(batch, (0,))
    projected, _ = subset.for_batch(batch)
    return prepare_candidate_projection(batch, subset, projected)


def _project_first_candidate_other(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    return _project_first_candidate(request, batch, selection_state)


def _project_fabricated_candidate(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    _ = (request, batch, selection_state)
    return object()


def _project_forged_candidate(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    _ = (request, selection_state)
    subset = prepare_candidate_subset(batch, (0,))
    projected, _ = subset.for_batch(batch)
    return PreparedCandidateProjection(
        subset=subset,
        state=projected,
        _proof=object(),
    )


def _project_another_batch(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    _ = (batch, selection_state)
    replacement = _two_items(request).validated()
    subset = prepare_candidate_subset(replacement, (0,))
    projected, _ = subset.for_batch(replacement)
    return prepare_candidate_projection(replacement, subset, projected)


def _project_oversized_batch(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    _ = (request, selection_state)
    return prepare_candidate_subset(batch, (0, 1))


def _projected_adapter(
    projection: Callable[
        [SearchRequest, CandidateEvaluationBatch, object], object
    ],
) -> EvaluatedSearchExecutionAdapter:
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    return EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_two_items,
            proposal_selector=_select_first,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=None,
                evaluator=_evaluate_identity_state,
                selection_aware_preparer=projection,
                state_count=_count_identity_state,
            ),
            prepared_selection=PreparedProposalSelection(
                state_preparer=_prepare_first_selection,
                selector=_select_prepared_first,
                state_count=_count_prepared_selection,
            ),
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


def test_prepared_proposal_selection_reuses_explicit_state() -> None:
    """Prepared selector state replaces ordinary selection only when reused."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    adapter = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_none,
            prepared_selection=PreparedProposalSelection(
                state_preparer=_prepare_first_selection,
                selector=_select_prepared_first,
                state_count=_count_prepared_selection,
            ),
        ),
    )
    request = _request(budget=1)
    prepared = adapter.prepare(request)

    assert adapter.search(request).proposals == ()
    assert adapter.prepared_selection_count(prepared) == 1
    assert adapter.search_prepared(prepared).proposals == (
        CandidateProposal(logical_id="one", payload=b"payload"),
    )


def test_prepared_selection_preparer_is_strategy_identity() -> None:
    """Distinct selector preparers cannot consume another strategy proof."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    first = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_none,
            prepared_selection=PreparedProposalSelection(
                state_preparer=_prepare_first_selection,
                selector=_select_prepared_first,
                state_count=_count_prepared_selection,
            ),
        ),
    )
    different = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_none,
            prepared_selection=PreparedProposalSelection(
                state_preparer=_prepare_first_selection_other,
                selector=_select_prepared_first,
                state_count=_count_prepared_selection,
            ),
        ),
    )
    prepared = first.prepare(_request(budget=1))

    _expect_error(
        "prepared search state belongs to a different strategy",
        lambda: different.search_prepared(prepared),
    )


def test_candidate_projection_rejects_forged_proof() -> None:
    """Raw projection construction cannot bind strategy state to a subset."""
    batch = _two_items(_request(budget=TWO_ITEM_COUNT)).validated()
    subset = prepare_candidate_subset(batch, (0,))
    forged = PreparedCandidateProjection(
        subset=subset,
        state=subset.batch,
        _proof=object(),
    )

    _expect_error(
        "prepared candidate projection is forged",
        lambda: forged.for_batch(batch),
    )


def test_selection_aware_projection_evaluates_exact_sub_batch() -> None:
    """Projected evidence preserves full-batch membership."""
    adapter = _projected_adapter(_project_first_candidate)
    request = _request(budget=TWO_ITEM_COUNT)

    prepared = adapter.prepare(request)
    result = adapter.search_prepared(prepared)

    assert adapter.prepared_candidate_state_count(prepared) == 1
    assert adapter.prepared_membership_count(prepared) == TWO_ITEM_COUNT
    assert result.proposals == (
        CandidateProposal(logical_id="one", payload=b"one"),
    )


def test_selection_aware_projection_rejects_fabricated_candidate() -> None:
    """Projection cannot invent identity or payload outside the full batch."""
    adapter = _projected_adapter(_project_fabricated_candidate)

    _expect_error(
        "selection-aware preparer returned wrong projection type",
        lambda: adapter.prepare(_request(budget=TWO_ITEM_COUNT)),
    )


def test_selection_aware_projection_rejects_forged_proof() -> None:
    """Raw projection construction cannot forge subset/state authority."""
    adapter = _projected_adapter(_project_forged_candidate)

    _expect_error(
        "prepared candidate projection is forged",
        lambda: adapter.prepare(_request(budget=TWO_ITEM_COUNT)),
    )


def test_selection_aware_projection_rejects_another_batch() -> None:
    """Equal content under another full batch cannot authorize evaluation."""
    adapter = _projected_adapter(_project_another_batch)

    _expect_error(
        "prepared candidate subset changed full candidate batch",
        lambda: adapter.prepare(_request(budget=TWO_ITEM_COUNT)),
    )


def test_selection_aware_projection_rejects_oversized_batch() -> None:
    """Projection cardinality cannot exceed the validated full batch."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    adapter = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=_one_item,
            proposal_selector=_select_first,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=None,
                evaluator=_evaluate_identity_state,
                selection_aware_preparer=_project_oversized_batch,
            ),
            prepared_selection=PreparedProposalSelection(
                state_preparer=_prepare_first_selection,
                selector=_select_prepared_first,
                state_count=_count_prepared_selection,
            ),
        ),
    )

    _expect_error(
        "candidate subset position outside candidate batch",
        lambda: adapter.prepare(_request(budget=1)),
    )


def test_projection_callbacks_are_strategy_identity() -> None:
    """Another projection callback cannot consume an existing prepared proof."""
    first = _projected_adapter(_project_first_candidate)
    different_preparer = _projected_adapter(_project_first_candidate_other)
    prepared = first.prepare(_request(budget=TWO_ITEM_COUNT))

    _expect_error(
        "prepared search state belongs to a different strategy",
        lambda: different_preparer.search_prepared(prepared),
    )


def test_prepared_execution_requires_exactly_one_preparer() -> None:
    """Generic preparation rejects missing or competing preparers."""
    evaluator = CpuCandidateEvaluationAdapter(EVALUATOR_ID, _identity)
    for batch_preparer, selection_preparer in (
        (None, None),
        (_prepare_identity_batch, _project_first_candidate),
    ):

        def construct_adapter(
            batch_preparer: Callable[[CandidateEvaluationBatch], object]
            | None = (batch_preparer),
            selection_preparer: Callable[
                [SearchRequest, CandidateEvaluationBatch, object],
                object,
            ]
            | None = selection_preparer,
        ) -> object:
            return EvaluatedSearchExecutionAdapter(
                ALGORITHM_ID,
                evaluator,
                EvaluatedSearchStrategy(
                    batch_builder=_two_items,
                    proposal_selector=_select_first,
                    prepared_execution=PreparedCandidateExecution(
                        batch_preparer=batch_preparer,
                        evaluator=_evaluate_identity_state,
                        selection_aware_preparer=selection_preparer,
                    ),
                ),
            )

        _expect_error(
            "prepared candidate execution requires exactly one preparer",
            construct_adapter,
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
                state_count=_count_identity_state,
            ),
        ),
    )
    request = _request(budget=1)

    prepared = adapter.prepare(request)
    result = adapter.search_prepared(prepared)

    assert adapter.prepared_candidate_state_count(prepared) == 1
    assert result == adapter.search(request)


def test_prepared_candidate_state_rejects_invalid_count() -> None:
    """Prepared candidate proof count must be a nonnegative integer."""
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
                state_count=_count_invalid_identity_state,
            ),
        ),
    )
    prepared = adapter.prepare(_request(budget=1))

    _expect_error(
        "prepared candidate state count must be nonnegative integer",
        lambda: adapter.prepared_candidate_state_count(prepared),
    )


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
                state_count=_count_identity_state,
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


def test_ordinary_indexed_membership_rejects_fabricated_payload() -> None:
    """One-shot indexed validation avoids item-table materialization."""
    items = indexed_candidate_items_from_unique_u32(
        logical_id_prefix="corpus-",
        logical_indices=(7, 9, 1, 3),
        payload_width=1,
        payloads=b"ABCD",
    )

    def batch_builder(request: SearchRequest) -> CandidateEvaluationBatch:
        del request
        return CandidateEvaluationBatch(
            evaluator_id=EVALUATOR_ID,
            items=items,
        )

    def fabricate(
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
        evidence: CandidateEvaluationResult,
    ) -> tuple[CandidateProposal, ...]:
        del request, batch, evidence
        return (CandidateProposal(logical_id="corpus-7", payload=b"X"),)

    _expect_error(
        "proposal was not in evaluated candidate batch",
        lambda: _adapter(batch_builder, fabricate).search(_request(budget=4)),
    )


def test_selector_cannot_fabricate_candidate_payload() -> None:
    """Selection cannot change payloads after candidate evaluation."""
    _expect_error(
        "proposal was not in evaluated candidate batch",
        lambda: _adapter(_one_item, _fabricate).search(_request(budget=1)),
    )


def test_prepared_membership_index_has_stable_identity() -> None:
    """Benchmark provenance names the exact membership algorithm."""
    assert prepared_membership_index_id() == EXPECTED_MEMBERSHIP_INDEX_ID


def test_prepared_membership_index_matches_exact_identity_and_payload() -> None:
    """Sorted membership references preserve exact ID and payload semantics."""
    batch = _two_items(_request(budget=2)).validated()
    index = PreparedCandidateMembershipIndex.prepare(batch)

    assert index.count_for(batch) == TWO_ITEM_COUNT
    assert index.contains(
        batch,
        CandidateProposal(logical_id="one", payload=b"one"),
    )
    assert not index.contains(
        batch,
        CandidateProposal(logical_id="one", payload=b"tampered"),
    )
    assert not index.contains(
        batch,
        CandidateProposal(logical_id="missing", payload=b"one"),
    )


def test_rotated_indexed_membership_reuses_candidate_index_bytes() -> None:
    """One rotation pivot replaces a duplicated sorted membership index."""
    items = indexed_candidate_items_from_unique_u32(
        logical_id_prefix="corpus-",
        logical_indices=(7, 9, 1, 3),
        payload_width=1,
        payloads=b"ABCD",
    )
    batch = CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=items,
    ).validated()

    index = PreparedCandidateMembershipIndex.prepare(batch)

    assert items.logical_rotation_pivot == TWO_ITEM_COUNT
    assert not index.indexed_pairs_u32le
    assert index.count_for(batch) == len(items)
    assert index.contains(
        batch,
        CandidateProposal(logical_id="corpus-7", payload=b"A"),
    )
    assert index.contains(
        batch,
        CandidateProposal(logical_id="corpus-1", payload=b"C"),
    )
    assert not index.contains(
        batch,
        CandidateProposal(logical_id="corpus-1", payload=b"X"),
    )
    assert not index.contains(
        batch,
        CandidateProposal(logical_id="corpus-2", payload=b"C"),
    )


def test_unordered_indexed_membership_uses_packed_pair_fallback() -> None:
    """Generic indexed batches retain exact lookup without rotation proof."""
    items = IndexedCandidateWorkItems(
        logical_id_prefix="candidate-",
        logical_indices_u32le=(7).to_bytes(4, "little")
        + (2).to_bytes(4, "little")
        + (9).to_bytes(4, "little"),
        payload_width=1,
        payloads=b"ABC",
    )
    batch = CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=items,
    ).validated()

    index = PreparedCandidateMembershipIndex.prepare(batch)

    assert len(index.indexed_pairs_u32le) == len(items) * 8
    assert index.contains(
        batch,
        CandidateProposal(logical_id="candidate-2", payload=b"B"),
    )
    assert not index.contains(
        batch,
        CandidateProposal(logical_id="candidate-2", payload=b"A"),
    )


def test_prepared_membership_index_rejects_forged_proof() -> None:
    """Raw construction cannot forge prepared membership authority."""
    batch = _one_item(_request(budget=1)).validated()
    forged = PreparedCandidateMembershipIndex(
        batch=batch,
        items_by_identity=tuple(batch.items),
        indexed_pairs_u32le=b"",
        _proof=object(),
    )

    _expect_error(
        "prepared candidate membership index is forged",
        lambda: forged.count_for(batch),
    )


def test_prepared_membership_index_rejects_another_batch() -> None:
    """Equal content under another batch identity cannot reuse the proof."""
    batch = _one_item(_request(budget=1)).validated()
    replacement = _one_item(_request(budget=1)).validated()
    index = PreparedCandidateMembershipIndex.prepare(batch)

    _expect_error(
        "prepared candidate membership index changed candidate batch",
        lambda: index.contains(
            replacement,
            CandidateProposal(logical_id="one", payload=b"payload"),
        ),
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
