# File:
#   - test_ticket_admission_memory_async_public_key_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_async_public_key_provider.py
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
#   - Inline async adapter regressions for the bounded memory key provider.
# - Must-Not:
#   - Require CUDA, files, network, hidden tasks, retry, secure cryptography,
#     certificates, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic memory services, requests, manifests, and tampering.
#   - Outputs: inline-await, integration, metadata, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when concrete network transports gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact inline async adaptation.
# - Summary:
#   - Bounded memory-to-sequential-async provider regressions.
# - Description:
#   - Proves awaiting retains exact synchronous validation without scheduling.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-key defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
#
# Large file:
#   - false
#

"""Inline async adapter tests for the bounded memory key provider."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_async_public_key_provider as async_port,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_async_public_key_provider as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_memory_public_key_provider import (
    validate_ticket_admission_telemetry_lineage_memory_public_key_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust_manifest import (
    build_ticket_admission_telemetry_lineage_signature_trust_manifest,
)

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProviderError
)
MemoryProviderError = (
    memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
MemoryAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider
)
PublicKeyRequest = provider.TicketAdmissionTelemetryLineagePublicKeyRequest
PublicKeyResult = provider.TicketAdmissionTelemetryLineagePublicKeyResult
ResultKind = provider.TicketAdmissionTelemetryLineagePublicKeyResultKind
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
build_memory = (
    memory.build_ticket_admission_telemetry_lineage_memory_public_key_provider
)
resolve_async = (
    async_port.resolve_ticket_admission_telemetry_lineage_signature_trust_async
)

ADAPTER_ID = (
    "bounded-in-memory-async-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)
PROVIDER_ID = "provider.test.memory-async-public-keys"
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
PROVIDER_FIELD = b"provider="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2


def _build_adapter(
    value: MemoryProvider,
) -> MemoryAsyncProvider:
    return adapter.build_ticket_admission_memory_async_public_key_provider(
        value
    )


def _validate_adapter(
    value: MemoryAsyncProvider,
) -> MemoryAsyncProvider:
    return adapter.validate_ticket_admission_memory_async_public_key_provider(
        value
    )


def _validate_memory(value: MemoryProvider) -> MemoryProvider:
    return (
        validate_ticket_admission_telemetry_lineage_memory_public_key_provider(
            value
        )
    )


def _build_manifest(
    entries: tuple[ManifestEntry, ...],
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return build_ticket_admission_telemetry_lineage_signature_trust_manifest(
        entries
    )


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
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
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _entries(*, same_key_id: bool = False) -> tuple[MemoryEntry, ...]:
    return (
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(),
    )


def _memory_provider(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> MemoryProvider:
    return build_memory(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _adapter(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
) -> MemoryAsyncProvider:
    return _build_adapter(_memory_provider(entries=entries))


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


def _manifest(
    *,
    same_key_id: bool = False,
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return _build_manifest((
        ManifestEntry(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
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


def _direct_result(
    value: MemoryAsyncProvider,
    request: PublicKeyRequest,
) -> PublicKeyResult:
    async def resolve() -> PublicKeyResult:
        return await value(request)

    return asyncio.run(resolve())


def _resolved_trust(
    value: MemoryAsyncProvider,
    *,
    manifest_value: (
        manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest | None
    ) = None,
) -> provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    async def resolve() -> (
        provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust
    ):
        return await resolve_async(
            _manifest() if manifest_value is None else manifest_value,
            value,
            provider_id=PROVIDER_ID,
        )

    return asyncio.run(resolve())


def test_adapter_identity_and_metadata_are_stable() -> None:
    value = _adapter()

    assert (
        adapter.ticket_admission_telemetry_lineage_memory_async_public_key_provider_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.provider_id == PROVIDER_ID
    assert value.key_count == TWO_KEYS
    assert _validate_adapter(value) is value


def test_adapter_and_wrapped_service_hide_public_key_bytes() -> None:
    value = _adapter()

    representation = repr(value).encode("utf-8")
    assert OLD_PUBLIC_KEY not in representation
    assert NEW_PUBLIC_KEY not in representation
    assert PUBLIC_KEY_FIELD not in representation
    assert PROVIDER_FIELD not in representation


def test_direct_await_resolves_exact_request() -> None:
    result = _direct_result(_adapter(), _request())

    assert result.kind is ResultKind.RESOLVED
    assert result.public_key == OLD_PUBLIC_KEY


def test_direct_await_returns_unavailable_for_unknown_reference() -> None:
    result = _direct_result(
        _adapter(),
        _request(public_key_reference_id=UNKNOWN_REFERENCE_ID),
    )

    assert result == PublicKeyResult(kind=ResultKind.UNAVAILABLE)


def test_direct_await_returns_failed_for_metadata_mismatch() -> None:
    result = _direct_result(
        _adapter(),
        _request(public_key_id=NEW_KEY_ID),
    )

    assert result == PublicKeyResult(kind=ResultKind.FAILED)


def test_await_completes_without_internal_scheduling_point() -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> PublicKeyResult:
        task = asyncio.create_task(marker())
        result = await _adapter()(_request())
        assert events == []
        await task
        return result

    result = asyncio.run(resolve())

    assert result.kind is ResultKind.RESOLVED
    assert events == ["marker"]


def test_sequential_async_boundary_builds_manifest_bound_trust() -> None:
    resolved = _resolved_trust(_adapter())

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_KEYS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.public_key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert resolved.trust.key_count == TWO_KEYS


def test_repeated_async_resolution_reuses_only_explicit_memory_state() -> None:
    value = _adapter()

    first = _resolved_trust(value)
    second = _resolved_trust(value)

    assert first == second
    assert _validate_adapter(value) is value


def test_empty_manifest_makes_no_adapter_lookup() -> None:
    empty = _build_manifest(())
    resolved = _resolved_trust(_adapter(), manifest_value=empty)

    assert resolved.request_count == 0
    assert resolved.trust.key_count == 0


def test_empty_memory_service_returns_unavailable_directly() -> None:
    result = _direct_result(_adapter(entries=()), _request())

    assert result.kind is ResultKind.UNAVAILABLE
    assert result.public_key is None


def test_same_key_id_under_distinct_algorithms_resolves_exactly() -> None:
    value = _build_adapter(_memory_provider(entries=_entries(same_key_id=True)))
    resolved = _resolved_trust(
        value, manifest_value=_manifest(same_key_id=True)
    )

    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.trust.key_count == TWO_KEYS


def test_public_memory_validator_returns_exact_service() -> None:
    value = _memory_provider()

    assert _validate_memory(value) is value


def test_builder_rejects_foreign_memory_provider_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-provider type"):
        _ = _build_adapter(cast("MemoryProvider", object()))


def test_builder_rejects_tampered_memory_provider() -> None:
    value = replace(_memory_provider(), service_id="unsupported")

    with pytest.raises(AdapterError, match="service identity is unsupported"):
        _ = _build_adapter(value)


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-async type"):
        _ = _validate_adapter(cast("MemoryAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value, _request())


@pytest.mark.parametrize("key_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_lookup(
    key_count: int,
) -> None:
    value = replace(_adapter(), key_count=key_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_count_binding_fails_before_lookup() -> None:
    value = replace(_adapter(), key_count=1)

    with pytest.raises(AdapterError, match="does not match provider"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_provider_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_provider_type_fails_before_lookup() -> None:
    value = replace(
        _adapter(),
        provider=cast("MemoryProvider", object()),
    )

    with pytest.raises(AdapterError, match="exact memory-provider type"):
        _ = _direct_result(value, _request())


def test_tampered_wrapped_key_bytes_fail_recomputed_fingerprint() -> None:
    service = _memory_provider()
    changed = replace(service.entries[0], public_key=WRONG_PUBLIC_KEY)
    tampered_service = replace(
        service,
        entries=(changed, service.entries[1]),
    )
    value = replace(_adapter(), provider=tampered_service)

    with pytest.raises(AdapterError, match="does not match exact key bytes"):
        _ = _direct_result(value, _request())


def test_direct_provider_identity_mismatch_preserves_memory_error() -> None:
    with pytest.raises(MemoryProviderError, match="does not match service"):
        _ = _direct_result(
            _adapter(),
            _request(provider_id=OTHER_PROVIDER_ID),
        )


def test_async_boundary_wraps_provider_identity_mismatch_stably() -> None:
    value = _build_adapter(_memory_provider(provider_id=OTHER_PROVIDER_ID))

    with pytest.raises(
        async_port.TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError,
        match="provider raised during request index 0",
    ):
        _ = _resolved_trust(value)


def test_async_boundary_stops_on_typed_failed_result() -> None:
    changed = replace(
        _entry(),
        first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        last_capture_sequence_id=None,
    )
    value = _adapter(entries=(changed, _entries()[0]))

    with pytest.raises(
        async_port.TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError,
        match="provider returned failed at request index 0",
    ):
        _ = _resolved_trust(value)


def test_direct_foreign_request_type_fails_closed() -> None:
    with pytest.raises(
        MemoryProviderError, match="exact public-key request type"
    ):
        _ = _direct_result(
            _adapter(),
            cast("PublicKeyRequest", object()),
        )


def test_empty_service_adapter_metadata_remains_exact() -> None:
    value = _adapter(entries=())

    assert value.key_count == 0
    assert value.provider_id == PROVIDER_ID
    assert _validate_adapter(value) is value
