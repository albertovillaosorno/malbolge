# File:
#   - test_ticket_admission_memory_https_auth_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_https_auth_provider.py
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
#   - Bounded caller-owned in-memory HTTPS Authorization provider regressions.
# - Must-Not:
#   - Read environment, files, network, secret stores, refresh, retry, cache,
#     persist, log values, require async plugins, or change admission policy.
# - Allows:
#   - Inputs: synthetic entries, requests, integrations, and tampering.
#   - Outputs: exact lookup, bounds, secrecy, ordering, and failure assertions.
#   - Side effects: none beyond explicit in-process calls.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-auth behavior.
# - Summary:
#   - Exact bounded memory HTTPS Authorization provider regressions.
# - Description:
#   - Proves caller-owned hidden values are revalidated on every exact lookup.
# - Usage:
#   - Runs without sockets, files, environment access, or accelerator hardware.
# - Defaults:
#   - Uses two synthetic entries and the 64-entry default.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Bounded caller-owned memory HTTPS Authorization provider tests."""


# ruff: file-ignore[too-many-arguments,undocumented-public-function]
# ruff: file-ignore[line-too-long,doc-line-too-long]

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
    ticket_admission_telemetry_lineage_https_authorized_fetcher as authorized,
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

MemoryAuthError = (
    memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthorization
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResultKind = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
)
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_build = memory.build_ticket_admission_memory_https_authorization_provider
_validate = memory.validate_ticket_admission_memory_https_authorization_provider
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_resolve = auth.resolve_ticket_admission_https_authorization
_build_authorized = (
    authorized.build_ticket_admission_authorized_https_bundle_fetcher
)

SERVICE_ID = "memory-ticket-admission-lineage-https-authorization-provider-v1"
AUTH_PROVIDER_ID = "credential-provider.test.memory-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.memory-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.memory-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.memory-auth-key-service-a"
SOURCE_B = "source.test.memory-auth-key-service-b"
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
AUTHORIZATION_A = "Bearer caller-owned-memory-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
AUTHORIZATION_FIELD = b"authorization_value"
ENTRIES_FIELD = b"entries=("
DEFAULT_MAX_ENTRIES = 64
MAX_ENTRIES = 4096
ONE_ENTRY = 1
TWO_ENTRIES = 2


def _authorization_byte_count(value: str) -> int:
    try:
        return len(value.encode("ascii"))
    except UnicodeEncodeError:
        return len(value)


def _entry_a(
    *,
    authorization_value: str = AUTHORIZATION_A,
    authorization_byte_count: int | None = None,
    bundle_fingerprint: str = FINGERPRINT_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> MemoryEntry:
    return MemoryEntry(
        authorization_byte_count=(
            _authorization_byte_count(authorization_value)
            if authorization_byte_count is None
            else authorization_byte_count
        ),
        authorization_value=authorization_value,
        bundle_fingerprint=bundle_fingerprint,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _entry_b() -> MemoryEntry:
    return MemoryEntry(
        authorization_byte_count=len(AUTHORIZATION_B.encode("ascii")),
        authorization_value=AUTHORIZATION_B,
        bundle_fingerprint=FINGERPRINT_B,
        fetch_provider_id=FETCH_PROVIDER_B,
        resource_id=RESOURCE_B,
        source_id=SOURCE_B,
    )


def _service(
    entries: tuple[MemoryEntry, ...] | None = None,
    *,
    provider_id: str = AUTH_PROVIDER_ID,
    max_entries: int = (
        memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
    ),
) -> MemoryProvider:
    return _build(
        (_entry_a(), _entry_b()) if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
    )


def _request(
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


def test_identity_limits_and_repr_are_stable() -> None:
    service = _service()
    representation = repr(service).encode("utf-8")
    entry_representation = repr(service.entries[0]).encode("utf-8")

    assert (
        memory.ticket_admission_memory_https_authorization_provider_id()
        == SERVICE_ID
    )
    assert (
        memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
        == DEFAULT_MAX_ENTRIES
    )
    assert (
        memory.MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS == MAX_ENTRIES
    )
    assert service.service_id == SERVICE_ID
    assert service.provider_id == AUTH_PROVIDER_ID
    assert service.max_entries == DEFAULT_MAX_ENTRIES
    assert _validate(service) is service
    assert AUTHORIZATION_A.encode() not in representation
    assert AUTHORIZATION_B.encode() not in representation
    assert AUTHORIZATION_A.encode() not in entry_representation
    assert AUTHORIZATION_FIELD not in entry_representation
    assert ENTRIES_FIELD not in representation


def test_exact_request_resolves_exact_caller_owned_value() -> None:
    result = _service()(_request())

    assert result.kind is AuthResultKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A
    assert AUTHORIZATION_A.encode() not in repr(result).encode("utf-8")


def test_repeated_calls_are_stable_and_cache_free() -> None:
    service = _service()

    first = service(_request())
    second = service(_request())

    assert first == second
    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == AUTHORIZATION_A


def test_provider_identity_mismatch_returns_failed() -> None:
    result = _service()(
        _request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID)
    )

    assert result.kind is AuthResultKind.FAILED
    assert result.authorization_value is None


@pytest.mark.parametrize(
    "auth_request",
    [
        _request(bundle_fingerprint=FINGERPRINT_B),
        _request(fetch_provider_id=FETCH_PROVIDER_B),
        _request(resource_id=RESOURCE_B),
        _request(source_id=SOURCE_B),
    ],
)
def test_well_formed_nonmatching_request_returns_unavailable(
    auth_request: AuthRequest,
) -> None:
    result = _service()(auth_request)

    assert result.kind is AuthResultKind.UNAVAILABLE
    assert result.authorization_value is None


def test_empty_service_returns_unavailable() -> None:
    result = _service(())(_request())

    assert result.kind is AuthResultKind.UNAVAILABLE
    assert result.authorization_value is None


def test_second_exact_entry_resolves_second_value() -> None:
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


def test_sync_authorization_boundary_resolves_memory_value() -> None:
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


def test_resolved_memory_value_builds_authorized_https_fetcher() -> None:
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


def test_service_revalidates_hidden_value_on_every_call() -> None:
    service = _service()
    tampered_entry = replace(
        service.entries[0],
        authorization_value="Bearer café",
    )
    tampered = replace(service, entries=(tampered_entry, service.entries[1]))

    with pytest.raises(MemoryAuthError, match="invalid authorization"):
        _ = tampered(_request())


def test_service_revalidates_byte_count_on_every_call() -> None:
    service = _service()
    tampered_entry = replace(service.entries[0], authorization_byte_count=1)
    tampered = replace(service, entries=(tampered_entry, service.entries[1]))

    with pytest.raises(MemoryAuthError, match="byte count does not match"):
        _ = tampered(_request())


def test_foreign_request_type_fails_closed() -> None:
    with pytest.raises(MemoryAuthError, match="invalid memory-provider"):
        _ = _service()(cast("AuthRequest", object()))


def test_malformed_request_fails_closed() -> None:
    malformed = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(MemoryAuthError, match="invalid memory-provider"):
        _ = _service()(malformed)


def test_validator_rejects_foreign_service_type() -> None:
    with pytest.raises(
        MemoryAuthError, match="exact memory auth provider type"
    ):
        _ = _validate(cast("MemoryProvider", object()))


def test_tampered_service_identity_fails_closed() -> None:
    tampered = replace(_service(), service_id="unsupported")

    with pytest.raises(
        MemoryAuthError, match="service identity is unsupported"
    ):
        _ = tampered(_request())


def test_tampered_provider_identity_fails_closed() -> None:
    tampered = replace(_service(), provider_id="bad provider")

    with pytest.raises(
        MemoryAuthError, match="authorization provider identity"
    ):
        _ = tampered(_request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_invalid_max_entry_limit_fails_closed(max_entries: int) -> None:
    with pytest.raises(MemoryAuthError, match="positive integer"):
        _ = _service((), max_entries=max_entries)


def test_max_entry_limit_above_supported_limit_fails_closed() -> None:
    with pytest.raises(MemoryAuthError, match="exceeds supported limit"):
        _ = _service(
            (),
            max_entries=(
                memory.MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS + 1
            ),
        )


def test_entry_count_above_configured_limit_fails_closed() -> None:
    with pytest.raises(MemoryAuthError, match="entry count exceeds"):
        _ = _service((_entry_a(), _entry_b()), max_entries=ONE_ENTRY)


def test_entries_require_exact_tuple() -> None:
    with pytest.raises(MemoryAuthError, match="exact immutable tuple"):
        _ = _build(
            cast("tuple[MemoryEntry, ...]", cast("object", [_entry_a()])),
            provider_id=AUTH_PROVIDER_ID,
        )


def test_entry_requires_exact_type() -> None:
    with pytest.raises(
        MemoryAuthError, match="exact memory authorization type"
    ):
        _ = _service((cast("MemoryEntry", object()),))


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_provider_identity_requires_canonical_form(provider_id: str) -> None:
    with pytest.raises(MemoryAuthError, match="canonical ASCII identity form"):
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
    entry: MemoryEntry,
) -> None:
    with pytest.raises(MemoryAuthError, match="invalid authorization"):
        _ = _service((entry,))


@pytest.mark.parametrize(
    "authorization_value",
    [
        "",
        " Bearer token",
        "Bearer token ",
        "Bearer\ttoken",
        "Bearer\ntoken",
        "Bearer\x00token",
        "Bearer\x7ftoken",
        "Bearer café",
    ],
)
def test_entry_authorization_value_uses_shared_validation(
    authorization_value: str,
) -> None:
    with pytest.raises(MemoryAuthError, match="invalid authorization"):
        _ = _service((_entry_a(authorization_value=authorization_value),))


def test_entry_authorization_value_requires_exact_text_type() -> None:
    entry = replace(
        _entry_a(),
        authorization_value=cast("str", cast("object", bytearray(b"foreign"))),
    )

    with pytest.raises(MemoryAuthError, match="invalid authorization"):
        _ = _service((entry,))


def test_entry_authorization_value_respects_supported_maximum() -> None:
    value = "X" * (auth.MAX_HTTPS_AUTHORIZATION_BYTES + 1)
    entry = MemoryEntry(
        authorization_byte_count=len(value),
        authorization_value=value,
        bundle_fingerprint=FINGERPRINT_A,
        fetch_provider_id=FETCH_PROVIDER_A,
        resource_id=RESOURCE_A,
        source_id=SOURCE_A,
    )

    with pytest.raises(MemoryAuthError, match="invalid authorization"):
        _ = _service((entry,))


@pytest.mark.parametrize(
    "authorization_byte_count",
    [0, -1, True, len(AUTHORIZATION_A.encode("ascii")) + 1],
)
def test_entry_byte_count_must_match_exact_value(
    authorization_byte_count: int,
) -> None:
    with pytest.raises(MemoryAuthError, match="byte count does not match"):
        _ = _service((
            _entry_a(
                authorization_byte_count=authorization_byte_count,
            ),
        ))


def test_entries_require_canonical_order() -> None:
    with pytest.raises(
        MemoryAuthError, match="canonical deterministic ordering"
    ):
        _ = _service((_entry_b(), _entry_a()))


def test_duplicate_request_binding_fails_closed() -> None:
    duplicate = replace(_entry_a(), authorization_value="Bearer duplicate")
    duplicate = replace(
        duplicate,
        authorization_byte_count=len(
            duplicate.authorization_value.encode("ascii")
        ),
    )

    with pytest.raises(MemoryAuthError, match="duplicate request binding"):
        _ = _service((_entry_a(), duplicate))
