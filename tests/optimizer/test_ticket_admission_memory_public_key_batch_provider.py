# File:
#   - test_ticket_admission_memory_public_key_batch_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_public_key_batch_provider.py
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
#   - Inline async batch-adapter regressions for bounded memory keys.
# - Must-Not:
#   - Require CUDA, files, network, tasks, concurrency, retry, secure
#     cryptography, certificates, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic services, batches, manifests, keys, and tampering.
#   - Outputs: inline-await, positional, integration, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when async HTTPS transports, credentials, hosted-service APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact inline batch adaptation.
# - Summary:
#   - Bounded memory-to-async-batch provider regressions.
# - Description:
#   - Proves positional memory lookups occur without hidden scheduling.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-request defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
#
# Large file:
#   - false
#

"""Inline async batch-adapter tests for bounded memory keys."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_batch_provider as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_batch_provider as batch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
MemoryBatchProvider = (
    adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider
)
BatchRequest = batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest
BatchResult = batch.TicketAdmissionTelemetryLineagePublicKeyBatchResult
PublicKeyRequest = provider.TicketAdmissionTelemetryLineagePublicKeyRequest
PublicKeyResult = provider.TicketAdmissionTelemetryLineagePublicKeyResult
ResultKind = provider.TicketAdmissionTelemetryLineagePublicKeyResultKind
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)

_resolve_batch_trust = (
    batch.resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch
)

ADAPTER_ID = (
    "bounded-memory-async-batch-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)
PROVIDER_ID = "provider.test.memory-batch-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
MANIFEST_FINGERPRINT = "manifest.test.fingerprint"
OTHER_MANIFEST_FINGERPRINT = "manifest.test.other-fingerprint"
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
RESULTS_FIELD = b"results="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2


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
    return memory.build_ticket_admission_telemetry_lineage_memory_public_key_provider(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _adapter(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    max_requests: int = (
        adapter.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_REQUESTS
    ),
    provider_id: str = PROVIDER_ID,
) -> MemoryBatchProvider:
    return adapter.build_ticket_admission_memory_public_key_batch_provider(
        _memory_provider(entries=entries, provider_id=provider_id),
        max_requests=max_requests,
    )


def _request(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str = MANIFEST_FINGERPRINT,
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
        manifest_fingerprint=manifest_fingerprint,
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


def _requests(*, same_key_id: bool = False) -> tuple[PublicKeyRequest, ...]:
    return (
        _request(),
        _request(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            request_index=1,
        ),
    )


def _batch_request(
    *,
    manifest_fingerprint: str = MANIFEST_FINGERPRINT,
    provider_id: str = PROVIDER_ID,
    requests: tuple[PublicKeyRequest, ...] | None = None,
) -> BatchRequest:
    return BatchRequest(
        manifest_fingerprint=manifest_fingerprint,
        provider_id=provider_id,
        requests=_requests() if requests is None else requests,
    )


def _manifest(
    *,
    same_key_id: bool = False,
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest((
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
    value: MemoryBatchProvider,
    request: BatchRequest,
) -> BatchResult:
    async def resolve() -> BatchResult:
        return await value(request)

    return asyncio.run(resolve())


def _resolved_trust(
    value: MemoryBatchProvider,
    *,
    manifest_value: (
        manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest | None
    ) = None,
) -> provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    async def resolve() -> (
        provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust
    ):
        return await _resolve_batch_trust(
            _manifest() if manifest_value is None else manifest_value,
            value,
            provider_id=PROVIDER_ID,
        )

    return asyncio.run(resolve())


def test_adapter_identity_and_metadata_are_stable() -> None:
    value = _adapter()

    assert (
        adapter.ticket_admission_memory_public_key_batch_provider_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.provider_id == PROVIDER_ID
    assert value.key_count == TWO_KEYS
    assert value.max_requests == (
        adapter.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_REQUESTS
    )
    assert (
        adapter.validate_ticket_admission_memory_public_key_batch_provider(
            value
        )
        is value
    )


def test_adapter_and_batch_result_hide_public_key_bytes() -> None:
    value = _adapter()
    result = _direct_result(value, _batch_request())

    adapter_repr = repr(value).encode("utf-8")
    result_repr = repr(result).encode("utf-8")
    assert OLD_PUBLIC_KEY not in adapter_repr
    assert NEW_PUBLIC_KEY not in adapter_repr
    assert PUBLIC_KEY_FIELD not in adapter_repr
    assert PROVIDER_FIELD not in adapter_repr
    assert OLD_PUBLIC_KEY not in result_repr
    assert NEW_PUBLIC_KEY not in result_repr
    assert RESULTS_FIELD not in result_repr


def test_direct_batch_resolves_exact_positional_results() -> None:
    result = _direct_result(_adapter(), _batch_request())

    assert tuple(item.kind for item in result.results) == (
        ResultKind.RESOLVED,
        ResultKind.RESOLVED,
    )
    assert tuple(item.public_key for item in result.results) == (
        OLD_PUBLIC_KEY,
        NEW_PUBLIC_KEY,
    )


def test_direct_batch_preserves_mixed_typed_results() -> None:
    requests = (
        _request(public_key_reference_id=UNKNOWN_REFERENCE_ID),
        _request(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=OLD_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
            request_index=1,
        ),
    )

    result = _direct_result(_adapter(), _batch_request(requests=requests))

    assert result.results == (
        PublicKeyResult(kind=ResultKind.UNAVAILABLE),
        PublicKeyResult(kind=ResultKind.FAILED),
    )


def test_empty_direct_batch_returns_empty_positional_result() -> None:
    result = _direct_result(_adapter(), _batch_request(requests=()))

    assert result == BatchResult(results=())


def test_await_completes_without_internal_scheduling_point() -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> BatchResult:
        task = asyncio.create_task(marker())
        result = await _adapter()(_batch_request())
        assert events == []
        await task
        return result

    result = asyncio.run(resolve())

    assert len(result.results) == TWO_KEYS
    assert events == ["marker"]


def test_batch_boundary_builds_manifest_bound_trust() -> None:
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


def test_repeated_batch_resolution_reuses_only_explicit_memory_state() -> None:
    value = _adapter()

    first = _resolved_trust(value)
    second = _resolved_trust(value)

    assert first == second
    assert (
        adapter.validate_ticket_admission_memory_public_key_batch_provider(
            value
        )
        is value
    )


def test_same_key_id_under_distinct_algorithms_resolves_exactly() -> None:
    value = _adapter(entries=_entries(same_key_id=True))
    resolved = _resolved_trust(
        value, manifest_value=_manifest(same_key_id=True)
    )

    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.trust.key_count == TWO_KEYS


def test_builder_rejects_foreign_memory_provider_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-provider type"):
        _ = adapter.build_ticket_admission_memory_public_key_batch_provider(
            cast("MemoryProvider", object())
        )


@pytest.mark.parametrize("max_requests", [0, True])
def test_builder_rejects_invalid_request_limit(max_requests: int) -> None:
    with pytest.raises(AdapterError, match="positive integer"):
        _ = _adapter(max_requests=max_requests)


def test_builder_rejects_tampered_memory_provider() -> None:
    value = replace(_memory_provider(), service_id="unsupported")

    with pytest.raises(AdapterError, match="service identity is unsupported"):
        _ = adapter.build_ticket_admission_memory_public_key_batch_provider(
            value
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-batch type"):
        _ = adapter.validate_ticket_admission_memory_public_key_batch_provider(
            cast("MemoryBatchProvider", object())
        )


def test_tampered_adapter_identity_fails_before_batch_lookup() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value, _batch_request())


@pytest.mark.parametrize("key_count", [-1, True])
def test_tampered_adapter_key_count_type_fails_before_batch_lookup(
    key_count: int,
) -> None:
    value = replace(_adapter(), key_count=key_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value, _batch_request())


def test_tampered_adapter_key_count_binding_fails_before_batch_lookup() -> None:
    value = replace(_adapter(), key_count=1)

    with pytest.raises(AdapterError, match="does not match provider"):
        _ = _direct_result(value, _batch_request())


@pytest.mark.parametrize("max_requests", [0, True])
def test_tampered_adapter_request_limit_fails_before_batch_lookup(
    max_requests: int,
) -> None:
    value = replace(_adapter(), max_requests=max_requests)

    with pytest.raises(AdapterError, match="positive integer"):
        _ = _direct_result(value, _batch_request())


def test_tampered_adapter_provider_identity_fails_before_batch_lookup() -> None:
    value = replace(_adapter(), provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _direct_result(value, _batch_request())


def test_tampered_adapter_provider_type_fails_before_batch_lookup() -> None:
    value = replace(_adapter(), provider=cast("MemoryProvider", object()))

    with pytest.raises(AdapterError, match="exact memory-provider type"):
        _ = _direct_result(value, _batch_request())


def test_tampered_wrapped_key_bytes_fail_before_batch_lookup() -> None:
    service = _memory_provider()
    changed = replace(service.entries[0], public_key=WRONG_PUBLIC_KEY)
    tampered = replace(service, entries=(changed, service.entries[1]))
    value = replace(_adapter(), provider=tampered)

    with pytest.raises(AdapterError, match="does not match exact key bytes"):
        _ = _direct_result(value, _batch_request())


def test_foreign_batch_request_type_fails_closed() -> None:
    with pytest.raises(AdapterError, match="exact batch request type"):
        _ = _direct_result(_adapter(), cast("BatchRequest", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "manifest_fingerprint",
            "",
            "manifest fingerprint must be a nonempty string",
        ),
        (
            "provider_id",
            "",
            "provider identity must be a nonempty string",
        ),
    ],
)
def test_batch_shape_requires_nonempty_metadata(
    field: str,
    value: str,
    match: str,
) -> None:
    request = replace(_batch_request(), **{field: value})

    with pytest.raises(AdapterError, match=match):
        _ = _direct_result(_adapter(), request)


def test_batch_provider_identity_must_match_adapter() -> None:
    request = _batch_request(provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="does not match adapter"):
        _ = _direct_result(_adapter(), request)


def test_batch_requests_require_exact_tuple() -> None:
    request = replace(
        _batch_request(),
        requests=cast(
            "tuple[PublicKeyRequest, ...]",
            cast("object", list(_requests())),
        ),
    )

    with pytest.raises(AdapterError, match="exact immutable tuple"):
        _ = _direct_result(_adapter(), request)


def test_batch_request_count_is_bounded_before_item_lookup() -> None:
    value = _adapter(max_requests=1)

    with pytest.raises(AdapterError, match="request count exceeds"):
        _ = _direct_result(value, _batch_request())


def test_foreign_batch_item_type_fails_closed() -> None:
    request = _batch_request(
        requests=cast(
            "tuple[PublicKeyRequest, ...]",
            cast("object", (object(),)),
        )
    )

    with pytest.raises(
        AdapterError, match="index 0 must use exact request type"
    ):
        _ = _direct_result(_adapter(), request)


def test_batch_item_index_must_match_position() -> None:
    changed = replace(_requests()[0], request_index=1)
    request = _batch_request(requests=(changed,))

    with pytest.raises(AdapterError, match="does not match position 0"):
        _ = _direct_result(_adapter(), request)


def test_batch_item_provider_must_match_batch() -> None:
    changed = replace(_requests()[0], provider_id=OTHER_PROVIDER_ID)
    request = _batch_request(requests=(changed,))

    with pytest.raises(
        AdapterError, match="provider does not match at index 0"
    ):
        _ = _direct_result(_adapter(), request)


def test_batch_item_manifest_must_match_batch() -> None:
    changed = replace(
        _requests()[0],
        manifest_fingerprint=OTHER_MANIFEST_FINGERPRINT,
    )
    request = _batch_request(requests=(changed,))

    with pytest.raises(
        AdapterError, match="manifest does not match at index 0"
    ):
        _ = _direct_result(_adapter(), request)


def test_batch_boundary_fails_on_unavailable_memory_result() -> None:
    value = _adapter(entries=())

    with pytest.raises(
        batch.TicketAdmissionTelemetryLineagePublicKeyBatchProviderError,
        match="provider returned unavailable at index 0",
    ):
        _ = _resolved_trust(value)


def test_batch_boundary_fails_on_failed_memory_result() -> None:
    changed = replace(
        _entry(),
        first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        last_capture_sequence_id=None,
    )
    value = _adapter(entries=(changed, _entries()[0]))

    with pytest.raises(
        batch.TicketAdmissionTelemetryLineagePublicKeyBatchProviderError,
        match="provider returned failed at index 0",
    ):
        _ = _resolved_trust(value)


def test_batch_boundary_wraps_adapter_provider_identity_error() -> None:
    value = _adapter(provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(
        batch.TicketAdmissionTelemetryLineagePublicKeyBatchProviderError,
        match="batch provider raised during resolution",
    ):
        _ = _resolved_trust(value)


def test_custom_limit_allows_matching_single_request() -> None:
    value = _adapter(max_requests=1)
    request = _batch_request(requests=(_requests()[0],))

    result = _direct_result(value, request)

    assert result.results == (
        PublicKeyResult(kind=ResultKind.RESOLVED, public_key=OLD_PUBLIC_KEY),
    )


def test_empty_memory_service_adapter_metadata_remains_exact() -> None:
    value = _adapter(entries=())

    assert value.key_count == 0
    assert value.provider_id == PROVIDER_ID
    assert (
        adapter.validate_ticket_admission_memory_public_key_batch_provider(
            value
        )
        is value
    )
