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
#   - Caller-owned bounded telemetry alternate-store regressions.
# - Must-Not:
#   - Require CUDA, filesystem access, merging, summaries, or admission policy.
# - Allows:
#   - Inputs: synthetic documents, fingerprints, limits, and local
#     monkeypatches.
#   - Outputs: put/get/remove, ordering, budget, collision, and corruption
#     checks.
#   - Side effects: caller-owned in-memory store mutation only.
# - Split-When:
#   - Split when another concrete store backend gains independent tests.
# - Merge-When:
#   - Merge when another suite owns this exact alternate-store behavior.
# - Summary:
#   - Bounded in-memory telemetry store regressions.
# - Description:
#   - Proves exact canonical storage is explicit, idempotent, and fail-closed.
# - Usage:
#   - Runs without accelerator hardware, files, or automatic loading.
# - Defaults:
#   - Uses two deterministic documents and exact schema-v1 canonical bytes
#     under explicit document, observation, and byte limits.
#

"""Caller-owned bounded telemetry alternate-store tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )
    from accelerator.ticket_admission_telemetry_store import (
        TicketAdmissionTelemetryStore,
    )

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
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)
import accelerator.ticket_admission_telemetry_store as store_module
from accelerator.ticket_admission_telemetry_store import (
    TicketAdmissionTelemetryMemoryStore,
)
from accelerator.ticket_admission_telemetry_store import (
    TicketAdmissionTelemetryStoreError,
)
from accelerator.ticket_admission_telemetry_store import (
    TicketAdmissionTelemetryStorePutKind,
)
from accelerator.ticket_admission_telemetry_store import (
    TicketAdmissionTelemetryStoreRemoveKind,
)
from accelerator.ticket_admission_telemetry_store import (
    ticket_admission_telemetry_store_id,
)

STORE_ID = "caller-owned-ticket-admission-telemetry-store-v1"
FINGERPRINT_PREFIX = "ticket-admission-telemetry-document-v1:sha256:"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "store-test-workload-v1"
BENCHMARK_ID = "store-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
DOCUMENT_PAIR_COUNT = 2
DEFAULT_DOCUMENT_LIMIT = 4_096
DEFAULT_BYTE_LIMIT = 16 * 1024 * 1024
DEFAULT_OBSERVATION_LIMIT = 4_096
INTERNAL_CANONICAL_FIELD = b"_canonical_by_fingerprint"
ZERO = 0
ONE = 1


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
    capacity: int = 4,
    elapsed_ns: int = CANDIDATE_NS,
    workload_id: str = WORKLOAD_ID,
) -> TicketAdmissionTelemetryDocument:
    attempts = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=capacity),
        failed=TicketAdmissionFailureTelemetry(capacity=capacity),
    )
    _ = attempts.record_completed(
        _report(workload_id=workload_id),
        elapsed_ns=elapsed_ns,
    )
    return capture_ticket_admission_telemetry_document(attempts)


def _assert_store_port(store: TicketAdmissionTelemetryStore) -> None:
    assert store.snapshot().store_id == STORE_ID


def _fingerprint_for(document: TicketAdmissionTelemetryDocument) -> str:
    return ticket_admission_telemetry_document_fingerprint(document)


def _assign_attribute(
    target: object,
    attribute_name: str,
    value: object,
) -> None:
    setattr(target, attribute_name, value)


def test_empty_store_has_stable_identity_and_default_bounds() -> None:
    """A new store is empty, bounded, and satisfies the alternate-store port."""
    store = TicketAdmissionTelemetryMemoryStore()

    snapshot = store.snapshot()

    _assert_store_port(store)
    assert ticket_admission_telemetry_store_id() == STORE_ID
    assert snapshot.store_id == STORE_ID
    assert snapshot.document_count == ZERO
    assert snapshot.total_canonical_byte_count == ZERO
    assert snapshot.entries == ()
    assert snapshot.max_documents == DEFAULT_DOCUMENT_LIMIT
    assert snapshot.max_observations == DEFAULT_OBSERVATION_LIMIT
    assert snapshot.max_total_bytes == DEFAULT_BYTE_LIMIT


def test_put_get_and_snapshot_preserve_exact_canonical_identity() -> None:
    """Insertion retains bytes and lookup restores the document."""
    document = _document()
    canonical = encode_ticket_admission_telemetry_document(document)
    fingerprint = _fingerprint_for(document)
    store = TicketAdmissionTelemetryMemoryStore()

    result = store.put(document)
    restored = store.get(fingerprint)
    snapshot = store.snapshot()

    assert result.kind is TicketAdmissionTelemetryStorePutKind.INSERTED
    assert result.document_fingerprint == fingerprint
    assert result.canonical_byte_count == len(canonical)
    assert result.document_count == ONE
    assert result.total_canonical_byte_count == len(canonical)
    assert restored == document
    assert snapshot.document_count == ONE
    assert snapshot.total_canonical_byte_count == len(canonical)
    assert snapshot.entries[0].document_fingerprint == fingerprint
    assert snapshot.entries[0].canonical_byte_count == len(canonical)


def test_duplicate_put_is_idempotent_and_consumes_no_budget() -> None:
    """Byte-identical documents do not increase counts or retained bytes."""
    document = _document()
    store = TicketAdmissionTelemetryMemoryStore()

    inserted = store.put(document)
    unchanged = store.put(document)

    assert inserted.kind is TicketAdmissionTelemetryStorePutKind.INSERTED
    assert unchanged.kind is TicketAdmissionTelemetryStorePutKind.UNCHANGED
    assert unchanged.document_fingerprint == inserted.document_fingerprint
    assert unchanged.document_count == ONE
    assert unchanged.total_canonical_byte_count == (
        inserted.total_canonical_byte_count
    )
    assert store.snapshot().document_count == ONE


def test_snapshot_entries_are_fingerprint_ordered() -> None:
    """Insertion order cannot change deterministic snapshot metadata order."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS, workload_id="work-z")
    second = _document(elapsed_ns=HIGH_ELAPSED_NS, workload_id="work-a")
    store = TicketAdmissionTelemetryMemoryStore()

    _ = store.put(first)
    _ = store.put(second)
    fingerprints = tuple(
        entry.document_fingerprint for entry in store.snapshot().entries
    )

    assert fingerprints == tuple(sorted(fingerprints))
    assert len(fingerprints) == DOCUMENT_PAIR_COUNT


