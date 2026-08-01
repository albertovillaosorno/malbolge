# File:
#   - test_ticket_admission_public_key_provider_session.py
# Path:
#   - tests/optimizer/test_ticket_admission_public_key_provider_session.py
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
#   - Explicit async public-key provider-session lifecycle regressions.
# - Must-Not:
#   - Require CUDA, external services, hidden tasks, retries, caches, or
#     admission-policy changes.
# - Allows:
#   - Inputs: synthetic manifests, sessions, batch providers, keys, failures.
#   - Outputs: preflight, open, close, cancellation, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when concrete network transports, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact session-lifecycle behavior.
# - Summary:
#   - Explicit one-use detached-key provider-session regressions.
# - Description:
#   - Proves nonempty resolution opens and closes exactly once.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-request defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Explicit async public-key provider-session lifecycle tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_batch_provider as b,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as p,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider_session as s,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as m,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

type SignatureManifest = m.TicketAdmissionTelemetryLineageSignatureTrustManifest

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
OpenResult = s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
CloseRequest = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest
)
CloseResult = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
)
SessionPort = s.TicketAdmissionTelemetryLineagePublicKeyProviderSession
SessionError = s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionError
BatchProvider = b.TicketAdmissionTelemetryLineagePublicKeyBatchProvider
BatchRequest = b.TicketAdmissionTelemetryLineagePublicKeyBatchRequest
BatchResult = b.TicketAdmissionTelemetryLineagePublicKeyBatchResult
BatchProviderError = (
    b.TicketAdmissionTelemetryLineagePublicKeyBatchProviderError
)
PublicKeyResult = p.TicketAdmissionTelemetryLineagePublicKeyResult
ResultKind = p.TicketAdmissionTelemetryLineagePublicKeyResultKind
ProviderTrust = p.TicketAdmissionTelemetryLineagePublicKeyProviderTrust
ManifestEntry = m.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
build_manifest = (
    m.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)
manifest_fingerprint = (
    m.ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint
)
resolve_session = (
    s.resolve_ticket_admission_telemetry_lineage_signature_trust_async_session
)
session_id = s.ticket_admission_telemetry_lineage_public_key_provider_session_id

PORT_PREFIX = "explicit-async-session-ticket-admission-"
PORT_SUFFIX = "telemetry-lineage-public-key-provider-v1"
PORT_ID = f"{PORT_PREFIX}{PORT_SUFFIX}"
PROVIDER_ID = "provider.test.session-public-keys"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
VENDOR_DETAIL = "vendor session details must not cross the boundary"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_REQUESTS = 2
TWO_LIFECYCLES = 2
BATCH_PROVIDER_REPR = "_BatchProvider"
PROVIDER_FIELD_REPR = "provider="


class _BatchProvider:
    def __init__(
        self,
        *,
        old_public_key: bytes = OLD_PUBLIC_KEY,
        fail: bool = False,
        cancel: bool = False,
    ) -> None:
        self._old_public_key: bytes = old_public_key
        self._fail: bool = fail
        self._cancel: bool = cancel
        self.call_count: int = 0

    async def __call__(
        self,
        request: BatchRequest,
    ) -> BatchResult:
        self.call_count += 1
        if self._cancel:
            raise asyncio.CancelledError
        if self._fail:
            return BatchResult(
                results=(
                    PublicKeyResult(kind=ResultKind.FAILED),
                    PublicKeyResult(
                        kind=ResultKind.RESOLVED,
                        public_key=NEW_PUBLIC_KEY,
                    ),
                )
            )
        keys = {
            OLD_REFERENCE_ID: self._old_public_key,
            NEW_REFERENCE_ID: NEW_PUBLIC_KEY,
        }
        return BatchResult(
            results=tuple(
                PublicKeyResult(
                    kind=ResultKind.RESOLVED,
                    public_key=keys[item.public_key_reference_id],
                )
                for item in request.requests
            )
        )


