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
#   - Pure and live evidence for multiposition crazy-target search tickets.
# - Must-Not:
#   - Claim speedup, independent streams, or candidate acceptance authority.
# - Allows:
#   - Inputs: deterministic crazy-target requests and candidate ticket backends.
#   - Outputs: projected-batch, lifetime, fallback, and proposal assertions.
#   - Side effects: scoped CPU counters and live CUDA allocations.
# - Split-When:
#   - Split when another multiposition strategy gains ticket evidence.
# - Merge-When:
#   - Merge when another test owns the same crazy-target submission contract.
# - Summary:
#   - Exact multiposition crazy-target submission regression tests.
# - Description:
#   - Proves full-batch selection over deferred 1,024-item evaluation.
# - Usage:
#   - Collected by the optimizer suite; live routes skip without CUDA.
# - Defaults:
#   - Every published proposal is compared with the CPU reference search.
#

"""Exact multiposition crazy-target search submission regressions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cpu.work_ports import CPU_WORK_CAPABILITY
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaPrimitiveCandidateSubmissionAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.search_submission import SearchSubmissionFallback
from accelerator.search_submission import SearchSubmissionState
from accelerator.search_submission import submit_search
from accelerator.submission import CandidateEvaluationTicket
from accelerator.submission import CandidateSubmissionAdapter
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import SearchRequest
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import cpu_crazy_target_search_adapter
from optimizer.crazy_target_submission import CrazyTargetSearchSubmissionAdapter
from optimizer.crazy_target_submission import crazy_target_submission_id
import pytest

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchResult

EXPECTED_SUBMISSION_ID = "classic-crazy-target-search-submission-v1"
ALL_ONES = MAX_WORD // 2
FULL_DOMAIN_COUNT = MAX_WORD + 1
MULTI_PREIMAGE_COUNT = 1 << 10
CUDA_BACKEND = "cuda"
CPU_BACKEND = "cpu-reference"
FIRST_PROJECTED_LOGICAL_ID = "corpus-0"
LAST_PROJECTED_LOGICAL_ID = f"corpus-{ALL_ONES}"
TEARDOWN_CORPUS_SIZE = 257


def _request(
    candidates: tuple[int, ...],
    *,
    accumulator: int = 0,
    target: int = ALL_ONES,
) -> SearchRequest:
    problem = CrazyTargetProblem(
        accumulator=accumulator,
        target=target,
        candidates=candidates,
    ).encode()
    return SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=len(candidates),
        problem=problem,
        seed=0,
    )


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


@dataclass(slots=True)
class _Ticket(CandidateEvaluationTicket):
    adapter: CandidateEvaluationAdapter
    batch: CandidateEvaluationBatch
    closes: int = 0
    malformed: bool = False
    waits: int = 0

    @override
    def close(self) -> None:
        self.closes += 1

    @override
    def wait(self) -> CandidateEvaluationResult:
        self.waits += 1
        result = self.adapter.evaluate(self.batch)
        if not self.malformed:
            return result
        return CandidateEvaluationResult(
            capability=result.capability,
            evaluator_id=result.evaluator_id,
        )


@final
class _RecordingCandidateAdapter(CandidateSubmissionAdapter):
    def __init__(
        self,
        inner: CandidateSubmissionAdapter | None = None,
        *,
        malformed: bool = False,
    ) -> None:
        self._inner = inner
        self._malformed = malformed
        self.local_tickets: list[_Ticket] = []
        self.submitted: list[CandidateEvaluationBatch] = []

    @override
    def capability(self) -> AcceleratorCapability:
        if self._inner is not None:
            return self._inner.capability()
        return CPU_WORK_CAPABILITY

    @override
    def submit(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationTicket:
        validated = batch.validated()
        self.submitted.append(validated)
        if self._inner is not None:
            ticket = self._inner.submit(validated)
        else:
            evaluator = PrimitiveCandidateEvaluationAdapter(
                CpuExactPrimitiveAdapter(),
                PrimitiveKind.CRAZY,
            )
            ticket = _Ticket(
                adapter=evaluator,
                batch=validated,
                malformed=self._malformed,
            )
            self.local_tickets.append(ticket)
        return ticket


@final
class _MalformedCandidateAdapter(CandidateSubmissionAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return CPU_WORK_CAPABILITY

    @override
    def submit(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationTicket:
        _ = batch.validated()
        return cast("CandidateEvaluationTicket", object())


def _assert_matches_reference(
    request: SearchRequest,
    observed: SearchResult,
) -> None:
    expected = cpu_crazy_target_search_adapter().search(request)
    assert observed == expected


def test_crazy_target_submission_identity_is_stable() -> None:
    """Evidence names the exact multiposition ticket composition."""
    assert crazy_target_submission_id() == EXPECTED_SUBMISSION_ID


def test_full_domain_ticket_submits_exact_1024_position_subset() -> None:
    """Full membership publishes through only exact deferred preimages."""
    request = _request(tuple(range(FULL_DOMAIN_COUNT)))
    candidate = _RecordingCandidateAdapter()
    reference = cpu_crazy_target_search_adapter()
    submission = submit_search(
        request,
        reference,
        CrazyTargetSearchSubmissionAdapter(candidate),
    )

    assert submission.status().state is SearchSubmissionState.PENDING
    assert len(candidate.submitted) == 1
    projected = candidate.submitted[0]
    assert len(projected.items) == MULTI_PREIMAGE_COUNT
    assert projected.items[0].logical_id == FIRST_PROJECTED_LOGICAL_ID
    assert projected.items[-1].logical_id == LAST_PROJECTED_LOGICAL_ID

    observed = submission.wait()

    _assert_matches_reference(request, observed)
    assert candidate.local_tickets[0].waits == 1
    assert candidate.local_tickets[0].closes == 1
    assert submission.status().fallback is None


def test_empty_projection_publishes_empty_result_without_candidates() -> None:
    """Impossible target submits an empty batch and remains exact."""
    request = _request(tuple(range(TEARDOWN_CORPUS_SIZE)), target=0)
    candidate = _RecordingCandidateAdapter()
    submission = submit_search(
        request,
        cpu_crazy_target_search_adapter(),
        CrazyTargetSearchSubmissionAdapter(candidate),
    )

    observed = submission.wait()

    _assert_matches_reference(request, observed)
    assert len(candidate.submitted[0].items) == 0
    assert observed.proposals == ()


def test_malformed_candidate_evidence_closes_then_falls_back() -> None:
    """Wrong projected evidence cannot publish and selects CPU search."""
    request = _request((0, 1, 2, 3, 4))
    candidate = _RecordingCandidateAdapter(malformed=True)
    submission = submit_search(
        request,
        cpu_crazy_target_search_adapter(),
        CrazyTargetSearchSubmissionAdapter(candidate),
    )

    observed = submission.wait()

    _assert_matches_reference(request, observed)
    assert candidate.local_tickets[0].closes == 1
    assert (
        submission.status().fallback is SearchSubmissionFallback.RESULT_INVALID
    )


def test_malformed_candidate_ticket_fails_before_search_fallback() -> None:
    """Unknown nested candidate lifetime propagates as protocol failure."""
    request = _request((0,))

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="candidate submission adapter returned invalid ticket",
    ):
        _ = submit_search(
            request,
            cpu_crazy_target_search_adapter(),
            CrazyTargetSearchSubmissionAdapter(_MalformedCandidateAdapter()),
        )


def test_live_cuda_ticket_publishes_exact_1024_position_result() -> None:
    """Live CUDA evaluates the exact multiposition subset and matches CPU."""
    request = _request(tuple(range(FULL_DOMAIN_COUNT)))
    reference = cpu_crazy_target_search_adapter()
    expected = reference.search(request)
    with _cuda() as cuda:
        inner = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.CRAZY,
        )
        candidate = _RecordingCandidateAdapter(inner)
        submission = submit_search(
            request,
            reference,
            CrazyTargetSearchSubmissionAdapter(candidate),
        )
        assert len(candidate.submitted[0].items) == MULTI_PREIMAGE_COUNT
        observed = submission.wait()

    assert observed.proposals == expected.proposals
    assert observed.capability.backend_id == CUDA_BACKEND
    assert submission.status().fallback is None


def test_live_cuda_teardown_drains_then_cpu_search_falls_back() -> None:
    """CUDA teardown closes multiposition lifetime before CPU search."""
    request = _request(tuple(range(TEARDOWN_CORPUS_SIZE)))
    reference = cpu_crazy_target_search_adapter()
    cuda = _cuda()
    candidate = CudaPrimitiveCandidateSubmissionAdapter(
        cuda,
        PrimitiveKind.CRAZY,
    )
    submission = submit_search(
        request,
        reference,
        CrazyTargetSearchSubmissionAdapter(candidate),
    )

    cuda.close()
    observed = submission.wait()

    assert observed.proposals == reference.search(request).proposals
    assert observed.capability.backend_id == CPU_BACKEND
    assert submission.status().fallback is SearchSubmissionFallback.WAIT_FAILED
