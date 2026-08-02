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
#   - Exact pairwise retained telemetry overlap regressions.
# - Must-Not:
#   - Require CUDA, infer lineage, merge snapshots, or modify admission.
# - Allows:
#   - Inputs: synthetic validated telemetry documents.
#   - Outputs: symmetric range, match, conflict, and collision assertions.
#   - Side effects: temporary monkeypatching of the local digest constructor.
# - Split-When:
#   - Split when asymmetric lineage or recommendations gain a protocol.
# - Merge-When:
#   - Merge when another suite owns this exact pairwise comparison behavior.
# - Summary:
#   - Pairwise telemetry overlap regressions.
# - Description:
#   - Proves retained overlap is exact without becoming lineage evidence.
# - Usage:
#   - Runs without accelerator hardware or filesystem access.
# - Defaults:
#   - Invalid or ambiguous documents fail closed.
#

"""Exact pairwise retained telemetry overlap tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
import accelerator.ticket_admission_telemetry_overlap as overlap_module
from accelerator.ticket_admission_telemetry_overlap import (
    TicketAdmissionTelemetryOverlapError,
)
from accelerator.ticket_admission_telemetry_overlap import (
    TicketAdmissionTelemetryOverlapKind,
)
from accelerator.ticket_admission_telemetry_overlap import (
    compare_ticket_admission_telemetry_documents,
)
from accelerator.ticket_admission_telemetry_overlap import (
    ticket_admission_telemetry_overlap_id,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

OVERLAP_ID = "offline-ticket-admission-telemetry-overlap-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "overlap-test-workload-v1"
BENCHMARK_ID = "overlap-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
PRIVATE_DETAIL = "private accelerator detail"
LOW_ELAPSED_NS = 70
MATCH_ELAPSED_NS = 80
HIGH_ELAPSED_NS = 90
PAIR_COUNT = 2


def _report() -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=TICKET_COUNT,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=TICKET_COUNT,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _attempts(capacity: int = 2) -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=capacity),
        failed=TicketAdmissionFailureTelemetry(capacity=capacity),
    )


def _capture(
    attempts: TicketAdmissionAttemptTelemetry,
) -> TicketAdmissionTelemetryDocument:
    return capture_ticket_admission_telemetry_document(attempts)


def test_identical_empty_documents_have_stable_overlap_identity() -> None:
    """Identical empty documents report exact equality and empty streams."""
    document = _capture(_attempts())

    overlap = compare_ticket_admission_telemetry_documents(document, document)

    assert ticket_admission_telemetry_overlap_id() == OVERLAP_ID
    assert overlap.overlap_id == OVERLAP_ID
    assert overlap.exact_document_match
    assert overlap.first_document_fingerprint == (
        overlap.second_document_fingerprint
    )
    assert overlap.completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.NO_RETAINED_OBSERVATIONS
    )
    assert overlap.failed == overlap.completed


def test_matching_successive_snapshots_report_exact_retained_overlap() -> None:
    """A later bounded snapshot can share exact retained observations."""
    report = _report()
    attempts = _attempts()
    _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = attempts.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    first = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    second = _capture(attempts)

    overlap = compare_ticket_admission_telemetry_documents(first, second)

    assert overlap == compare_ticket_admission_telemetry_documents(
        second,
        first,
    )
    assert not overlap.exact_document_match
    assert overlap.completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.MATCHING
    )
    assert overlap.completed.overlap_sequence_start == 1
    assert overlap.completed.overlap_sequence_stop == PAIR_COUNT
    assert overlap.completed.overlapping_observation_count == 1
    assert overlap.completed.matching_observation_count == 1
    assert overlap.completed.conflicting_sequence_ids == ()
    ranges = {
        (
            overlap.completed.first_sequence_start,
            overlap.completed.first_sequence_stop,
        ),
        (
            overlap.completed.second_sequence_start,
            overlap.completed.second_sequence_stop,
        ),
    }
    assert ranges == {(0, PAIR_COUNT), (1, 3)}


def test_partial_overlap_reports_matching_and_conflicting_sequences() -> None:
    """Equal sequence zero and divergent sequence one remain distinguishable."""
    report = _report()
    first_attempts = _attempts()
    second_attempts = _attempts()
    for attempts, elapsed_values in (
        (first_attempts, (LOW_ELAPSED_NS, MATCH_ELAPSED_NS)),
        (second_attempts, (LOW_ELAPSED_NS, HIGH_ELAPSED_NS)),
    ):
        for elapsed_ns in elapsed_values:
            _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)

    overlap = compare_ticket_admission_telemetry_documents(
        _capture(first_attempts),
        _capture(second_attempts),
    )

    assert overlap.completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.CONFLICTING
    )
    assert overlap.completed.overlap_sequence_start == 0
    assert overlap.completed.overlap_sequence_stop == PAIR_COUNT
    assert overlap.completed.overlapping_observation_count == PAIR_COUNT
    assert overlap.completed.matching_observation_count == 1
    assert overlap.completed.conflicting_sequence_ids == (1,)


def test_nonoverlapping_retained_ranges_do_not_imply_lineage() -> None:
    """Disjoint ranges report no overlap from one recorder."""
    report = _report()
    attempts = _attempts(capacity=1)
    _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    first = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    _ = attempts.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    second = _capture(attempts)

    overlap = compare_ticket_admission_telemetry_documents(first, second)

    assert overlap.completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.NO_OVERLAP
    )
    assert overlap.completed.overlap_sequence_start is None
    assert overlap.completed.overlap_sequence_stop is None
    assert overlap.completed.overlapping_observation_count == 0
    assert overlap.completed.conflicting_sequence_ids == ()
    ranges = {
        (
            overlap.completed.first_sequence_start,
            overlap.completed.first_sequence_stop,
        ),
        (
            overlap.completed.second_sequence_start,
            overlap.completed.second_sequence_stop,
        ),
    }
    assert ranges == {(0, 1), (PAIR_COUNT, 3)}


def test_matching_overlap_preserves_capacity_mismatch() -> None:
    """Equal retained data does not erase a capacity mismatch."""
    report = _report()
    first_attempts = _attempts(capacity=1)
    second_attempts = _attempts(capacity=PAIR_COUNT)
    _ = first_attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = second_attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)

    overlap = compare_ticket_admission_telemetry_documents(
        _capture(first_attempts),
        _capture(second_attempts),
    )

    assert overlap.completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.MATCHING
    )
    assert not overlap.completed.capacities_equal
    assert {
        overlap.completed.first_capacity,
        overlap.completed.second_capacity,
    } == {1, PAIR_COUNT}
    assert overlap.completed.matching_observation_count == 1
    assert not overlap.exact_document_match


def test_failed_fifo_reports_matching_overlap_without_error_text() -> None:
    """Stable failures overlap exactly without private messages."""
    report = _report()
    attempts = _attempts()
    _ = attempts.record_failed(
        report,
        elapsed_ns=LOW_ELAPSED_NS,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    _ = attempts.record_failed(
        report,
        elapsed_ns=MATCH_ELAPSED_NS,
        error=AcceleratorUnavailableError(PRIVATE_DETAIL),
    )
    first = _capture(attempts)
    _ = attempts.record_failed(
        report,
        elapsed_ns=HIGH_ELAPSED_NS,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    second = _capture(attempts)

    overlap = compare_ticket_admission_telemetry_documents(first, second)

    assert overlap.failed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.MATCHING
    )
    assert overlap.failed.overlap_sequence_start == 1
    assert overlap.failed.overlap_sequence_stop == PAIR_COUNT
    assert overlap.failed.matching_observation_count == 1
    assert PRIVATE_DETAIL not in repr(overlap)


def test_invalid_typed_document_fails_before_overlap() -> None:
    """A forged schema cannot acquire an overlap report."""
    document = _capture(_attempts())
    malformed = replace(document, schema_version=True)

    with pytest.raises(
        TicketAdmissionTelemetryOverlapError,
        match="document schema is unsupported",
    ):
        _ = compare_ticket_admission_telemetry_documents(
            malformed,
            document,
        )


class _ConstantDigest:
    @staticmethod
    def hexdigest() -> str:
        """Return one deterministic forged digest.

        Returns:
            A fixed 64-character hexadecimal string.

        """
        return "0" * 64


def _constant_sha256(payload: bytes) -> _ConstantDigest:
    _ = payload
    return _ConstantDigest()


def test_digest_collision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct canonical documents may never share one overlap identity."""
    monkeypatch.setattr(overlap_module, "sha256", _constant_sha256)
    report = _report()
    first_attempts = _attempts()
    second_attempts = _attempts()
    _ = first_attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = second_attempts.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)

    with pytest.raises(
        TicketAdmissionTelemetryOverlapError,
        match="document fingerprint collision detected",
    ):
        _ = compare_ticket_admission_telemetry_documents(
            _capture(first_attempts),
            _capture(second_attempts),
        )
