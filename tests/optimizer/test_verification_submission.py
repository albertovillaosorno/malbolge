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
#   - Contract evidence for optional verification submission lifetime.
# - Must-Not:
#   - Create workers or treat hints as candidate acceptance decisions.
# - Allows:
#   - Inputs: deterministic optional tickets and exact hint batches.
#   - Outputs: state, route, cleanup, and ordered hint assertions.
#   - Side effects: in-memory counters only.
# - Split-When:
#   - Split when a live backend requires independent integration evidence.
# - Merge-When:
#   - Merge when another test owns the same complete optional-hint lifetime.
# - Summary:
#   - Hardware-neutral verification submission regression tests.
# - Description:
#   - Proves optional empty completion, validation, idempotence, and cleanup.
# - Usage:
#   - Collected by the optimizer Python test suite.
# - Defaults:
#   - Clean optional failure yields no hints; unknown lifetime fails closed.
#

"""Hardware-neutral optional verification submission regressions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.verification_submission import VerificationAssistSubmission
from accelerator.verification_submission import VerificationAssistTicket
from accelerator.verification_submission import VerificationSubmissionAdapter
from accelerator.verification_submission import VerificationSubmissionOutcome
from accelerator.verification_submission import VerificationSubmissionState
from accelerator.verification_submission import submit_verification_hints
from accelerator.verification_submission import verification_submission_id
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import VerificationAssistBatch
from accelerator.work_ports import VerificationAssistResult
from accelerator.work_ports import VerificationHint
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    type VerificationSubmissionConstructor = Callable[
        [VerificationAssistBatch, object],
        VerificationAssistSubmission,
    ]

EXPECTED_SUBMISSION_ID = "validated-verification-assist-submission-v1"
REPEATED_WAIT_COUNT = 2
VERIFIER_ID = "trusted-check-v1"
PREFERRED_CAPABILITY = AcceleratorCapability(
    backend_id="test-verification-async",
    device_arch="test",
    device_name="test-device",
)


def _batch() -> VerificationAssistBatch:
    return VerificationAssistBatch(
        items=(
            CandidateWorkItem(logical_id="a", payload=b"abc"),
            CandidateWorkItem(logical_id="b", payload=b"xyz"),
        ),
        verifier_id=VERIFIER_ID,
    )


def _result(
    batch: VerificationAssistBatch,
    capability: AcceleratorCapability,
) -> VerificationAssistResult:
    return VerificationAssistResult(
        capability=capability,
        hints=tuple(
            VerificationHint(
                logical_id=item.logical_id,
                payload=item.payload[::-1],
            )
            for item in batch.items
        ),
        verifier_id=batch.verifier_id,
    )


@dataclass(slots=True)
class _Counters:
    closes: int = 0
    waits: int = 0


class _Ticket(VerificationAssistTicket):
    _counters: _Counters
    _failure: AcceleratorExecutionError | None
    _result: VerificationAssistResult | None

    def __init__(
        self,
        counters: _Counters,
        result: VerificationAssistResult | None,
        failure: AcceleratorExecutionError | None = None,
    ) -> None:
        self._counters = counters
        self._failure = failure
        self._result = result

    @override
    def close(self) -> None:
        self._counters.closes += 1

    @override
    def wait(self) -> VerificationAssistResult:
        self._counters.waits += 1
        if self._failure is not None:
            raise self._failure
        if self._result is None:
            message = "synthetic verification ticket has no result"
            raise AcceleratorExecutionError(message)
        return self._result


@final
class _CloseFailingTicket(_Ticket):
    @override
    def close(self) -> None:
        self._counters.closes += 1
        message = "synthetic verification ticket cleanup failure"
        raise AcceleratorExecutionError(message)


@final
class _AsyncAdapter(VerificationSubmissionAdapter):
    def __init__(
        self,
        ticket: VerificationAssistTicket | object,
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
        batch: VerificationAssistBatch,
    ) -> VerificationAssistTicket:
        _ = batch.validated()
        if self._submit_failure:
            message = "synthetic verification submit failure"
            raise AcceleratorExecutionError(message)
        return cast("VerificationAssistTicket", self._ticket)


def test_verification_submission_identity_is_stable() -> None:
    """Evidence names the exact optional-hint lifetime contract."""
    assert verification_submission_id() == EXPECTED_SUBMISSION_ID


def test_no_backend_is_deferred_empty_and_wait_is_idempotent() -> None:
    """Missing optional assistance remains pending until explicit wait."""
    submission = submit_verification_hints(_batch())

    assert submission.status().state is VerificationSubmissionState.PENDING
    assert (
        submission.status().outcome
        is VerificationSubmissionOutcome.NO_PREFERRED
    )
    first = submission.wait()
    second = submission.wait()

    assert first is second
    assert first == ()
    assert submission.status().state is VerificationSubmissionState.COMPLETED
    assert submission.status().actual_capability is None


def test_preferred_ticket_publishes_only_after_exact_validation() -> None:
    """Optional hints close before exact ordered publication."""
    batch = _batch()
    counters = _Counters()
    ticket = _Ticket(counters, _result(batch, PREFERRED_CAPABILITY))
    submission = submit_verification_hints(batch, _AsyncAdapter(ticket))

    first = submission.wait()
    second = submission.wait()

    assert first is second
    assert first == _result(batch, PREFERRED_CAPABILITY).hints
    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().actual_capability == PREFERRED_CAPABILITY
    assert submission.status().outcome is None


def test_submit_failure_completes_empty_only_at_wait() -> None:
    """Typed optional submit failure remains pending until empty completion."""
    submission = submit_verification_hints(
        _batch(),
        _AsyncAdapter(object(), submit_failure=True),
    )

    assert submission.status().state is VerificationSubmissionState.PENDING
    assert (
        submission.status().outcome
        is VerificationSubmissionOutcome.SUBMIT_FAILED
    )
    assert submission.wait() == ()
    assert submission.status().state is VerificationSubmissionState.COMPLETED


def test_malformed_ticket_fails_before_optional_empty_completion() -> None:
    """A ticket without wait/close cannot masquerade as unavailable hints."""
    with pytest.raises(
        InvalidAcceleratorResultError,
        match="returned invalid ticket",
    ):
        _ = submit_verification_hints(_batch(), _AsyncAdapter(object()))


def test_wait_failure_closes_ticket_before_empty_completion() -> None:
    """Optional failure releases lifetime before returning no hints."""
    counters = _Counters()
    failure = AcceleratorExecutionError("synthetic verification wait failure")
    submission = submit_verification_hints(
        _batch(),
        _AsyncAdapter(_Ticket(counters, None, failure)),
    )

    assert submission.wait() == ()
    assert counters == _Counters(closes=1, waits=1)
    assert (
        submission.status().outcome is VerificationSubmissionOutcome.WAIT_FAILED
    )
    assert submission.status().state is VerificationSubmissionState.COMPLETED


def test_malformed_result_closes_ticket_before_empty_completion() -> None:
    """Wrong hint order cannot publish and cleanly becomes no assistance."""
    batch = _batch()
    counters = _Counters()
    malformed = VerificationAssistResult(
        capability=PREFERRED_CAPABILITY,
        hints=(VerificationHint(logical_id="wrong", payload=b"bad"),),
        verifier_id=batch.verifier_id,
    )
    submission = submit_verification_hints(
        batch,
        _AsyncAdapter(_Ticket(counters, malformed)),
    )

    assert submission.wait() == ()
    assert counters.closes == 1
    assert (
        submission.status().outcome
        is VerificationSubmissionOutcome.RESULT_INVALID
    )


def test_close_before_wait_releases_ticket_and_blocks_hints() -> None:
    """Explicit close is idempotent and permanently prevents publication."""
    batch = _batch()
    counters = _Counters()
    submission = submit_verification_hints(
        batch,
        _AsyncAdapter(_Ticket(counters, _result(batch, PREFERRED_CAPABILITY))),
    )

    submission.close()
    submission.close()

    assert counters == _Counters(closes=1)
    assert submission.status().state is VerificationSubmissionState.CLOSED
    with pytest.raises(AcceleratorExecutionError, match="submission is closed"):
        _ = submission.wait()


def test_cleanup_failure_blocks_empty_completion_and_is_cached() -> None:
    """Unknown optional lifetime records failure instead of empty hints."""
    counters = _Counters()
    wait_failure = AcceleratorExecutionError(
        "synthetic verification wait failure"
    )
    ticket = _CloseFailingTicket(counters, None, wait_failure)
    submission = submit_verification_hints(_batch(), _AsyncAdapter(ticket))

    for _ in range(REPEATED_WAIT_COUNT):
        with pytest.raises(
            AcceleratorExecutionError,
            match="ticket cleanup failure",
        ):
            _ = submission.wait()

    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().state is VerificationSubmissionState.FAILED


@final
class _MalformedCapabilityAdapter(VerificationSubmissionAdapter):
    def __init__(self) -> None:
        self.submits = 0

    @override
    def capability(self) -> AcceleratorCapability:
        malformed: object = object()
        return cast("AcceleratorCapability", malformed)

    @override
    def submit(
        self,
        batch: VerificationAssistBatch,
    ) -> VerificationAssistTicket:
        _ = batch
        self.submits += 1
        return cast("VerificationAssistTicket", object())


def test_malformed_preferred_capability_fails_before_hint_submit() -> None:
    """Invalid route metadata cannot create a hint ticket or status."""
    adapter = _MalformedCapabilityAdapter()

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="preferred accelerator capability has wrong type",
    ):
        _ = submit_verification_hints(_batch(), adapter)

    assert adapter.submits == 0


@final
class _ForeignResultTicket(_Ticket):
    @override
    def wait(self) -> VerificationAssistResult:
        self._counters.waits += 1
        foreign: object = object()
        return cast("VerificationAssistResult", foreign)


def test_foreign_verification_result_closes_and_completes_empty() -> None:
    """A foreign hint result becomes explicit invalid optional assistance."""
    counters = _Counters()
    submission = submit_verification_hints(
        _batch(),
        _AsyncAdapter(_ForeignResultTicket(counters, None)),
    )

    assert submission.wait() == ()
    assert counters == _Counters(closes=1, waits=1)
    assert (
        submission.status().outcome
        is VerificationSubmissionOutcome.RESULT_INVALID
    )
    assert submission.status().state is VerificationSubmissionState.COMPLETED


def test_submission_requires_structural_verification_adapter() -> None:
    """A foreign submit adapter fails before capability access."""
    foreign: object = object()

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="verification submission adapter has wrong type",
    ):
        _ = submit_verification_hints(
            _batch(),
            cast("VerificationSubmissionAdapter", foreign),
        )


def test_direct_verification_submission_validates_input_and_route() -> None:
    """Direct construction cannot bypass batch or route admission."""
    foreign: object = object()
    constructor = cast(
        "VerificationSubmissionConstructor",
        cast("object", VerificationAssistSubmission),
    )

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="verification submission batch has wrong type",
    ):
        _ = constructor(cast("VerificationAssistBatch", foreign), foreign)
    with pytest.raises(
        InvalidAcceleratorResultError,
        match="verification submission route has wrong type",
    ):
        _ = constructor(_batch(), foreign)
