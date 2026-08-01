# File:
#   - ticket_admission_telemetry_overlap.py
# Path:
#   - accelerator/ticket_admission_telemetry_overlap.py
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
#   - Exact retained-sequence overlap comparison for two telemetry documents.
# - Must-Not:
#   - Infer recorder lineage, merge snapshots, load files, or change admission.
# - Allows:
#   - Inputs: two explicit schema-v1 telemetry documents.
#   - Outputs: immutable symmetric completed/failed overlap reports.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric lineage or recommendations gain a contract.
# - Merge-When:
#   - Merge when another module owns this exact pairwise overlap boundary.
# - Summary:
#   - Pairwise retained telemetry overlap detection.
# - Description:
#   - Compares exact retained observations without claiming common provenance.
# - Usage:
#   - Supply two documents and inspect matching or conflicting retained ranges.
# - Defaults:
#   - Invalid documents and digest collisions fail closed.
#
# Related documents:
# - accelerator/ticket_admission_telemetry.py
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_migration.py
# - accelerator/ticket_admission_telemetry_store.py
# - accelerator/ticket_admission_telemetry_overlap_index.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Exact pairwise overlap detection for retained telemetry observations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Final
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_collection import (
    TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_OVERLAP_ID: Final = (
    "offline-ticket-admission-telemetry-overlap-v1"
)


class TicketAdmissionTelemetryOverlapError(ValueError):
    """Two telemetry documents cannot produce an unambiguous overlap report."""


class TicketAdmissionTelemetryOverlapKind(StrEnum):
    """Exact relationship between two retained observation ranges."""

    CONFLICTING = "conflicting-overlap"
    MATCHING = "matching-overlap"
    NO_OVERLAP = "no-overlap"
    NO_RETAINED_OBSERVATIONS = "no-retained-observations"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryStreamOverlap:
    """Exact retained-range comparison for one completed or failed FIFO."""

    capacities_equal: bool
    conflicting_sequence_ids: tuple[int, ...]
    first_capacity: int
    first_retained_observation_count: int
    first_sequence_start: int
    first_sequence_stop: int
    matching_observation_count: int
    overlap_kind: TicketAdmissionTelemetryOverlapKind
    overlap_sequence_start: int | None
    overlap_sequence_stop: int | None
    overlapping_observation_count: int
    second_capacity: int
    second_retained_observation_count: int
    second_sequence_start: int
    second_sequence_stop: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryDocumentOverlap:
    """Symmetric non-lineage report for one canonical document pair."""

    completed: TicketAdmissionTelemetryStreamOverlap
    exact_document_match: bool
    failed: TicketAdmissionTelemetryStreamOverlap
    first_document_fingerprint: str
    overlap_id: str
    second_document_fingerprint: str


@dataclass(frozen=True, slots=True)
class _DocumentItem:
    canonical_bytes: bytes
    document: TicketAdmissionTelemetryDocument
    fingerprint: str


@dataclass(frozen=True, slots=True)
class _StreamView:
    capacity: int
    observations: tuple[object, ...]
    sequence_start: int
    sequence_stop: int


def ticket_admission_telemetry_overlap_id() -> str:
    """Return the stable pairwise overlap report identity.

    Returns:
        Versioned non-lineage overlap identity.

    """
    return TICKET_ADMISSION_TELEMETRY_OVERLAP_ID


def compare_ticket_admission_telemetry_documents(
    first: TicketAdmissionTelemetryDocument,
    second: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocumentOverlap:
    """Compare exact retained ranges without inferring recorder lineage.

    Returns:
        Fingerprint-ordered symmetric completed/failed overlap report.

    """
    first_item = _document_item(first)
    second_item = _document_item(second)
    _validate_distinct_fingerprint_bytes(first_item, second_item)
    lower, upper = _ordered_items(first_item, second_item)
    return TicketAdmissionTelemetryDocumentOverlap(
        completed=_stream_overlap(
            _completed_view(lower.document),
            _completed_view(upper.document),
        ),
        exact_document_match=(
            lower.canonical_bytes == upper.canonical_bytes
        ),
        failed=_stream_overlap(
            _failed_view(lower.document),
            _failed_view(upper.document),
        ),
        first_document_fingerprint=lower.fingerprint,
        overlap_id=TICKET_ADMISSION_TELEMETRY_OVERLAP_ID,
        second_document_fingerprint=upper.fingerprint,
    )


def _document_item(
    document: TicketAdmissionTelemetryDocument,
) -> _DocumentItem:
    canonical_bytes = _canonical_document_bytes(document)
    return _DocumentItem(
        canonical_bytes=canonical_bytes,
        document=document,
        fingerprint=_fingerprint(canonical_bytes),
    )


def _validate_distinct_fingerprint_bytes(
    first: _DocumentItem,
    second: _DocumentItem,
) -> None:
    if (
        first.fingerprint == second.fingerprint
        and first.canonical_bytes != second.canonical_bytes
    ):
        _raise_overlap("document fingerprint collision detected")


def _ordered_items(
    first: _DocumentItem,
    second: _DocumentItem,
) -> tuple[_DocumentItem, _DocumentItem]:
    if first.fingerprint <= second.fingerprint:
        return first, second
    return second, first


def _completed_view(
    document: TicketAdmissionTelemetryDocument,
) -> _StreamView:
    snapshot = document.completed
    return _StreamView(
        capacity=snapshot.capacity,
        observations=snapshot.observations,
        sequence_start=snapshot.dropped_observation_count,
        sequence_stop=snapshot.next_sequence_id,
    )


def _failed_view(
    document: TicketAdmissionTelemetryDocument,
) -> _StreamView:
    snapshot = document.failed
    return _StreamView(
        capacity=snapshot.capacity,
        observations=snapshot.observations,
        sequence_start=snapshot.dropped_observation_count,
        sequence_stop=snapshot.next_sequence_id,
    )


def _stream_overlap(
    first: _StreamView,
    second: _StreamView,
) -> TicketAdmissionTelemetryStreamOverlap:
    overlap_start = max(first.sequence_start, second.sequence_start)
    overlap_stop = min(first.sequence_stop, second.sequence_stop)
    if not first.observations and not second.observations:
        return _without_overlap(
            first,
            second,
            TicketAdmissionTelemetryOverlapKind.NO_RETAINED_OBSERVATIONS,
        )
    if overlap_start >= overlap_stop:
        return _without_overlap(
            first,
            second,
            TicketAdmissionTelemetryOverlapKind.NO_OVERLAP,
        )
    overlap_range = (overlap_start, overlap_stop)
    conflicts = _conflicting_sequence_ids(first, second, overlap_range)
    overlap_count = overlap_stop - overlap_start
    kind = TicketAdmissionTelemetryOverlapKind.MATCHING
    if conflicts:
        kind = TicketAdmissionTelemetryOverlapKind.CONFLICTING
    return TicketAdmissionTelemetryStreamOverlap(
        capacities_equal=first.capacity == second.capacity,
        conflicting_sequence_ids=conflicts,
        first_capacity=first.capacity,
        first_retained_observation_count=len(first.observations),
        first_sequence_start=first.sequence_start,
        first_sequence_stop=first.sequence_stop,
        matching_observation_count=overlap_count - len(conflicts),
        overlap_kind=kind,
        overlap_sequence_start=overlap_start,
        overlap_sequence_stop=overlap_stop,
        overlapping_observation_count=overlap_count,
        second_capacity=second.capacity,
        second_retained_observation_count=len(second.observations),
        second_sequence_start=second.sequence_start,
        second_sequence_stop=second.sequence_stop,
    )


def _without_overlap(
    first: _StreamView,
    second: _StreamView,
    kind: TicketAdmissionTelemetryOverlapKind,
) -> TicketAdmissionTelemetryStreamOverlap:
    return TicketAdmissionTelemetryStreamOverlap(
        capacities_equal=first.capacity == second.capacity,
        conflicting_sequence_ids=(),
        first_capacity=first.capacity,
        first_retained_observation_count=len(first.observations),
        first_sequence_start=first.sequence_start,
        first_sequence_stop=first.sequence_stop,
        matching_observation_count=0,
        overlap_kind=kind,
        overlap_sequence_start=None,
        overlap_sequence_stop=None,
        overlapping_observation_count=0,
        second_capacity=second.capacity,
        second_retained_observation_count=len(second.observations),
        second_sequence_start=second.sequence_start,
        second_sequence_stop=second.sequence_stop,
    )


def _conflicting_sequence_ids(
    first: _StreamView,
    second: _StreamView,
    overlap_range: tuple[int, int],
) -> tuple[int, ...]:
    overlap_start, overlap_stop = overlap_range
    return tuple(
        sequence_id
        for sequence_id in range(overlap_start, overlap_stop)
        if _observation(first, sequence_id)
        != _observation(second, sequence_id)
    )


def _observation(snapshot: _StreamView, sequence_id: int) -> object:
    return snapshot.observations[sequence_id - snapshot.sequence_start]


def _canonical_document_bytes(
    document: TicketAdmissionTelemetryDocument,
) -> bytes:
    try:
        return encode_ticket_admission_telemetry_document(document)
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid ticket telemetry document: {error}"
        raise TicketAdmissionTelemetryOverlapError(message) from error


def _fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return f"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}{digest}"


def _raise_overlap(message: str) -> None:
    raise TicketAdmissionTelemetryOverlapError(message)
