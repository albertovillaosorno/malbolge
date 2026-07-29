# File:
#   - search_submission.py
# Path:
#   - accelerator/search_submission.py
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
#   - Hardware-neutral lifetime and publication for search submissions.
# - Must-Not:
#   - Create hidden workers, expose device handles, or accept proposals.
# - Allows:
#   - Inputs: one exact search request plus reference/optional adapters.
#   - Outputs: one structurally validated untrusted search result.
#   - Side effects: backend work owned until explicit wait or close.
# - Split-When:
#   - Split when verification-assist submission gains a distinct contract.
# - Merge-When:
#   - Merge when another neutral port owns identical search lifetime.
# - Summary:
#   - Validated hardware-neutral search submission lifetime.
# - Description:
#   - Defers proposal publication and CPU fallback until explicit wait.
# - Usage:
#   - Submit search, inspect status, then wait or close.
# - Defaults:
#   - CPU search is deferred; optional cleanup precedes any fallback.
#
# Related documents:
# - docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md
# - docs/technical/adr/verification-trust-boundary.md
#
# Large file:
#   - false
#

"""Hardware-neutral asynchronous search submission lifetime."""

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
    from accelerator.work_ports import SearchExecutionAdapter
    from accelerator.work_ports import SearchRequest
    from accelerator.work_ports import SearchResult

SEARCH_SUBMISSION_ID = "validated-search-submission-v1"


class SearchSubmissionState(StrEnum):
    """Observable lifetime state for one neutral search submission."""

    PENDING = "pending"
    COMPLETED = "completed"
    CLOSED = "closed"
    FAILED = "failed"


class SearchSubmissionFallback(StrEnum):
    """Stable reason that optional search selected the CPU reference."""

    RESULT_INVALID = "preferred-result-invalid"
    SUBMIT_FAILED = "preferred-submit-failed"
    WAIT_FAILED = "preferred-wait-failed"


@dataclass(frozen=True, slots=True)
class SearchSubmissionStatus:
    """Observable configured/actual route and search submission state."""

    actual_capability: AcceleratorCapability | None
    fallback: SearchSubmissionFallback | None
    preferred_capability: AcceleratorCapability | None
    state: SearchSubmissionState


class SearchExecutionTicket(Protocol):
    """Backend-owned search ticket with explicit wait and cleanup."""

    def close(self) -> None:
        """Release pending or completed backend resources."""
        ...

    def wait(self) -> SearchResult:
        """Complete backend work and return untrusted proposals."""
        ...


@dataclass(frozen=True, slots=True)
class _SearchRoute:
    fallback: SearchSubmissionFallback | None = None
    preferred_capability: AcceleratorCapability | None = None
    preferred_ticket: SearchExecutionTicket | None = None


class SearchSubmissionAdapter(Protocol):
    """Replaceable adapter capable of deferred search submission."""

    def capability(self) -> AcceleratorCapability:
        """Return stable configured backend identity."""
        ...

    def submit(self, request: SearchRequest) -> SearchExecutionTicket:
        """Submit search without publishing proposals."""
        ...


