# File:
#   - test_ticket_admission_async_https_bundle_fetcher.py
# Path:
#   - tests/optimizer/test_ticket_admission_async_https_bundle_fetcher.py
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
#   - Caller-offloaded async HTTPS public-key bundle adapter regressions.
# - Must-Not:
#   - Use live sockets, hidden tasks, threads, executors, credentials, retries,
#     redirects, trust-root loading, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: exact HTTPS fetchers, caller offloaders, requests, and tampering.
#   - Outputs: preflight, await, cancellation, result, and binding assertions.
#   - Side effects: caller-owned event loops and monkeypatched connections only.
# - Split-When:
#   - Split when native async HTTPS, credentials, hosted APIs, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact caller-offloaded async boundary.
# - Summary:
#   - Explicit caller-scheduled async HTTPS bundle adapter regressions.
# - Description:
#   - Proves the adapter owns no task, thread, executor, retry, or cache policy.
# - Usage:
#   - Runs without network access, pytest async plugins, or accelerator hardware.
# - Defaults:
#   - Uses one synthetic key, caller-owned TLS state, and one awaited offloader.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Caller-offloaded async HTTPS detached public-key bundle fetch tests."""

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
    ticket_admission_telemetry_lineage_async_https_bundle_fetcher as adapter,
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
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError
)
AsyncHttpsFetcher = (
    adapter.TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher
)
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
_build_adapter = adapter.build_ticket_admission_async_https_bundle_fetcher
_validate_adapter = adapter.validate_ticket_admission_async_https_bundle_fetcher
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_validate_https = (
    https.validate_ticket_admission_https_public_key_bundle_fetcher
)
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
_build_manifest = (
    manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)
_resolve_provider = (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider
)

ADAPTER_ID = (
    "offloaded-async-https-ticket-admission-lineage-"
    "public-key-bundle-fetcher-v1"
)
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json"
SOURCE_ID = "source.test.async-https-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
PROVIDER_ID = "provider.test.async-https-public-keys"
ALGORITHM_ID = "test-only-public-digest-v1"
PUBLIC_KEY_ID = "public.test-key.2026-08"
REFERENCE_ID = "vault.public-key.2026-08"
PUBLIC_KEY = b"caller-owned-async-https-test-public-key"
VENDOR_DETAIL = "caller scheduling detail must not cross boundary"
GENESIS_SEQUENCE_ID = 0
HTTP_OK = 200
ONE_KEY = 1
TWO_CALLS = 2
FETCHER_FIELD = b"fetcher="
OFFLOADER_FIELD = b"offloader="
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


class _Offloader:
    def __init__(self, *, suspend: bool = True) -> None:
        self.suspend: bool = suspend
        self.fetchers: list[HttpsFetcher] = []
        self.requests: list[FetchRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(
        self,
        fetcher: HttpsFetcher,
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
        fetcher: HttpsFetcher,
        request: FetchRequest,
    ) -> FetchResult:
        _ = fetcher, request
        raise asyncio.CancelledError


class _RaisingOffloader:
    async def __call__(
        self,
        fetcher: HttpsFetcher,
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
        fetcher: HttpsFetcher,
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


def _request(
    *,
    max_bytes: int | None = None,
    resource_id: str = RESOURCE_ID,
    source_id: str = SOURCE_ID,
) -> FetchRequest:
    built = _bundle()
    return FetchRequest(
        bundle_fingerprint=_bundle_fingerprint(built),
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
            if max_bytes is None
            else max_bytes
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=PROVIDER_ID,
        resource_id=resource_id,
        source_id=source_id,
    )


def _manifest() -> (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest
):
    entry = ManifestEntry(
        algorithm_id=ALGORITHM_ID,
        first_capture_sequence_id=GENESIS_SEQUENCE_ID,
        last_capture_sequence_id=None,
        public_key_fingerprint=_fingerprint(PUBLIC_KEY),
        public_key_id=PUBLIC_KEY_ID,
        public_key_reference_id=REFERENCE_ID,
    )
    return _build_manifest((entry,))


def _install(
    monkeypatch: pytest.MonkeyPatch,
    connections: list[_Connection],
) -> _Opener:
    opener = _Opener(connections)
    monkeypatch.setattr(https, "_open_connection", opener)
    return opener


def _adapter(
    offloader: adapter.TicketAdmissionTelemetryLineageHttpsBundleOffloader
    | None = None,
) -> AsyncHttpsFetcher:
    return _build_adapter(
        _https_fetcher(),
        _Offloader() if offloader is None else offloader,
    )


def _run_direct(
    value: AsyncHttpsFetcher,
    request: FetchRequest | None = None,
) -> FetchResult:
    async def resolve() -> FetchResult:
        return await value(_request() if request is None else request)

    return asyncio.run(resolve())


def _run_loaded(
    value: AsyncHttpsFetcher,
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
    value = _adapter(offloader)
    representation = repr(value).encode("utf-8")

    assert (
        adapter.ticket_admission_async_https_bundle_fetcher_id() == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert (
        value.fetcher_id
        == https.ticket_admission_https_public_key_bundle_fetcher_id()
    )
    assert value.resource_id == RESOURCE_ID
    assert value.source_id == SOURCE_ID
    assert _validate_adapter(value) is value
    assert _validate_https(value.fetcher) is value.fetcher
    assert HOST.encode() not in representation
    assert TARGET.encode() not in representation
    assert FETCHER_FIELD not in representation
    assert OFFLOADER_FIELD not in representation


def test_coroutine_does_not_start_before_caller_runs_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])
    offloader = _Offloader()
    value = _adapter(offloader)
    coroutine = value(_request())

    assert offloader.requests == []
    result = asyncio.run(coroutine)

    assert result.kind is FetchKind.FETCHED
    assert offloader.requests == [_request()]


def test_exact_request_awaits_once_in_same_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])
    offloader = _Offloader()
    value = _adapter(offloader)
    request = _request()

    result = _run_direct(value, request)

    assert result.kind is FetchKind.FETCHED
    assert result.payload == _payload()
    assert offloader.fetchers == [value.fetcher]
    assert offloader.requests == [request]
    assert len(set(offloader.tasks)) == 1
    assert offloader.task_counts == [1]
    assert connection.close_count == 1


