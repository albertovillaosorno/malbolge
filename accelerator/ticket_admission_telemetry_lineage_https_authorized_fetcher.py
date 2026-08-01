# File:
#   - ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
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
#   - Explicit synchronous HTTPS fetcher with one resolved Authorization value.
# - Must-Not:
#   - Resolve credentials, select schemes, discover endpoints, retry, redirect,
#     cache, persist, log authorization, create workers, or change policy.
# - Allows:
#   - Inputs: one exact HTTPS fetcher and one exact resolved Authorization value.
#   - Outputs: the shared typed fetched, unavailable, or failed transport result.
#   - Side effects: one HTTPS connection, one GET, and one close per matched call.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact authorized HTTPS boundary.
# - Summary:
#   - Explicit Authorization-injecting HTTPS detached-key bundle fetcher.
# - Description:
#   - Binds exact caller-owned authorization to one exact HTTPS bundle source.
# - Usage:
#   - Resolve authorization explicitly, build this fetcher, then fetch normally.
# - Defaults:
#   - Exactly one Authorization header and the base no-redirect HTTPS semantics.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_environment_async_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit Authorization-injecting synchronous HTTPS bundle fetcher."""

# ruff: file-ignore[line-too-long,doc-line-too-long,private-member-access]
# pyright: reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from http.client import HTTPException
from typing import Final
from typing import Never
from typing import Protocol
from typing import cast

from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)

type _ResolvedHttpsAuthorization = (
    auth.TicketAdmissionTelemetryLineageResolvedHttpsAuthorization
)

_AUTHORIZED_FETCHER_ID_PREFIX: Final = "authorized-https-ticket-admission-"
_AUTHORIZED_FETCHER_ID_SUFFIX: Final = "lineage-public-key-bundle-fetcher-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_AUTHORIZED_HTTPS_FETCHER_ID: Final = (
    f"{_AUTHORIZED_FETCHER_ID_PREFIX}{_AUTHORIZED_FETCHER_ID_SUFFIX}"
)
_validate_https_fetcher: Final = (
    https.validate_ticket_admission_https_public_key_bundle_fetcher
)
_validate_authorization: Final = (
    auth.validate_ticket_admission_resolved_https_authorization
)
_validate_request: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_request
)
_FAILED: Final = (
    fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind.FAILED
)


class _HttpsResponse(Protocol):
    status: int

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one combined response header value."""
        ...

    def read(self, amount: int | None = None) -> bytes:
        """Read at most the requested number of response bytes."""
        ...


class _HttpsConnection(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> None:
        """Send one HTTP request."""
        ...

    def getresponse(self) -> _HttpsResponse:
        """Return the response for the preceding request."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


class TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError(ValueError):
    """An explicit authorized HTTPS fetcher is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher:
    """Immutable explicit binding of HTTPS transport and Authorization value."""

    adapter_id: str
    authorization: _ResolvedHttpsAuthorization = field(repr=False)
    authorization_byte_count: int
    authorization_provider_id: str
    bundle_fingerprint: str
    fetch_provider_id: str
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher = field(
        repr=False
    )
    fetcher_id: str
    resource_id: str
    source_id: str

    def __call__(
        self,
        request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Perform one direct authorized no-redirect HTTPS GET.

        Returns:
            Shared typed fetched, unavailable, or failed result.

        """
        adapter = _validated_adapter(self)
        validated_request = _validated_shared_request(request)
        if not _request_matches_adapter(validated_request, adapter):
            return _failed_result()
        return _exchange(adapter, validated_request)


