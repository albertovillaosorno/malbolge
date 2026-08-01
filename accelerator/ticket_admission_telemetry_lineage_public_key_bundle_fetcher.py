# File:
#   - ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
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
#   - Explicit synchronous transport port for canonical public-key bundles.
# - Must-Not:
#   - Implement HTTP, discover endpoints, manage credentials, retry, redirect,
#     watch, cache, persist, validate certificates, or change policy.
# - Allows:
#   - Inputs: exact source/resource identities, expected metadata, and one port.
#   - Outputs: caller-owned memory providers bound to canonical bundle bytes.
#   - Side effects: exactly one caller-supplied fetcher call per invocation.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact explicit bundle-fetch boundary.
# - Summary:
#   - Explicit one-call remote detached public-key bundle fetch port.
# - Description:
#   - Validates expected fingerprint and provider identity after bounded decode.
# - Usage:
#   - Supply one transport explicitly; the module performs no endpoint
#     discovery.
# - Defaults:
#   - At most 256 keys and 1 MiB in one exact synchronous fetch result.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit synchronous transport port for canonical public-key bundles."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
    )

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle as bundle,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)

_FETCHER_ID: Final = (
    "explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCHER_ID: Final = (
    _FETCHER_ID
)
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES: Final = (
    bundle.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES
)
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES: Final = (
    bundle.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES
)
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_BUNDLE_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:[0-9a-f]{64}"
)
_decode_bundle: Final = (
    bundle.decode_ticket_admission_telemetry_lineage_public_key_bundle
)
_materialize_provider: Final = (
    bundle.materialize_ticket_admission_public_key_bundle_provider
)


class TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError(ValueError):
    """An explicit bundle fetch request or result is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    """One immutable transport-neutral request for exact canonical bytes."""

    bundle_fingerprint: str
    max_bytes: int
    max_entries: int
    provider_id: str
    resource_id: str
    source_id: str


class TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind(StrEnum):
    """Stable fetch outcome without transport or vendor detail."""

    FETCHED = "fetched"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    """Typed fetch outcome with hidden optional canonical bundle bytes."""

    kind: TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
    payload: bytes | None = field(default=None, repr=False)


class TicketAdmissionTelemetryLineagePublicKeyBundleFetcher(Protocol):
    """Caller-supplied synchronous transport without lifecycle semantics."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    ) -> TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
        """Fetch one exact resource without retries or hidden caching."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFetchedPublicKeyBundle:
    """Fetched bundle metadata with a hidden caller-owned memory provider."""

    bundle_fingerprint: str
    byte_count: int
    key_count: int
    provider: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider = (
        field(repr=False)
    )
    provider_id: str
    resource_id: str
    source_id: str


def ticket_admission_telemetry_lineage_public_key_bundle_fetcher_id() -> str:
    """Return the stable explicit bundle-fetcher port identity.

    Returns:
        Versioned synchronous fetcher-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCHER_ID


