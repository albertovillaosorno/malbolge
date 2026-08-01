# File:
#   - test_ticket_admission_public_key_bundle_fetcher.py
# Path:
#   - tests/optimizer/test_ticket_admission_public_key_bundle_fetcher.py
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
#   - Explicit synchronous public-key bundle fetch-port regressions.
# - Must-Not:
#   - Require CUDA, HTTP, network access, credentials, retry, discovery,
#     certificates, PKI, secure cryptography, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic requests, fetch results, bundles, and tampering.
#   - Outputs: preflight, call-count, binding, load, and failure assertions.
#   - Side effects: in-process caller-supplied fetcher recording only.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact bundle-fetch boundary.
# - Summary:
#   - One-call transport-neutral public-key bundle fetch regressions.
# - Description:
#   - Proves exact expected metadata binds every fetched canonical bundle.
# - Usage:
#   - Runs without sockets, files, accelerator hardware, or external services.
# - Defaults:
#   - Uses two synthetic keys, 256 entries, and a 1 MiB byte limit.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Explicit transport-neutral detached public-key bundle fetch tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle as bundle,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

FetchError = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetcherError
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
FetchedBundle = fetch.TicketAdmissionTelemetryLineageFetchedPublicKeyBundle
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
_fetch_provider = (
    fetch.fetch_ticket_admission_telemetry_lineage_public_key_bundle_provider
)
_build_bundle = (
    bundle.build_ticket_admission_telemetry_lineage_public_key_bundle
)
_encode_bundle = (
    bundle.encode_ticket_admission_telemetry_lineage_public_key_bundle
)
_bundle_fingerprint = (
    bundle.ticket_admission_telemetry_lineage_public_key_bundle_fingerprint
)
_build_manifest = (
    manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)
_resolve_provider = (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider
)

FETCHER_ID = (
    "explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1"
)
PROVIDER_ID = "provider.test.remote-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
SOURCE_ID = "source.test.remote-key-service"
RESOURCE_ID = "resource.test.public-key-bundle.current"
OTHER_RESOURCE_ID = "resource.test.public-key-bundle.other"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
REPLACEMENT_PUBLIC_KEY = b"caller-owned-replacement-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_FIELD = b"public_key=b"
PAYLOAD_FIELD = b"payload=b"
PROVIDER_FIELD = b"provider="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2
TWO_FETCHES = 2


class _Fetcher:
    def __init__(
        self,
        callback: Callable[[FetchRequest], FetchResult],
    ) -> None:
        self._callback: Callable[[FetchRequest], FetchResult] = callback
        self.requests: list[FetchRequest] = []

    def __call__(self, request: FetchRequest) -> FetchResult:
        self.requests.append(request)
        return self._callback(request)


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_fingerprint: str | None = None,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
) -> BundleEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return BundleEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key=public_key,
        public_key_fingerprint=(
            _fingerprint(public_key)
            if public_key_fingerprint is None
            else public_key_fingerprint
        ),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _entries(
    *,
    old_public_key: bytes = OLD_PUBLIC_KEY,
    same_key_id: bool = False,
) -> tuple[BundleEntry, ...]:
    return (
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(public_key=old_public_key),
    )


