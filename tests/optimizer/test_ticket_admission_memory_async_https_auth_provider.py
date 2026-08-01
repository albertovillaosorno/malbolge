# File:
#   - test_ticket_admission_memory_async_https_auth_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_async_https_auth_provider.py
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
#   - Inline async adapter regressions for the bounded memory auth provider.
# - Must-Not:
#   - Read environment, files, network, secret stores, create hidden tasks,
#     refresh, retry, persist, log values, use async plugins, or change policy.
# - Allows:
#   - Inputs: synthetic memory services, requests, integrations, and tampering.
#   - Outputs: inline-await, metadata, secrecy, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-auth async adaptation.
# - Summary:
#   - Bounded memory-to-async HTTPS Authorization provider regressions.
# - Description:
#   - Proves awaiting retains exact synchronous validation without scheduling.
# - Usage:
#   - Runs without sockets, files, environment access, or accelerator hardware.
# - Defaults:
#   - Uses two synthetic Authorization entries and the 64-entry default.
#
# Related documents:
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Inline async adapter tests for the bounded memory auth provider."""


# ruff: file-ignore[undocumented-public-function]
# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

import asyncio
from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

import pytest

from accelerator import (
    ticket_admission_memory_async_https_auth_provider as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_async_https_auth_provider as async_auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_https_auth_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProviderError
)
MemoryAuthError = (
    memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthorization
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider
MemoryAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider
)
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthKind = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
ResolvedAuth = auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_build_memory = (
    memory.build_ticket_admission_memory_https_authorization_provider
)
_build_adapter = (
    adapter.build_ticket_admission_memory_async_https_authorization_provider
)
_validate_adapter = (
    adapter.validate_ticket_admission_memory_async_https_authorization_provider
)
_resolve_async = async_auth.resolve_ticket_admission_https_authorization_async
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher

ADAPTER_ID = (
    "memory-async-ticket-admission-lineage-https-authorization-provider-v1"
)
AUTH_PROVIDER_ID = "credential-provider.test.memory-async-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.memory-async-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.memory-async-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.memory-async-auth-key-service-a"
SOURCE_B = "source.test.memory-async-auth-key-service-b"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/a.json"
FINGERPRINT_A = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("0" * 64)
)
FINGERPRINT_B = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("1" * 64)
)
AUTHORIZATION_A = "Bearer caller-owned-memory-async-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
AUTHORIZATION_FIELD = b"authorization_value"
PROVIDER_FIELD = b"provider="
DEFAULT_MAX_ENTRIES = 64
TWO_ENTRIES = 2
ONE_ENTRY = 1


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    authorization_value: str = AUTHORIZATION_A,
    bundle_fingerprint: str = FINGERPRINT_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> MemoryEntry:
    return MemoryEntry(
        authorization_byte_count=len(authorization_value.encode("ascii")),
        authorization_value=authorization_value,
        bundle_fingerprint=bundle_fingerprint,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _entries() -> tuple[MemoryEntry, ...]:
    return (
        _entry(),
        _entry(
            authorization_value=AUTHORIZATION_B,
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        ),
    )


def _memory_provider(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    provider_id: str = AUTH_PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> MemoryProvider:
    return _build_memory(
        _entries() if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
    )


def _adapter(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
) -> MemoryAsyncProvider:
    return _build_adapter(_memory_provider(entries=entries))


def _auth_request(  # ruff: ignore[too-many-arguments]
    *,
    authorization_provider_id: str = AUTH_PROVIDER_ID,
    bundle_fingerprint: str = FINGERPRINT_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> AuthRequest:
    return AuthRequest(
        authorization_provider_id=authorization_provider_id,
        bundle_fingerprint=bundle_fingerprint,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _https_fetcher() -> HttpsFetcher:
    return _build_https(
        HttpsConfig(
            host=HOST,
            resource_id=RESOURCE_A,
            source_id=SOURCE_A,
            target=TARGET,
            tls_context=_tls_context(),
        )
    )


def _fetch_request() -> FetchRequest:
    return FetchRequest(
        bundle_fingerprint=FINGERPRINT_A,
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=FETCH_PROVIDER_A,
        resource_id=RESOURCE_A,
        source_id=SOURCE_A,
    )


def _direct_result(
    value: MemoryAsyncProvider,
    request: AuthRequest,
) -> AuthResult:
    async def resolve() -> AuthResult:
        return await value(request)

    return asyncio.run(resolve())


def _resolved_authorization(
    value: MemoryAsyncProvider,
) -> ResolvedAuth:
    return asyncio.run(
        _resolve_async(
            _https_fetcher(),
            _fetch_request(),
            value,
            authorization_provider_id=AUTH_PROVIDER_ID,
        )
    )


def test_adapter_identity_and_metadata_are_stable() -> None:
    value = _adapter()

    assert (
        adapter.ticket_admission_memory_async_https_authorization_provider_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.entry_count == TWO_ENTRIES
    assert value.max_entries == DEFAULT_MAX_ENTRIES
    assert value.provider_id == AUTH_PROVIDER_ID
    assert _validate_adapter(value) is value


def test_adapter_and_wrapped_service_hide_authorization_values() -> None:
    value = _adapter()
    representation = repr(value).encode("utf-8")

    assert AUTHORIZATION_A.encode() not in representation
    assert AUTHORIZATION_B.encode() not in representation
    assert AUTHORIZATION_FIELD not in representation
    assert PROVIDER_FIELD not in representation


def test_direct_await_resolves_exact_request() -> None:
    result = _direct_result(_adapter(), _auth_request())

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A


def test_direct_await_returns_unavailable_for_unknown_binding() -> None:
    result = _direct_result(
        _adapter(),
        _auth_request(resource_id=RESOURCE_B),
    )

    assert result == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_direct_await_returns_failed_for_provider_mismatch() -> None:
    result = _direct_result(
        _adapter(),
        _auth_request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID),
    )

    assert result == AuthResult(kind=AuthKind.FAILED)


def test_await_completes_without_internal_scheduling_point() -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> AuthResult:
        task = asyncio.create_task(marker())
        result = await _adapter()(_auth_request())
        assert events == []
        await task
        return result

    result = asyncio.run(resolve())

    assert result.kind is AuthKind.RESOLVED
    assert events == ["marker"]


def test_await_runs_in_same_task_without_hidden_task_creation() -> None:
    async def resolve() -> tuple[AuthResult, int, asyncio.Task[object] | None]:
        current = asyncio.current_task()
        before = len(asyncio.all_tasks())
        result = await _adapter()(_auth_request())
        after = len(asyncio.all_tasks())
        assert before == after == ONE_ENTRY
        return result, after, current

    result, task_count, current = asyncio.run(resolve())

    assert result.kind is AuthKind.RESOLVED
    assert task_count == ONE_ENTRY
    assert current is not None


def test_async_authorization_boundary_materializes_exact_memory_value() -> None:
    resolved = _resolved_authorization(_adapter())

    assert resolved.authorization_value == AUTHORIZATION_A
    assert resolved.authorization_provider_id == AUTH_PROVIDER_ID
    assert resolved.bundle_fingerprint == FINGERPRINT_A
    assert resolved.fetch_provider_id == FETCH_PROVIDER_A
    assert resolved.resource_id == RESOURCE_A
    assert resolved.source_id == SOURCE_A


def test_repeated_async_resolution_reuses_only_explicit_memory_state() -> None:
    value = _adapter()

    first = _resolved_authorization(value)
    second = _resolved_authorization(value)

    assert first == second
    assert _validate_adapter(value) is value


def test_empty_memory_service_returns_unavailable_directly() -> None:
    value = _adapter(entries=())
    result = _direct_result(value, _auth_request())

    assert value.entry_count == 0
    assert result == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_value() -> None:
    result = _direct_result(
        _adapter(),
        _auth_request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        ),
    )

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_B


def test_builder_rejects_foreign_memory_provider_type() -> None:
    with pytest.raises(
        AdapterError, match="invalid memory Authorization provider"
    ):
        _ = _build_adapter(cast("MemoryProvider", object()))


def test_builder_rejects_tampered_memory_provider() -> None:
    value = replace(_memory_provider(), service_id="unsupported")

    with pytest.raises(
        AdapterError, match="invalid memory Authorization provider"
    ):
        _ = _build_adapter(value)


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-async auth type"):
        _ = _validate_adapter(cast("MemoryAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value, _auth_request())


@pytest.mark.parametrize("entry_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_lookup(
    entry_count: int,
) -> None:
    value = replace(_adapter(), entry_count=entry_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value, _auth_request())


def test_tampered_adapter_count_binding_fails_before_lookup() -> None:
    value = replace(_adapter(), entry_count=ONE_ENTRY)

    with pytest.raises(
        AdapterError, match="entry count does not match provider"
    ):
        _ = _direct_result(value, _auth_request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_tampered_adapter_limit_type_fails_before_lookup(
    max_entries: int,
) -> None:
    value = replace(_adapter(), max_entries=max_entries)

    with pytest.raises(AdapterError, match="positive integer"):
        _ = _direct_result(value, _auth_request())


def test_tampered_adapter_limit_binding_fails_before_lookup() -> None:
    value = replace(_adapter(), max_entries=DEFAULT_MAX_ENTRIES + 1)

    with pytest.raises(
        AdapterError, match="entry limit does not match provider"
    ):
        _ = _direct_result(value, _auth_request())


def test_tampered_adapter_provider_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), provider_id=OTHER_AUTH_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _direct_result(value, _auth_request())


def test_tampered_adapter_provider_type_fails_before_lookup() -> None:
    value = replace(
        _adapter(),
        provider=cast("MemoryProvider", object()),
    )

    with pytest.raises(
        AdapterError, match="invalid memory Authorization provider"
    ):
        _ = _direct_result(value, _auth_request())


def test_tampered_wrapped_value_fails_shared_validation() -> None:
    service = _memory_provider()
    changed = replace(
        service.entries[0],
        authorization_value="Bearer café",
    )
    tampered_service = replace(
        service,
        entries=(changed, service.entries[1]),
    )
    value = replace(_adapter(), provider=tampered_service)

    with pytest.raises(
        AdapterError, match="invalid memory Authorization provider"
    ):
        _ = _direct_result(value, _auth_request())


def test_tampered_wrapped_byte_count_fails_shared_validation() -> None:
    service = _memory_provider()
    changed = replace(service.entries[0], authorization_byte_count=1)
    tampered_service = replace(
        service,
        entries=(changed, service.entries[1]),
    )
    value = replace(_adapter(), provider=tampered_service)

    with pytest.raises(
        AdapterError, match="invalid memory Authorization provider"
    ):
        _ = _direct_result(value, _auth_request())


def test_direct_foreign_request_type_preserves_memory_error() -> None:
    with pytest.raises(MemoryAuthError, match="invalid memory-provider"):
        _ = _direct_result(
            _adapter(),
            cast("AuthRequest", object()),
        )


def test_direct_malformed_request_preserves_memory_error() -> None:
    malformed = replace(_auth_request(), bundle_fingerprint="malformed")

    with pytest.raises(MemoryAuthError, match="invalid memory-provider"):
        _ = _direct_result(_adapter(), malformed)


def test_async_boundary_stops_on_typed_unavailable_result() -> None:
    value = _adapter(entries=())

    with pytest.raises(
        async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError,
        match="cannot materialize async HTTPS Authorization result",
    ):
        _ = _resolved_authorization(value)


def test_async_boundary_stops_on_typed_failed_result() -> None:
    value = _build_adapter(_memory_provider(provider_id=OTHER_AUTH_PROVIDER_ID))

    with pytest.raises(
        async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError,
        match="cannot materialize async HTTPS Authorization result",
    ):
        _ = _resolved_authorization(value)


def test_custom_service_limit_is_copied_exactly() -> None:
    service = _memory_provider(max_entries=TWO_ENTRIES)
    value = _build_adapter(service)

    assert value.entry_count == TWO_ENTRIES
    assert value.max_entries == TWO_ENTRIES
    assert _validate_adapter(value) is value
