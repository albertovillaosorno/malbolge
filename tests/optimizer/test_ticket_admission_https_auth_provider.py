# File:
#   - test_ticket_admission_https_auth_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_https_auth_provider.py
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
#   - Explicit synchronous HTTPS Authorization-provider port regressions.
# - Must-Not:
#   - Use sockets, inject headers, select schemes, discover credentials,
#     retry, cache, persist, log secrets, load trust roots, or change policy.
# - Allows:
#   - Inputs: exact HTTPS fetchers, fetch requests, providers, and tampering.
#   - Outputs: preflight, one-call, bounds, secrecy, and failure assertions.
#   - Side effects: in-memory caller-provider recording only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact Authorization-provider boundary.
# - Summary:
#   - One-call bounded HTTPS Authorization credential-provider regressions.
# - Description:
#   - Proves opaque credential resolution adds no scheme, retry, or cache policy.
# - Usage:
#   - Runs without network access, files, async plugins, or accelerator hardware.
# - Defaults:
#   - Uses one canonical bundle request and a 4096-byte Authorization limit.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
#
# Large file:
#   - false
#

"""Explicit synchronous HTTPS Authorization credential-provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

AuthError = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthKind = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
ResolvedAuth = auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization
PreparedAuth = auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization
HttpsFetcher = https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_resolve = auth.resolve_ticket_admission_https_authorization
_prepare = auth.prepare_ticket_admission_https_authorization
_materialize = auth.materialize_ticket_admission_https_authorization
_validate_prepared = auth.validate_ticket_admission_prepared_https_authorization
_validate_request = auth.validate_ticket_admission_https_authorization_request
_validate_result = auth.validate_ticket_admission_https_authorization_result
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher

PORT_ID = "explicit-ticket-admission-lineage-https-authorization-provider-v1"
AUTHORIZATION_PROVIDER_ID = "credential-provider.test.authorization"
OTHER_AUTHORIZATION_PROVIDER_ID = "credential-provider.test.other"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/current.json"
SOURCE_ID = "source.test.authorization-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_SOURCE_ID = "source.test.other-key-service"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
FETCH_PROVIDER_ID = "provider.test.authorization-public-keys"
BUNDLE_FINGERPRINT = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("0" * 64)
)
AUTHORIZATION_VALUE = "Bearer caller-owned-test-token"
BASIC_VALUE = "Basic Y2FsbGVyOm93bmVk"
CUSTOM_VALUE = "Signature keyId=test,algorithm=test-only"
VENDOR_DETAIL = "credential backend detail must not cross boundary"
AUTHORIZATION_FIELD = b"authorization_value"
AUTHORIZATION_BYTES = AUTHORIZATION_VALUE.encode("ascii")
ONE_CALL = 1
TWO_CALLS = 2
AUTHORIZATION_HEADER_NAME = "Authorization"
DEFAULT_AUTHORIZATION_BYTES = 4096
MAX_AUTHORIZATION_BYTES = 16384


class _Provider:
    def __init__(self, result: AuthResult) -> None:
        self.result: AuthResult = result
        self.requests: list[AuthRequest] = []

    def __call__(self, request: AuthRequest) -> AuthResult:
        self.requests.append(request)
        return self.result


class _RaisingProvider:
    def __init__(self) -> None:
        self.requests: list[AuthRequest] = []

    def __call__(self, request: AuthRequest) -> AuthResult:
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


def _provider(value: str = AUTHORIZATION_VALUE) -> _Provider:
    return _Provider(_resolved(value))


def _resolve_value(  # ruff: ignore[too-many-arguments]
    provider: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProvider,
    *,
    fetcher: HttpsFetcher | None = None,
    request: FetchRequest | None = None,
    authorization_provider_id: str = AUTHORIZATION_PROVIDER_ID,
    max_authorization_bytes: int = auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES,
) -> ResolvedAuth:
    return _resolve(
        _fetcher() if fetcher is None else fetcher,
        _request() if request is None else request,
        provider,
        authorization_provider_id=authorization_provider_id,
        max_authorization_bytes=max_authorization_bytes,
    )


def test_identity_defaults_and_result_kinds_are_stable() -> None:
    assert auth.ticket_admission_https_authorization_provider_id() == PORT_ID
    assert auth.HTTPS_AUTHORIZATION_HEADER_NAME == AUTHORIZATION_HEADER_NAME
    assert (
        auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES
        == DEFAULT_AUTHORIZATION_BYTES
    )
    assert auth.MAX_HTTPS_AUTHORIZATION_BYTES == MAX_AUTHORIZATION_BYTES
    assert tuple(AuthKind) == (
        AuthKind.RESOLVED,
        AuthKind.UNAVAILABLE,
        AuthKind.FAILED,
    )
    assert tuple(kind.value for kind in AuthKind) == (
        "resolved",
        "unavailable",
        "failed",
    )


def test_exact_resolution_calls_provider_once_with_bound_metadata() -> None:
    provider = _provider()

    resolved = _resolve_value(provider)

    assert len(provider.requests) == ONE_CALL
    provider_request = provider.requests[0]
    assert (
        provider_request.authorization_provider_id == AUTHORIZATION_PROVIDER_ID
    )
    assert provider_request.bundle_fingerprint == BUNDLE_FINGERPRINT
    assert provider_request.fetch_provider_id == FETCH_PROVIDER_ID
    assert provider_request.resource_id == RESOURCE_ID
    assert provider_request.source_id == SOURCE_ID
    assert resolved.authorization_value == AUTHORIZATION_VALUE
    assert resolved.authorization_byte_count == len(AUTHORIZATION_BYTES)
    assert resolved.authorization_provider_id == AUTHORIZATION_PROVIDER_ID
    assert resolved.bundle_fingerprint == BUNDLE_FINGERPRINT
    assert resolved.fetch_provider_id == FETCH_PROVIDER_ID
    assert resolved.header_name == AUTHORIZATION_HEADER_NAME
    assert resolved.resource_id == RESOURCE_ID
    assert resolved.source_id == SOURCE_ID


def test_result_and_resolved_value_hide_credential_text() -> None:
    result = _resolved()
    resolved = _resolve_value(_Provider(result))

    result_repr = repr(result).encode("utf-8")
    resolved_repr = repr(resolved).encode("utf-8")
    assert AUTHORIZATION_BYTES not in result_repr
    assert AUTHORIZATION_BYTES not in resolved_repr
    assert AUTHORIZATION_FIELD not in result_repr
    assert AUTHORIZATION_FIELD not in resolved_repr


def test_repeated_resolution_has_no_cache() -> None:
    provider = _provider()

    first = _resolve_value(provider)
    second = _resolve_value(provider)

    assert first == second
    assert len(provider.requests) == TWO_CALLS


@pytest.mark.parametrize(
    "value", [AUTHORIZATION_VALUE, BASIC_VALUE, CUSTOM_VALUE]
)
def test_scheme_and_opaque_value_are_caller_owned(value: str) -> None:
    resolved = _resolve_value(_provider(value))

    assert resolved.authorization_value == value
    assert resolved.authorization_byte_count == len(value.encode("ascii"))


def test_internal_spaces_are_allowed_without_normalization() -> None:
    value = "Custom alpha  beta"

    resolved = _resolve_value(_provider(value))

    assert resolved.authorization_value == value


def test_exact_configured_byte_limit_is_allowed() -> None:
    value = "X" * len(AUTHORIZATION_VALUE)

    resolved = _resolve_value(
        _provider(value),
        max_authorization_bytes=len(value),
    )

    assert resolved.authorization_byte_count == len(value)


@pytest.mark.parametrize(
    ("source_id", "resource_id", "match"),
    [
        (
            OTHER_SOURCE_ID,
            RESOURCE_ID,
            "source identity does not match HTTPS fetcher",
        ),
        (
            SOURCE_ID,
            OTHER_RESOURCE_ID,
            "resource identity does not match HTTPS fetcher",
        ),
    ],
)
def test_fetch_binding_mismatch_fails_before_provider_call(
    source_id: str,
    resource_id: str,
    match: str,
) -> None:
    provider = _provider()

    with pytest.raises(AuthError, match=match):
        _ = _resolve_value(
            provider,
            request=_request(source_id=source_id, resource_id=resource_id),
        )

    assert provider.requests == []


def test_foreign_https_fetcher_fails_before_provider_call() -> None:
    provider = _provider()

    with pytest.raises(AuthError, match="invalid HTTPS fetcher"):
        _ = _resolve_value(
            provider,
            fetcher=cast("HttpsFetcher", object()),
        )

    assert provider.requests == []


def test_tampered_https_fetcher_fails_before_provider_call() -> None:
    provider = _provider()
    tampered = replace(_fetcher(), fetcher_id="unsupported")

    with pytest.raises(AuthError, match="invalid HTTPS fetcher"):
        _ = _resolve_value(provider, fetcher=tampered)

    assert provider.requests == []


def test_foreign_fetch_request_fails_before_provider_call() -> None:
    provider = _provider()

    with pytest.raises(AuthError, match="invalid fetch request"):
        _ = _resolve_value(
            provider,
            request=cast("FetchRequest", object()),
        )

    assert provider.requests == []


def test_malformed_fetch_request_fails_before_provider_call() -> None:
    provider = _provider()
    request = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(AuthError, match="invalid fetch request"):
        _ = _resolve_value(provider, request=request)

    assert provider.requests == []


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_invalid_authorization_provider_identity_fails_before_call(
    provider_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(AuthError, match="canonical ASCII identity form"):
        _ = _resolve_value(
            provider,
            authorization_provider_id=provider_id,
        )

    assert provider.requests == []


@pytest.mark.parametrize("limit", [0, -1, True])
def test_invalid_byte_limit_fails_before_provider_call(limit: int) -> None:
    provider = _provider()

    with pytest.raises(AuthError, match="positive integer"):
        _ = _resolve_value(provider, max_authorization_bytes=limit)

    assert provider.requests == []


def test_byte_limit_above_supported_maximum_fails_before_provider_call() -> (
    None
):
    provider = _provider()

    with pytest.raises(AuthError, match="exceeds supported maximum"):
        _ = _resolve_value(
            provider,
            max_authorization_bytes=auth.MAX_HTTPS_AUTHORIZATION_BYTES + 1,
        )

    assert provider.requests == []


def test_noncallable_provider_fails_before_resolution() -> None:
    with pytest.raises(
        AuthError, match="authorization provider must be callable"
    ):
        _ = _resolve_value(
            cast(
                "auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProvider",
                object(),
            )
        )


def test_provider_exception_is_wrapped_without_vendor_text() -> None:
    provider = _RaisingProvider()

    with pytest.raises(
        AuthError,
        match="authorization provider raised during explicit resolution",
    ) as caught:
        _ = _resolve_value(provider)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(provider.requests) == ONE_CALL


@pytest.mark.parametrize("kind", [AuthKind.UNAVAILABLE, AuthKind.FAILED])
def test_typed_nonresolved_result_stops_without_retry(kind: AuthKind) -> None:
    provider = _Provider(AuthResult(kind=kind))

    with pytest.raises(AuthError, match=rf"provider returned {kind.value}"):
        _ = _resolve_value(provider)

    assert len(provider.requests) == ONE_CALL


def test_foreign_result_type_fails_closed() -> None:
    provider = _Provider(cast("AuthResult", object()))

    with pytest.raises(AuthError, match="exact authorization result type"):
        _ = _resolve_value(provider)

    assert len(provider.requests) == ONE_CALL


def test_foreign_result_kind_fails_closed() -> None:
    result = AuthResult(
        kind=cast("AuthKind", cast("object", "resolved")),
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AuthError, match="exact authorization result enum"):
        _ = _resolve_value(_Provider(result))


def test_nonresolved_result_cannot_smuggle_credential_text() -> None:
    result = AuthResult(
        kind=AuthKind.FAILED,
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AuthError, match="cannot contain credential text"):
        _ = _resolve_value(_Provider(result))


@pytest.mark.parametrize(
    "value",
    [None, "", cast("str | None", cast("object", bytearray(b"foreign")))],
)
def test_resolved_result_requires_nonempty_exact_text(
    value: str | None,
) -> None:
    result = AuthResult(kind=AuthKind.RESOLVED, authorization_value=value)

    with pytest.raises(AuthError, match="nonempty exact text"):
        _ = _resolve_value(_Provider(result))


@pytest.mark.parametrize("value", ["Bearer café", "Bearer 🔑"])
def test_resolved_authorization_requires_ascii(value: str) -> None:
    with pytest.raises(AuthError, match="must use ASCII text"):
        _ = _resolve_value(_provider(value))


@pytest.mark.parametrize(
    "value",
    [
        " Bearer token",
        "Bearer token ",
        "\tBearer token",
        "Bearer\ttoken",
        "Bearer\ntoken",
        "Bearer\r token",
        "Bearer\x00token",
        "Bearer\x7ftoken",
    ],
)
def test_edge_spaces_and_controls_fail_closed(value: str) -> None:
    with pytest.raises(AuthError, match=r"edge spaces|unsupported characters"):
        _ = _resolve_value(_provider(value))


def test_authorization_above_requested_limit_fails_closed() -> None:
    value = "X" * 9

    with pytest.raises(AuthError, match="exceeds configured byte limit"):
        _ = _resolve_value(
            _provider(value),
            max_authorization_bytes=8,
        )


def test_public_request_validator_returns_exact_request() -> None:
    request = AuthRequest(
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        bundle_fingerprint=BUNDLE_FINGERPRINT,
        fetch_provider_id=FETCH_PROVIDER_ID,
        resource_id=RESOURCE_ID,
        source_id=SOURCE_ID,
    )

    assert _validate_request(request) is request


def test_public_request_validator_rejects_foreign_type() -> None:
    with pytest.raises(AuthError, match="exact authorization request type"):
        _ = _validate_request(cast("AuthRequest", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        (
            "authorization_provider_id",
            "bad provider",
            "authorization provider identity",
        ),
        ("bundle_fingerprint", "bad", "bundle fingerprint is malformed"),
        ("fetch_provider_id", "bad provider", "fetch provider identity"),
        ("resource_id", "bad resource", "resource identity"),
        ("source_id", "bad source", "source identity"),
    ],
)
def test_public_request_validator_rejects_invalid_metadata(
    field: str,
    value: str,
    match: str,
) -> None:
    request = AuthRequest(
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        bundle_fingerprint=BUNDLE_FINGERPRINT,
        fetch_provider_id=FETCH_PROVIDER_ID,
        resource_id=RESOURCE_ID,
        source_id=SOURCE_ID,
    )

    with pytest.raises(AuthError, match=match):
        _ = _validate_request(replace(request, **{field: value}))


def test_public_result_validator_returns_exact_resolved_result() -> None:
    result = _resolved()

    assert _validate_result(result) is result


def test_public_result_validator_rejects_foreign_type() -> None:
    with pytest.raises(AuthError, match="exact authorization result type"):
        _ = _validate_result(cast("AuthResult", object()))


def test_public_result_validator_rejects_foreign_enum() -> None:
    result = AuthResult(
        kind=cast("AuthKind", cast("object", "resolved")),
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AuthError, match="exact authorization result enum"):
        _ = _validate_result(result)


def test_public_result_validator_rejects_nonresolved_payload() -> None:
    result = AuthResult(
        kind=AuthKind.UNAVAILABLE,
        authorization_value=AUTHORIZATION_VALUE,
    )

    with pytest.raises(AuthError, match="cannot contain credential text"):
        _ = _validate_result(result)


def test_public_preflight_contains_exact_nonsecret_metadata() -> None:
    prepared = _prepare(
        _fetcher(),
        _request(),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        max_authorization_bytes=len(AUTHORIZATION_VALUE),
    )

    assert _validate_prepared(prepared) is prepared
    assert prepared.max_authorization_bytes == len(AUTHORIZATION_VALUE)
    assert prepared.request == AuthRequest(
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        bundle_fingerprint=BUNDLE_FINGERPRINT,
        fetch_provider_id=FETCH_PROVIDER_ID,
        resource_id=RESOURCE_ID,
        source_id=SOURCE_ID,
    )
    assert AUTHORIZATION_BYTES not in repr(prepared).encode("utf-8")


def test_public_materializer_matches_synchronous_resolution() -> None:
    result = _resolved(BASIC_VALUE)
    prepared = _prepare(
        _fetcher(),
        _request(),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )

    materialized = _materialize(prepared, result)
    resolved = _resolve_value(_Provider(result))

    assert materialized == resolved


def test_public_preflight_validator_rejects_foreign_type() -> None:
    with pytest.raises(AuthError, match="exact preflight type"):
        _ = _validate_prepared(cast("PreparedAuth", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("max_authorization_bytes", 0, "positive integer"),
        (
            "request",
            cast("AuthRequest", object()),
            "exact authorization request type",
        ),
    ],
)
def test_public_preflight_validator_rejects_tampering(
    field: str,
    value: object,
    match: str,
) -> None:
    prepared = _prepare(
        _fetcher(),
        _request(),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )

    with pytest.raises(AuthError, match=match):
        _ = _validate_prepared(replace(prepared, **{field: value}))


def test_public_materializer_rejects_foreign_preflight() -> None:
    with pytest.raises(AuthError, match="exact preflight type"):
        _ = _materialize(
            cast("PreparedAuth", object()),
            _resolved(),
        )


def test_public_materializer_rejects_foreign_result() -> None:
    prepared = _prepare(
        _fetcher(),
        _request(),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
    )

    with pytest.raises(AuthError, match="exact authorization result type"):
        _ = _materialize(prepared, cast("AuthResult", object()))


def test_public_materializer_enforces_prepared_byte_limit() -> None:
    prepared = _prepare(
        _fetcher(),
        _request(),
        authorization_provider_id=AUTHORIZATION_PROVIDER_ID,
        max_authorization_bytes=8,
    )

    with pytest.raises(AuthError, match="exceeds configured byte limit"):
        _ = _materialize(prepared, _resolved("X" * 9))
