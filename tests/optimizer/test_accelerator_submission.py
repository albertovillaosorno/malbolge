# File:
#   - test_accelerator_submission.py
# Path:
#   - tests/optimizer/test_accelerator_submission.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - Contract evidence for neutral candidate submission lifetime and fallback.
# - Must-Not:
#   - Create worker threads or treat candidate evidence as accepted output.
# - Allows:
#   - Inputs: deterministic fake tickets and the mandatory CPU reference.
#   - Outputs: state, route, cleanup, and exact result assertions.
#   - Side effects: in-memory counters only.
# - Split-When:
#   - Split when a live backend requires independent integration evidence.
# - Merge-When:
#   - Merge when another test owns the same complete submission contract.
# - Summary:
#   - Hardware-neutral candidate submission regression tests.
# - Description:
#   - Proves deferred execution, validation, fallback, idempotence, and close.
# - Usage:
#   - Collected by the optimizer Python test suite.
# - Defaults:
#   - Optional failures fall back only after ticket cleanup succeeds.
#
# Related documents:
# - accelerator/submission.py
#
# Large file:
#   - false
#

"""Hardware-neutral candidate submission lifetime regressions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from typing import final
from typing import override

import pytest

from accelerator.cpu import CpuCandidateEvaluationAdapter
from accelerator.cpu.work_ports import CPU_WORK_CAPABILITY
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.submission import CandidateEvaluationTicket
from accelerator.submission import CandidateSubmissionAdapter
from accelerator.submission import CandidateSubmissionFallback
from accelerator.submission import CandidateSubmissionState
from accelerator.submission import candidate_submission_id
from accelerator.submission import submit_candidate_evaluation
from accelerator.work_ports import CandidateEvaluationAdapter
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateEvidence
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorResultError

EXPECTED_SUBMISSION_ID = "validated-candidate-submission-v1"
BATCH_ITEM_COUNT = 2
REPEATED_WAIT_COUNT = 2
PREFERRED_CAPABILITY = AcceleratorCapability(
    backend_id="test-async",
    device_arch="test",
    device_name="test-device",
)


def _batch() -> CandidateEvaluationBatch:
    return CandidateEvaluationBatch(
        evaluator_id="reverse-bytes-v1",
        items=(
            CandidateWorkItem(logical_id="a", payload=b"abc"),
            CandidateWorkItem(logical_id="b", payload=b"xyz"),
        ),
    )


def _result(
    batch: CandidateEvaluationBatch,
    capability: AcceleratorCapability,
) -> CandidateEvaluationResult:
    return CandidateEvaluationResult(
        capability=capability,
        evaluator_id=batch.evaluator_id,
        items=tuple(
            CandidateEvidence(
                logical_id=item.logical_id,
                payload=item.payload[::-1],
            )
            for item in batch.items
        ),
    )


@dataclass(slots=True)
class _Counters:
    closes: int = 0
    reference_calls: int = 0
    waits: int = 0


class _Ticket(CandidateEvaluationTicket):
    _counters: _Counters
    _failure: AcceleratorExecutionError | None
    _result: CandidateEvaluationResult | None

    def __init__(
        self,
        counters: _Counters,
        result: CandidateEvaluationResult | None,
        failure: AcceleratorExecutionError | None = None,
    ) -> None:
        self._counters = counters
        self._failure = failure
        self._result = result

    @override
    def close(self) -> None:
        self._counters.closes += 1

    @override
    def wait(self) -> CandidateEvaluationResult:
        self._counters.waits += 1
        if self._failure is not None:
            raise self._failure
        if self._result is None:
            message = "synthetic ticket has no result"
            raise AcceleratorExecutionError(message)
        return self._result


@final
class _CloseFailingTicket(_Ticket):
    @override
    def close(self) -> None:
        self._counters.closes += 1
        message = "synthetic ticket cleanup failure"
        raise AcceleratorExecutionError(message)


@final
class _AsyncAdapter(CandidateSubmissionAdapter):
    def __init__(
        self,
        ticket: CandidateEvaluationTicket | object,
        *,
        submit_failure: bool = False,
    ) -> None:
        self._submit_failure = submit_failure
        self._ticket = ticket

    @override
    def capability(self) -> AcceleratorCapability:
        return PREFERRED_CAPABILITY

    @override
    def submit(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationTicket:
        _ = batch.validated()
        if self._submit_failure:
            message = "synthetic submit failure"
            raise AcceleratorExecutionError(message)
        return cast("CandidateEvaluationTicket", self._ticket)


@final
class _FailingReference(CandidateEvaluationAdapter):
    def __init__(self, counters: _Counters) -> None:
        self._counters = counters

    @override
    def capability(self) -> AcceleratorCapability:
        return CPU_WORK_CAPABILITY

    @override
    def evaluate(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationResult:
        _ = batch.validated()
        self._counters.reference_calls += 1
        message = "synthetic mandatory reference failure"
        raise AcceleratorExecutionError(message)


def _reference(counters: _Counters) -> CpuCandidateEvaluationAdapter:
    def evaluate(payload: bytes) -> bytes:
        counters.reference_calls += 1
        return payload[::-1]

    return CpuCandidateEvaluationAdapter("reverse-bytes-v1", evaluate)


def test_candidate_submission_identity_is_stable() -> None:
    """Evidence names the exact neutral lifetime contract."""
    assert candidate_submission_id() == EXPECTED_SUBMISSION_ID


def test_reference_execution_is_deferred_and_wait_is_idempotent() -> None:
    """CPU work starts only at wait and publishes the same validated result."""
    counters = _Counters()
    submission = submit_candidate_evaluation(_batch(), _reference(counters))

    assert submission.status().state is CandidateSubmissionState.PENDING
    assert counters.reference_calls == 0
    first = submission.wait()
    second = submission.wait()

    assert first is second
    assert counters.reference_calls == BATCH_ITEM_COUNT
    assert submission.status().actual_capability == CPU_WORK_CAPABILITY
    assert submission.status().state is CandidateSubmissionState.COMPLETED


def test_preferred_ticket_publishes_only_after_exact_validation() -> None:
    """Optional evidence completes once and closes before publication."""
    batch = _batch()
    counters = _Counters()
    ticket = _Ticket(counters, _result(batch, PREFERRED_CAPABILITY))
    submission = submit_candidate_evaluation(
        batch,
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    result = submission.wait()

    assert result.capability == PREFERRED_CAPABILITY
    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().actual_capability == PREFERRED_CAPABILITY
    assert submission.status().fallback is None


def test_submit_failure_selects_deferred_reference() -> None:
    """Typed submit failure never starts CPU work before explicit wait."""
    counters = _Counters()
    adapter = _AsyncAdapter(object(), submit_failure=True)
    submission = submit_candidate_evaluation(
        _batch(),
        _reference(counters),
        adapter,
    )

    assert counters.reference_calls == 0
    assert (
        submission.status().fallback
        is CandidateSubmissionFallback.SUBMIT_FAILED
    )
    assert submission.wait().capability == CPU_WORK_CAPABILITY
    assert counters.reference_calls == BATCH_ITEM_COUNT


def test_malformed_ticket_fails_before_unknown_lifetime_can_fallback() -> None:
    """An optional ticket without wait/close cannot leak into CPU fallback."""
    counters = _Counters()
    adapter = _AsyncAdapter(object())

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="returned invalid ticket",
    ):
        _ = submit_candidate_evaluation(
            _batch(),
            _reference(counters),
            adapter,
        )

    assert counters.reference_calls == 0


def test_wait_failure_closes_ticket_before_reference_fallback() -> None:
    """Optional execution failure releases backend lifetime before CPU work."""
    counters = _Counters()
    failure = AcceleratorExecutionError("synthetic wait failure")
    ticket = _Ticket(counters, None, failure)
    submission = submit_candidate_evaluation(
        _batch(),
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    result = submission.wait()

    assert result.capability == CPU_WORK_CAPABILITY
    assert counters == _Counters(closes=1, reference_calls=2, waits=1)
    assert (
        submission.status().fallback is CandidateSubmissionFallback.WAIT_FAILED
    )


def test_malformed_result_closes_ticket_and_falls_back() -> None:
    """Wrong request order cannot cross publication and selects CPU exactly."""
    batch = _batch()
    counters = _Counters()
    malformed = CandidateEvaluationResult(
        capability=PREFERRED_CAPABILITY,
        evaluator_id=batch.evaluator_id,
        items=(CandidateEvidence(logical_id="wrong", payload=b"bad"),),
    )
    submission = submit_candidate_evaluation(
        batch,
        _reference(counters),
        _AsyncAdapter(_Ticket(counters, malformed)),
    )

    result = submission.wait()

    assert result.capability == CPU_WORK_CAPABILITY
    assert counters.closes == 1
    assert (
        submission.status().fallback
        is CandidateSubmissionFallback.RESULT_INVALID
    )


def test_close_before_wait_releases_ticket_and_blocks_execution() -> None:
    """Explicit close is idempotent and permanently prevents publication."""
    batch = _batch()
    counters = _Counters()
    submission = submit_candidate_evaluation(
        batch,
        _reference(counters),
        _AsyncAdapter(_Ticket(counters, _result(batch, PREFERRED_CAPABILITY))),
    )

    submission.close()
    submission.close()

    assert counters == _Counters(closes=1)
    assert submission.status().state is CandidateSubmissionState.CLOSED
    with pytest.raises(AcceleratorExecutionError, match="submission is closed"):
        _ = submission.wait()


def test_mandatory_failure_is_recorded_and_not_reexecuted() -> None:
    """Mandatory failure remains failed and repeated waits do not rerun it."""
    counters = _Counters()
    submission = submit_candidate_evaluation(
        _batch(),
        _FailingReference(counters),
    )

    for _ in range(REPEATED_WAIT_COUNT):
        with pytest.raises(
            AcceleratorExecutionError,
            match="mandatory reference failure",
        ):
            _ = submission.wait()

    assert counters.reference_calls == 1
    assert submission.status().state is CandidateSubmissionState.FAILED


def test_cleanup_failure_blocks_reference_fallback() -> None:
    """Unknown optional lifetime prevents CPU fallback and records failure."""
    counters = _Counters()
    wait_failure = AcceleratorExecutionError("synthetic wait failure")
    ticket = _CloseFailingTicket(counters, None, wait_failure)
    submission = submit_candidate_evaluation(
        _batch(),
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    with pytest.raises(
        AcceleratorExecutionError,
        match="ticket cleanup failure",
    ):
        _ = submission.wait()

    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().state is CandidateSubmissionState.FAILED
