# File:
#   - ticket_admission_telemetry_store.py
# Path:
#   - accelerator/ticket_admission_telemetry_store.py
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
#   - Explicit caller-owned alternate store port and bounded memory adapter.
# - Must-Not:
#   - Auto-load, persist, merge, summarize, recommend, or change admission
#     policy.
# - Allows:
#   - Inputs: canonical schema-v1 telemetry documents and exact fingerprints.
#   - Outputs: deterministic put/get/remove results and immutable store
#     snapshots.
#   - Side effects: caller-owned in-memory insertion and removal only.
# - Split-When:
#   - Split when another concrete store backend gains an independent lifecycle.
# - Merge-When:
#   - Merge when another module owns this exact bounded alternate-store
#     contract.
# - Summary:
#   - Caller-owned bounded telemetry store port and memory adapter.
# - Description:
#   - Retains exact canonical document bytes without automatic loading or
#     policy.
# - Usage:
#   - Construct explicitly, put/get/remove explicitly, and inspect snapshots.
# - Defaults:
#   - At most 4,096 unique documents, 4,096 observations per FIFO, and
#     16 MiB of canonical bytes.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_summary.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-owned bounded alternate storage for canonical telemetry documents."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from hashlib import sha256
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
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
    decode_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_STORE_ID: Final = (
    "caller-owned-ticket-admission-telemetry-store-v1"
)
DEFAULT_MAX_TELEMETRY_STORE_DOCUMENTS: Final = 4_096
DEFAULT_MAX_TELEMETRY_STORE_BYTES: Final = 16 * 1024 * 1024
DEFAULT_MAX_TELEMETRY_STORE_OBSERVATIONS: Final = 4_096

_FINGERPRINT_PATTERN: Final = compile_pattern(
    rf"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}[0-9a-f]{{64}}"
)


class TicketAdmissionTelemetryStoreError(ValueError):
    """A telemetry store operation or retained canonical document is invalid."""


class TicketAdmissionTelemetryStorePutKind(StrEnum):
    """Stable result category for an explicit put operation."""

    INSERTED = "inserted"
    UNCHANGED = "unchanged"


class TicketAdmissionTelemetryStoreRemoveKind(StrEnum):
    """Stable result category for an explicit remove operation."""

    REMOVED = "removed"
    NOT_FOUND = "not-found"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryStoreEntry:
    """One exact retained fingerprint and canonical byte count."""

    canonical_byte_count: int
    document_fingerprint: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryStoreSnapshot:
    """Deterministic immutable metadata for one caller-owned store."""

    document_count: int
    entries: tuple[TicketAdmissionTelemetryStoreEntry, ...]
    max_documents: int
    max_observations: int
    max_total_bytes: int
    store_id: str
    total_canonical_byte_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryStorePutResult:
    """Explicit put result with the resulting bounded store totals."""

    canonical_byte_count: int
    document_count: int
    document_fingerprint: str
    kind: TicketAdmissionTelemetryStorePutKind
    total_canonical_byte_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryStoreRemoveResult:
    """Explicit remove result with the resulting bounded store totals."""

    document_count: int
    document_fingerprint: str
    kind: TicketAdmissionTelemetryStoreRemoveKind
    removed_canonical_byte_count: int
    total_canonical_byte_count: int


class TicketAdmissionTelemetryStore(Protocol):
    """Explicit alternate-store port for canonical telemetry documents."""

    def put(
        self,
        document: TicketAdmissionTelemetryDocument,
    ) -> TicketAdmissionTelemetryStorePutResult:
        """Insert exact canonical bytes or report an idempotent duplicate."""
        ...

    def get(
        self,
        document_fingerprint: str,
    ) -> TicketAdmissionTelemetryDocument | None:
        """Return one exact document or ``None`` without implicit loading."""
        ...

    def remove(
        self,
        document_fingerprint: str,
    ) -> TicketAdmissionTelemetryStoreRemoveResult:
        """Remove one exact document or report that it was absent."""
        ...

    def snapshot(self) -> TicketAdmissionTelemetryStoreSnapshot:
        """Return immutable deterministic non-document store metadata."""
        ...


