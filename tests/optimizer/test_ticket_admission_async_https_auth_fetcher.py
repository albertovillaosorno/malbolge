# File:
#   - test_ticket_admission_async_https_auth_fetcher.py
# Path:
#   - tests/optimizer/test_ticket_admission_async_https_auth_fetcher.py
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
#   - Caller-offloaded async authorized HTTPS bundle-fetcher regressions.
# - Must-Not:
#   - Use live sockets, hidden tasks, threads, executors, credential refresh,
#     retries, redirects, trust-root loading, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: exact authorized fetchers, offloaders, requests, and tampering.
#   - Outputs: preflight, await, cancellation, result, and binding assertions.
#   - Side effects: caller-owned event loops and monkeypatched connections only.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact authorized async boundary.
# - Summary:
#   - Caller-scheduled async authorized HTTPS bundle-fetcher regressions.
# - Description:
#   - Proves async authorization injection adds no scheduling or refresh policy.
# - Usage:
#   - Runs without network access, pytest async plugins, or accelerator hardware.
# - Defaults:
#   - Uses one synthetic key, one resolved Authorization value, and one offloader.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_https_auth_provider.py
# - accelerator/ticket_admission_file_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Caller-offloaded async authorized HTTPS bundle-fetcher tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_async_bundle_fetcher as async_fetch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_async_https_auth_fetcher as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_authorized_fetcher as authorized,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle as bundle,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError
)
AsyncAuthorizedFetcher = (
    adapter.TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher
)
AuthorizedFetcher = (
    authorized.TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher
)
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthKind = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
_build_adapter = (
    adapter.build_ticket_admission_async_authorized_https_bundle_fetcher
)
_validate_adapter = (
    adapter.validate_ticket_admission_async_authorized_https_bundle_fetcher
)
_build_authorized = (
    authorized.build_ticket_admission_authorized_https_bundle_fetcher
)
_validate_authorized = (
    authorized.validate_ticket_admission_authorized_https_bundle_fetcher
)
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_resolve_auth = auth.resolve_ticket_admission_https_authorization
_fetch_async = (
    async_fetch.fetch_ticket_admission_public_key_bundle_provider_async
)
_build_bundle = (
    bundle.build_ticket_admission_telemetry_lineage_public_key_bundle
)
_encode_bundle = (
    bundle.encode_ticket_admission_telemetry_lineage_public_key_bundle
)
_bundle_fingerprint = (
    bundle.ticket_admission_telemetry_lineage_public_key_bundle_fingerprint
)

ADAPTER_ID = (
    "offloaded-async-authorized-https-ticket-admission-lineage-"
    "public-key-bundle-fetcher-v1"
)
AUTHORIZATION_PROVIDER_ID = "credential-provider.test.async-authorized"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json"
SOURCE_ID = "source.test.async-authorized-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
PROVIDER_ID = "provider.test.async-authorized-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
ALGORITHM_ID = "test-only-public-digest-v1"
PUBLIC_KEY_ID = "public.test-key.2026-08"
REFERENCE_ID = "vault.public-key.2026-08"
PUBLIC_KEY = b"caller-owned-async-authorized-test-public-key"
AUTHORIZATION_VALUE = "Bearer caller-owned-async-authorized-token"
AUTHORIZATION_BYTES = AUTHORIZATION_VALUE.encode("ascii")
VENDOR_DETAIL = "caller authorized scheduling detail must not cross boundary"
GENESIS_SEQUENCE_ID = 0
HTTP_OK = 200
ONE_KEY = 1
ONE_CALL = 1
TWO_CALLS = 2
FETCHER_FIELD = b"fetcher="
OFFLOADER_FIELD = b"offloader="
AUTHORIZATION_FIELD = b"authorization_value"
CONTENT_TYPE_HEADER = "content-type"
CONTENT_LENGTH_HEADER = "content-length"


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.status: int = HTTP_OK
        self.payload: bytes = payload

    def getheader(self, name: str, default: str | None = None) -> str | None:
        if name.lower() == CONTENT_TYPE_HEADER:
            return "application/json"
        if name.lower() == CONTENT_LENGTH_HEADER:
            return str(len(self.payload))
        return default

    def read(self, amount: int | None = None) -> bytes:
        _ = amount
        return self.payload


