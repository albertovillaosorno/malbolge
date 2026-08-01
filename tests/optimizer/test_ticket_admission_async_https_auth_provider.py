# File:
#   - test_ticket_admission_async_https_auth_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_async_https_auth_provider.py
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
#   - Explicit async HTTPS Authorization-provider port regressions.
# - Must-Not:
#   - Use sockets, hidden tasks, threads, refresh, discovery, retries, caches,
#     persistence, secret logging, trust-root loading, PKI, or policy changes.
# - Allows:
#   - Inputs: exact HTTPS fetchers, requests, async providers, and tampering.
#   - Outputs: preflight, await, cancellation, bounds, secrecy, and failures.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact async Authorization boundary.
# - Summary:
#   - One-await bounded HTTPS Authorization provider regressions.
# - Description:
#   - Proves async resolution reuses exact synchronous validation without policy.
# - Usage:
#   - Runs without network access, files, async plugins, or accelerator hardware.
# - Defaults:
#   - Uses one canonical request and the shared 4096-byte default.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Explicit async HTTPS Authorization credential-provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]
# ruff: file-ignore[too-many-arguments]

from __future__ import annotations

import asyncio
from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

import pytest

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
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

AsyncAuthError = (
    async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError
)
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthKind = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
ResolvedAuth = auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization
AsyncProviderPort = (
    async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthorizationProvider
)
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_resolve_async = async_auth.resolve_ticket_admission_https_authorization_async
_resolve_sync = auth.resolve_ticket_admission_https_authorization
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher

PORT_ID = (
    "explicit-async-ticket-admission-lineage-https-authorization-provider-v1"
)
AUTHORIZATION_PROVIDER_ID = "credential-provider.test.async-authorization"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json"
SOURCE_ID = "source.test.async-authorization-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
FETCH_PROVIDER_ID = "provider.test.async-authorization-public-keys"
BUNDLE_FINGERPRINT = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("0" * 64)
)
AUTHORIZATION_VALUE = "Bearer caller-owned-async-test-token"
BASIC_VALUE = "Basic Y2FsbGVyOm93bmVk"
VENDOR_DETAIL = "async credential backend detail must not cross boundary"
AUTHORIZATION_BYTES = AUTHORIZATION_VALUE.encode("ascii")
AUTHORIZATION_FIELD = b"authorization_value"
ONE_CALL = 1
TWO_CALLS = 2
DEFAULT_AUTHORIZATION_BYTES = 4096
MAX_AUTHORIZATION_BYTES = 16384


