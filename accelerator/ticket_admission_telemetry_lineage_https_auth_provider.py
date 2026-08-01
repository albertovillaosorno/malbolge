# File:
#   - ticket_admission_telemetry_lineage_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
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
#   - Explicit synchronous provider port for one HTTPS Authorization value.
# - Must-Not:
#   - Inject headers, select schemes, discover credentials, retry, cache,
#     persist, log authorization values, create workers, or change policy.
# - Allows:
#   - Inputs: one exact HTTPS fetcher, request, provider identity, and port.
#   - Outputs: one hidden caller-owned bounded Authorization value and metadata.
#   - Side effects: exactly one explicit provider call per successful preflight.
# - Split-When:
#   - Split when async providers or Authorization injection, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact Authorization-provider boundary.
# - Summary:
#   - Explicit one-call HTTPS Authorization credential-provider port.
# - Description:
#   - Resolves bounded opaque ASCII authorization without scheme policy.
# - Usage:
#   - Resolve explicitly, then pass the caller-owned value to a later transport.
# - Defaults:
#   - At most 4096 ASCII bytes and never more than 16384 bytes.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit bounded HTTPS Authorization credential-provider port."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_AUTHORIZATION_PROVIDER_ID: Final = (
    "explicit-ticket-admission-lineage-https-authorization-provider-v1"
)
HTTPS_AUTHORIZATION_HEADER_NAME: Final = "Authorization"
DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES: Final = 4096
MAX_HTTPS_AUTHORIZATION_BYTES: Final = 16384
_ASCII_SPACE: Final = 32
_ASCII_VISIBLE_MIN: Final = 33
_ASCII_VISIBLE_MAX: Final = 126
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_BUNDLE_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:[0-9a-f]{64}"
)
_validate_https_fetcher: Final = (
    https.validate_ticket_admission_https_public_key_bundle_fetcher
)
_validate_fetch_request: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_request
)


class TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError(
    ValueError
):
    """An explicit HTTPS Authorization request or result is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageHttpsAuthorizationRequest:
    """Immutable nonsecret metadata for one Authorization resolution."""

    authorization_provider_id: str
    bundle_fingerprint: str
    fetch_provider_id: str
    resource_id: str
    source_id: str


class TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind(StrEnum):
    """Stable provider outcome without exception or vendor text."""

    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    """Typed provider outcome with hidden optional Authorization value."""

    kind: TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
    authorization_value: str | None = field(default=None, repr=False)


class TicketAdmissionTelemetryLineageHttpsAuthorizationProvider(Protocol):
    """Caller-supplied synchronous credential resolver without lifecycle."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Return one typed result for exact immutable nonsecret metadata."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageResolvedHttpsAuthorization:
    """Caller-owned hidden Authorization value and stable request metadata."""

    authorization_byte_count: int
    authorization_provider_id: str
    authorization_value: str = field(repr=False)
    bundle_fingerprint: str
    fetch_provider_id: str
    header_name: str
    resource_id: str
    source_id: str


