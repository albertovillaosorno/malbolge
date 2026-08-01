# File:
#   - ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
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
#   - Caller-offloaded async adapter for one authorized synchronous HTTPS fetcher.
# - Must-Not:
#   - Resolve or refresh credentials, create tasks, threads, executors, retry,
#     redirect, cache, persist, log authorization, or change policy.
# - Allows:
#   - Inputs: one exact authorized HTTPS fetcher, caller offloader, and requests.
#   - Outputs: the shared typed fetched, unavailable, or failed transport result.
#   - Side effects: exactly one caller-supplied offloader await per matched call.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact authorized async boundary.
# - Summary:
#   - Caller-offloaded async adapter for authorized detached-key HTTPS fetches.
# - Description:
#   - Reuses exact authorized synchronous validation without owning scheduling.
# - Usage:
#   - Build from explicit authorized HTTPS state and a caller-selected offloader.
# - Defaults:
#   - No default offloader and no credential refresh or scheduling policy.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-offloaded async adapter for an authorized HTTPS bundle fetcher."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_https_authorized_fetcher as authorized,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

type _AuthorizedHttpsFetcher = (
    authorized.TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher
)

_ADAPTER_ID_PREFIX: Final = "offloaded-async-authorized-https-ticket-admission-"
_ADAPTER_ID_SUFFIX: Final = "lineage-public-key-bundle-fetcher-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_AUTHORIZED_HTTPS_FETCHER_ID: Final = (
    f"{_ADAPTER_ID_PREFIX}{_ADAPTER_ID_SUFFIX}"
)
_validate_authorized_fetcher: Final = (
    authorized.validate_ticket_admission_authorized_https_bundle_fetcher
)
_validate_request: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_request
)
_validate_result: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_result
)
_FAILED: Final = (
    fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind.FAILED
)


class TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
    ValueError
):
    """A caller-offloaded authorized async HTTPS adapter is invalid."""


class TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader(Protocol):
    """Caller-owned placement of one authorized synchronous HTTPS invocation."""

    async def __call__(
        self,
        fetcher: _AuthorizedHttpsFetcher,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Run one exact authorized fetcher call under caller scheduling."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher:
    """Immutable async adapter with hidden authorized fetcher and offloader."""

    adapter_id: str
    authorization_byte_count: int
    authorization_provider_id: str
    bundle_fingerprint: str
    fetch_provider_id: str
    fetcher: _AuthorizedHttpsFetcher = field(repr=False)
    fetcher_id: str
    offloader: TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader = field(
        repr=False
    )
    resource_id: str
    source_id: str

    async def __call__(
        self,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Await one caller-owned authorized offload.

        Returns:
            Shared typed fetched, unavailable, or failed result.

        Cancellation propagates directly to the caller.

        """
        adapter = _validated_adapter(self)
        validated_request = _validated_shared_request(request)
        if not _request_matches_adapter(validated_request, adapter):
            return _failed_result()
        result = await _await_offloader(adapter, validated_request)
        return _validated_shared_result(
            result,
            max_bytes=validated_request.max_bytes,
        )


def ticket_admission_async_authorized_https_bundle_fetcher_id() -> str:
    """Return the stable caller-offloaded authorized HTTPS adapter identity.

    Returns:
        Versioned async authorized HTTPS adapter identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_AUTHORIZED_HTTPS_FETCHER_ID


def build_ticket_admission_async_authorized_https_bundle_fetcher(
    fetcher: _AuthorizedHttpsFetcher,
    offloader: TicketAdmissionTelemetryLineageAuthorizedHttpsOffloader,
) -> TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher:
    """Build one caller-offloaded adapter over exact authorized HTTPS state.

    Returns:
        Validated immutable async authorized HTTPS adapter.

    """
    validated = _validated_authorized_fetcher(fetcher)
    _validate_offloader(offloader)
    return TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_AUTHORIZED_HTTPS_FETCHER_ID
        ),
        authorization_byte_count=validated.authorization_byte_count,
        authorization_provider_id=validated.authorization_provider_id,
        bundle_fingerprint=validated.bundle_fingerprint,
        fetch_provider_id=validated.fetch_provider_id,
        fetcher=validated,
        fetcher_id=validated.adapter_id,
        offloader=offloader,
        resource_id=validated.resource_id,
        source_id=validated.source_id,
    )


def validate_ticket_admission_async_authorized_https_bundle_fetcher(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher:
    """Validate one exact caller-offloaded authorized HTTPS adapter.

    Returns:
        The same exact adapter after complete binding validation.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher:
    _validate_adapter_shape(adapter)
    validated = _validated_authorized_fetcher(adapter.fetcher)
    _validate_adapter_binding(adapter, validated)
    _validate_offloader(adapter.offloader)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher
    ):
        _raise_adapter(
            "adapter must use the exact async authorized HTTPS adapter type"
        )
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_AUTHORIZED_HTTPS_FETCHER_ID
    ):
        _raise_adapter("adapter identity is unsupported")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
    validated: _AuthorizedHttpsFetcher,
) -> None:
    if adapter.fetcher_id != validated.adapter_id:
        _raise_adapter("adapter fetcher identity does not match fetcher")
    _validate_authorization_binding(adapter, validated)
    _validate_request_binding(adapter, validated)


def _validate_authorization_binding(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
    validated: _AuthorizedHttpsFetcher,
) -> None:
    if adapter.authorization_byte_count != validated.authorization_byte_count:
        _raise_adapter(
            "adapter authorization byte count does not match fetcher"
        )
    if adapter.authorization_provider_id != validated.authorization_provider_id:
        _raise_adapter(
            "adapter authorization provider identity does not match fetcher"
        )


def _validate_request_binding(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
    validated: _AuthorizedHttpsFetcher,
) -> None:
    if adapter.bundle_fingerprint != validated.bundle_fingerprint:
        _raise_adapter("adapter bundle fingerprint does not match fetcher")
    if adapter.fetch_provider_id != validated.fetch_provider_id:
        _raise_adapter("adapter fetch provider identity does not match fetcher")
    if adapter.resource_id != validated.resource_id:
        _raise_adapter("adapter resource identity does not match fetcher")
    if adapter.source_id != validated.source_id:
        _raise_adapter("adapter source identity does not match fetcher")


def _validated_authorized_fetcher(
    value: _AuthorizedHttpsFetcher,
) -> _AuthorizedHttpsFetcher:
    try:
        return _validate_authorized_fetcher(value)
    except (
        authorized.TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError
    ) as error:
        message = "invalid synchronous authorized HTTPS bundle fetcher"
        raise TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
            message
        ) from error


def _validate_offloader(value: object) -> None:
    if not callable(value):
        _raise_adapter("offloader must be callable")


def _validated_shared_request(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    try:
        return _validate_request(request)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = (
            "invalid caller-offloaded authorized HTTPS bundle fetch request"
        )
        raise TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
            message
        ) from error


def _request_matches_adapter(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
) -> bool:
    return (
        request.bundle_fingerprint == adapter.bundle_fingerprint
        and request.provider_id == adapter.fetch_provider_id
        and request.resource_id == adapter.resource_id
        and request.source_id == adapter.source_id
    )


async def _await_offloader(
    adapter: TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        return await adapter.offloader(adapter.fetcher, request)
    except CancelledError:
        raise
    except Exception as error:
        message = (
            "caller authorized HTTPS offloader raised during explicit fetch"
        )
        raise TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
            message
        ) from error


def _validated_shared_result(
    result: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult,
    *,
    max_bytes: int,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        return _validate_result(result, max_bytes=max_bytes)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "caller authorized HTTPS offloader returned an invalid result"
        raise TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
            message
        ) from error


def _failed_result() -> (
    fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
):
    return fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult(
        kind=_FAILED
    )


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage async authorized HTTPS fetcher "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageAsyncAuthorizedHttpsFetcherError(
        message
    )
