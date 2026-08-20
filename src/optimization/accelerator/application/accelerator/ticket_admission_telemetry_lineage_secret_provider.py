# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Explicit synchronous secret-provider port for lineage trust manifests.
# - Must-Not:
#   - Discover, retry, cache, persist, log secrets, spawn workers, or
#     change policy.
# - Allows:
#   - Inputs: one validated manifest, provider identity, and caller-supplied
#     port.
#   - Outputs: immutable requests and manifest-bound caller-owned trust.
#   - Side effects: exactly one explicit provider call per manifest entry.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact live secret-provider boundary.
# - Summary:
#   - Explicit one-pass telemetry lineage secret-provider port.
# - Description:
#   - Resolves canonical manifest references without discovery or retained
#     caches.
# - Usage:
#   - Pass one provider explicitly, resolve once, then authenticate
#     attestations.
# - Defaults:
#   - At most 256 requests; empty manifests make no provider calls.
#

"""Explicit one-pass secret-provider port for telemetry lineage trust."""

# ruff: file-ignore[hardcoded-password-string]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_trust import (
        TicketAdmissionTelemetryLineageTrust,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )

from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageResolvedSecret,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestError,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    resolve_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_fingerprint,
)

_SECRET_PROVIDER_ID_PREFIX: Final = (
    "explicit-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_SECRET_PROVIDER_ID: Final = (
    f"{_SECRET_PROVIDER_ID_PREFIX}secret-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES
)
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_MANIFEST_FINGERPRINT_PATTERN: Final = compile_pattern(
    TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX
    + r"[0-9a-f]{64}"
)


class TicketAdmissionTelemetryLineageSecretProviderError(ValueError):
    """An explicit lineage secret-provider request or result is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSecretRequest:
    """One immutable manifest-bound request for secret bytes."""

    first_capture_sequence_id: int
    key_id: str
    key_reference_id: str
    last_capture_sequence_id: int | None
    manifest_fingerprint: str
    provider_id: str
    request_index: int


class TicketAdmissionTelemetryLineageSecretResultKind(StrEnum):
    """Stable provider outcome without exception or vendor text."""

    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSecretResult:
    """Typed provider outcome with hidden optional secret bytes."""

    kind: TicketAdmissionTelemetryLineageSecretResultKind
    secret_key: bytes | None = field(default=None, repr=False)


class TicketAdmissionTelemetryLineageSecretProvider(Protocol):
    """Synchronous caller-supplied resolver without a lifecycle contract."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> TicketAdmissionTelemetryLineageSecretResult:
        """Return one typed result for an exact immutable request."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageProviderTrust:
    """Manifest-bound trust and nonsecret provider request metadata."""

    key_ids: tuple[str, ...]
    key_reference_ids: tuple[str, ...]
    manifest_fingerprint: str
    provider_id: str
    request_count: int
    trust: TicketAdmissionTelemetryLineageTrust


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePreparedSecretProvider:
    """Validated nonsecret preflight for one ordered provider walk."""

    manifest: TicketAdmissionTelemetryLineageTrustManifest
    manifest_fingerprint: str
    max_requests: int
    provider_id: str
    requests: tuple[TicketAdmissionTelemetryLineageSecretRequest, ...]


def ticket_admission_telemetry_lineage_secret_provider_id() -> str:
    """Return the stable explicit secret-provider port identity.

    Returns:
        Versioned provider-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_SECRET_PROVIDER_ID


def resolve_ticket_admission_telemetry_lineage_trust_with_provider(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    provider: TicketAdmissionTelemetryLineageSecretProvider,
    *,
    provider_id: str,
    max_requests: int = DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS,
) -> TicketAdmissionTelemetryLineageProviderTrust:
    """Resolve one manifest through an explicit synchronous provider port.

    Returns:
        Manifest-bound caller-owned trust and nonsecret request metadata.

    """
    prepared = prepare_ticket_admission_telemetry_lineage_secret_provider(
        manifest,
        provider_id=provider_id,
        max_requests=max_requests,
    )
    resolved = tuple(
        materialize_ticket_admission_telemetry_lineage_secret_result(
            request,
            provider(request),
        )
        for request in prepared.requests
    )
    return materialize_ticket_admission_telemetry_lineage_provider_trust(
        prepared,
        resolved,
    )


