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
#   - Explicit synchronous public-key provider for signature trust manifests.
# - Must-Not:
#   - Discover, retry, cache, persist, log key bytes, spawn workers, select
#     algorithms, validate certificates, or change policy.
# - Allows:
#   - Inputs: one manifest, provider identity, and caller-supplied port.
#   - Outputs: immutable requests and manifest-bound signature trust.
#   - Side effects: exactly one explicit provider call per manifest entry.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this live public-key provider boundary.
# - Summary:
#   - Explicit one-pass detached-lineage public-key provider port.
# - Description:
#   - Resolves canonical references without discovery or retained caches.
# - Usage:
#   - Pass one provider explicitly, resolve once, then verify signatures.
# - Defaults:
#   - At most 256 requests; empty manifests make no provider calls.
#

"""Explicit one-pass public-key provider for detached lineage trust."""

# ruff: file-ignore[line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as m,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
        TicketAdmissionTelemetryLineageSignatureTrust,
    )

TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_ID: Final = (
    "explicit-ticket-admission-telemetry-lineage-public-key-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS: Final = (
    m.DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineagePublicKeyProviderError(ValueError):
    """An explicit public-key provider request or result is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyRequest:
    """One immutable manifest-bound request for exact public-key bytes."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    manifest_fingerprint: str
    provider_id: str
    public_key_fingerprint: str
    public_key_id: str
    public_key_reference_id: str
    request_index: int


class TicketAdmissionTelemetryLineagePublicKeyResultKind(StrEnum):
    """Stable provider outcome without exception or vendor text."""

    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyResult:
    """Typed provider outcome with hidden optional public-key bytes."""

    kind: TicketAdmissionTelemetryLineagePublicKeyResultKind
    public_key: bytes | None = field(default=None, repr=False)


class TicketAdmissionTelemetryLineagePublicKeyProvider(Protocol):
    """Synchronous caller-supplied resolver without a lifecycle contract."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyResult:
        """Return one typed result for an exact immutable request."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    """Manifest-bound trust and non-key provider request metadata."""

    algorithm_ids: tuple[str, ...]
    manifest_fingerprint: str
    provider_id: str
    public_key_fingerprints: tuple[str, ...]
    public_key_ids: tuple[str, ...]
    public_key_reference_ids: tuple[str, ...]
    request_count: int
    trust: TicketAdmissionTelemetryLineageSignatureTrust


def ticket_admission_telemetry_lineage_public_key_provider_id() -> str:
    """Return the stable explicit public-key provider port identity.

    Returns:
        Versioned provider-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_ID


def resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    provider: TicketAdmissionTelemetryLineagePublicKeyProvider,
    *,
    provider_id: str,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS
    ),
) -> TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    """Resolve one signature manifest through an explicit provider.

    Returns:
        Manifest-bound caller-owned signature trust and request metadata.

    Raises:
        TicketAdmissionTelemetryLineagePublicKeyProviderError: Validation,
            provider execution, or trust construction fails.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "provider identity",
    )
    request_limit = _validated_positive_limit(max_requests, "request limit")
    try:
        manifest_id = _manifest_fingerprint(manifest)
    except (
        m.TicketAdmissionTelemetryLineageSignatureTrustManifestError
    ) as error:
        message = f"invalid signature trust manifest: {error}"
        raise TicketAdmissionTelemetryLineagePublicKeyProviderError(
            message
        ) from error
    if len(manifest.entries) > request_limit:
        _raise_provider("manifest request count exceeds configured limit")
    requests = _requests(
        manifest,
        manifest_fingerprint=manifest_id,
        provider_id=validated_provider_id,
    )
    resolved = tuple(
        _resolve_request(provider, request) for request in requests
    )
    try:
        resolved_trust = _resolve_manifest(manifest, resolved)
    except (
        m.TicketAdmissionTelemetryLineageSignatureTrustManifestError
    ) as error:
        message = f"cannot build provider-resolved signature trust: {error}"
        raise TicketAdmissionTelemetryLineagePublicKeyProviderError(
            message
        ) from error
    return TicketAdmissionTelemetryLineagePublicKeyProviderTrust(
        algorithm_ids=tuple(request.algorithm_id for request in requests),
        manifest_fingerprint=resolved_trust.manifest_fingerprint,
        provider_id=validated_provider_id,
        public_key_fingerprints=tuple(
            request.public_key_fingerprint for request in requests
        ),
        public_key_ids=tuple(request.public_key_id for request in requests),
        public_key_reference_ids=tuple(
            request.public_key_reference_id for request in requests
        ),
        request_count=len(requests),
        trust=resolved_trust.trust,
    )


def _manifest_fingerprint(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> str:
    # jig-ignore-next-line: indivisible reviewed identifier
    return m.ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
        manifest
    )


def _resolve_manifest(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    public_keys: tuple[
        m.TicketAdmissionTelemetryLineageResolvedPublicKey,
        ...,
    ],
) -> m.TicketAdmissionTelemetryLineageResolvedSignatureTrust:
    return (
        m.resolve_ticket_admission_telemetry_lineage_signature_trust_manifest(
            manifest,
            public_keys,
        )
    )


def _requests(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    *,
    manifest_fingerprint: str,
    provider_id: str,
) -> tuple[TicketAdmissionTelemetryLineagePublicKeyRequest, ...]:
    return tuple(
        TicketAdmissionTelemetryLineagePublicKeyRequest(
            algorithm_id=entry.algorithm_id,
            first_capture_sequence_id=entry.first_capture_sequence_id,
            last_capture_sequence_id=entry.last_capture_sequence_id,
            manifest_fingerprint=manifest_fingerprint,
            provider_id=provider_id,
            public_key_fingerprint=entry.public_key_fingerprint,
            public_key_id=entry.public_key_id,
            public_key_reference_id=entry.public_key_reference_id,
            request_index=index,
        )
        for index, entry in enumerate(manifest.entries)
    )


def _resolve_request(
    provider: TicketAdmissionTelemetryLineagePublicKeyProvider,
    request: TicketAdmissionTelemetryLineagePublicKeyRequest,
) -> m.TicketAdmissionTelemetryLineageResolvedPublicKey:
    result = provider(request)
    validated = _validated_result(result)
    resolved_kind = TicketAdmissionTelemetryLineagePublicKeyResultKind.RESOLVED
    if validated.kind is not resolved_kind:
        detail = (
            f"provider returned {validated.kind.value} at request index "
            f"{request.request_index}"
        )
        _raise_provider(detail)
    if type(validated.public_key) is not bytes:
        _raise_provider(
            "resolved provider result must use exact public-key bytes"
        )
    return m.TicketAdmissionTelemetryLineageResolvedPublicKey(
        algorithm_id=request.algorithm_id,
        public_key=validated.public_key,
        public_key_id=request.public_key_id,
        public_key_reference_id=request.public_key_reference_id,
    )


def _validated_result(
    result: TicketAdmissionTelemetryLineagePublicKeyResult,
) -> TicketAdmissionTelemetryLineagePublicKeyResult:
    if type(result) is not TicketAdmissionTelemetryLineagePublicKeyResult:
        _raise_provider("result must use the exact provider result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineagePublicKeyResultKind
    ):
        _raise_provider("result kind must use the exact provider result enum")
    resolved_kind = TicketAdmissionTelemetryLineagePublicKeyResultKind.RESOLVED
    if result.kind is not resolved_kind and result.public_key is not None:
        _raise_provider(
            "nonresolved provider result cannot contain public-key bytes"
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
    message = f"ticket admission telemetry lineage public-key provider {detail}"
    raise TicketAdmissionTelemetryLineagePublicKeyProviderError(message)