class _AsyncProvider:
    def __init__(
        self,
        result: AuthResult,
        *,
        suspend: bool = True,
    ) -> None:
        self.result: AuthResult = result
        self.suspend: bool = suspend
        self.requests: list[AuthRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(self, request: AuthRequest) -> AuthResult:
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        self.task_counts.append(len(asyncio.all_tasks()))
        if self.suspend:
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        return self.result


class _SyncProvider:
    def __init__(self, result: AuthResult) -> None:
        self.result: AuthResult = result

    def __call__(self, request: AuthRequest) -> AuthResult:
        _ = request
        return self.result


class _CancellingProvider:
    async def __call__(self, request: AuthRequest) -> AuthResult:
        _ = request
        raise asyncio.CancelledError


class _RaisingProvider:
    def __init__(self) -> None:
        self.requests: list[AuthRequest] = []

    async def __call__(self, request: AuthRequest) -> AuthResult:
        self.requests.append(request)
        raise RuntimeError(VENDOR_DETAIL)


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _fetcher() -> HttpsFetcher:
    return _build_https(
        HttpsConfig(
            host=HOST,
            resource_id=RESOURCE_ID,
            source_id=SOURCE_ID,
            target=TARGET,
            tls_context=_tls_context(),
        )
    )


def _request(
    *,
    resource_id: str = RESOURCE_ID,
    source_id: str = SOURCE_ID,
) -> FetchRequest:
    return FetchRequest(
        bundle_fingerprint=BUNDLE_FINGERPRINT,
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=FETCH_PROVIDER_ID,
        resource_id=resource_id,
        source_id=source_id,
    )


def _resolved(value: str = AUTHORIZATION_VALUE) -> AuthResult:
    return AuthResult(kind=AuthKind.RESOLVED, authorization_value=value)


def _provider(
    value: str = AUTHORIZATION_VALUE,
    *,
    suspend: bool = True,
) -> _AsyncProvider:
    return _AsyncProvider(_resolved(value), suspend=suspend)


def _run(
    provider: async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthorizationProvider,
    *,
    fetcher: HttpsFetcher | None = None,
    request: FetchRequest | None = None,
    authorization_provider_id: str = AUTHORIZATION_PROVIDER_ID,
    max_authorization_bytes: int = auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES,
) -> ResolvedAuth:
    return asyncio.run(
        _resolve_async(
            _fetcher() if fetcher is None else fetcher,
            _request() if request is None else request,
            provider,
            authorization_provider_id=authorization_provider_id,
            max_authorization_bytes=max_authorization_bytes,
        )
    )


def test_identity_and_defaults_are_stable() -> None:
    assert (
        async_auth.ticket_admission_async_https_authorization_provider_id()
        == PORT_ID
    )
    assert (
        auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES
        == DEFAULT_AUTHORIZATION_BYTES
    )
    assert auth.MAX_HTTPS_AUTHORIZATION_BYTES == MAX_AUTHORIZATION_BYTES


def test_coroutine_does_not_start_before_caller_runs_it() -> None:
    provider = _provider()
    coroutine = _resolve_async(
        _fetcher(),
        _request(),
        provider,
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )

    assert provider.requests == []
    resolved = asyncio.run(coroutine)

    assert resolved.authorization_value == AUTHORIZATION_VALUE
    assert len(provider.requests) == ONE_CALL


def test_exact_request_awaits_once_in_same_task() -> None:
    provider = _provider()
    request = _request()

    resolved = _run(provider, request=request)

    assert len(provider.requests) == ONE_CALL
    assert provider.requests[0].bundle_fingerprint == request.bundle_fingerprint
    assert provider.requests[0].fetch_provider_id == request.provider_id
    assert provider.requests[0].resource_id == request.resource_id
    assert provider.requests[0].source_id == request.source_id
    assert len(set(provider.tasks)) == ONE_CALL
    assert provider.task_counts == [ONE_CALL]
    assert resolved.authorization_byte_count == len(AUTHORIZATION_BYTES)
    assert resolved.authorization_provider_id == AUTHORIZATION_PROVIDER_ID
    assert resolved.bundle_fingerprint == BUNDLE_FINGERPRINT
    assert resolved.fetch_provider_id == FETCH_PROVIDER_ID
    assert resolved.resource_id == RESOURCE_ID
    assert resolved.source_id == SOURCE_ID


def test_inline_provider_controls_absence_of_suspension() -> None:
    provider = _provider(suspend=False)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> ResolvedAuth:
        marker_task = asyncio.create_task(marker())
        result = await _resolve_async(
            _fetcher(),
            _request(),
            provider,
            authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        )
        assert events == []
        await marker_task
        return result

    resolved = asyncio.run(resolve())

    assert resolved.authorization_value == AUTHORIZATION_VALUE
    assert events == ["marker"]


def test_suspending_provider_controls_scheduling_point() -> None:
    provider = _provider(suspend=True)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> ResolvedAuth:
        marker_task = asyncio.create_task(marker())
        result = await _resolve_async(
            _fetcher(),
            _request(),
            provider,
            authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        )
        assert events == ["marker"]
        await marker_task
        return result

    resolved = asyncio.run(resolve())

    assert resolved.authorization_value == AUTHORIZATION_VALUE


def test_sync_and_async_paths_materialize_identical_state() -> None:
    result = _resolved(BASIC_VALUE)

    synchronous = _resolve_sync(
        _fetcher(),
        _request(),
        _SyncProvider(result),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )
    asynchronous = _run(_AsyncProvider(result, suspend=False))

    assert asynchronous == synchronous


def test_result_and_resolved_value_hide_credential_text() -> None:
    result = _resolved()
    resolved = _run(_AsyncProvider(result, suspend=False))

    assert AUTHORIZATION_BYTES not in repr(result).encode("utf-8")
    assert AUTHORIZATION_BYTES not in repr(resolved).encode("utf-8")
    assert AUTHORIZATION_FIELD not in repr(result).encode("utf-8")
    assert AUTHORIZATION_FIELD not in repr(resolved).encode("utf-8")


def test_repeated_resolution_has_no_cache_or_refresh() -> None:
    provider = _provider(suspend=False)

    first = _run(provider)
    second = _run(provider)

    assert first == second
    assert len(provider.requests) == TWO_CALLS


@pytest.mark.parametrize("value", [AUTHORIZATION_VALUE, BASIC_VALUE])
def test_scheme_and_opaque_value_are_caller_owned(value: str) -> None:
    resolved = _run(_provider(value, suspend=False))

    assert resolved.authorization_value == value
    assert resolved.authorization_byte_count == len(value.encode("ascii"))


def test_exact_configured_byte_limit_is_allowed() -> None:
    value = "X" * 17

    resolved = _run(
        _provider(value, suspend=False),
        max_authorization_bytes=len(value),
    )

    assert resolved.authorization_byte_count == len(value)


@pytest.mark.parametrize(
    ("source_id", "resource_id"),
    [
        (OTHER_SOURCE_ID, RESOURCE_ID),
        (SOURCE_ID, OTHER_RESOURCE_ID),
    ],
)
def test_fetch_binding_mismatch_fails_before_first_await(
    source_id: str,
    resource_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(
            provider,
            request=_request(source_id=source_id, resource_id=resource_id),
        )

    assert provider.requests == []


def test_foreign_fetcher_fails_before_first_await() -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, fetcher=cast("HttpsFetcher", object()))

    assert provider.requests == []


def test_tampered_fetcher_fails_before_first_await() -> None:
    provider = _provider()
    tampered = replace(_fetcher(), fetcher_id="unsupported")

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, fetcher=tampered)

    assert provider.requests == []


