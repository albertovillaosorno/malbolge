# File:
#   - ticket_admission_telemetry_lineage_async_public_key_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
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
#   - Explicit sequential async public-key resolution for signature trust.
# - Must-Not:
#   - Create event loops, spawn tasks, parallelize, discover, retry, cache,
#     persist, log key bytes, validate certificates, or change policy.
# - Allows:
#   - Inputs: one manifest, provider identity, and caller-supplied async port.
#   - Outputs: manifest-bound caller-owned signature trust.
#   - Side effects: one ordered awaited provider call per manifest entry.
# - Split-When:
#   - Split when memory batch/session adapters, external services, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact async provider boundary.
# - Summary:
#   - Caller-driven sequential async detached-key provider port.
# - Description:
#   - Awaits canonical requests without hidden scheduling or retained state.
# - Usage:
#   - Await from a caller-owned event loop, then verify signatures explicitly.
# - Defaults:
#   - At most 256 requests; empty manifests make no provider calls.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Sequential caller-driven async public-key provider for lineage trust."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

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

TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_PROVIDER_ID: Final = (
    "explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_PROVIDER_REQUESTS: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError(ValueError):
    """An explicit async public-key resolution is invalid or unsuccessful."""


class TicketAdmissionTelemetryLineageAsyncPublicKeyProvider(Protocol):
    """Caller-supplied async resolver without scheduling or lifecycle policy."""

    async def __call__(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyResult:
        """Return one typed result for an exact immutable request."""
        ...


def ticket_admission_telemetry_lineage_async_public_key_provider_id() -> str:
    """Return the stable explicit async provider-port identity.

    Returns:
        Versioned async provider-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_PROVIDER_ID


async def resolve_ticket_admission_telemetry_lineage_signature_trust_async(
    manifest: m.TicketAdmissionTelemetryLineageSignatureTrustManifest,
    provider: TicketAdmissionTelemetryLineageAsyncPublicKeyProvider,
    *,
    provider_id: str,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_PROVIDER_REQUESTS
    ),
) -> TicketAdmissionTelemetryLineagePublicKeyProviderTrust:
    """Resolve one signature manifest with ordered caller-driven awaits.

    Returns:
        Manifest-bound signature trust and non-key request metadata.

    Raises:
        TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError: Preflight,
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
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError(
            message
        ) from error
    if len(manifest.entries) > request_limit:
        _raise_provider("manifest request count exceeds configured limit")
    requests = _requests(
        manifest,
        manifest_fingerprint=manifest_id,
        provider_id=validated_provider_id,
    )
    resolved = [
        await _resolve_request(provider, request) for request in requests
    ]
    try:
        resolved_trust = _resolve_manifest(manifest, tuple(resolved))
    except (
        m.TicketAdmissionTelemetryLineageSignatureTrustManifestError
    ) as error:
        message = (
            f"cannot build async-provider-resolved signature trust: {error}"
        )
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError(
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


async def _resolve_request(
    provider: TicketAdmissionTelemetryLineageAsyncPublicKeyProvider,
    request: TicketAdmissionTelemetryLineagePublicKeyRequest,
) -> m.TicketAdmissionTelemetryLineageResolvedPublicKey:
    try:
        result = await provider(request)
    except Exception as error:
        message = (
            f"provider raised during request index {request.request_index}"
        )
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError(
            message
        ) from error
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
    message = (
        f"ticket admission telemetry lineage async public-key provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError(message)
