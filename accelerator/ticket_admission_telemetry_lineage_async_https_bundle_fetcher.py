# File:
#   - ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
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
#   - Explicit caller-offloaded async adapter for the synchronous HTTPS fetcher.
# - Must-Not:
#   - Create event loops, tasks, threads, executors, credentials, redirects,
#     retries, caches, trust roots, hosted-service policy, or admission policy.
# - Allows:
#   - Inputs: one exact HTTPS fetcher, one caller offloader, and exact requests.
#   - Outputs: the shared typed fetched, unavailable, or failed transport result.
#   - Side effects: exactly one caller-supplied offloader await per matched call.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact caller-offloaded async boundary.
# - Summary:
#   - Caller-offloaded async adapter for detached-key HTTPS bundle fetches.
# - Description:
#   - Reuses exact synchronous HTTPS validation without owning scheduling.
# - Usage:
#   - Build with one HTTPS fetcher and a caller-selected async offloader.
# - Defaults:
#   - No default offloader; caller explicitly owns all blocking-work placement.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-offloaded async adapter for the synchronous HTTPS bundle fetcher."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

_ADAPTER_ID_PREFIX: Final = "offloaded-async-https-ticket-admission-"
_ADAPTER_ID_SUFFIX: Final = "lineage-public-key-bundle-fetcher-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_BUNDLE_FETCHER_ID: Final = (
    f"{_ADAPTER_ID_PREFIX}{_ADAPTER_ID_SUFFIX}"
)
_validate_https_fetcher: Final = (
    https.validate_ticket_admission_https_public_key_bundle_fetcher
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


class TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(ValueError):
    """A caller-offloaded async HTTPS adapter is invalid or unsuccessful."""


class TicketAdmissionTelemetryLineageHttpsBundleOffloader(Protocol):
    """Caller-owned placement of one synchronous HTTPS fetch invocation."""

    async def __call__(
        self,
        fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Run one exact synchronous fetcher call under caller scheduling."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher:
    """Immutable async adapter with hidden fetcher and offload policy."""

    adapter_id: str
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher = field(
        repr=False
    )
    fetcher_id: str
    offloader: TicketAdmissionTelemetryLineageHttpsBundleOffloader = field(
        repr=False
    )
    resource_id: str
    source_id: str

    async def __call__(
        self,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Await one caller-owned offload without creating scheduling resources.

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


def ticket_admission_async_https_bundle_fetcher_id() -> str:
    """Return the stable caller-offloaded async HTTPS adapter identity.

    Returns:
        Versioned async HTTPS adapter identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_BUNDLE_FETCHER_ID


def build_ticket_admission_async_https_bundle_fetcher(
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    offloader: TicketAdmissionTelemetryLineageHttpsBundleOffloader,
) -> TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher:
    """Build one explicit caller-offloaded adapter over exact HTTPS state.

    Returns:
        Validated immutable async adapter.

    """
    validated = _validated_https_fetcher(fetcher)
    _validate_offloader(offloader)
    return TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_BUNDLE_FETCHER_ID
        ),
        fetcher=validated,
        fetcher_id=validated.fetcher_id,
        offloader=offloader,
        resource_id=validated.config.resource_id,
        source_id=validated.config.source_id,
    )


def validate_ticket_admission_async_https_bundle_fetcher(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher:
    """Validate one exact immutable caller-offloaded HTTPS adapter.

    Returns:
        The same exact adapter after complete binding validation.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher:
    _validate_adapter_shape(adapter)
    validated = _validated_https_fetcher(adapter.fetcher)
    _validate_adapter_binding(adapter, validated)
    _validate_offloader(adapter.offloader)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher
    ):
        _raise_adapter("adapter must use the exact async HTTPS adapter type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_HTTPS_BUNDLE_FETCHER_ID
    ):
        _raise_adapter("adapter identity is unsupported")
    _validate_adapter_metadata(adapter)


def _validate_adapter_metadata(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
) -> None:
    if type(adapter.fetcher_id) is not str or not adapter.fetcher_id:
        _raise_adapter("wrapped fetcher identity must be a nonempty string")
    if type(adapter.resource_id) is not str or not adapter.resource_id:
        _raise_adapter("resource identity must be a nonempty string")
    if type(adapter.source_id) is not str or not adapter.source_id:
        _raise_adapter("source identity must be a nonempty string")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
    validated: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> None:
    if adapter.fetcher_id != validated.fetcher_id:
        _raise_adapter("adapter fetcher identity does not match fetcher")
    if adapter.resource_id != validated.config.resource_id:
        _raise_adapter("adapter resource identity does not match fetcher")
    if adapter.source_id != validated.config.source_id:
        _raise_adapter("adapter source identity does not match fetcher")


def _validated_https_fetcher(
    value: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    try:
        return _validate_https_fetcher(value)
    except (
        https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError
    ) as error:
        message = "invalid synchronous HTTPS public-key bundle fetcher"
        raise TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(
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
        message = "invalid caller-offloaded HTTPS bundle fetch request"
        raise TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(
            message
        ) from error


def _request_matches_adapter(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
) -> bool:
    return (
        request.resource_id == adapter.resource_id
        and request.source_id == adapter.source_id
    )


async def _await_offloader(
    adapter: TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        return await adapter.offloader(adapter.fetcher, request)
    except CancelledError:
        raise
    except Exception as error:
        message = "caller HTTPS offloader raised during explicit fetch"
        raise TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(
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
        message = "caller HTTPS offloader returned an invalid fetch result"
        raise TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(
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
        "ticket admission telemetry lineage async HTTPS bundle fetcher "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageAsyncHttpsBundleFetcherError(message)
