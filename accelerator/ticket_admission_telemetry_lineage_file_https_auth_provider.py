# File:
#   - ticket_admission_telemetry_lineage_file_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_file_https_auth_provider.py
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
#   - Explicit bounded read-only files for HTTPS Authorization requests.
# - Must-Not:
#   - Discover paths, write files, retry, cache Authorization text, inspect
#     permissions, follow provider lifecycles, log values or paths, create
#     workers, select schemes, refresh credentials, or change policy.
# - Allows:
#   - Inputs: one provider identity and explicit request-bound absolute paths.
#   - Outputs: stable typed results containing exact caller-file ASCII text.
#   - Side effects: one bounded explicit file read for one exact matched request.
# - Split-When:
#   - Split when native async file I/O, external stores, hosted APIs,
#     certificates, PKI, or refresh gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact explicit file-auth boundary.
# - Summary:
#   - Exact read-only file-backed HTTPS Authorization provider.
# - Description:
#   - Reads one caller-selected file only after exact request binding.
# - Usage:
#   - Build explicitly from absolute paths, then pass to the synchronous port.
# - Defaults:
#   - At most 64 bindings and 4096 Authorization bytes per matched file.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_secret_provider.py
# - accelerator/ticket_admission_file_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit bounded read-only files for HTTPS Authorization requests."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from re import compile as compile_pattern
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_memory_https_auth_provider as memory,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_HTTPS_AUTH_PROVIDER_ID: Final = (
    "explicit-file-ticket-admission-lineage-https-authorization-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS: Final = (
    memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
)
MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS: Final = (
    memory.MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
)
DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES: Final = (
    auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES
)
MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES: Final = (
    auth.MAX_HTTPS_AUTHORIZATION_BYTES
)
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
_NUL: Final = chr(0)


class TicketAdmissionTelemetryLineageFileHttpsAuthProviderError(ValueError):
    """An explicit bounded file HTTPS Authorization provider is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFileHttpsAuthorization:
    """One exact request binding and hidden absolute Authorization path."""

    authorization_path: str = field(repr=False)
    bundle_fingerprint: str
    fetch_provider_id: str
    resource_id: str
    source_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFileHttpsAuthProvider:
    """Immutable explicit read-only file service implementing the auth port."""

    authorization_count: int
    entries: tuple[
        TicketAdmissionTelemetryLineageFileHttpsAuthorization,
        ...,
    ] = field(repr=False)
    max_authorization_bytes: int
    max_entries: int
    provider_id: str
    service_id: str

    def __call__(
        self,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Read one exact matched file after complete revalidation.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        service = _validated_service(self)
        validated_request = _validated_request(request)
        if validated_request.authorization_provider_id != service.provider_id:
            return _result(_FAILED)
        entry = _matching_entry(service.entries, validated_request)
        if entry is None:
            return _result(_UNAVAILABLE)
        return _file_result(
            entry,
            validated_request,
            max_authorization_bytes=service.max_authorization_bytes,
        )


def ticket_admission_file_https_authorization_provider_id() -> str:
    """Return the stable explicit file provider identity.

    Returns:
        Versioned file-service identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_HTTPS_AUTH_PROVIDER_ID


def build_ticket_admission_file_https_authorization_provider(
    entries: tuple[
        TicketAdmissionTelemetryLineageFileHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS,
    max_authorization_bytes: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES
    ),
) -> TicketAdmissionTelemetryLineageFileHttpsAuthProvider:
    """Build one bounded provider from explicit absolute file bindings.

    Returns:
        Canonically ordered service with hidden caller-selected paths.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "authorization provider identity",
    )
    entry_limit = _validated_max_entries(max_entries)
    byte_limit = _validated_max_authorization_bytes(max_authorization_bytes)
    ordered = _ordered_entries(
        entries,
        provider_id=validated_provider_id,
        max_entries=entry_limit,
    )
    return TicketAdmissionTelemetryLineageFileHttpsAuthProvider(
        authorization_count=len(ordered),
        entries=ordered,
        max_authorization_bytes=byte_limit,
        max_entries=entry_limit,
        provider_id=validated_provider_id,
        service_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_HTTPS_AUTH_PROVIDER_ID,
    )


def validate_ticket_admission_file_https_authorization_provider(
    service: TicketAdmissionTelemetryLineageFileHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageFileHttpsAuthProvider:
    """Validate one exact bounded file Authorization provider.

    Returns:
        The same exact service after complete non-I/O revalidation.

    """
    return _validated_service(service)


def _validated_service(
    service: TicketAdmissionTelemetryLineageFileHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageFileHttpsAuthProvider:
    _validate_service_shape(service)
    entry_limit = _validated_max_entries(service.max_entries)
    _ = _validated_max_authorization_bytes(service.max_authorization_bytes)
    _validate_service_count(service, entry_limit=entry_limit)
    validated = _ordered_entries(
        service.entries,
        provider_id=service.provider_id,
        max_entries=entry_limit,
    )
    if service.entries != validated:
        _raise_service("service entries are not canonically ordered")
    return service


def _validate_service_shape(
    service: TicketAdmissionTelemetryLineageFileHttpsAuthProvider,
) -> None:
    if (
        type(service)
        is not TicketAdmissionTelemetryLineageFileHttpsAuthProvider
    ):
        _raise_service("service must use the exact file auth provider type")
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_HTTPS_AUTH_PROVIDER_ID
    ):
        _raise_service("service identity is unsupported")
    _ = _validated_identifier(
        service.provider_id,
        "authorization provider identity",
    )
    if type(service.entries) is not tuple:
        _raise_service(
            "service entries must use the exact immutable tuple type"
        )


def _validate_service_count(
    service: TicketAdmissionTelemetryLineageFileHttpsAuthProvider,
    *,
    entry_limit: int,
) -> None:
    if (
        type(service.authorization_count) is not int
        or service.authorization_count < 0
    ):
        _raise_service(
            "service authorization count must be a nonnegative integer"
        )
    if service.authorization_count != len(service.entries):
        _raise_service("service authorization count does not match entries")
    if service.authorization_count > entry_limit:
        _raise_service(
            "service authorization count exceeds configured entry limit"
        )


def _ordered_entries(
    entries: tuple[
        TicketAdmissionTelemetryLineageFileHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int,
) -> tuple[TicketAdmissionTelemetryLineageFileHttpsAuthorization, ...]:
    if type(entries) is not tuple:
        _raise_service("entries must use the exact immutable tuple type")
    if len(entries) > max_entries:
        _raise_service("entry count exceeds configured authorization limit")
    validated = tuple(
        _validated_entry(entry, provider_id=provider_id) for entry in entries
    )
    identities = [_entry_identity(entry) for entry in validated]
    if len(identities) != len(set(identities)):
        _raise_service("entries contain duplicate request binding")
    return tuple(sorted(validated, key=_entry_sort_key))


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageFileHttpsAuthorization,
    *,
    provider_id: str,
) -> TicketAdmissionTelemetryLineageFileHttpsAuthorization:
    if type(entry) is not TicketAdmissionTelemetryLineageFileHttpsAuthorization:
        _raise_service("entry must use the exact file authorization type")
    request = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest(
        authorization_provider_id=provider_id,
        bundle_fingerprint=entry.bundle_fingerprint,
        fetch_provider_id=entry.fetch_provider_id,
        resource_id=entry.resource_id,
        source_id=entry.source_id,
    )
    try:
        _ = auth.validate_ticket_admission_https_authorization_request(request)
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "entry contains invalid authorization request metadata"
        raise TicketAdmissionTelemetryLineageFileHttpsAuthProviderError(
            message
        ) from error
    _ = _validated_absolute_path(entry.authorization_path)
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
        message = "invalid file-provider Authorization request"
        raise TicketAdmissionTelemetryLineageFileHttpsAuthProviderError(
            message
        ) from error


def _file_result(
    entry: TicketAdmissionTelemetryLineageFileHttpsAuthorization,
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    *,
    max_authorization_bytes: int,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    kind, candidate = _read_authorization_bytes(
        entry.authorization_path,
        max_authorization_bytes=max_authorization_bytes,
    )
    if kind is not _RESOLVED or candidate is None:
        return _result(kind)
    try:
        authorization_value = candidate.decode("ascii")
    except UnicodeDecodeError:
        return _result(_FAILED)
    return _validated_candidate_result(
        request,
        authorization_value,
        max_authorization_bytes=max_authorization_bytes,
    )


def _read_authorization_bytes(
    authorization_path: str,
    *,
    max_authorization_bytes: int,
) -> tuple[
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind,
    bytes | None,
]:
    kind = _FAILED
    authorization_bytes: bytes | None = None
    try:
        with Path(authorization_path).open("rb") as stream:
            candidate = stream.read(max_authorization_bytes + 1)
    except FileNotFoundError:
        kind = _UNAVAILABLE
    except OSError:
        kind = _FAILED
    else:
        if len(candidate) <= max_authorization_bytes:
            kind = _RESOLVED
            authorization_bytes = candidate
    return (kind, authorization_bytes)


def _validated_candidate_result(
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    candidate: str,
    *,
    max_authorization_bytes: int,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    result = _result(_RESOLVED, authorization_value=candidate)
    prepared = auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization(
        max_authorization_bytes=max_authorization_bytes,
        request=request,
    )
    try:
        _ = auth.materialize_ticket_admission_https_authorization(
            prepared,
            result,
        )
    except auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError:
        return _result(_FAILED)
    return result


def _matching_entry(
    entries: tuple[
        TicketAdmissionTelemetryLineageFileHttpsAuthorization,
        ...,
    ],
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> TicketAdmissionTelemetryLineageFileHttpsAuthorization | None:
    identity = (
        request.bundle_fingerprint,
        request.fetch_provider_id,
        request.resource_id,
        request.source_id,
    )
    for entry in entries:
        if _entry_identity(entry) == identity:
            return entry
    return None


def _entry_identity(
    entry: TicketAdmissionTelemetryLineageFileHttpsAuthorization,
) -> tuple[str, str, str, str]:
    return (
        entry.bundle_fingerprint,
        entry.fetch_provider_id,
        entry.resource_id,
        entry.source_id,
    )


def _entry_sort_key(
    entry: TicketAdmissionTelemetryLineageFileHttpsAuthorization,
) -> tuple[str, str, str, str, str]:
    return (*_entry_identity(entry), entry.authorization_path)


def _result(
    kind: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind,
    *,
    authorization_value: str | None = None,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    return auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult(
        kind=kind,
        authorization_value=authorization_value,
    )


def _validated_absolute_path(value: str) -> str:
    if type(value) is not str or not value or _NUL in value:
        _raise_service("authorization path must be a nonempty path string")
    if not Path(value).is_absolute():
        _raise_service("authorization path must be absolute")
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_service(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_service(f"{field_name} exceeds configured length")
    return value


def _validated_max_entries(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_service("maximum authorization count must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS:
        _raise_service("maximum authorization count exceeds supported limit")
    return value


def _validated_max_authorization_bytes(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_service("maximum authorization bytes must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES:
        _raise_service("maximum authorization bytes exceeds supported limit")
    return value


def _raise_service(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage file HTTPS Authorization provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageFileHttpsAuthProviderError(message)
