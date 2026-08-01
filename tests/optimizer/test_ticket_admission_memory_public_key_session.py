# File:
#   - test_ticket_admission_memory_public_key_session.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_public_key_session.py
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
#   - Serial memory-backed public-key session adapter regressions.
# - Must-Not:
#   - Require CUDA, files, network, locks, tasks, retry, secure cryptography,
#     certificates, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic memory services, lifecycle requests, and tampering.
#   - Outputs: serial lifecycle, integration, reuse, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when native async HTTPS transports, credentials,
#     hosted-service APIs, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-session adaptation.
# - Summary:
#   - Bounded memory-to-provider-session regressions.
# - Description:
#   - Proves one active lifecycle and exact close binding without scheduling.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-request defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_s.py
#
# Large file:
#   - false
#

"""Serial memory-backed public-key provider-session tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_session as adapter,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_batch_provider as batch_port,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider_session as s,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_memory_public_key_batch_provider as mb_types,
    )
    from accelerator import (
        ticket_admission_telemetry_lineage_public_key_provider as provider,
    )

AdapterError = (
    adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
MemorySession = (
    adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession
)
OpenKind = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind
)
CloseKind = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind
)
CloseReason = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason
)
OpenRequest = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest
)
CloseRequest = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest
)
OpenResult = s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
CloseResult = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
)
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
_resolve_session = (
    s.resolve_ticket_admission_telemetry_lineage_signature_trust_async_session
)

SESSION_ID = (
    "memory-async-session-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)
PROVIDER_ID = "provider.test.memory-session-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
MANIFEST_FINGERPRINT = "manifest.test.fingerprint"
OTHER_MANIFEST_FINGERPRINT = "manifest.test.other-fingerprint"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_FIELD = b"public_key=b"
BATCH_PROVIDER_FIELD = b"batch_provider="
ACTIVE_REQUEST_FIELD = b"active_open_request="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2
TWO_LIFECYCLES = 2


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
) -> MemoryEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return MemoryEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key=public_key,
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _entries(*, same_key_id: bool = False) -> tuple[MemoryEntry, ...]:
    return (
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(),
    )


def _memory_provider(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> MemoryProvider:
    return memory.build_ticket_admission_telemetry_lineage_memory_public_key_provider(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _session(
    *,
    entries: tuple[MemoryEntry, ...] | None = None,
    max_requests: int = (
        adapter.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_SESSION_REQUESTS
    ),
    provider_id: str = PROVIDER_ID,
) -> MemorySession:
    return adapter.build_ticket_admission_memory_public_key_provider_session(
        _memory_provider(entries=entries, provider_id=provider_id),
        max_requests=max_requests,
    )


def _open_request(
    *,
    manifest_fingerprint: str = MANIFEST_FINGERPRINT,
    provider_id: str = PROVIDER_ID,
    request_count: int = TWO_KEYS,
) -> OpenRequest:
    return OpenRequest(
        manifest_fingerprint=manifest_fingerprint,
        provider_id=provider_id,
        request_count=request_count,
    )


def _close_request(
    *,
    manifest_fingerprint: str = MANIFEST_FINGERPRINT,
    provider_id: str = PROVIDER_ID,
    reason: CloseReason = CloseReason.COMPLETED,
    request_count: int = TWO_KEYS,
) -> CloseRequest:
    return CloseRequest(
        manifest_fingerprint=manifest_fingerprint,
        provider_id=provider_id,
        reason=reason,
        request_count=request_count,
    )


def _build_manifest(
    entries: tuple[ManifestEntry, ...],
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest(
        entries
    )


def _manifest(
    *,
    same_key_id: bool = False,
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return _build_manifest((
        ManifestEntry(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
        ManifestEntry(
            algorithm_id=OLD_ALGORITHM_ID,
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
            public_key_fingerprint=_fingerprint(OLD_PUBLIC_KEY),
            public_key_id=OLD_KEY_ID,
            public_key_reference_id=OLD_REFERENCE_ID,
        ),
    ))


def _open(value: MemorySession, request: OpenRequest) -> OpenResult:
    async def run() -> OpenResult:
        return await value.open(request)

    return asyncio.run(run())


def _close(value: MemorySession, request: CloseRequest) -> CloseResult:
    async def run() -> CloseResult:
        return await value.close(request)

    return asyncio.run(run())


def _resolved_trust(
    value: MemorySession,
    *,
    manifest_value: (
        manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest | None
    ) = None,
) -> provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    async def run() -> (
        provider.TicketAdmissionTelemetryLineagePublicKeyProviderTrust
    ):
        return await _resolve_session(
            _manifest() if manifest_value is None else manifest_value,
            value,
            provider_id=PROVIDER_ID,
        )

    return asyncio.run(run())


def test_session_identity_and_initial_metadata_are_stable() -> None:
    value = _session()

    assert (
        adapter.ticket_admission_memory_public_key_provider_session_id()
        == SESSION_ID
    )
    assert value.session_id == SESSION_ID
    assert value.provider_id == PROVIDER_ID
    assert value.key_count == TWO_KEYS
    assert value.max_requests == (
        adapter.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_SESSION_REQUESTS
    )
    assert value.active is False
    assert value.active_open_request is None
    assert value.completed_lifecycle_count == 0
    assert (
        adapter.validate_ticket_admission_memory_public_key_provider_session(
            value
        )
        is value
    )


def test_session_repr_hides_provider_state_and_key_bytes() -> None:
    value = _session()
    opened = _open(value, _open_request())

    representation = repr(value).encode("utf-8")
    assert opened.kind is OpenKind.OPENED
    assert OLD_PUBLIC_KEY not in representation
    assert NEW_PUBLIC_KEY not in representation
    assert PUBLIC_KEY_FIELD not in representation
    assert BATCH_PROVIDER_FIELD not in representation
    assert ACTIVE_REQUEST_FIELD not in representation


def test_direct_open_and_close_complete_exact_lifecycle() -> None:
    value = _session()

    opened = _open(value, _open_request())
    closed = _close(value, _close_request())

    assert opened.kind is OpenKind.OPENED
    assert opened.provider is value.batch_provider
    assert closed.kind is CloseKind.CLOSED
    assert value.active is False
    assert value.active_open_request is None
    assert value.completed_lifecycle_count == 1


def test_open_and_close_have_no_internal_scheduling_point() -> None:
    value = _session()
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def run() -> tuple[OpenResult, CloseResult]:
        task = asyncio.create_task(marker())
        opened = await value.open(_open_request())
        assert events == []
        closed = await value.close(_close_request())
        assert events == []
        await task
        return opened, closed

    opened, closed = asyncio.run(run())

    assert opened.kind is OpenKind.OPENED
    assert closed.kind is CloseKind.CLOSED
    assert events == ["marker"]


def test_second_open_while_active_fails_without_replacing_state() -> None:
    value = _session()
    first_request = _open_request()

    first = _open(value, first_request)
    second = _open(
        value,
        _open_request(manifest_fingerprint=OTHER_MANIFEST_FINGERPRINT),
    )

    assert first.kind is OpenKind.OPENED
    assert second == OpenResult(kind=OpenKind.FAILED)
    assert value.active is True
    assert value.active_open_request == first_request


def test_close_without_open_returns_failed() -> None:
    value = _session()

    result = _close(value, _close_request())

    assert result == CloseResult(kind=CloseKind.FAILED)
    assert value.active is False
    assert value.completed_lifecycle_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("manifest_fingerprint", OTHER_MANIFEST_FINGERPRINT),
        ("provider_id", OTHER_PROVIDER_ID),
        ("request_count", 1),
    ],
)
def test_mismatched_close_fails_and_retains_active_state(
    field: str,
    value: object,
) -> None:
    session_value = _session()
    open_request = _open_request()
    _ = _open(session_value, open_request)
    close_request = replace(_close_request(), **{field: value})

    result = _close(session_value, close_request)

    assert result.kind is CloseKind.FAILED
    assert session_value.active is True
    assert session_value.active_open_request == open_request
    assert session_value.completed_lifecycle_count == 0


def test_correct_close_can_recover_after_mismatched_close() -> None:
    value = _session()
    _ = _open(value, _open_request())
    _ = _close(value, _close_request(provider_id=OTHER_PROVIDER_ID))

    result = _close(value, _close_request(reason=CloseReason.FAILED))

    assert result.kind is CloseKind.CLOSED
    assert value.active is False
    assert value.completed_lifecycle_count == 1


@pytest.mark.parametrize("reason", list(CloseReason))
def test_every_exact_close_reason_can_close_active_session(
    reason: CloseReason,
) -> None:
    value = _session()
    _ = _open(value, _open_request())

    result = _close(value, _close_request(reason=reason))

    assert result.kind is CloseKind.CLOSED
    assert value.completed_lifecycle_count == 1


def test_session_boundary_builds_manifest_bound_trust_and_closes() -> None:
    value = _session()

    resolved = _resolved_trust(value)

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_KEYS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.trust.key_count == TWO_KEYS
    assert value.active is False
    assert value.completed_lifecycle_count == 1


def test_serial_session_reuses_same_explicit_memory_state() -> None:
    value = _session()

    first = _resolved_trust(value)
    second = _resolved_trust(value)

    assert first == second
    assert value.active is False
    assert value.completed_lifecycle_count == TWO_LIFECYCLES


def test_empty_manifest_performs_no_lifecycle_mutation() -> None:
    empty = _build_manifest(())
    value = _session()

    resolved = _resolved_trust(value, manifest_value=empty)

    assert resolved.request_count == 0
    assert value.active is False
    assert value.completed_lifecycle_count == 0


def test_same_key_id_under_distinct_algorithms_resolves_exactly() -> None:
    value = _session(entries=_entries(same_key_id=True))

    resolved = _resolved_trust(
        value, manifest_value=_manifest(same_key_id=True)
    )

    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert value.completed_lifecycle_count == 1


def test_failed_memory_batch_is_closed_and_session_becomes_reusable() -> None:
    changed = replace(
        _entry(),
        first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        last_capture_sequence_id=None,
    )
    value = _session(entries=(changed, _entries()[0]))

    with pytest.raises(
        batch_port.TicketAdmissionTelemetryLineagePublicKeyBatchProviderError,
        match="provider returned failed at index 0",
    ):
        _ = _resolved_trust(value)

    assert value.active is False
    assert value.completed_lifecycle_count == 1


def test_direct_open_rejects_provider_mismatch_with_typed_failure() -> None:
    value = _session()

    result = _open(value, _open_request(provider_id=OTHER_PROVIDER_ID))

    assert result == OpenResult(kind=OpenKind.FAILED)
    assert value.active is False


def test_direct_open_rejects_count_over_limit_with_typed_failure() -> None:
    value = _session(max_requests=1)

    result = _open(value, _open_request(request_count=TWO_KEYS))

    assert result == OpenResult(kind=OpenKind.FAILED)
    assert value.active is False


def test_outer_boundary_preflights_count_before_open() -> None:
    value = _session(max_requests=1)

    with pytest.raises(
        s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionError,
        match="request count exceeds configured limit",
    ):
        _ = asyncio.run(
            _resolve_session(
                _manifest(),
                value,
                provider_id=PROVIDER_ID,
                max_requests=1,
            )
        )

    assert value.active is False
    assert value.completed_lifecycle_count == 0


def test_builder_rejects_foreign_memory_provider_type() -> None:
    with pytest.raises(AdapterError, match="exact provider type"):
        _ = adapter.build_ticket_admission_memory_public_key_provider_session(
            cast("MemoryProvider", object())
        )


@pytest.mark.parametrize("max_requests", [0, True])
def test_builder_rejects_invalid_request_limit(max_requests: int) -> None:
    with pytest.raises(
        adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError,
        match="positive integer",
    ):
        _ = _session(max_requests=max_requests)


def test_builder_rejects_tampered_memory_provider() -> None:
    value = replace(_memory_provider(), service_id="unsupported")

    with pytest.raises(
        adapter.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError,
        match="cannot build memory batch provider",
    ):
        _ = adapter.build_ticket_admission_memory_public_key_provider_session(
            value
        )


def test_validator_rejects_foreign_session_type() -> None:
    with pytest.raises(AdapterError, match="exact memory-session type"):
        _ = adapter.validate_ticket_admission_memory_public_key_provider_session(
            cast("MemorySession", object())
        )


def test_tampered_session_identity_fails_before_open() -> None:
    value = replace(_session(), session_id="unsupported")

    with pytest.raises(AdapterError, match="session identity is unsupported"):
        _ = _open(value, _open_request())


def test_tampered_active_type_fails_before_open() -> None:
    value = replace(_session(), active=cast("bool", cast("object", 1)))

    with pytest.raises(AdapterError, match="exact boolean type"):
        _ = _open(value, _open_request())


@pytest.mark.parametrize("key_count", [-1, True])
def test_tampered_key_count_type_fails_before_open(key_count: int) -> None:
    value = replace(_session(), key_count=key_count)

    with pytest.raises(AdapterError, match="nonnegative integer"):
        _ = _open(value, _open_request())


def test_tampered_key_count_binding_fails_before_open() -> None:
    value = replace(_session(), key_count=1)

    with pytest.raises(AdapterError, match="does not match batch provider"):
        _ = _open(value, _open_request())


@pytest.mark.parametrize("max_requests", [0, True])
def test_tampered_request_limit_type_fails_before_open(
    max_requests: int,
) -> None:
    value = replace(_session(), max_requests=max_requests)

    with pytest.raises(AdapterError, match="positive integer"):
        _ = _open(value, _open_request())


def test_tampered_request_limit_binding_fails_before_open() -> None:
    value = replace(_session(), max_requests=1)

    with pytest.raises(AdapterError, match="does not match batch provider"):
        _ = _open(value, _open_request())


@pytest.mark.parametrize("completed", [-1, True])
def test_tampered_completed_count_fails_before_open(completed: int) -> None:
    value = replace(_session(), completed_lifecycle_count=completed)

    with pytest.raises(AdapterError, match="completed lifecycle count"):
        _ = _open(value, _open_request())


def test_tampered_provider_identity_binding_fails_before_open() -> None:
    value = replace(_session(), provider_id=OTHER_PROVIDER_ID)

    with pytest.raises(AdapterError, match="does not match batch provider"):
        _ = _open(value, _open_request())


def test_tampered_batch_provider_type_fails_before_open() -> None:
    value = replace(
        _session(),
        batch_provider=cast(
            "mb_types.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider",
            object(),
        ),
    )

    with pytest.raises(AdapterError, match="invalid memory batch provider"):
        _ = _open(value, _open_request())


def test_tampered_wrapped_key_bytes_fail_before_open() -> None:
    value = _session()
    batch_provider = value.batch_provider
    memory_provider = batch_provider.provider
    changed = replace(memory_provider.entries[0], public_key=WRONG_PUBLIC_KEY)
    tampered_memory = replace(
        memory_provider,
        entries=(changed, memory_provider.entries[1]),
    )
    tampered_batch = replace(batch_provider, provider=tampered_memory)
    tampered_session = replace(value, batch_provider=tampered_batch)

    with pytest.raises(AdapterError, match="does not match exact key bytes"):
        _ = _open(tampered_session, _open_request())


def test_foreign_open_request_type_fails_closed() -> None:
    with pytest.raises(AdapterError, match="exact session request type"):
        _ = _open(_session(), cast("OpenRequest", object()))


def test_foreign_close_request_type_fails_closed() -> None:
    with pytest.raises(AdapterError, match="exact session request type"):
        _ = _close(_session(), cast("CloseRequest", object()))


def test_foreign_close_reason_type_fails_closed() -> None:
    value = _session()
    _ = _open(value, _open_request())
    request = replace(
        _close_request(),
        reason=cast("CloseReason", cast("object", "completed")),
    )

    with pytest.raises(AdapterError, match="exact session enum"):
        _ = _close(value, request)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("manifest_fingerprint", "", "manifest fingerprint"),
        ("provider_id", "", "provider identity"),
    ],
)
def test_open_request_requires_nonempty_metadata(
    field: str,
    value: str,
    match: str,
) -> None:
    request = replace(_open_request(), **{field: value})

    with pytest.raises(AdapterError, match=match):
        _ = _open(_session(), request)


@pytest.mark.parametrize("request_count", [0, True])
def test_open_request_count_requires_positive_exact_integer(
    request_count: int,
) -> None:
    request = _open_request(request_count=request_count)

    with pytest.raises(AdapterError, match="positive integer"):
        _ = _open(_session(), request)


@pytest.mark.parametrize(
    ("active_value", "active_request", "match"),
    [
        (True, None, "active state does not match"),
        (False, _open_request(), "active state does not match"),
        (
            True,
            _open_request(provider_id=OTHER_PROVIDER_ID),
            "active provider identity does not match",
        ),
    ],
)
def test_tampered_active_binding_fails_closed(
    active_value: object,
    active_request: OpenRequest | None,
    match: str,
) -> None:
    value = replace(
        _session(),
        active=cast("bool", active_value),
        active_open_request=active_request,
    )

    with pytest.raises(AdapterError, match=match):
        _ = adapter.validate_ticket_admission_memory_public_key_provider_session(
            value
        )
