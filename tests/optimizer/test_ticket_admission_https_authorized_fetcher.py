# File:
#   - test_ticket_admission_https_authorized_fetcher.py
# Path:
#   - tests/optimizer/test_ticket_admission_https_authorized_fetcher.py
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
#   - Explicit Authorization-injecting synchronous HTTPS fetcher regressions.
# - Must-Not:
#   - Use live sockets, resolve schemes, discover credentials, retry, redirect,
#     cache, persist, log secrets, load trust roots, or change policy.
# - Allows:
#   - Inputs: exact HTTPS fetchers, resolved authorization, requests, and faults.
#   - Outputs: binding, header, response, secrecy, and tampering assertions.
#   - Side effects: monkeypatched in-memory HTTPS connections only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact authorized HTTPS boundary.
# - Summary:
#   - Explicit authorized HTTPS detached-key bundle fetcher regressions.
# - Description:
#   - Proves exact header injection adds no credential or transport policy.
# - Usage:
#   - Runs without network access, async plugins, or accelerator hardware.
# - Defaults:
#   - Uses one canonical bundle and one caller-owned Bearer-shaped value.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Explicit Authorization-injecting HTTPS bundle fetcher tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long]
# ruff: file-ignore[undocumented-public-function,too-many-positional-arguments]

from __future__ import annotations

from dataclasses import replace
from http.client import HTTPException
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

import pytest

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

AuthorizedError = (
    authorized.TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError
)
AuthorizedFetcher = (
    authorized.TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher
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
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
_build_authorized = (
    authorized.build_ticket_admission_authorized_https_bundle_fetcher
)
_validate_authorized = (
    authorized.validate_ticket_admission_authorized_https_bundle_fetcher
)
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_resolve_auth = auth.resolve_ticket_admission_https_authorization
_validate_resolved_auth = (
    auth.validate_ticket_admission_resolved_https_authorization
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
_fetch_provider = (
    fetch.fetch_ticket_admission_telemetry_lineage_public_key_bundle_provider
)

ADAPTER_ID = (
    "authorized-https-ticket-admission-lineage-public-key-bundle-fetcher-v1"
)
AUTHORIZATION_PROVIDER_ID = "credential-provider.test.authorized"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json"
SOURCE_ID = "source.test.authorized-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
FETCH_PROVIDER_ID = "provider.test.authorized-public-keys"
OTHER_FETCH_PROVIDER_ID = "provider.test.other-public-keys"
ALGORITHM_ID = "test-only-public-digest-v1"
PUBLIC_KEY_ID = "public.test-key.2026-08"
REFERENCE_ID = "vault.public-key.2026-08"
PUBLIC_KEY = b"caller-owned-authorized-https-test-public-key"
AUTHORIZATION_VALUE = "Bearer caller-owned-authorized-test-token"
BASIC_AUTHORIZATION = "Basic Y2FsbGVyOm93bmVk"
AUTHORIZATION_BYTES = AUTHORIZATION_VALUE.encode("ascii")
AUTHORIZATION_FIELD = b"authorization_value"
FETCHER_FIELD = b"fetcher="
AUTHORIZATION_OBJECT_FIELD = b"authorization="
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_GONE = 410
HTTP_REDIRECT = 302
ONE_KEY = 1
ONE_CALL = 1
TWO_CALLS = 2
GENESIS_SEQUENCE_ID = 0
REQUEST_FAILURE_PHASE = "request"
RESPONSE_FAILURE_PHASE = "response"
READ_FAILURE_PHASE = "read"


class _Response:
    def __init__(
        self,
        *,
        payload: bytes,
        status: int = HTTP_OK,
        headers: dict[str, str | None] | None = None,
        read_error: BaseException | None = None,
    ) -> None:
        self.status: int = status
        self.payload: bytes = payload
        self.headers: dict[str, str | None] = {
            key.lower(): value for key, value in (headers or {}).items()
        }
        self.read_error: BaseException | None = read_error
        self.read_amounts: list[int | None] = []

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name.lower(), default)

    def read(self, amount: int | None = None) -> bytes:
        self.read_amounts.append(amount)
        if self.read_error is not None:
            raise self.read_error
        return self.payload


class _Connection:
    def __init__(
        self,
        response: _Response,
        *,
        request_error: BaseException | None = None,
        response_error: BaseException | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        self.response: _Response = response
        self.request_error: BaseException | None = request_error
        self.response_error: BaseException | None = response_error
        self.close_error: BaseException | None = close_error
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
        error: BaseException | None = None,
    ) -> None:
        self.connections: list[_Connection] = connections
        self.error: BaseException | None = error
        self.configs: list[HttpsConfig] = []

    def __call__(self, config: HttpsConfig) -> _Connection:
        self.configs.append(config)
        if self.error is not None:
            raise self.error
        return self.connections.pop(0)


class _AuthProvider:
    def __init__(self, value: str = AUTHORIZATION_VALUE) -> None:
        self.value: str = value
        self.requests: list[AuthRequest] = []

    def __call__(self, request: AuthRequest) -> AuthResult:
        self.requests.append(request)
        return AuthResult(
            kind=AuthKind.RESOLVED,
            authorization_value=self.value,
        )


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _https_fetcher(
    *,
    resource_id: str = RESOURCE_ID,
    source_id: str = SOURCE_ID,
) -> HttpsFetcher:
    return _build_https(
        HttpsConfig(
            host=HOST,
            resource_id=resource_id,
            source_id=source_id,
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
    return _build_bundle((entry,), provider_id=FETCH_PROVIDER_ID)


def _payload() -> bytes:
    return _encode_bundle(_bundle())


def _request(
    *,
    bundle_fingerprint: str | None = None,
    provider_id: str = FETCH_PROVIDER_ID,
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
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _resolved_authorization(
    *,
    fetcher: HttpsFetcher | None = None,
    request: FetchRequest | None = None,
    provider: _AuthProvider | None = None,
) -> tuple[ResolvedAuth, _AuthProvider]:
    selected_fetcher = _https_fetcher() if fetcher is None else fetcher
    selected_request = _request() if request is None else request
    selected_provider = _AuthProvider() if provider is None else provider
    resolved = _resolve_auth(
        selected_fetcher,
        selected_request,
        selected_provider,
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )
    return resolved, selected_provider


def _authorized_fetcher(
    *,
    fetcher: HttpsFetcher | None = None,
    authorization: ResolvedAuth | None = None,
) -> AuthorizedFetcher:
    selected_fetcher = _https_fetcher() if fetcher is None else fetcher
    selected_authorization = authorization
    if selected_authorization is None:
        selected_authorization, _ = _resolved_authorization(
            fetcher=selected_fetcher
        )
    return _build_authorized(selected_fetcher, selected_authorization)


def _response(
    *,
    payload: bytes | None = None,
    status: int = HTTP_OK,
    headers: dict[str, str | None] | None = None,
    read_error: BaseException | None = None,
) -> _Response:
    selected_payload = _payload() if payload is None else payload
    selected_headers: dict[str, str | None] = {
        "Content-Type": "application/json",
        "Content-Length": str(len(selected_payload)),
    }
    if headers is not None:
        selected_headers.update(headers)
    return _Response(
        payload=selected_payload,
        status=status,
        headers=selected_headers,
        read_error=read_error,
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    opener: _Opener,
) -> None:
    monkeypatch.setattr(https, "_open_connection", opener)


def test_identity_metadata_validator_and_repr_are_stable() -> None:
    authorization, _ = _resolved_authorization()
    value = _authorized_fetcher(authorization=authorization)
    representation = repr(value).encode("utf-8")

    assert (
        authorized.ticket_admission_authorized_https_bundle_fetcher_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.authorization_byte_count == len(AUTHORIZATION_BYTES)
    assert value.authorization_provider_id == AUTHORIZATION_PROVIDER_ID
    assert value.bundle_fingerprint == _request().bundle_fingerprint
    assert value.fetch_provider_id == FETCH_PROVIDER_ID
    assert value.resource_id == RESOURCE_ID
    assert value.source_id == SOURCE_ID
    assert _validate_authorized(value) is value
    assert _validate_resolved_auth(authorization) is authorization
    assert AUTHORIZATION_BYTES not in representation
    assert AUTHORIZATION_FIELD not in representation
    assert FETCHER_FIELD not in representation
    assert AUTHORIZATION_OBJECT_FIELD not in representation
    assert HOST.encode() not in representation
    assert TARGET.encode() not in representation


def test_exact_authorized_get_injects_one_opaque_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _response()
    connection = _Connection(response)
    opener = _Opener([connection])
    _install(monkeypatch, opener)
    fetcher = _https_fetcher()
    authorization, provider = _resolved_authorization(fetcher=fetcher)
    value = _authorized_fetcher(fetcher=fetcher, authorization=authorization)

    result = value(_request())

    assert result.kind is FetchKind.FETCHED
    assert result.payload == _payload()
    assert len(provider.requests) == ONE_CALL
    assert opener.configs == [fetcher.config]
    assert connection.requests == [
        (
            "GET",
            TARGET,
            {
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Authorization": AUTHORIZATION_VALUE,
                "Connection": "close",
            },
        )
    ]
    assert response.read_amounts == [_request().max_bytes + 1]
    assert connection.getresponse_count == ONE_CALL
    assert connection.close_count == ONE_CALL


def test_authorization_scheme_and_text_are_not_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_response())
    _install(monkeypatch, _Opener([connection]))
    fetcher = _https_fetcher()
    provider = _AuthProvider(BASIC_AUTHORIZATION)
    authorization, _ = _resolved_authorization(
        fetcher=fetcher,
        provider=provider,
    )

    result = _authorized_fetcher(
        fetcher=fetcher,
        authorization=authorization,
    )(_request())

    assert result.kind is FetchKind.FETCHED
    assert connection.requests[0][2]["Authorization"] == BASIC_AUTHORIZATION


def test_shared_fetch_boundary_materializes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(_response())
    _install(monkeypatch, _Opener([connection]))

    loaded = _fetch_provider(_authorized_fetcher(), _request())

    assert loaded.bundle_fingerprint == _request().bundle_fingerprint
    assert loaded.key_count == ONE_KEY
    assert loaded.provider_id == FETCH_PROVIDER_ID
    assert loaded.resource_id == RESOURCE_ID
    assert loaded.source_id == SOURCE_ID


def test_repeated_calls_reuse_explicit_authorization_without_hidden_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _Connection(_response())
    second = _Connection(_response())
    opener = _Opener([first, second])
    _install(monkeypatch, opener)
    fetcher = _https_fetcher()
    authorization, provider = _resolved_authorization(fetcher=fetcher)
    value = _authorized_fetcher(fetcher=fetcher, authorization=authorization)

    first_result = value(_request())
    second_result = value(_request())

    assert first_result.kind is FetchKind.FETCHED
    assert second_result.kind is FetchKind.FETCHED
    assert len(provider.requests) == ONE_CALL
    assert len(opener.configs) == TWO_CALLS
    assert first.close_count == ONE_CALL
    assert second.close_count == ONE_CALL


@pytest.mark.parametrize(
    ("fetch_request", "match_field"),
    [
        (
            _request(
                bundle_fingerprint=(
                    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
                    + ("1" * 64)
                )
            ),
            "bundle",
        ),
        (_request(provider_id=OTHER_FETCH_PROVIDER_ID), "provider"),
        (_request(resource_id=OTHER_RESOURCE_ID), "resource"),
        (_request(source_id=OTHER_SOURCE_ID), "source"),
    ],
)
def test_request_binding_mismatch_returns_failed_without_connection(
    monkeypatch: pytest.MonkeyPatch,
    fetch_request: FetchRequest,
    match_field: str,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)

    result = _authorized_fetcher()(fetch_request)

    assert match_field
    assert result == FetchResult(kind=FetchKind.FAILED)
    assert opener.configs == []


def test_invalid_request_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)

    with pytest.raises(AuthorizedError, match="invalid authorized HTTPS"):
        _ = _authorized_fetcher()(replace(_request(), max_bytes=0))

    assert opener.configs == []


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (HTTP_NOT_FOUND, FetchKind.UNAVAILABLE),
        (HTTP_GONE, FetchKind.UNAVAILABLE),
        (HTTP_REDIRECT, FetchKind.FAILED),
        (500, FetchKind.FAILED),
    ],
)
def test_http_status_mapping_matches_base_transport(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    expected: FetchKind,
) -> None:
    response = _response(status=status)
    connection = _Connection(response)
    _install(monkeypatch, _Opener([connection]))

    result = _authorized_fetcher()(_request())

    assert result.kind is expected
    assert result.payload is None
    assert response.read_amounts == []
    assert connection.close_count == ONE_CALL


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Type": "text/plain"},
        {"Content-Encoding": "gzip"},
        {"Content-Length": "0"},
        {"Content-Length": "01"},
    ],
)
def test_invalid_response_metadata_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str | None],
) -> None:
    response = _response(headers=headers)
    connection = _Connection(response)
    _install(monkeypatch, _Opener([connection]))

    result = _authorized_fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert connection.close_count == ONE_CALL


