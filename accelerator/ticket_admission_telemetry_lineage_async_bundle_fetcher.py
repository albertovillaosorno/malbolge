# File:
#   - ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
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
#   - Explicit caller-driven async transport port for canonical key bundles.
# - Must-Not:
#   - Create event loops or tasks, discover endpoints, manage credentials,
#     retry, redirect, watch, cache, persist, validate certificates, or
#     change policy.
# - Allows:
#   - Inputs: one exact fetch request and one caller-supplied async port.
#   - Outputs: caller-owned memory providers bound to canonical bundle bytes.
#   - Side effects: exactly one awaited fetcher call per invocation.
# - Split-When:
#   - Split when native async HTTPS, concrete Authorization providers,
#     async Authorization injection, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact async bundle-fetch boundary.
# - Summary:
#   - Explicit one-await detached public-key bundle fetch port.
# - Description:
#   - Reuses synchronous request and result validation without hidden scheduling.
# - Usage:
#   - Await from a caller-owned event loop with one caller-owned fetcher.
# - Defaults:
#   - Reuses the synchronous 256-key and 1 MiB bounded request contract.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-driven async transport port for canonical public-key bundles."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from asyncio import CancelledError
from typing import Final
from typing import Protocol

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

_ASYNC_FETCHER_ID_PREFIX: Final = "explicit-async-ticket-admission-telemetry-"
_ASYNC_FETCHER_ID_SUFFIX: Final = "lineage-public-key-bundle-fetcher-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_BUNDLE_FETCHER_ID: Final = (
    f"{_ASYNC_FETCHER_ID_PREFIX}{_ASYNC_FETCHER_ID_SUFFIX}"
)

_validate_request: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_request
)
_materialize_result: Final = (
    fetch.materialize_ticket_admission_public_key_bundle_fetch_result
)


class TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError(
    ValueError
):
    """An explicit async bundle fetch is invalid or unsuccessful."""


class TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcher(Protocol):
    """Caller-supplied async transport without scheduling or lifecycle policy."""

    async def __call__(
        self,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Fetch one exact resource without retries or hidden caching."""
        ...


def ticket_admission_async_public_key_bundle_fetcher_id() -> str:
    """Return the stable explicit async bundle-fetcher identity.

    Returns:
        Versioned async fetcher-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ASYNC_PUBLIC_KEY_BUNDLE_FETCHER_ID


async def fetch_ticket_admission_public_key_bundle_provider_async(
    fetcher: TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineageFetchedPublicKeyBundle:
    """Await, validate, and materialize one canonical public-key bundle.

    Returns:
        Stable source metadata and hidden caller-owned memory provider.

    Cancellation propagates directly to the caller.

    Raises:
        TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError:
            Request preflight, fetch execution, or result processing fails.

    """
    validated_request = _validated_request(request)
    result = await _await_fetcher(fetcher, validated_request)
    try:
        return _materialize_result(validated_request, result)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "cannot process async fetched public-key bundle"
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError(
            message
        ) from error


def _validated_request(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    try:
        return _validate_request(request)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "invalid async public-key bundle fetch request"
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError(
            message
        ) from error


async def _await_fetcher(
    fetcher: TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        return await fetcher(request)
    except CancelledError:
        raise
    except Exception as error:
        message = "async bundle fetcher raised during explicit fetch"
        raise TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError(
            message
        ) from error
