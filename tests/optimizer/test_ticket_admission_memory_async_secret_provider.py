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
#   - Inline async adapter regressions for the bounded memory secret provider.
# - Must-Not:
#   - Read environment, files, network, external secret stores, create hidden
#     tasks, refresh, retry, persist, log secrets, use async plugins, or change
#     policy.
# - Allows:
#   - Inputs: synthetic memory services, requests, integrations, and tampering.
#   - Outputs: inline-await, metadata, secrecy, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-secret async adaptation.
# - Summary:
#   - Bounded memory-to-async lineage secret-provider regressions.
# - Description:
#   - Proves awaiting retains exact synchronous validation without scheduling.
# - Usage:
#   - Runs without files, network, environment access, or accelerator hardware.
# - Defaults:
#   - Uses two synthetic 32-byte secrets and the 256-entry default.
#

"""Inline async adapter tests for bounded memory lineage secrets."""

# ruff: file-ignore[undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

from accelerator import ticket_admission_memory_async_secret_provider as adapter
from accelerator import (
    ticket_admission_telemetry_lineage_async_secret_provider as async_port,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_secret_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
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
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncSecretProviderError
)
MemoryProviderError = (
    memory.TicketAdmissionTelemetryLineageMemorySecretProviderError
)
AsyncProviderError = (
    async_port.TicketAdmissionTelemetryLineageAsyncSecretProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemorySecretEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemorySecretProvider
MemoryAsyncProvider = (
    adapter.TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider
)
SecretRequest = port.TicketAdmissionTelemetryLineageSecretRequest
SecretResult = port.TicketAdmissionTelemetryLineageSecretResult
SecretKind = port.TicketAdmissionTelemetryLineageSecretResultKind
_build_memory = (
    memory.build_ticket_admission_telemetry_lineage_memory_secret_provider
)
_build_adapter = adapter.build_ticket_admission_memory_async_secret_provider
_validate_adapter = (
    adapter.validate_ticket_admission_memory_async_secret_provider
)
_resolve_async = (
    async_port.resolve_ticket_admission_telemetry_lineage_trust_async
)

ADAPTER_ID = (
    "bounded-in-memory-async-ticket-admission-telemetry-lineage-"
    "secret-provider-v1"
)
PROVIDER_ID = "provider.test.memory-async-lineage-secrets"
OTHER_PROVIDER_ID = "provider.test.other-lineage-secrets"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "vault.lineage-key.2026-07"
NEW_REFERENCE_ID = "vault.lineage-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.lineage-key.unknown"
OLD_SECRET = b"o" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
NEW_SECRET = b"n" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
SECRET_FIELD = b"secret_key"
PROVIDER_FIELD = b"provider="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
ONE_ENTRY = 1
TWO_ENTRIES = 2
DEFAULT_MAX_ENTRIES = 256


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


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    secret_key: bytes = OLD_SECRET,
) -> MemoryEntry:
    return MemoryEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
                _manifest()
            )
        ),
        secret_key=secret_key,
    )


def _entries() -> tuple[MemoryEntry, ...]:
    return (
        _entry(),
        _entry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            secret_key=NEW_SECRET,
        ),
    )


def _memory_provider(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> MemoryProvider:
    return _build_memory(
        _entries() if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
    )


def _adapter(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
) -> MemoryAsyncProvider:
    return _build_adapter(_memory_provider(entries=entries))


def _request(  # ruff: ignore[too-many-arguments]
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    provider_id: str = PROVIDER_ID,
    request_index: int = 0,
) -> SecretRequest:
    return SecretRequest(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
                _manifest()
            )
        ),
        provider_id=provider_id,
        request_index=request_index,
    )


def _direct_result(
    value: MemoryAsyncProvider,
    request: SecretRequest,
) -> SecretResult:
    async def resolve() -> SecretResult:
        return await value(request)

    return asyncio.run(resolve())


def _resolved_trust(
    value: MemoryAsyncProvider,
) -> TicketAdmissionTelemetryLineageProviderTrust:
    return asyncio.run(
        _resolve_async(
            _manifest(),
            value,
            provider_id=PROVIDER_ID,
        )
    )


def test_adapter_identity_metadata_and_repr_are_stable() -> None:
    value = _adapter()
    representation = repr(value).encode("utf-8")

    assert (
        adapter.ticket_admission_memory_async_secret_provider_id() == ADAPTER_ID
    )
    assert value.adapter_id == ADAPTER_ID
    assert value.max_entries == DEFAULT_MAX_ENTRIES
    assert value.provider_id == PROVIDER_ID
    assert value.secret_count == TWO_ENTRIES
    assert _validate_adapter(value) is value
    assert OLD_SECRET not in representation
    assert NEW_SECRET not in representation
    assert SECRET_FIELD not in representation
    assert PROVIDER_FIELD not in representation