def fetch_ticket_admission_telemetry_lineage_public_key_bundle_provider(
    fetcher: TicketAdmissionTelemetryLineagePublicKeyBundleFetcher,
    request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> TicketAdmissionTelemetryLineageFetchedPublicKeyBundle:
    """Fetch, validate, and materialize one exact canonical public-key bundle.

    Returns:
        Stable source metadata and hidden caller-owned memory provider.

    """
    validated_request = (
        validate_ticket_admission_public_key_bundle_fetch_request(request)
    )
    result = _invoke_fetcher(fetcher, validated_request)
    return materialize_ticket_admission_public_key_bundle_fetch_result(
        validated_request,
        result,
    )


def validate_ticket_admission_public_key_bundle_fetch_request(
    request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest:
    """Validate one exact transport-neutral fetch request.

    Returns:
        The same immutable request after complete preflight.

    """
    if (
        type(request)
        is not TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
    ):
        _raise_fetcher("request must use the exact fetch request type")
    _ = _validated_bundle_fingerprint(request.bundle_fingerprint)
    _ = _validated_identifier(request.provider_id, "provider identity")
    _ = _validated_identifier(request.resource_id, "resource identity")
    _ = _validated_identifier(request.source_id, "source identity")
    _ = _validated_bounded_limit(
        request.max_bytes,
        field_name="byte limit",
        maximum=DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES,
    )
    _ = _validated_bounded_limit(
        request.max_entries,
        field_name="entry limit",
        maximum=DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES,
    )
    return request


def validate_ticket_admission_public_key_bundle_fetch_result(
    result: TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult,
    *,
    max_bytes: int,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    """Validate one exact bounded transport-neutral fetch result.

    Returns:
        The same immutable result after exact shape and payload validation.

    """
    validated = _validated_result(result)
    if (
        validated.kind
        is TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind.FETCHED
    ):
        _ = _validated_fetched_payload(validated, max_bytes=max_bytes)
    return validated


def materialize_ticket_admission_public_key_bundle_fetch_result(
    request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
    result: TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult,
) -> TicketAdmissionTelemetryLineageFetchedPublicKeyBundle:
    """Validate one typed fetch result and materialize its memory provider.

    Returns:
        Stable source metadata and hidden caller-owned memory provider.

    """
    validated_request = (
        validate_ticket_admission_public_key_bundle_fetch_request(request)
    )
    validated_result = _validated_result(result)
    payload = _validated_fetched_payload(
        validated_result,
        max_bytes=validated_request.max_bytes,
    )
    decoded = _decode_payload(payload, request=validated_request)
    loaded = _materialize(decoded, max_entries=validated_request.max_entries)
    if loaded.bundle_fingerprint != validated_request.bundle_fingerprint:
        _raise_fetcher("fetched bundle fingerprint does not match request")
    if loaded.provider_id != validated_request.provider_id:
        _raise_fetcher(
            "fetched bundle provider identity does not match request"
        )
    return TicketAdmissionTelemetryLineageFetchedPublicKeyBundle(
        bundle_fingerprint=loaded.bundle_fingerprint,
        byte_count=loaded.byte_count,
        key_count=loaded.key_count,
        provider=loaded.provider,
        provider_id=loaded.provider_id,
        resource_id=validated_request.resource_id,
        source_id=validated_request.source_id,
    )


def _invoke_fetcher(
    fetcher: TicketAdmissionTelemetryLineagePublicKeyBundleFetcher,
    request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    try:
        return fetcher(request)
    except Exception as error:
        message = "bundle fetcher raised during explicit fetch"
        raise TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError(
            message
        ) from error


def _validated_fetched_payload(
    result: TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult,
    *,
    max_bytes: int,
) -> bytes:
    fetch_kind = TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
    if result.kind is not fetch_kind.FETCHED:
        _raise_fetcher(f"bundle fetcher returned {result.kind.value}")
    payload = result.payload
    if type(payload) is not bytes:
        _raise_fetcher("fetched result requires exact payload bytes")
    if not payload:
        _raise_fetcher("fetched payload cannot be empty")
    if len(payload) > max_bytes:
        _raise_fetcher("fetched payload exceeds requested byte limit")
    return payload


def _validated_result(
    result: TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult:
    if (
        type(result)
        is not TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
    ):
        _raise_fetcher("result must use the exact fetch result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
    ):
        _raise_fetcher("result kind must use the exact fetch result enum")
    fetch_kind = TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
    if result.kind is not fetch_kind.FETCHED and result.payload is not None:
        _raise_fetcher("nonfetched result cannot contain bundle bytes")
    return result


def _decode_payload(
    payload: bytes,
    *,
    request: TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest,
) -> bundle.TicketAdmissionTelemetryLineagePublicKeyBundle:
    try:
        return _decode_bundle(
            payload,
            max_bytes=request.max_bytes,
            max_entries=request.max_entries,
        )
    except bundle.TicketAdmissionTelemetryLineagePublicKeyBundleError as error:
        message = "cannot decode fetched public-key bundle"
        raise TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError(
            message
        ) from error


def _materialize(
    value: bundle.TicketAdmissionTelemetryLineagePublicKeyBundle,
    *,
    max_entries: int,
) -> bundle.TicketAdmissionTelemetryLineageLoadedPublicKeyBundle:
    try:
        return _materialize_provider(value, max_entries=max_entries)
    except bundle.TicketAdmissionTelemetryLineagePublicKeyBundleError as error:
        message = "cannot materialize fetched public-key bundle"
        raise TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError(
            message
        ) from error


def _validated_bundle_fingerprint(value: str) -> str:
    if (
        type(value) is not str
        or _BUNDLE_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_fetcher("bundle fingerprint is malformed")
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_fetcher(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_fetcher(f"{field_name} exceeds configured length")
    return value


def _validated_bounded_limit(
    value: int,
    *,
    field_name: str,
    maximum: int,
) -> int:
    if type(value) is not int or value <= 0:
        _raise_fetcher(f"{field_name} must be a positive integer")
    if value > maximum:
        _raise_fetcher(f"{field_name} exceeds supported maximum")
    return value


def _raise_fetcher(detail: str) -> Never:
    message = (
        f"ticket admission telemetry lineage public-key bundle fetcher {detail}"
    )
    raise TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError(message)