def test_missing_get_is_explicit_and_nonmutating() -> None:
    """Absent exact fingerprints return ``None`` without changing the store."""
    store = TicketAdmissionTelemetryMemoryStore()
    fingerprint = f"{FINGERPRINT_PREFIX}{"0" * 64}"

    result = store.get(fingerprint)

    assert result is None
    assert store.snapshot().document_count == ZERO


def test_remove_releases_exact_document_and_byte_budget() -> None:
    """Removal returns exact bytes released and restores empty-store totals."""
    document = _document()
    store = TicketAdmissionTelemetryMemoryStore()
    inserted = store.put(document)

    removed = store.remove(inserted.document_fingerprint)

    assert removed.kind is TicketAdmissionTelemetryStoreRemoveKind.REMOVED
    assert removed.document_fingerprint == inserted.document_fingerprint
    assert removed.removed_canonical_byte_count == inserted.canonical_byte_count
    assert removed.document_count == ZERO
    assert removed.total_canonical_byte_count == ZERO
    assert store.get(inserted.document_fingerprint) is None


def test_remove_missing_is_stable_and_nonmutating() -> None:
    """Removing an absent exact fingerprint returns a typed not-found result."""
    store = TicketAdmissionTelemetryMemoryStore()
    fingerprint = f"{FINGERPRINT_PREFIX}{"f" * 64}"

    result = store.remove(fingerprint)

    assert result.kind is TicketAdmissionTelemetryStoreRemoveKind.NOT_FOUND
    assert result.document_fingerprint == fingerprint
    assert result.removed_canonical_byte_count == ZERO
    assert result.document_count == ZERO
    assert result.total_canonical_byte_count == ZERO


def test_removal_frees_document_limit_for_later_insert() -> None:
    """A removed entry frees one unique-document slot for explicit reuse."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    store = TicketAdmissionTelemetryMemoryStore(max_documents=ONE)
    inserted = store.put(first)

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document count exceeds configured limit",
    ):
        _ = store.put(second)

    _ = store.remove(inserted.document_fingerprint)
    replacement = store.put(second)

    assert replacement.kind is TicketAdmissionTelemetryStorePutKind.INSERTED
    assert store.snapshot().document_count == ONE


def test_removal_frees_byte_limit_for_later_insert() -> None:
    """A removed entry releases exact canonical bytes for explicit reuse."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    first_bytes = len(encode_ticket_admission_telemetry_document(first))
    second_bytes = len(encode_ticket_admission_telemetry_document(second))
    store = TicketAdmissionTelemetryMemoryStore(
        max_total_bytes=max(first_bytes, second_bytes),
    )
    inserted = store.put(first)

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="canonical bytes exceed configured limit",
    ):
        _ = store.put(second)

    _ = store.remove(inserted.document_fingerprint)
    replacement = store.put(second)

    assert replacement.kind is TicketAdmissionTelemetryStorePutKind.INSERTED
    assert replacement.total_canonical_byte_count == second_bytes


