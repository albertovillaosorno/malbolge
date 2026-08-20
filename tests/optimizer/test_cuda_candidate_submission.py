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
#   - Live CUDA evidence for neutral one-shot candidate submission lifetime.
# - Must-Not:
#   - Claim speedup, kernel overlap, or candidate acceptance authority.
# - Allows:
#   - Inputs: deterministic classic rotate/crazy candidate batches.
#   - Outputs: exact CPU-equal untrusted evidence and lifetime assertions.
#   - Side effects: scoped CUDA allocations, launches, downloads, and teardown.
# - Split-When:
#   - Split when another CUDA candidate family gains independent evidence.
# - Merge-When:
#   - Merge when another test owns the same neutral CUDA ticket contract.
# - Summary:
#   - Live exact CUDA candidate ticket and cleanup regressions.
# - Description:
#   - Proves explicit submission, publication, close, and concurrent tickets.
# - Usage:
#   - Runs with the optimizer CUDA suite and skips when CUDA is unavailable.
# - Defaults:
#   - Every route compares against the mandatory CPU reference.
#

"""Live CUDA candidate submission through the neutral ticket lifetime."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaPrimitiveCandidateSubmissionAdapter
from accelerator.cuda import cuda_independent_kernel_launch_id
from accelerator.cuda import cuda_independent_ticket_transfer_id
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import CRAZY_EVALUATOR_ID
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_crazy_candidate
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.submission import CandidateSubmissionFallback
from accelerator.submission import CandidateSubmissionState
from accelerator.submission import submit_candidate_evaluation
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateWorkItem
import pytest

if TYPE_CHECKING:
    from accelerator.work_ports import CandidateEvaluationResult

CUDA_KERNEL_LAUNCH_ID = "cuda-independent-stream-kernel-launch-v1"
CUDA_TICKET_TRANSFER_ID = "cuda-independent-stream-ticket-transfer-v1"
ROTATE_COUNT = 257
CRAZY_COUNT = 64
CUDA_BACKEND_ID = "cuda"
CPU_BACKEND_ID = "cpu-reference"


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _rotate_batch(offset: int = 0) -> CandidateEvaluationBatch:
    return CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"rotate-{offset}-{index}",
                payload=encode_rotate_candidate((offset + index) % 59_049),
            )
            for index in range(ROTATE_COUNT)
        ),
    )


def _crazy_batch() -> CandidateEvaluationBatch:
    return CandidateEvaluationBatch(
        evaluator_id=CRAZY_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"crazy-{index}",
                payload=encode_crazy_candidate(
                    index,
                    CRAZY_COUNT - index,
                ),
            )
            for index in range(CRAZY_COUNT)
        ),
    )


def _reference(kind: PrimitiveKind) -> PrimitiveCandidateEvaluationAdapter:
    return PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        kind,
    )


def _assert_same_evidence(
    observed: CandidateEvaluationResult,
    expected: CandidateEvaluationResult,
) -> None:
    assert observed.evaluator_id == expected.evaluator_id
    assert observed.items == expected.items
    assert observed.packed == expected.packed


def test_cuda_ticket_kernel_launch_identity_is_stable() -> None:
    """Candidate tickets name the exact isolated-stream launch lifetime."""
    assert cuda_independent_kernel_launch_id() == CUDA_KERNEL_LAUNCH_ID


def test_cuda_ticket_transfer_identity_is_stable() -> None:
    """Opt-in tickets name their registered same-stream transfer lifetime."""
    assert cuda_independent_ticket_transfer_id() == CUDA_TICKET_TRANSFER_ID


def test_streamed_cuda_ticket_uses_no_synchronous_host_copies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Streamed publication survives when synchronous copies are rejected."""
    batch = _rotate_batch()
    reference = _reference(PrimitiveKind.ROTATE)
    expected = reference.evaluate(batch)

    def reject_synchronous_copy(
        *arguments: object,
        **keywords: object,
    ) -> None:
        del arguments, keywords
        message = "streamed CUDA ticket attempted a synchronous host copy"
        raise AssertionError(message)

    with _cuda() as cuda:
        monkeypatch.setattr(
            CudaRuntime,
            "copy_to_device",
            reject_synchronous_copy,
        )
        monkeypatch.setattr(
            CudaRuntime,
            "copy_from_device",
            reject_synchronous_copy,
        )
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
            submit=cuda.ticket_transfers.submit,
        )
        observed = preferred.submit(batch).wait()

    _assert_same_evidence(observed, expected)


def test_streamed_cuda_crazy_submission_matches_cpu_reference() -> None:
    """Registered same-stream crazy transfers preserve exact evidence."""
    batch = _crazy_batch()
    reference = _reference(PrimitiveKind.CRAZY)
    expected = reference.evaluate(batch)
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.CRAZY,
            submit=cuda.ticket_transfers.submit,
        )
        observed = preferred.submit(batch).wait()

    _assert_same_evidence(observed, expected)
    assert observed.capability.backend_id == CUDA_BACKEND_ID


def test_streamed_adapter_close_drains_then_neutral_falls_back() -> None:
    """Streamed teardown releases registrations before exact CPU fallback."""
    batch = _rotate_batch()
    reference = _reference(PrimitiveKind.ROTATE)
    expected = reference.evaluate(batch)
    cuda = _cuda()
    preferred = CudaPrimitiveCandidateSubmissionAdapter(
        cuda,
        PrimitiveKind.ROTATE,
        submit=cuda.ticket_transfers.submit,
    )
    submission = submit_candidate_evaluation(batch, reference, preferred)

    cuda.close()
    observed = submission.wait()

    _assert_same_evidence(observed, expected)
    assert observed.capability.backend_id == CPU_BACKEND_ID
    assert (
        submission.status().fallback is CandidateSubmissionFallback.WAIT_FAILED
    )


