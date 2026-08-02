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
#   - Caller-offloaded async file-secret adapter regressions.
# - Must-Not:
#   - Use hidden tasks, threads, executors, discovery, environment, network,
#     retries, external stores, secret logging, async plugins, or policy
#     changes.
# - Allows:
#   - Inputs: explicit temporary files, exact providers, offloaders, and
#     tampering.
#   - Outputs: preflight, await, cancellation, result, secrecy, and binding
#     checks.
#   - Side effects: caller-owned event loops and pytest-managed temporary files.
# - Split-When:
#   - Split when native async file I/O, external stores, hosted APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact caller-offloaded file boundary.
# - Summary:
#   - Explicit caller-scheduled async raw-secret file regressions.
# - Description:
#   - Proves the adapter owns no task, thread, executor, retry, or cache policy.
# - Usage:
#   - Runs without network access, async plugins, or accelerator hardware.
# - Defaults:
#   - Uses two temporary 32-byte raw-secret files and one caller offloader.
#

"""Caller-offloaded async explicit file-secret adapter tests."""

# ruff: file-ignore[undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from accelerator import ticket_admission_file_async_secret_provider as adapter
from accelerator import (
    ticket_admission_telemetry_lineage_async_secret_provider as async_port,
)
from accelerator import (
    ticket_admission_telemetry_lineage_file_secret_provider as file_provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MIN_TELEMETRY_LINEAGE_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestEntry,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    build_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_fingerprint,
)
import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
        TicketAdmissionTelemetryLineageProviderTrust,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageFileAsyncSecretProviderError
)
FileProviderError = (
    file_provider.TicketAdmissionTelemetryLineageFileSecretProviderError
)
AsyncProviderError = (
    async_port.TicketAdmissionTelemetryLineageAsyncSecretProviderError
)
FileEntry = file_provider.TicketAdmissionTelemetryLineageFileSecretEntry
FileProvider = file_provider.TicketAdmissionTelemetryLineageFileSecretProvider
FileAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageFileAsyncSecretProvider
)
SecretRequest = port.TicketAdmissionTelemetryLineageSecretRequest
SecretResult = port.TicketAdmissionTelemetryLineageSecretResult
SecretKind = port.TicketAdmissionTelemetryLineageSecretResultKind
_build_file = (
    file_provider.build_ticket_admission_telemetry_lineage_file_secret_provider
)
_build_adapter = adapter.build_ticket_admission_file_async_secret_provider
_validate_adapter = adapter.validate_ticket_admission_file_async_secret_provider
_resolve_async = (
    async_port.resolve_ticket_admission_telemetry_lineage_trust_async
)

ADAPTER_ID = (
    "offloaded-async-file-ticket-admission-telemetry-lineage-secret-provider-v1"
)
PROVIDER_ID = "provider.test.file-async-lineage-secrets"
OTHER_PROVIDER_ID = "provider.test.other-lineage-secrets"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "file.lineage-key.2026-07"
NEW_REFERENCE_ID = "file.lineage-key.2026-08"
UNKNOWN_REFERENCE_ID = "file.lineage-key.unknown"
OLD_SECRET = b"o" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
NEW_SECRET = b"n" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
ROTATED_SECRET = b"r" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
VENDOR_DETAIL = "caller scheduling detail must not cross boundary"
PROVIDER_FIELD = b"provider="
OFFLOADER_FIELD = b"offloader="
SECRET_FIELD = b"secret_key"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
ONE_CALL = 1
TWO_CALLS = 2
TWO_ENTRIES = 2
DEFAULT_MAX_ENTRIES = 256
DEFAULT_MAX_SECRET_BYTES = MAX_TELEMETRY_LINEAGE_KEY_BYTES


class _Offloader:
    def __init__(self, *, suspend: bool = True) -> None:
        self.suspend: bool = suspend
        self.providers: list[FileProvider] = []
        self.requests: list[SecretRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []

    async def __call__(
        self,
        provider: FileProvider,
        request: SecretRequest,
    ) -> SecretResult:
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
        provider: FileProvider,
        request: SecretRequest,
    ) -> SecretResult:
        _ = provider, request
        raise asyncio.CancelledError


class _RaisingOffloader:
    async def __call__(
        self,
        provider: FileProvider,
        request: SecretRequest,
    ) -> SecretResult:
        _ = provider, request
        raise RuntimeError(VENDOR_DETAIL)


