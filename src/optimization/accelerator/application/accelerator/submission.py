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
#   - Hardware-neutral lifetime and publication for candidate submissions.
# - Must-Not:
#   - Create hidden worker threads, expose device handles, or accept candidates.
# - Allows:
#   - Inputs: one validated candidate batch plus reference/optional adapters.
#   - Outputs: one structurally validated untrusted candidate result.
#   - Side effects: backend work owned until explicit wait or close.
# - Split-When:
#   - Split when search or verification submission gains a distinct contract.
# - Merge-When:
#   - Merge when another neutral port owns identical submission lifetime.
# - Summary:
#   - Validated hardware-neutral candidate submission lifetime.
# - Description:
#   - Defers publication until wait and falls back only after optional cleanup.
# - Usage:
#   - Submit candidate evaluation, inspect status, then wait or close.
# - Defaults:
#   - CPU reference work is deferred; invalid optional work falls back exactly.
#

"""Hardware-neutral asynchronous candidate submission lifetime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast
from typing import final

from accelerator.exact_primitives import AcceleratorError
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.work_ports import InvalidAcceleratorResultError

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateEvaluationResult

CANDIDATE_SUBMISSION_ID = "validated-candidate-submission-v1"


class CandidateSubmissionState(StrEnum):
    """Observable lifetime state for one neutral candidate submission."""

    PENDING = "pending"
    COMPLETED = "completed"
    CLOSED = "closed"
    FAILED = "failed"


class CandidateSubmissionFallback(StrEnum):
    """Stable reason that optional submission selected the CPU reference."""

    RESULT_INVALID = "preferred-result-invalid"
    SUBMIT_FAILED = "preferred-submit-failed"
    WAIT_FAILED = "preferred-wait-failed"


@dataclass(frozen=True, slots=True)
class CandidateSubmissionStatus:
    """Observable configured/actual route and submission state."""

    actual_capability: AcceleratorCapability | None
    fallback: CandidateSubmissionFallback | None
    preferred_capability: AcceleratorCapability | None
    state: CandidateSubmissionState


class CandidateEvaluationTicket(Protocol):
    """Backend-owned work ticket with explicit wait and cleanup."""

    def close(self) -> None:
        """Release pending or completed backend resources."""
        ...

    def wait(self) -> CandidateEvaluationResult:
        """Complete backend work and return untrusted candidate evidence."""
        ...


@dataclass(frozen=True, slots=True)
class _SubmissionRoute:
    fallback: CandidateSubmissionFallback | None = None
    preferred_capability: AcceleratorCapability | None = None
    preferred_ticket: CandidateEvaluationTicket | None = None


class CandidateSubmissionAdapter(Protocol):
    """Replaceable adapter capable of deferred candidate submission."""

    def capability(self) -> AcceleratorCapability:
        """Return stable configured backend identity."""
        ...

    def submit(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationTicket:
        """Submit work without publishing candidate evidence."""
        ...


@final
class CandidateEvaluationSubmission:
    """Neutral submission that validates publication and owns fallback."""

    __slots__ = (
        "_actual_capability",
        "_batch",
        "_failure",
        "_fallback",
        "_preferred_capability",
        "_preferred_ticket",
        "_reference",
        "_result",
        "_state",
    )

    def __init__(
        self,
        batch: CandidateEvaluationBatch,
        reference: CandidateEvaluationAdapter,
        route: _SubmissionRoute,
    ) -> None:
        """Bind one exact batch to optional and mandatory execution routes."""
        self._actual_capability: AcceleratorCapability | None = None
        self._batch = batch
        self._failure: AcceleratorError | None = None
        self._fallback = route.fallback
        self._preferred_capability = route.preferred_capability
        self._preferred_ticket = route.preferred_ticket
        self._reference = reference
        self._result: CandidateEvaluationResult | None = None
        self._state = CandidateSubmissionState.PENDING

    def close(self) -> None:
        """Close pending work and permanently reject later wait.

        Raises:
            AcceleratorError: If backend cleanup fails.

        """
        if self._state in {
            CandidateSubmissionState.CLOSED,
            CandidateSubmissionState.COMPLETED,
        }:
            return
        if self._state is CandidateSubmissionState.FAILED:
            self._raise_failure()
        ticket = self._preferred_ticket
        if ticket is not None:
            try:
                ticket.close()
            except AcceleratorError as error:
                self._record_failure(error)
                raise
            self._preferred_ticket = None
        self._state = CandidateSubmissionState.CLOSED

    def status(self) -> CandidateSubmissionStatus:
        """Return immutable route and lifetime evidence.

        Returns:
            Current configured route, actual route, fallback, and state.

        """
        return CandidateSubmissionStatus(
            actual_capability=self._actual_capability,
            fallback=self._fallback,
            preferred_capability=self._preferred_capability,
            state=self._state,
        )

    def wait(self) -> CandidateEvaluationResult:
        """Publish one validated result or execute exact CPU fallback.

        Returns:
            Structurally validated untrusted evidence from one exact route.

        Raises:
            AcceleratorExecutionError: If closed or execution cannot complete.

        """
        if self._state is CandidateSubmissionState.COMPLETED:
            return self._completed_result()
        if self._state is CandidateSubmissionState.CLOSED:
            message = "candidate evaluation submission is closed"
            raise AcceleratorExecutionError(message)
        if self._state is CandidateSubmissionState.FAILED:
            self._raise_failure()
        preferred = self._wait_preferred()
        if preferred is not None:
            return preferred
        return self._wait_reference()

    def _completed_result(self) -> CandidateEvaluationResult:
        result = self._result
        if result is None:
            message = "completed candidate submission has no result"
            raise AcceleratorExecutionError(message)
        return result

    def _publish(
        self,
        result: CandidateEvaluationResult,
        capability: AcceleratorCapability,
    ) -> CandidateEvaluationResult:
        self._actual_capability = capability
        self._result = result
        self._state = CandidateSubmissionState.COMPLETED
        return result

    def _record_failure(self, error: AcceleratorError) -> None:
        self._failure = error
        self._state = CandidateSubmissionState.FAILED

    def _raise_failure(self) -> None:
        failure = self._failure
        if failure is None:
            message = "failed candidate submission has no failure"
            raise AcceleratorExecutionError(message)
        raise failure

    def _wait_preferred(self) -> CandidateEvaluationResult | None:
        ticket = self._preferred_ticket
        capability = self._preferred_capability
        if ticket is None or capability is None:
            return None
        try:
            result = ticket.wait().validated_against(self._batch, capability)
        except InvalidAcceleratorResultError:
            self._fallback = CandidateSubmissionFallback.RESULT_INVALID
        except AcceleratorError:
            self._fallback = CandidateSubmissionFallback.WAIT_FAILED
        else:
            self._close_preferred()
            return self._publish(result, capability)
        self._close_preferred()
        return None

    def _close_preferred(self) -> None:
        ticket = self._preferred_ticket
        if ticket is None:
            return
        try:
            ticket.close()
        except AcceleratorError as error:
            self._record_failure(error)
            raise
        self._preferred_ticket = None

    def _wait_reference(self) -> CandidateEvaluationResult:
        capability = self._reference.capability()
        try:
            result = self._reference.evaluate(self._batch)
            validated = result.validated_against(self._batch, capability)
        except AcceleratorError as error:
            self._record_failure(error)
            raise
        return self._publish(validated, capability)


def candidate_submission_id() -> str:
    """Return the stable neutral candidate-submission contract identity.

    Returns:
        Versioned identity used by retained evidence and diagnostics.

    """
    return CANDIDATE_SUBMISSION_ID


def submit_candidate_evaluation(
    batch: CandidateEvaluationBatch,
    reference: CandidateEvaluationAdapter,
    preferred: CandidateSubmissionAdapter | None = None,
) -> CandidateEvaluationSubmission:
    """Submit optional work or retain an exact deferred CPU fallback.

    Returns:
        Neutral submission that owns validation, cleanup, and fallback.

    """
    validated = batch.validated()
    route = _preferred_route(validated, preferred)
    return CandidateEvaluationSubmission(validated, reference, route)


def _preferred_route(
    batch: CandidateEvaluationBatch,
    preferred: CandidateSubmissionAdapter | None,
) -> _SubmissionRoute:
    route = _SubmissionRoute()
    if preferred is not None:
        try:
            capability = preferred.capability()
            ticket = preferred.submit(batch)
        except AcceleratorError:
            route = _SubmissionRoute(
                fallback=CandidateSubmissionFallback.SUBMIT_FAILED,
            )
        else:
            route = _ticket_route(capability, ticket)
    return route


def _ticket_route(
    capability: AcceleratorCapability,
    ticket: object,
) -> _SubmissionRoute:
    if not _valid_ticket(ticket):
        message = "candidate submission adapter returned invalid ticket"
        raise InvalidAcceleratorResultError(message)
    admitted = cast("CandidateEvaluationTicket", ticket)
    return _SubmissionRoute(
        preferred_capability=capability,
        preferred_ticket=admitted,
    )


def _valid_ticket(ticket: object) -> bool:
    return callable(getattr(ticket, "close", None)) and callable(
        getattr(ticket, "wait", None)
    )
