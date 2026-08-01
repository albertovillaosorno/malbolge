# File:
#   - ticket_admission_telemetry_lineage_memory_public_key_session.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
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
#   - Explicit serial async session adapter for one bounded memory key service.
# - Must-Not:
#   - Create event loops, tasks, locks, concurrency, scheduling points, discover,
#     retry, fetch, persist, validate certificates, or change policy.
# - Allows:
#   - Inputs: one exact memory service and exact open/close lifecycle requests.
#   - Outputs: one inline batch provider and exact typed close outcomes.
#   - Side effects: caller-owned serial lifecycle state only.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact memory-session adaptation.
# - Summary:
#   - Serial async session adapter for caller-owned detached public keys.
# - Description:
#   - Enforces one active memory-backed provider session with exact close binding.
# - Usage:
#   - Build explicitly and pass to the public-key provider-session boundary.
# - Defaults:
#   - At most 256 requests and one active lifecycle at a time.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_s.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Serial async session adapter for the bounded memory key provider."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_batch_provider as mb,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider_session as s,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_SESSION_ID: Final = (
    "memory-async-session-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_SESSION_REQUESTS: Final = (
    mb.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_REQUESTS
)
_validate_batch_provider: Final = (
    mb.validate_ticket_admission_memory_public_key_batch_provider
)

OpenKind = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind
)
CloseKind = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind
)
CloseReasonClass = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseReason
)
OpenRequestClass = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest
)
CloseRequestClass = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest
)
OpenResultClass = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
)
CloseResultClass = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
)
MemoryProviderClass = (
    memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
)
type OpenRequest = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenRequest
)
type CloseRequest = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseRequest
)
type OpenResult = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResult
)
type CloseResult = (
    s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResult
)
type MemoryProvider = (
    memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
)
type MemoryBatchProvider = (
    mb.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider
)


class TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError(
    ValueError
):
    """An in-memory provider session or lifecycle request is invalid."""


@dataclass(slots=True)
class TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession:
    """Mutable caller-owned serial lifecycle around one memory batch adapter."""

    active: bool
    batch_provider: MemoryBatchProvider = field(repr=False)
    completed_lifecycle_count: int
    key_count: int
    max_requests: int
    provider_id: str
    session_id: str
    active_open_request: OpenRequest | None = field(default=None, repr=False)

    async def open(
        self,
        request: OpenRequest,
    ) -> OpenResult:
        """Open one inline batch provider without an internal scheduling point.

        Returns:
            Typed opened or failed lifecycle result.

        """
        value = _validated_session(self)
        validated_request = _validated_open_request(request)
        if not _can_open(value, validated_request):
            return _open_result(OpenKind.FAILED)
        value.active = True
        value.active_open_request = validated_request
        return _open_result(
            OpenKind.OPENED,
            provider=value.batch_provider,
        )

    async def close(
        self,
        request: CloseRequest,
    ) -> CloseResult:
        """Close one exactly matching active lifecycle inline.

        Returns:
            Typed closed or failed lifecycle result.

        """
        value = _validated_session(self)
        validated_request = _validated_close_request(request)
        active_request = value.active_open_request
        if active_request is None or not _close_matches_open(
            validated_request,
            active_request,
        ):
            return _close_result(CloseKind.FAILED)
        value.active = False
        value.active_open_request = None
        value.completed_lifecycle_count += 1
        return _close_result(CloseKind.CLOSED)


def ticket_admission_memory_public_key_provider_session_id() -> str:
    """Return the stable in-memory provider-session adapter identity.

    Returns:
        Versioned session implementation identity.

    """
    return (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_SESSION_ID
    )


def build_ticket_admission_memory_public_key_provider_session(
    value: MemoryProvider,
    *,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_SESSION_REQUESTS
    ),
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession:
    """Build one reusable serial memory-backed provider session.

    Returns:
        Validated inactive session with hidden memory-backed batch provider.

    """
    validated_value = _validated_memory_input(value)
    request_limit = _validated_positive_limit(max_requests, "request limit")
    batch_provider = _build_batch_provider(
        validated_value,
        max_requests=request_limit,
    )
    return TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession(
        active=False,
        batch_provider=batch_provider,
        completed_lifecycle_count=0,
        key_count=batch_provider.key_count,
        max_requests=batch_provider.max_requests,
        provider_id=batch_provider.provider_id,
        session_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_SESSION_ID
        ),
    )


def _validated_memory_input(value: MemoryProvider) -> MemoryProvider:
    if type(value) is not MemoryProviderClass:
        _raise_session("memory provider must use the exact provider type")
    return value