@dataclass(slots=True, init=False)
class TicketAdmissionTelemetryMemoryStore:
    """Bounded caller-owned memory implementation of the store port."""

    _canonical_by_fingerprint: dict[str, bytes] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _max_documents: int = field(init=False, repr=False)
    _max_observations: int = field(init=False, repr=False)
    _max_total_bytes: int = field(init=False, repr=False)
    _total_canonical_byte_count: int = field(
        default=0,
        init=False,
        repr=False,
    )

    def __init__(
        self,
        *,
        max_documents: int = DEFAULT_MAX_TELEMETRY_STORE_DOCUMENTS,
        max_observations: int = DEFAULT_MAX_TELEMETRY_STORE_OBSERVATIONS,
        max_total_bytes: int = DEFAULT_MAX_TELEMETRY_STORE_BYTES,
    ) -> None:
        """Create an empty store with immutable positive resource limits."""
        self._canonical_by_fingerprint = {}
        self._max_documents = _validated_positive_limit(
            max_documents,
            "document limit",
        )
        self._max_observations = _validated_positive_limit(
            max_observations,
            "observation limit",
        )
        self._max_total_bytes = _validated_positive_limit(
            max_total_bytes,
            "byte limit",
        )
        self._total_canonical_byte_count = 0

    @property
    def max_documents(self) -> int:
        """The immutable unique-document limit.

        Returns:
            Positive document limit selected at construction.

        """
        return self._max_documents

    @property
    def max_observations(self) -> int:
        """The immutable per-FIFO observation limit.

        Returns:
            Positive observation limit selected at construction.

        """
        return self._max_observations

    @property
    def max_total_bytes(self) -> int:
        """The immutable canonical-byte limit.

        Returns:
            Positive byte limit selected at construction.

        """
        return self._max_total_bytes

    def put(
        self,
        document: TicketAdmissionTelemetryDocument,
    ) -> TicketAdmissionTelemetryStorePutResult:
        """Insert canonical bytes under exact unique-document budgets.

        Returns:
            Stable insertion or idempotent-duplicate result.

        """
        canonical_bytes = _canonical_bytes(
            document,
            max_observations=self.max_observations,
        )
        fingerprint = _fingerprint(canonical_bytes)
        existing = self._canonical_by_fingerprint.get(fingerprint)
        if existing is not None:
            if existing != canonical_bytes:
                _raise_store("document fingerprint collision detected")
            return self._put_result(
                fingerprint,
                canonical_bytes,
                TicketAdmissionTelemetryStorePutKind.UNCHANGED,
            )
        self._validate_insert_budget(len(canonical_bytes))
        self._canonical_by_fingerprint[fingerprint] = canonical_bytes
        self._total_canonical_byte_count += len(canonical_bytes)
        return self._put_result(
            fingerprint,
            canonical_bytes,
            TicketAdmissionTelemetryStorePutKind.INSERTED,
        )

    def get(
        self,
        document_fingerprint: str,
    ) -> TicketAdmissionTelemetryDocument | None:
        """Decode one retained canonical byte sequence on explicit lookup.

        Returns:
            Exact retained document, or ``None`` when absent.

        """
        fingerprint = _validated_fingerprint(document_fingerprint)
        canonical_bytes = self._canonical_by_fingerprint.get(fingerprint)
        if canonical_bytes is None:
            return None
        return _decoded_document(
            canonical_bytes,
            max_observations=self.max_observations,
        )

    def remove(
        self,
        document_fingerprint: str,
    ) -> TicketAdmissionTelemetryStoreRemoveResult:
        """Remove one retained byte sequence and release its byte budget.

        Returns:
            Stable removed or not-found result.

        """
        fingerprint = _validated_fingerprint(document_fingerprint)
        canonical_bytes = self._canonical_by_fingerprint.pop(fingerprint, None)
        if canonical_bytes is None:
            return self._remove_result(
                fingerprint,
                0,
                TicketAdmissionTelemetryStoreRemoveKind.NOT_FOUND,
            )
        removed_byte_count = len(canonical_bytes)
        self._total_canonical_byte_count -= removed_byte_count
        return self._remove_result(
            fingerprint,
            removed_byte_count,
            TicketAdmissionTelemetryStoreRemoveKind.REMOVED,
        )

    def snapshot(self) -> TicketAdmissionTelemetryStoreSnapshot:
        """Return fingerprint-ordered metadata without canonical bytes.

        Returns:
            Immutable deterministic store metadata.

        """
        entries = tuple(
            TicketAdmissionTelemetryStoreEntry(
                canonical_byte_count=len(
                    self._canonical_by_fingerprint[fingerprint]
                ),
                document_fingerprint=fingerprint,
            )
            for fingerprint in sorted(self._canonical_by_fingerprint)
        )
        return TicketAdmissionTelemetryStoreSnapshot(
            document_count=len(entries),
            entries=entries,
            max_documents=self.max_documents,
            max_observations=self.max_observations,
            max_total_bytes=self.max_total_bytes,
            store_id=TICKET_ADMISSION_TELEMETRY_STORE_ID,
            total_canonical_byte_count=self._total_canonical_byte_count,
        )

    def _validate_insert_budget(self, canonical_byte_count: int) -> None:
        if len(self._canonical_by_fingerprint) >= self.max_documents:
            _raise_store("document count exceeds configured limit")
        resulting_byte_count = (
            self._total_canonical_byte_count + canonical_byte_count
        )
        if resulting_byte_count > self.max_total_bytes:
            _raise_store("canonical bytes exceed configured limit")

    def _put_result(
        self,
        fingerprint: str,
        canonical_bytes: bytes,
        kind: TicketAdmissionTelemetryStorePutKind,
    ) -> TicketAdmissionTelemetryStorePutResult:
        return TicketAdmissionTelemetryStorePutResult(
            canonical_byte_count=len(canonical_bytes),
            document_count=len(self._canonical_by_fingerprint),
            document_fingerprint=fingerprint,
            kind=kind,
            total_canonical_byte_count=self._total_canonical_byte_count,
        )

    def _remove_result(
        self,
        fingerprint: str,
        removed_byte_count: int,
        kind: TicketAdmissionTelemetryStoreRemoveKind,
    ) -> TicketAdmissionTelemetryStoreRemoveResult:
        return TicketAdmissionTelemetryStoreRemoveResult(
            document_count=len(self._canonical_by_fingerprint),
            document_fingerprint=fingerprint,
            kind=kind,
            removed_canonical_byte_count=removed_byte_count,
            total_canonical_byte_count=self._total_canonical_byte_count,
        )