def test_content_length_mismatch_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload()
    response = _response(headers={"Content-Length": str(len(payload) + 1)})
    connection = _Connection(response)
    _install(monkeypatch, _Opener([connection]))

    result = _authorized_fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert response.read_amounts == [_request().max_bytes + 1]


@pytest.mark.parametrize(
    "error",
    [HTTPException("open"), OSError("open"), ValueError("open")],
)
def test_connection_open_failure_returns_failed_without_retry(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    opener = _Opener([], error=error)
    _install(monkeypatch, opener)

    result = _authorized_fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert len(opener.configs) == ONE_CALL


@pytest.mark.parametrize(
    ("field", "error"),
    [
        (REQUEST_FAILURE_PHASE, HTTPException("request")),
        (RESPONSE_FAILURE_PHASE, OSError("response")),
        (READ_FAILURE_PHASE, ValueError("read")),
    ],
)
def test_exchange_failure_returns_failed_and_closes_once(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    error: BaseException,
) -> None:
    response = _response(
        read_error=error if field == READ_FAILURE_PHASE else None
    )
    connection = _Connection(
        response,
        request_error=error if field == REQUEST_FAILURE_PHASE else None,
        response_error=error if field == RESPONSE_FAILURE_PHASE else None,
    )
    _install(monkeypatch, _Opener([connection]))

    result = _authorized_fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert len(connection.requests) == ONE_CALL
    assert connection.close_count == ONE_CALL


def test_close_failure_overrides_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _Connection(
        _response(),
        close_error=OSError("close"),
    )
    _install(monkeypatch, _Opener([connection]))

    result = _authorized_fetcher()(_request())

    assert result == FetchResult(kind=FetchKind.FAILED)
    assert connection.close_count == ONE_CALL


def test_builder_rejects_foreign_https_fetcher() -> None:
    authorization, _ = _resolved_authorization()

    with pytest.raises(AuthorizedError, match="invalid HTTPS fetcher"):
        _ = _build_authorized(
            cast("HttpsFetcher", object()),
            authorization,
        )


def test_builder_rejects_tampered_https_fetcher() -> None:
    authorization, _ = _resolved_authorization()
    tampered = replace(_https_fetcher(), fetcher_id="unsupported")

    with pytest.raises(AuthorizedError, match="invalid HTTPS fetcher"):
        _ = _build_authorized(tampered, authorization)


def test_builder_rejects_foreign_resolved_authorization() -> None:
    with pytest.raises(AuthorizedError, match="invalid resolved Authorization"):
        _ = _build_authorized(
            _https_fetcher(),
            cast("ResolvedAuth", object()),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authorization_byte_count", 0),
        ("authorization_provider_id", "bad provider"),
        ("authorization_value", "Bearer\ntoken"),
        ("bundle_fingerprint", "bad"),
        ("fetch_provider_id", "bad provider"),
        ("header_name", "Proxy-Authorization"),
        ("resource_id", "bad resource"),
        ("source_id", "bad source"),
    ],
)
def test_builder_rejects_tampered_resolved_authorization(
    field: str,
    value: int | str,
) -> None:
    authorization, _ = _resolved_authorization()
    tampered = replace(authorization, **{field: value})

    with pytest.raises(AuthorizedError, match="invalid resolved Authorization"):
        _ = _build_authorized(_https_fetcher(), tampered)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("resource_id", OTHER_RESOURCE_ID, "resource identity does not match"),
        ("source_id", OTHER_SOURCE_ID, "source identity does not match"),
    ],
)
def test_builder_rejects_authorization_fetcher_binding_mismatch(
    field: str,
    value: str,
    match: str,
) -> None:
    authorization, _ = _resolved_authorization()
    tampered = replace(authorization, **{field: value})

    with pytest.raises(AuthorizedError, match=match):
        _ = _build_authorized(_https_fetcher(), tampered)