def ticket_admission_https_authorization_provider_id() -> str:
    """Return the stable explicit HTTPS Authorization provider identity.

    Returns:
        Versioned synchronous Authorization-provider port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_AUTHORIZATION_PROVIDER_ID


def resolve_ticket_admission_https_authorization(  # ruff: ignore[too-many-arguments]
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    provider: TicketAdmissionTelemetryLineageHttpsAuthorizationProvider,
    *,
    authorization_provider_id: str,
    max_authorization_bytes: int = DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES,
) -> TicketAdmissionTelemetryLineageResolvedHttpsAuthorization:
    """Resolve one caller-owned Authorization value through an explicit port.

    Returns:
        Hidden bounded Authorization value and stable request metadata.

    """
    validated_fetcher = _validated_https_fetcher(fetcher)
    validated_request = _validated_fetch_request(request)
    validated_provider_id = _validated_identifier(
        authorization_provider_id,
        "authorization provider identity",
    )
    byte_limit = _validated_byte_limit(max_authorization_bytes)
    _validate_provider(provider)
    _validate_fetch_binding(validated_fetcher, validated_request)
    provider_request = TicketAdmissionTelemetryLineageHttpsAuthorizationRequest(
        authorization_provider_id=validated_provider_id,
        bundle_fingerprint=validated_request.bundle_fingerprint,
        fetch_provider_id=validated_request.provider_id,
        resource_id=validated_request.resource_id,
        source_id=validated_request.source_id,
    )
    result = _call_provider(provider, provider_request)
    validated_result = validate_ticket_admission_https_authorization_result(
        result
    )
    resolved_kind = (
        TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.RESOLVED
    )
    if validated_result.kind is not resolved_kind:
        _raise_provider(f"provider returned {validated_result.kind.value}")
    authorization_value = _validated_authorization_value(
        validated_result.authorization_value,
        max_bytes=byte_limit,
    )
    return TicketAdmissionTelemetryLineageResolvedHttpsAuthorization(
        authorization_byte_count=len(authorization_value.encode("ascii")),
        authorization_provider_id=validated_provider_id,
        authorization_value=authorization_value,
        bundle_fingerprint=validated_request.bundle_fingerprint,
        fetch_provider_id=validated_request.provider_id,
        header_name=HTTPS_AUTHORIZATION_HEADER_NAME,
        resource_id=validated_request.resource_id,
        source_id=validated_request.source_id,
    )


def validate_ticket_admission_https_authorization_request(
    request: TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> TicketAdmissionTelemetryLineageHttpsAuthorizationRequest:
    """Validate one exact immutable nonsecret credential request.

    Returns:
        The same exact validated request.

    """
    if (
        type(request)
        is not TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
    ):
        _raise_provider("request must use the exact authorization request type")
    _ = _validated_identifier(
        request.authorization_provider_id,
        "authorization provider identity",
    )
    _ = _validated_identifier(
        request.fetch_provider_id, "fetch provider identity"
    )
    _ = _validated_identifier(request.resource_id, "resource identity")
    _ = _validated_identifier(request.source_id, "source identity")
    if (
        type(request.bundle_fingerprint) is not str
        or _BUNDLE_FINGERPRINT_PATTERN.fullmatch(request.bundle_fingerprint)
        is None
    ):
        _raise_provider("bundle fingerprint is malformed")
    return request


def validate_ticket_admission_https_authorization_result(
    result: TicketAdmissionTelemetryLineageHttpsAuthorizationResult,
) -> TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    """Validate one exact typed Authorization provider result shape.

    Returns:
        The same exact validated result.

    """
    if (
        type(result)
        is not TicketAdmissionTelemetryLineageHttpsAuthorizationResult
    ):
        _raise_provider("result must use the exact authorization result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
    ):
        _raise_provider(
            "result kind must use the exact authorization result enum"
        )
    resolved = (
        TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.RESOLVED
    )
    if result.kind is not resolved and result.authorization_value is not None:
        _raise_provider(
            "nonresolved authorization result cannot contain credential text"
        )
    return result


def validate_ticket_admission_resolved_https_authorization(
    value: TicketAdmissionTelemetryLineageResolvedHttpsAuthorization,
) -> TicketAdmissionTelemetryLineageResolvedHttpsAuthorization:
    """Validate one exact caller-owned resolved Authorization value.

    Returns:
        The same exact resolved value after complete binding validation.

    """
    if (
        type(value)
        is not TicketAdmissionTelemetryLineageResolvedHttpsAuthorization
    ):
        _raise_provider(
            "resolved authorization must use the exact resolved type"
        )
    _ = _validated_identifier(
        value.authorization_provider_id,
        "authorization provider identity",
    )
    _ = _validated_identifier(
        value.fetch_provider_id,
        "fetch provider identity",
    )
    _ = _validated_identifier(value.resource_id, "resource identity")
    _ = _validated_identifier(value.source_id, "source identity")
    if (
        type(value.bundle_fingerprint) is not str
        or _BUNDLE_FINGERPRINT_PATTERN.fullmatch(value.bundle_fingerprint)
        is None
    ):
        _raise_provider("resolved bundle fingerprint is malformed")
    if value.header_name != HTTPS_AUTHORIZATION_HEADER_NAME:
        _raise_provider("resolved header name is unsupported")
    authorization_value = _validated_authorization_value(
        value.authorization_value,
        max_bytes=MAX_HTTPS_AUTHORIZATION_BYTES,
    )
    byte_count = len(authorization_value.encode("ascii"))
    if type(value.authorization_byte_count) is not int or (
        value.authorization_byte_count != byte_count
    ):
        _raise_provider(
            "resolved authorization byte count does not match value"
        )
    return value


def _validated_https_fetcher(
    value: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    try:
        return _validate_https_fetcher(value)
    except (
        https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError
    ) as error:
        message = "invalid HTTPS fetcher for authorization resolution"
        raise TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError(
            message
        ) from error


def _validated_fetch_request(
    value: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    try:
        return _validate_fetch_request(value)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "invalid fetch request for authorization resolution"
        raise TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError(
            message
        ) from error


def _validate_fetch_binding(
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> None:
    if request.resource_id != fetcher.config.resource_id:
        _raise_provider(
            "fetch request resource identity does not match HTTPS fetcher"
        )
    if request.source_id != fetcher.config.source_id:
        _raise_provider(
            "fetch request source identity does not match HTTPS fetcher"
        )


def _validate_provider(value: object) -> None:
    if not callable(value):
        _raise_provider("authorization provider must be callable")


def _call_provider(
    provider: TicketAdmissionTelemetryLineageHttpsAuthorizationProvider,
    request: TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    _ = validate_ticket_admission_https_authorization_request(request)
    try:
        return provider(request)
    except Exception as error:
        message = "authorization provider raised during explicit resolution"
        raise TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError(
            message
        ) from error


def _validated_authorization_value(
    value: str | None,
    *,
    max_bytes: int,
) -> str:
    if type(value) is not str or not value:
        _raise_provider("resolved authorization must use nonempty exact text")
    _validate_authorization_text_shape(value)
    if len(value.encode("ascii")) > max_bytes:
        _raise_provider("resolved authorization exceeds configured byte limit")
    return value


def _validate_authorization_text_shape(value: str) -> None:
    if not value.isascii():
        _raise_provider("resolved authorization must use ASCII text")
    if value != value.strip(" "):
        _raise_provider("resolved authorization cannot have edge spaces")
    if any(
        not _authorization_character_is_valid(character) for character in value
    ):
        _raise_provider(
            "resolved authorization contains unsupported characters"
        )


def _authorization_character_is_valid(character: str) -> bool:
    codepoint = ord(character)
    return codepoint == _ASCII_SPACE or (
        _ASCII_VISIBLE_MIN <= codepoint <= _ASCII_VISIBLE_MAX
    )


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_provider(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_provider(f"{field_name} exceeds configured length")
    return value


def _validated_byte_limit(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_provider("authorization byte limit must be a positive integer")
    if value > MAX_HTTPS_AUTHORIZATION_BYTES:
        _raise_provider("authorization byte limit exceeds supported maximum")
    return value


def _raise_provider(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage HTTPS authorization provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError(
        message
    )
