# File:
#   - test_ticket_admission_telemetry_collection.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_collection.py
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
#   - Byte-exact telemetry collection identity and deduplication regressions.
# - Must-Not:
#   - Require CUDA, merge snapshots, recommend routes, or modify admission.
# - Allows:
#   - Inputs: synthetic telemetry documents and bounded immutable collections.
#   - Outputs: fingerprint, ordering, duplicate, limit, and collision
#     assertions.
#   - Side effects: temporary monkeypatching of the local digest constructor.
# - Split-When:
#   - Split when overlap graph components gain an evidence protocol.
# - Merge-When:
#   - Merge when another suite owns this exact collection identity behavior.
# - Summary:
#   - Exact telemetry document collection regressions.
# - Description:
#   - Proves only byte-identical canonical documents are deduplicated.
# - Usage:
#   - Runs without accelerator hardware or filesystem access.
# - Defaults:
#   - Empty collections are valid and malformed or ambiguous input fails closed.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_overlap.py
# - accelerator/ticket_admission_telemetry_overlap_index.py
#
# Large file:
#   - false
#

"""Byte-exact telemetry document collection tests."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import TYPE_CHECKING
from typing import cast

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
import accelerator.ticket_admission_telemetry_collection as collection_module
from accelerator.ticket_admission_telemetry_collection import (
    TicketAdmissionTelemetryCollectionError,
)
from accelerator.ticket_admission_telemetry_collection import (
    collect_ticket_admission_telemetry,
)
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_collection_id,
)
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

COLLECTION_ID = "offline-ticket-admission-telemetry-collection-v1"
FINGERPRINT_PREFIX = "ticket-admission-telemetry-document-v1:sha256:"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "collection-test-workload-v1"
BENCHMARK_ID = "collection-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
PRIVATE_DETAIL = "private accelerator detail"
DOCUMENT_PAIR_COUNT = 2
DUPLICATE_INPUT_COUNT = 3
DUPLICATE_COUNT = 2
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90


def _report(*, workload_id: str = WORKLOAD_ID) -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=TICKET_COUNT,
        workload_id=workload_id,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=f"{BENCHMARK_ID}-{workload_id}",
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=TICKET_COUNT,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=workload_id,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _document(
    *,
    elapsed_ns: int = CANDIDATE_NS,
    workload_id: str = WORKLOAD_ID,
    failed: bool = False,
) -> TicketAdmissionTelemetryDocument:
    attempts = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=4),
        failed=TicketAdmissionFailureTelemetry(capacity=4),
    )
    report = _report(workload_id=workload_id)
    if failed:
        _ = attempts.record_failed(
            report,
            elapsed_ns=elapsed_ns,
            error=AcceleratorExecutionError(PRIVATE_DETAIL),
        )
    else:
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def test_empty_collection_has_stable_identity() -> None:
    """No explicit documents yields one stable empty immutable collection."""
    collection = collect_ticket_admission_telemetry(())

    assert ticket_admission_telemetry_collection_id() == COLLECTION_ID
    assert collection.collection_id == COLLECTION_ID
    assert collection.input_document_count == 0
    assert collection.duplicate_document_count == 0
    assert collection.input_canonical_byte_count == 0
    assert collection.unique_canonical_byte_count == 0
    assert collection.duplicate_canonical_byte_count == 0
    assert collection.unique_documents == ()


def test_document_fingerprint_hashes_exact_canonical_bytes() -> None:
    """The self-describing identity hashes the persistence encoding exactly."""
    document = _document(failed=True)
    canonical = encode_ticket_admission_telemetry_document(document)

    fingerprint = ticket_admission_telemetry_document_fingerprint(document)

    assert fingerprint == f"{FINGERPRINT_PREFIX}{sha256(canonical).hexdigest()}"
    assert PRIVATE_DETAIL not in fingerprint


def test_exact_duplicates_are_counted_once() -> None:
    """Byte-identical documents retain one summary and occurrence count."""
    document = _document()

    collection = collect_ticket_admission_telemetry(
        (document, document, document)
    )

    canonical_byte_count = len(
        encode_ticket_admission_telemetry_document(document)
    )
    assert collection.input_document_count == DUPLICATE_INPUT_COUNT
    assert collection.duplicate_document_count == DUPLICATE_COUNT
    assert collection.input_canonical_byte_count == (
        canonical_byte_count * DUPLICATE_INPUT_COUNT
    )
    assert collection.unique_canonical_byte_count == canonical_byte_count
    assert collection.duplicate_canonical_byte_count == (
        canonical_byte_count * DUPLICATE_COUNT
    )
    assert len(collection.unique_documents) == 1
    entry = collection.unique_documents[0]
    assert entry.occurrence_count == DUPLICATE_INPUT_COUNT
    assert entry.canonical_byte_count == canonical_byte_count
    assert entry.summary.contexts[0].completed.observation_count == 1


def test_unique_documents_are_sorted_and_order_independent() -> None:
    """Input permutation cannot change unique fingerprint-ordered entries."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS, workload_id="work-z")
    second = _document(elapsed_ns=HIGH_ELAPSED_NS, workload_id="work-a")

    forward = collect_ticket_admission_telemetry((first, second))
    reverse = collect_ticket_admission_telemetry((second, first))

    assert forward == reverse
    fingerprints = tuple(
        entry.document_fingerprint for entry in forward.unique_documents
    )
    assert fingerprints == tuple(sorted(fingerprints))


