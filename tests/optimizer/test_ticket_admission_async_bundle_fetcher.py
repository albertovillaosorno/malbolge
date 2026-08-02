# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Caller-driven async public-key bundle fetch-port regressions.
# - Must-Not:
#   - Require CUDA, HTTP, sockets, credentials, hidden tasks, retry, discovery,
#     certificates, PKI, secure cryptography, or policy changes.
# - Allows:
#   - Inputs: synthetic requests, async fetchers, bundles, and failures.
#   - Outputs: preflight, awaiting, cancellation, binding, and load assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when native async HTTPS, external credentials, hosted APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact async bundle-fetch behavior.
# - Summary:
#   - One-await transport-neutral public-key bundle fetch regressions.
# - Description:
#   - Proves async fetching adds no tasks, retry, cache, or duplicate
#     validation.
# - Usage:
#   - Runs without pytest async plugins, files, sockets, or accelerator
#     hardware.
# - Defaults:
#   - Uses two synthetic keys, 256 entries, and a 1 MiB byte limit.
#

"""Caller-driven async detached public-key bundle fetch tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

from accelerator import (
    ticket_admission_telemetry_lineage_async_bundle_fetcher as async_fetch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle as bundle,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)

# jig-ignore-next-line: indivisible reviewed identifier
from accelerator.ticket_admission_telemetry_lineage_async_bundle_fetcher import (
    fetch_ticket_admission_public_key_bundle_provider_async as _fetch_async,
)

# jig-ignore-next-line: indivisible reviewed identifier
from accelerator.ticket_admission_telemetry_lineage_async_bundle_fetcher import (
    ticket_admission_async_public_key_bundle_fetcher_id as _async_fetcher_id,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


AsyncFetchError = (
    async_fetch.TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcherError
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
FetchResult = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResult
FetchKind = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchResultKind
FetchedBundle = fetch.TicketAdmissionTelemetryLineageFetchedPublicKeyBundle
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
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

ASYNC_FETCHER_ID = (
    "explicit-async-ticket-admission-telemetry-lineage-"
    "public-key-bundle-fetcher-v1"
)
PROVIDER_ID = "provider.test.async-remote-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
SOURCE_ID = "source.test.async-key-service"
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
VENDOR_DETAIL = "vendor endpoint detail must not cross the boundary"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2
TWO_FETCHES = 2


class _AsyncFetcher:
    def __init__(
        self,
        callback: Callable[[FetchRequest], FetchResult],
        *,
        suspend: bool = True,
    ) -> None:
        self._callback: Callable[[FetchRequest], FetchResult] = callback
        self._suspend: bool = suspend
        self.requests: list[FetchRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []
        self.task_counts: list[int] = []
        self.active_count: int = 0
        self.max_active_count: int = 0

    async def __call__(self, request: FetchRequest) -> FetchResult:
        self.active_count += 1
        self.max_active_count = max(self.max_active_count, self.active_count)
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        self.task_counts.append(len(asyncio.all_tasks()))
        if self._suspend:
            await asyncio.sleep(0)
        self.active_count -= 1
        return self._callback(request)


class _CancellingFetcher:
    async def __call__(self, request: FetchRequest) -> FetchResult:
        _ = request
        raise asyncio.CancelledError


class _RaisingFetcher:
    def __init__(self) -> None:
        self.requests: list[FetchRequest] = []

    async def __call__(self, request: FetchRequest) -> FetchResult:
        self.requests.append(request)
        raise RuntimeError(VENDOR_DETAIL)


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
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
        public_key_fingerprint=_fingerprint(public_key),
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
    # jig-ignore-next-line: indivisible reviewed identifier
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


def _constant_fetcher(
    result: FetchResult, *, suspend: bool = True
) -> _AsyncFetcher:
    def callback(request: FetchRequest) -> FetchResult:
        _ = request
        return result

    return _AsyncFetcher(callback, suspend=suspend)


def _fetcher(
    payload: bytes | None = None, *, suspend: bool = True
) -> _AsyncFetcher:
    selected = _payload() if payload is None else payload
    return _constant_fetcher(_fetched(selected), suspend=suspend)


def _run(
    # jig-ignore-next-line: indivisible reviewed identifier
    fetcher: async_fetch.TicketAdmissionTelemetryLineageAsyncPublicKeyBundleFetcher,
    request: FetchRequest | None = None,
) -> FetchedBundle:
    return asyncio.run(
        _fetch_async(fetcher, _request() if request is None else request)
    )


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


def test_async_fetcher_identity_is_stable() -> None:
    assert _async_fetcher_id() == ASYNC_FETCHER_ID


def test_coroutine_does_not_start_before_caller_runs_it() -> None:
    transport = _fetcher()
    coroutine = _fetch_async(transport, _request())

    assert transport.requests == []
    loaded = asyncio.run(coroutine)

    assert loaded.key_count == TWO_KEYS
    assert len(transport.requests) == 1


def test_exact_request_makes_one_await_in_same_task() -> None:
    transport = _fetcher()
    request = _request()

    loaded = _run(transport, request)

    assert transport.requests == [request]
    assert transport.requests[0] is request
    assert transport.max_active_count == 1
    assert len(set(transport.tasks)) == 1
    assert transport.task_counts == [1]
    assert loaded.bundle_fingerprint == request.bundle_fingerprint
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.resource_id == RESOURCE_ID
    assert loaded.source_id == SOURCE_ID


def test_fetcher_controls_whether_the_await_suspends() -> None:
    transport = _fetcher(suspend=False)

    loaded = _run(transport)

    assert loaded.key_count == TWO_KEYS
    assert len(transport.requests) == 1
    assert transport.task_counts == [1]


def test_empty_bundle_still_uses_one_explicit_await() -> None:
    empty = _bundle(entries=())
    transport = _fetcher(_encode_bundle(empty))

    loaded = _run(transport, _request(expected_bundle=empty))

    assert len(transport.requests) == 1
    assert loaded.key_count == 0
    assert loaded.provider.entries == ()


def test_fetched_provider_builds_manifest_bound_trust() -> None:
    loaded = _run(_fetcher())

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


def test_repeated_explicit_await_has_no_cache() -> None:
    first_payload = _payload()
    replacement_entries = _entries(old_public_key=REPLACEMENT_PUBLIC_KEY)
    second_bundle = _bundle(entries=replacement_entries)
    payloads = [first_payload, _encode_bundle(second_bundle)]

    def next_payload(request: FetchRequest) -> FetchResult:
        _ = request
        return _fetched(payloads.pop(0))

    transport = _AsyncFetcher(next_payload)

    first = _run(transport)
    second = _run(transport, _request(expected_bundle=second_bundle))

    assert len(transport.requests) == TWO_FETCHES
    assert first.bundle_fingerprint != second.bundle_fingerprint
    assert first.provider.entries[0].public_key == OLD_PUBLIC_KEY
    assert second.provider.entries[0].public_key == REPLACEMENT_PUBLIC_KEY


def test_same_key_id_under_distinct_algorithms_is_preserved() -> None:
    entries = _entries(same_key_id=True)
    built = _bundle(entries=entries)
    loaded = _run(
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


def test_resource_identity_remains_transport_metadata() -> None:
    request = replace(_request(), resource_id=OTHER_RESOURCE_ID)
    transport = _fetcher()

    loaded = _run(transport, request)

    assert transport.requests == [request]
    assert loaded.resource_id == OTHER_RESOURCE_ID
    assert loaded.source_id == SOURCE_ID


def test_foreign_request_type_fails_before_first_await() -> None:
    transport = _fetcher()

    with pytest.raises(
        AsyncFetchError, match="invalid async public-key bundle"
    ):
        _ = _run(transport, cast("FetchRequest", object()))

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
def test_malformed_fingerprint_fails_before_first_await(
    bundle_fingerprint: str,
) -> None:
    transport = _fetcher()
    request = _request(bundle_fingerprint=bundle_fingerprint)

    with pytest.raises(
        AsyncFetchError, match="invalid async public-key bundle"
    ):
        _ = _run(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider_id", "bad provider"),
        ("resource_id", "bad resource"),
        ("source_id", "bad source"),
    ],
)
def test_invalid_identity_fails_before_first_await(
    field: str,
    value: str,
) -> None:
    transport = _fetcher()
    request = replace(_request(), **{field: value})

    with pytest.raises(
        AsyncFetchError, match="invalid async public-key bundle"
    ):
        _ = _run(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_bytes", 0),
        ("max_bytes", True),
        ("max_entries", 0),
        ("max_entries", True),
    ],
)
def test_invalid_limit_fails_before_first_await(
    field: str,
    value: int,
) -> None:
    transport = _fetcher()
    request = replace(_request(), **{field: value})

    with pytest.raises(
        AsyncFetchError, match="invalid async public-key bundle"
    ):
        _ = _run(transport, request)

    assert transport.requests == []


def test_limit_above_supported_maximum_fails_before_first_await() -> None:
    transport = _fetcher()
    request = replace(
        _request(),
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
            + 1
        ),
    )

    with pytest.raises(
        AsyncFetchError, match="invalid async public-key bundle"
    ):
        _ = _run(transport, request)

    assert transport.requests == []


@pytest.mark.parametrize("kind", [FetchKind.UNAVAILABLE, FetchKind.FAILED])
def test_typed_nonfetched_result_fails_without_retry(kind: FetchKind) -> None:
    transport = _constant_fetcher(FetchResult(kind=kind))

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(transport)

    assert len(transport.requests) == 1


def test_foreign_result_type_fails_closed() -> None:
    transport = _constant_fetcher(cast("FetchResult", object()))

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(transport)

    assert len(transport.requests) == 1


def test_foreign_result_enum_fails_closed() -> None:
    result = FetchResult(
        kind=cast("FetchKind", cast("object", "fetched")),
        payload=_payload(),
    )
    transport = _constant_fetcher(result)

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(transport)


def test_nonfetched_result_cannot_carry_bytes() -> None:
    result = FetchResult(kind=FetchKind.FAILED, payload=_payload())

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_constant_fetcher(result))


@pytest.mark.parametrize(
    "payload",
    [
        None,
        b"",
        cast("bytes | None", cast("object", bytearray(b"{}\n"))),
    ],
)
def test_fetched_result_requires_exact_nonempty_bytes(
    payload: bytes | None,
) -> None:
    result = FetchResult(kind=FetchKind.FETCHED, payload=payload)

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_constant_fetcher(result))


def test_fetched_payload_respects_requested_byte_limit() -> None:
    payload = _payload()
    request = replace(_request(), max_bytes=len(payload) - 1)

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_fetcher(payload), request)


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json\n",
        b'{"bundle_id":"bad"}\n',
        _payload().rstrip(b"\n"),
    ],
)
def test_invalid_or_noncanonical_bundle_fails_closed(payload: bytes) -> None:
    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_fetcher(payload))


def test_entry_limit_is_applied_during_result_processing() -> None:
    request = replace(_request(), max_entries=1)

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_fetcher(), request)


def test_expected_fingerprint_mismatch_fails_closed() -> None:
    other = _bundle(entries=_entries(old_public_key=REPLACEMENT_PUBLIC_KEY))
    request = _request(expected_bundle=other)

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(_fetcher(), request)


def test_expected_provider_identity_mismatch_fails_closed() -> None:
    other_bundle = _bundle(provider_id=OTHER_PROVIDER_ID)
    transport = _fetcher(_encode_bundle(other_bundle))
    request = _request(
        expected_bundle=other_bundle,
        provider_id=PROVIDER_ID,
    )

    with pytest.raises(AsyncFetchError, match="cannot process async fetched"):
        _ = _run(transport, request)


def test_fetcher_exception_is_wrapped_without_vendor_text() -> None:
    transport = _RaisingFetcher()

    with pytest.raises(
        AsyncFetchError,
        match="async bundle fetcher raised during explicit fetch",
    ) as caught:
        _ = _run(transport)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(transport.requests) == 1


def test_cancellation_propagates_to_the_caller() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_CancellingFetcher())


def test_shared_fetch_result_and_loaded_provider_hide_bytes() -> None:
    payload = _payload()
    result = _fetched(payload)
    loaded = _run(_constant_fetcher(result))

    assert payload not in repr(result).encode("utf-8")
    assert OLD_PUBLIC_KEY not in repr(loaded).encode("utf-8")
    assert NEW_PUBLIC_KEY not in repr(loaded).encode("utf-8")
