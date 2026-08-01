# File:
#   - ticket_admission_telemetry_overlap_index.py
# Path:
#   - accelerator/ticket_admission_telemetry_overlap_index.py
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
#   - Deterministic bounded all-pairs overlap indexing for explicit telemetry.
# - Must-Not:
#   - Infer recorder lineage, merge snapshots, load files, or change admission.
# - Allows:
#   - Inputs: one explicit bounded tuple of schema-v1 telemetry documents.
#   - Outputs: one deduplicated collection and fingerprint-ordered pair reports.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric lineage or recommendations gain a contract.
# - Merge-When:
#   - Merge when another module owns this exact all-pairs indexing boundary.
# - Summary:
#   - Bounded collection-wide telemetry overlap index.
# - Description:
#   - Compares every unique canonical document pair without provenance claims.
# - Usage:
#   - Supply explicit documents and review deterministic pair classifications.
# - Defaults:
#   - Collection bounds apply; at most 65,536 unique pairs are compared.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_overlap.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_secret_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Bounded all-pairs overlap indexing for explicit telemetry documents."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from itertools import starmap
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_collection import (
        TicketAdmissionTelemetryCollection,
    )
    from accelerator.ticket_admission_telemetry_overlap import (
        TicketAdmissionTelemetryDocumentOverlap,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_collection import (
    DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES,
)
from accelerator.ticket_admission_telemetry_collection import (
    DEFAULT_MAX_TELEMETRY_DOCUMENTS,
)
from accelerator.ticket_admission_telemetry_collection import (
    TicketAdmissionTelemetryCollectionError,
)
from accelerator.ticket_admission_telemetry_collection import (
    collect_ticket_admission_telemetry,
)
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_overlap import (
    TicketAdmissionTelemetryOverlapError,
)
from accelerator.ticket_admission_telemetry_overlap import (
    TicketAdmissionTelemetryOverlapKind,
)
from accelerator.ticket_admission_telemetry_overlap import (
    compare_ticket_admission_telemetry_documents,
)

TICKET_ADMISSION_TELEMETRY_OVERLAP_INDEX_ID: Final = (
    "offline-ticket-admission-telemetry-overlap-index-v1"
)
DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS: Final = 65_536


class TicketAdmissionTelemetryOverlapIndexError(ValueError):
    """A telemetry collection cannot produce a bounded overlap index."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryOverlapClassificationSummary:
    """Stable pair counts for every retained-overlap classification."""

    conflicting_pair_count: int
    matching_pair_count: int
    no_overlap_pair_count: int
    no_retained_observations_pair_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryOverlapIndex:
    """Deterministic all-pairs review surface without lineage authority."""

    collection: TicketAdmissionTelemetryCollection
    completed_classifications: (
        TicketAdmissionTelemetryOverlapClassificationSummary
    )
    failed_classifications: TicketAdmissionTelemetryOverlapClassificationSummary
    index_id: str
    pair_count: int
    pair_limit: int
    pairs: tuple[TicketAdmissionTelemetryDocumentOverlap, ...]


def ticket_admission_telemetry_overlap_index_id() -> str:
    """Return the stable collection-wide overlap index identity.

    Returns:
        Versioned bounded all-pairs index identity.

    """
    return TICKET_ADMISSION_TELEMETRY_OVERLAP_INDEX_ID


def index_ticket_admission_telemetry_overlap(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    *,
    max_documents: int = DEFAULT_MAX_TELEMETRY_DOCUMENTS,
    max_total_bytes: int = DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES,
    max_pairs: int = DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS,
) -> TicketAdmissionTelemetryOverlapIndex:
    """Index every unique canonical document pair within explicit bounds.

    Returns:
        Fingerprint-ordered pair reports and stable classification counts.

    """
    pair_limit = _validated_pair_limit(max_pairs)
    collection = _collection(
        documents,
        max_documents=max_documents,
        max_total_bytes=max_total_bytes,
    )
    pair_count = _pair_count(len(collection.unique_documents))
    if pair_count > pair_limit:
        _raise_index("unique document pairs exceed configured limit")
    ordered_documents = _ordered_unique_documents(documents, collection)
    pairs = tuple(
        starmap(_compare, combinations(ordered_documents, 2))
    )
    return TicketAdmissionTelemetryOverlapIndex(
        collection=collection,
        completed_classifications=_classification_summary(
            tuple(pair.completed.overlap_kind for pair in pairs)
        ),
        failed_classifications=_classification_summary(
            tuple(pair.failed.overlap_kind for pair in pairs)
        ),
        index_id=TICKET_ADMISSION_TELEMETRY_OVERLAP_INDEX_ID,
        pair_count=pair_count,
        pair_limit=pair_limit,
        pairs=pairs,
    )


def _validated_pair_limit(max_pairs: int) -> int:
    if type(max_pairs) is not int or max_pairs <= 0:
        _raise_index("pair limit must be a positive integer")
    return max_pairs


def _collection(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    *,
    max_documents: int,
    max_total_bytes: int,
) -> TicketAdmissionTelemetryCollection:
    try:
        return collect_ticket_admission_telemetry(
            documents,
            max_documents=max_documents,
            max_total_bytes=max_total_bytes,
        )
    except TicketAdmissionTelemetryCollectionError as error:
        message = f"invalid telemetry collection: {error}"
        raise TicketAdmissionTelemetryOverlapIndexError(message) from error


def _pair_count(unique_document_count: int) -> int:
    return unique_document_count * (unique_document_count - 1) // 2


def _ordered_unique_documents(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    collection: TicketAdmissionTelemetryCollection,
) -> tuple[TicketAdmissionTelemetryDocument, ...]:
    by_fingerprint: dict[str, TicketAdmissionTelemetryDocument] = {}
    for document in documents:
        fingerprint = _document_fingerprint(document)
        if fingerprint not in by_fingerprint:
            by_fingerprint[fingerprint] = document
    return tuple(
        by_fingerprint[entry.document_fingerprint]
        for entry in collection.unique_documents
    )


def _document_fingerprint(
    document: TicketAdmissionTelemetryDocument,
) -> str:
    try:
        return ticket_admission_telemetry_document_fingerprint(document)
    except TicketAdmissionTelemetryCollectionError as error:
        message = f"invalid telemetry document identity: {error}"
        raise TicketAdmissionTelemetryOverlapIndexError(message) from error


def _compare(
    first: TicketAdmissionTelemetryDocument,
    second: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocumentOverlap:
    try:
        return compare_ticket_admission_telemetry_documents(first, second)
    except TicketAdmissionTelemetryOverlapError as error:
        message = f"invalid telemetry overlap pair: {error}"
        raise TicketAdmissionTelemetryOverlapIndexError(message) from error


def _classification_summary(
    kinds: tuple[TicketAdmissionTelemetryOverlapKind, ...],
) -> TicketAdmissionTelemetryOverlapClassificationSummary:
    counts = dict.fromkeys(TicketAdmissionTelemetryOverlapKind, 0)
    for kind in kinds:
        counts[kind] += 1
    return TicketAdmissionTelemetryOverlapClassificationSummary(
        conflicting_pair_count=counts[
            TicketAdmissionTelemetryOverlapKind.CONFLICTING
        ],
        matching_pair_count=counts[
            TicketAdmissionTelemetryOverlapKind.MATCHING
        ],
        no_overlap_pair_count=counts[
            TicketAdmissionTelemetryOverlapKind.NO_OVERLAP
        ],
        no_retained_observations_pair_count=counts[
            TicketAdmissionTelemetryOverlapKind.NO_RETAINED_OBSERVATIONS
        ],
    )


def _raise_index(detail: str) -> Never:
    message = f"ticket admission telemetry overlap index {detail}"
    raise TicketAdmissionTelemetryOverlapIndexError(message)