def test_distinct_snapshots_are_not_merged_even_with_same_context() -> None:
    """Distinct documents retain separate same-context summaries."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)

    collection = collect_ticket_admission_telemetry((first, second))

    assert collection.input_document_count == DOCUMENT_PAIR_COUNT
    assert collection.duplicate_document_count == 0
    assert collection.duplicate_canonical_byte_count == 0
    assert collection.input_canonical_byte_count == (
        collection.unique_canonical_byte_count
    )
    assert len(collection.unique_documents) == DOCUMENT_PAIR_COUNT
    observed_elapsed = tuple(
        entry.summary.contexts[0].completed.elapsed_ns
        for entry in collection.unique_documents
    )
    assert tuple(sorted(observed_elapsed)) == (
        LOW_ELAPSED_NS,
        HIGH_ELAPSED_NS,
    )
    assert all(
        entry.summary.contexts[0].completed.observation_count == 1
        for entry in collection.unique_documents
    )


def _mutable_document_sequence() -> object:
    return [_document()]


def test_collection_rejects_mutable_document_sequences() -> None:
    """A list cannot silently become the immutable collection input contract."""
    invalid_source = _mutable_document_sequence()
    invalid = cast(
        "tuple[TicketAdmissionTelemetryDocument, ...]",
        invalid_source,
    )
    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="documents must be an immutable tuple",
    ):
        _ = collect_ticket_admission_telemetry(invalid)


@pytest.mark.parametrize("max_documents", [0, True])
def test_collection_rejects_invalid_document_limits(
    max_documents: int,
) -> None:
    """Zero and boolean document limits never bypass collection bounds."""
    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="document limit must be a positive integer",
    ):
        _ = collect_ticket_admission_telemetry(
            (),
            max_documents=max_documents,
        )


@pytest.mark.parametrize("max_total_bytes", [0, True])
def test_collection_rejects_invalid_byte_limits(
    max_total_bytes: int,
) -> None:
    """Zero and boolean byte limits never bypass collection bounds."""
    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="byte limit must be a positive integer",
    ):
        _ = collect_ticket_admission_telemetry(
            (),
            max_total_bytes=max_total_bytes,
        )


def test_collection_enforces_canonical_byte_limit() -> None:
    """Canonical input bytes are bounded before collection publication."""
    document = _document()
    canonical_byte_count = len(
        encode_ticket_admission_telemetry_document(document)
    )

    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="canonical input exceeds configured byte limit",
    ):
        _ = collect_ticket_admission_telemetry(
            (document,),
            max_total_bytes=canonical_byte_count - 1,
        )


def test_collection_enforces_document_count_limit() -> None:
    """The document tuple is bounded before hashing or summarization."""
    documents = (
        _document(elapsed_ns=LOW_ELAPSED_NS),
        _document(elapsed_ns=HIGH_ELAPSED_NS),
    )

    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="document count exceeds configured limit",
    ):
        _ = collect_ticket_admission_telemetry(documents, max_documents=1)


def test_invalid_typed_document_fails_before_collection_identity() -> None:
    """Forged typed documents cannot acquire a fingerprint or summary entry."""
    malformed = replace(_document(), schema_version=True)

    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="document schema is unsupported",
    ):
        _ = ticket_admission_telemetry_document_fingerprint(malformed)
    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="document schema is unsupported",
    ):
        _ = collect_ticket_admission_telemetry((malformed,))


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
    """Distinct canonical bytes may never share one collection identity."""
    monkeypatch.setattr(collection_module, "sha256", _constant_sha256)
    documents = (
        _document(elapsed_ns=LOW_ELAPSED_NS),
        _document(elapsed_ns=HIGH_ELAPSED_NS),
    )

    with pytest.raises(
        TicketAdmissionTelemetryCollectionError,
        match="document fingerprint collision detected",
    ):
        _ = collect_ticket_admission_telemetry(documents)