def test_foreign_request_fails_before_first_await() -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, request=cast("FetchRequest", object()))

    assert provider.requests == []


def test_malformed_request_fails_before_first_await() -> None:
    provider = _provider()
    malformed = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, request=malformed)

    assert provider.requests == []


@pytest.mark.parametrize(
    "provider_id", ["", "bad provider", cast("str", object())]
)
def test_invalid_provider_identity_fails_before_first_await(
    provider_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, authorization_provider_id=provider_id)

    assert provider.requests == []


@pytest.mark.parametrize("limit", [0, -1, True])
def test_invalid_byte_limit_fails_before_first_await(limit: int) -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(provider, max_authorization_bytes=limit)

    assert provider.requests == []


def test_byte_limit_above_supported_maximum_fails_before_first_await() -> None:
    provider = _provider()

    with pytest.raises(AsyncAuthError, match="invalid async HTTPS"):
        _ = _run(
            provider,
            max_authorization_bytes=auth.MAX_HTTPS_AUTHORIZATION_BYTES + 1,
        )

    assert provider.requests == []


def test_noncallable_provider_fails_before_first_await() -> None:
    with pytest.raises(AsyncAuthError, match="provider must be callable"):
        _ = _run(cast("AsyncProviderPort", object()))


def test_cancellation_propagates() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_CancellingProvider())


def test_provider_exception_is_wrapped_without_vendor_text() -> None:
    provider = _RaisingProvider()

    with pytest.raises(
        AsyncAuthError,
        match="async Authorization provider raised during explicit resolution",
    ) as caught:
        _ = _run(provider)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(provider.requests) == ONE_CALL


@pytest.mark.parametrize("kind", [AuthKind.UNAVAILABLE, AuthKind.FAILED])
def test_typed_nonresolved_result_fails_after_one_await(kind: AuthKind) -> None:
    provider = _AsyncProvider(AuthResult(kind=kind), suspend=False)

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(provider)

    assert len(provider.requests) == ONE_CALL


def test_foreign_result_type_fails_after_one_await() -> None:
    provider = _AsyncProvider(cast("AuthResult", object()), suspend=False)

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(provider)

    assert len(provider.requests) == ONE_CALL


def test_foreign_result_enum_fails_after_one_await() -> None:
    result = AuthResult(
        kind=cast("AuthKind", cast("object", "resolved")),
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(_AsyncProvider(result, suspend=False))


def test_nonresolved_result_cannot_smuggle_credential_text() -> None:
    result = AuthResult(
        kind=AuthKind.FAILED,
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(_AsyncProvider(result, suspend=False))


@pytest.mark.parametrize(
    "value",
    [None, "", cast("str | None", cast("object", bytearray(b"foreign")))],
)
def test_resolved_result_requires_nonempty_exact_text(
    value: str | None,
) -> None:
    result = AuthResult(kind=AuthKind.RESOLVED, authorization_value=value)

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(_AsyncProvider(result, suspend=False))


@pytest.mark.parametrize("value", ["Bearer café", "Bearer 🔑"])
def test_resolved_authorization_requires_ascii(value: str) -> None:
    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(_provider(value, suspend=False))


@pytest.mark.parametrize(
    "value",
    [
        " Bearer token",
        "Bearer token ",
        "Bearer\ttoken",
        "Bearer\ntoken",
        "Bearer\r token",
        "Bearer\x00token",
        "Bearer\x7ftoken",
    ],
)
def test_edge_spaces_and_controls_fail_closed(value: str) -> None:
    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(_provider(value, suspend=False))


def test_authorization_above_requested_limit_fails_closed() -> None:
    value = "X" * 9

    with pytest.raises(AsyncAuthError, match="cannot materialize"):
        _ = _run(
            _provider(value, suspend=False),
            max_authorization_bytes=8,
        )
