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
#   - Byte-exact identity and deduplication for explicit telemetry documents.
# - Must-Not:
#   - Merge overlapping snapshots, recommend routes, load files, or change
#     policy.
# - Allows:
#   - Inputs: one immutable bounded tuple of schema-v1 telemetry documents.
#   - Outputs: canonical SHA-256 identities and per-document offline summaries.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric lineage or recommendations gain an independent
#     contract.
# - Merge-When:
#   - Merge when another module owns this exact collection identity boundary.
# - Summary:
#   - Exact telemetry document collection identity.
# - Description:
#   - Deduplicates only byte-identical canonical telemetry documents.
# - Usage:
#   - Supply explicit documents, then review deterministic unique entries.
# - Defaults:
#   - Empty collections are valid; malformed, oversized, or ambiguous input
#     fails.
#

"""Byte-exact identity and deduplication for telemetry documents."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )
    from accelerator.ticket_admission_telemetry_summary import (
        TicketAdmissionTelemetrySummary,
    )

from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_summary import (
    TicketAdmissionTelemetrySummaryError,
)
from accelerator.ticket_admission_telemetry_summary import (
    summarize_ticket_admission_telemetry,
)

TICKET_ADMISSION_TELEMETRY_COLLECTION_ID: Final = (
    "offline-ticket-admission-telemetry-collection-v1"
)
TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-document-v1:sha256:"
)
DEFAULT_MAX_TELEMETRY_DOCUMENTS: Final = 4_096
DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES: Final = 16 * 1024 * 1024


class TicketAdmissionTelemetryCollectionError(ValueError):
    """An explicit telemetry document collection is invalid or ambiguous."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryCollectionEntry:
    """One unique canonical document and its non-authoritative summary."""

    canonical_byte_count: int
    document_fingerprint: str
    occurrence_count: int
    summary: TicketAdmissionTelemetrySummary


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryCollection:
    """Deterministic byte-exact document identities without snapshot merging."""

    collection_id: str
    duplicate_canonical_byte_count: int
    duplicate_document_count: int
    input_canonical_byte_count: int
    input_document_count: int
    unique_canonical_byte_count: int
    unique_documents: tuple[TicketAdmissionTelemetryCollectionEntry, ...]


@dataclass(slots=True)
class _CollectedDocument:
    canonical_bytes: bytes
    occurrence_count: int
    summary: TicketAdmissionTelemetrySummary


def ticket_admission_telemetry_collection_id() -> str:
    """Return the stable explicit telemetry collection identity.

    Returns:
        Versioned byte-exact collection identity.

    """
    return TICKET_ADMISSION_TELEMETRY_COLLECTION_ID


def ticket_admission_telemetry_document_fingerprint(
    document: TicketAdmissionTelemetryDocument,
) -> str:
    """Return a self-describing SHA-256 over canonical document bytes.

    Returns:
        Stable canonical telemetry document fingerprint.

    """
    canonical_bytes = _canonical_document_bytes(document)
    return _fingerprint(canonical_bytes)


def collect_ticket_admission_telemetry(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    *,
    max_documents: int = DEFAULT_MAX_TELEMETRY_DOCUMENTS,
    max_total_bytes: int = DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES,
) -> TicketAdmissionTelemetryCollection:
    """Identify and deduplicate one explicit bounded document tuple.

    Returns:
        Fingerprint-ordered unique documents with occurrence counts.

    """
    document_limit = _validated_document_limit(max_documents)
    byte_limit = _validated_byte_limit(max_total_bytes)
    items = _validated_documents(documents, document_limit)
    collected: dict[str, _CollectedDocument] = {}
    input_byte_count = 0
    for document in items:
        canonical_bytes = _canonical_document_bytes(document)
        input_byte_count += len(canonical_bytes)
        if input_byte_count > byte_limit:
            _raise_collection("canonical input exceeds configured byte limit")
        _collect_document(collected, document, canonical_bytes)
    unique_documents = tuple(
        _collection_entry(fingerprint, collected[fingerprint])
        for fingerprint in sorted(collected)
    )
    unique_byte_count = sum(
        entry.canonical_byte_count for entry in unique_documents
    )
    return TicketAdmissionTelemetryCollection(
        collection_id=TICKET_ADMISSION_TELEMETRY_COLLECTION_ID,
        duplicate_canonical_byte_count=input_byte_count - unique_byte_count,
        duplicate_document_count=len(items) - len(unique_documents),
        input_canonical_byte_count=input_byte_count,
        input_document_count=len(items),
        unique_canonical_byte_count=unique_byte_count,
        unique_documents=unique_documents,
    )


def _validated_documents(
    documents: object,
    max_documents: int,
) -> tuple[TicketAdmissionTelemetryDocument, ...]:
    if type(documents) is not tuple:
        _raise_collection("documents must be an immutable tuple")
    items = cast("tuple[object, ...]", documents)
    if len(items) > max_documents:
        _raise_collection("document count exceeds configured limit")
    return cast("tuple[TicketAdmissionTelemetryDocument, ...]", items)


def _validated_document_limit(max_documents: int) -> int:
    if type(max_documents) is not int or max_documents <= 0:
        _raise_collection("document limit must be a positive integer")
    return max_documents


def _validated_byte_limit(max_total_bytes: int) -> int:
    if type(max_total_bytes) is not int or max_total_bytes <= 0:
        _raise_collection("byte limit must be a positive integer")
    return max_total_bytes


def _collect_document(
    collected: dict[str, _CollectedDocument],
    document: TicketAdmissionTelemetryDocument,
    canonical_bytes: bytes,
) -> None:
    fingerprint = _fingerprint(canonical_bytes)
    existing = collected.get(fingerprint)
    if existing is None:
        collected[fingerprint] = _CollectedDocument(
            canonical_bytes=canonical_bytes,
            occurrence_count=1,
            summary=_summary(document),
        )
        return
    if existing.canonical_bytes != canonical_bytes:
        _raise_collection("document fingerprint collision detected")
    existing.occurrence_count += 1


def _canonical_document_bytes(
    document: TicketAdmissionTelemetryDocument,
) -> bytes:
    try:
        return encode_ticket_admission_telemetry_document(document)
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid telemetry document: {error}"
        raise TicketAdmissionTelemetryCollectionError(message) from error


def _summary(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetrySummary:
    try:
        return summarize_ticket_admission_telemetry(document)
    except TicketAdmissionTelemetrySummaryError as error:
        message = f"invalid telemetry document summary: {error}"
        raise TicketAdmissionTelemetryCollectionError(message) from error


def _fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return f"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}{digest}"


def _collection_entry(
    fingerprint: str,
    document: _CollectedDocument,
) -> TicketAdmissionTelemetryCollectionEntry:
    return TicketAdmissionTelemetryCollectionEntry(
        canonical_byte_count=len(document.canonical_bytes),
        document_fingerprint=fingerprint,
        occurrence_count=document.occurrence_count,
        summary=document.summary,
    )


def _raise_collection(detail: str) -> Never:
    message = f"ticket admission telemetry collection {detail}"
    raise TicketAdmissionTelemetryCollectionError(message)