@pytest.mark.parametrize("max_documents", [ZERO, True])
def test_invalid_document_limit_fails_at_construction(
    max_documents: int,
) -> None:
    """Zero and boolean document limits never create a store."""
    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document limit must be a positive integer",
    ):
        _ = TicketAdmissionTelemetryMemoryStore(
            max_documents=max_documents,
        )


@pytest.mark.parametrize("max_observations", [ZERO, True])
def test_invalid_observation_limit_fails_at_construction(
    max_observations: int,
) -> None:
    """Zero and boolean observation limits never create a store."""
    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="observation limit must be a positive integer",
    ):
        _ = TicketAdmissionTelemetryMemoryStore(
            max_observations=max_observations,
        )


def test_observation_limit_rejects_document_before_mutation() -> None:
    """Per-FIFO capacity is bounded symmetrically for put and get."""
    document = _document(capacity=2)
    store = TicketAdmissionTelemetryMemoryStore(max_observations=ONE)

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="snapshot capacity exceeds observation limit",
    ):
        _ = store.put(document)

    assert store.snapshot().document_count == ZERO


@pytest.mark.parametrize("max_total_bytes", [ZERO, True])
def test_invalid_byte_limit_fails_at_construction(
    max_total_bytes: int,
) -> None:
    """Zero and boolean byte limits never create a store."""
    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="byte limit must be a positive integer",
    ):
        _ = TicketAdmissionTelemetryMemoryStore(
            max_total_bytes=max_total_bytes,
        )


def test_exact_document_and_byte_limits_are_admitted() -> None:
    """A document exactly matching both configured budgets is accepted."""
    document = _document()
    canonical_byte_count = len(
        encode_ticket_admission_telemetry_document(document)
    )
    store = TicketAdmissionTelemetryMemoryStore(
        max_documents=ONE,
        max_total_bytes=canonical_byte_count,
    )

    result = store.put(document)

    assert result.kind is TicketAdmissionTelemetryStorePutKind.INSERTED
    assert result.document_count == ONE
    assert result.total_canonical_byte_count == canonical_byte_count


def test_duplicate_put_is_allowed_when_store_is_at_both_limits() -> None:
    """An idempotent duplicate requires no additional budget."""
    document = _document()
    canonical_byte_count = len(
        encode_ticket_admission_telemetry_document(document)
    )
    store = TicketAdmissionTelemetryMemoryStore(
        max_documents=ONE,
        max_total_bytes=canonical_byte_count,
    )
    _ = store.put(document)

    result = store.put(document)

    assert result.kind is TicketAdmissionTelemetryStorePutKind.UNCHANGED
    assert result.document_count == ONE
    assert result.total_canonical_byte_count == canonical_byte_count


def test_store_limits_are_read_only_after_construction() -> None:
    """Callers cannot widen resource budgets after constructing a store."""
    store = TicketAdmissionTelemetryMemoryStore(
        max_documents=ONE,
        max_total_bytes=ONE,
    )

    with pytest.raises(AttributeError, match="has no setter"):
        _assign_attribute(store, "max_documents", 2)
    with pytest.raises(AttributeError, match="has no setter"):
        _assign_attribute(store, "max_observations", 2)
    with pytest.raises(AttributeError, match="has no setter"):
        _assign_attribute(store, "max_total_bytes", 2)

    assert store.max_documents == ONE
    assert store.max_observations == DEFAULT_OBSERVATION_LIMIT
    assert store.max_total_bytes == ONE


@pytest.mark.parametrize(
    "fingerprint",
    [
        "",
        "not-a-fingerprint",
        f"{FINGERPRINT_PREFIX}{"A" * 64}",
        f"{FINGERPRINT_PREFIX}{"0" * 63}",
        cast("str", object()),
    ],
)
def test_invalid_fingerprint_fails_before_lookup_or_removal(
    fingerprint: str,
) -> None:
    """Only the exact lowercase schema-v1 fingerprint form is accepted."""
    store = TicketAdmissionTelemetryMemoryStore()

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document fingerprint is invalid",
    ):
        _ = store.get(fingerprint)
    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document fingerprint is invalid",
    ):
        _ = store.remove(fingerprint)

    assert store.snapshot().document_count == ZERO


def test_invalid_typed_document_fails_before_store_mutation() -> None:
    """Forged typed documents cannot consume store budget."""
    malformed = replace(_document(), schema_version=True)
    store = TicketAdmissionTelemetryMemoryStore()

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document schema is unsupported",
    ):
        _ = store.put(malformed)

    assert store.snapshot().document_count == ZERO