def test_inline_offloader_controls_absence_of_suspension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])
    events: list[str] = []
    offloader = _Offloader(suspend=False)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> FetchResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(offloader)(_request())
        assert events == []
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is FetchKind.FETCHED
    assert events == ["marker"]


def test_suspending_offloader_controls_scheduling_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])
    events: list[str] = []
    offloader = _Offloader(suspend=True)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> FetchResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(offloader)(_request())
        assert events == ["marker"]
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is FetchKind.FETCHED


def test_async_fetch_boundary_materializes_provider_and_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_payload())
    _ = _install(monkeypatch, [connection])

    loaded = _run_loaded(_adapter())
    resolved = _resolve_provider(
        _manifest(),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert loaded.key_count == ONE_KEY
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.resource_id == RESOURCE_ID
    assert loaded.source_id == SOURCE_ID
    assert resolved.request_count == ONE_KEY
    assert resolved.public_key_ids == (PUBLIC_KEY_ID,)
    assert resolved.trust.key_count == ONE_KEY


def test_repeated_calls_have_no_adapter_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _Connection(_payload())
    second = _Connection(_payload())
    opener = _install(monkeypatch, [first, second])
    offloader = _Offloader(suspend=False)
    value = _adapter(offloader)

    first_result = _run_direct(value)
    second_result = _run_direct(value)

    assert first_result.kind is FetchKind.FETCHED
    assert second_result.kind is FetchKind.FETCHED
    assert len(offloader.requests) == TWO_CALLS
    assert len(opener.configs) == TWO_CALLS
    assert first.close_count == 1
    assert second.close_count == 1


@pytest.mark.parametrize(
    ("source_id", "resource_id"),
    [
        (OTHER_SOURCE_ID, RESOURCE_ID),
        (SOURCE_ID, OTHER_RESOURCE_ID),
    ],
)
def test_binding_mismatch_returns_failed_without_offload(
    source_id: str,
    resource_id: str,
) -> None:
    offloader = _Offloader()

    result = _run_direct(
        _adapter(offloader),
        _request(source_id=source_id, resource_id=resource_id),
    )

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert offloader.requests == []


def test_invalid_request_fails_before_first_await() -> None:
    offloader = _Offloader()
    request = replace(_request(), max_bytes=0)

    with pytest.raises(AdapterError, match="invalid caller-offloaded HTTPS"):
        _ = _run_direct(_adapter(offloader), request)

    assert offloader.requests == []


def test_offloader_cancellation_propagates() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run_direct(_adapter(_CancellingOffloader()))


def test_offloader_exception_is_wrapped_without_vendor_text() -> None:
    with pytest.raises(
        AdapterError,
        match="caller HTTPS offloader raised during explicit fetch",
    ) as caught:
        _ = _run_direct(_adapter(_RaisingOffloader()))

    assert VENDOR_DETAIL not in str(caught.value)


@pytest.mark.parametrize("kind", [FetchKind.UNAVAILABLE, FetchKind.FAILED])
def test_typed_nonfetched_result_is_preserved(kind: FetchKind) -> None:
    offloader = _ResultOffloader(FetchResult(kind=kind))

    result = _run_direct(_adapter(offloader))

    assert result == FetchResult(kind=kind)
    assert offloader.call_count == 1


def test_foreign_result_type_fails_after_one_await() -> None:
    offloader = _ResultOffloader(cast("FetchResult", object()))

    with pytest.raises(AdapterError, match="invalid fetch result"):
        _ = _run_direct(_adapter(offloader))

    assert offloader.call_count == 1


def test_foreign_result_enum_fails_after_one_await() -> None:
    result = FetchResult(
        kind=cast("FetchKind", cast("object", "fetched")),
        payload=_payload(),
    )

    with pytest.raises(AdapterError, match="invalid fetch result"):
        _ = _run_direct(_adapter(_ResultOffloader(result)))


def test_nonfetched_result_cannot_carry_payload() -> None:
    result = FetchResult(kind=FetchKind.FAILED, payload=_payload())

    with pytest.raises(AdapterError, match="invalid fetch result"):
        _ = _run_direct(_adapter(_ResultOffloader(result)))


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

    with pytest.raises(AdapterError, match="invalid fetch result"):
        _ = _run_direct(_adapter(_ResultOffloader(result)))


def test_fetched_result_respects_request_byte_limit() -> None:
    payload = _payload()
    result = FetchResult(kind=FetchKind.FETCHED, payload=payload)
    request = _request(max_bytes=len(payload) - 1)

    with pytest.raises(AdapterError, match="invalid fetch result"):
        _ = _run_direct(_adapter(_ResultOffloader(result)), request)


def test_outer_async_boundary_rejects_typed_failed_result() -> None:
    offloader = _ResultOffloader(FetchResult(kind=FetchKind.FAILED))

    with pytest.raises(
        async_fetch.TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError,
        match="cannot process async fetched public-key bundle",
    ):
        _ = _run_loaded(_adapter(offloader))


def test_builder_rejects_foreign_https_fetcher_type() -> None:
    with pytest.raises(AdapterError, match="invalid synchronous HTTPS"):
        _ = _build_adapter(
            cast("HttpsFetcher", object()),
            _Offloader(),
        )


def test_builder_rejects_tampered_https_fetcher() -> None:
    value = replace(_https_fetcher(), fetcher_id="unsupported")

    with pytest.raises(AdapterError, match="invalid synchronous HTTPS"):
        _ = _build_adapter(value, _Offloader())


def test_builder_rejects_noncallable_offloader() -> None:
    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _build_adapter(
            _https_fetcher(),
            cast(
                "adapter.TicketAdmissionTelemetryLineageHttpsBundleOffloader",
                object(),
            ),
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact async HTTPS adapter type"):
        _ = _validate_adapter(cast("AsyncHttpsFetcher", object()))


def test_tampered_adapter_identity_fails_before_await() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _run_direct(value)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("fetcher_id", "", "fetcher identity must be"),
        ("resource_id", "", "resource identity must be"),
        ("source_id", "", "source identity must be"),
    ],
)
def test_empty_adapter_metadata_fails_before_await(
    field: str,
    value: str,
    match: str,
) -> None:
    tampered = replace(_adapter(), **{field: value})

    with pytest.raises(AdapterError, match=match):
        _ = _run_direct(tampered)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("fetcher_id", "other", "fetcher identity does not match"),
        ("resource_id", OTHER_RESOURCE_ID, "resource identity does not match"),
        ("source_id", OTHER_SOURCE_ID, "source identity does not match"),
    ],
)
def test_tampered_adapter_binding_fails_before_await(
    field: str,
    value: str,
    match: str,
) -> None:
    tampered = replace(_adapter(), **{field: value})

    with pytest.raises(AdapterError, match=match):
        _ = _run_direct(tampered)


def test_tampered_wrapped_fetcher_fails_before_await() -> None:
    tampered_fetcher = replace(_https_fetcher(), fetcher_id="unsupported")
    value = replace(_adapter(), fetcher=tampered_fetcher)

    with pytest.raises(AdapterError, match="invalid synchronous HTTPS"):
        _ = _run_direct(value)


def test_tampered_noncallable_offloader_fails_before_await() -> None:
    value = replace(
        _adapter(),
        offloader=cast(
            "adapter.TicketAdmissionTelemetryLineageHttpsBundleOffloader",
            object(),
        ),
    )

    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _run_direct(value)
