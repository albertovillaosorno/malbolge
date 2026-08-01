# File:
#   - test_ticket_admission_https_bundle_fetcher.py
# Path:
#   - tests/optimizer/test_ticket_admission_https_bundle_fetcher.py
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
#   - Concrete synchronous HTTPS public-key bundle transport regressions.
# - Must-Not:
#   - Use live sockets, credentials, redirects, retries, automatic trust roots,
#     certificates outside caller TLS state, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic HTTPS configs, responses, bundles, and tampering.
#   - Outputs: request, TLS, status, header, limit, close, and binding assertions.
#   - Side effects: monkeypatched in-process connection recording only.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact synchronous HTTPS behavior.
# - Summary:
#   - No-redirect caller-trusted HTTPS bundle fetch regressions.
# - Description:
#   - Proves exact endpoint binding and fail-closed HTTP response processing.
# - Usage:
#   - Runs without network access, files, accelerator hardware, or trust stores.
# - Defaults:
#   - Uses one synthetic key, port 443, TLS 1.2, and bounded JSON responses.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
#
# Large file:
#   - false
#

"""Concrete synchronous HTTPS detached public-key bundle fetch tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from http.client import HTTPException
from ssl import CERT_OPTIONAL
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast
from typing import override

import pytest

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

HttpsError = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError
)
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_https_id = https.ticket_admission_https_public_key_bundle_fetcher_id
_build_bundle = (
    bundle.build_ticket_admission_telemetry_lineage_public_key_bundle
)
_encode_bundle = (
    bundle.encode_ticket_admission_telemetry_lineage_public_key_bundle
)
_bundle_fingerprint = (
    bundle.ticket_admission_telemetry_lineage_public_key_bundle_fingerprint
)
_fetch_provider = (
    fetch.fetch_ticket_admission_telemetry_lineage_public_key_bundle_provider
)
_build_manifest = (
    manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)
_resolve_provider = (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider
)

HTTPS_FETCHER_ID = (
    "explicit-https-ticket-admission-telemetry-lineage-"
    "public-key-bundle-fetcher-v1"
)
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json?format=canonical"
SOURCE_ID = "source.test.https-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
PROVIDER_ID = "provider.test.https-public-keys"
ALGORITHM_ID = "test-only-public-digest-v1"
PUBLIC_KEY_ID = "public.test-key.2026-08"
REFERENCE_ID = "vault.public-key.2026-08"
PUBLIC_KEY = b"caller-owned-https-test-public-key"
GENESIS_SEQUENCE_ID = 0
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_GONE = 410
DEFAULT_TIMEOUT = 30.0
ONE_KEY = 1
TWO_CALLS = 2
SSL_CONTEXT_TEXT = "SSLContext"
AUTHORIZATION_HEADER = "Authorization"
OPEN_STAGE = "open"
REQUEST_STAGE = "request"
RESPONSE_STAGE = "response"
READ_STAGE = "read"
HEADER_FAILURE_MESSAGE = "header failure"


class _Response:
    def __init__(
        self,
        *,
        status: int = HTTP_OK,
        headers: dict[str, str | None] | None = None,
        payload: bytes = b"payload",
        read_error: HTTPException | OSError | ValueError | None = None,
    ) -> None:
        self.status: int = status
        self.headers: dict[str, str | None] = {
            key.lower(): value for key, value in (headers or {}).items()
        }
        self.payload: bytes = payload
        self.read_error: HTTPException | OSError | ValueError | None = (
            read_error
        )
        self.read_amounts: list[int | None] = []

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name.lower(), default)

    def read(self, amount: int | None = None) -> bytes:
        self.read_amounts.append(amount)
        if self.read_error is not None:
            raise self.read_error
        return self.payload


class _HeaderRaisingResponse(_Response):
    @override
    def getheader(self, name: str, default: str | None = None) -> str | None:
        _ = name, default
        raise ValueError(HEADER_FAILURE_MESSAGE)


class _Connection:
    def __init__(
        self,
        response: _Response,
        *,
        request_error: HTTPException | OSError | ValueError | None = None,
        response_error: HTTPException | OSError | ValueError | None = None,
        close_error: HTTPException | OSError | ValueError | None = None,
    ) -> None:
        self.response: _Response = response
        self.request_error: HTTPException | OSError | ValueError | None = (
            request_error
        )
        self.response_error: HTTPException | OSError | ValueError | None = (
            response_error
        )
        self.close_error: HTTPException | OSError | ValueError | None = (
            close_error
        )
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.getresponse_count: int = 0
        self.close_count: int = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> None:
        self.requests.append((method, url, dict(headers)))
        if self.request_error is not None:
            raise self.request_error

    def getresponse(self) -> _Response:
        self.getresponse_count += 1
        if self.response_error is not None:
            raise self.response_error
        return self.response

    def close(self) -> None:
        self.close_count += 1
        if self.close_error is not None:
            raise self.close_error


class _Opener:
    def __init__(
        self,
        connections: list[_Connection],
        *,
        error: HTTPException | OSError | ValueError | None = None,
    ) -> None:
        self.connections: list[_Connection] = connections
        self.error: HTTPException | OSError | ValueError | None = error
        self.configs: list[HttpsConfig] = []

    def __call__(self, config: HttpsConfig) -> _Connection:
        self.configs.append(config)
        if self.error is not None:
            raise self.error
        return self.connections.pop(0)


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _config() -> HttpsConfig:
    return HttpsConfig(
        host=HOST,
        resource_id=RESOURCE_ID,
        source_id=SOURCE_ID,
        target=TARGET,
        tls_context=_tls_context(),
        timeout_seconds=DEFAULT_TIMEOUT,
    )


def _fetcher(config: HttpsConfig | None = None) -> HttpsFetcher:
    return _build_https(_config() if config is None else config)


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


def _response(  # ruff: ignore[too-many-arguments]
    *,
    status: int = HTTP_OK,
    content_type: str | None = "application/json",
    content_encoding: str | None = None,
    content_length: str | None = None,
    payload: bytes | None = None,
) -> _Response:
    selected_payload = _payload() if payload is None else payload
    headers: dict[str, str | None] = {
        "Content-Type": content_type,
        "Content-Encoding": content_encoding,
        "Content-Length": (
            str(len(selected_payload))
            if content_length is None
            else content_length
        ),
    }
    return _Response(
        status=status,
        headers=headers,
        payload=selected_payload,
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    opener: _Opener,
) -> None:
    monkeypatch.setattr(https, "_open_connection", opener)


def _direct(
    monkeypatch: pytest.MonkeyPatch,
    connection: _Connection,
    *,
    request: FetchRequest | None = None,
    concrete: HttpsFetcher | None = None,
) -> tuple[FetchResult, _Opener]:
    opener = _Opener([connection])
    _install(monkeypatch, opener)
    selected = _fetcher() if concrete is None else concrete
    return selected(_request() if request is None else request), opener


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


def test_identity_defaults_and_repr_are_stable() -> None:
    concrete = _fetcher()
    config_repr = repr(concrete.config)
    fetcher_repr = repr(concrete)

    assert _https_id() == HTTPS_FETCHER_ID
    assert concrete.fetcher_id == HTTPS_FETCHER_ID
    assert concrete.config.port == https.DEFAULT_HTTPS_PUBLIC_KEY_BUNDLE_PORT
    assert concrete.config.timeout_seconds == DEFAULT_TIMEOUT
    assert HOST not in config_repr
    assert TARGET not in config_repr
    assert SSL_CONTEXT_TEXT not in config_repr
    assert HOST not in fetcher_repr
    assert TARGET not in fetcher_repr


def test_exact_https_get_returns_fetched_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    response = _response(payload=payload)
    connection = _Connection(response)

    concrete = _fetcher()
    result, opener = _direct(monkeypatch, connection, concrete=concrete)

    assert result.kind is FetchKind.FETCHED
    assert result.payload == payload
    assert opener.configs == [concrete.config]
    assert connection.requests == [
        (
            "GET",
            TARGET,
            {
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
    ]
    assert AUTHORIZATION_HEADER not in connection.requests[0][2]
    assert response.read_amounts == [_request().max_bytes + 1]
    assert connection.getresponse_count == 1
    assert connection.close_count == 1


def test_shared_fetch_boundary_materializes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_response())
    opener = _Opener([connection])
    _install(monkeypatch, opener)

    loaded = _fetch_provider(_fetcher(), _request())
    resolved = _resolve_provider(
        _manifest(),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert loaded.provider_id == PROVIDER_ID
    assert loaded.key_count == ONE_KEY
    assert loaded.source_id == SOURCE_ID
    assert loaded.resource_id == RESOURCE_ID
    assert resolved.request_count == ONE_KEY
    assert resolved.public_key_ids == (PUBLIC_KEY_ID,)
    assert resolved.trust.key_count == ONE_KEY


def test_repeated_calls_open_new_connections_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _Connection(_response())
    second = _Connection(_response())
    opener = _Opener([first, second])
    _install(monkeypatch, opener)
    concrete = _fetcher()
    request = _request()

    first_result = concrete(request)
    second_result = concrete(request)

    assert first_result.kind is FetchKind.FETCHED
    assert second_result.kind is FetchKind.FETCHED
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
def test_request_binding_mismatch_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
    source_id: str,
    resource_id: str,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)

    result = _fetcher()(_request(source_id=source_id, resource_id=resource_id))

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert opener.configs == []


def test_invalid_shared_request_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)
    request = replace(_request(), max_bytes=0)

    with pytest.raises(HttpsError, match="invalid HTTPS public-key bundle"):
        _ = _fetcher()(request)

    assert opener.configs == []


@pytest.mark.parametrize("status", [HTTP_NOT_FOUND, HTTP_GONE])
def test_missing_https_resource_is_typed_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    response = _response(status=status)
    connection = _Connection(response)

    result, _ = _direct(monkeypatch, connection)

    assert result == FetchResult(kind=FetchKind.UNAVAILABLE)
    assert response.read_amounts == []
    assert connection.close_count == 1


@pytest.mark.parametrize("status", [201, 204, 301, 302, 307, 308, 500])
def test_non_success_status_fails_without_redirect_or_body_read(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    response = _response(status=status)
    connection = _Connection(response)

    result, _ = _direct(monkeypatch, connection)

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert len(connection.requests) == 1
    assert response.read_amounts == []
    assert connection.close_count == 1


@pytest.mark.parametrize(
    "content_type",
    [
        "application/json",
        "Application/JSON; Charset=UTF-8",
        " application/json ; charset=utf-8 ",
    ],
)
def test_supported_json_content_types_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
) -> None:
    result, _ = _direct(
        monkeypatch,
        _Connection(_response(content_type=content_type)),
    )

    assert result.kind is FetchKind.FETCHED


@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        "text/json",
        "application/json; charset=ascii",
        "application/json, application/json",
        "application/json; charset=utf-8; version=1",
    ],
)
def test_unsupported_or_missing_content_type_fails(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str | None,
) -> None:
    response = _response(content_type=content_type)

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FAILED
    assert response.read_amounts == []


@pytest.mark.parametrize("content_encoding", [None, "identity", " Identity "])
def test_identity_content_encoding_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
    content_encoding: str | None,
) -> None:
    result, _ = _direct(
        monkeypatch,
        _Connection(_response(content_encoding=content_encoding)),
    )

    assert result.kind is FetchKind.FETCHED


@pytest.mark.parametrize(
    "content_encoding",
    ["gzip", "br", "identity, gzip", "chunked"],
)
def test_nonidentity_content_encoding_fails(
    monkeypatch: pytest.MonkeyPatch,
    content_encoding: str,
) -> None:
    response = _response(content_encoding=content_encoding)

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FAILED
    assert response.read_amounts == []


def test_missing_content_length_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _response()
    _ = response.headers.pop("content-length")

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FETCHED
    assert response.read_amounts == [_request().max_bytes + 1]


@pytest.mark.parametrize(
    "content_length",
    ["", "0", "00", "01", "-1", "+1", "1.0", "abc", "1, 1"],
)
def test_malformed_or_zero_content_length_fails_before_read(
    monkeypatch: pytest.MonkeyPatch,
    content_length: str,
) -> None:
    response = _response(content_length=content_length)

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FAILED
    assert response.read_amounts == []


def test_content_length_above_request_limit_fails_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    request = _request(max_bytes=len(payload))
    response = _response(content_length=str(len(payload) + 1), payload=payload)

    result, _ = _direct(
        monkeypatch,
        _Connection(response),
        request=request,
    )

    assert result.kind is FetchKind.FAILED
    assert response.read_amounts == []


def test_content_length_must_match_actual_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    response = _response(content_length=str(len(payload) - 1), payload=payload)

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FAILED
    assert response.read_amounts == [_request().max_bytes + 1]


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        cast("bytes", cast("object", bytearray(b"foreign"))),
    ],
)
def test_body_requires_exact_nonempty_bytes(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    response = _response(payload=payload, content_length=str(len(payload)))

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FAILED


def test_body_read_is_bounded_to_request_limit_plus_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    request = _request(max_bytes=len(payload))
    response = _response(payload=payload)

    result, _ = _direct(
        monkeypatch,
        _Connection(response),
        request=request,
    )

    assert result.kind is FetchKind.FETCHED
    assert response.read_amounts == [len(payload) + 1]


def test_body_larger_than_request_limit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    request = _request(max_bytes=len(payload) - 1)
    response = _response(
        content_length=None,
        payload=payload,
    )
    _ = response.headers.pop("content-length")

    result, _ = _direct(
        monkeypatch,
        _Connection(response),
        request=request,
    )

    assert result.kind is FetchKind.FAILED


@pytest.mark.parametrize(
    "stage",
    [OPEN_STAGE, REQUEST_STAGE, RESPONSE_STAGE, READ_STAGE],
)
def test_transport_failures_return_typed_failed_and_close_when_opened(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    response = _response()
    if stage == READ_STAGE:
        response.read_error = OSError("read failed")
    connection = _Connection(
        response,
        request_error=(
            OSError("request failed") if stage == REQUEST_STAGE else None
        ),
        response_error=(
            HTTPException("response failed")
            if stage == RESPONSE_STAGE
            else None
        ),
    )
    opener = _Opener(
        [connection],
        error=(OSError("open failed") if stage == OPEN_STAGE else None),
    )
    _install(monkeypatch, opener)

    result = _fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    expected_close_count = 0 if stage == OPEN_STAGE else 1
    assert connection.close_count == expected_close_count


def test_close_failure_overrides_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(
        _response(),
        close_error=OSError("close failed"),
    )

    result, _ = _direct(monkeypatch, connection)

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert connection.close_count == 1


def test_real_https_connection_constructor_receives_exact_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_response())
    calls: list[tuple[str, int, float, SSLContext]] = []

    def constructor(
        host: str,
        port: int,
        *,
        timeout: float,
        context: SSLContext,
    ) -> _Connection:
        calls.append((host, port, timeout, context))
        return connection

    monkeypatch.setattr(https, "HTTPSConnection", constructor)
    config = _config()

    result = _fetcher(config)(_request())

    assert result.kind is FetchKind.FETCHED
    assert calls == [
        (
            HOST,
            https.DEFAULT_HTTPS_PUBLIC_KEY_BUNDLE_PORT,
            DEFAULT_TIMEOUT,
            config.tls_context,
        )
    ]
    assert connection.close_count == 1


def test_foreign_config_type_fails_build() -> None:
    with pytest.raises(HttpsError, match="exact HTTPS config type"):
        _ = _build_https(cast("HttpsConfig", object()))


@pytest.mark.parametrize(
    "host",
    [
        "",
        "Keys.example.test",
        "keys example.test",
        "-keys.example.test",
        "keys-.example.test",
        "keys.example.test.",
        "keys_underscore.example.test",
    ],
)
def test_host_requires_canonical_lowercase_ascii_dns(host: str) -> None:
    with pytest.raises(HttpsError, match="canonical lowercase ASCII DNS"):
        _ = _build_https(replace(_config(), host=host))


@pytest.mark.parametrize("port", [0, 65536, True, cast("int", object())])
def test_port_requires_exact_bounded_integer(port: int) -> None:
    with pytest.raises(HttpsError, match="integer from 1 through 65535"):
        _ = _build_https(replace(_config(), port=port))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_id", "", "source identity must use"),
        ("source_id", "bad source", "source identity must use"),
        ("resource_id", "", "resource identity must use"),
        ("resource_id", "bad resource", "resource identity must use"),
    ],
)
def test_source_and_resource_identifiers_are_exact(
    field: str,
    value: str,
    match: str,
) -> None:
    with pytest.raises(HttpsError, match=match):
        _ = _build_https(replace(_config(), **{field: value}))


@pytest.mark.parametrize(
    "target",
    [
        "",
        "relative/path",
        "https://keys.example.test/bundle.json",
        "//keys.example.test/bundle.json",
        "/bundle.json#fragment",
        "/bundle json",
        r"/bundle\json",
        "/búndle.json",
    ],
)
def test_target_requires_canonical_ascii_origin_form(target: str) -> None:
    with pytest.raises(HttpsError, match="target"):
        _ = _build_https(replace(_config(), target=target))


@pytest.mark.parametrize(
    "timeout_seconds",
    [
        0.0,
        -1.0,
        float("inf"),
        float("nan"),
        cast("float", cast("object", 1)),
    ],
)
def test_timeout_requires_positive_finite_exact_float(
    timeout_seconds: float,
) -> None:
    with pytest.raises(HttpsError, match="positive finite float"):
        _ = _build_https(replace(_config(), timeout_seconds=timeout_seconds))


def test_timeout_cannot_exceed_supported_maximum() -> None:
    with pytest.raises(HttpsError, match="timeout exceeds supported maximum"):
        _ = _build_https(
            replace(
                _config(),
                timeout_seconds=(
                    https.MAX_HTTPS_PUBLIC_KEY_BUNDLE_TIMEOUT_SECONDS + 1.0
                ),
            )
        )


def test_tls_context_must_use_exact_type() -> None:
    config = replace(
        _config(),
        tls_context=cast("SSLContext", object()),
    )

    with pytest.raises(HttpsError, match="exact SSLContext type"):
        _ = _build_https(config)


def test_tls_context_must_enable_hostname_checking() -> None:
    context = _tls_context()
    context.check_hostname = False

    with pytest.raises(HttpsError, match="enable hostname checking"):
        _ = _build_https(replace(_config(), tls_context=context))


def test_tls_context_must_require_peer_certificates() -> None:
    context = _tls_context()
    context.verify_mode = CERT_OPTIONAL

    with pytest.raises(HttpsError, match="require peer certificates"):
        _ = _build_https(replace(_config(), tls_context=context))


def test_tls_context_must_require_tls_1_2_or_newer() -> None:
    context = _tls_context()
    context.minimum_version = TLSVersion.MINIMUM_SUPPORTED

    with pytest.raises(HttpsError, match=r"TLS 1\.2 or newer"):
        _ = _build_https(replace(_config(), tls_context=context))


def test_builder_retains_exact_caller_owned_tls_context() -> None:
    context = _tls_context()
    config = replace(_config(), tls_context=context)

    concrete = _build_https(config)

    assert concrete.config is config
    assert concrete.config.tls_context is context


def test_tampered_fetcher_identity_is_detected_on_use() -> None:
    concrete = _fetcher()
    object.__setattr__(  # ruff: ignore[unnecessary-dunder-call]
        concrete, "fetcher_id", "unsupported"
    )

    with pytest.raises(HttpsError, match="fetcher identity is unsupported"):
        _ = concrete(_request())


def test_tampered_fetcher_config_is_detected_on_use() -> None:
    concrete = _fetcher()
    object.__setattr__(  # ruff: ignore[unnecessary-dunder-call]
        concrete,
        "config",
        replace(concrete.config, target="relative"),
    )

    with pytest.raises(HttpsError, match="target"):
        _ = concrete(_request())


def test_boolean_or_foreign_status_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for status in (
        True,
        cast("int", cast("object", "200")),
    ):
        response = _response()
        response.status = status
        result, _ = _direct(monkeypatch, _Connection(response))
        assert result.kind is FetchKind.FAILED
        assert response.read_amounts == []


def test_exact_content_length_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    response = _response(content_length=str(len(payload)), payload=payload)

    result, _ = _direct(monkeypatch, _Connection(response))

    assert result.kind is FetchKind.FETCHED
    assert result.payload == payload


def test_response_header_failure_returns_failed_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_HeaderRaisingResponse())

    result, _ = _direct(monkeypatch, connection)

    assert result.kind is FetchKind.FAILED
    assert connection.close_count == 1