def _bundle(
    *,
    entries: tuple[BundleEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> bundle.TicketAdmissionTelemetryLineagePublicKeyBundle:
    return _build_bundle(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _payload(
    *,
    entries: tuple[BundleEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> bytes:
    return _encode_bundle(_bundle(entries=entries, provider_id=provider_id))


def _request(  # ruff: ignore[too-many-arguments]
    *,
    expected_bundle: bundle.TicketAdmissionTelemetryLineagePublicKeyBundle
    | None = None,
    bundle_fingerprint: str | None = None,
    provider_id: str = PROVIDER_ID,
    resource_id: str = RESOURCE_ID,
    source_id: str = SOURCE_ID,
    max_bytes: int = fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES,
    max_entries: int = (
        fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
    ),
) -> FetchRequest:
    built = _bundle() if expected_bundle is None else expected_bundle
    return FetchRequest(
        bundle_fingerprint=(
            _bundle_fingerprint(built)
            if bundle_fingerprint is None
            else bundle_fingerprint
        ),
        max_bytes=max_bytes,
        max_entries=max_entries,
        provider_id=provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _fetched(payload: bytes) -> FetchResult:
    return FetchResult(kind=FetchKind.FETCHED, payload=payload)


def _constant_fetcher(result: FetchResult) -> _Fetcher:
    def callback(request: FetchRequest) -> FetchResult:
        _ = request
        return result

    return _Fetcher(callback)


def _fetcher(payload: bytes | None = None) -> _Fetcher:
    selected = _payload() if payload is None else payload
    return _constant_fetcher(_fetched(selected))


def _fetch(
    fetcher: _Fetcher,
    request: FetchRequest | None = None,
) -> FetchedBundle:
    return _fetch_provider(fetcher, _request() if request is None else request)


def _manifest(
    *,
    old_public_key: bytes = OLD_PUBLIC_KEY,
    same_key_id: bool = False,
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    return _build_manifest((
        ManifestEntry(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
        ManifestEntry(
            algorithm_id=OLD_ALGORITHM_ID,
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
            public_key_fingerprint=_fingerprint(old_public_key),
            public_key_id=OLD_KEY_ID,
            public_key_reference_id=OLD_REFERENCE_ID,
        ),
    ))


def test_fetcher_identity_result_values_and_defaults_are_stable() -> None:
    assert (
        fetch.ticket_admission_telemetry_lineage_public_key_bundle_fetcher_id()
        == FETCHER_ID
    )
    assert tuple(kind.value for kind in FetchKind) == (
        "fetched",
        "unavailable",
        "failed",
    )
    assert (
        fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
        == bundle.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES
    )
    assert (
        fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        == bundle.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES
    )


def test_public_request_validator_returns_same_immutable_request() -> None:
    request = _request()

    validated = fetch.validate_ticket_admission_public_key_bundle_fetch_request(
        request
    )

    assert validated is request


def test_public_result_materializer_requires_no_transport_call() -> None:
    request = _request()
    result = _fetched(_payload())

    loaded = fetch.materialize_ticket_admission_public_key_bundle_fetch_result(
        request,
        result,
    )

    assert loaded.bundle_fingerprint == request.bundle_fingerprint
    assert loaded.provider_id == request.provider_id
    assert loaded.resource_id == request.resource_id
    assert loaded.source_id == request.source_id
    assert loaded.key_count == TWO_KEYS


def test_exact_request_makes_one_call_and_returns_bound_metadata() -> None:
    transport = _fetcher()
    request = _request()

    loaded = _fetch(transport, request)

    assert transport.requests == [request]
    assert transport.requests[0] is request
    assert loaded.bundle_fingerprint == request.bundle_fingerprint
    assert loaded.byte_count == len(_payload())
    assert loaded.key_count == TWO_KEYS
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.resource_id == RESOURCE_ID
    assert loaded.source_id == SOURCE_ID
    assert loaded.provider.key_count == TWO_KEYS


def test_empty_bundle_still_uses_one_explicit_fetch() -> None:
    empty = _bundle(entries=())
    transport = _fetcher(_encode_bundle(empty))

    loaded = _fetch(transport, _request(expected_bundle=empty))

    assert len(transport.requests) == 1
    assert loaded.key_count == 0
    assert loaded.provider.entries == ()


def test_fetched_provider_builds_manifest_bound_trust() -> None:
    loaded = _fetch(_fetcher())

    resolved = _resolve_provider(
        _manifest(),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_KEYS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.trust.key_count == TWO_KEYS


def test_repeated_explicit_fetch_has_no_cache() -> None:
    first_payload = _payload()
    replacement_entries = _entries(old_public_key=REPLACEMENT_PUBLIC_KEY)
    second_bundle = _bundle(entries=replacement_entries)
    payloads = [first_payload, _encode_bundle(second_bundle)]

    def next_payload(request: FetchRequest) -> FetchResult:
        _ = request
        return _fetched(payloads.pop(0))

    transport = _Fetcher(next_payload)

    first = _fetch(transport)
    second = _fetch(transport, _request(expected_bundle=second_bundle))

    assert len(transport.requests) == TWO_FETCHES
    assert first.bundle_fingerprint != second.bundle_fingerprint
    assert first.provider.entries[0].public_key == OLD_PUBLIC_KEY
    assert second.provider.entries[0].public_key == REPLACEMENT_PUBLIC_KEY


def test_same_key_id_under_distinct_algorithms_fetches_and_resolves() -> None:
    entries = _entries(same_key_id=True)
    built = _bundle(entries=entries)
    loaded = _fetch(
        _fetcher(_encode_bundle(built)),
        _request(expected_bundle=built),
    )

    resolved = _resolve_provider(
        _manifest(same_key_id=True),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)


def test_fetch_result_and_loaded_repr_hide_bytes_and_provider() -> None:
    payload = _payload()
    result = _fetched(payload)
    loaded = _fetch(_fetcher(payload))
    result_repr = repr(result).encode("utf-8")
    loaded_repr = repr(loaded).encode("utf-8")

    assert payload not in result_repr
    assert PAYLOAD_FIELD not in result_repr
    assert OLD_PUBLIC_KEY not in loaded_repr
    assert NEW_PUBLIC_KEY not in loaded_repr
    assert PUBLIC_KEY_FIELD not in loaded_repr
    assert PROVIDER_FIELD not in loaded_repr


def test_foreign_request_type_fails_before_fetch() -> None:
    transport = _fetcher()

    with pytest.raises(FetchError, match="exact fetch request type"):
        _ = _fetch_provider(transport, cast("FetchRequest", object()))

    assert transport.requests == []


@pytest.mark.parametrize(
    "bundle_fingerprint",
    [
        "",
        "bundle.test.fingerprint",
        "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:ABC",
        cast("str", object()),
    ],
)
def test_malformed_fingerprint_fails_before_fetch(
    bundle_fingerprint: str,
) -> None:
    transport = _fetcher()
    request = _request(bundle_fingerprint=bundle_fingerprint)

    with pytest.raises(FetchError, match="bundle fingerprint is malformed"):
        _ = _fetch(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("provider_id", "", "provider identity must use"),
        ("provider_id", "bad provider", "provider identity must use"),
        ("resource_id", "", "resource identity must use"),
        ("resource_id", "bad resource", "resource identity must use"),
        ("source_id", "", "source identity must use"),
        ("source_id", "bad source", "source identity must use"),
    ],
)
def test_identifier_preflight_fails_before_fetch(
    field: str,
    value: str,
    match: str,
) -> None:
    transport = _fetcher()
    request = replace(_request(), **{field: value})

    with pytest.raises(FetchError, match=match):
        _ = _fetch(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize("max_bytes", [0, True])
def test_byte_limit_requires_positive_exact_integer_before_fetch(
    max_bytes: int,
) -> None:
    transport = _fetcher()
    request = replace(_request(), max_bytes=max_bytes)

    with pytest.raises(
        FetchError, match="byte limit must be a positive integer"
    ):
        _ = _fetch(transport, request)

    assert transport.requests == []


def test_byte_limit_cannot_exceed_supported_maximum() -> None:
    transport = _fetcher()
    request = replace(
        _request(),
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
            + 1
        ),
    )

    with pytest.raises(
        FetchError, match="byte limit exceeds supported maximum"
    ):
        _ = _fetch(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize("max_entries", [0, True])
def test_entry_limit_requires_positive_exact_integer_before_fetch(
    max_entries: int,
) -> None:
    transport = _fetcher()
    request = replace(_request(), max_entries=max_entries)

    with pytest.raises(
        FetchError, match="entry limit must be a positive integer"
    ):
        _ = _fetch(transport, request)

    assert transport.requests == []


def test_entry_limit_cannot_exceed_supported_maximum() -> None:
    transport = _fetcher()
    request = replace(
        _request(),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
            + 1
        ),
    )

    with pytest.raises(
        FetchError, match="entry limit exceeds supported maximum"
    ):
        _ = _fetch(transport, request)

    assert transport.requests == []


def test_exact_payload_byte_limit_is_accepted() -> None:
    payload = _payload()
    request = replace(_request(), max_bytes=len(payload))

    loaded = _fetch(_fetcher(payload), request)

    assert loaded.byte_count == len(payload)


def test_foreign_result_type_fails_closed() -> None:
    transport = _constant_fetcher(cast("FetchResult", object()))

    with pytest.raises(FetchError, match="exact fetch result type"):
        _ = _fetch(transport)

    assert len(transport.requests) == 1


def test_foreign_result_enum_fails_closed() -> None:
    result = FetchResult(
        kind=cast("FetchKind", cast("object", "fetched")),
        payload=_payload(),
    )
    transport = _constant_fetcher(result)

    with pytest.raises(FetchError, match="exact fetch result enum"):
        _ = _fetch(transport)


@pytest.mark.parametrize("kind", [FetchKind.UNAVAILABLE, FetchKind.FAILED])
def test_nonfetched_result_fails_closed(kind: FetchKind) -> None:
    transport = _constant_fetcher(FetchResult(kind=kind))

    with pytest.raises(
        FetchError, match=f"bundle fetcher returned {kind.value}"
    ):
        _ = _fetch(transport)


@pytest.mark.parametrize("kind", [FetchKind.UNAVAILABLE, FetchKind.FAILED])
def test_nonfetched_result_cannot_contain_bytes(kind: FetchKind) -> None:
    transport = _constant_fetcher(FetchResult(kind=kind, payload=_payload()))

    with pytest.raises(FetchError, match="nonfetched result cannot contain"):
        _ = _fetch(transport)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (None, "requires exact payload bytes"),
        (cast("bytes", cast("object", bytearray(b"{}\n"))), "requires exact"),
        (b"", "fetched payload cannot be empty"),
    ],
)
def test_fetched_payload_type_and_presence_are_exact(
    payload: bytes | None,
    match: str,
) -> None:
    transport = _constant_fetcher(
        FetchResult(kind=FetchKind.FETCHED, payload=payload)
    )

    with pytest.raises(FetchError, match=match):
        _ = _fetch(transport)


def test_fetched_payload_respects_requested_byte_limit() -> None:
    payload = _payload()
    request = replace(_request(), max_bytes=len(payload) - 1)

    with pytest.raises(FetchError, match="exceeds requested byte limit"):
        _ = _fetch(_fetcher(payload), request)


def test_fetcher_exception_is_wrapped_without_vendor_text() -> None:
    vendor_text = "vendor-secret-endpoint-detail"

    def raise_vendor(request: FetchRequest) -> FetchResult:
        _ = request
        raise RuntimeError(vendor_text)

    transport = _Fetcher(raise_vendor)

    with pytest.raises(
        FetchError, match="raised during explicit fetch"
    ) as caught:
        _ = _fetch(transport)

    assert vendor_text not in str(caught.value)
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json\n",
        b'{"bundle_id":"bad"}\n',
        _payload().rstrip(b"\n"),
    ],
)
def test_invalid_or_noncanonical_bundle_is_wrapped(payload: bytes) -> None:
    with pytest.raises(
        FetchError, match="cannot decode fetched public-key bundle"
    ):
        _ = _fetch(_fetcher(payload))


def test_entry_limit_is_applied_during_decode() -> None:
    request = replace(_request(), max_entries=1)

    with pytest.raises(
        FetchError, match="cannot decode fetched public-key bundle"
    ):
        _ = _fetch(_fetcher(), request)


def test_expected_fingerprint_mismatch_fails_closed() -> None:
    other = _bundle(entries=_entries(old_public_key=REPLACEMENT_PUBLIC_KEY))
    request = _request(expected_bundle=other)

    with pytest.raises(FetchError, match="fingerprint does not match request"):
        _ = _fetch(_fetcher(), request)


def test_expected_provider_identity_mismatch_fails_closed() -> None:
    other_bundle = _bundle(provider_id=OTHER_PROVIDER_ID)
    transport = _fetcher(_encode_bundle(other_bundle))
    request = _request(
        expected_bundle=other_bundle,
        provider_id=PROVIDER_ID,
    )

    with pytest.raises(
        FetchError, match="provider identity does not match request"
    ):
        _ = _fetch(transport, request)


def test_resource_identity_is_metadata_not_transport_discovery() -> None:
    request = replace(_request(), resource_id=OTHER_RESOURCE_ID)
    transport = _fetcher()

    loaded = _fetch(transport, request)

    assert transport.requests == [request]
    assert loaded.resource_id == OTHER_RESOURCE_ID
    assert loaded.source_id == SOURCE_ID