def _build_batch_provider(
    value: MemoryProvider,
    *,
    max_requests: int,
) -> MemoryBatchProvider:
    try:
        return mb.build_ticket_admission_memory_public_key_batch_provider(
            value,
            max_requests=max_requests,
        )
    except (
        mb.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError
    ) as error:
        message = "cannot build memory batch provider"
        raise TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError(
            message
        ) from error


def validate_ticket_admission_memory_public_key_provider_session(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession:
    """Validate one exact mutable serial memory session.

    Returns:
        The exact validated session.

    """
    return _validated_session(value)


def _validated_session(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession:
    _validate_session_shape(value)
    batch_provider = _validated_batch(value.batch_provider)
    _validate_session_binding(value, batch_provider)
    _validate_active_binding(value)
    return value


def _validate_session_shape(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
) -> None:
    if (
        type(value)
        is not TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession
    ):
        _raise_session("session must use the exact memory-session type")
    if (
        value.session_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_SESSION_ID
    ):
        _raise_session("session identity is unsupported")
    if type(value.active) is not bool:
        _raise_session("active state must use the exact boolean type")
    _validate_session_counts(value)


def _validate_session_counts(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
) -> None:
    if type(value.key_count) is not int or value.key_count < 0:
        _raise_session("key count must be a nonnegative integer")
    _ = _validated_positive_limit(value.max_requests, "request limit")
    if (
        type(value.completed_lifecycle_count) is not int
        or value.completed_lifecycle_count < 0
    ):
        _raise_session("completed lifecycle count must be nonnegative")


def _validated_batch(
    value: MemoryBatchProvider,
) -> MemoryBatchProvider:
    try:
        return _validate_batch_provider(value)
    except (
        mb.TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError
    ) as error:
        message = f"invalid memory batch provider: {error}"
        raise TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError(
            message
        ) from error


def _validate_session_binding(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
    batch_provider: MemoryBatchProvider,
) -> None:
    if value.key_count != batch_provider.key_count:
        _raise_session("key count does not match batch provider")
    if value.max_requests != batch_provider.max_requests:
        _raise_session("request limit does not match batch provider")
    if value.provider_id != batch_provider.provider_id:
        _raise_session("provider identity does not match batch provider")


def _validate_active_binding(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
) -> None:
    active_request = value.active_open_request
    if value.active != (active_request is not None):
        _raise_session("active state does not match open request")
    if active_request is None:
        return
    validated = _validated_open_request(active_request)
    if validated.provider_id != value.provider_id:
        _raise_session("active provider identity does not match session")
    if validated.request_count > value.max_requests:
        _raise_session("active request count exceeds session limit")


def _validated_open_request(
    request: OpenRequest,
) -> OpenRequest:
    if type(request) is not OpenRequestClass:
        _raise_session("open request must use the exact session request type")
    _validate_lifecycle_metadata(
        request.manifest_fingerprint,
        request.provider_id,
        request.request_count,
    )
    return request


def _validated_close_request(
    request: CloseRequest,
) -> CloseRequest:
    if type(request) is not CloseRequestClass:
        _raise_session("close request must use the exact session request type")
    if type(request.reason) is not CloseReasonClass:
        _raise_session("close reason must use the exact session enum")
    _validate_lifecycle_metadata(
        request.manifest_fingerprint,
        request.provider_id,
        request.request_count,
    )
    return request


def _validate_lifecycle_metadata(
    manifest_fingerprint: str,
    provider_id: str,
    request_count: int,
) -> None:
    if type(manifest_fingerprint) is not str or not manifest_fingerprint:
        _raise_session("manifest fingerprint must be a nonempty string")
    if type(provider_id) is not str or not provider_id:
        _raise_session("provider identity must be a nonempty string")
    if type(request_count) is not int or request_count <= 0:
        _raise_session("request count must be a positive integer")


def _can_open(
    value: TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSession,
    request: OpenRequest,
) -> bool:
    return (
        not value.active
        and request.provider_id == value.provider_id
        and request.request_count <= value.max_requests
    )


def _close_matches_open(
    request: CloseRequest,
    open_request: OpenRequest,
) -> bool:
    return (
        request.manifest_fingerprint == open_request.manifest_fingerprint
        and request.provider_id == open_request.provider_id
        and request.request_count == open_request.request_count
    )


def _open_result(
    kind: s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionOpenResultKind,
    *,
    provider: MemoryBatchProvider | None = None,
) -> OpenResult:
    return OpenResultClass(
        kind=kind,
        provider=provider,
    )


def _close_result(
    kind: s.TicketAdmissionTelemetryLineagePublicKeyProviderSessionCloseResultKind,
) -> CloseResult:
    return CloseResultClass(kind=kind)


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_session(f"{field_name} must be a positive integer")
    return value


def _raise_session(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory public-key provider session "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryPublicKeyProviderSessionError(
        message
    )