def test_snapshot_and_repr_do_not_expose_canonical_document_bytes() -> None:
    """Metadata surfaces do not retain or display full canonical payloads."""
    document = _document()
    canonical = encode_ticket_admission_telemetry_document(document)
    store = TicketAdmissionTelemetryMemoryStore()
    _ = store.put(document)

    snapshot_repr = repr(store.snapshot()).encode("utf-8")
    store_repr = repr(store).encode("utf-8")

    assert canonical not in snapshot_repr
    assert canonical not in store_repr
    assert INTERNAL_CANONICAL_FIELD not in store_repr


def test_put_and_remove_result_kinds_have_stable_values() -> None:
    """Mutation results expose only stable operation categories."""
    put_values = tuple(
        kind.value for kind in TicketAdmissionTelemetryStorePutKind
    )
    assert put_values == (
        "inserted",
        "unchanged",
    )
    assert tuple(
        kind.value for kind in TicketAdmissionTelemetryStoreRemoveKind
    ) == ("removed", "not-found")


def test_get_decodes_a_fresh_validated_document() -> None:
    """Lookup validates retained bytes instead of returning the input object."""
    document = _document()
    store = TicketAdmissionTelemetryMemoryStore()
    inserted = store.put(document)

    restored = store.get(inserted.document_fingerprint)

    assert restored == document
    assert restored is not document


def test_document_limit_failure_leaves_existing_state_unchanged() -> None:
    """A rejected unique insert cannot partially mutate counts or bytes."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    store = TicketAdmissionTelemetryMemoryStore(max_documents=ONE)
    _ = store.put(first)
    before = store.snapshot()

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document count exceeds configured limit",
    ):
        _ = store.put(second)

    assert store.snapshot() == before


def test_byte_limit_failure_leaves_existing_state_unchanged() -> None:
    """A rejected byte expansion cannot partially mutate retained state."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    first_byte_count = len(encode_ticket_admission_telemetry_document(first))
    store = TicketAdmissionTelemetryMemoryStore(
        max_total_bytes=first_byte_count,
    )
    _ = store.put(first)
    before = store.snapshot()

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="canonical bytes exceed configured limit",
    ):
        _ = store.put(second)

    assert store.snapshot() == before


def test_two_documents_publish_exact_total_byte_count() -> None:
    """Snapshot totals equal the sum of unique canonical document bytes."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    store = TicketAdmissionTelemetryMemoryStore()

    first_result = store.put(first)
    second_result = store.put(second)
    snapshot = store.snapshot()

    expected = (
        first_result.canonical_byte_count + second_result.canonical_byte_count
    )
    assert snapshot.document_count == DOCUMENT_PAIR_COUNT
    assert snapshot.total_canonical_byte_count == expected
    assert second_result.total_canonical_byte_count == expected


def test_fingerprint_collision_fails_closed_without_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct canonical bytes cannot share one retained store identity."""
    first = _document(elapsed_ns=LOW_ELAPSED_NS)
    second = _document(elapsed_ns=HIGH_ELAPSED_NS)
    constant = f"{FINGERPRINT_PREFIX}{"a" * 64}"

    def constant_fingerprint(canonical_bytes: bytes) -> str:
        del canonical_bytes
        return constant

    monkeypatch.setattr(store_module, "_fingerprint", constant_fingerprint)
    store = TicketAdmissionTelemetryMemoryStore()
    _ = store.put(first)
    before = store.snapshot()

    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="document fingerprint collision detected",
    ):
        _ = store.put(second)

    assert store.snapshot() == before
    assert store.get(constant) == first


def test_corrupted_retained_bytes_fail_closed_on_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lookup wraps retained canonical decode failure."""
    document = _document()
    store = TicketAdmissionTelemetryMemoryStore()
    inserted = store.put(document)

    def fail_decode(
        _canonical_bytes: bytes,
        *,
        max_bytes: int,
        max_observations: int = 4_096,
    ) -> TicketAdmissionTelemetryDocument:
        del _canonical_bytes, max_bytes, max_observations
        message = "corrupt retained bytes"
        raise TicketAdmissionTelemetryPersistenceError(message)

    monkeypatch.setattr(
        store_module,
        "decode_ticket_admission_telemetry_document",
        fail_decode,
    )
    with pytest.raises(
        TicketAdmissionTelemetryStoreError,
        match="retained telemetry document became invalid",
    ):
        _ = store.get(inserted.document_fingerprint)


def test_fingerprint_matches_existing_collection_identity() -> None:
    """The store reuses the established schema-v1 document identity."""
    document = _document()
    store = TicketAdmissionTelemetryMemoryStore()

    result = store.put(document)

    assert result.document_fingerprint == _fingerprint_for(document)
