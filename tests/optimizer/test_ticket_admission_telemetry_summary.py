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
#   - Deterministic offline ticket telemetry summary regressions.
# - Must-Not:
#   - Require CUDA, recommend routes, or treat telemetry as admission evidence.
# - Allows:
#   - Inputs: synthetic validated telemetry documents.
#   - Outputs: exact aggregate, ordering, retention, and failure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when cross-document review gains an independent identity contract.
# - Merge-When:
#   - Merge when another suite owns this exact summary behavior.
# - Summary:
#   - Offline ticket telemetry summary regressions.
# - Description:
#   - Proves summaries remain deterministic, exact, and non-authoritative.
# - Usage:
#   - Runs without accelerator hardware.
# - Defaults:
#   - Invalid documents fail closed and empty documents remain valid.
#

"""Deterministic offline ticket telemetry summary tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionFailureKind
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_summary import (
    TicketAdmissionFailureCount,
)
from accelerator.ticket_admission_telemetry_summary import (
    TicketAdmissionOutcomeSummary,
)
from accelerator.ticket_admission_telemetry_summary import (
    TicketAdmissionTelemetrySummaryError,
)
from accelerator.ticket_admission_telemetry_summary import (
    summarize_ticket_admission_telemetry,
)
from accelerator.ticket_admission_telemetry_summary import (
    ticket_admission_telemetry_summary_id,
)

SUMMARY_ID = "offline-ticket-admission-telemetry-summary-v1"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "exact-test-workload-v1"
PAIR_GROUP_SIZE = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
PRIVATE_DETAIL = "private accelerator detail"
COMPLETED_OBSERVATIONS = 3
COMPLETED_TICKETS = 6
COMPLETED_ELAPSED_NS = 250
COMPLETED_ESTIMATED_NS = 240
COMPLETED_DELTA_NS = 10
FAILED_OBSERVATIONS = 2
FAILED_TICKETS = 4
FAILED_ELAPSED_NS = 200
FAILED_ESTIMATED_NS = 160
FAILED_DELTA_NS = 40
RETENTION_CAPACITY = 2
NEXT_SEQUENCE_ID = 3


def _candidate(
    *,
    backend_id: str,
    benchmark_id: str,
    group_size: int,
    workload_id: str,
) -> TicketRouteCandidate:
    return TicketRouteCandidate(
        backend_id=backend_id,
        benchmark_id=benchmark_id,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=group_size,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=workload_id,
    )


def _report(
    *,
    backend_id: str = "cuda",
    ticket_count: int = PAIR_GROUP_SIZE,
    workload_id: str = WORKLOAD_ID,
) -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=backend_id,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=ticket_count,
        workload_id=workload_id,
    )
    candidate = _candidate(
        backend_id=backend_id,
        benchmark_id=f"{backend_id}-{workload_id}-route-v1",
        group_size=ticket_count,
        workload_id=workload_id,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _attempts(capacity: int = 8) -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=capacity),
        failed=TicketAdmissionFailureTelemetry(capacity=capacity),
    )


def test_empty_document_has_stable_non_authoritative_summary() -> None:
    """An empty explicit document yields stable identity and empty contexts."""
    document = capture_ticket_admission_telemetry_document(_attempts())

    summary = summarize_ticket_admission_telemetry(document)

    assert ticket_admission_telemetry_summary_id() == SUMMARY_ID
    assert summary.summary_id == SUMMARY_ID
    assert summary.document_id == document.document_id
    assert summary.schema_version == document.schema_version
    assert summary.contexts == ()
    assert summary.completed_retention.first_sequence_id is None
    assert summary.failed_retention.first_sequence_id is None


def test_one_context_aggregates_exact_completed_and_failed_counts() -> None:
    """Elapsed, estimate, ticket, chunk, and failure totals remain exact."""
    report = _report()
    attempts = _attempts()
    for elapsed_ns in (70, 80, 100):
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
    _ = attempts.record_failed(
        report,
        elapsed_ns=90,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    _ = attempts.record_failed(
        report,
        elapsed_ns=110,
        error=AcceleratorUnavailableError(PRIVATE_DETAIL),
    )

    context = summarize_ticket_admission_telemetry(
        capture_ticket_admission_telemetry_document(attempts)
    ).contexts[0]

    assert context.completed == TicketAdmissionOutcomeSummary(
        chunk_count=COMPLETED_OBSERVATIONS,
        elapsed_ns=COMPLETED_ELAPSED_NS,
        estimate_delta_ns=COMPLETED_DELTA_NS,
        estimated_ns=COMPLETED_ESTIMATED_NS,
        fallback_ticket_count=0,
        faster_than_estimate_count=1,
        matched_estimate_count=1,
        observation_count=COMPLETED_OBSERVATIONS,
        selected_streamed_ticket_count=0,
        selected_synchronous_ticket_count=COMPLETED_TICKETS,
        slower_than_estimate_count=1,
        ticket_count=COMPLETED_TICKETS,
    )
    assert context.failed == TicketAdmissionOutcomeSummary(
        chunk_count=FAILED_OBSERVATIONS,
        elapsed_ns=FAILED_ELAPSED_NS,
        estimate_delta_ns=FAILED_DELTA_NS,
        estimated_ns=FAILED_ESTIMATED_NS,
        fallback_ticket_count=0,
        faster_than_estimate_count=0,
        matched_estimate_count=0,
        observation_count=FAILED_OBSERVATIONS,
        selected_streamed_ticket_count=0,
        selected_synchronous_ticket_count=FAILED_TICKETS,
        slower_than_estimate_count=FAILED_OBSERVATIONS,
        ticket_count=FAILED_TICKETS,
    )
    assert context.failure_counts == (
        TicketAdmissionFailureCount(
            count=1,
            failure_kind=TicketAdmissionFailureKind.EXECUTION,
        ),
        TicketAdmissionFailureCount(
            count=1,
            failure_kind=TicketAdmissionFailureKind.UNAVAILABLE,
        ),
    )
    assert PRIVATE_DETAIL not in repr(context)


def test_summary_preserves_bounded_retention_ranges() -> None:
    """Dropped counts and retained sequence ranges remain visible offline."""
    report = _report()
    attempts = _attempts(capacity=2)
    for elapsed_ns in (70, 80, 90):
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
        _ = attempts.record_failed(
            report,
            elapsed_ns=elapsed_ns,
            error=AcceleratorExecutionError(PRIVATE_DETAIL),
        )

    summary = summarize_ticket_admission_telemetry(
        capture_ticket_admission_telemetry_document(attempts)
    )

    assert summary.completed_retention.capacity == RETENTION_CAPACITY
    assert summary.completed_retention.dropped_observation_count == 1
    assert summary.completed_retention.first_sequence_id == 1
    assert summary.completed_retention.next_sequence_id == NEXT_SEQUENCE_ID
    retained_count = summary.completed_retention.retained_observation_count
    assert retained_count == RETENTION_CAPACITY
    assert summary.failed_retention == summary.completed_retention


def test_contexts_are_separated_and_sorted_by_exact_identity() -> None:
    """Insertion order cannot change exact-context summary ordering."""
    attempts = _attempts()
    _ = attempts.record_completed(
        _report(backend_id="zeta", workload_id="work-z"),
        elapsed_ns=80,
    )
    _ = attempts.record_completed(
        _report(backend_id="alpha", workload_id="work-a"),
        elapsed_ns=80,
    )
    _ = attempts.record_completed(
        _report(backend_id="alpha", ticket_count=3, workload_id="work-a"),
        elapsed_ns=80,
    )

    contexts = summarize_ticket_admission_telemetry(
        capture_ticket_admission_telemetry_document(attempts)
    ).contexts

    identities = tuple(
        (context.backend_id, context.workload_id, context.ticket_count)
        for context in contexts
    )
    assert identities == (
        ("alpha", "work-a", 2),
        ("alpha", "work-a", 3),
        ("zeta", "work-z", 2),
    )


def test_evidence_appearances_are_sorted_and_outcome_specific() -> None:
    """Selected evidence appearances retain completed and failed counts."""
    backend_id = "cuda"
    workload_id = "multi-route-workload-v1"
    request = TicketAdmissionRequest(
        backend_id=backend_id,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=5,
        workload_id=workload_id,
    )
    candidates = (
        _candidate(
            backend_id=backend_id,
            benchmark_id="z-route-v1",
            group_size=2,
            workload_id=workload_id,
        ),
        _candidate(
            backend_id=backend_id,
            benchmark_id="a-route-v1",
            group_size=3,
            workload_id=workload_id,
        ),
    )
    report = plan_ticket_submissions_with_report(
        request,
        candidates=candidates,
        fallback_ticket_ns=100,
    )
    attempts = _attempts()
    _ = attempts.record_completed(report, elapsed_ns=160)
    _ = attempts.record_failed(
        report,
        elapsed_ns=170,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    document = capture_ticket_admission_telemetry_document(attempts)
    selected = document.completed.observations[0].selected_evidence_ids

    appearances = (
        summarize_ticket_admission_telemetry(document)
        .contexts[0]
        .evidence_appearances
    )

    assert tuple(item.evidence_id for item in appearances) == tuple(
        sorted(selected)
    )
    assert all(item.completed_observation_count == 1 for item in appearances)
    assert all(item.failed_observation_count == 1 for item in appearances)


def test_repeated_summary_is_deterministic_and_does_not_mutate_source() -> None:
    """Review is pure and repeated calls return equal immutable values."""
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=75)
    document = capture_ticket_admission_telemetry_document(attempts)

    first = summarize_ticket_admission_telemetry(document)
    second = summarize_ticket_admission_telemetry(document)

    assert first == second
    assert document == capture_ticket_admission_telemetry_document(attempts)


def test_invalid_typed_document_fails_before_aggregation() -> None:
    """Summary construction reuses strict persistence validation."""
    document = capture_ticket_admission_telemetry_document(_attempts())

    with pytest.raises(
        TicketAdmissionTelemetrySummaryError,
        match="document schema is unsupported",
    ):
        _ = summarize_ticket_admission_telemetry(
            replace(document, schema_version=True)
        )
