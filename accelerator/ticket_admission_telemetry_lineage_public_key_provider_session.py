# File:
#   - ticket_admission_telemetry_lineage_public_key_provider_session.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
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
#   - Explicit async lifecycle around one caller-owned batch key provider.
# - Must-Not:
#   - Create services, event loops, tasks, discover, retry, cache, persist,
#     validate certificates, select algorithms, or change policy.
# - Allows:
#   - Inputs: one manifest, provider identity, and caller-supplied session port.
#   - Outputs: typed lifecycle requests and manifest-bound signature trust.
#   - Side effects: one open and one close call for each nonempty resolution.
# - Split-When:
#   - Split when native async HTTPS, concrete Authorization providers,
#     async Authorization injection, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact provider-session boundary.
# - Summary:
#   - Explicit one-use async public-key provider session lifecycle.
# - Description:
#   - Opens one batch provider and closes it after success, failure, or cancel.
# - Usage:
#   - Await from a caller-owned event loop with one caller-owned session port.
# - Defaults:
#   - At most 256 requests; empty manifests perform no lifecycle calls.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit async lifecycle for caller-owned public-key batch providers."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_batch_provider as batch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust_manifest import (
    ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_public_key_provider as provider_types,
    )

_SESSION_ID_PREFIX: Final = "explicit-async-session-ticket-admission-"
_SESSION_ID_SUFFIX: Final = "telemetry-lineage-public-key-provider-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_SESSION_ID: Final = (
    f"{_SESSION_ID_PREFIX}{_SESSION_ID_SUFFIX}"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_SESSION_REQUESTS: Final = (
    batch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_REQUESTS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_resolve_batch: Final = (
    batch.resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch
)


class TicketAdmissionTelemetryLineagePublicKeyProviderSessionError(ValueError):
    """An explicit async provider session is invalid or unsuccessful."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest:
    """Immutable metadata for one explicit provider-session opening."""

    manifest_fingerprint: str
    provider_id: str
    request_count: int


class TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind(
    StrEnum
):
    """Stable session-opening outcome without provider-specific text."""

    OPENED = "opened"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult:
    """Typed opening outcome with a hidden optional batch provider."""

    kind: TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind
    provider: (
        batch.TicketAdmissionTelemetryLineagePublicKeyBatchProvider | None
    ) = field(default=None, repr=False)


class TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason(
    StrEnum
):
    """Stable reason for one mandatory opened-session close attempt."""

    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest:
    """Immutable metadata for one explicit provider-session close attempt."""

    manifest_fingerprint: str
    provider_id: str
    reason: TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason
    request_count: int


class TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind(
    StrEnum
):
    """Stable session-closing outcome without provider-specific text."""

    CLOSED = "closed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult:
    """Typed closing outcome for one previously opened session."""

    kind: TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind


class TicketAdmissionTelemetryLineagePublicKeyProviderSession(Protocol):
    """Caller-supplied one-use async provider-session lifecycle."""

    async def open(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult:
        """Open one caller-owned batch provider."""
        ...

    async def close(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult:
        """Close one previously opened provider session."""
        ...


type _OpenRequest = (
    TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest
)
type _OpenResult = (
    TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
)
type _CloseRequest = (
    TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest
)
type _CloseResult = (
    TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
)


def ticket_admission_telemetry_lineage_public_key_provider_session_id() -> str:
    """Return the stable explicit provider-session identity.

    Returns:
        Versioned provider-session port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_SESSION_ID


async def resolve_ticket_admission_telemetry_lineage_signature_trust_async_session(
    manifest_value: manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    session: TicketAdmissionTelemetryLineagePublicKeyProviderSession,
    *,
    provider_id: str,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_SESSION_REQUESTS
    ),
) -> provider_types.TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    """Resolve one manifest through one explicit async provider session.

    Returns:
        Manifest-bound signature trust and non-key request metadata.

    Cancellation propagates after a successful close attempt. A close failure
    fails closed and replaces the preceding operation outcome.

    Raises:
        CancelledError: Opening, provider execution, or closing is cancelled.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "provider identity",
    )
    request_limit = _validated_positive_limit(max_requests, "request limit")
    manifest_fingerprint = _validated_manifest_fingerprint(manifest_value)
    request_count = len(manifest_value.entries)
    if request_count > request_limit:
        _raise_session("manifest request count exceeds configured limit")
    if request_count == 0:
        return await _resolve_batch(
            manifest_value,
            _UnreachableBatchProvider(),
            provider_id=validated_provider_id,
            max_requests=request_limit,
        )
    close_reason = (
        TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason
    )
    open_request = (
        TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest(
            manifest_fingerprint=manifest_fingerprint,
            provider_id=validated_provider_id,
            request_count=request_count,
        )
    )
    provider = await _open_session(session, open_request)
    try:
        resolved = await _resolve_batch(
            manifest_value,
            provider,
            provider_id=validated_provider_id,
            max_requests=request_limit,
        )
    except CancelledError:
        await _close_session(
            session,
            _close_request(open_request, close_reason.CANCELLED),
        )
        raise
    except Exception:
        await _close_session(
            session,
            _close_request(open_request, close_reason.FAILED),
        )
        raise
    await _close_session(
        session,
        _close_request(open_request, close_reason.COMPLETED),
    )
    return resolved


class _UnreachableBatchProvider:
    async def __call__(
        self,
        request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
    ) -> batch.TicketAdmissionTelemetryLineagePublicKeyBatchResult:
        del request
        message = "empty manifest unexpectedly called batch provider"
        raise AssertionError(message)


def _validated_manifest_fingerprint(
    manifest_value: manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> str:
    try:
        return ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            manifest_value
        )
    except (
        manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestError
    ) as error:
        message = f"invalid signature trust manifest: {error}"
        raise TicketAdmissionTelemetryLineagePublicKeyProviderSessionError(
            message
        ) from error


async def _open_session(
    session: TicketAdmissionTelemetryLineagePublicKeyProviderSession,
    request: _OpenRequest,
) -> batch.TicketAdmissionTelemetryLineagePublicKeyBatchProvider:
    result = await _await_open(session, request)
    _validate_open_result_shape(result)
    open_kind = (
        TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind
    )
    if result.kind is not open_kind.OPENED:
        _raise_unopened_result(result)
    return _validated_opened_provider(result.provider)


async def _await_open(
    session: TicketAdmissionTelemetryLineagePublicKeyProviderSession,
    request: _OpenRequest,
) -> _OpenResult:
    try:
        return await session.open(request)
    except CancelledError:
        raise
    except Exception as error:
        message = "provider session raised while opening"
        raise TicketAdmissionTelemetryLineagePublicKeyProviderSessionError(
            message
        ) from error


def _validate_open_result_shape(result: _OpenResult) -> None:
    if (
        type(result)
        is not TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
    ):
        _raise_session("open result must use the exact session result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind
    ):
        _raise_session("open result kind must use the exact session enum")


def _raise_unopened_result(result: _OpenResult) -> Never:
    if result.provider is not None:
        _raise_session("nonopened session result cannot contain a provider")
    _raise_session(f"session returned {result.kind.value} while opening")


def _validated_opened_provider(
    provider: batch.TicketAdmissionTelemetryLineagePublicKeyBatchProvider
    | None,
) -> batch.TicketAdmissionTelemetryLineagePublicKeyBatchProvider:
    if provider is None or not callable(provider):
        _raise_session("opened session result requires a callable provider")
    return provider


def _close_request(
    open_request: _OpenRequest,
    reason: TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason,
) -> _CloseRequest:
    return TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest(
        manifest_fingerprint=open_request.manifest_fingerprint,
        provider_id=open_request.provider_id,
        reason=reason,
        request_count=open_request.request_count,
    )


async def _close_session(
    session: TicketAdmissionTelemetryLineagePublicKeyProviderSession,
    request: _CloseRequest,
) -> None:
    result = await _await_close(session, request)
    _validate_close_result(result)


async def _await_close(
    session: TicketAdmissionTelemetryLineagePublicKeyProviderSession,
    request: _CloseRequest,
) -> _CloseResult:
    try:
        return await session.close(request)
    except CancelledError:
        raise
    except Exception as error:
        message = "provider session raised while closing"
        raise TicketAdmissionTelemetryLineagePublicKeyProviderSessionError(
            message
        ) from error


def _validate_close_result(result: _CloseResult) -> None:
    if (
        type(result)
        is not TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
    ):
        _raise_session("close result must use the exact session result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind
    ):
        _raise_session("close result kind must use the exact session enum")
    close_kind = (
        TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind
    )
    if result.kind is not close_kind.CLOSED:
        _raise_session("session returned failed while closing")


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_session(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_session(f"{field_name} exceeds configured length")
    return value


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_session(f"{field_name} must be a positive integer")
    return value


def _raise_session(detail: str) -> Never:
    message = f"ticket admission telemetry lineage public-key session {detail}"
    raise TicketAdmissionTelemetryLineagePublicKeyProviderSessionError(message)