def test_validator_rejects_foreign_authorized_fetcher_type() -> None:
    with pytest.raises(AuthorizedError, match="exact authorized HTTPS type"):
        _ = _validate_authorized(cast("AuthorizedFetcher", object()))


def test_tampered_adapter_identity_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)
    tampered = replace(_authorized_fetcher(), adapter_id="unsupported")

    with pytest.raises(
        AuthorizedError, match="fetcher identity is unsupported"
    ):
        _ = tampered(_request())

    assert opener.configs == []


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("fetcher_id", "unsupported", "copied fetcher identity"),
        ("authorization_byte_count", 1, "copied authorization byte count"),
        (
            "authorization_provider_id",
            "credential-provider.test.other",
            "copied authorization provider identity",
        ),
        (
            "bundle_fingerprint",
            "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
            + ("1" * 64),
            "copied bundle fingerprint",
        ),
        (
            "fetch_provider_id",
            OTHER_FETCH_PROVIDER_ID,
            "copied fetch provider identity",
        ),
        ("resource_id", OTHER_RESOURCE_ID, "copied resource identity"),
        ("source_id", OTHER_SOURCE_ID, "copied source identity"),
    ],
)
def test_tampered_copied_adapter_binding_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: int | str,
    match: str,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)
    tampered = replace(_authorized_fetcher(), **{field: value})

    with pytest.raises(AuthorizedError, match=match):
        _ = tampered(_request())

    assert opener.configs == []


