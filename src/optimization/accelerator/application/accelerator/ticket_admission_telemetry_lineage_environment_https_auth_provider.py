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
#   - Explicit bounded environment-backed HTTPS Authorization resolution.
# - Must-Not:
#   - Enumerate environment state, discover names, mutate environment, read
#     files,
#     network, external stores, retry, cache, persist, log names or values,
#     create
#     workers, select schemes, refresh credentials, or change policy.
# - Allows:
#   - Inputs: one provider identity and explicit request-to-variable bindings.
#   - Outputs: stable typed results for exact nonsecret authorization requests.
#   - Side effects: one exact environment lookup for one matched request.
# - Split-When:
#   - Split when external stores, hosted APIs, certificates, PKI, or refresh
#     gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact explicit environment boundary.
# - Summary:
#   - Exact environment-backed HTTPS Authorization provider.
# - Description:
#   - Reads one caller-named variable only after complete request binding.
# - Usage:
#   - Build explicitly, then pass the service to the synchronous auth port.
# - Defaults:
#   - At most 64 bindings and 4096 Authorization bytes per matched variable.
#

"""Explicit bounded environment-backed HTTPS Authorization provider."""


from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from os import environ
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

TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTH_PROVIDER_ID: Final = (
    "explicit-environment-ticket-admission-lineage-https-"
    "authorization-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS: Final = (
    memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
)
MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS: Final = (
    memory.MAX_TELEMETRY_LINEAGE_MEMORY_HTTPS_AUTHORIZATIONS
)
DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES: Final = (
    auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES
)
MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES: Final = (
    auth.MAX_HTTPS_AUTHORIZATION_BYTES
)
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_ENVIRONMENT_VARIABLE_PATTERN: Final = compile_pattern(r"[A-Z][A-Z0-9_]{0,127}")
_RESOLVED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.RESOLVED
)
_UNAVAILABLE: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.UNAVAILABLE
)
_FAILED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.FAILED
)


class TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError(
    ValueError
):
    """An explicit environment HTTPS Authorization provider is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization:
    """One exact request binding and hidden canonical environment name."""

    bundle_fingerprint: str
    environment_variable_name: str = field(repr=False)
    fetch_provider_id: str
    resource_id: str
    source_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider:
    """Immutable explicit environment service implementing the auth port."""

    entries: tuple[
        TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
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
        """Read one exact matched environment value after full revalidation.

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
        return _environment_result(
            entry,
            validated_request,
            max_authorization_bytes=service.max_authorization_bytes,
        )


def ticket_admission_environment_https_authorization_provider_id() -> str:
    """Return the stable explicit environment provider identity.

    Returns:
        Versioned environment-service identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTH_PROVIDER_ID


def build_ticket_admission_environment_https_authorization_provider(
    entries: tuple[
        TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS
    ),
    max_authorization_bytes: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES
    ),
) -> TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider:
    """Build one bounded provider from explicit environment-name bindings.

    Returns:
        Canonically ordered service with hidden variable names.

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
    return TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider(
        entries=ordered,
        max_authorization_bytes=byte_limit,
        max_entries=entry_limit,
        provider_id=validated_provider_id,
        service_id=(
            # jig-ignore-next-line: indivisible reviewed identifier
            TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTH_PROVIDER_ID
        ),
    )


def validate_ticket_admission_environment_https_authorization_provider(
    service: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider:
    """Validate one exact bounded environment Authorization provider.

    Returns:
        The same exact service after complete non-lookup revalidation.

    """
    return _validated_service(service)


def _validated_service(
    service: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider:
    _validate_service_shape(service)
    entry_limit = _validated_max_entries(service.max_entries)
    _ = _validated_max_authorization_bytes(service.max_authorization_bytes)
    validated = _ordered_entries(
        service.entries,
        provider_id=service.provider_id,
        max_entries=entry_limit,
    )
    if service.entries != validated:
        _raise_service("service entries are not canonically ordered")
    return service


def _validate_service_shape(
    service: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
) -> None:
    if (
        type(service)
        is not TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider
    ):
        _raise_service(
            "service must use the exact environment auth provider type"
        )
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTH_PROVIDER_ID
    ):
        _raise_service("service identity is unsupported")
    _ = _validated_identifier(
        service.provider_id,
        "authorization provider identity",
    )


def _ordered_entries(
    entries: tuple[
        TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
        ...,
    ],
    *,
    provider_id: str,
    max_entries: int,
) -> tuple[TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization, ...]:
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
    entry: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
    *,
    provider_id: str,
) -> TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization:
    if (
        type(entry)
        is not TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization
    ):
        _raise_service(
            "entry must use the exact environment authorization type"
        )
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
        raise TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError(
            message
        ) from error
    _ = _validated_environment_variable_name(entry.environment_variable_name)
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
        message = "invalid environment-provider Authorization request"
        raise TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError(
            message
        ) from error


def _environment_result(
    entry: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    *,
    max_authorization_bytes: int,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    try:
        candidate = _read_environment_value(entry.environment_variable_name)
    except OSError, UnicodeError:
        return _result(_FAILED)
    if candidate is None:
        return _result(_UNAVAILABLE)
    return _validated_candidate_result(
        request,
        candidate,
        max_authorization_bytes=max_authorization_bytes,
    )


def _read_environment_value(variable_name: str) -> str | None:
    return environ.get(variable_name)


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
        TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
        ...,
    ],
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization | None:
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
    entry: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
) -> tuple[str, str, str, str]:
    return (
        entry.bundle_fingerprint,
        entry.fetch_provider_id,
        entry.resource_id,
        entry.source_id,
    )


def _entry_sort_key(
    entry: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthorization,
) -> tuple[str, str, str, str, str]:
    return (*_entry_identity(entry), entry.environment_variable_name)


def _result(
    kind: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind,
    *,
    authorization_value: str | None = None,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    return auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult(
        kind=kind,
        authorization_value=authorization_value,
    )


def _validated_environment_variable_name(value: str) -> str:
    if (
        type(value) is not str
        or _ENVIRONMENT_VARIABLE_PATTERN.fullmatch(value) is None
    ):
        _raise_service(
            "environment variable name must use canonical uppercase ASCII form"
        )
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_service("environment variable name exceeds configured length")
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
    if value > MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATIONS:
        _raise_service("maximum authorization count exceeds supported limit")
    return value


def _validated_max_authorization_bytes(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_service("maximum authorization bytes must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_ENVIRONMENT_HTTPS_AUTHORIZATION_BYTES:
        _raise_service("maximum authorization bytes exceeds supported limit")
    return value


def _raise_service(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage environment HTTPS Authorization "
        f"provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError(
        message
    )