class _Session:
    def __init__(  # ruff: ignore[too-many-arguments]
        self,
        provider_value: BatchProvider,
        *,
        open_kind: OpenKind = OpenKind.OPENED,
        close_kind: CloseKind = CloseKind.CLOSED,
        raise_open: bool = False,
        raise_close: bool = False,
        cancel_open: bool = False,
        cancel_close: bool = False,
    ) -> None:
        self._provider: BatchProvider = provider_value
        self._open_kind: OpenKind = open_kind
        self._close_kind: CloseKind = close_kind
        self._raise_open: bool = raise_open
        self._raise_close: bool = raise_close
        self._cancel_open: bool = cancel_open
        self._cancel_close: bool = cancel_close
        self.open_requests: list[OpenRequest] = []
        self.close_requests: list[CloseRequest] = []

    async def open(
        self,
        request: OpenRequest,
    ) -> OpenResult:
        self.open_requests.append(request)
        if self._cancel_open:
            raise asyncio.CancelledError
        if self._raise_open:
            message = VENDOR_DETAIL
            raise RuntimeError(message)
        opened = OpenKind.OPENED
        return OpenResult(
            kind=self._open_kind,
            provider=(self._provider if self._open_kind is opened else None),
        )

    async def close(
        self,
        request: CloseRequest,
    ) -> CloseResult:
        self.close_requests.append(request)
        if self._cancel_close:
            raise asyncio.CancelledError
        if self._raise_close:
            message = VENDOR_DETAIL
            raise RuntimeError(message)
        return CloseResult(kind=self._close_kind)


class _FixedSession:
    def __init__(self, open_value: object, close_value: object) -> None:
        self._open_value: object = open_value
        self._close_value: object = close_value
        self.open_requests: list[OpenRequest] = []
        self.close_requests: list[CloseRequest] = []

    async def open(self, request: OpenRequest) -> OpenResult:
        self.open_requests.append(request)
        return cast("OpenResult", self._open_value)

    async def close(self, request: CloseRequest) -> CloseResult:
        self.close_requests.append(request)
        return cast("CloseResult", self._close_value)


def _opened(batch_provider: BatchProvider | None) -> OpenResult:
    return OpenResult(kind=OpenKind.OPENED, provider=batch_provider)


def _closed() -> CloseResult:
    return CloseResult(kind=CloseKind.CLOSED)


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, None),
) -> ManifestEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return ManifestEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _manifest() -> SignatureManifest:
    return build_manifest((
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(window=(GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID)),
    ))


def _run(
    manifest_value: SignatureManifest,
    session: SessionPort,
    *,
    provider_id: str = PROVIDER_ID,
    max_requests: int = TWO_REQUESTS,
) -> ProviderTrust:
    return asyncio.run(
        resolve_session(
            manifest_value,
            session,
            provider_id=provider_id,
            max_requests=max_requests,
        )
    )


def test_empty_manifest_performs_no_lifecycle_calls() -> None:
    batch_provider = _BatchProvider()
    session = _Session(batch_provider)
    empty = build_manifest(())

    resolved = _run(empty, session, max_requests=1)

    assert session_id() == PORT_ID
    assert session.open_requests == []
    assert session.close_requests == []
    assert batch_provider.call_count == 0
    assert resolved.request_count == 0


def test_success_opens_batches_and_closes_once() -> None:
    batch_provider = _BatchProvider()
    session = _Session(batch_provider)
    manifest_value = _manifest()

    resolved = _run(manifest_value, session)

    assert batch_provider.call_count == 1
    assert len(session.open_requests) == 1
    assert len(session.close_requests) == 1
    opened = session.open_requests[0]
    closed = session.close_requests[0]
    assert opened.provider_id == PROVIDER_ID
    assert opened.request_count == TWO_REQUESTS
    assert opened.manifest_fingerprint == manifest_fingerprint(manifest_value)
    assert closed.manifest_fingerprint == opened.manifest_fingerprint
    assert closed.provider_id == opened.provider_id
    assert closed.request_count == opened.request_count
    assert closed.reason is CloseReason.COMPLETED
    assert resolved.request_count == TWO_REQUESTS
    assert resolved.trust.key_count == TWO_REQUESTS