def ticket_admission_telemetry_store_id() -> str:
    """Return the stable caller-owned alternate-store identity.

    Returns:
        Versioned store identity.

    """
    return TICKET_ADMISSION_TELEMETRY_STORE_ID


def _canonical_bytes(
    document: TicketAdmissionTelemetryDocument,
    *,
    max_observations: int,
) -> bytes:
    try:
        canonical_bytes = encode_ticket_admission_telemetry_document(document)
        _ = decode_ticket_admission_telemetry_document(
            canonical_bytes,
            max_bytes=len(canonical_bytes),
            max_observations=max_observations,
        )
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid telemetry document: {error}"
        raise TicketAdmissionTelemetryStoreError(message) from error
    return canonical_bytes


def _decoded_document(
    canonical_bytes: bytes,
    *,
    max_observations: int,
) -> TicketAdmissionTelemetryDocument:
    try:
        return decode_ticket_admission_telemetry_document(
            canonical_bytes,
            max_bytes=len(canonical_bytes),
            max_observations=max_observations,
        )
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"retained telemetry document became invalid: {error}"
        raise TicketAdmissionTelemetryStoreError(message) from error


def _fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return f"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}{digest}"


def _validated_fingerprint(document_fingerprint: str) -> str:
    if (
        type(document_fingerprint) is not str
        or _FINGERPRINT_PATTERN.fullmatch(document_fingerprint) is None
    ):
        _raise_store("document fingerprint is invalid")
    return document_fingerprint


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_store(f"{field_name} must be a positive integer")
    return value


def _raise_store(detail: str) -> Never:
    message = f"ticket admission telemetry store {detail}"
    raise TicketAdmissionTelemetryStoreError(message)
