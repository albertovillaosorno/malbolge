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
#   - Regression evidence for prepared evaluated-search checkpoint resume.
# - Must-Not:
#   - Treat restored evidence or prepared proposals as acceptance authority.
# - Allows:
#   - Inputs: deterministic prepared searches and canonical evidence prefixes.
#   - Outputs: resumed/uninterrupted prepared-search differential assertions.
#   - Side effects: optional exact CUDA execution when available.
# - Split-When:
#   - A prepared strategy needs independently durable opaque preparation state.
# - Merge-When:
#   - Prepared and ordinary resume use one indistinguishable execution path.
# - Summary:
#   - Prepared-search resume execution regressions.
# - Description:
#   - Reconstructs preparation, evaluates only projected suffix state, then
#     reselects.
# - Usage:
#   - Runs with the optimizer Python validation suite.
# - Defaults:
#   - Checkpoint identity and prepared projection mismatches fail closed.
#

"""Regression tests for prepared evaluated-search checkpoint resume."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.resumable_search import RESUMABLE_PREPARED_EVALUATED_SEARCH_ID
from accelerator.resumable_search import resumable_prepared_evaluated_search_id
from accelerator.search_checkpoint import SearchCheckpointError
from accelerator.search_checkpoint import encode_search_checkpoint
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import SearchRequest
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import cpu_crazy_target_prepared_resume_execution
from optimizer.crazy_target import cpu_crazy_target_search_adapter
from optimizer.crazy_target import crazy_target_prepared_resume_execution
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import cpu_rotate_target_prepared_resume_execution
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_prepared_resume_execution
import pytest

if TYPE_CHECKING:
    from accelerator.resumable_search import (
        ResumablePreparedEvaluatedSearchExecution,
    )

CRAZY_ALL_ONES = 29_524
PREPARED_CRAZY_COUNT = 4
CUDA_BACKEND = "cuda"
ROTATE_ONE = 19_683


def _prefix_checkpoint_with_evaluator(
    execution: ResumablePreparedEvaluatedSearchExecution,
    request: SearchRequest,
    evaluator: PrimitiveCandidateEvaluationAdapter,
    *,
    completed: int,
) -> tuple[bytes, CandidateEvaluationBatch]:
    batch = execution.checkpoint_batch(request).validated()
    prefix_batch = CandidateEvaluationBatch(
        evaluator_id=batch.evaluator_id,
        items=tuple(batch.items[index] for index in range(completed)),
    ).validated()
    result = evaluator.evaluate(prefix_batch)
    evidence = result.materialized_items_against(
        prefix_batch,
        evaluator.capability(),
    )
    return encode_search_checkpoint(request, batch, evidence), batch


def _prefix_checkpoint(
    execution: ResumablePreparedEvaluatedSearchExecution,
    request: SearchRequest,
    kind: PrimitiveKind,
    *,
    completed: int,
) -> tuple[bytes, CandidateEvaluationBatch]:
    evaluator = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        kind,
    )
    return _prefix_checkpoint_with_evaluator(
        execution,
        request,
        evaluator,
        completed=completed,
    )


def _crazy_request() -> SearchRequest:
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    return SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=6,
        problem=problem.encode(),
        seed=17,
    )


def _rotate_request() -> SearchRequest:
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    return SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=5,
        problem=problem.encode(),
        seed=23,
    )


def test_prepared_resume_identity_is_stable() -> None:
    """Prepared checkpoint execution has one stable provenance identity."""
    assert resumable_prepared_evaluated_search_id() == (
        RESUMABLE_PREPARED_EVALUATED_SEARCH_ID
    )


def test_crazy_prepared_prefix_resume_matches_uninterrupted_search() -> None:
    """Resume interrupted multiposition state without proposal drift."""
    request = _crazy_request()
    execution = cpu_crazy_target_prepared_resume_execution()
    checkpoint, batch = _prefix_checkpoint(
        execution,
        request,
        PrimitiveKind.CRAZY,
        completed=1,
    )
    reference = cpu_crazy_target_search_adapter()
    prepared = reference.prepare(request)

    observed = execution.resume(request, checkpoint)
    expected = reference.search_prepared(prepared)

    assert len(batch.items) == PREPARED_CRAZY_COUNT
    assert observed == expected


def test_completed_prepared_checkpoint_needs_no_suffix_evaluation() -> None:
    """Reselect a complete prepared prefix without more candidate work."""
    request = _crazy_request()
    execution = cpu_crazy_target_prepared_resume_execution()
    batch = execution.checkpoint_batch(request)
    checkpoint, _ = _prefix_checkpoint(
        execution,
        request,
        PrimitiveKind.CRAZY,
        completed=len(batch.items),
    )
    reference = cpu_crazy_target_search_adapter()

    observed = execution.resume(request, checkpoint)
    expected = reference.search_prepared(reference.prepare(request))

    assert observed == expected


def test_rotate_empty_prepared_prefix_resumes_projected_search() -> None:
    """Reconstruct and execute an empty rotate prepared projection."""
    request = _rotate_request()
    execution = cpu_rotate_target_prepared_resume_execution()
    checkpoint, batch = _prefix_checkpoint(
        execution,
        request,
        PrimitiveKind.ROTATE,
        completed=0,
    )
    reference = cpu_rotate_target_search_adapter()

    observed = execution.resume(request, checkpoint)
    expected = reference.search_prepared(reference.prepare(request))

    assert len(batch.items) == 1
    assert observed == expected


def test_prepared_resume_rejects_ordinary_full_batch_checkpoint() -> None:
    """Bind prepared resume to the projected batch, not the full corpus."""
    request = _crazy_request()
    full_batch = build_crazy_target_batch(request).validated()
    checkpoint = encode_search_checkpoint(request, full_batch, ())

    with pytest.raises(SearchCheckpointError, match="batch_fingerprint"):
        _ = cpu_crazy_target_prepared_resume_execution().resume(
            request,
            checkpoint,
        )


def test_cpu_prepared_checkpoint_resumes_on_live_cuda() -> None:
    """CPU prepared prefix can resume through CUDA with matching proposals."""
    request = _crazy_request()
    cpu_execution = cpu_crazy_target_prepared_resume_execution()
    checkpoint, _ = _prefix_checkpoint(
        cpu_execution,
        request,
        PrimitiveKind.CRAZY,
        completed=1,
    )
    reference = cpu_crazy_target_search_adapter()
    expected = reference.search_prepared(reference.prepare(request))
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        observed = crazy_target_prepared_resume_execution(cuda).resume(
            request,
            checkpoint,
        )

    assert observed.proposals == expected.proposals
    assert observed.seed == expected.seed
    assert observed.capability.backend_id == CUDA_BACKEND


def test_cuda_prepared_checkpoint_resumes_on_cpu_without_drift() -> None:
    """CUDA prepared prefix is byte-identical and resumes through CPU."""
    request = _crazy_request()
    cpu_execution = cpu_crazy_target_prepared_resume_execution()
    cpu_checkpoint = _prefix_checkpoint(
        cpu_execution,
        request,
        PrimitiveKind.CRAZY,
        completed=1,
    )[0]
    reference = cpu_crazy_target_search_adapter()
    expected = reference.search_prepared(reference.prepare(request))
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        evaluator = PrimitiveCandidateEvaluationAdapter(
            cuda,
            PrimitiveKind.CRAZY,
        )
        cuda_checkpoint, _ = _prefix_checkpoint_with_evaluator(
            crazy_target_prepared_resume_execution(cuda),
            request,
            evaluator,
            completed=1,
        )
    observed = cpu_execution.resume(request, cuda_checkpoint)

    assert cuda_checkpoint == cpu_checkpoint
    assert observed == expected
    assert observed.capability == expected.capability


def test_rotate_cpu_prepared_checkpoint_resumes_on_live_cuda() -> None:
    """Completed CPU rotate checkpoint remains valid on the CUDA consumer."""
    request = _rotate_request()
    cpu_execution = cpu_rotate_target_prepared_resume_execution()
    checkpoint, batch = _prefix_checkpoint(
        cpu_execution,
        request,
        PrimitiveKind.ROTATE,
        completed=1,
    )
    reference = cpu_rotate_target_search_adapter()
    expected = reference.search_prepared(reference.prepare(request))
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        observed = rotate_target_prepared_resume_execution(cuda).resume(
            request,
            checkpoint,
        )

    assert len(batch.items) == 1
    assert observed.proposals == expected.proposals
    assert observed.seed == expected.seed
    assert observed.capability.backend_id == CUDA_BACKEND


def test_cuda_rotate_prepared_checkpoint_resumes_on_cpu_without_drift() -> None:
    """Completed CUDA rotate state encodes identically and resumes on CPU."""
    request = _rotate_request()
    cpu_execution = cpu_rotate_target_prepared_resume_execution()
    cpu_checkpoint, _ = _prefix_checkpoint(
        cpu_execution,
        request,
        PrimitiveKind.ROTATE,
        completed=1,
    )
    reference = cpu_rotate_target_search_adapter()
    expected = reference.search_prepared(reference.prepare(request))
    try:
        cuda = CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")
    with cuda:
        evaluator = PrimitiveCandidateEvaluationAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        cuda_checkpoint, _ = _prefix_checkpoint_with_evaluator(
            rotate_target_prepared_resume_execution(cuda),
            request,
            evaluator,
            completed=1,
        )
    observed = cpu_execution.resume(request, cuda_checkpoint)

    assert cuda_checkpoint == cpu_checkpoint
    assert observed == expected
    assert observed.capability == expected.capability
