# File:
#   - ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
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
#   - Explicit synchronous HTTPS GET transport for canonical key bundles.
# - Must-Not:
#   - Discover endpoints, create trust roots, send credentials, redirect,
#     retry, watch, cache, persist, select algorithms, or change policy.
# - Allows:
#   - Inputs: one exact endpoint config, caller-owned TLS context, and request.
#   - Outputs: shared typed fetched, unavailable, or failed transport results.
#   - Side effects: one direct HTTPS connection and one close per call.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact synchronous HTTPS boundary.
# - Summary:
#   - Explicit no-redirect HTTPS detached public-key bundle fetcher.
# - Description:
#   - Uses stdlib HTTPS with caller-owned certificate-validation state.
# - Usage:
#   - Build from one exact config, then pass it to the shared fetch boundary.
# - Defaults:
#   - HTTPS GET, JSON identity encoding, port 443, and at most 300 seconds.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit synchronous HTTPS transport for canonical public-key bundles."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from http.client import HTTPException
from http.client import HTTPSConnection
from math import isfinite
from re import compile as compile_pattern
from ssl import CERT_REQUIRED
from ssl import SSLContext
from ssl import TLSVersion
from typing import Final
from typing import Never
from typing import Protocol
from typing import cast
from urllib.parse import urlsplit

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