def test_two_streamed_tickets_are_exact_under_reverse_wait() -> None:
    """Registered per-ticket buffers remain exact under reverse waiting."""
    first_batch = _rotate_batch()
    second_batch = _rotate_batch(2_048)
    reference = _reference(PrimitiveKind.ROTATE)
    expected = (
        reference.evaluate(first_batch),
        reference.evaluate(second_batch),
    )
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
            submit=cuda.ticket_transfers.submit,
        )
        first = preferred.submit(first_batch)
        second = preferred.submit(second_batch)
        observed_second = second.wait()
        observed_first = first.wait()

    _assert_same_evidence(observed_first, expected[0])
    _assert_same_evidence(observed_second, expected[1])


def test_cuda_rotate_submission_publishes_exactly_after_wait() -> None:
    """Neutral status stays pending until exact CUDA rotate publication."""
    batch = _rotate_batch()
    reference = _reference(PrimitiveKind.ROTATE)
    expected = reference.evaluate(batch)
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        submission = submit_candidate_evaluation(
            batch,
            reference,
            preferred,
        )
        pending = submission.status()
        assert pending.state is CandidateSubmissionState.PENDING
        assert pending.actual_capability is None
        assert pending.preferred_capability == cuda.capability()

        first = submission.wait()
        second = submission.wait()

    assert first is second
    _assert_same_evidence(first, expected)
    completed = submission.status()
    assert completed.actual_capability is not None
    assert completed.actual_capability.backend_id == CUDA_BACKEND_ID
    assert completed.fallback is None
    assert completed.state is CandidateSubmissionState.COMPLETED


def test_cuda_crazy_submission_matches_cpu_reference() -> None:
    """One-shot crazy launch preserves exact ordered candidate evidence."""
    batch = _crazy_batch()
    reference = _reference(PrimitiveKind.CRAZY)
    expected = reference.evaluate(batch)
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.CRAZY,
        )
        submission = submit_candidate_evaluation(
            batch,
            reference,
            preferred,
        )
        observed = submission.wait()

    _assert_same_evidence(observed, expected)
    assert observed.capability.backend_id == CUDA_BACKEND_ID


def test_empty_cuda_ticket_is_exact_and_direct_wait_is_idempotent() -> None:
    """Empty work publishes empty evidence without launching a CUDA kernel."""
    batch = CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=(),
    )
    reference = _reference(PrimitiveKind.ROTATE)
    expected = reference.evaluate(batch)
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        ticket = preferred.submit(batch)
        first = ticket.wait()
        second = ticket.wait()
        ticket.close()

    assert first is second
    _assert_same_evidence(first, expected)
    assert first.capability.backend_id == CUDA_BACKEND_ID


def test_neutral_close_drains_cuda_ticket_without_publication() -> None:
    """Close-before-wait synchronizes/frees and permanently blocks execution."""
    batch = _rotate_batch()
    with _cuda() as cuda:
        submission = submit_candidate_evaluation(
            batch,
            _reference(PrimitiveKind.ROTATE),
            CudaPrimitiveCandidateSubmissionAdapter(
                cuda,
                PrimitiveKind.ROTATE,
            ),
        )
        submission.close()
        submission.close()

        assert submission.status().state is CandidateSubmissionState.CLOSED
        with pytest.raises(
            AcceleratorExecutionError,
            match="submission is closed",
        ):
            _ = submission.wait()


def test_adapter_close_drains_ticket_then_neutral_falls_back() -> None:
    """Adapter teardown completes device lifetime before exact CPU fallback."""
    batch = _rotate_batch()
    reference = _reference(PrimitiveKind.ROTATE)
    expected = reference.evaluate(batch)
    cuda = _cuda()
    preferred = CudaPrimitiveCandidateSubmissionAdapter(
        cuda,
        PrimitiveKind.ROTATE,
    )
    submission = submit_candidate_evaluation(batch, reference, preferred)

    cuda.close()
    observed = submission.wait()

    _assert_same_evidence(observed, expected)
    assert observed.capability.backend_id == CPU_BACKEND_ID
    assert (
        submission.status().fallback is CandidateSubmissionFallback.WAIT_FAILED
    )


def test_two_cuda_tickets_remain_exact_when_waited_in_reverse() -> None:
    """Independent streams and buffers remain exact under reverse waiting."""
    first_batch = _rotate_batch()
    second_batch = _rotate_batch(1_024)
    reference = _reference(PrimitiveKind.ROTATE)
    expected = (
        reference.evaluate(first_batch),
        reference.evaluate(second_batch),
    )
    with _cuda() as cuda:
        preferred = CudaPrimitiveCandidateSubmissionAdapter(
            cuda,
            PrimitiveKind.ROTATE,
        )
        first = submit_candidate_evaluation(
            first_batch,
            reference,
            preferred,
        )
        second = submit_candidate_evaluation(
            second_batch,
            reference,
            preferred,
        )
        observed_second = second.wait()
        observed_first = first.wait()

    _assert_same_evidence(observed_first, expected[0])
    _assert_same_evidence(observed_second, expected[1])
