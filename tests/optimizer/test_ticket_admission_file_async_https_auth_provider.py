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
#   - Caller-offloaded async file Authorization adapter regressions.
# - Must-Not:
#   - Use hidden tasks, owned threads or executors, discovery, network, retries,
#     external stores, credential logging, refresh, or policy changes.
# - Allows:
#   - Inputs: temporary files, exact providers, caller offloaders, and
#     tampering.
#   - Outputs: preflight, await, placement, cancellation, rotation, and secrecy.
#   - Side effects: caller event loops and pytest-owned temporary file changes.
# - Split-When:
#   - Split when native async file I/O or hosted credential APIs gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact caller-offloaded file boundary.
# - Summary:
#   - Caller-scheduled async file Authorization regressions.
# - Description:
#   - Proves the adapter owns no task, thread, executor, retry, refresh, or
#     cache.
# - Usage:
#   - Runs without network access, plugins, or accelerator hardware.
# - Defaults:
#   - Uses two explicit files, 64 bindings, and one caller offloader.
#

"""Caller-offloaded async file Authorization adapter tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import cast

from accelerator import (
    ticket_admission_file_async_https_auth_provider as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_async_https_auth_provider as async_auth,
)
from accelerator import (
    # jig-ignore-next-line: indivisible reviewed identifier
    ticket_admission_telemetry_lineage_file_https_auth_provider as file_provider,
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

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageFileAsyncHttpsAuthProviderError
)
FileEntry = file_provider.TicketAdmissionTelemetryLineageFileHttpsAuthorization
FileProvider = (
    file_provider.TicketAdmissionTelemetryLineageFileHttpsAuthProvider
)
FileAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageFileAsyncHttpsAuthProvider
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
_build_file = (
    file_provider.build_ticket_admission_file_https_authorization_provider
)
_build_adapter = (
    adapter.build_ticket_admission_file_async_https_authorization_provider
)
_validate_adapter = (
    adapter.validate_ticket_admission_file_async_https_authorization_provider
)
_resolve_async = async_auth.resolve_ticket_admission_https_authorization_async
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher

# jig-ignore-next-line: indivisible reviewed identifier
ADAPTER_ID = "offloaded-async-file-ticket-admission-lineage-https-authorization-provider-v1"
AUTH_PROVIDER_ID = "credential-provider.test.file-async-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.file-async-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.file-async-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.file-async-auth-key-service-a"
SOURCE_B = "source.test.file-async-auth-key-service-b"
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
AUTHORIZATION_A = "Bearer caller-owned-file-async-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
ROTATED_AUTHORIZATION = "Bearer rotated-file-async-token"
STATIC_FIXTURE_ROOT = Path(__file__).resolve().parent / "file-async-fixtures"
STATIC_PATH_A = str(STATIC_FIXTURE_ROOT / "authorization-a.txt")
STATIC_PATH_B = str(STATIC_FIXTURE_ROOT / "authorization-b.txt")
VENDOR_DETAIL = "caller scheduling detail must not cross boundary"
DEFAULT_MAX_ENTRIES = 64
DEFAULT_MAX_BYTES = 4096
ONE_ENTRY = 1
TWO_ENTRIES = 2
ONE_CALL = 1
TWO_CALLS = 2
PROVIDER_FIELD = b"provider="
OFFLOADER_FIELD = b"offloader="
AUTHORIZATION_FIELD = b"authorization_value"


class _Offloader:
    def __init__(self, *, suspend: bool = True) -> None:
        self.suspend: bool = suspend
        self.providers: list[FileProvider] = []
        self.requests: list[AuthRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(
        self,
        provider: FileProvider,
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


class _ThreadOffloader:
    async def __call__(
        self,
        provider: FileProvider,
        request: AuthRequest,
    ) -> AuthResult:
        return await asyncio.to_thread(provider, request)


class _CancellingOffloader:
    async def __call__(
        self,
        provider: FileProvider,
        request: AuthRequest,
    ) -> AuthResult:
        _ = provider, request
        raise asyncio.CancelledError


class _RaisingOffloader:
    async def __call__(
        self,
        provider: FileProvider,
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
        provider: FileProvider,
        request: AuthRequest,
    ) -> AuthResult:
        _ = provider, request
        self.call_count += 1
        return self.result


def _entry_a(path: Path | str) -> FileEntry:
    return FileEntry(
        authorization_path=str(path),
        bundle_fingerprint=FINGERPRINT_A,
        fetch_provider_id=FETCH_PROVIDER_A,
        resource_id=RESOURCE_A,
        source_id=SOURCE_A,
    )


def _entry_b(path: Path | str) -> FileEntry:
    return FileEntry(
        authorization_path=str(path),
        bundle_fingerprint=FINGERPRINT_B,
        fetch_provider_id=FETCH_PROVIDER_B,
        resource_id=RESOURCE_B,
        source_id=SOURCE_B,
    )


def _static_provider(
    *,
    max_authorization_bytes: int = DEFAULT_MAX_BYTES,
) -> FileProvider:
    return _build_file(
        (_entry_a(STATIC_PATH_A), _entry_b(STATIC_PATH_B)),
        provider_id=AUTH_PROVIDER_ID,
        max_authorization_bytes=max_authorization_bytes,
    )


def _file_provider(tmp_path: Path) -> FileProvider:
    path_a = tmp_path / "authorization-a.txt"
    path_b = tmp_path / "authorization-b.txt"
    _ = path_a.write_text(AUTHORIZATION_A, encoding="ascii", newline="")
    _ = path_b.write_text(AUTHORIZATION_B, encoding="ascii", newline="")
    return _build_file(
        (_entry_a(path_a), _entry_b(path_b)),
        provider_id=AUTH_PROVIDER_ID,
    )


def _adapter(
    offloader: adapter.TicketAdmissionTelemetryLineageFileHttpsAuthOffloader
    | None = None,
    *,
    provider: FileProvider | None = None,
) -> FileAsyncProvider:
    return _build_adapter(
        _static_provider() if provider is None else provider,
        _Offloader() if offloader is None else offloader,
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
        # jig-ignore-next-line: indivisible reviewed identifier
        max_bytes=fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES,
        # jig-ignore-next-line: indivisible reviewed identifier
        max_entries=fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES,
        provider_id=FETCH_PROVIDER_A,
        resource_id=RESOURCE_A,
        source_id=SOURCE_A,
    )


def _direct_result(
    value: FileAsyncProvider,
    request: AuthRequest | None = None,
) -> AuthResult:
    async def resolve() -> AuthResult:
        return await value(_request() if request is None else request)

    return asyncio.run(resolve())


def _resolved_authorization(value: FileAsyncProvider) -> ResolvedAuth:
    return asyncio.run(
        _resolve_async(
            _https_fetcher(),
            _fetch_request(),
            value,
            authorization_provider_id=AUTH_PROVIDER_ID,
        )
    )


def test_identity_metadata_validator_and_repr_are_stable() -> None:
    value = _adapter()
    representation = repr(value).encode("utf-8")

    assert (
        adapter.ticket_admission_file_async_https_authorization_provider_id()
        == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.authorization_count == TWO_ENTRIES
    assert value.max_entries == DEFAULT_MAX_ENTRIES
    assert value.max_authorization_bytes == DEFAULT_MAX_BYTES
    assert value.provider_id == AUTH_PROVIDER_ID
    assert _validate_adapter(value) is value
    assert STATIC_PATH_A.encode() not in representation
    assert STATIC_PATH_B.encode() not in representation
    assert PROVIDER_FIELD not in representation
    assert OFFLOADER_FIELD not in representation


def test_builder_and_validator_do_not_read_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _static_provider()

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError

    monkeypatch.setattr(Path, "open", forbidden_open)

    value = _build_adapter(provider, _Offloader())

    assert _validate_adapter(value) is value


def test_coroutine_does_not_start_before_caller_runs_it(tmp_path: Path) -> None:
    offloader = _Offloader()
    value = _adapter(offloader, provider=_file_provider(tmp_path))
    coroutine = value(_request())

    assert offloader.requests == []
    result = asyncio.run(coroutine)

    assert result.authorization_value == AUTHORIZATION_A
    assert offloader.requests == [_request()]


def test_exact_request_awaits_once_with_same_objects(tmp_path: Path) -> None:
    offloader = _Offloader()
    value = _adapter(offloader, provider=_file_provider(tmp_path))
    request = _request()

    result = _direct_result(value, request)

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A
    assert offloader.providers == [value.provider]
    assert offloader.requests == [request]
    assert offloader.requests[0] is request
    assert len(set(offloader.tasks)) == ONE_CALL
    assert offloader.task_counts == [ONE_CALL]


def test_inline_offloader_controls_absence_of_suspension(
    tmp_path: Path,
) -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> AuthResult:
        marker_task = asyncio.create_task(marker())
        value = _adapter(
            _Offloader(suspend=False), provider=_file_provider(tmp_path)
        )
        result = await value(_request())
        assert events == []
        await marker_task
        return result

    assert asyncio.run(resolve()).authorization_value == AUTHORIZATION_A
    assert events == ["marker"]


def test_suspending_offloader_controls_scheduling_point(tmp_path: Path) -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> AuthResult:
        marker_task = asyncio.create_task(marker())
        value = _adapter(
            _Offloader(suspend=True), provider=_file_provider(tmp_path)
        )
        result = await value(_request())
        assert events == ["marker"]
        await marker_task
        return result

    assert asyncio.run(resolve()).authorization_value == AUTHORIZATION_A


def test_caller_may_choose_thread_offload(tmp_path: Path) -> None:
    value = _adapter(_ThreadOffloader(), provider=_file_provider(tmp_path))

    result = _direct_result(value)

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A


def test_async_boundary_materializes_exact_file_value(tmp_path: Path) -> None:
    value = _adapter(
        _Offloader(suspend=False), provider=_file_provider(tmp_path)
    )

    resolved = _resolved_authorization(value)

    assert resolved.authorization_value == AUTHORIZATION_A
    assert resolved.authorization_provider_id == AUTH_PROVIDER_ID
    assert resolved.bundle_fingerprint == FINGERPRINT_A
    assert resolved.fetch_provider_id == FETCH_PROVIDER_A
    assert resolved.resource_id == RESOURCE_A
    assert resolved.source_id == SOURCE_A


def test_repeated_calls_reread_rotated_file_without_cache(
    tmp_path: Path,
) -> None:
    offloader = _Offloader(suspend=False)
    provider = _file_provider(tmp_path)
    value = _adapter(offloader, provider=provider)

    first = _direct_result(value)
    _ = Path(provider.entries[0].authorization_path).write_text(
        ROTATED_AUTHORIZATION,
        encoding="ascii",
        newline="",
    )
    second = _direct_result(value)

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == ROTATED_AUTHORIZATION
    assert len(offloader.requests) == TWO_CALLS


def test_deleted_file_becomes_unavailable_without_cache(tmp_path: Path) -> None:
    provider = _file_provider(tmp_path)
    value = _adapter(_Offloader(suspend=False), provider=provider)
    assert _direct_result(value).kind is AuthKind.RESOLVED
    Path(provider.entries[0].authorization_path).unlink()

    assert _direct_result(value) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_file(tmp_path: Path) -> None:
    value = _adapter(
        _Offloader(suspend=False), provider=_file_provider(tmp_path)
    )

    result = _direct_result(
        value,
        _request(
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
        _request(resource_id=RESOURCE_B),
    )

    assert result == AuthResult(kind=AuthKind.UNAVAILABLE)
    assert len(offloader.requests) == ONE_CALL


def test_provider_mismatch_returns_failed_before_await() -> None:
    offloader = _Offloader()

    result = _direct_result(
        _adapter(offloader),
        _request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID),
    )

    assert result == AuthResult(kind=AuthKind.FAILED)
    assert offloader.requests == []


def test_invalid_request_fails_before_first_await() -> None:
    offloader = _Offloader()
    malformed = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(AdapterError, match="invalid caller-offloaded file"):
        _ = _direct_result(_adapter(offloader), malformed)

    assert offloader.requests == []


def test_foreign_request_type_fails_before_first_await() -> None:
    offloader = _Offloader()

    with pytest.raises(AdapterError, match="invalid caller-offloaded file"):
        _ = _direct_result(_adapter(offloader), cast("AuthRequest", object()))

    assert offloader.requests == []


def test_offloader_cancellation_propagates() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _direct_result(_adapter(_CancellingOffloader()))


def test_offloader_exception_is_wrapped_without_vendor_text() -> None:
    with pytest.raises(
        AdapterError,
        match="caller file Authorization offloader raised",
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
    provider = _static_provider(max_authorization_bytes=32)
    result = AuthResult(
        kind=AuthKind.RESOLVED,
        authorization_value="X" * 33,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _direct_result(
            _adapter(_ResultOffloader(result), provider=provider)
        )


def test_exact_adapter_byte_limit_is_allowed() -> None:
    provider = _static_provider(max_authorization_bytes=32)
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


def test_builder_rejects_foreign_file_provider_type() -> None:
    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _build_adapter(
            cast("FileProvider", object()),
            _Offloader(),
        )


def test_builder_rejects_tampered_file_provider() -> None:
    provider = replace(_static_provider(), service_id="unsupported")

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _build_adapter(provider, _Offloader())


def test_builder_rejects_noncallable_offloader() -> None:
    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _build_adapter(
            _static_provider(),
            cast(
                "adapter.TicketAdmissionTelemetryLineageFileHttpsAuthOffloader",
                object(),
            ),
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact file-async auth type"):
        _ = _validate_adapter(cast("FileAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_await() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value)


@pytest.mark.parametrize("authorization_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_await(
    authorization_count: int,
) -> None:
    value = replace(_adapter(), authorization_count=authorization_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value)


def test_tampered_adapter_count_binding_fails_before_await() -> None:
    value = replace(_adapter(), authorization_count=ONE_ENTRY)

    with pytest.raises(AdapterError, match="count does not match provider"):
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
        provider=cast("FileProvider", object()),
    )

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _direct_result(value)


def test_tampered_wrapped_provider_fails_before_await() -> None:
    provider = replace(_static_provider(), service_id="unsupported")
    value = replace(_adapter(), provider=provider)

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _direct_result(value)


def test_tampered_noncallable_offloader_fails_before_await() -> None:
    value = replace(
        _adapter(),
        offloader=cast(
            "adapter.TicketAdmissionTelemetryLineageFileHttpsAuthOffloader",
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


def test_invalid_file_content_remains_typed_failed(tmp_path: Path) -> None:
    provider = _file_provider(tmp_path)
    _ = Path(provider.entries[0].authorization_path).write_bytes(
        b"Bearer token\n"
    )
    value = _adapter(_Offloader(suspend=False), provider=provider)

    result = _direct_result(value)

    assert result == AuthResult(kind=AuthKind.FAILED)


def test_file_read_error_remains_typed_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _file_provider(tmp_path)

    def failing_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError(VENDOR_DETAIL)

    monkeypatch.setattr(Path, "open", failing_open)
    value = _adapter(_Offloader(suspend=False), provider=provider)

    result = _direct_result(value)

    assert result == AuthResult(kind=AuthKind.FAILED)