class _ResultOffloader:
    def __init__(self, result: SecretResult) -> None:
        self.result: SecretResult = result
        self.call_count: int = 0

    async def __call__(
        self,
        provider: FileProvider,
        request: SecretRequest,
    ) -> SecretResult:
        _ = provider, request
        self.call_count += 1
        return self.result


def _manifest() -> TicketAdmissionTelemetryLineageTrustManifest:
    return build_ticket_admission_telemetry_lineage_trust_manifest((
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
        ),
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            key_id=OLD_KEY_ID,
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
        ),
    ))


def _manifest_fingerprint() -> str:
    return ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
        _manifest()
    )


def _entry(  # ruff: ignore[too-many-arguments]
    secret_path: Path,
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str | None = None,
) -> FileEntry:
    return FileEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            _manifest_fingerprint()
            if manifest_fingerprint is None
            else manifest_fingerprint
        ),
        secret_path=str(secret_path.absolute()),
    )


def _entries(tmp_path: Path) -> tuple[FileEntry, ...]:
    return (
        _entry(tmp_path / "old.secret"),
        _entry(
            tmp_path / "new.secret",
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
        ),
    )


def _write_secrets(tmp_path: Path) -> None:
    _ = (tmp_path / "old.secret").write_bytes(OLD_SECRET)
    _ = (tmp_path / "new.secret").write_bytes(NEW_SECRET)


def _file_provider(  # ruff: ignore[too-many-arguments]
    tmp_path: Path,
    *,
    entries: tuple[FileEntry, ...] | None = None,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_secret_bytes: int = DEFAULT_MAX_SECRET_BYTES,
    provider_id: str = PROVIDER_ID,
    write_secrets: bool = True,
) -> FileProvider:
    if write_secrets:
        _write_secrets(tmp_path)
    return _build_file(
        _entries(tmp_path) if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
        max_secret_bytes=max_secret_bytes,
    )


def _adapter(
    tmp_path: Path,
    offloader: adapter.TicketAdmissionTelemetryLineageFileSecretOffloader
    | None = None,
    *,
    provider: FileProvider | None = None,
) -> FileAsyncProvider:
    return _build_adapter(
        _file_provider(tmp_path) if provider is None else provider,
        _Offloader() if offloader is None else offloader,
    )


def _request(  # ruff: ignore[too-many-arguments]
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str | None = None,
    provider_id: str = PROVIDER_ID,
    request_index: int = 0,
) -> SecretRequest:
    return SecretRequest(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            _manifest_fingerprint()
            if manifest_fingerprint is None
            else manifest_fingerprint
        ),
        provider_id=provider_id,
        request_index=request_index,
    )


def _run_direct(
    value: FileAsyncProvider,
    request: SecretRequest | None = None,
) -> SecretResult:
    async def resolve() -> SecretResult:
        return await value(_request() if request is None else request)

    return asyncio.run(resolve())


def _resolved_trust(
    value: FileAsyncProvider,
) -> TicketAdmissionTelemetryLineageProviderTrust:
    return asyncio.run(
        _resolve_async(
            _manifest(),
            value,
            provider_id=PROVIDER_ID,
        )
    )