def test_direct_await_resolves_exact_request() -> None:
    result = _direct_result(_adapter(), _request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is OLD_SECRET


def test_direct_await_returns_unavailable_for_unknown_reference() -> None:
    result = _direct_result(
        _adapter(),
        _request(key_reference_id=UNKNOWN_REFERENCE_ID),
    )

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_direct_await_returns_failed_for_provider_mismatch() -> None:
    result = _direct_result(
        _adapter(),
        _request(provider_id=OTHER_PROVIDER_ID),
    )

    assert result == SecretResult(kind=SecretKind.FAILED)


def test_direct_coroutine_finishes_without_yielding() -> None:
    coroutine = _adapter()(_request())

    with pytest.raises(StopIteration) as caught:
        coroutine.send(None)

    result = cast("SecretResult", caught.value.value)
    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is OLD_SECRET


def test_await_completes_without_internal_scheduling_point() -> None:
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> SecretResult:
        task = asyncio.create_task(marker())
        result = await _adapter()(_request())
        assert events == []
        await task
        return result

    result = asyncio.run(resolve())

    assert result.kind is SecretKind.RESOLVED
    assert events == ["marker"]


def test_await_runs_in_same_task_without_hidden_task_creation() -> None:
    async def resolve() -> tuple[SecretResult, int]:
        before = len(asyncio.all_tasks())
        result = await _adapter()(_request())
        after = len(asyncio.all_tasks())
        assert before == after == ONE_ENTRY
        return result, after

    result, task_count = asyncio.run(resolve())

    assert result.kind is SecretKind.RESOLVED
    assert task_count == ONE_ENTRY


def test_async_secret_boundary_materializes_exact_memory_trust() -> None:
    resolved = _resolved_trust(_adapter())

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_ENTRIES
    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert tuple(key.secret_key for key in resolved.trust.keys) == (
        OLD_SECRET,
        NEW_SECRET,
    )


def test_repeated_async_resolution_reuses_only_explicit_memory_state() -> None:
    value = _adapter()

    first = _resolved_trust(value)
    second = _resolved_trust(value)

    assert first == second
    assert _validate_adapter(value) is value


def test_empty_memory_service_returns_unavailable_directly() -> None:
    value = _adapter(entries=())
    result = _direct_result(value, _request())

    assert value.secret_count == 0
    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_secret() -> None:
    result = _direct_result(
        _adapter(),
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            request_index=1,
        ),
    )

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is NEW_SECRET


def test_builder_rejects_foreign_memory_provider_type() -> None:
    with pytest.raises(AdapterError, match="invalid memory lineage secret"):
        _ = _build_adapter(cast("MemoryProvider", object()))


def test_builder_rejects_tampered_memory_provider() -> None:
    value = replace(_memory_provider(), service_id="unsupported")

    with pytest.raises(AdapterError, match="invalid memory lineage secret"):
        _ = _build_adapter(value)


def test_validator_rejects_foreign_adapter_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-async secret type"):
        _ = _validate_adapter(cast("MemoryAsyncProvider", object()))


def test_tampered_adapter_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), adapter_id="unsupported")

    with pytest.raises(AdapterError, match="adapter identity is unsupported"):
        _ = _direct_result(value, _request())


@pytest.mark.parametrize("secret_count", [-1, True])
def test_tampered_adapter_count_type_fails_before_lookup(
    secret_count: int,
) -> None:
    value = replace(_adapter(), secret_count=secret_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_count_binding_fails_before_lookup() -> None:
    value = replace(_adapter(), secret_count=ONE_ENTRY)

    with pytest.raises(AdapterError, match="secret count does not match"):
        _ = _direct_result(value, _request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_tampered_adapter_limit_type_fails_before_lookup(
    max_entries: int,
) -> None:
    value = replace(_adapter(), max_entries=max_entries)

    with pytest.raises(AdapterError, match="positive integer"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_limit_binding_fails_before_lookup() -> None:
    value = replace(_adapter(), max_entries=DEFAULT_MAX_ENTRIES + 1)

    with pytest.raises(AdapterError, match="entry limit does not match"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_provider_identity_fails_before_lookup() -> None:
    value = replace(_adapter(), provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="identity does not match provider"):
        _ = _direct_result(value, _request())


def test_tampered_adapter_provider_type_fails_before_lookup() -> None:
    value = replace(
        _adapter(),
        provider=cast("MemoryProvider", object()),
    )

    with pytest.raises(AdapterError, match="invalid memory lineage secret"):
        _ = _direct_result(value, _request())


def test_tampered_wrapped_secret_fails_shared_validation() -> None:
    service = _memory_provider()
    changed = replace(service.entries[0], secret_key=b"short")
    tampered_service = replace(
        service,
        entries=(changed, service.entries[1]),
    )
    value = replace(_adapter(), provider=tampered_service)

    with pytest.raises(AdapterError, match="invalid memory lineage secret"):
        _ = _direct_result(value, _request())


def test_tampered_wrapped_order_fails_shared_validation() -> None:
    service = _memory_provider()
    tampered_service = replace(
        service,
        entries=tuple(reversed(service.entries)),
    )
    value = replace(_adapter(), provider=tampered_service)

    with pytest.raises(AdapterError, match="invalid memory lineage secret"):
        _ = _direct_result(value, _request())


def test_direct_foreign_request_type_preserves_memory_error() -> None:
    with pytest.raises(
        MemoryProviderError, match="exact secret-provider request type"
    ):
        _ = _direct_result(
            _adapter(),
            cast("SecretRequest", object()),
        )


def test_direct_malformed_request_preserves_memory_error() -> None:
    malformed = replace(_request(), manifest_fingerprint="malformed")

    with pytest.raises(MemoryProviderError, match="manifest fingerprint"):
        _ = _direct_result(_adapter(), malformed)


def test_async_boundary_stops_on_typed_unavailable_result() -> None:
    value = _adapter(entries=())

    with pytest.raises(
        AsyncProviderError, match="provider returned unavailable"
    ):
        _ = _resolved_trust(value)


def test_async_boundary_stops_on_typed_failed_result() -> None:
    value = _build_adapter(_memory_provider(provider_id=OTHER_PROVIDER_ID))

    with pytest.raises(AsyncProviderError, match="provider returned failed"):
        _ = _resolved_trust(value)


def test_custom_service_limit_is_copied_exactly() -> None:
    service = _memory_provider(max_entries=TWO_ENTRIES)
    value = _build_adapter(service)

    assert value.max_entries == TWO_ENTRIES
    assert value.secret_count == TWO_ENTRIES
    assert _validate_adapter(value) is value