class _Connection:
    def __init__(self, payload: bytes) -> None:
        self.response: _Response = _Response(payload)
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.close_count: int = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> None:
        self.requests.append((method, url, dict(headers)))

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        self.close_count += 1


class _Opener:
    def __init__(self, connections: list[_Connection]) -> None:
        self.connections: list[_Connection] = connections
        self.configs: list[HttpsConfig] = []

    def __call__(self, config: HttpsConfig) -> _Connection:
        self.configs.append(config)
        return self.connections.pop(0)


class _AuthProvider:
    def __init__(self) -> None:
        self.requests: list[AuthRequest] = []

    def __call__(self, request: AuthRequest) -> AuthResult:
        self.requests.append(request)
        return AuthResult(
            kind=AuthKind.RESOLVED,
            authorization_value=AUTHORIZATION_VALUE,
        )


class _Offloader:
    def __init__(self, *, suspend: bool = True) -> None:
        self.suspend: bool = suspend
        self.fetchers: list[AuthorizedFetcher] = []
        self.requests: list[FetchRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(
        self,
        fetcher: AuthorizedFetcher,
        request: FetchRequest,
    ) -> FetchResult:
        self.fetchers.append(fetcher)
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        self.task_counts.append(len(asyncio.all_tasks()))
        if self.suspend:
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        return fetcher(request)


class _CancellingOffloader:
    async def __call__(
        self,
        fetcher: AuthorizedFetcher,
        request: FetchRequest,
    ) -> FetchResult:
        _ = fetcher, request
        raise asyncio.CancelledError


class _RaisingOffloader:
    async def __call__(
        self,
        fetcher: AuthorizedFetcher,
        request: FetchRequest,
    ) -> FetchResult:
        _ = fetcher, request
        raise RuntimeError(VENDOR_DETAIL)


class _ResultOffloader:
    def __init__(self, result: FetchResult) -> None:
        self.result: FetchResult = result
        self.call_count: int = 0

    async def __call__(
        self,
        fetcher: AuthorizedFetcher,
        request: FetchRequest,
    ) -> FetchResult:
        _ = fetcher, request
        self.call_count += 1
        return self.result


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _https_fetcher() -> HttpsFetcher:
    return _build_https(
        HttpsConfig(
            host=HOST,
            resource_id=RESOURCE_ID,
            source_id=SOURCE_ID,
            target=TARGET,
            tls_context=_tls_context(),
        )
    )


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _bundle() -> bundle.TicketAdmissionTelemetryLineagePublicKeyBundle:
    entry = BundleEntry(
        algorithm_id=ALGORITHM_ID,
        first_capture_sequence_id=GENESIS_SEQUENCE_ID,
        last_capture_sequence_id=None,
        public_key=PUBLIC_KEY,
        public_key_fingerprint=_fingerprint(PUBLIC_KEY),
        public_key_id=PUBLIC_KEY_ID,
        public_key_reference_id=REFERENCE_ID,
    )
    return _build_bundle((entry,), provider_id=PROVIDER_ID)


def _payload() -> bytes:
    return _encode_bundle(_bundle())


def _request(  # ruff: ignore[too-many-arguments]
    *,
    bundle_fingerprint: str | None = None,
    max_bytes: int | None = None,
    provider_id: str = PROVIDER_ID,
    resource_id: str = RESOURCE_ID,
    source_id: str = SOURCE_ID,
) -> FetchRequest:
    return FetchRequest(
        bundle_fingerprint=(
            _bundle_fingerprint(_bundle())
            if bundle_fingerprint is None
            else bundle_fingerprint
        ),
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
            if max_bytes is None
            else max_bytes
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _authorized_fetcher() -> tuple[AuthorizedFetcher, _AuthProvider]:
    https_fetcher = _https_fetcher()
    provider = _AuthProvider()
    authorization = _resolve_auth(
        https_fetcher,
        _request(),
        provider,
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )
    return _build_authorized(https_fetcher, authorization), provider


def _adapter(
    offloader: adapter.TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader
    | None = None,
) -> tuple[AsyncAuthorizedFetcher, _AuthProvider]:
    sync_fetcher, provider = _authorized_fetcher()
    built = _build_adapter(
        sync_fetcher,
        _Offloader() if offloader is None else offloader,
    )
    return built, provider


def _install(
    monkeypatch: pytest.MonkeyPatch,
    connections: list[_Connection],
) -> _Opener:
    opener = _Opener(connections)
    monkeypatch.setattr(https, "_open_connection", opener)
    return opener


def _run_direct(
    value: AsyncAuthorizedFetcher,
    request: FetchRequest | None = None,
) -> FetchResult:
    async def resolve() -> FetchResult:
        return await value(_request() if request is None else request)

    return asyncio.run(resolve())


def _run_loaded(
    value: AsyncAuthorizedFetcher,
    request: FetchRequest | None = None,
) -> fetch.TicketAdmissionTelemetryLineageFetchedPublicKeyBundle:
    async def resolve() -> (
        fetch.TicketAdmissionTelemetryLineageFetchedPublicKeyBundle
    ):
        return await _fetch_async(
            value,
            _request() if request is None else request,
        )

    return asyncio.run(resolve())


def test_identity_metadata_validator_and_repr_are_stable() -> None:
    offloader = _Offloader()
    value, provider = _adapter(offloader)
    representation = repr(value).encode("utf-8")

    assert (
        adapter.ticket_admission_async_authorized_https_bundle_fetcher_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.authorization_byte_count == len(AUTHORIZATION_BYTES)
    assert value.authorization_provider_id == AUTHORIZATION_PROVIDER_ID
    assert value.bundle_fingerprint == _request().bundle_fingerprint
    assert value.fetch_provider_id == PROVIDER_ID
    assert value.resource_id == RESOURCE_ID
    assert value.source_id == SOURCE_ID
    assert _validate_adapter(value) is value
    assert _validate_authorized(value.fetcher) is value.fetcher
    assert len(provider.requests) == ONE_CALL
    assert AUTHORIZATION_BYTES not in representation
    assert AUTHORIZATION_FIELD not in representation
    assert FETCHER_FIELD not in representation
    assert OFFLOADER_FIELD not in representation
    assert HOST.encode() not in representation
    assert TARGET.encode() not in representation


def test_coroutine_does_not_start_before_caller_runs_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install(monkeypatch, [_Connection(_payload())])
    offloader = _Offloader()
    value, _ = _adapter(offloader)
    coroutine = value(_request())

    assert offloader.requests == []
    result = asyncio.run(coroutine)

    assert result.kind is FetchKind.FETCHED
    assert offloader.requests == [_request()]


def test_exact_request_awaits_once_in_same_task_and_injects_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])
    offloader = _Offloader()
    value, provider = _adapter(offloader)
    request = _request()

    result = _run_direct(value, request)

    assert result.kind is FetchKind.FETCHED
    assert result.payload == _payload()
    assert offloader.fetchers == [value.fetcher]
    assert offloader.requests == [request]
    assert offloader.requests[0] is request
    assert len(set(offloader.tasks)) == ONE_CALL
    assert offloader.task_counts == [ONE_CALL]
    assert len(provider.requests) == ONE_CALL
    assert connection.requests[0][2]["Authorization"] == AUTHORIZATION_VALUE
    assert connection.close_count == ONE_CALL


def test_inline_offloader_controls_absence_of_suspension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install(monkeypatch, [_Connection(_payload())])
    events: list[str] = []
    offloader = _Offloader(suspend=False)
    value, _ = _adapter(offloader)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> FetchResult:
        marker_task = asyncio.create_task(marker())
        result = await value(_request())
        assert events == []
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is FetchKind.FETCHED
    assert events == ["marker"]


def test_suspending_offloader_controls_scheduling_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install(monkeypatch, [_Connection(_payload())])
    events: list[str] = []
    offloader = _Offloader(suspend=True)
    value, _ = _adapter(offloader)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> FetchResult:
        marker_task = asyncio.create_task(marker())
        result = await value(_request())
        assert events == ["marker"]
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is FetchKind.FETCHED


def test_async_fetch_boundary_materializes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = _install(monkeypatch, [_Connection(_payload())])
    value, _ = _adapter()

    loaded = _run_loaded(value)

    assert loaded.key_count == ONE_KEY
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.resource_id == RESOURCE_ID
    assert loaded.source_id == SOURCE_ID


def test_repeated_calls_have_no_adapter_cache_or_credential_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _Connection(_payload())
    second = _Connection(_payload())
    opener = _install(monkeypatch, [first, second])
    offloader = _Offloader(suspend=False)
    value, provider = _adapter(offloader)

    first_result = _run_direct(value)
    second_result = _run_direct(value)

    assert first_result.kind is FetchKind.FETCHED
    assert second_result.kind is FetchKind.FETCHED
    assert len(offloader.requests) == TWO_CALLS
    assert len(opener.configs) == TWO_CALLS
    assert len(provider.requests) == ONE_CALL
    assert first.close_count == ONE_CALL
    assert second.close_count == ONE_CALL


@pytest.mark.parametrize(
    "fetch_request",
    [
        _request(
            bundle_fingerprint=(
                "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
                + ("1" * 64)
            )
        ),
        _request(provider_id=OTHER_PROVIDER_ID),
        _request(resource_id=OTHER_RESOURCE_ID),
        _request(source_id=OTHER_SOURCE_ID),
    ],
)
def test_binding_mismatch_returns_failed_without_offload(
    fetch_request: FetchRequest,
) -> None:
    offloader = _Offloader()
    value, provider = _adapter(offloader)

    result = _run_direct(value, fetch_request)

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert offloader.requests == []
    assert len(provider.requests) == ONE_CALL


def test_invalid_request_fails_before_first_await() -> None:
    offloader = _Offloader()
    value, _ = _adapter(offloader)

    with pytest.raises(
        AdapterError, match="invalid caller-offloaded authorized"
    ):
        _ = _run_direct(value, replace(_request(), max_bytes=0))

    assert offloader.requests == []


def test_offloader_cancellation_propagates() -> None:
    value, _ = _adapter(_CancellingOffloader())

    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run_direct(value)


def test_offloader_exception_is_wrapped_without_vendor_text() -> None:
    value, _ = _adapter(_RaisingOffloader())

    with pytest.raises(
        AdapterError,
        match="caller authorized HTTPS offloader raised during explicit fetch",
    ) as caught:
        _ = _run_direct(value)

    assert VENDOR_DETAIL not in str(caught.value)


@pytest.mark.parametrize("kind", [FetchKind.UNAVAILABLE, FetchKind.FAILED])
def test_typed_nonfetched_result_is_preserved(kind: FetchKind) -> None:
    offloader = _ResultOffloader(FetchResult(kind=kind))
    value, _ = _adapter(offloader)

    result = _run_direct(value)

    assert result == FetchResult(kind=kind)
    assert offloader.call_count == ONE_CALL


def test_foreign_result_type_fails_after_one_await() -> None:
    offloader = _ResultOffloader(cast("FetchResult", object()))
    value, _ = _adapter(offloader)

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(value)

    assert offloader.call_count == ONE_CALL


def test_foreign_result_enum_fails_after_one_await() -> None:
    result = FetchResult(
        kind=cast("FetchKind", cast("object", "fetched")),
        payload=_payload(),
    )
    value, _ = _adapter(_ResultOffloader(result))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(value)


def test_nonfetched_result_cannot_carry_payload() -> None:
    result = FetchResult(kind=FetchKind.FAILED, payload=_payload())
    value, _ = _adapter(_ResultOffloader(result))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(value)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        b"",
        cast("bytes | None", cast("object", bytearray(b"foreign"))),
    ],
)
def test_fetched_result_requires_exact_nonempty_bytes(
    payload: bytes | None,
) -> None:
    result = FetchResult(kind=FetchKind.FETCHED, payload=payload)
    value, _ = _adapter(_ResultOffloader(result))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(value)


def test_fetched_result_respects_request_byte_limit() -> None:
    payload = _payload()
    result = FetchResult(kind=FetchKind.FETCHED, payload=payload)
    value, _ = _adapter(_ResultOffloader(result))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(value, _request(max_bytes=len(payload) - 1))


def test_outer_async_boundary_rejects_typed_failed_result() -> None:
    value, _ = _adapter(_ResultOffloader(FetchResult(kind=FetchKind.FAILED)))

    with pytest.raises(
        async_fetch.TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError,
        match="cannot process async fetched public-key bundle",
    ):
        _ = _run_loaded(value)


def test_builder_rejects_foreign_authorized_fetcher_type() -> None:
    with pytest.raises(
        AdapterError, match="invalid synchronous authorized HTTPS"
    ):
        _ = _build_adapter(
            cast("AuthorizedFetcher", object()),
            _Offloader(),
        )


def test_builder_rejects_tampered_authorized_fetcher() -> None:
    value, _ = _authorized_fetcher()
    tampered = replace(value, adapter_id="unsupported")

    with pytest.raises(
        AdapterError, match="invalid synchronous authorized HTTPS"
    ):
        _ = _build_adapter(tampered, _Offloader())


def test_builder_rejects_noncallable_offloader() -> None:
    value, _ = _authorized_fetcher()

    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _build_adapter(
            value,
            cast(
                "adapter.TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader",
                object(),
            ),
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact async authorized HTTPS"):
        _ = _validate_adapter(cast("AsyncAuthorizedFetcher", object()))


def test_tampered_adapter_identity_fails_before_await() -> None:
    value, _ = _adapter()
    tampered = replace(value, adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _run_direct(tampered)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("fetcher_id", "unsupported", "fetcher identity does not match"),
        (
            "authorization_byte_count",
            1,
            "authorization byte count does not match",
        ),
        (
            "authorization_provider_id",
            "credential-provider.test.other",
            "authorization provider identity does not match",
        ),
        (
            "bundle_fingerprint",
            "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
            + ("1" * 64),
            "bundle fingerprint does not match",
        ),
        (
            "fetch_provider_id",
            OTHER_PROVIDER_ID,
            "fetch provider identity does not match",
        ),
        ("resource_id", OTHER_RESOURCE_ID, "resource identity does not match"),
        ("source_id", OTHER_SOURCE_ID, "source identity does not match"),
    ],
)
def test_tampered_adapter_binding_fails_before_await(
    field: str,
    value: int | str,
    match: str,
) -> None:
    built, _ = _adapter()
    tampered = replace(built, **{field: value})

    with pytest.raises(AdapterError, match=match):
        _ = _run_direct(tampered)


def test_tampered_wrapped_authorized_fetcher_fails_before_await() -> None:
    built, _ = _adapter()
    wrapped = replace(built.fetcher, adapter_id="unsupported")
    tampered = replace(built, fetcher=wrapped)

    with pytest.raises(
        AdapterError, match="invalid synchronous authorized HTTPS"
    ):
        _ = _run_direct(tampered)


def test_tampered_noncallable_offloader_fails_before_await() -> None:
    built, _ = _adapter()
    tampered = replace(
        built,
        offloader=cast(
            "adapter.TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader",
            object(),
        ),
    )

    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _run_direct(tampered)
