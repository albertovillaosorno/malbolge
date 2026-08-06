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
#   - Hardware-neutral lifetime for optional verification-assist submissions.
# - Must-Not:
#   - Create hidden workers, expose device handles, or accept candidates.
# - Allows:
#   - Inputs: one exact verification-assist batch and optional backend ticket.
#   - Outputs: validated untrusted hints or an explicit empty optional result.
#   - Side effects: backend work owned until explicit wait or close.
# - Split-When:
#   - Split when trusted verification gains a separate execution lifetime.
# - Merge-When:
#   - Merge when another neutral port owns identical optional-hint lifetime.
# - Summary:
#   - Validated optional verification-assist submission lifetime.
# - Description:
#   - Publishes hints only after wait and successful backend cleanup.
# - Usage:
#   - Submit optional assistance, inspect status, then wait or close.
# - Defaults:
#   - Missing or cleanly failed assistance completes with no hints.
#

"""Hardware-neutral optional verification-assist submission lifetime."""

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
from accelerator.work_ports import VerificationAssistBatch
from accelerator.work_ports import validated_accelerator_capability
from accelerator.work_ports import validated_verification_assist_result

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import VerificationAssistResult
    from accelerator.work_ports import VerificationHint

VERIFICATION_SUBMISSION_ID = "validated-verification-assist-submission-v1"


class VerificationSubmissionState(StrEnum):
    """Observable lifetime state for one optional hint submission."""

    PENDING = "pending"
    COMPLETED = "completed"
    CLOSED = "closed"
    FAILED = "failed"


class VerificationSubmissionOutcome(StrEnum):
    """Stable optional-assistance outcome when no hints are published."""

    NO_PREFERRED = "no-preferred-backend"
    RESULT_INVALID = "preferred-result-invalid"
    SUBMIT_FAILED = "preferred-submit-failed"
    WAIT_FAILED = "preferred-wait-failed"


@dataclass(frozen=True, slots=True)
class VerificationSubmissionStatus:
    """Observable configured/actual route, outcome, and lifetime state."""

    actual_capability: AcceleratorCapability | None
    outcome: VerificationSubmissionOutcome | None
    preferred_capability: AcceleratorCapability | None
    state: VerificationSubmissionState


class VerificationAssistTicket(Protocol):
    """Backend-owned optional hint ticket with explicit wait and cleanup."""

    def close(self) -> None:
        """Release pending or completed backend resources."""
        ...

    def wait(self) -> VerificationAssistResult:
        """Complete backend work and return untrusted hints."""
        ...


@dataclass(frozen=True, slots=True)
class _VerificationRoute:
    outcome: VerificationSubmissionOutcome | None = None
    preferred_capability: AcceleratorCapability | None = None
    preferred_ticket: VerificationAssistTicket | None = None


class VerificationSubmissionAdapter(Protocol):
    """Replaceable adapter capable of deferred optional hint submission."""

    def capability(self) -> AcceleratorCapability:
        """Return stable configured backend identity."""
        ...

    def submit(
        self,
        batch: VerificationAssistBatch,
    ) -> VerificationAssistTicket:
        """Submit assistance without publishing hints."""
        ...


@final
class VerificationAssistSubmission:
    """Neutral optional submission that validates hint publication."""

    __slots__ = (
        "_actual_capability",
        "_batch",
        "_failure",
        "_hints",
        "_outcome",
        "_preferred_capability",
        "_preferred_ticket",
        "_state",
    )

    def __init__(
        self,
        batch: VerificationAssistBatch,
        route: _VerificationRoute,
    ) -> None:
        """Bind one exact optional-hint request to one backend route."""
        validated_batch = _validated_submission_batch(batch)
        validated_route = _validated_route(route)
        self._actual_capability: AcceleratorCapability | None = None
        self._batch = validated_batch
        self._failure: AcceleratorError | None = None
        self._hints: tuple[VerificationHint, ...] = ()
        self._outcome = validated_route.outcome
        self._preferred_capability = validated_route.preferred_capability
        self._preferred_ticket = validated_route.preferred_ticket
        self._state = VerificationSubmissionState.PENDING

    def close(self) -> None:
        """Close pending assistance and permanently reject later wait.

        Raises:
            AcceleratorError: If backend cleanup fails.

        """
        if self._state in {
            VerificationSubmissionState.CLOSED,
            VerificationSubmissionState.COMPLETED,
        }:
            return
        if self._state is VerificationSubmissionState.FAILED:
            self._raise_failure()
        ticket = self._preferred_ticket
        if ticket is not None:
            try:
                ticket.close()
            except AcceleratorError as error:
                self._record_failure(error)
                raise
            self._preferred_ticket = None
        self._state = VerificationSubmissionState.CLOSED

    def status(self) -> VerificationSubmissionStatus:
        """Return immutable optional route and lifetime evidence.

        Returns:
            Current configured route, actual route, outcome, and state.

        """
        return VerificationSubmissionStatus(
            actual_capability=self._actual_capability,
            outcome=self._outcome,
            preferred_capability=self._preferred_capability,
            state=self._state,
        )

    def wait(self) -> tuple[VerificationHint, ...]:
        """Publish validated hints or complete with no optional assistance.

        Returns:
            Ordered untrusted hints, or empty after a clean optional failure.

        Raises:
            AcceleratorExecutionError: If closed or cleanup cannot complete.

        """
        if self._state is VerificationSubmissionState.COMPLETED:
            return self._hints
        if self._state is VerificationSubmissionState.CLOSED:
            message = "verification-assist submission is closed"
            raise AcceleratorExecutionError(message)
        if self._state is VerificationSubmissionState.FAILED:
            self._raise_failure()
        ticket = self._preferred_ticket
        if ticket is None:
            return self._complete_empty()
        return self._wait_preferred(ticket)

    def _complete_empty(self) -> tuple[VerificationHint, ...]:
        self._state = VerificationSubmissionState.COMPLETED
        return ()

    def _publish(
        self,
        result: VerificationAssistResult,
        capability: AcceleratorCapability,
    ) -> tuple[VerificationHint, ...]:
        self._actual_capability = capability
        self._hints = result.hints
        self._state = VerificationSubmissionState.COMPLETED
        return self._hints

    def _record_failure(self, error: AcceleratorError) -> None:
        self._failure = error
        self._state = VerificationSubmissionState.FAILED

    def _raise_failure(self) -> None:
        failure = self._failure
        if failure is None:
            message = "failed verification submission has no failure"
            raise AcceleratorExecutionError(message)
        raise failure

    def _wait_preferred(
        self,
        ticket: VerificationAssistTicket,
    ) -> tuple[VerificationHint, ...]:
        capability = self._preferred_capability
        if capability is None:
            message = "verification ticket has no backend capability"
            raise AcceleratorExecutionError(message)
        try:
            result = validated_verification_assist_result(
                ticket.wait(),
            ).validated_against(self._batch, capability)
        except InvalidAcceleratorResultError:
            self._outcome = VerificationSubmissionOutcome.RESULT_INVALID
        except AcceleratorError:
            self._outcome = VerificationSubmissionOutcome.WAIT_FAILED
        else:
            self._close_preferred()
            return self._publish(result, capability)
        self._close_preferred()
        return self._complete_empty()

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


