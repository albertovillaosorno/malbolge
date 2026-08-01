# File:
#   - ticket_admission_environment_async_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_environment_async_https_auth_provider.py
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
#   - Caller-offloaded async adaptation of one exact environment Authorization
#     provider.
# - Must-Not:
#   - Create event loops, tasks, threads, executors, enumerate or mutate the
#     environment, discover names, retry, cache, persist, log names or values,
#     refresh credentials, inject headers, or change policy.
# - Allows:
#   - Inputs: one exact environment provider, one caller offloader, and exact
#     nonsecret Authorization requests.
#   - Outputs: the shared typed resolved, unavailable, or failed result.
#   - Side effects: exactly one caller-supplied offloader await per matched
#     provider-identity call.
# - Split-When:
#   - Split when native async environment access, external stores, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact caller-offloaded environment
#     boundary.
# - Summary:
#   - Caller-offloaded async adapter for explicit environment Authorization.
# - Description:
#   - Reuses exact environment-provider validation without owning scheduling.
# - Usage:
#   - Build with one environment provider and a caller-selected async offloader.
# - Defaults:
#   - No default offloader; caller owns all environment-read placement.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
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

"""Caller-offloaded async adapter for environment HTTPS Authorization."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_environment_https_auth_provider as environment,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)

_ADAPTER_ID_PREFIX: Final = (
    "offloaded-async-environment-ticket-admission-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_ASYNC_HTTPS_AUTH_PROVIDER_ID: Final = f"{_ADAPTER_ID_PREFIX}https-authorization-provider-v1"
_validate_environment_provider: Final = (  # fmt: skip
    environment.validate_ticket_admission_environment_https_authorization_provider
)
_validate_request: Final = (
    auth.validate_ticket_admission_https_authorization_request
)
_validate_result: Final = (
    auth.validate_ticket_admission_https_authorization_result
)
_materialize: Final = auth.materialize_ticket_admission_https_authorization
_FAILED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.FAILED
)
_RESOLVED: Final = (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind.RESOLVED
)


class TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
    ValueError
):
    """A caller-offloaded async environment Authorization adapter is invalid."""


class TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader(Protocol):
    """Caller-owned placement of one synchronous environment-provider call."""

    async def __call__(
        self,
        provider: environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Run one exact synchronous provider call under caller scheduling."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider:
    """Immutable async adapter with hidden environment provider and offloader."""

    adapter_id: str
    entry_count: int
    max_authorization_bytes: int
    max_entries: int
    offloader: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader = (
        field(repr=False)
    )
    provider: environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider = field(
        repr=False
    )
    provider_id: str

    async def __call__(
        self,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Await one caller-owned offload without hidden scheduling resources.

        Returns:
            Shared typed resolved, unavailable, or failed result.

        Cancellation propagates directly to the caller.

        """
        adapter = _validated_adapter(self)
        validated_request = _validated_shared_request(request)
        if validated_request.authorization_provider_id != adapter.provider_id:
            return _failed_result()
        result = await _await_offloader(adapter, validated_request)
        return _validated_shared_result(
            result,
            request=validated_request,
            max_authorization_bytes=adapter.max_authorization_bytes,
        )


def ticket_admission_environment_async_https_authorization_provider_id() -> str:
    """Return the stable caller-offloaded environment adapter identity.

    Returns:
        Versioned async environment Authorization adapter identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_ASYNC_HTTPS_AUTH_PROVIDER_ID


def build_ticket_admission_environment_async_https_authorization_provider(
    provider: environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
    offloader: TicketAdmissionTelemetryLineageEnvironmentHttpsAuthOffloader,
) -> TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider:
    """Build one caller-offloaded adapter over exact environment state.

    Returns:
        Validated immutable async adapter with hidden provider and offloader.

    """
    validated = _validated_environment_provider(provider)
    _validate_offloader(offloader)
    return TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_ASYNC_HTTPS_AUTH_PROVIDER_ID
        ),
        entry_count=len(validated.entries),
        max_authorization_bytes=validated.max_authorization_bytes,
        max_entries=validated.max_entries,
        offloader=offloader,
        provider=validated,
        provider_id=validated.provider_id,
    )


def validate_ticket_admission_environment_async_https_authorization_provider(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider:
    """Validate one exact immutable caller-offloaded environment adapter.

    Returns:
        The same exact adapter after complete binding validation.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_environment_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    _validate_offloader(adapter.offloader)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> None:
    _validate_adapter_identity(adapter)
    _validate_adapter_limits(adapter)
    _validate_adapter_metadata(adapter)


def _validate_adapter_identity(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider
    ):
        _raise_adapter("adapter must use the exact environment-async auth type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_ENVIRONMENT_ASYNC_HTTPS_AUTH_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")


def _validate_adapter_limits(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> None:
    if type(adapter.max_entries) is not int or adapter.max_entries <= 0:
        _raise_adapter("adapter entry limit must be a positive integer")
    if (
        type(adapter.max_authorization_bytes) is not int
        or adapter.max_authorization_bytes <= 0
    ):
        _raise_adapter(
            "adapter Authorization byte limit must be a positive integer"
        )


def _validate_adapter_metadata(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
) -> None:
    if type(adapter.entry_count) is not int or adapter.entry_count < 0:
        _raise_adapter("adapter entry count must be a nonnegative integer")
    if type(adapter.provider_id) is not str or not adapter.provider_id:
        _raise_adapter("adapter provider identity must be a nonempty string")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
    validated: environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
) -> None:
    if adapter.entry_count != len(validated.entries):
        _raise_adapter("adapter entry count does not match provider")
    if adapter.max_entries != validated.max_entries:
        _raise_adapter("adapter entry limit does not match provider")
    if adapter.max_authorization_bytes != validated.max_authorization_bytes:
        _raise_adapter(
            "adapter Authorization byte limit does not match provider"
        )
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")


def _validated_environment_provider(
    value: environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider,
) -> environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProvider:
    try:
        return _validate_environment_provider(value)
    except environment.TicketAdmissionTelemetryLineageEnvironmentHttpsAuthProviderError as error:
        message = "invalid synchronous environment Authorization provider"
        raise TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
            message
        ) from error


def _validate_offloader(value: object) -> None:
    if not callable(value):
        _raise_adapter("offloader must be callable")


def _validated_shared_request(
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest:
    try:
        return _validate_request(request)
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "invalid caller-offloaded environment Authorization request"
        raise TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
            message
        ) from error


async def _await_offloader(
    adapter: TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProvider,
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    try:
        return await adapter.offloader(adapter.provider, request)
    except CancelledError:
        raise
    except Exception as error:
        message = (
            "caller environment Authorization offloader raised during "
            "explicit read"
        )
        raise TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
            message
        ) from error


def _validated_shared_result(
    result: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult,
    *,
    request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    max_authorization_bytes: int,
) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
    try:
        validated = _validate_result(result)
        if validated.kind is _RESOLVED:
            prepared = (
                auth.TicketAdmissionTelemetryLineagePreparedHttpsAuthorization(
                    max_authorization_bytes=max_authorization_bytes,
                    request=request,
                )
            )
            _ = _materialize(prepared, validated)
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = (
            "caller environment Authorization offloader returned an invalid "
            "result"
        )
        raise TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
            message
        ) from error
    return validated


def _failed_result() -> (
    auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
):
    return auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult(
        kind=_FAILED
    )


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage environment async HTTPS "
        f"Authorization provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageEnvironmentAsyncHttpsAuthProviderError(
        message
    )