def test_identity_metadata_validator_and_repr_are_stable(
    tmp_path: Path,
) -> None:
    offloader = _Offloader()
    value = _adapter(tmp_path, offloader)
    representation = repr(value).encode("utf-8")

    assert (
        adapter.ticket_admission_file_async_secret_provider_id() == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.max_entries == DEFAULT_MAX_ENTRIES
    assert value.max_secret_bytes == DEFAULT_MAX_SECRET_BYTES
    assert value.provider_id == PROVIDER_ID
    assert value.secret_count == TWO_ENTRIES
    assert _validate_adapter(value) is value
    assert str(tmp_path).encode() not in representation
    assert OLD_SECRET not in representation
    assert NEW_SECRET not in representation
    assert PROVIDER_FIELD not in representation
    assert OFFLOADER_FIELD not in representation
    assert SECRET_FIELD not in representation


def test_coroutine_does_not_start_before_caller_runs_it(tmp_path: Path) -> None:
    offloader = _Offloader()
    value = _adapter(tmp_path, offloader)
    coroutine = value(_request())

    assert offloader.requests == []
    result = asyncio.run(coroutine)

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == OLD_SECRET
    assert offloader.requests == [_request()]


def test_exact_request_awaits_once_in_same_task(tmp_path: Path) -> None:
    offloader = _Offloader()
    value = _adapter(tmp_path, offloader)
    request = _request()

    result = _run_direct(value, request)

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == OLD_SECRET
    assert offloader.providers == [value.provider]
    assert offloader.requests == [request]
    assert offloader.requests[0] is request
    assert len(set(offloader.tasks)) == ONE_CALL
    assert offloader.task_counts == [ONE_CALL]


def test_inline_offloader_controls_absence_of_suspension(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    offloader = _Offloader(suspend=False)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> SecretResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(tmp_path, offloader)(_request())
        assert events == []
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is SecretKind.RESOLVED
    assert events == ["marker"]


def test_suspending_offloader_controls_scheduling_point(tmp_path: Path) -> None:
    events: list[str] = []
    offloader = _Offloader(suspend=True)

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> SecretResult:
        marker_task = asyncio.create_task(marker())
        result = await _adapter(tmp_path, offloader)(_request())
        assert events == ["marker"]
        await marker_task
        return result

    result = asyncio.run(resolve())

    assert result.kind is SecretKind.RESOLVED


def test_async_boundary_materializes_exact_file_trust(tmp_path: Path) -> None:
    resolved = _resolved_trust(_adapter(tmp_path))

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_ENTRIES
    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert tuple(key.secret_key for key in resolved.trust.keys) == (
        OLD_SECRET,
        NEW_SECRET,
    )


def test_repeated_calls_reread_rotated_file_without_cache(
    tmp_path: Path,
) -> None:
    offloader = _Offloader(suspend=False)
    value = _adapter(tmp_path, offloader)

    first = _run_direct(value)
    _ = (tmp_path / "old.secret").write_bytes(ROTATED_SECRET)
    second = _run_direct(value)

    assert first.secret_key == OLD_SECRET
    assert second.secret_key == ROTATED_SECRET
    assert len(offloader.requests) == TWO_CALLS


def test_repeated_async_trust_resolution_rereads_files(tmp_path: Path) -> None:
    value = _adapter(tmp_path, _Offloader(suspend=False))

    first = _resolved_trust(value)
    _ = (tmp_path / "old.secret").write_bytes(ROTATED_SECRET)
    second = _resolved_trust(value)

    assert first.trust.keys[0].secret_key == OLD_SECRET
    assert second.trust.keys[0].secret_key == ROTATED_SECRET


def test_second_exact_entry_resolves_second_secret(tmp_path: Path) -> None:
    result = _run_direct(
        _adapter(tmp_path),
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            request_index=1,
        ),
    )

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == NEW_SECRET


def test_unknown_reference_is_offloaded_once_and_returns_unavailable(
    tmp_path: Path,
) -> None:
    offloader = _Offloader(suspend=False)

    result = _run_direct(
        _adapter(tmp_path, offloader),
        _request(key_reference_id=UNKNOWN_REFERENCE_ID),
    )

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)
    assert len(offloader.requests) == ONE_CALL


def test_provider_mismatch_returns_failed_before_await(tmp_path: Path) -> None:
    offloader = _Offloader()

    result = _run_direct(
        _adapter(tmp_path, offloader),
        _request(provider_id=OTHER_PROVIDER_ID),
    )

    assert result == SecretResult(kind=SecretKind.FAILED)
    assert offloader.requests == []


def test_invalid_request_fails_before_first_await(tmp_path: Path) -> None:
    offloader = _Offloader()
    malformed = replace(_request(), manifest_fingerprint="malformed")

    with pytest.raises(AdapterError, match="invalid caller-offloaded file"):
        _ = _run_direct(_adapter(tmp_path, offloader), malformed)

    assert offloader.requests == []


def test_foreign_request_type_fails_before_first_await(tmp_path: Path) -> None:
    offloader = _Offloader()

    with pytest.raises(AdapterError, match="invalid caller-offloaded file"):
        _ = _run_direct(
            _adapter(tmp_path, offloader),
            cast("SecretRequest", object()),
        )

    assert offloader.requests == []


def test_offloader_cancellation_propagates(tmp_path: Path) -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run_direct(_adapter(tmp_path, _CancellingOffloader()))


