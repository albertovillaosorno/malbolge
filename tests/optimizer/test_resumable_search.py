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
#   - Regression evidence for backend-neutral evaluated-search resume execution.
# - Must-Not:
#   - Treat accelerator evidence or selected proposals as acceptance authority.
# - Allows:
#   - Inputs: deterministic requests, candidate batches, and checkpoints.
#   - Outputs: resumed/uninterrupted differential and failure assertions.
#   - Side effects: in-memory evaluator call recording only.
# - Split-When:
#   - Split when prepared-search resume requires distinct fixtures.
# - Merge-When:
#   - Merge when another suite owns the same ordinary resume behavior.
# - Summary:
#   - Evaluated-search resume execution regressions.
# - Description:
#   - Proves suffix-only evaluation and exact proposal reconstruction.
# - Usage:
#   - Runs with the optimizer Python validation suite.
# - Defaults:
#   - Checkpoint, backend, and proposal mismatches fail closed.
#

"""Regression tests for backend-neutral evaluated-search resume execution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast
from typing import final

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import EvaluatedSearchStrategy
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.resumable_search import RESUMABLE_EVALUATED_SEARCH_ID
from accelerator.resumable_search import ResumableEvaluatedSearchExecution
from accelerator.resumable_search import resumable_evaluated_search_id
from accelerator.search_checkpoint import encode_search_checkpoint
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateEvidence
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import PackedCandidateEvidence
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import candidate_work_items_suffix
from accelerator.work_ports import indexed_candidate_items_from_unique_u32
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import cpu_crazy_target_resume_execution
from optimizer.crazy_target import cpu_crazy_target_search_adapter
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import build_rotate_target_batch
from optimizer.rotate_target import cpu_rotate_target_resume_execution
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_resume_execution
import pytest

if TYPE_CHECKING:
    from accelerator.evaluated_search import SearchBatchBuilder
    from accelerator.evaluated_search import SearchProposalSelector
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import SearchResult

ALGORITHM_ID = "resumable-search-test-v1"
CRAZY_ALL_ONES = 29_524
CUDA_BACKEND = "cuda"
EVALUATOR_ID = "resumable-evaluator-v1"
RESUME_CAPABILITY = AcceleratorCapability(
    backend_id="resume-backend",
    device_arch="portable",
    device_name="resume-device",
)
FOREIGN_CAPABILITY = AcceleratorCapability(
    backend_id="foreign-backend",
    device_arch="portable",
    device_name="foreign-device",
)


def _request() -> SearchRequest:
    return SearchRequest(
        algorithm_id=ALGORITHM_ID,
        evaluation_budget=3,
        problem=b"resume-problem",
        seed=23,
    )


def _tuple_batch(request: SearchRequest) -> CandidateEvaluationBatch:
    _ = request
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(
            CandidateWorkItem(logical_id="candidate-0", payload=b"a"),
            CandidateWorkItem(logical_id="candidate-1", payload=b"b"),
            CandidateWorkItem(logical_id="candidate-2", payload=b"c"),
        ),
    )


def _indexed_batch(request: SearchRequest) -> CandidateEvaluationBatch:
    _ = request
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=indexed_candidate_items_from_unique_u32(
            logical_id_prefix="candidate-",
            logical_indices=(2, 0, 1),
            payload_width=1,
            payloads=b"abc",
        ),
    )


def _evidence_for(
    batch: CandidateEvaluationBatch,
    count: int,
) -> tuple[CandidateEvidence, ...]:
    return tuple(
        CandidateEvidence(
            logical_id=batch.items[index].logical_id,
            payload=b"e:" + batch.items[index].payload,
        )
        for index in range(count)
    )


def _select_last_exact_evidence(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    _ = request
    matched: list[CandidateProposal] = []
    for position, item in enumerate(batch.items):
        observed = evidence.items[position]
        if observed.payload == b"e:" + item.payload:
            matched.append(
                CandidateProposal(
                    logical_id=item.logical_id,
                    payload=item.payload,
                )
            )
    return () if not matched else (matched[-1],)


def _fabricated_selector(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    _ = (request, batch, evidence)
    return (CandidateProposal(logical_id="candidate-0", payload=b"tampered"),)


@final
class _RecordingEvaluator:
    calls: list[tuple[str, ...]]
    indexed_calls: list[bool]

    def __init__(
        self,
        capability: AcceleratorCapability = RESUME_CAPABILITY,
        *,
        packed: bool = False,
        result_capability: AcceleratorCapability | None = None,
    ) -> None:
        self._capability = capability
        self._packed = packed
        self._result_capability = result_capability or capability
        self.calls = []
        self.indexed_calls = []

    def capability(self) -> AcceleratorCapability:
        return self._capability

    def evaluate(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationResult:
        validated = batch.validated()
        self.calls.append(tuple(item.logical_id for item in validated.items))
        self.indexed_calls.append(
            isinstance(validated.items, IndexedCandidateWorkItems)
        )
        evidence = tuple(
            CandidateEvidence(
                logical_id=item.logical_id,
                payload=b"e:" + item.payload,
            )
            for item in validated.items
        )
        if self._packed:
            return CandidateEvaluationResult(
                capability=self._result_capability,
                evaluator_id=validated.evaluator_id,
                packed=PackedCandidateEvidence(
                    payload_width=3,
                    payloads=b"".join(item.payload for item in evidence),
                ),
            )
        return CandidateEvaluationResult(
            capability=self._result_capability,
            evaluator_id=validated.evaluator_id,
            items=evidence,
        )


def _strategy(
    batch_builder: SearchBatchBuilder = _tuple_batch,
    selector: SearchProposalSelector = _select_last_exact_evidence,
) -> EvaluatedSearchStrategy:
    return EvaluatedSearchStrategy(
        batch_builder=batch_builder,
        proposal_selector=selector,
    )


def test_resumable_search_identity_is_stable() -> None:
    """Progress provenance can bind the exact resume executor identity."""
    assert resumable_evaluated_search_id() == RESUMABLE_EVALUATED_SEARCH_ID


def test_partial_resume_matches_uninterrupted_suffix_only() -> None:
    """A durable prefix skips completed evaluations without changing result."""
    request = _request()
    batch = _tuple_batch(request).validated()
    checkpoint = encode_search_checkpoint(
        request,
        batch,
        _evidence_for(batch, 1),
    )
    resumed_evaluator = _RecordingEvaluator()
    ordinary_evaluator = _RecordingEvaluator()
    strategy = _strategy()

    resumed = ResumableEvaluatedSearchExecution(
        ALGORITHM_ID,
        resumed_evaluator,
        strategy,
    ).resume(request, checkpoint)
    ordinary = EvaluatedSearchExecutionAdapter(
        ALGORITHM_ID,
        ordinary_evaluator,
        strategy,
    ).search(request)

    assert resumed == ordinary
    assert resumed_evaluator.calls == [("candidate-1", "candidate-2")]
    assert ordinary_evaluator.calls == [
        ("candidate-0", "candidate-1", "candidate-2")
    ]


def test_partial_resume_materializes_packed_suffix_evidence() -> None:
    """Packed suffix evidence combines with the durable materialized prefix."""
    request = _request()
    batch = _tuple_batch(request).validated()
    checkpoint = encode_search_checkpoint(
        request,
        batch,
        _evidence_for(batch, 1),
    )
    evaluator = _RecordingEvaluator(packed=True)

    result = ResumableEvaluatedSearchExecution(
        ALGORITHM_ID,
        evaluator,
        _strategy(),
    ).resume(request, checkpoint)

    assert evaluator.calls == [("candidate-1", "candidate-2")]
    assert result.proposals == (
        CandidateProposal(logical_id="candidate-2", payload=b"c"),
    )


def test_completed_resume_performs_no_candidate_evaluation() -> None:
    """A fully completed checkpoint reselects without invoking the evaluator."""
    request = _request()
    batch = _tuple_batch(request).validated()
    checkpoint = encode_search_checkpoint(
        request,
        batch,
        _evidence_for(batch, len(batch.items)),
    )
    evaluator = _RecordingEvaluator()

    result = ResumableEvaluatedSearchExecution(
        ALGORITHM_ID,
        evaluator,
        _strategy(),
    ).resume(request, checkpoint)

    assert evaluator.calls == []
    assert result.proposals == (
        CandidateProposal(logical_id="candidate-2", payload=b"c"),
    )


def test_resume_preserves_indexed_suffix_storage() -> None:
    """Packed candidate storage stays packed when completed prefixes are cut."""
    request = _request()
    batch = _indexed_batch(request).validated()
    checkpoint = encode_search_checkpoint(
        request,
        batch,
        _evidence_for(batch, 1),
    )
    evaluator = _RecordingEvaluator()

    result = ResumableEvaluatedSearchExecution(
        ALGORITHM_ID,
        evaluator,
        _strategy(_indexed_batch),
    ).resume(request, checkpoint)

    assert evaluator.calls == [("candidate-0", "candidate-1")]
    assert evaluator.indexed_calls == [True]
    assert result.proposals == (
        CandidateProposal(logical_id="candidate-1", payload=b"c"),
    )


def test_candidate_suffix_rejects_invalid_start_and_keeps_indexed() -> None:
    """Suffix projection rejects aliases and keeps indexed representation."""
    batch = _indexed_batch(_request()).validated()

    empty = candidate_work_items_suffix(batch.items, len(batch.items))

    assert isinstance(empty, IndexedCandidateWorkItems)
    assert len(empty) == 0
    with pytest.raises(InvalidAcceleratorWorkError, match="suffix start"):
        _ = candidate_work_items_suffix(batch.items, -1)
    boolean_value: object = True
    boolean_start = cast("int", boolean_value)
    with pytest.raises(InvalidAcceleratorWorkError, match="suffix start"):
        _ = candidate_work_items_suffix(batch.items, boolean_start)


def _primitive_prefix_checkpoint(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evaluator: CandidateEvaluationAdapter,
) -> bytes:
    prefix_batch = CandidateEvaluationBatch(
        evaluator_id=batch.evaluator_id,
        items=(batch.items[0],),
    ).validated()
    prefix_result = evaluator.evaluate(prefix_batch)
    prefix = prefix_result.materialized_items_against(
        prefix_batch,
        evaluator.capability(),
    )
    return encode_search_checkpoint(request, batch, prefix)


def _cpu_rotate_checkpoint() -> tuple[SearchRequest, bytes, SearchResult]:
    problem = RotateTargetProblem(
        target=19_683,
        candidates=(0, 1, 2, 1, 4),
    )
    request = SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=5,
        problem=problem.encode(),
        seed=0,
    )
    batch = build_rotate_target_batch(request).validated()
    cpu_evaluator = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    checkpoint = _primitive_prefix_checkpoint(request, batch, cpu_evaluator)
    expected = cpu_rotate_target_search_adapter().search(request)
    return request, checkpoint, expected


def test_cpu_checkpoint_resumes_on_cuda_with_same_rotate_proposals() -> None:
    """CPU checkpoint evidence can resume on CUDA without semantic drift."""
    request, checkpoint, expected = _cpu_rotate_checkpoint()
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        observed = rotate_target_resume_execution(cuda).resume(
            request,
            checkpoint,
        )

    assert observed.proposals == expected.proposals
    assert observed.seed == expected.seed
    assert observed.capability.backend_id == CUDA_BACKEND


def test_cuda_checkpoint_bytes_resume_on_cpu_without_drift() -> None:
    """CUDA evidence encodes identically and resumes through the CPU route."""
    request, cpu_checkpoint, expected = _cpu_rotate_checkpoint()
    batch = build_rotate_target_batch(request).validated()
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        cuda_evaluator = PrimitiveCandidateEvaluationAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        cuda_checkpoint = _primitive_prefix_checkpoint(
            request,
            batch,
            cuda_evaluator,
        )
    observed = cpu_rotate_target_resume_execution().resume(
        request,
        cuda_checkpoint,
    )

    assert cuda_checkpoint == cpu_checkpoint
    assert observed == expected


def test_cpu_crazy_resume_factory_matches_uninterrupted_search() -> None:
    """Crazy-target resume factory shares ordinary search semantics."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    request = SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=6,
        problem=problem.encode(),
        seed=0,
    )
    batch = build_crazy_target_batch(request).validated()
    evaluator = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.CRAZY,
    )
    checkpoint = _primitive_prefix_checkpoint(request, batch, evaluator)

    observed = cpu_crazy_target_resume_execution().resume(request, checkpoint)
    expected = cpu_crazy_target_search_adapter().search(request)

    assert observed == expected


def test_resume_rejects_backend_result_capability_drift() -> None:
    """Suffix evidence must retain the selected resume backend capability."""
    request = _request()
    batch = _tuple_batch(request).validated()
    checkpoint = encode_search_checkpoint(
        request,
        batch,
        _evidence_for(batch, 1),
    )
    evaluator = _RecordingEvaluator(result_capability=FOREIGN_CAPABILITY)

    with pytest.raises(InvalidAcceleratorResultError, match="capability"):
        _ = ResumableEvaluatedSearchExecution(
            ALGORITHM_ID,
            evaluator,
            _strategy(),
        ).resume(request, checkpoint)


def test_resume_rejects_selector_fabrication() -> None:
    """Restored evidence cannot authorize a foreign proposal."""
    request = _request()
    batch = _tuple_batch(request).validated()
    checkpoint = encode_search_checkpoint(request, batch, ())

    with pytest.raises(InvalidAcceleratorWorkError, match="not in evaluated"):
        _ = ResumableEvaluatedSearchExecution(
            ALGORITHM_ID,
            _RecordingEvaluator(),
            _strategy(selector=_fabricated_selector),
        ).resume(request, checkpoint)