def ticket_admission_authorized_https_bundle_fetcher_id() -> str:
    """Return the stable explicit authorized HTTPS fetcher identity.

    Returns:
        Versioned authorized HTTPS fetcher identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_AUTHORIZED_HTTPS_FETCHER_ID


def build_ticket_admission_authorized_https_bundle_fetcher(
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    authorization: _ResolvedHttpsAuthorization,
) -> TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher:
    """Build one exact authorized HTTPS fetcher from explicit caller state.

    Returns:
        Validated immutable authorized HTTPS fetcher.

    """
    validated_fetcher = _validated_https_fetcher(fetcher)
    validated_authorization = _validated_authorization_value(authorization)
    _validate_authorization_fetcher_binding(
        validated_authorization,
        validated_fetcher,
    )
    return TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher(
        adapter_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_AUTHORIZED_HTTPS_FETCHER_ID,
        authorization=validated_authorization,
        authorization_byte_count=(
            validated_authorization.authorization_byte_count
        ),
        authorization_provider_id=(
            validated_authorization.authorization_provider_id
        ),
        bundle_fingerprint=validated_authorization.bundle_fingerprint,
        fetch_provider_id=validated_authorization.fetch_provider_id,
        fetcher=validated_fetcher,
        fetcher_id=validated_fetcher.fetcher_id,
        resource_id=validated_authorization.resource_id,
        source_id=validated_authorization.source_id,
    )


def validate_ticket_admission_authorized_https_bundle_fetcher(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher:
    """Validate one exact immutable authorized HTTPS fetcher.

    Returns:
        The same exact adapter after complete binding validation.

    """
    return _validated_adapter(value)


def _validated_adapter(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
) -> TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher:
    _validate_adapter_shape(value)
    validated_fetcher = _validated_https_fetcher(value.fetcher)
    validated_authorization = _validated_authorization_value(
        value.authorization
    )
    _validate_authorization_fetcher_binding(
        validated_authorization,
        validated_fetcher,
    )
    _validate_adapter_binding(
        value,
        validated_fetcher,
        validated_authorization,
    )
    return value


def _validate_adapter_shape(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
) -> None:
    if (
        type(value)
        is not TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher
    ):
        _raise_authorized("fetcher must use the exact authorized HTTPS type")
    if (
        value.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_AUTHORIZED_HTTPS_FETCHER_ID
    ):
        _raise_authorized("fetcher identity is unsupported")


def _validate_authorization_fetcher_binding(
    authorization: _ResolvedHttpsAuthorization,
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> None:
    if authorization.resource_id != fetcher.config.resource_id:
        _raise_authorized(
            "authorization resource identity does not match HTTPS fetcher"
        )
    if authorization.source_id != fetcher.config.source_id:
        _raise_authorized(
            "authorization source identity does not match HTTPS fetcher"
        )


def _validate_adapter_binding(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
    fetcher: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
    authorization: _ResolvedHttpsAuthorization,
) -> None:
    if value.fetcher_id != fetcher.fetcher_id:
        _raise_authorized("copied fetcher identity does not match fetcher")
    _validate_adapter_authorization_metadata(value, authorization)
    _validate_adapter_request_metadata(value, authorization)


def _validate_adapter_authorization_metadata(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
    authorization: _ResolvedHttpsAuthorization,
) -> None:
    if value.authorization_byte_count != authorization.authorization_byte_count:
        _raise_authorized(
            "copied authorization byte count does not match authorization"
        )
    if (
        value.authorization_provider_id
        != authorization.authorization_provider_id
    ):
        _raise_authorized(
            "copied authorization provider identity does not match authorization"
        )


def _validate_adapter_request_metadata(
    value: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
    authorization: _ResolvedHttpsAuthorization,
) -> None:
    if value.bundle_fingerprint != authorization.bundle_fingerprint:
        _raise_authorized(
            "copied bundle fingerprint does not match authorization"
        )
    if value.fetch_provider_id != authorization.fetch_provider_id:
        _raise_authorized(
            "copied fetch provider identity does not match authorization"
        )
    if value.resource_id != authorization.resource_id:
        _raise_authorized(
            "copied resource identity does not match authorization"
        )
    if value.source_id != authorization.source_id:
        _raise_authorized("copied source identity does not match authorization")


def _validated_https_fetcher(
    value: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    try:
        return _validate_https_fetcher(value)
    except (
        https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError
    ) as error:
        message = "invalid HTTPS fetcher for authorized transport"
        raise TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError(
            message
        ) from error


def _validated_authorization_value(
    value: _ResolvedHttpsAuthorization,
) -> _ResolvedHttpsAuthorization:
    try:
        return _validate_authorization(value)
    except (
        auth.TicketAdmissionTelemetryLineageHttpsAuthorizationProviderError
    ) as error:
        message = "invalid resolved Authorization for HTTPS transport"
        raise TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError(
            message
        ) from error


def _validated_shared_request(
    value: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    try:
        return _validate_request(value)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "invalid authorized HTTPS public-key bundle fetch request"
        raise TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError(
            message
        ) from error


def _request_matches_adapter(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    adapter: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
) -> bool:
    return (
        request.bundle_fingerprint == adapter.bundle_fingerprint
        and request.provider_id == adapter.fetch_provider_id
        and request.resource_id == adapter.resource_id
        and request.source_id == adapter.source_id
    )


def _exchange(
    adapter: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        connection = _open_connection(adapter.fetcher.config)
    except HTTPException, OSError, ValueError:
        return _failed_result()
    result = _request_result(connection, adapter, request)
    try:
        connection.close()
    except HTTPException, OSError, ValueError:
        return _failed_result()
    return result


def _request_result(
    connection: _HttpsConnection,
    adapter: TicketAdmissionTelemetryLineageAuthorizedHttpsBundleFetcher,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        connection.request(
            "GET",
            adapter.fetcher.config.target,
            headers=_request_headers(adapter.authorization),
        )
        response = connection.getresponse()
        return _response_result(response, max_bytes=request.max_bytes)
    except HTTPException, OSError, ValueError:
        return _failed_result()


def _request_headers(
    authorization: _ResolvedHttpsAuthorization,
) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        authorization.header_name: authorization.authorization_value,
        "Connection": "close",
    }


def _open_connection(
    config: https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
) -> _HttpsConnection:
    connection = https._open_connection(config)
    return cast("_HttpsConnection", cast("object", connection))


def _response_result(
    response: _HttpsResponse,
    *,
    max_bytes: int,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    return https._response_result(
        response,
        max_bytes=max_bytes,
    )


def _failed_result() -> (
    fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
):
    return fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult(
        kind=_FAILED
    )


def _raise_authorized(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage authorized HTTPS bundle fetcher "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageAuthorizedHttpsFetcherError(message)
