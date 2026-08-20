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
#   - Explicit sequential async secret resolution for lineage trust manifests.
# - Must-Not:
#   - Create event loops, spawn tasks, parallelize, discover, retry, cache,
#     persist, log secret bytes, read external stores, or change policy.
# - Allows:
#   - Inputs: one manifest, provider identity, and caller-supplied async port.
#   - Outputs: manifest-bound caller-owned HMAC trust.
#   - Side effects: one ordered awaited provider call per manifest entry.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact async secret-provider boundary.
# - Summary:
#   - Caller-driven sequential async HMAC-secret provider port.
# - Description:
#   - Reuses synchronous preflight and materialization without hidden
#     scheduling.
# - Usage:
#   - Await from a caller-owned event loop, then authenticate lineage
#     explicitly.
# - Defaults:
#   - At most 256 requests; empty manifests make no provider calls.
#

"""Sequential caller-driven async secret provider for lineage trust."""

# ruff: file-ignore[hardcoded-password-string]

from __future__ import annotations

from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as sync,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_trust_manifest as manifest,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )

_ASYNC_SECRET_PROVIDER_ID_PREFIX: Final = (
    "explicit-async-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_SECRET_PROVIDER_ID: Final = (
    f"{_ASYNC_SECRET_PROVIDER_ID_PREFIX}secret-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_ASYNC_SECRET_PROVIDER_REQUESTS: Final = (
    sync.DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS
)


class TicketAdmissionTelemetryLineageAsyncSecretProviderError(ValueError):
    """An explicit async secret resolution is invalid or unsuccessful."""


class TicketAdmissionTelemetryLineageAsyncSecretProvider(Protocol):
    """Caller-supplied async resolver without scheduling or lifecycle policy."""

    async def __call__(
        self,
        request: sync.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> sync.TicketAdmissionTelemetryLineageSecretResult:
        """Return one typed result for an exact immutable request."""
        ...


def ticket_admission_telemetry_lineage_async_secret_provider_id() -> str:
    """Return the stable explicit async secret-provider port identity.

    Returns:
        Versioned async provider-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_SECRET_PROVIDER_ID


async def resolve_ticket_admission_telemetry_lineage_trust_async(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    provider: TicketAdmissionTelemetryLineageAsyncSecretProvider,
    *,
    provider_id: str,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_ASYNC_SECRET_PROVIDER_REQUESTS
    ),
) -> sync.TicketAdmissionTelemetryLineageProviderTrust:
    """Resolve one HMAC trust manifest with ordered caller-driven awaits.

    Returns:
        Manifest-bound trust and nonsecret provider request metadata.

    """
    prepared = _prepared(
        manifest,
        provider_id=provider_id,
        max_requests=max_requests,
    )
    _validate_provider(provider)
    resolved: list[manifest.TicketAdmissionTelemetryLineageResolvedSecret] = []
    for request in prepared.requests:
        result = await _provider_result(provider, request)
        resolved.append(_materialized_result(request, result))
    return _materialized_trust(prepared, tuple(resolved))


def _prepared(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    *,
    provider_id: str,
    max_requests: int,
) -> sync.TicketAdmissionTelemetryLineagePreparedSecretProvider:
    try:
        return sync.prepare_ticket_admission_telemetry_lineage_secret_provider(
            manifest,
            provider_id=provider_id,
            max_requests=max_requests,
        )
    except sync.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = f"invalid async secret-provider preflight: {error}"
        raise TicketAdmissionTelemetryLineageAsyncSecretProviderError(
            message
        ) from error


def _validate_provider(value: object) -> None:
    if not callable(value):
        _raise_provider("provider must be callable")


async def _provider_result(
    provider: TicketAdmissionTelemetryLineageAsyncSecretProvider,
    request: sync.TicketAdmissionTelemetryLineageSecretRequest,
) -> sync.TicketAdmissionTelemetryLineageSecretResult:
    try:
        return await provider(request)
    except Exception as error:
        message = (
            f"provider raised during request index {request.request_index}"
        )
        raise TicketAdmissionTelemetryLineageAsyncSecretProviderError(
            message
        ) from error


def _materialized_result(
    request: sync.TicketAdmissionTelemetryLineageSecretRequest,
    result: sync.TicketAdmissionTelemetryLineageSecretResult,
) -> manifest.TicketAdmissionTelemetryLineageResolvedSecret:
    try:
        return (
            sync.materialize_ticket_admission_telemetry_lineage_secret_result(
                request,
                result,
            )
        )
    except sync.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = (
            f"invalid async provider result at request index "
            f"{request.request_index}: {error}"
        )
        raise TicketAdmissionTelemetryLineageAsyncSecretProviderError(
            message
        ) from error


def _materialized_trust(
    prepared: sync.TicketAdmissionTelemetryLineagePreparedSecretProvider,
    resolved: tuple[
        manifest.TicketAdmissionTelemetryLineageResolvedSecret,
        ...,
    ],
) -> sync.TicketAdmissionTelemetryLineageProviderTrust:
    try:
        return (
            sync.materialize_ticket_admission_telemetry_lineage_provider_trust(
                prepared,
                resolved,
            )
        )
    except sync.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = f"cannot materialize async secret-provider trust: {error}"
        raise TicketAdmissionTelemetryLineageAsyncSecretProviderError(
            message
        ) from error


def _raise_provider(detail: str) -> Never:
    message = (
        f"ticket admission telemetry lineage async secret provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageAsyncSecretProviderError(message)
