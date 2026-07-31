# File:
#   - test_ticket_admission_telemetry_overlap_index.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_overlap_index.py
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
#   - Bounded collection-wide telemetry overlap index regressions.
# - Must-Not:
#   - Require CUDA, infer lineage, merge snapshots, or modify admission.
# - Allows:
#   - Inputs: synthetic telemetry documents and explicit index limits.
#   - Outputs: pair ordering, classification, deduplication, and limit
#     assertions.
#   - Side effects: temporary monkeypatching of the local pair comparator.
# - Split-When:
#   - Split when asymmetric lineage or recommendations gain a protocol.
# - Merge-When:
#   - Merge when another suite owns this exact all-pairs index behavior.
# - Summary:
#   - Collection-wide telemetry overlap index regressions.
# - Description:
#   - Proves unique canonical pairs are compared within an explicit budget.
# - Usage:
#   - Runs without accelerator hardware or filesystem access.
# - Defaults:
#   - Empty and singleton collections are valid; invalid bounds fail closed.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_overlap_index.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
#
# Large file:
#   - false
#

"""Bounded collection-wide telemetry overlap index tests."""

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
from accelerator.ticket_admission_telemetry_overlap import (
    TicketAdmissionTelemetryOverlapKind,
)
from accelerator.ticket_admission_telemetry_overlap import (
    compare_ticket_admission_telemetry_documents,
)
import accelerator.ticket_admission_telemetry_overlap_index as index_module
from accelerator.ticket_admission_telemetry_overlap_index import (
    DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    TicketAdmissionTelemetryOverlapClassificationSummary,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    TicketAdmissionTelemetryOverlapIndexError,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    index_ticket_admission_telemetry_overlap,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    ticket_admission_telemetry_overlap_index_id,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

INDEX_ID = "offline-ticket-admission-telemetry-overlap-index-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "overlap-index-test-workload-v1"
BENCHMARK_ID = "overlap-index-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
PRIVATE_DETAIL = "private accelerator detail"
LOW_ELAPSED_NS = 70
MATCH_ELAPSED_NS = 80
HIGH_ELAPSED_NS = 90
PAIR_COUNT = 3
DUPLICATE_INPUT_COUNT = 3
DUPLICATE_DOCUMENT_COUNT = 2


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


def _completed_document(elapsed_ns: int) -> TicketAdmissionTelemetryDocument:
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return _capture(attempts)


def _zero_classifications() -> (
    TicketAdmissionTelemetryOverlapClassificationSummary
):
    return TicketAdmissionTelemetryOverlapClassificationSummary(
        conflicting_pair_count=0,
        matching_pair_count=0,
        no_overlap_pair_count=0,
        no_retained_observations_pair_count=0,
    )


def test_empty_index_has_stable_identity_and_zero_counts() -> None:
    """An empty explicit collection yields no pairs or classifications."""
    index = index_ticket_admission_telemetry_overlap(())

    assert ticket_admission_telemetry_overlap_index_id() == INDEX_ID
    assert index.index_id == INDEX_ID
    assert index.pair_limit == DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS
    assert index.pair_count == 0
    assert index.pairs == ()
    assert index.completed_classifications == _zero_classifications()
    assert index.failed_classifications == _zero_classifications()
    assert index.collection.input_document_count == 0


def test_exact_duplicates_do_not_create_pairs() -> None:
    """Byte-identical inputs remain occurrences, not pair vertices."""
    document = _completed_document(LOW_ELAPSED_NS)

    index = index_ticket_admission_telemetry_overlap(
        (document, document, document)
    )

    assert index.collection.input_document_count == DUPLICATE_INPUT_COUNT
    assert index.collection.duplicate_document_count == (
        DUPLICATE_DOCUMENT_COUNT
    )
    assert len(index.collection.unique_documents) == 1
    assert index.pair_count == 0
    assert index.pairs == ()


def test_pair_order_is_deterministic_across_input_permutations() -> None:
    """Fingerprint ordering makes pair output input-order independent."""
    documents = (
        _completed_document(LOW_ELAPSED_NS),
        _completed_document(MATCH_ELAPSED_NS),
        _completed_document(HIGH_ELAPSED_NS),
    )

    forward = index_ticket_admission_telemetry_overlap(documents)
    reverse = index_ticket_admission_telemetry_overlap(
        tuple(reversed(documents))
    )

    assert forward == reverse
    assert forward.pair_count == PAIR_COUNT
    identities = tuple(
        (
            pair.first_document_fingerprint,
            pair.second_document_fingerprint,
        )
        for pair in forward.pairs
    )
    assert identities == tuple(sorted(identities))
    assert all(first < second for first, second in identities)


def test_classification_counts_cover_every_unique_pair() -> None:
    """Matching and conflicting completed pairs are counted exactly once."""
    report = _report()
    successive = _attempts()
    _ = successive.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = successive.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    first = _capture(successive)
    _ = successive.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    second = _capture(successive)

    independent = _attempts()
    _ = independent.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = independent.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    third = _capture(independent)

    index = index_ticket_admission_telemetry_overlap((first, second, third))

    assert index.pair_count == PAIR_COUNT
    assert index.completed_classifications == (
        TicketAdmissionTelemetryOverlapClassificationSummary(
            conflicting_pair_count=2,
            matching_pair_count=1,
            no_overlap_pair_count=0,
            no_retained_observations_pair_count=0,
        )
    )
    assert index.failed_classifications == (
        TicketAdmissionTelemetryOverlapClassificationSummary(
            conflicting_pair_count=0,
            matching_pair_count=0,
            no_overlap_pair_count=0,
            no_retained_observations_pair_count=PAIR_COUNT,
        )
    )


def test_no_overlap_and_failed_matching_counts_are_independent() -> None:
    """Completed and failed classifications retain separate pair totals."""
    report = _report()
    attempts = _attempts(capacity=1)
    _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = attempts.record_failed(
        report,
        elapsed_ns=LOW_ELAPSED_NS,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    first = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    _ = attempts.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    second = _capture(attempts)

    index = index_ticket_admission_telemetry_overlap((first, second))

    assert index.completed_classifications.no_overlap_pair_count == 1
    assert index.completed_classifications.matching_pair_count == 0
    assert index.failed_classifications.matching_pair_count == 1
    assert index.failed_classifications.no_overlap_pair_count == 0


def test_single_pair_matches_direct_pairwise_report() -> None:
    """The all-pairs index reuses the exact pairwise comparison contract."""
    first = _completed_document(LOW_ELAPSED_NS)
    second = _completed_document(HIGH_ELAPSED_NS)

    index = index_ticket_admission_telemetry_overlap((first, second))

    assert index.pair_count == 1
    assert index.pairs == (
        compare_ticket_admission_telemetry_documents(first, second),
    )
    assert index.pairs[0].completed.overlap_kind == (
        TicketAdmissionTelemetryOverlapKind.CONFLICTING
    )


@pytest.mark.parametrize("max_pairs", [0, True])
def test_invalid_pair_limits_fail_closed(max_pairs: int) -> None:
    """Zero and boolean limits cannot bypass the pair budget."""
    with pytest.raises(
        TicketAdmissionTelemetryOverlapIndexError,
        match="pair limit must be a positive integer",
    ):
        _ = index_ticket_admission_telemetry_overlap((), max_pairs=max_pairs)


def _unexpected_compare(first: object, second: object) -> object:
    _ = (first, second)
    message = "pair comparison ran after the pair budget failed"
    raise AssertionError(message)


def test_pair_limit_is_checked_before_pair_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized unique pair set fails before quadratic comparison work."""
    documents = (
        _completed_document(LOW_ELAPSED_NS),
        _completed_document(MATCH_ELAPSED_NS),
        _completed_document(HIGH_ELAPSED_NS),
    )
    monkeypatch.setattr(
        index_module,
        "compare_ticket_admission_telemetry_documents",
        _unexpected_compare,
    )

    with pytest.raises(
        TicketAdmissionTelemetryOverlapIndexError,
        match="unique document pairs exceed configured limit",
    ):
        _ = index_ticket_admission_telemetry_overlap(
            documents,
            max_pairs=2,
        )


def test_collection_document_limit_is_forwarded() -> None:
    """The index preserves the collection's explicit document bound."""
    documents = (
        _completed_document(LOW_ELAPSED_NS),
        _completed_document(HIGH_ELAPSED_NS),
    )

    with pytest.raises(
        TicketAdmissionTelemetryOverlapIndexError,
        match="document count exceeds configured limit",
    ):
        _ = index_ticket_admission_telemetry_overlap(
            documents,
            max_documents=1,
        )


def test_collection_byte_limit_is_forwarded() -> None:
    """Canonical collection bytes remain bounded before pair indexing."""
    document = _completed_document(LOW_ELAPSED_NS)
    canonical_byte_count = len(
        encode_ticket_admission_telemetry_document(document)
    )

    with pytest.raises(
        TicketAdmissionTelemetryOverlapIndexError,
        match="canonical input exceeds configured byte limit",
    ):
        _ = index_ticket_admission_telemetry_overlap(
            (document,),
            max_total_bytes=canonical_byte_count - 1,
        )


def test_invalid_typed_document_fails_before_indexing() -> None:
    """A forged schema cannot become an index vertex."""
    document = _completed_document(LOW_ELAPSED_NS)
    malformed = replace(document, schema_version=True)

    with pytest.raises(
        TicketAdmissionTelemetryOverlapIndexError,
        match="document schema is unsupported",
    ):
        _ = index_ticket_admission_telemetry_overlap(
            (malformed, document),
        )
