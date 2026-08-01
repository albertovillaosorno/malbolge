# File:
#   - ticket_admission_telemetry_lineage_async_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
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
#   - Explicit one-await provider port for one HTTPS Authorization value.
# - Must-Not:
#   - Create event loops or tasks, select schemes, discover credentials, retry,
#     cache, persist, refresh, log values, inject headers, or change policy.
# - Allows:
#   - Inputs: one exact HTTPS fetcher, request, provider identity, and async port.
#   - Outputs: one hidden caller-owned bounded Authorization value and metadata.
#   - Side effects: exactly one awaited provider call per successful preflight.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact async Authorization boundary.
# - Summary:
#   - Explicit one-await HTTPS Authorization credential-provider port.
# - Description:
#   - Reuses synchronous preflight and materialization without scheduling policy.
# - Usage:
#   - Await from a caller-owned event loop, then inject the value explicitly.
# - Defaults:
#   - Reuses the synchronous 4096-byte default and 16384-byte maximum.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_https_auth_provider.py
# - accelerator/ticket_admission_file_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit one-await HTTPS Authorization credential-provider port."""

# ruff: file-ignore[line-too-long,doc-line-too-long,too-many-arguments]

from __future__ import annotations

from asyncio import CancelledError
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
    )
    from accelerator import (
        ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
    )

TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_AUTHORIZATION_PROVIDER_ID: Final = (
    "explicit-async-ticket-admission-lineage-"
    "https-authorization-provider-v1"
)
_prepare: Final = auth.prepare_ticket_admission_https_authorization
_materialize: Final = auth.materialize_ticket_admission_https_authorization


class TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError(ValueError):
    """An explicit async HTTPS Authorization resolution is invalid."""


class TicketAdmissionTelemetryLineageAsyncHttpsAuthorizationProvider(Protocol):
    """Caller-supplied async credential resolver without scheduling policy."""

    async def __call__(
        self,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Return one typed result for exact immutable nonsecret metadata."""
        ...


def ticket_admission_async_https_authorization_provider_id() -> str:
    """Return the stable explicit async Authorization-provider identity.

    Returns:
        Versioned async Authorization-provider port identity.

    """
    return (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_AUTHORIZATION_PROVIDER_ID
    )


async def resolve_ticket_admission_https_authorization_async(
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    provider: TicketAdmissionTelemetryLineageAsyncHttpsAuthorizationProvider,
    *,
    authorization_provider_id: str,
    max_authorization_bytes: int = auth.DEFAULT_MAX_HTTPS_AUTHORIZATION_BYTES,
) -> auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization:
    """Await one explicit provider and materialize caller-owned authorization.

    Returns:
        Hidden bounded Authorization value and stable request metadata.

    Cancellation propagates directly to the caller.

    """
    prepared = _prepared_authorization(
        fetcher,
        request,
        authorization_provider_id=authorization_provider_id,
        max_authorization_bytes=max_authorization_bytes,
    )
    _validate_provider(provider)
    result = await _await_provider(provider, prepared.request)
    return _materialized_authorization(prepared, result)


def _prepared_authorization(
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    *,
    authorization_provider_id: str,
    max_authorization_bytes: int,
) -> auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization:
    try:
        return _prepare(
            fetcher,
            request,
            authorization_provider_id=authorization_provider_id,
            max_authorization_bytes=max_authorization_bytes,
        )
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "invalid async HTTPS Authorization preflight"
        raise TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError(
            message
        ) from error


def _validate_provider(value: object) -> None:
    if not callable(value):
        _raise_provider("provider must be callable")


async def _await_provider(
    provider: TicketAdmissionTelemetryLineageAsyncHttpsAuthorizationProvider,
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    try:
        return await provider(request)
    except CancelledError:
        raise
    except Exception as error:
        message = (
            "async Authorization provider raised during explicit resolution"
        )
        raise TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError(
            message
        ) from error


def _materialized_authorization(
    prepared: auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization,
    result: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult,
) -> auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization:
    try:
        return _materialize(prepared, result)
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "cannot materialize async HTTPS Authorization result"
        raise TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError(
            message
        ) from error


def _raise_provider(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage async HTTPS Authorization provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageAsyncHttpsAuthProviderError(message)
