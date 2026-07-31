# File:
#   - ticket_admission_telemetry_lineage_secret_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
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
#   - Split when asynchronous providers or provider lifecycles gain contracts.
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
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_migration.py
# - accelerator/ticket_admission_telemetry_store.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit one-pass secret-provider port for telemetry lineage trust."""

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

TICKET_ADMISSION_TELEMETRY_LINEAGE_SECRET_PROVIDER_ID: Final = (
    "explicit-ticket-admission-telemetry-lineage-secret-provider-v1"  # ruff: ignore[hardcoded-password-string]
)
DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
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

    Raises:
        TicketAdmissionTelemetryLineageSecretProviderError: Validation,
            provider execution, or trust construction fails.

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
    resolved = tuple(
        _resolve_request(provider, request) for request in requests
    )
    try:
        resolved_trust = (
            resolve_ticket_admission_telemetry_lineage_trust_manifest(
                manifest,
                resolved,
            )
        )
    except TicketAdmissionTelemetryLineageTrustManifestError as error:
        message = f"cannot build provider-resolved trust: {error}"
        raise TicketAdmissionTelemetryLineageSecretProviderError(
            message
        ) from error
    return TicketAdmissionTelemetryLineageProviderTrust(
        key_ids=tuple(request.key_id for request in requests),
        key_reference_ids=tuple(
            request.key_reference_id for request in requests
        ),
        manifest_fingerprint=resolved_trust.manifest_fingerprint,
        provider_id=validated_provider_id,
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


def _resolve_request(
    provider: TicketAdmissionTelemetryLineageSecretProvider,
    request: TicketAdmissionTelemetryLineageSecretRequest,
) -> TicketAdmissionTelemetryLineageResolvedSecret:
    result = provider(request)
    validated = _validated_result(result)
    resolved_kind = TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED
    if validated.kind is not resolved_kind:
        detail = (
            f"provider returned {validated.kind.value} at request index "
            f"{request.request_index}"
        )
        _raise_provider(detail)
    if type(validated.secret_key) is not bytes:
        _raise_provider("resolved provider result must use exact secret bytes")
    return TicketAdmissionTelemetryLineageResolvedSecret(
        key_id=request.key_id,
        key_reference_id=request.key_reference_id,
        secret_key=validated.secret_key,
    )


def _validated_result(
    result: TicketAdmissionTelemetryLineageSecretResult,
) -> TicketAdmissionTelemetryLineageSecretResult:
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
