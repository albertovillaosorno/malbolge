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
#   - Pure and live evidence for candidate-backed verification tickets.
# - Must-Not:
#   - Claim speedup, independent streams, or candidate acceptance authority.
# - Allows:
#   - Inputs: exact rotate evidence batches and candidate ticket backends.
#   - Outputs: exact hint, nested lifetime, and optional outcome assertions.
#   - Side effects: scoped CPU counters and live CUDA allocations.
# - Split-When:
#   - Split when another evidence family gains independent ticket evidence.
# - Merge-When:
#   - Merge when another test owns the same candidate-backed hint contract.
# - Summary:
#   - Candidate-backed verification submission regression tests.
# - Description:
#   - Proves ordered evidence conversion, failure cleanup, and CUDA lifetime.
# - Usage:
#   - Collected by the optimizer suite; live routes skip without CUDA.
# - Defaults:
#   - Hints remain optional and never become candidate acceptance decisions.
#

"""Candidate-ticket-backed optional verification submission regressions."""

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
from accelerator.evidence_verification import EvidenceVerificationAssistAdapter
from accelerator.evidence_verification_submission import (
    EvidenceVerificationSubmissionAdapter,
)
from accelerator.evidence_verification_submission import (
    evidence_verification_submission_id,
)
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.submission import CandidateEvaluationTicket
from accelerator.submission import CandidateSubmissionAdapter
from accelerator.verification_submission import VerificationSubmissionOutcome
from accelerator.verification_submission import submit_verification_hints
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import VerificationAssistBatch
import pytest

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch

EXPECTED_SUBMISSION_ID = "candidate-evidence-verification-submission-v1"
VERIFIER_ID = "classic-rotate-check-v1"
CUDA_BACKEND = "cuda"
CORPUS_SIZE = 257


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _words(count: int) -> tuple[int, ...]:
    value = 0xA5A5_1F1F
    result: list[int] = []
    for _ in range(count):
        value = (value * 1_103_515_245 + 12_345) & 0xFFFF_FFFF
        result.append(value % (MAX_WORD + 1))
    return tuple(result)


def _batch() -> VerificationAssistBatch:
    return VerificationAssistBatch(
        items=tuple(
            CandidateWorkItem(
                logical_id=f"rotate-{index}",
                payload=encode_rotate_candidate(value),
            )
            for index, value in enumerate(_words(CORPUS_SIZE))
        ),
        verifier_id=VERIFIER_ID,
    )


@dataclass(slots=True)
class _CandidateTicket(CandidateEvaluationTicket):
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
        self.local_tickets: list[_CandidateTicket] = []
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
            return self._inner.submit(validated)
        evaluator = PrimitiveCandidateEvaluationAdapter(
            CpuExactPrimitiveAdapter(),
            PrimitiveKind.ROTATE,
        )
        ticket = _CandidateTicket(
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


def _adapter(
    candidate: CandidateSubmissionAdapter,
) -> EvidenceVerificationSubmissionAdapter:
    return EvidenceVerificationSubmissionAdapter(
        candidate,
        evaluator_id=ROTATE_EVALUATOR_ID,
        verifier_id=VERIFIER_ID,
    )


def test_evidence_verification_submission_identity_is_stable() -> None:
    """Evidence names the exact candidate-backed optional-hint lifetime."""
    assert evidence_verification_submission_id() == EXPECTED_SUBMISSION_ID


def test_cpu_candidate_ticket_publishes_exact_ordered_hints() -> None:
    """Deferred CPU candidate evidence becomes exact untrusted hints."""
    batch = _batch()
    candidate = _RecordingCandidateAdapter()
    submission = submit_verification_hints(batch, _adapter(candidate))

    hints = submission.wait()

    evaluator = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    )
    expected = EvidenceVerificationAssistAdapter(
        evaluator,
        evaluator_id=ROTATE_EVALUATOR_ID,
        verifier_id=VERIFIER_ID,
    ).assist(batch)
    assert hints == expected.hints
    assert candidate.local_tickets[0].waits == 1
    assert candidate.local_tickets[0].closes == 1


def test_malformed_candidate_evidence_closes_then_returns_no_hints() -> None:
    """Malformed nested evidence cannot publish and cleanly becomes no hints."""
    candidate = _RecordingCandidateAdapter(malformed=True)
    submission = submit_verification_hints(_batch(), _adapter(candidate))

    assert submission.wait() == ()
    assert candidate.local_tickets[0].closes == 1
    assert (
        submission.status().outcome
        is VerificationSubmissionOutcome.RESULT_INVALID
    )


def test_malformed_candidate_ticket_fails_before_optional_completion() -> None:
    """Unknown nested lifetime propagates before optional empty completion."""
    with pytest.raises(
        InvalidAcceleratorResultError,
        match="candidate submission adapter returned invalid ticket",
    ):
        _ = submit_verification_hints(
            _batch(),
            _adapter(_MalformedCandidateAdapter()),
        )


def test_verifier_identity_mismatch_fails_before_candidate_submission() -> None:
    """Another verifier identity cannot silently reuse the evidence adapter."""
    batch = VerificationAssistBatch(
        items=_batch().items,
        verifier_id="other-verifier",
    )
    candidate = _RecordingCandidateAdapter()

    with pytest.raises(
        InvalidAcceleratorWorkError,
        match="selects a different assist adapter",
    ):
        _ = submit_verification_hints(batch, _adapter(candidate))

    assert candidate.submitted == []


def test_live_cuda_ticket_matches_cpu_hints() -> None:
    """Live CUDA candidate ticket publishes exact ordered optional hints."""
    batch = _batch()
    cpu_candidate = _RecordingCandidateAdapter()
    cpu_hints = submit_verification_hints(
        batch,
        _adapter(cpu_candidate),
    ).wait()
    with _cuda() as cuda:
        candidate = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        submission = submit_verification_hints(batch, _adapter(candidate))
        cuda_hints = submission.wait()

    assert cuda_hints == cpu_hints
    capability = submission.status().actual_capability
    assert capability is not None
    assert capability.backend_id == CUDA_BACKEND


def test_live_cuda_teardown_drains_then_returns_no_hints() -> None:
    """CUDA teardown drains nested lifetime before optional empty completion."""
    batch = _batch()
    cuda = _cuda()
    candidate = CudaPrimitiveCandidateSubmissionAdapter(
        cuda,
        PrimitiveKind.ROTATE,
    )
    submission = submit_verification_hints(batch, _adapter(candidate))

    cuda.close()
    hints = submission.wait()

    assert hints == ()
    assert (
        submission.status().outcome is VerificationSubmissionOutcome.WAIT_FAILED
    )