def test_repeated_resolution_has_fresh_lifecycles() -> None:
    batch_provider = _BatchProvider()
    session = _Session(batch_provider)
    manifest_value = _manifest()

    first = _run(manifest_value, session)
    second = _run(manifest_value, session)

    assert first == second
    assert len(session.open_requests) == TWO_LIFECYCLES
    assert len(session.close_requests) == TWO_LIFECYCLES
    assert batch_provider.call_count == TWO_LIFECYCLES


def test_request_budget_fails_before_open() -> None:
    session = _Session(_BatchProvider())

    with pytest.raises(
        SessionError,
        match="request count exceeds",
    ):
        _ = _run(_manifest(), session, max_requests=1)

    assert session.open_requests == []
    assert session.close_requests == []


@pytest.mark.parametrize("max_requests", [0, True])
def test_invalid_request_limit_fails_before_open(max_requests: int) -> None:
    session = _Session(_BatchProvider())

    with pytest.raises(
        SessionError,
        match="positive integer",
    ):
        _ = _run(_manifest(), session, max_requests=max_requests)

    assert session.open_requests == []


@pytest.mark.parametrize(
    "provider_id", ["bad provider", "", cast("str", object())]
)
def test_invalid_provider_identity_fails_before_open(provider_id: str) -> None:
    session = _Session(_BatchProvider())

    with pytest.raises(
        SessionError,
        match="provider identity must use",
    ):
        _ = _run(_manifest(), session, provider_id=provider_id)

    assert session.open_requests == []


def test_tampered_manifest_fails_before_open() -> None:
    session = _Session(_BatchProvider())
    manifest_value = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(
        SessionError,
        match="manifest identity is unsupported",
    ):
        _ = _run(manifest_value, session)

    assert session.open_requests == []


@pytest.mark.parametrize(
    "kind",
    [
        OpenKind.UNAVAILABLE,
        OpenKind.FAILED,
    ],
)
def test_nonopened_result_stops_without_close(
    kind: OpenKind,
) -> None:
    batch_provider = _BatchProvider()
    session = _Session(batch_provider, open_kind=kind)

    with pytest.raises(
        SessionError,
        match=rf"session returned {kind.value}",
    ):
        _ = _run(_manifest(), session)

    assert len(session.open_requests) == 1
    assert session.close_requests == []
    assert batch_provider.call_count == 0


def test_open_exception_is_wrapped_without_vendor_text() -> None:
    session = _Session(_BatchProvider(), raise_open=True)

    with pytest.raises(
        SessionError,
        match="raised while opening",
    ) as caught:
        _ = _run(_manifest(), session)

    assert VENDOR_DETAIL not in str(caught.value)
    assert session.close_requests == []


def test_open_cancellation_propagates_without_close() -> None:
    session = _Session(_BatchProvider(), cancel_open=True)

    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), session)

    assert len(session.open_requests) == 1
    assert session.close_requests == []


def test_batch_failure_closes_with_failed_reason() -> None:
    batch_provider = _BatchProvider(fail=True)
    session = _Session(batch_provider)

    with pytest.raises(
        BatchProviderError,
        match="provider returned failed",
    ):
        _ = _run(_manifest(), session)

    assert batch_provider.call_count == 1
    assert len(session.close_requests) == 1
    assert session.close_requests[0].reason is CloseReason.FAILED


def test_batch_cancellation_closes_then_propagates() -> None:
    batch_provider = _BatchProvider(cancel=True)
    session = _Session(batch_provider)

    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), session)

    assert len(session.close_requests) == 1
    assert session.close_requests[0].reason is CloseReason.CANCELLED


def test_wrong_key_closes_with_failed_reason() -> None:
    session = _Session(_BatchProvider(old_public_key=WRONG_PUBLIC_KEY))

    with pytest.raises(
        BatchProviderError,
        match="fingerprint does not match",
    ):
        _ = _run(_manifest(), session)

    assert session.close_requests[0].reason is CloseReason.FAILED