def test_tampered_wrapped_https_fetcher_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)
    wrapped = replace(_https_fetcher(), fetcher_id="unsupported")
    tampered = replace(_authorized_fetcher(), fetcher=wrapped)

    with pytest.raises(AuthorizedError, match="invalid HTTPS fetcher"):
        _ = tampered(_request())

    assert opener.configs == []


def test_tampered_wrapped_authorization_fails_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = _Opener([])
    _install(monkeypatch, opener)
    authorization, _ = _resolved_authorization()
    wrapped = replace(authorization, authorization_value="Bearer\ntoken")
    tampered = replace(_authorized_fetcher(), authorization=wrapped)

    with pytest.raises(AuthorizedError, match="invalid resolved Authorization"):
        _ = tampered(_request())

    assert opener.configs == []


def test_public_resolved_authorization_validator_returns_exact_value() -> None:
    authorization, _ = _resolved_authorization()

    assert _validate_resolved_auth(authorization) is authorization


def test_public_resolved_authorization_validator_rejects_foreign_type() -> None:
    with pytest.raises(
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError,
        match="exact resolved type",
    ):
        _ = _validate_resolved_auth(cast("ResolvedAuth", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "authorization_byte_count",
            True,
            "byte count does not match value",
        ),
        (
            "authorization_provider_id",
            "bad provider",
            "authorization provider identity",
        ),
        (
            "authorization_value",
            "Bearer\ntoken",
            "unsupported characters",
        ),
        ("bundle_fingerprint", "bad", "bundle fingerprint is malformed"),
        ("fetch_provider_id", "bad provider", "fetch provider identity"),
        ("header_name", "Proxy-Authorization", "header name is unsupported"),
        ("resource_id", "bad resource", "resource identity"),
        ("source_id", "bad source", "source identity"),
    ],
)
def test_public_resolved_authorization_validator_rejects_tampering(
    field: str,
    value: object,
    match: str,
) -> None:
    authorization, _ = _resolved_authorization()

    with pytest.raises(
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError,
        match=match,
    ):
        _ = _validate_resolved_auth(replace(authorization, **{field: value}))