@final
class SearchExecutionSubmission:
    """Neutral search submission that validates publication and fallback."""

    __slots__ = (
        "_actual_capability",
        "_failure",
        "_fallback",
        "_preferred_capability",
        "_preferred_ticket",
        "_reference",
        "_request",
        "_result",
        "_state",
    )

    def __init__(
        self,
        request: SearchRequest,
        reference: SearchExecutionAdapter,
        route: _SearchRoute,
    ) -> None:
        """Bind one exact request to optional and mandatory execution routes."""
        self._actual_capability: AcceleratorCapability | None = None
        self._failure: AcceleratorError | None = None
        self._fallback = route.fallback
        self._preferred_capability = route.preferred_capability
        self._preferred_ticket = route.preferred_ticket
        self._reference = reference
        self._request = request
        self._result: SearchResult | None = None
        self._state = SearchSubmissionState.PENDING

    def close(self) -> None:
        """Close pending search and permanently reject later wait.

        Raises:
            AcceleratorError: If backend cleanup fails.

        """
        if self._state in {
            SearchSubmissionState.CLOSED,
            SearchSubmissionState.COMPLETED,
        }:
            return
        if self._state is SearchSubmissionState.FAILED:
            self._raise_failure()
        ticket = self._preferred_ticket
        if ticket is not None:
            try:
                ticket.close()
            except AcceleratorError as error:
                self._record_failure(error)
                raise
            self._preferred_ticket = None
        self._state = SearchSubmissionState.CLOSED

    def status(self) -> SearchSubmissionStatus:
        """Return immutable route and lifetime evidence.

        Returns:
            Current configured route, actual route, fallback, and state.

        """
        return SearchSubmissionStatus(
            actual_capability=self._actual_capability,
            fallback=self._fallback,
            preferred_capability=self._preferred_capability,
            state=self._state,
        )

    def wait(self) -> SearchResult:
        """Publish validated proposals or execute exact CPU fallback.

        Returns:
            Structurally valid untrusted proposals from one exact route.

        Raises:
            AcceleratorExecutionError: If closed or execution cannot complete.

        """
        if self._state is SearchSubmissionState.COMPLETED:
            return self._completed_result()
        if self._state is SearchSubmissionState.CLOSED:
            message = "search execution submission is closed"
            raise AcceleratorExecutionError(message)
        if self._state is SearchSubmissionState.FAILED:
            self._raise_failure()
        preferred = self._wait_preferred()
        if preferred is not None:
            return preferred
        return self._wait_reference()

    def _completed_result(self) -> SearchResult:
        result = self._result
        if result is None:
            message = "completed search submission has no result"
            raise AcceleratorExecutionError(message)
        return result

    def _publish(
        self,
        result: SearchResult,
        capability: AcceleratorCapability,
    ) -> SearchResult:
        self._actual_capability = capability
        self._result = result
        self._state = SearchSubmissionState.COMPLETED
        return result

    def _record_failure(self, error: AcceleratorError) -> None:
        self._failure = error
        self._state = SearchSubmissionState.FAILED

    def _raise_failure(self) -> None:
        failure = self._failure
        if failure is None:
            message = "failed search submission has no failure"
            raise AcceleratorExecutionError(message)
        raise failure

    def _wait_preferred(self) -> SearchResult | None:
        ticket = self._preferred_ticket
        capability = self._preferred_capability
        if ticket is None or capability is None:
            return None
        try:
            result = ticket.wait().validated_against(
                self._request,
                capability,
            )
        except InvalidAcceleratorResultError:
            self._fallback = SearchSubmissionFallback.RESULT_INVALID
        except AcceleratorError:
            self._fallback = SearchSubmissionFallback.WAIT_FAILED
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

    def _wait_reference(self) -> SearchResult:
        capability = self._reference.capability()
        try:
            result = self._reference.search(self._request)
            validated = result.validated_against(
                self._request,
                capability,
            )
        except AcceleratorError as error:
            self._record_failure(error)
            raise
        return self._publish(validated, capability)


def search_submission_id() -> str:
    """Return the stable neutral search-submission contract identity.

    Returns:
        Versioned identity used by retained evidence and diagnostics.

    """
    return SEARCH_SUBMISSION_ID


def submit_search(
    request: SearchRequest,
    reference: SearchExecutionAdapter,
    preferred: SearchSubmissionAdapter | None = None,
) -> SearchExecutionSubmission:
    """Submit optional search or retain an exact deferred CPU fallback.

    Returns:
        Neutral submission that owns validation, cleanup, and fallback.

    """
    validated = request.validated()
    route = _preferred_route(validated, preferred)
    return SearchExecutionSubmission(validated, reference, route)


def _preferred_route(
    request: SearchRequest,
    preferred: SearchSubmissionAdapter | None,
) -> _SearchRoute:
    route = _SearchRoute()
    if preferred is not None:
        try:
            capability = preferred.capability()
            ticket = preferred.submit(request)
        except InvalidAcceleratorResultError:
            raise
        except AcceleratorError:
            route = _SearchRoute(
                fallback=SearchSubmissionFallback.SUBMIT_FAILED,
            )
        else:
            route = _ticket_route(capability, ticket)
    return route


def _ticket_route(
    capability: AcceleratorCapability,
    ticket: object,
) -> _SearchRoute:
    if not _valid_ticket(ticket):
        message = "search submission adapter returned invalid ticket"
        raise InvalidAcceleratorResultError(message)
    admitted = cast("SearchExecutionTicket", ticket)
    return _SearchRoute(
        preferred_capability=capability,
        preferred_ticket=admitted,
    )


def _valid_ticket(ticket: object) -> bool:
    return callable(getattr(ticket, "close", None)) and callable(
        getattr(ticket, "wait", None)
    )