def test_close_failed_result_fails_closed_after_success() -> None:
    failed = CloseKind.FAILED
    session = _Session(_BatchProvider(), close_kind=failed)

    with pytest.raises(
        SessionError,
        match="failed while closing",
    ):
        _ = _run(_manifest(), session)

    assert len(session.close_requests) == 1


def test_close_exception_is_wrapped_without_vendor_text() -> None:
    session = _Session(_BatchProvider(), raise_close=True)

    with pytest.raises(
        SessionError,
        match="raised while closing",
    ) as caught:
        _ = _run(_manifest(), session)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(session.close_requests) == 1


def test_close_cancellation_propagates() -> None:
    session = _Session(_BatchProvider(), cancel_close=True)

    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), session)

    assert len(session.close_requests) == 1


def test_open_result_hides_provider() -> None:
    batch_provider = _BatchProvider()
    result = OpenResult(
        kind=OpenKind.OPENED,
        provider=batch_provider,
    )

    assert BATCH_PROVIDER_REPR not in repr(result)
    assert PROVIDER_FIELD_REPR not in repr(result)


def test_lifecycle_enums_have_stable_values() -> None:
    assert tuple(kind.value for kind in OpenKind) == (
        "opened",
        "unavailable",
        "failed",
    )
    assert tuple(reason.value for reason in CloseReason) == (
        "completed",
        "failed",
        "cancelled",
    )
    assert tuple(kind.value for kind in CloseKind) == ("closed", "failed")


def test_foreign_open_result_type_fails_closed() -> None:
    session = _FixedSession(object(), _closed())

    with pytest.raises(SessionError, match="exact session result type"):
        _ = _run(_manifest(), session)

    assert len(session.open_requests) == 1
    assert session.close_requests == []


def test_foreign_open_result_kind_fails_closed() -> None:
    result = OpenResult(
        kind=cast("OpenKind", cast("object", "opened")),
        provider=_BatchProvider(),
    )
    session = _FixedSession(result, _closed())

    with pytest.raises(SessionError, match="exact session enum"):
        _ = _run(_manifest(), session)

    assert session.close_requests == []


def test_nonopened_result_cannot_carry_provider() -> None:
    result = OpenResult(kind=OpenKind.FAILED, provider=_BatchProvider())
    session = _FixedSession(result, _closed())

    with pytest.raises(SessionError, match="nonopened session result"):
        _ = _run(_manifest(), session)

    assert session.close_requests == []


def test_opened_result_requires_callable_provider() -> None:
    session = _FixedSession(_opened(None), _closed())

    with pytest.raises(SessionError, match="requires a callable provider"):
        _ = _run(_manifest(), session)

    assert session.close_requests == []


def test_foreign_close_result_type_fails_closed() -> None:
    session = _FixedSession(_opened(_BatchProvider()), object())

    with pytest.raises(SessionError, match="close result must use the exact"):
        _ = _run(_manifest(), session)

    assert len(session.close_requests) == 1


def test_foreign_close_result_kind_fails_closed() -> None:
    result = CloseResult(kind=cast("CloseKind", cast("object", "closed")))
    session = _FixedSession(_opened(_BatchProvider()), result)

    with pytest.raises(SessionError, match="close result kind"):
        _ = _run(_manifest(), session)

    assert len(session.close_requests) == 1


def test_close_failure_replaces_batch_failure() -> None:
    close_failed = CloseResult(kind=CloseKind.FAILED)
    session = _FixedSession(_opened(_BatchProvider(fail=True)), close_failed)

    with pytest.raises(SessionError, match="failed while closing"):
        _ = _run(_manifest(), session)

    assert session.close_requests[0].reason is CloseReason.FAILED


def test_close_failure_replaces_batch_cancellation() -> None:
    close_failed = CloseResult(kind=CloseKind.FAILED)
    session = _FixedSession(_opened(_BatchProvider(cancel=True)), close_failed)

    with pytest.raises(SessionError, match="failed while closing"):
        _ = _run(_manifest(), session)

    assert session.close_requests[0].reason is CloseReason.CANCELLED
