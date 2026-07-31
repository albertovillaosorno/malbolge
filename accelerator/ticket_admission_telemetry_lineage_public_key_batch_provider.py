# File:
#   - ticket_admission_telemetry_lineage_public_key_batch_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
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
#   - Explicit caller-controlled async batch public-key resolution.
# - Must-Not:
#   - Create event loops or tasks, choose concurrency, discover, retry, cache,
#     persist, log key bytes, validate certificates, or change policy.
# - Allows:
#   - Inputs: one manifest, provider identity, and caller-supplied batch port.
#   - Outputs: one canonical batch request and manifest-bound signature trust.
#   - Side effects: at most one awaited batch-provider call per resolution.
# - Split-When:
#   - Split when built-in services, certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact async batch boundary.
# - Summary:
#   - Explicit async batch detached-key provider port.
# - Description:
#   - Delegates all scheduling and concurrency decisions to the caller port.
# - Usage:
#   - Await one caller-owned batch provider, then verify signatures explicitly.
# - Defaults:
#   - At most 256 requests; empty manifests make no provider calls.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-controlled async batch public-key provider for lineage trust."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as m,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyProviderTrust,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyRequest,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResult,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResultKind,
)

_BATCH_PROVIDER_ID_PREFIX: Final = "explicit-async-batch-ticket-admission-"
_BATCH_PROVIDER_ID_SUFFIX: Final = "telemetry-lineage-public-key-provider-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_ID: Final = (
    f"{_BATCH_PROVIDER_ID_PREFIX}{_BATCH_PROVIDER_ID_SUFFIX}"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_REQUESTS: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineagePublicKeyBatchProviderError(ValueError):
    """An explicit async batch resolution is invalid or unsuccessful."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBatchRequest:
    """One immutable canonical batch supplied to a caller-owned provider."""

    manifest_fingerprint: str
    provider_id: str
    requests: tuple[TicketAdmissionTelemetryLineagePublicKeyRequest, ...]


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBatchResult:
    """One exact positional result tuple with hidden public-key material."""

    results: tuple[TicketAdmissionTelemetryLineagePublicKeyResult, ...] = field(
        repr=False
    )


class TicketAdmissionTelemetryLineagePublicKeyBatchProvider(Protocol):
    """Caller-supplied async batch resolver with caller-owned concurrency."""

    async def __call__(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyBatchResult:
        """Resolve one complete canonical batch."""
        ...


def ticket_admission_telemetry_lineage_public_key_batch_provider_id() -> str:
    """Return the stable explicit async batch-provider identity.

    Returns:
        Versioned batch-provider port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_ID


async def resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    provider: TicketAdmissionTelemetryLineagePublicKeyBatchProvider,
    *,
    provider_id: str,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_REQUESTS
    ),
) -> TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    """Resolve one manifest through one caller-controlled async batch call.

    Returns:
        Manifest-bound signature trust and non-key request metadata.

    Raises:
        TicketAdmissionTelemetryLineagePublicKeyBatchProviderError: Preflight,
            provider execution, result validation, or trust construction fails.

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
        raise TicketAdmissionTelemetryLineagePublicKeyBatchProviderError(
            message
        ) from error
    if len(manifest.entries) > request_limit:
        _raise_provider("manifest request count exceeds configured limit")
    requests = _requests(
        manifest,
        manifest_fingerprint=manifest_id,
        provider_id=validated_provider_id,
    )
    if requests:
        batch = TicketAdmissionTelemetryLineagePublicKeyBatchRequest(
            manifest_fingerprint=manifest_id,
            provider_id=validated_provider_id,
            requests=requests,
        )
        results = await _resolve_batch(provider, batch)
    else:
        results = ()
    resolved = tuple(map(_resolved_public_key, requests, results, strict=True))
    try:
        resolved_trust = _resolve_manifest(manifest, resolved)
    except (
        m.TicketAdmissionTelemetryLineageSignatureTrustManifestError
    ) as error:
        message = (
            f"cannot build batch-provider-resolved signature trust: {error}"
        )
        raise TicketAdmissionTelemetryLineagePublicKeyBatchProviderError(
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


async def _resolve_batch(
    provider: TicketAdmissionTelemetryLineagePublicKeyBatchProvider,
    request: TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
) -> tuple[TicketAdmissionTelemetryLineagePublicKeyResult, ...]:
    try:
        result = await provider(request)
    except Exception as error:
        message = "batch provider raised during resolution"
        raise TicketAdmissionTelemetryLineagePublicKeyBatchProviderError(
            message
        ) from error
    if type(result) is not TicketAdmissionTelemetryLineagePublicKeyBatchResult:
        _raise_provider("result must use the exact batch result type")
    if type(result.results) is not tuple:
        _raise_provider("batch results must use the exact tuple type")
    if len(result.results) != len(request.requests):
        _raise_provider("batch result count does not match request count")
    return result.results


def _resolved_public_key(
    request: TicketAdmissionTelemetryLineagePublicKeyRequest,
    result: TicketAdmissionTelemetryLineagePublicKeyResult,
) -> m.TicketAdmissionTelemetryLineageResolvedPublicKey:
    validated = _validated_result(result, request_index=request.request_index)
    if type(validated.public_key) is not bytes:
        detail = f"resolved result needs exact bytes at index {request.request_index}"
        _raise_provider(detail)
    return m.TicketAdmissionTelemetryLineageResolvedPublicKey(
        algorithm_id=request.algorithm_id,
        public_key=validated.public_key,
        public_key_id=request.public_key_id,
        public_key_reference_id=request.public_key_reference_id,
    )


def _validated_result(
    result: TicketAdmissionTelemetryLineagePublicKeyResult,
    *,
    request_index: int,
) -> TicketAdmissionTelemetryLineagePublicKeyResult:
    if type(result) is not TicketAdmissionTelemetryLineagePublicKeyResult:
        detail = f"result at index {request_index} must use the exact type"
        _raise_provider(detail)
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineagePublicKeyResultKind
    ):
        detail = f"result kind at index {request_index} must use the exact enum"
        _raise_provider(detail)
    resolved_kind = TicketAdmissionTelemetryLineagePublicKeyResultKind.RESOLVED
    if result.kind is not resolved_kind:
        if result.public_key is not None:
            detail = f"nonresolved result has bytes at index {request_index}"
            _raise_provider(detail)
        detail = (
            f"provider returned {result.kind.value} at index {request_index}"
        )
        _raise_provider(detail)
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
    message = (
        f"ticket admission telemetry lineage public-key batch provider {detail}"
    )
    raise TicketAdmissionTelemetryLineagePublicKeyBatchProviderError(message)
