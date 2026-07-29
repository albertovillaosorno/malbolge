# File:
#   - test_search_submission.py
# Path:
#   - tests/optimizer/test_search_submission.py
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
#   - Contract evidence for neutral search submission lifetime and fallback.
# - Must-Not:
#   - Create worker threads or treat proposals as accepted candidates.
# - Allows:
#   - Inputs: deterministic fake tickets and the mandatory CPU reference.
#   - Outputs: state, route, cleanup, and exact result assertions.
#   - Side effects: in-memory counters only.
# - Split-When:
#   - Split when a live backend requires independent integration evidence.
# - Merge-When:
#   - Merge when another test owns the same complete search lifetime.
# - Summary:
#   - Hardware-neutral search submission regression tests.
# - Description:
#   - Proves deferred search, validation, fallback, idempotence, and close.
# - Usage:
#   - Collected by the optimizer Python test suite.
# - Defaults:
#   - Optional failures fall back only after ticket cleanup succeeds.
#
# Related documents:
# - accelerator/search_submission.py
#
# Large file:
#   - false
#

"""Hardware-neutral search submission lifetime regressions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from typing import final
from typing import override

import pytest

from accelerator.cpu import CpuSearchExecutionAdapter
from accelerator.cpu.work_ports import CPU_WORK_CAPABILITY
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.search_submission import SearchExecutionTicket
from accelerator.search_submission import SearchSubmissionAdapter
from accelerator.search_submission import SearchSubmissionFallback
from accelerator.search_submission import SearchSubmissionState
from accelerator.search_submission import search_submission_id
from accelerator.search_submission import submit_search
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import SearchResult

ALGORITHM_ID = "deterministic-enumeration-v1"
EXPECTED_SUBMISSION_ID = "validated-search-submission-v1"
REPEATED_WAIT_COUNT = 2
PREFERRED_CAPABILITY = AcceleratorCapability(
    backend_id="test-search-async",
    device_arch="test",
    device_name="test-device",
)


def _request() -> SearchRequest:
    return SearchRequest(
        algorithm_id=ALGORITHM_ID,
        evaluation_budget=2,
        problem=b"problem",
        seed=17,
    )


def _proposals(request: SearchRequest) -> tuple[CandidateProposal, ...]:
    return tuple(
        CandidateProposal(
            logical_id=f"candidate-{index}",
            payload=request.problem + bytes((index,)),
        )
        for index in range(request.evaluation_budget)
    )


def _result(
    request: SearchRequest,
    capability: AcceleratorCapability,
) -> SearchResult:
    return SearchResult(
        algorithm_id=request.algorithm_id,
        capability=capability,
        proposals=_proposals(request),
        seed=request.seed,
    )


@dataclass(slots=True)
class _Counters:
    closes: int = 0
    reference_calls: int = 0
    waits: int = 0


class _Ticket(SearchExecutionTicket):
    _counters: _Counters
    _failure: AcceleratorExecutionError | None
    _result: SearchResult | None

    def __init__(
        self,
        counters: _Counters,
        result: SearchResult | None,
        failure: AcceleratorExecutionError | None = None,
    ) -> None:
        self._counters = counters
        self._failure = failure
        self._result = result

    @override
    def close(self) -> None:
        self._counters.closes += 1

    @override
    def wait(self) -> SearchResult:
        self._counters.waits += 1
        if self._failure is not None:
            raise self._failure
        if self._result is None:
            message = "synthetic search ticket has no result"
            raise AcceleratorExecutionError(message)
        return self._result


@final
class _CloseFailingTicket(_Ticket):
    @override
    def close(self) -> None:
        self._counters.closes += 1
        message = "synthetic search ticket cleanup failure"
        raise AcceleratorExecutionError(message)


@final
class _AsyncAdapter(SearchSubmissionAdapter):
    def __init__(
        self,
        ticket: SearchExecutionTicket | object,
        *,
        submit_failure: bool = False,
    ) -> None:
        self._submit_failure = submit_failure
        self._ticket = ticket

    @override
    def capability(self) -> AcceleratorCapability:
        return PREFERRED_CAPABILITY

    @override
    def submit(self, request: SearchRequest) -> SearchExecutionTicket:
        _ = request.validated()
        if self._submit_failure:
            message = "synthetic search submit failure"
            raise AcceleratorExecutionError(message)
        return cast("SearchExecutionTicket", self._ticket)


@final
class _FailingReference(SearchExecutionAdapter):
    def __init__(self, counters: _Counters) -> None:
        self._counters = counters

    @override
    def capability(self) -> AcceleratorCapability:
        return CPU_WORK_CAPABILITY

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        _ = request.validated()
        self._counters.reference_calls += 1
        message = "synthetic mandatory search failure"
        raise AcceleratorExecutionError(message)


def _reference(counters: _Counters) -> CpuSearchExecutionAdapter:
    def search(request: SearchRequest) -> tuple[CandidateProposal, ...]:
        counters.reference_calls += 1
        return _proposals(request)

    return CpuSearchExecutionAdapter(ALGORITHM_ID, search)


def test_search_submission_identity_is_stable() -> None:
    """Evidence names the exact neutral search lifetime contract."""
    assert search_submission_id() == EXPECTED_SUBMISSION_ID


def test_reference_search_is_deferred_and_wait_is_idempotent() -> None:
    """CPU search starts only at wait and publishes one stable result."""
    counters = _Counters()
    submission = submit_search(_request(), _reference(counters))

    assert submission.status().state is SearchSubmissionState.PENDING
    assert counters.reference_calls == 0
    first = submission.wait()
    second = submission.wait()

    assert first is second
    assert counters.reference_calls == 1
    assert submission.status().actual_capability == CPU_WORK_CAPABILITY
    assert submission.status().state is SearchSubmissionState.COMPLETED


def test_preferred_ticket_publishes_only_after_request_validation() -> None:
    """Optional proposals close before structurally valid publication."""
    request = _request()
    counters = _Counters()
    ticket = _Ticket(counters, _result(request, PREFERRED_CAPABILITY))
    submission = submit_search(
        request,
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    result = submission.wait()

    assert result.capability == PREFERRED_CAPABILITY
    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().actual_capability == PREFERRED_CAPABILITY
    assert submission.status().fallback is None


def test_submit_failure_selects_deferred_reference_search() -> None:
    """Typed submit failure never starts CPU search before explicit wait."""
    counters = _Counters()
    adapter = _AsyncAdapter(object(), submit_failure=True)
    submission = submit_search(_request(), _reference(counters), adapter)

    assert counters.reference_calls == 0
    assert (
        submission.status().fallback is SearchSubmissionFallback.SUBMIT_FAILED
    )
    assert submission.wait().capability == CPU_WORK_CAPABILITY
    assert counters.reference_calls == 1


def test_malformed_ticket_fails_before_unknown_lifetime_can_fallback() -> None:
    """An optional ticket without wait/close cannot enter CPU fallback."""
    counters = _Counters()
    adapter = _AsyncAdapter(object())

    with pytest.raises(
        InvalidAcceleratorResultError,
        match="returned invalid ticket",
    ):
        _ = submit_search(_request(), _reference(counters), adapter)

    assert counters.reference_calls == 0


def test_wait_failure_closes_ticket_before_reference_fallback() -> None:
    """Optional execution failure releases lifetime before CPU search."""
    counters = _Counters()
    failure = AcceleratorExecutionError("synthetic search wait failure")
    ticket = _Ticket(counters, None, failure)
    submission = submit_search(
        _request(),
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    result = submission.wait()

    assert result.capability == CPU_WORK_CAPABILITY
    assert counters == _Counters(closes=1, reference_calls=1, waits=1)
    assert submission.status().fallback is SearchSubmissionFallback.WAIT_FAILED


def test_malformed_result_closes_ticket_and_falls_back() -> None:
    """Changed seed cannot cross publication and selects CPU search."""
    request = _request()
    counters = _Counters()
    malformed = SearchResult(
        algorithm_id=request.algorithm_id,
        capability=PREFERRED_CAPABILITY,
        proposals=(),
        seed=request.seed + 1,
    )
    submission = submit_search(
        request,
        _reference(counters),
        _AsyncAdapter(_Ticket(counters, malformed)),
    )

    result = submission.wait()

    assert result.capability == CPU_WORK_CAPABILITY
    assert counters.closes == 1
    assert (
        submission.status().fallback is SearchSubmissionFallback.RESULT_INVALID
    )


def test_close_before_wait_releases_ticket_and_blocks_search() -> None:
    """Explicit close is idempotent and permanently prevents publication."""
    request = _request()
    counters = _Counters()
    submission = submit_search(
        request,
        _reference(counters),
        _AsyncAdapter(
            _Ticket(counters, _result(request, PREFERRED_CAPABILITY))
        ),
    )

    submission.close()
    submission.close()

    assert counters == _Counters(closes=1)
    assert submission.status().state is SearchSubmissionState.CLOSED
    with pytest.raises(AcceleratorExecutionError, match="submission is closed"):
        _ = submission.wait()


def test_mandatory_failure_is_recorded_and_not_reexecuted() -> None:
    """Mandatory search failure remains failed across repeated waits."""
    counters = _Counters()
    submission = submit_search(_request(), _FailingReference(counters))

    for _ in range(REPEATED_WAIT_COUNT):
        with pytest.raises(
            AcceleratorExecutionError,
            match="mandatory search failure",
        ):
            _ = submission.wait()

    assert counters.reference_calls == 1
    assert submission.status().state is SearchSubmissionState.FAILED


def test_cleanup_failure_blocks_reference_search_fallback() -> None:
    """Unknown optional lifetime prevents CPU search and records failure."""
    counters = _Counters()
    wait_failure = AcceleratorExecutionError("synthetic search wait failure")
    ticket = _CloseFailingTicket(counters, None, wait_failure)
    submission = submit_search(
        _request(),
        _reference(counters),
        _AsyncAdapter(ticket),
    )

    with pytest.raises(
        AcceleratorExecutionError,
        match="ticket cleanup failure",
    ):
        _ = submission.wait()

    assert counters == _Counters(closes=1, waits=1)
    assert submission.status().state is SearchSubmissionState.FAILED
