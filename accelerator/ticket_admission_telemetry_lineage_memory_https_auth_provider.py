# File:
#   - ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
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
#   - Reusable bounded caller-owned in-memory HTTPS Authorization provider.
# - Must-Not:
#   - Read environment, files, network, secret stores, discover, refresh, retry,
#     cache externally, persist, log values, create workers, or change policy.
# - Allows:
#   - Inputs: one provider identity and explicit immutable authorization entries.
#   - Outputs: stable typed results for exact nonsecret authorization requests.
#   - Side effects: none; retained Authorization values remain caller-owned.
# - Split-When:
#   - Split when async memory adaptation, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact bounded memory-auth boundary.
# - Summary:
#   - Exact reusable in-memory HTTPS Authorization provider.
# - Description:
#   - Revalidates bounded metadata and hidden values before every exact lookup.
# - Usage:
#   - Build explicitly, then pass the service to the synchronous auth port.
# - Defaults:
#   - At most 64 entries; empty services return unavailable for every request.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Reusable bounded caller-owned in-memory HTTPS Authorization provider."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from re import compile as compile_pattern
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTH_PROVIDER_ID: Final = (
    "memory-ticket-admission-lineage-https-authorization-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS: Final = 64
MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS: Final = 4096
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_RESOLVED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.RESOLVED
)
_UNAVAILABLE: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.UNAVAILABLE
)
_FAILED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.FAILED
)


class TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError(ValueError):
    """A caller-owned memory HTTPS Authorization provider is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryHttpsAuthorization:
    """One exact hidden Authorization value and its nonsecret request binding."""

    authorization_byte_count: int
    authorization_value: str = field(repr=False)
    bundle_fingerprint: str
    fetch_provider_id: str
    resource_id: str
    source_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider:
    """Immutable bounded memory service implementing the synchronous auth port."""

    entries: tuple[
        TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
        ...,
    ] = field(repr=False)
    max_entries: int
    provider_id: str
    service_id: str

    def __call__(
        self,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Return one exact matching Authorization value without mutation.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        service = _validated_service(self)
        validated_request = _validated_request(request)
        if validated_request.authorization_provider_id != service.provider_id:
            return _result(_FAILED)
        match = _matching_entry(service.entries, validated_request)
        if match is None:
            return _result(_UNAVAILABLE)
        return _result(_RESOLVED, authorization_value=match.authorization_value)


def ticket_admission_memory_https_authorization_provider_id() -> str:
    """Return the stable memory HTTPS Authorization provider identity.

    Returns:
        Versioned caller-owned memory-service identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTH_PROVIDER_ID


def build_ticket_admission_memory_https_authorization_provider(
    entries: tuple[
        TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS,
) -> TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider:
    """Build one reusable bounded caller-owned in-memory auth service.

    Returns:
        Validated immutable memory Authorization provider service.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "authorization provider identity",
    )
    entry_limit = _validated_max_entries(max_entries)
    validated_entries = _validated_entries(
        entries,
        provider_id=validated_provider_id,
        max_entries=entry_limit,
    )
    return TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider(
        entries=validated_entries,
        max_entries=entry_limit,
        provider_id=validated_provider_id,
        service_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTH_PROVIDER_ID,
    )


def validate_ticket_admission_memory_https_authorization_provider(
    service: TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider:
    """Validate one exact bounded memory Authorization provider.

    Returns:
        The same exact service after complete revalidation.

    """
    return _validated_service(service)


def _validated_service(
    service: TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider:
    if (
        type(service)
        is not TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider
    ):
        _raise_service("service must use the exact memory auth provider type")
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTH_PROVIDER_ID
    ):
        _raise_service("service identity is unsupported")
    provider_id = _validated_identifier(
        service.provider_id,
        "authorization provider identity",
    )
    entry_limit = _validated_max_entries(service.max_entries)
    _ = _validated_entries(
        service.entries,
        provider_id=provider_id,
        max_entries=entry_limit,
    )
    return service


def _validated_entries(
    entries: tuple[
        TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int,
) -> tuple[TicketAdmissionTelemetryLineageMemoryHttpsAuthorization, ...]:
    if type(entries) is not tuple:
        _raise_service("entries must use an exact immutable tuple")
    if len(entries) > max_entries:
        _raise_service("entry count exceeds configured authorization limit")
    validated = tuple(
        _validated_entry(entry, provider_id=provider_id) for entry in entries
    )
    if validated != tuple(sorted(validated, key=_entry_sort_key)):
        _raise_service("entries must use canonical deterministic ordering")
    identities = [_entry_identity(entry) for entry in validated]
    if len(identities) != len(set(identities)):
        _raise_service("entries contain duplicate request binding")
    return validated


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
    *,
    provider_id: str,
) -> TicketAdmissionTelemetryLineageMemoryHttpsAuthorization:
    if (
        type(entry)
        is not TicketAdmissionTelemetryLineageMemoryHttpsAuthorization
    ):
        _raise_service("entry must use the exact memory authorization type")
    prepared = auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization(
        max_authorization_bytes=auth.MAX_HTTPS_AUTHORIZATION_BYTES,
        request=auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest(
            authorization_provider_id=provider_id,
            bundle_fingerprint=entry.bundle_fingerprint,
            fetch_provider_id=entry.fetch_provider_id,
            resource_id=entry.resource_id,
            source_id=entry.source_id,
        ),
    )
    result = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult(
        kind=_RESOLVED,
        authorization_value=entry.authorization_value,
    )
    try:
        resolved = auth.materialize_ticket_admission_https_authorization(
            prepared,
            result,
        )
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "entry contains invalid authorization metadata or value"
        raise TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError(
            message
        ) from error
    if (
        type(entry.authorization_byte_count) is not int
        or entry.authorization_byte_count != resolved.authorization_byte_count
    ):
        _raise_service("entry authorization byte count does not match value")
    return entry


def _validated_request(
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest:
    try:
        return auth.validate_ticket_admission_https_authorization_request(
            request
        )
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "invalid memory-provider Authorization request"
        raise TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError(
            message
        ) from error


def _matching_entry(
    entries: tuple[
        TicketAdmissionTelemetryLineageMemoryHttpsAuthorization, ...
    ],
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> TicketAdmissionTelemetryLineageMemoryHttpsAuthorization | None:
    for entry in entries:
        if _entry_identity(entry) == (
            request.bundle_fingerprint,
            request.fetch_provider_id,
            request.resource_id,
            request.source_id,
        ):
            return entry
    return None


def _entry_identity(
    entry: TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
) -> tuple[str, str, str, str]:
    return (
        entry.bundle_fingerprint,
        entry.fetch_provider_id,
        entry.resource_id,
        entry.source_id,
    )


def _entry_sort_key(
    entry: TicketAdmissionTelemetryLineageMemoryHttpsAuthorization,
) -> tuple[str, str, str, str]:
    return _entry_identity(entry)


def _result(
    kind: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind,
    *,
    authorization_value: str | None = None,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    return auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult(
        kind=kind,
        authorization_value=authorization_value,
    )


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_service(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_service(f"{field_name} exceeds configured length")
    return value


def _validated_max_entries(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_service("maximum authorization count must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS:
        _raise_service("maximum authorization count exceeds supported limit")
    return value


def _raise_service(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory HTTPS Authorization provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError(message)
