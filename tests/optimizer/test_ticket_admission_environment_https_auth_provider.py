# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Explicit environment HTTPS Authorization provider regressions.
# - Must-Not:
#   - Enumerate host environment, use files, network, external stores, retries,
#     caches, workers, async plugins, secret logging, or policy changes.
# - Allows:
#   - Inputs: explicit test variables, bindings, requests, and tampering.
#   - Outputs: lookup, rotation, bounds, secrecy, ordering, and failure checks.
#   - Side effects: pytest-owned environment mutation only.
# - Split-When:
#   - Split when external stores, hosted APIs, certificates, PKI, or refresh
#     gain
#     tests.
# - Merge-When:
#   - Merge when another suite owns this exact environment-auth behavior.
# - Summary:
#   - Exact bounded environment HTTPS Authorization provider regressions.
# - Description:
#   - Proves one matched name is reread without discovery or caching.
# - Usage:
#   - Runs without sockets, files, external stores, or accelerator hardware.
# - Defaults:
#   - Uses two explicit variables, 64 bindings, and a 4096-byte value limit.
#

"""Explicit bounded environment HTTPS Authorization provider tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

from accelerator import (
    # jig-ignore-next-line: indivisible reviewed identifier
    ticket_admission_telemetry_lineage_environment_https_auth_provider as environment,
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
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
import pytest

EnvironmentAuthError = (
    environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError
)
EnvironmentEntry = (
    environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization
)
EnvironmentProvider = (
    environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider
)
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthResultKind = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
)
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_build = (
    environment.build_ticket_admission_environment_https_authorization_provider
)
_validate = (  # fmt: skip
    # jig-ignore-next-line: indivisible reviewed identifier
    environment.validate_ticket_admission_environment_https_authorization_provider
)
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_resolve = auth.resolve_ticket_admission_https_authorization
_build_authorized = (
    authorized.build_ticket_admission_authorized_https_bundle_fetcher
)

SERVICE_ID = (
    "explicit-environment-ticket-admission-lineage-https-"
    "authorization-provider-v1"
)
AUTH_PROVIDER_ID = "credential-provider.test.environment-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.environment-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.environment-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.environment-auth-key-service-a"
SOURCE_B = "source.test.environment-auth-key-service-b"
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
VARIABLE_A = "MALBOLGE_TEST_AUTHORIZATION_A"
VARIABLE_B = "MALBOLGE_TEST_AUTHORIZATION_B"
SHARED_VARIABLE = "MALBOLGE_TEST_AUTHORIZATION_SHARED"
AUTHORIZATION_A = "Bearer caller-owned-environment-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
ROTATED_AUTHORIZATION = "Bearer rotated-environment-token"
VARIABLE_FIELD = b"environment_variable_name"
ENTRIES_FIELD = b"entries=("
AUTHORIZATION_FIELD = b"authorization_value"
DEFAULT_MAX_ENTRIES = 64
MAX_ENTRIES = 4096
DEFAULT_MAX_BYTES = 4096
MAX_BYTES = 16384
ONE_ENTRY = 1
HIDDEN_DETAIL = "hidden"
INVALID_VARIABLE_NAME = "lowercase"


def _entry_a(  # ruff: ignore[too-many-arguments]
    *,
    bundle_fingerprint: str = FINGERPRINT_A,
    environment_variable_name: str = VARIABLE_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> EnvironmentEntry:
    return EnvironmentEntry(
        bundle_fingerprint=bundle_fingerprint,
        environment_variable_name=environment_variable_name,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _entry_b(
    *,
    environment_variable_name: str = VARIABLE_B,
) -> EnvironmentEntry:
    return EnvironmentEntry(
        bundle_fingerprint=FINGERPRINT_B,
        environment_variable_name=environment_variable_name,
        fetch_provider_id=FETCH_PROVIDER_B,
        resource_id=RESOURCE_B,
        source_id=SOURCE_B,
    )


def _service(
    entries: tuple[EnvironmentEntry, ...] | None = None,
    *,
    provider_id: str = AUTH_PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_authorization_bytes: int = DEFAULT_MAX_BYTES,
) -> EnvironmentProvider:
    return _build(
        (_entry_a(), _entry_b()) if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
        max_authorization_bytes=max_authorization_bytes,
    )


def _request(  # ruff: ignore[too-many-arguments]
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


def _https_fetcher() -> (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
):
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


def _forbid_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(variable_name: str) -> str | None:
        del variable_name
        raise AssertionError

    monkeypatch.setattr(environment, "_read_environment_value", forbidden)


def test_identity_limits_and_repr_are_stable() -> None:
    service = _service()
    representation = repr(service).encode("utf-8")
    entry_representation = repr(service.entries[0]).encode("utf-8")

    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        environment.ticket_admission_environment_https_authorization_provider_id()
        == SERVICE_ID
    )
    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        environment.DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS
        == DEFAULT_MAX_ENTRIES
    )
    assert (
        environment.MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS
        == MAX_ENTRIES
    )
    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        environment.DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES
        == DEFAULT_MAX_BYTES
    )
    assert (
        environment.MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES
        == MAX_BYTES
    )
    assert service.service_id == SERVICE_ID
    assert service.provider_id == AUTH_PROVIDER_ID
    assert service.max_entries == DEFAULT_MAX_ENTRIES
    assert service.max_authorization_bytes == DEFAULT_MAX_BYTES
    assert _validate(service) is service
    assert VARIABLE_A.encode() not in representation
    assert VARIABLE_B.encode() not in representation
    assert VARIABLE_A.encode() not in entry_representation
    assert VARIABLE_FIELD not in entry_representation
    assert ENTRIES_FIELD not in representation


def test_builder_and_validator_do_not_read_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_lookup(monkeypatch)

    service = _service()

    assert _validate(service) is service


def test_exact_request_resolves_exact_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)

    result = _service()(_request())

    assert result.kind is AuthResultKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A
    assert AUTHORIZATION_A.encode() not in repr(result).encode("utf-8")
    assert AUTHORIZATION_FIELD not in repr(result).encode("utf-8")


def test_repeated_calls_reread_rotated_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)

    first = service(_request())
    monkeypatch.setenv(VARIABLE_A, ROTATED_AUTHORIZATION)
    second = service(_request())

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == ROTATED_AUTHORIZATION


def test_deleted_variable_becomes_unavailable_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    first = service(_request())
    monkeypatch.delenv(VARIABLE_A)

    second = service(_request())

    assert first.kind is AuthResultKind.RESOLVED
    assert second == AuthResult(kind=AuthResultKind.UNAVAILABLE)


def test_provider_identity_mismatch_returns_failed_without_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_lookup(monkeypatch)

    result = _service()(
        _request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID)
    )

    assert result == AuthResult(kind=AuthResultKind.FAILED)


@pytest.mark.parametrize(
    "auth_request",
    [
        _request(bundle_fingerprint=FINGERPRINT_B),
        _request(fetch_provider_id=FETCH_PROVIDER_B),
        _request(resource_id=RESOURCE_B),
        _request(source_id=SOURCE_B),
    ],
)
def test_well_formed_nonmatch_returns_unavailable_without_lookup(
    monkeypatch: pytest.MonkeyPatch,
    auth_request: AuthRequest,
) -> None:
    _forbid_lookup(monkeypatch)

    result = _service()(auth_request)

    assert result == AuthResult(kind=AuthResultKind.UNAVAILABLE)


def test_empty_service_returns_unavailable_without_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_lookup(monkeypatch)

    result = _service(())(_request())

    assert result == AuthResult(kind=AuthResultKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_B, AUTHORIZATION_B)

    result = _service()(
        _request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        )
    )

    assert result.kind is AuthResultKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_B


def test_sync_authorization_boundary_resolves_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)

    resolved = _resolve(
        _https_fetcher(),
        _fetch_request(),
        _service(),
        authorization_provider_id=AUTH_PROVIDER_ID,
    )

    assert resolved.authorization_value == AUTHORIZATION_A
    assert resolved.authorization_provider_id == AUTH_PROVIDER_ID
    assert resolved.bundle_fingerprint == FINGERPRINT_A
    assert resolved.fetch_provider_id == FETCH_PROVIDER_A
    assert resolved.resource_id == RESOURCE_A
    assert resolved.source_id == SOURCE_A


def test_resolved_environment_value_builds_authorized_fetcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    https_fetcher = _https_fetcher()
    resolved = _resolve(
        https_fetcher,
        _fetch_request(),
        _service(),
        authorization_provider_id=AUTH_PROVIDER_ID,
    )

    built = _build_authorized(https_fetcher, resolved)

    assert built.authorization_provider_id == AUTH_PROVIDER_ID
    assert built.bundle_fingerprint == FINGERPRINT_A
    assert built.fetch_provider_id == FETCH_PROVIDER_A
    assert built.resource_id == RESOURCE_A
    assert built.source_id == SOURCE_A


@pytest.mark.parametrize(
    "authorization_value",
    [
        "",
        " Bearer token",
        "Bearer token ",
        "Bearer\ttoken",
        "Bearer\ntoken",
        "Bearer\x7ftoken",
        "Bearer café",
    ],
)
def test_invalid_environment_value_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
    authorization_value: str,
) -> None:
    monkeypatch.setenv(VARIABLE_A, authorization_value)

    result = _service()(_request())

    assert result == AuthResult(kind=AuthResultKind.FAILED)


def test_foreign_environment_value_type_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def foreign(variable_name: str) -> str | None:
        del variable_name
        return cast("str", cast("object", bytearray(b"foreign")))

    monkeypatch.setattr(environment, "_read_environment_value", foreign)

    result = _service()(_request())

    assert result == AuthResult(kind=AuthResultKind.FAILED)


def test_environment_value_with_nul_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def nul_value(variable_name: str) -> str | None:
        del variable_name
        return "Bearer" + chr(0) + "token"

    monkeypatch.setattr(environment, "_read_environment_value", nul_value)

    result = _service()(_request())

    assert result == AuthResult(kind=AuthResultKind.FAILED)


def test_environment_value_respects_service_byte_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, "X" * 33)

    result = _service(max_authorization_bytes=32)(_request())

    assert result == AuthResult(kind=AuthResultKind.FAILED)


def test_environment_value_at_exact_service_limit_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "X" * 32
    monkeypatch.setenv(VARIABLE_A, value)

    result = _service(max_authorization_bytes=32)(_request())

    assert result.kind is AuthResultKind.RESOLVED
    assert result.authorization_value == value


@pytest.mark.parametrize(
    "error", [OSError(HIDDEN_DETAIL), UnicodeError(HIDDEN_DETAIL)]
)
def test_environment_read_error_returns_failed_without_text(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def failing(variable_name: str) -> str | None:
        del variable_name
        raise error

    monkeypatch.setattr(environment, "_read_environment_value", failing)

    result = _service()(_request())

    assert result == AuthResult(kind=AuthResultKind.FAILED)
    assert HIDDEN_DETAIL not in repr(result)


def test_unrelated_environment_variable_is_not_discovered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MALBOLGE_TEST_UNRELATED_AUTHORIZATION", AUTHORIZATION_A)
    monkeypatch.delenv(VARIABLE_A, raising=False)

    result = _service()(_request())

    assert result == AuthResult(kind=AuthResultKind.UNAVAILABLE)


def test_two_bindings_may_share_one_explicit_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SHARED_VARIABLE, AUTHORIZATION_A)
    service = _service((
        _entry_a(environment_variable_name=SHARED_VARIABLE),
        _entry_b(environment_variable_name=SHARED_VARIABLE),
    ))

    first = service(_request())
    second = service(
        _request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        )
    )

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == AUTHORIZATION_A


def test_foreign_request_type_fails_closed() -> None:
    with pytest.raises(
        EnvironmentAuthError, match="invalid environment-provider"
    ):
        _ = _service()(cast("AuthRequest", object()))


def test_malformed_request_fails_closed() -> None:
    malformed = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(
        EnvironmentAuthError, match="invalid environment-provider"
    ):
        _ = _service()(malformed)


def test_validator_rejects_foreign_service_type() -> None:
    with pytest.raises(EnvironmentAuthError, match="exact environment auth"):
        _ = _validate(cast("EnvironmentProvider", object()))


def test_tampered_service_identity_fails_closed() -> None:
    tampered = replace(_service(), service_id="unsupported")

    with pytest.raises(EnvironmentAuthError, match="service identity"):
        _ = tampered(_request())


def test_tampered_provider_identity_fails_closed() -> None:
    tampered = replace(_service(), provider_id="bad provider")

    with pytest.raises(EnvironmentAuthError, match="provider identity"):
        _ = tampered(_request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_invalid_max_entry_limit_fails_closed(max_entries: int) -> None:
    with pytest.raises(EnvironmentAuthError, match="positive integer"):
        _ = _service((), max_entries=max_entries)


def test_max_entry_limit_above_supported_limit_fails_closed() -> None:
    with pytest.raises(EnvironmentAuthError, match="exceeds supported limit"):
        _ = _service((), max_entries=MAX_ENTRIES + 1)


def test_entry_count_above_configured_limit_fails_closed() -> None:
    with pytest.raises(EnvironmentAuthError, match="entry count exceeds"):
        _ = _service((_entry_a(), _entry_b()), max_entries=ONE_ENTRY)


@pytest.mark.parametrize("max_bytes", [0, -1, True])
def test_invalid_max_byte_limit_fails_closed(max_bytes: int) -> None:
    with pytest.raises(EnvironmentAuthError, match="positive integer"):
        _ = _service((), max_authorization_bytes=max_bytes)


def test_max_byte_limit_above_supported_limit_fails_closed() -> None:
    with pytest.raises(EnvironmentAuthError, match="exceeds supported limit"):
        _ = _service((), max_authorization_bytes=MAX_BYTES + 1)


def test_entries_require_exact_tuple() -> None:
    with pytest.raises(EnvironmentAuthError, match="exact immutable tuple"):
        _ = _build(
            cast(
                "tuple[EnvironmentEntry, ...]",
                cast("object", [_entry_a()]),
            ),
            provider_id=AUTH_PROVIDER_ID,
        )


def test_entry_requires_exact_type() -> None:
    with pytest.raises(EnvironmentAuthError, match="exact environment"):
        _ = _service((cast("EnvironmentEntry", object()),))


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_provider_identity_requires_canonical_form(provider_id: str) -> None:
    with pytest.raises(EnvironmentAuthError, match="canonical ASCII"):
        _ = _service((), provider_id=provider_id)


@pytest.mark.parametrize(
    "entry",
    [
        _entry_a(bundle_fingerprint="malformed"),
        _entry_a(fetch_provider_id="bad provider"),
        _entry_a(resource_id="bad resource"),
        _entry_a(source_id="bad source"),
    ],
)
def test_entry_metadata_requires_shared_canonical_form(
    entry: EnvironmentEntry,
) -> None:
    with pytest.raises(EnvironmentAuthError, match="request metadata"):
        _ = _service((entry,))


@pytest.mark.parametrize(
    "variable_name",
    [
        "",
        "lowercase",
        "Mixed_Case",
        "1TOKEN",
        "_TOKEN",
        "TOKEN-NAME",
        "TOKEN.NAME",
        "TOKEN=NAME",
        "TOKEN NAME",
        "TÖKEN",
        cast("str", object()),
    ],
)
def test_environment_variable_name_requires_canonical_form(
    variable_name: str,
) -> None:
    with pytest.raises(EnvironmentAuthError, match="uppercase ASCII"):
        _ = _service((_entry_a(environment_variable_name=variable_name),))


def test_environment_variable_name_at_maximum_length_is_allowed() -> None:
    name = "A" + ("B" * 127)

    service = _service((_entry_a(environment_variable_name=name),))

    assert service.entries[0].environment_variable_name == name


def test_environment_variable_name_above_maximum_fails_closed() -> None:
    name = "A" + ("B" * 128)

    with pytest.raises(EnvironmentAuthError, match="uppercase ASCII"):
        _ = _service((_entry_a(environment_variable_name=name),))


def test_builder_canonicalizes_entry_order() -> None:
    service = _service((_entry_b(), _entry_a()))

    assert service.entries == (_entry_a(), _entry_b())


def test_tampered_service_order_fails_closed() -> None:
    service = _service()
    tampered = replace(service, entries=tuple(reversed(service.entries)))

    with pytest.raises(EnvironmentAuthError, match="not canonically ordered"):
        _ = tampered(_request())


def test_duplicate_request_binding_fails_closed() -> None:
    duplicate = replace(_entry_a(), environment_variable_name=VARIABLE_B)

    with pytest.raises(EnvironmentAuthError, match="duplicate request binding"):
        _ = _service((_entry_a(), duplicate))


def test_service_revalidates_tampered_variable_name_on_every_call() -> None:
    service = _service()
    changed = replace(
        service.entries[0], environment_variable_name=INVALID_VARIABLE_NAME
    )
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(EnvironmentAuthError, match="uppercase ASCII"):
        _ = tampered(_request())


def test_service_revalidates_tampered_metadata_on_every_call() -> None:
    service = _service()
    changed = replace(service.entries[0], bundle_fingerprint="malformed")
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(EnvironmentAuthError, match="request metadata"):
        _ = tampered(_request())


def test_service_revalidates_tampered_entry_limit_on_every_call() -> None:
    tampered = replace(_service(), max_entries=0)

    with pytest.raises(EnvironmentAuthError, match="positive integer"):
        _ = tampered(_request())


def test_service_revalidates_tampered_byte_limit_on_every_call() -> None:
    tampered = replace(_service(), max_authorization_bytes=0)

    with pytest.raises(EnvironmentAuthError, match="positive integer"):
        _ = tampered(_request())


def test_tampered_entries_type_fails_closed() -> None:
    tampered = replace(
        _service(),
        entries=cast(
            "tuple[EnvironmentEntry, ...]",
            cast("object", [_entry_a()]),
        ),
    )

    with pytest.raises(EnvironmentAuthError, match="exact immutable tuple"):
        _ = tampered(_request())


def test_environment_variable_name_is_not_in_failure_text() -> None:
    entry = _entry_a(environment_variable_name=INVALID_VARIABLE_NAME)

    with pytest.raises(EnvironmentAuthError) as caught:
        _ = _service((entry,))

    assert INVALID_VARIABLE_NAME not in str(caught.value)