def verification_submission_id() -> str:
    """Return the stable optional-hint submission contract identity.

    Returns:
        Versioned identity used by retained evidence and diagnostics.

    """
    return VERIFICATION_SUBMISSION_ID


def submit_verification_hints(
    batch: VerificationAssistBatch,
    preferred: VerificationSubmissionAdapter | None = None,
) -> VerificationAssistSubmission:
    """Submit optional assistance without granting acceptance authority.

    Returns:
        Neutral submission owning validation, cleanup, and empty completion.

    """
    validated = batch.validated()
    route = _preferred_route(validated, preferred)
    return VerificationAssistSubmission(validated, route)


def _validated_submission_batch(value: object) -> VerificationAssistBatch:
    if type(value) is not VerificationAssistBatch:
        message = "verification submission batch has wrong type"
        raise InvalidAcceleratorResultError(message)
    return value.validated()


def _validated_route(value: object) -> _VerificationRoute:
    if type(value) is not _VerificationRoute:
        message = "verification submission route has wrong type"
        raise InvalidAcceleratorResultError(message)
    if (
        value.outcome is not None
        and type(value.outcome) is not VerificationSubmissionOutcome
    ):
        message = "verification submission outcome has wrong type"
        raise InvalidAcceleratorResultError(message)
    _validate_route_ticket(
        value.preferred_capability,
        value.preferred_ticket,
        value.outcome,
    )
    return value


def _validate_route_ticket(
    capability: AcceleratorCapability | None,
    ticket: VerificationAssistTicket | None,
    outcome: VerificationSubmissionOutcome | None,
) -> None:
    if (capability is None) != (ticket is None):
        message = "verification submission route has incomplete preferred state"
        raise InvalidAcceleratorResultError(message)
    if capability is not None:
        _ = validated_accelerator_capability(
            capability,
            "verification submission route capability",
        )
    _validate_ticket_outcome(ticket, outcome)


def _validate_ticket_outcome(
    ticket: VerificationAssistTicket | None,
    outcome: VerificationSubmissionOutcome | None,
) -> None:
    if ticket is not None and not _valid_ticket(ticket):
        message = "verification submission route has invalid ticket"
        raise InvalidAcceleratorResultError(message)
    if ticket is not None and outcome is not None:
        message = "verification submission route mixes ticket and outcome"
        raise InvalidAcceleratorResultError(message)
    if ticket is None and outcome is None:
        message = "verification submission route has no outcome"
        raise InvalidAcceleratorResultError(message)


def _preferred_route(
    batch: VerificationAssistBatch,
    preferred: VerificationSubmissionAdapter | None,
) -> _VerificationRoute:
    if preferred is None:
        return _VerificationRoute(
            outcome=VerificationSubmissionOutcome.NO_PREFERRED,
        )
    try:
        admitted = _validated_submission_adapter(preferred)
        capability = validated_accelerator_capability(
            admitted.capability(),
            "preferred accelerator capability",
        )
        ticket = admitted.submit(batch)
    except InvalidAcceleratorResultError:
        raise
    except AcceleratorError:
        return _VerificationRoute(
            outcome=VerificationSubmissionOutcome.SUBMIT_FAILED,
        )
    return _ticket_route(capability, ticket)


def _validated_submission_adapter(
    value: object,
) -> VerificationSubmissionAdapter:
    capability = getattr(value, "capability", None)
    submit = getattr(value, "submit", None)
    if not callable(capability) or not callable(submit):
        message = "verification submission adapter has wrong type"
        raise InvalidAcceleratorResultError(message)
    return cast("VerificationSubmissionAdapter", value)


def _ticket_route(
    capability: AcceleratorCapability,
    ticket: object,
) -> _VerificationRoute:
    if not _valid_ticket(ticket):
        message = "verification submission adapter returned invalid ticket"
        raise InvalidAcceleratorResultError(message)
    admitted = cast("VerificationAssistTicket", ticket)
    return _VerificationRoute(
        preferred_capability=capability,
        preferred_ticket=admitted,
    )


def _valid_ticket(ticket: object) -> bool:
    return callable(getattr(ticket, "close", None)) and callable(
        getattr(ticket, "wait", None)
    )