def test_offloader_exception_is_wrapped_without_vendor_text(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        AdapterError,
        match="caller file-secret offloader raised during explicit read",
    ) as caught:
        _ = _run_direct(_adapter(tmp_path, _RaisingOffloader()))

    assert VENDOR_DETAIL not in str(caught.value)


@pytest.mark.parametrize("kind", [SecretKind.UNAVAILABLE, SecretKind.FAILED])
def test_typed_nonresolved_result_is_preserved(
    tmp_path: Path,
    kind: SecretKind,
) -> None:
    offloader = _ResultOffloader(SecretResult(kind=kind))

    result = _run_direct(_adapter(tmp_path, offloader))

    assert result == SecretResult(kind=kind)
    assert offloader.call_count == ONE_CALL


def test_foreign_result_type_fails_after_one_await(tmp_path: Path) -> None:
    offloader = _ResultOffloader(cast("SecretResult", object()))

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(_adapter(tmp_path, offloader))

    assert offloader.call_count == ONE_CALL


def test_foreign_result_enum_fails_after_one_await(tmp_path: Path) -> None:
    result = SecretResult(
        kind=cast("SecretKind", cast("object", "resolved")),
        secret_key=OLD_SECRET,
    )

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(_adapter(tmp_path, _ResultOffloader(result)))


def test_nonresolved_result_cannot_smuggle_secret_bytes(tmp_path: Path) -> None:
    result = SecretResult(kind=SecretKind.FAILED, secret_key=OLD_SECRET)

    with pytest.raises(AdapterError, match="invalid result"):
        _ = _run_direct(_adapter(tmp_path, _ResultOffloader(result)))


@pytest.mark.parametrize(
    "secret_key",
    [
        None,
        b"",
        b"short",
        cast("bytes | None", cast("object", bytearray(OLD_SECRET))),
    ],
)
def test_resolved_result_requires_exact_bounded_bytes(
    tmp_path: Path,
    secret_key: bytes | None,
) -> None:
    result = SecretResult(kind=SecretKind.RESOLVED, secret_key=secret_key)

    with pytest.raises(AdapterError, match="resolved"):
        _ = _run_direct(_adapter(tmp_path, _ResultOffloader(result)))


def test_resolved_result_respects_adapter_byte_limit(tmp_path: Path) -> None:
    provider = _file_provider(
        tmp_path,
        max_secret_bytes=MIN_TELEMETRY_LINEAGE_KEY_BYTES,
    )
    result = SecretResult(
        kind=SecretKind.RESOLVED,
        secret_key=b"x" * (MIN_TELEMETRY_LINEAGE_KEY_BYTES + 1),
    )

    with pytest.raises(AdapterError, match="exceeds adapter byte limit"):
        _ = _run_direct(
            _adapter(tmp_path, _ResultOffloader(result), provider=provider)
        )


def test_exact_adapter_byte_limit_is_allowed(tmp_path: Path) -> None:
    provider = _file_provider(
        tmp_path,
        max_secret_bytes=MIN_TELEMETRY_LINEAGE_KEY_BYTES,
    )
    result = SecretResult(kind=SecretKind.RESOLVED, secret_key=OLD_SECRET)

    resolved = _run_direct(
        _adapter(tmp_path, _ResultOffloader(result), provider=provider)
    )

    assert resolved.secret_key == OLD_SECRET


def test_outer_async_boundary_rejects_typed_unavailable(tmp_path: Path) -> None:
    offloader = _ResultOffloader(SecretResult(kind=SecretKind.UNAVAILABLE))

    with pytest.raises(
        AsyncProviderError,
        match="invalid async provider result",
    ):
        _ = _resolved_trust(_adapter(tmp_path, offloader))


def test_builder_rejects_foreign_file_provider_type() -> None:
    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _build_adapter(
            cast("FileProvider", object()),
            _Offloader(),
        )


def test_builder_rejects_tampered_file_provider(tmp_path: Path) -> None:
    value = replace(_file_provider(tmp_path), service_id="unsupported")

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _build_adapter(value, _Offloader())