def prepare_ticket_admission_telemetry_lineage_secret_provider(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    *,
    provider_id: str,
    max_requests: int = DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS,
) -> TicketAdmissionTelemetryLineagePreparedSecretProvider:
    """Validate one provider-independent manifest resolution preflight.

    Returns:
        Exact manifest, fingerprint, requests, provider identity, and limit.

    Raises:
        TicketAdmissionTelemetryLineageSecretProviderError: Preflight fails.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "provider identity",
    )
    request_limit = _validated_positive_limit(max_requests, "request limit")
    try:
        manifest_fingerprint = (
            ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
                manifest
            )
        )
    except TicketAdmissionTelemetryLineageTrustManifestError as error:
        message = f"invalid trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageSecretProviderError(
            message
        ) from error
    if len(manifest.entries) > request_limit:
        _raise_provider("manifest request count exceeds configured limit")
    requests = _requests(
        manifest,
        manifest_fingerprint=manifest_fingerprint,
        provider_id=validated_provider_id,
    )
    return TicketAdmissionTelemetryLineagePreparedSecretProvider(
        manifest=manifest,
        manifest_fingerprint=manifest_fingerprint,
        max_requests=request_limit,
        provider_id=validated_provider_id,
        requests=requests,
    )


def validate_ticket_admission_prepared_secret_provider(
    prepared: TicketAdmissionTelemetryLineagePreparedSecretProvider,
) -> TicketAdmissionTelemetryLineagePreparedSecretProvider:
    """Validate one exact provider-independent secret resolution preflight.

    Returns:
        The same exact prepared value after complete validation.

    """
    if (
        type(prepared)
        is not TicketAdmissionTelemetryLineagePreparedSecretProvider
    ):
        _raise_provider("prepared value must use the exact preflight type")
    expected = prepare_ticket_admission_telemetry_lineage_secret_provider(
        prepared.manifest,
        provider_id=prepared.provider_id,
        max_requests=prepared.max_requests,
    )
    if prepared.manifest_fingerprint != expected.manifest_fingerprint:
        _raise_provider("prepared manifest fingerprint does not match manifest")
    if prepared.requests != expected.requests:
        _raise_provider("prepared requests do not match manifest preflight")
    return prepared


def validate_ticket_admission_telemetry_lineage_secret_request(
    request: TicketAdmissionTelemetryLineageSecretRequest,
) -> TicketAdmissionTelemetryLineageSecretRequest:
    """Validate one exact immutable manifest-bound secret request.

    Returns:
        The same exact request after complete validation.

    """
    if type(request) is not TicketAdmissionTelemetryLineageSecretRequest:
        _raise_provider(
            "request must use the exact secret-provider request type"
        )
    _validate_window(
        request.first_capture_sequence_id,
        request.last_capture_sequence_id,
    )
    _ = _validated_identifier(request.key_id, "request key identity")
    _ = _validated_identifier(
        request.key_reference_id,
        "request key reference identity",
    )
    _ = _validated_manifest_fingerprint(request.manifest_fingerprint)
    _ = _validated_identifier(request.provider_id, "request provider identity")
    if type(request.request_index) is not int or request.request_index < 0:
        _raise_provider("request index must be a nonnegative integer")
    return request


def validate_ticket_admission_telemetry_lineage_secret_result(
    result: TicketAdmissionTelemetryLineageSecretResult,
) -> TicketAdmissionTelemetryLineageSecretResult:
    """Validate one exact typed secret-provider result.

    Returns:
        The same exact result after type and kind validation.

    """
    if type(result) is not TicketAdmissionTelemetryLineageSecretResult:
        _raise_provider("result must use the exact provider result type")
    if type(result.kind) is not TicketAdmissionTelemetryLineageSecretResultKind:
        _raise_provider("result kind must use the exact provider result enum")
    resolved_kind = TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED
    if result.kind is not resolved_kind and result.secret_key is not None:
        _raise_provider(
            "nonresolved provider result cannot contain secret bytes"
        )
    return result


def materialize_ticket_admission_telemetry_lineage_secret_result(
    request: TicketAdmissionTelemetryLineageSecretRequest,
    result: TicketAdmissionTelemetryLineageSecretResult,
) -> TicketAdmissionTelemetryLineageResolvedSecret:
    """Validate one provider result and bind exact hidden bytes to its request.

    Returns:
        Exact caller-owned resolved secret for manifest materialization.

    """
    validated_request = (
        validate_ticket_admission_telemetry_lineage_secret_request(request)
    )
    validated_result = (
        validate_ticket_admission_telemetry_lineage_secret_result(result)
    )
    resolved_kind = TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED
    if validated_result.kind is not resolved_kind:
        detail = (
            f"provider returned {validated_result.kind.value} at request index "
            f"{validated_request.request_index}"
        )
        _raise_provider(detail)
    if type(validated_result.secret_key) is not bytes:
        _raise_provider("resolved provider result must use exact secret bytes")
    return TicketAdmissionTelemetryLineageResolvedSecret(
        key_id=validated_request.key_id,
        key_reference_id=validated_request.key_reference_id,
        secret_key=validated_result.secret_key,
    )


def materialize_ticket_admission_telemetry_lineage_provider_trust(
    prepared: TicketAdmissionTelemetryLineagePreparedSecretProvider,
    resolved: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
) -> TicketAdmissionTelemetryLineageProviderTrust:
    """Build one manifest-bound trust result from exact ordered resolutions.

    Returns:
        Manifest-bound caller-owned trust and nonsecret request metadata.

    Raises:
        TicketAdmissionTelemetryLineageSecretProviderError:
            Materialization fails.

    """
    validated_prepared = validate_ticket_admission_prepared_secret_provider(
        prepared
    )
    if type(resolved) is not tuple:
        _raise_provider("resolved secrets must use the exact immutable tuple")
    if len(resolved) != len(validated_prepared.requests):
        _raise_provider(
            "resolved secret count does not match prepared requests"
        )
    try:
        resolved_trust = (
            resolve_ticket_admission_telemetry_lineage_trust_manifest(
                validated_prepared.manifest,
                resolved,
            )
        )
    except TicketAdmissionTelemetryLineageTrustManifestError as error:
        message = f"cannot build provider-resolved trust: {error}"
        raise TicketAdmissionTelemetryLineageSecretProviderError(
            message
        ) from error
    requests = validated_prepared.requests
    return TicketAdmissionTelemetryLineageProviderTrust(
        key_ids=tuple(request.key_id for request in requests),
        key_reference_ids=tuple(
            request.key_reference_id for request in requests
        ),
        manifest_fingerprint=resolved_trust.manifest_fingerprint,
        provider_id=validated_prepared.provider_id,
        request_count=len(requests),
        trust=resolved_trust.trust,
    )


def _requests(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    *,
    manifest_fingerprint: str,
    provider_id: str,
) -> tuple[TicketAdmissionTelemetryLineageSecretRequest, ...]:
    return tuple(
        TicketAdmissionTelemetryLineageSecretRequest(
            first_capture_sequence_id=entry.first_capture_sequence_id,
            key_id=entry.key_id,
            key_reference_id=entry.key_reference_id,
            last_capture_sequence_id=entry.last_capture_sequence_id,
            manifest_fingerprint=manifest_fingerprint,
            provider_id=provider_id,
            request_index=index,
        )
        for index, entry in enumerate(manifest.entries)
    )


def _validated_manifest_fingerprint(value: str) -> str:
    if (
        type(value) is not str
        or _MANIFEST_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_provider("manifest fingerprint must use canonical SHA-256 form")
    return value


def _validate_window(first: int, last: int | None) -> None:
    if type(first) is not int or first < 0:
        _raise_provider("first capture sequence identity must be nonnegative")
    if last is None:
        return
    if type(last) is not int or last < 0:
        _raise_provider("last capture sequence identity must be nonnegative")
    if last < first:
        _raise_provider("last capture sequence precedes first capture sequence")


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_provider(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_provider(f"{field_name} exceeds configured length")
    return value


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_provider(f"{field_name} must be a positive integer")
    return value


def _raise_provider(detail: str) -> Never:
    message = f"ticket admission telemetry lineage secret provider {detail}"
    raise TicketAdmissionTelemetryLineageSecretProviderError(message)
