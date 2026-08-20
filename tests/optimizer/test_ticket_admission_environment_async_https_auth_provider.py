# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Caller-offloaded async environment Authorization adapter regressions.
# - Must-Not:
#   - Use hidden tasks, threads, executors, discovery, files, network, retries,
#     external stores, credential logging, async plugins, refresh, or policy.
# - Allows:
#   - Inputs: explicit variables, exact providers, offloaders, and tampering.
#   - Outputs: preflight, await, cancellation, rotation, result, and secrecy.
#   - Side effects: caller event loops and pytest-owned environment changes.
# - Split-When:
#   - Split when native async environment access or hosted providers gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact offloaded environment boundary.
# - Summary:
#   - Caller-scheduled async environment Authorization regressions.
# - Description:
#   - Proves no task, thread, executor, retry, refresh, or cache is owned here.
# - Usage:
#   - Runs without network access, files, plugins, or accelerator hardware.
# - Defaults:
#   - Uses two explicit variables, 64 bindings, and one caller offloader.
#

"""Caller-offloaded async environment Authorization adapter tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

from accelerator import (
    ticket_admission_environment_async_https_auth_provider as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_async_https_auth_provider as async_auth,
)
from accelerator import (
    # jig-ignore-next-line: indivisible reviewed identifier
    ticket_admission_telemetry_lineage_environment_https_auth_provider as environment,
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
import pytest

# jig-ignore-next-line: indivisible reviewed identifier
AdapterError = adapter.TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError
EnvironmentEntry = (
    environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization
)
EnvironmentProvider = (
    environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider
)
EnvironmentAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider
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
_build_environment = (
    environment.build_ticket_admission_environment_https_authorization_provider
)
# jig-ignore-next-line: indivisible reviewed identifier
_build_adapter = adapter.build_ticket_admission_environment_async_https_authorization_provider
# jig-ignore-next-line: indivisible reviewed identifier
_validate_adapter = adapter.validate_ticket_admission_environment_async_https_authorization_provider
_resolve_async = async_auth.resolve_ticket_admission_https_authorization_async
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher

ADAPTER_ID = (
    "offloaded-async-environment-ticket-admission-lineage-"
    "https-authorization-provider-v1"
)
AUTH_PROVIDER_ID = "credential-provider.test.environment-async-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.environment-async-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.environment-async-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.environment-async-auth-key-service-a"
SOURCE_B = "source.test.environment-async-auth-key-service-b"
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
VARIABLE_A = "MALBOLGE_TEST_ASYNC_AUTHORIZATION_A"
VARIABLE_B = "MALBOLGE_TEST_ASYNC_AUTHORIZATION_B"
AUTHORIZATION_A = "Bearer caller-owned-environment-async-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
ROTATED_AUTHORIZATION = "Bearer rotated-environment-async-token"
VENDOR_DETAIL = "caller scheduling detail must not cross boundary"
PROVIDER_FIELD = b"provider="
OFFLOADER_FIELD = b"offloader="
AUTHORIZATION_FIELD = b"authorization_value"
DEFAULT_MAX_ENTRIES = 64
DEFAULT_MAX_BYTES = 4096
TWO_ENTRIES = 2
ONE_ENTRY = 1
ONE_CALL = 1
TWO_CALLS = 2


class _Offloader:
    def __init__(self, *, suspend: bool = True) -> None:
        self.suspend: bool = suspend
        self.providers: list[EnvironmentProvider] = []
        self.requests: list[AuthRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(
        self,
        provider: EnvironmentProvider,
        request: AuthRequest,
    ) -> AuthResult:
        self.providers.append(provider)
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        self.task_counts.append(len(asyncio.all_tasks()))
        if self.suspend:
            await asyncio.sleep(0)
            await asyncio.sleep(0)
        return provider(request)


class _CancellingOffloader:
    async def __call__(
        self,
        provider: EnvironmentProvider,
        request: AuthRequest,
    ) -> AuthResult:
        _ = provider, request
        raise asyncio.CancelledError


class _RaisingOffloader:
    async def __call__(
        self,
        provider: EnvironmentProvider,
        request: AuthRequest,
    ) -> AuthResult:
        _ = provider, request
        raise RuntimeError(VENDOR_DETAIL)


class _ResultOffloader:
    def __init__(self, result: AuthResult) -> None:
        self.result: AuthResult = result
        self.call_count: int = 0

    async def __call__(
        self,
        provider: EnvironmentProvider,
        request: AuthRequest,
    ) -> AuthResult:
        _ = provider, request
        self.call_count += 1
        return self.result


def _entry(  # ruff: ignore[too-many-arguments]
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


def _entries() -> tuple[EnvironmentEntry, ...]:
    return (
        _entry(),
        _entry(
            bundle_fingerprint=FINGERPRINT_B,
            environment_variable_name=VARIABLE_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        ),
    )


def _environment_provider(
    *,
    entries: tuple[EnvironmentEntry, ...] | None = None,
    provider_id: str = AUTH_PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_authorization_bytes: int = DEFAULT_MAX_BYTES,
) -> EnvironmentProvider:
    return _build_environment(
        _entries() if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
        max_authorization_bytes=max_authorization_bytes,
    )


def _adapter(
    # jig-ignore-next-line: indivisible reviewed identifier
    offloader: adapter.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader
    | None = None,
    *,
    provider: EnvironmentProvider | None = None,
) -> EnvironmentAsyncProvider:
    return _build_adapter(
        _environment_provider() if provider is None else provider,
        _Offloader() if offloader is None else offloader,
    )


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
    value: EnvironmentAsyncProvider,
    request: AuthRequest | None = None,
) -> AuthResult:
    async def resolve() -> AuthResult:
        return await value(_auth_request() if request is None else request)

    return asyncio.run(resolve())


def _resolved_authorization(
    value: EnvironmentAsyncProvider,
) -> ResolvedAuth:
    return asyncio.run(
        _resolve_async(
            _https_fetcher(),
            _fetch_request(),
            value,
            authorization_provider_id=AUTH_PROVIDER_ID,
        )
    )


def _forbid_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(variable_name: str) -> str | None:
        del variable_name
        raise AssertionError

    monkeypatch.setattr(environment, "_read_environment_value", forbidden)


def test_identity_metadata_validator_and_repr_are_stable() -> None:
    value = _adapter()
    representation = repr(value).encode("utf-8")

    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        adapter.ticket_admission_environment_async_https_authorization_provider_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.entry_count == TWO_ENTRIES
    assert value.max_entries == DEFAULT_MAX_ENTRIES
    assert value.max_authorization_bytes == DEFAULT_MAX_BYTES
    assert value.provider_id == AUTH_PROVIDER_ID
    assert _validate_adapter(value) is value
    assert VARIABLE_A.encode() not in representation
    assert VARIABLE_B.encode() not in representation
    assert AUTHORIZATION_A.encode() not in representation
    assert PROVIDER_FIELD not in representation
    assert OFFLOADER_FIELD not in representation


def test_builder_and_validator_do_not_read_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _environment_provider()
    _forbid_lookup(monkeypatch)

    value = _build_adapter(provider, _Offloader())

    assert _validate_adapter(value) is value


def test_coroutine_does_not_start_before_caller_runs_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    offloader = _Offloader()
    value = _adapter(offloader)
    coroutine = value(_auth_request())

    assert offloader.requests == []
    result = asyncio.run(coroutine)

    assert result.authorization_value == AUTHORIZATION_A
    assert offloader.requests == [_auth_request()]


def test_exact_request_awaits_once_with_same_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    offloader = _Offloader()
    value = _adapter(offloader)
    request = _auth_request()

    result = _direct_result(value, request)

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A
    assert offloader.providers == [value.provider]
    assert offloader.requests == [request]
    assert offloader.requests[0] is request
    assert len(set(offloader.tasks)) == ONE_CALL
    assert offloader.task_counts == [ONE_CALL]


def test_inline_offloader_controls_absence_of_suspension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> AuthResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(_Offloader(suspend=False))(_auth_request())
        assert events == []
        await marker_task
        return result

    assert asyncio.run(resolve()).kind is AuthKind.RESOLVED
    assert events == ["marker"]


def test_suspending_offloader_controls_scheduling_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> AuthResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(_Offloader(suspend=True))(_auth_request())
        assert events == ["marker"]
        await marker_task
        return result

    assert asyncio.run(resolve()).kind is AuthKind.RESOLVED


def test_async_boundary_materializes_exact_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)

    resolved = _resolved_authorization(_adapter(_Offloader(suspend=False)))

    assert resolved.authorization_value == AUTHORIZATION_A
    assert resolved.authorization_provider_id == AUTH_PROVIDER_ID
    assert resolved.bundle_fingerprint == FINGERPRINT_A
    assert resolved.fetch_provider_id == FETCH_PROVIDER_A
    assert resolved.resource_id == RESOURCE_A
    assert resolved.source_id == SOURCE_A


def test_repeated_calls_reread_rotated_environment_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offloader = _Offloader(suspend=False)
    value = _adapter(offloader)
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)

    first = _direct_result(value)
    monkeypatch.setenv(VARIABLE_A, ROTATED_AUTHORIZATION)
    second = _direct_result(value)

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == ROTATED_AUTHORIZATION
    assert len(offloader.requests) == TWO_CALLS


def test_deleted_variable_becomes_unavailable_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _adapter(_Offloader(suspend=False))
    monkeypatch.setenv(VARIABLE_A, AUTHORIZATION_A)
    assert _direct_result(value).kind is AuthKind.RESOLVED
    monkeypatch.delenv(VARIABLE_A)

    assert _direct_result(value) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VARIABLE_B, AUTHORIZATION_B)

    result = _direct_result(
        _adapter(_Offloader(suspend=False)),
        _auth_request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        ),
    )

    assert result.authorization_value == AUTHORIZATION_B


def test_unknown_binding_is_offloaded_once_and_unavailable() -> None:
    offloader = _Offloader(suspend=False)

    result = _direct_result(
        _adapter(offloader),
        _auth_request(resource_id=RESOURCE_B),
    )

    assert result == AuthResult(kind=AuthKind.UNAVAILABLE)
    assert len(offloader.requests) == ONE_CALL


def test_provider_mismatch_returns_failed_before_await() -> None:
    offloader = _Offloader()

    result = _direct_result(
        _adapter(offloader),
        _auth_request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID),
    )

    assert result == AuthResult(kind=AuthKind.FAILED)
    assert offloader.requests == []


def test_invalid_request_fails_before_first_await() -> None:
    offloader = _Offloader()
    malformed = replace(_auth_request(), bundle_fingerprint="malformed")

    with pytest.raises(
        AdapterError, match="invalid caller-offloaded environment"
    ):
        _ = _direct_result(_adapter(offloader), malformed)

    assert offloader.requests == []


def test_foreign_request_type_fails_before_first_await() -> None:
    offloader = _Offloader()

    with pytest.raises(
        AdapterError, match="invalid caller-offloaded environment"
    ):
        _ = _direct_result(_adapter(offloader), cast("AuthRequest", object()))

    assert offloader.requests == []


def test_offloader_cancellation_propagates() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _direct_result(_adapter(_CancellingOffloader()))


def test_offloader_exception_is_wrapped_without_vendor_text() -> None:
    with pytest.raises(
        AdapterError,
        match="caller environment Authorization offloader raised",
    ) as caught:
        _ = _direct_result(_adapter(_RaisingOffloader()))

    assert VENDOR_DETAIL not in str(caught.value)


@pytest.mark.parametrize("kind", [AuthKind.UNAVAILABLE, AuthKind.FAILED])
def test_typed_nonresolved_result_is_preserved(kind: AuthKind) -> None:
    offloader = _ResultOffloader(AuthResult(kind=kind))

    result = _direct_result(_adapter(offloader))

    assert result == AuthResult(kind=kind)
    assert offloader.call_count == ONE_CALL


def test_foreign_result_type_fails_after_one_await() -> None:
    offloader = _ResultOffloader(cast("AuthResult", object()))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(_adapter(offloader))

    assert offloader.call_count == ONE_CALL


def test_foreign_result_enum_fails_after_one_await() -> None:
    result = AuthResult(
        kind=cast("AuthKind", cast("object", "resolved")),
        authorization_value=AUTHORIZATION_A,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(_adapter(_ResultOffloader(result)))


def test_nonresolved_result_cannot_smuggle_authorization_text() -> None:
    result = AuthResult(
        kind=AuthKind.FAILED,
        authorization_value=AUTHORIZATION_A,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(_adapter(_ResultOffloader(result)))


@pytest.mark.parametrize(
    "authorization_value",
    [
        None,
        "",
        " Bearer token",
        "Bearer token ",
        "Bearer\ttoken",
        "Bearer\ntoken",
        "Bearer\x7ftoken",
        "Bearer café",
        cast("str | None", cast("object", bytearray(b"Bearer token"))),
    ],
)
def test_resolved_result_requires_exact_bounded_ascii_text(
    authorization_value: str | None,
) -> None:
    result = AuthResult(
        kind=AuthKind.RESOLVED,
        authorization_value=authorization_value,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(_adapter(_ResultOffloader(result)))


def test_resolved_result_respects_adapter_byte_limit() -> None:
    provider = _environment_provider(max_authorization_bytes=32)
    result = AuthResult(
        kind=AuthKind.RESOLVED,
        authorization_value="X" * 33,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(
            _adapter(_ResultOffloader(result), provider=provider)
        )


def test_exact_adapter_byte_limit_is_allowed() -> None:
    provider = _environment_provider(max_authorization_bytes=32)
    result = AuthResult(
        kind=AuthKind.RESOLVED,
        authorization_value="X" * 32,
    )

    resolved = _direct_result(
        _adapter(_ResultOffloader(result), provider=provider)
    )

    assert resolved.authorization_value == "X" * 32


def test_outer_async_boundary_rejects_typed_unavailable() -> None:
    value = _adapter(_ResultOffloader(AuthResult(kind=AuthKind.UNAVAILABLE)))

    with pytest.raises(
        async_auth.TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError,
        match="cannot materialize async HTTPS Authorization result",
    ):
        _ = _resolved_authorization(value)


def test_builder_rejects_foreign_environment_provider_type() -> None:
    with pytest.raises(AdapterError, match="invalid synchronous environment"):
        _ = _build_adapter(
            cast("EnvironmentProvider", object()),
            _Offloader(),
        )


def test_builder_rejects_tampered_environment_provider() -> None:
    value = replace(_environment_provider(), service_id="unsupported")

    with pytest.raises(AdapterError, match="invalid synchronous environment"):
        _ = _build_adapter(value, _Offloader())


def test_builder_rejects_noncallable_offloader() -> None:
    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _build_adapter(
            _environment_provider(),
            cast(
                # jig-ignore-next-line: indivisible reviewed identifier
                "adapter.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader",
                object(),
            ),
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact environment-async auth type"):
        _ = _validate_adapter(cast("EnvironmentAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_await() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value)


@pytest.mark.parametrize("entry_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_await(
    entry_count: int,
) -> None:
    value = replace(_adapter(), entry_count=entry_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value)


def test_tampered_adapter_count_binding_fails_before_await() -> None:
    value = replace(_adapter(), entry_count=ONE_ENTRY)

    with pytest.raises(AdapterError, match="entry count does not match"):
        _ = _direct_result(value)


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_tampered_adapter_entry_limit_fails_before_await(
    max_entries: int,
) -> None:
    value = replace(_adapter(), max_entries=max_entries)

    with pytest.raises(AdapterError, match="entry limit must be"):
        _ = _direct_result(value)


def test_tampered_adapter_entry_limit_binding_fails_before_await() -> None:
    value = replace(_adapter(), max_entries=DEFAULT_MAX_ENTRIES + 1)

    with pytest.raises(AdapterError, match="entry limit does not match"):
        _ = _direct_result(value)


@pytest.mark.parametrize("max_authorization_bytes", [0, -1, True])
def test_tampered_adapter_byte_limit_fails_before_await(
    max_authorization_bytes: int,
) -> None:
    value = replace(
        _adapter(),
        max_authorization_bytes=max_authorization_bytes,
    )

    with pytest.raises(AdapterError, match="byte limit must be"):
        _ = _direct_result(value)


def test_tampered_adapter_byte_limit_binding_fails_before_await() -> None:
    value = replace(
        _adapter(),
        max_authorization_bytes=DEFAULT_MAX_BYTES - 1,
    )

    with pytest.raises(AdapterError, match="byte limit does not match"):
        _ = _direct_result(value)


@pytest.mark.parametrize("provider_id", ["", cast("str", cast("object", 1))])
def test_tampered_adapter_provider_metadata_fails_before_await(
    provider_id: str,
) -> None:
    value = replace(_adapter(), provider_id=provider_id)

    with pytest.raises(AdapterError, match="provider identity"):
        _ = _direct_result(value)


def test_tampered_adapter_provider_binding_fails_before_await() -> None:
    value = replace(_adapter(), provider_id=OTHER_AUTH_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _direct_result(value)


def test_tampered_wrapped_provider_type_fails_before_await() -> None:
    value = replace(
        _adapter(),
        provider=cast("EnvironmentProvider", object()),
    )

    with pytest.raises(AdapterError, match="invalid synchronous environment"):
        _ = _direct_result(value)


def test_tampered_wrapped_provider_fails_before_await() -> None:
    provider = replace(_environment_provider(), service_id="unsupported")
    value = replace(_adapter(), provider=provider)

    with pytest.raises(AdapterError, match="invalid synchronous environment"):
        _ = _direct_result(value)


def test_tampered_noncallable_offloader_fails_before_await() -> None:
    value = replace(
        _adapter(),
        offloader=cast(
            # jig-ignore-next-line: indivisible reviewed identifier
            "adapter.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader",
            object(),
        ),
    )

    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _direct_result(value)


def test_result_repr_hides_async_authorization_value() -> None:
    result = _direct_result(
        _adapter(
            _ResultOffloader(
                AuthResult(
                    kind=AuthKind.RESOLVED,
                    authorization_value=AUTHORIZATION_A,
                )
            )
        )
    )
    representation = repr(result).encode("utf-8")

    assert AUTHORIZATION_A.encode() not in representation
    assert AUTHORIZATION_FIELD not in representation


def test_environment_read_error_remains_typed_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing(variable_name: str) -> str | None:
        del variable_name
        raise OSError(VENDOR_DETAIL)

    monkeypatch.setattr(environment, "_read_environment_value", failing)

    result = _direct_result(_adapter(_Offloader(suspend=False)))

    assert result == AuthResult(kind=AuthKind.FAILED)