_HTTPS_FETCHER_ID_PREFIX: Final = "explicit-https-ticket-admission-telemetry-"
_HTTPS_FETCHER_ID_SUFFIX: Final = "lineage-public-key-bundle-fetcher-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_PUBLIC_KEY_BUNDLE_FETCHER_ID: Final = (
    f"{_HTTPS_FETCHER_ID_PREFIX}{_HTTPS_FETCHER_ID_SUFFIX}"
)
DEFAULT_HTTPS_PUBLIC_KEY_BUNDLE_PORT: Final = 443
MAX_HTTPS_PUBLIC_KEY_BUNDLE_TIMEOUT_SECONDS: Final = 300.0
_HTTP_OK: Final = 200
_HTTP_NOT_FOUND: Final = 404
_HTTP_GONE: Final = 410
_MAX_TCP_PORT: Final = 65535
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_HOST_PATTERN_PREFIX: Final = (
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
)
_HOST_PATTERN_SUFFIX: Final = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST_PATTERN: Final = compile_pattern(
    f"{_HOST_PATTERN_PREFIX}{_HOST_PATTERN_SUFFIX}"
)
_FETCH_KIND: Final = (
    fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
)
_FETCHED: Final = _FETCH_KIND.FETCHED
_UNAVAILABLE: Final = _FETCH_KIND.UNAVAILABLE
_FAILED: Final = _FETCH_KIND.FAILED
_JSON_MEDIA_TYPE: Final = "application/json"
_UTF8_PARAMETER: Final = "charset=utf-8"
_IDENTITY_ENCODING: Final = "identity"
_ASCII_CONTROL_LIMIT: Final = 32
_BACKSLASH: Final = "\\"
_validate_request: Final = (
    fetch.validate_ticket_admission_public_key_bundle_fetch_request
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


class TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError(
    ValueError
):
    """An explicit HTTPS bundle fetcher configuration is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig:
    """Exact caller-owned HTTPS endpoint and TLS validation configuration."""

    host: str = field(repr=False)
    resource_id: str
    source_id: str
    target: str = field(repr=False)
    tls_context: SSLContext = field(repr=False)
    port: int = DEFAULT_HTTPS_PUBLIC_KEY_BUNDLE_PORT
    timeout_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    """Stateless exact HTTPS GET fetcher with hidden endpoint and TLS state."""

    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig = (
        field(repr=False)
    )
    fetcher_id: str

    def __call__(
        self,
        request: (
            fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
        ),
    ) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Perform one direct no-redirect HTTPS GET.

        Returns:
            Shared typed fetched, unavailable, or failed result.

        """
        validated = _validated_fetcher(self)
        validated_request = _validated_shared_request(request)
        if not _request_matches_config(validated_request, validated.config):
            return _result(_FAILED)
        return _exchange(validated.config, validated_request)


def ticket_admission_https_public_key_bundle_fetcher_id() -> str:
    """Return the stable concrete HTTPS fetcher identity.

    Returns:
        Versioned synchronous HTTPS fetcher identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_PUBLIC_KEY_BUNDLE_FETCHER_ID


def build_ticket_admission_https_public_key_bundle_fetcher(
    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
) -> TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    """Build one exact stateless HTTPS public-key bundle fetcher.

    Returns:
        Validated reusable synchronous HTTPS fetcher.

    """
    validated = _validated_config(config)
    return TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher(
        config=validated,
        fetcher_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_PUBLIC_KEY_BUNDLE_FETCHER_ID
        ),
    )


def validate_ticket_admission_https_public_key_bundle_fetcher(
    value: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    """Validate one exact immutable synchronous HTTPS fetcher.

    Returns:
        The same exact fetcher after complete configuration validation.

    """
    return _validated_fetcher(value)


def _validated_fetcher(
    value: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher,
) -> TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher:
    if (
        type(value)
        is not TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
    ):
        _raise_https("fetcher must use the exact HTTPS fetcher type")
    if (
        value.fetcher_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_HTTPS_PUBLIC_KEY_BUNDLE_FETCHER_ID
    ):
        _raise_https("fetcher identity is unsupported")
    _ = _validated_config(value.config)
    return value


def _validated_config(
    value: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
) -> TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig:
    if (
        type(value)
        is not TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
    ):
        _raise_https("config must use the exact HTTPS config type")
    _ = _validated_host(value.host)
    _ = _validated_port(value.port)
    _ = _validated_identifier(value.resource_id, "resource identity")
    _ = _validated_identifier(value.source_id, "source identity")
    _ = _validated_target(value.target)
    _ = _validated_timeout(value.timeout_seconds)
    _ = _validated_tls_context(value.tls_context)
    return value


def _validated_shared_request(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    try:
        return _validate_request(request)
    except (
        fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
    ) as error:
        message = "invalid HTTPS public-key bundle fetch request"
        raise TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError(
            message
        ) from error


def _request_matches_config(
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
) -> bool:
    return (
        request.resource_id == config.resource_id
        and request.source_id == config.source_id
    )


def _exchange(
    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        connection = _open_connection(config)
    except HTTPException, OSError, ValueError:
        return _result(_FAILED)
    result = _request_result(connection, config, request)
    try:
        connection.close()
    except HTTPException, OSError, ValueError:
        return _result(_FAILED)
    return result


def _request_result(
    connection: _HttpsConnection,
    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
    request: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        connection.request(
            "GET",
            config.target,
            headers=_request_headers(),
        )
        response = connection.getresponse()
        return _response_result(response, max_bytes=request.max_bytes)
    except HTTPException, OSError, ValueError:
        return _result(_FAILED)


def _response_result(
    response: _HttpsResponse,
    *,
    max_bytes: int,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    kind = _response_kind(response.status)
    if kind is not _FETCHED:
        return _result(kind)
    payload = _validated_response_payload(response, max_bytes=max_bytes)
    if payload is None:
        return _result(_FAILED)
    return _result(_FETCHED, payload=payload)


def _response_kind(
    status: int,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind:
    kind = _FAILED
    if type(status) is int and status == _HTTP_OK:
        kind = _FETCHED
    elif type(status) is int and status in {_HTTP_NOT_FOUND, _HTTP_GONE}:
        kind = _UNAVAILABLE
    return kind


def _validated_response_payload(
    response: _HttpsResponse,
    *,
    max_bytes: int,
) -> bytes | None:
    valid, expected_length = _response_metadata(response, max_bytes=max_bytes)
    payload: bytes | None = None
    if valid:
        candidate = response.read(max_bytes + 1)
        shape_valid = _payload_shape_is_valid(candidate, max_bytes=max_bytes)
        length_valid = (
            expected_length is None or len(candidate) == expected_length
        )
        if shape_valid and length_valid:
            payload = candidate
    return payload


def _response_metadata(
    response: _HttpsResponse,
    *,
    max_bytes: int,
) -> tuple[bool, int | None]:
    if not _content_type_is_json(response):
        return False, None
    if not _content_encoding_is_identity(response):
        return False, None
    return _content_length(response, max_bytes=max_bytes)


def _payload_shape_is_valid(payload: bytes, *, max_bytes: int) -> bool:
    return (
        type(payload) is bytes and bool(payload) and len(payload) <= max_bytes
    )


def _content_type_is_json(response: _HttpsResponse) -> bool:
    value = response.getheader("Content-Type")
    if type(value) is not str:
        return False
    parts = tuple(part.strip().lower() for part in value.split(";"))
    if not parts or parts[0] != _JSON_MEDIA_TYPE:
        return False
    return len(parts) == 1 or parts == (_JSON_MEDIA_TYPE, _UTF8_PARAMETER)


def _content_encoding_is_identity(response: _HttpsResponse) -> bool:
    value = response.getheader("Content-Encoding")
    if value is None:
        return True
    return type(value) is str and value.strip().lower() == _IDENTITY_ENCODING


def _content_length(
    response: _HttpsResponse,
    *,
    max_bytes: int,
) -> tuple[bool, int | None]:
    value = response.getheader("Content-Length")
    valid = value is None
    length: int | None = None
    if value is not None and _content_length_text_is_valid(value):
        candidate = int(value)
        valid = 0 < candidate <= max_bytes
        if valid:
            length = candidate
    return valid, length


def _content_length_text_is_valid(value: str) -> bool:
    return (
        type(value) is str
        and value.isascii()
        and value.isdecimal()
        and (len(value) == 1 or not value.startswith("0"))
    )


def _request_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }


def _result(
    kind: fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind,
    *,
    payload: bytes | None = None,
) -> fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    return fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult(
        kind=kind,
        payload=payload,
    )


def _validated_host(value: str) -> str:
    if type(value) is not str or _HOST_PATTERN.fullmatch(value) is None:
        _raise_https("host must use canonical lowercase ASCII DNS form")
    return value


def _validated_port(value: int) -> int:
    if type(value) is not int or not 1 <= value <= _MAX_TCP_PORT:
        _raise_https("port must be an integer from 1 through 65535")
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_https(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_https(f"{field_name} exceeds configured length")
    return value


def _validated_target(value: str) -> str:
    if (
        type(value) is not str
        or not value.isascii()
        or not value.startswith("/")
    ):
        _raise_https("target must use absolute ASCII origin form")
    if any(
        character.isspace() or ord(character) < _ASCII_CONTROL_LIMIT
        for character in value
    ):
        _raise_https("target cannot contain whitespace or controls")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        _raise_https("target must not contain scheme, authority, or fragment")
    if value.startswith("//") or _BACKSLASH in value:
        _raise_https("target must use canonical origin form")
    return value


def _validated_timeout(value: float) -> float:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        _raise_https("timeout must be a positive finite float")
    if value > MAX_HTTPS_PUBLIC_KEY_BUNDLE_TIMEOUT_SECONDS:
        _raise_https("timeout exceeds supported maximum")
    return value


def _validated_tls_context(value: SSLContext) -> SSLContext:
    if type(value) is not SSLContext:
        _raise_https("TLS context must use the exact SSLContext type")
    if not value.check_hostname:
        _raise_https("TLS context must enable hostname checking")
    if value.verify_mode != CERT_REQUIRED:
        _raise_https("TLS context must require peer certificates")
    if value.minimum_version < TLSVersion.TLSv1_2:
        _raise_https("TLS context must require TLS 1.2 or newer")
    return value


def _open_connection(
    config: TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig,
) -> _HttpsConnection:
    connection = HTTPSConnection(
        config.host,
        config.port,
        timeout=config.timeout_seconds,
        context=config.tls_context,
    )
    return cast("_HttpsConnection", cast("object", connection))


def _raise_https(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage HTTPS public-key bundle fetcher "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherError(
        message
    )
