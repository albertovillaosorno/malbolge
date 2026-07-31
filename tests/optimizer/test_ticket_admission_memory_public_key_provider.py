# File:
#   - test_ticket_admission_memory_public_key_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_public_key_provider.py
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
#   - Bounded caller-owned in-memory public-key provider regressions.
# - Must-Not:
#   - Require CUDA, files, network, discovery, retry, secure cryptography, or
#     admission-policy changes.
# - Allows:
#   - Inputs: synthetic entries, requests, manifests, keys, and tampering.
#   - Outputs: ordering, resolution, integrity, and fail-closed assertions.
#   - Side effects: none beyond explicit in-process calls.
# - Split-When:
#   - Split when batch/session adapters, external services, certificates,
#     or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-provider behavior.
# - Summary:
#   - Exact bounded memory-provider implementation regressions.
# - Description:
#   - Proves caller-owned key bytes remain exact and revalidated on every use.
# - Usage:
#   - Runs without accelerator hardware or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and a 256-key default.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Bounded caller-owned in-memory public-key provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

ServiceError = (
    memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
PublicKeyRequest = provider.TicketAdmissionTelemetryLineagePublicKeyRequest
PublicKeyResult = provider.TicketAdmissionTelemetryLineagePublicKeyResult
ResultKind = provider.TicketAdmissionTelemetryLineagePublicKeyResultKind
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
build_memory = (
    memory.build_ticket_admission_telemetry_lineage_memory_public_key_provider
)
build_manifest = (
    manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)

SERVICE_PREFIX = "bounded-in-memory-ticket-admission-"
SERVICE_SUFFIX = "telemetry-lineage-public-key-provider-v1"
SERVICE_ID = f"{SERVICE_PREFIX}{SERVICE_SUFFIX}"
PROVIDER_ID = "provider.test.memory-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
MANIFEST_FINGERPRINT = "manifest.test.fingerprint"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.public-key.unknown"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_FIELD = b"public_key=b"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _memory_entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_fingerprint: str | None = None,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
) -> MemoryEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return MemoryEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key=public_key,
        public_key_fingerprint=(
            _fingerprint(public_key)
            if public_key_fingerprint is None
            else public_key_fingerprint
        ),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _entries(*, same_key_id: bool = False) -> tuple[MemoryEntry, ...]:
    return (
        _memory_entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _memory_entry(),
    )


def _service(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> MemoryProvider:
    return build_memory(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _request(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    provider_id: str = PROVIDER_ID,
    public_key_fingerprint: str | None = None,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    request_index: int = 0,
) -> PublicKeyRequest:
    return PublicKeyRequest(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=MANIFEST_FINGERPRINT,
        provider_id=provider_id,
        public_key_fingerprint=(
            _fingerprint(OLD_PUBLIC_KEY)
            if public_key_fingerprint is None
            else public_key_fingerprint
        ),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
        request_index=request_index,
    )


def _manifest() -> (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest
):
    return build_manifest((
        ManifestEntry(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
        ManifestEntry(
            algorithm_id=OLD_ALGORITHM_ID,
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
            public_key_fingerprint=_fingerprint(OLD_PUBLIC_KEY),
            public_key_id=OLD_KEY_ID,
            public_key_reference_id=OLD_REFERENCE_ID,
        ),
    ))


def _resolve_manifest(
    service: MemoryProvider,
) -> provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    return resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        _manifest(),
        service,
        provider_id=PROVIDER_ID,
    )


def test_service_identity_and_empty_provider_are_stable() -> None:
    service = _service(entries=())

    result = service(_request(public_key_reference_id=UNKNOWN_REFERENCE_ID))

    assert (
        memory.ticket_admission_telemetry_lineage_memory_public_key_provider_id()
        == SERVICE_ID
    )
    assert service.service_id == SERVICE_ID
    assert service.key_count == 0
    assert service.entries == ()
    assert result.kind is ResultKind.UNAVAILABLE
    assert result.public_key is None


def test_entries_are_sorted_by_reference_and_hide_key_bytes() -> None:
    service = _service()

    service_repr = repr(service).encode("utf-8")
    entry_repr = repr(service.entries[0]).encode("utf-8")
    assert tuple(
        entry.public_key_reference_id for entry in service.entries
    ) == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert OLD_PUBLIC_KEY not in service_repr
    assert NEW_PUBLIC_KEY not in service_repr
    assert OLD_PUBLIC_KEY not in entry_repr
    assert PUBLIC_KEY_FIELD not in service_repr
    assert PUBLIC_KEY_FIELD not in entry_repr


def test_exact_request_returns_resolved_hidden_bytes() -> None:
    result = _service()(_request())

    assert result.kind is ResultKind.RESOLVED
    assert result.public_key == OLD_PUBLIC_KEY
    assert OLD_PUBLIC_KEY not in repr(result).encode("utf-8")


def test_unknown_reference_returns_unavailable() -> None:
    result = _service()(_request(public_key_reference_id=UNKNOWN_REFERENCE_ID))

    assert result == PublicKeyResult(kind=ResultKind.UNAVAILABLE)


@pytest.mark.parametrize(
    "request_case",
    [
        _request(algorithm_id=NEW_ALGORITHM_ID),
        _request(public_key_id=NEW_KEY_ID),
        _request(public_key_fingerprint=_fingerprint(WRONG_PUBLIC_KEY)),
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
        ),
        _request(last_capture_sequence_id=SUCCESSOR_SEQUENCE_ID),
    ],
)
def test_reference_metadata_mismatch_returns_failed(
    request_case: PublicKeyRequest,
) -> None:
    result = _service()(request_case)

    assert result == PublicKeyResult(kind=ResultKind.FAILED)


def test_provider_identity_mismatch_fails_before_lookup() -> None:
    with pytest.raises(ServiceError, match="does not match service"):
        _ = _service()(_request(provider_id=OTHER_PROVIDER_ID))


def test_same_key_id_under_distinct_algorithms_is_allowed() -> None:
    service = _service(entries=_entries(same_key_id=True))
    request = _request(
        algorithm_id=NEW_ALGORITHM_ID,
        first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        last_capture_sequence_id=None,
        public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
        public_key_id=OLD_KEY_ID,
        public_key_reference_id=NEW_REFERENCE_ID,
        request_index=1,
    )

    result = service(request)

    assert service.key_count == TWO_KEYS
    assert result.kind is ResultKind.RESOLVED
    assert result.public_key == NEW_PUBLIC_KEY


def test_sync_provider_port_builds_manifest_bound_trust() -> None:
    resolved = _resolve_manifest(_service())

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_KEYS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.public_key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert resolved.trust.key_count == TWO_KEYS


def test_empty_service_causes_stable_unavailable_provider_failure() -> None:
    with pytest.raises(
        provider.TicketAdmissionTelemetryLineagePublicKeyProviderError,
        match="provider returned unavailable at request index 0",
    ):
        _ = _resolve_manifest(_service(entries=()))


def test_mismatched_service_entry_causes_stable_failed_provider_result() -> (
    None
):
    changed = replace(
        _memory_entry(),
        first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        last_capture_sequence_id=None,
    )
    service = _service(entries=(changed, _entries()[0]))

    with pytest.raises(
        provider.TicketAdmissionTelemetryLineagePublicKeyProviderError,
        match="provider returned failed at request index 0",
    ):
        _ = _resolve_manifest(service)


def test_entries_require_exact_immutable_tuple() -> None:
    with pytest.raises(ServiceError, match="exact immutable tuple"):
        _ = build_memory(
            cast("tuple[MemoryEntry, ...]", cast("object", list(_entries()))),
            provider_id=PROVIDER_ID,
        )


@pytest.mark.parametrize("max_keys", [0, True])
def test_key_limit_must_be_positive_exact_integer(max_keys: int) -> None:
    with pytest.raises(ServiceError, match="positive integer"):
        _ = build_memory((), provider_id=PROVIDER_ID, max_keys=max_keys)


def test_key_count_is_bounded_before_entry_validation() -> None:
    entries = tuple(
        _memory_entry(public_key_reference_id=f"ref.{index}")
        for index in range(2)
    )

    with pytest.raises(ServiceError, match="key count exceeds"):
        _ = build_memory(entries, provider_id=PROVIDER_ID, max_keys=1)


@pytest.mark.parametrize(
    "provider_id", ["bad provider", "", cast("str", object())]
)
def test_provider_identity_must_be_canonical(provider_id: str) -> None:
    with pytest.raises(ServiceError, match="provider identity must use"):
        _ = build_memory((), provider_id=provider_id)


def test_duplicate_composite_identity_fails_closed() -> None:
    duplicate = replace(
        _memory_entry(),
        public_key_reference_id=NEW_REFERENCE_ID,
    )

    with pytest.raises(
        ServiceError, match="duplicate algorithm and public-key"
    ):
        _ = _service(entries=(_memory_entry(), duplicate))


def test_duplicate_reference_identity_fails_closed() -> None:
    duplicate = _memory_entry(
        algorithm_id=NEW_ALGORITHM_ID,
        public_key=NEW_PUBLIC_KEY,
        public_key_id=NEW_KEY_ID,
    )

    with pytest.raises(ServiceError, match="duplicate public-key reference"):
        _ = _service(entries=(_memory_entry(), duplicate))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("algorithm_id", "bad algorithm", "algorithm identity must use"),
        ("public_key_id", "", "public-key identity must use"),
        (
            "public_key_reference_id",
            "bad reference",
            "public-key reference identity must use",
        ),
        (
            "first_capture_sequence_id",
            -1,
            "first capture sequence identity must be nonnegative",
        ),
        (
            "last_capture_sequence_id",
            -1,
            "last capture sequence identity must be absent or ordered",
        ),
    ],
)
def test_entry_metadata_is_validated(
    field: str,
    value: object,
    match: str,
) -> None:
    entry = replace(_memory_entry(), **{field: value})

    with pytest.raises(ServiceError, match=match):
        _ = _service(entries=(entry,))


@pytest.mark.parametrize(
    ("public_key", "match"),
    [
        pytest.param(b"", "public key cannot be empty", id="empty"),
        pytest.param(
            cast("bytes", cast("object", bytearray(OLD_PUBLIC_KEY))),
            "public key must use the exact bytes type",
            id="foreign-bytes",
        ),
    ],
)
def test_entry_public_key_is_validated(
    public_key: bytes,
    match: str,
) -> None:
    entry = replace(_memory_entry(), public_key=public_key)

    with pytest.raises(ServiceError, match=match):
        _ = _service(entries=(entry,))


def test_oversized_entry_public_key_is_rejected() -> None:
    oversized = b"x" * (DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES + 1)
    entry = replace(_memory_entry(), public_key=oversized)

    with pytest.raises(
        ServiceError, match="public key exceeds configured byte limit"
    ):
        _ = _service(entries=(entry,))


def test_entry_fingerprint_must_match_exact_key_bytes() -> None:
    entry = _memory_entry(
        public_key_fingerprint=_fingerprint(WRONG_PUBLIC_KEY),
    )

    with pytest.raises(ServiceError, match="does not match exact key bytes"):
        _ = _service(entries=(entry,))


def test_foreign_entry_type_fails_closed() -> None:
    with pytest.raises(ServiceError, match="exact memory-provider entry type"):
        _ = _service(
            entries=cast(
                "tuple[MemoryEntry, ...]",
                (object(),),
            )
        )


def test_foreign_request_type_fails_closed() -> None:
    with pytest.raises(ServiceError, match="exact public-key request type"):
        _ = _service()(cast("PublicKeyRequest", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("algorithm_id", "bad algorithm", "request algorithm identity"),
        ("provider_id", "bad provider", "request provider identity"),
        ("public_key_id", "", "request public-key identity"),
        (
            "public_key_reference_id",
            "bad reference",
            "request public-key reference identity",
        ),
        (
            "first_capture_sequence_id",
            -1,
            "first capture sequence identity",
        ),
        ("request_index", -1, "request index must be a nonnegative"),
        ("manifest_fingerprint", "", "manifest fingerprint must be a nonempty"),
        (
            "public_key_fingerprint",
            "",
            "public-key fingerprint must be a nonempty",
        ),
    ],
)
def test_request_shape_is_validated(
    field: str,
    value: object,
    match: str,
) -> None:
    request = replace(_request(), **{field: value})

    with pytest.raises(ServiceError, match=match):
        _ = _service()(request)


def test_tampered_service_identity_fails_on_use() -> None:
    service = replace(_service(), service_id="unsupported")

    with pytest.raises(ServiceError, match="service identity is unsupported"):
        _ = service(_request())


def test_tampered_service_count_fails_on_use() -> None:
    service = replace(_service(), key_count=1)

    with pytest.raises(ServiceError, match="key count does not match"):
        _ = service(_request())


def test_tampered_service_order_fails_on_use() -> None:
    service = _service()
    reversed_service = replace(
        service, entries=tuple(reversed(service.entries))
    )

    with pytest.raises(ServiceError, match="not uniquely reference ordered"):
        _ = reversed_service(_request())


def test_tampered_service_key_bytes_fail_recomputed_fingerprint() -> None:
    service = _service()
    changed = replace(service.entries[0], public_key=WRONG_PUBLIC_KEY)
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(ServiceError, match="does not match exact key bytes"):
        _ = tampered(_request())


def test_tampered_service_provider_identity_fails_on_use() -> None:
    service = replace(_service(), provider_id="bad provider")

    with pytest.raises(ServiceError, match="provider identity must use"):
        _ = service(_request())