def test_builder_rejects_noncallable_offloader(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _build_adapter(
            _file_provider(tmp_path),
            cast(
                "adapter.TicketAdmissionTelemetryLineageFileSecretOffloader",
                object(),
            ),
        )


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact file-async secret type"):
        _ = _validate_adapter(cast("FileAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_await(tmp_path: Path) -> None:
    value = replace(_adapter(tmp_path), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _run_direct(value)


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_tampered_adapter_entry_limit_type_fails_before_await(
    tmp_path: Path,
    max_entries: int,
) -> None:
    value = replace(_adapter(tmp_path), max_entries=max_entries)

    with pytest.raises(AdapterError, match="entry limit must be"):
        _ = _run_direct(value)


@pytest.mark.parametrize(
    "max_secret_bytes",
    [0, MIN_TELEMETRY_LINEAGE_KEY_BYTES - 1, True],
)
def test_tampered_adapter_secret_limit_type_fails_before_await(
    tmp_path: Path,
    max_secret_bytes: int,
) -> None:
    value = replace(_adapter(tmp_path), max_secret_bytes=max_secret_bytes)

    with pytest.raises(AdapterError, match="secret byte limit"):
        _ = _run_direct(value)


@pytest.mark.parametrize("secret_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_await(
    tmp_path: Path,
    secret_count: int,
) -> None:
    value = replace(_adapter(tmp_path), secret_count=secret_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _run_direct(value)


@pytest.mark.parametrize("provider_id", ["", cast("str", cast("object", 1))])
def test_tampered_adapter_provider_metadata_fails_before_await(
    tmp_path: Path,
    provider_id: str,
) -> None:
    value = replace(_adapter(tmp_path), provider_id=provider_id)

    with pytest.raises(AdapterError, match="provider identity"):
        _ = _run_direct(value)


def test_builder_and_validator_do_not_open_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _file_provider(tmp_path, write_secrets=False)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError

    monkeypatch.setattr(Path, "open", forbidden_open)

    value = _build_adapter(provider, _Offloader())

    assert _validate_adapter(value) is value


def test_missing_matched_file_is_offloaded_once_and_unavailable(
    tmp_path: Path,
) -> None:
    provider = _file_provider(tmp_path, write_secrets=False)
    offloader = _Offloader(suspend=False)

    result = _run_direct(
        _adapter(tmp_path, offloader, provider=provider),
    )

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)
    assert len(offloader.requests) == ONE_CALL


def test_raw_newline_bytes_are_preserved_async(tmp_path: Path) -> None:
    secret = OLD_SECRET + b"\n"
    value = _adapter(tmp_path, _Offloader(suspend=False))
    _ = (tmp_path / "old.secret").write_bytes(secret)

    result = _run_direct(value)

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == secret


def test_tampered_adapter_entry_limit_binding_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(
        _adapter(tmp_path),
        max_entries=DEFAULT_MAX_ENTRIES + 1,
    )

    with pytest.raises(AdapterError, match="entry limit does not match"):
        _ = _run_direct(value)


def test_tampered_adapter_secret_limit_binding_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(
        _adapter(tmp_path),
        max_secret_bytes=MIN_TELEMETRY_LINEAGE_KEY_BYTES,
    )

    with pytest.raises(AdapterError, match="secret byte limit does not match"):
        _ = _run_direct(value)


def test_tampered_adapter_provider_binding_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(_adapter(tmp_path), provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _run_direct(value)


def test_tampered_adapter_count_binding_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(_adapter(tmp_path), secret_count=ONE_CALL)

    with pytest.raises(AdapterError, match="count does not match provider"):
        _ = _run_direct(value)


def test_tampered_wrapped_provider_type_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(
        _adapter(tmp_path),
        provider=cast("FileProvider", object()),
    )

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _run_direct(value)


def test_tampered_wrapped_provider_fails_before_await(tmp_path: Path) -> None:
    provider = replace(_file_provider(tmp_path), service_id="unsupported")
    value = replace(_adapter(tmp_path), provider=provider)

    with pytest.raises(AdapterError, match="invalid synchronous file"):
        _ = _run_direct(value)


def test_tampered_noncallable_offloader_fails_before_await(
    tmp_path: Path,
) -> None:
    value = replace(
        _adapter(tmp_path),
        offloader=cast(
            "adapter.TicketAdmissionTelemetryLineageFileSecretOffloader",
            object(),
        ),
    )

    with pytest.raises(AdapterError, match="offloader must be callable"):
        _ = _run_direct(value)


def test_result_repr_hides_async_secret_bytes(tmp_path: Path) -> None:
    result = _run_direct(_adapter(tmp_path, _Offloader(suspend=False)))
    representation = repr(result).encode("utf-8")

    assert OLD_SECRET not in representation
    assert SECRET_FIELD not in representation
