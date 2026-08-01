# File:
#   - test_ticket_admission_async_public_key_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_async_public_key_provider.py
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
#   - Sequential caller-driven async public-key provider regressions.
# - Must-Not:
#   - Require CUDA, external services, hidden tasks, retries, caches, or
#     admission-policy changes.
# - Allows:
#   - Inputs: synthetic manifests, async providers, keys, and failures.
#   - Outputs: preflight, ordering, awaiting, resolution, and failure assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when concrete network transports, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact async provider behavior.
# - Summary:
#   - Explicit sequential async detached-key provider regressions.
# - Description:
#   - Proves canonical awaits occur without retained state or hidden scheduling.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-request defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Sequential caller-driven async public-key provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from accelerator.ticket_admission_telemetry_lineage_async_public_key_provider import (
    TicketAdmissionTelemetryLineageAsyncPublicKeyProviderError as AsyncProviderError,
)
from accelerator.ticket_admission_telemetry_lineage_async_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_async,
)
from accelerator.ticket_admission_telemetry_lineage_async_public_key_provider import (
    ticket_admission_telemetry_lineage_async_public_key_provider_id,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResult as PublicKeyResult,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResultKind as ResultKind,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust_manifest import (
    TicketAdmissionTelemetryLineageSignatureTrustManifestEntry as ManifestEntry,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust_manifest import (
    build_ticket_admission_telemetry_lineage_signature_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust_manifest import (
    ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_async_public_key_provider as async_types,
    )
    from accelerator import (
        ticket_admission_telemetry_lineage_signature_trust_manifest as manifest_types,
    )

    AsyncProvider = (
        async_types.TicketAdmissionTelemetryLineageAsyncPublicKeyProvider
    )
    from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
        TicketAdmissionTelemetryLineagePublicKeyProviderTrust as ProviderTrust,
    )
    from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
        TicketAdmissionTelemetryLineagePublicKeyRequest as PublicKeyRequest,
    )

    SignatureManifest = (
        manifest_types.TicketAdmissionTelemetryLineageSignatureTrustManifest
    )

PORT_ID = (
    "explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1"
)
PROVIDER_ID = "provider.test.async-public-keys"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_FIELD = b"public_key=b"
VENDOR_DETAIL = "vendor details must not cross the boundary"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_REQUESTS = 2


class _AsyncProvider:
    def __init__(self, results: dict[str, PublicKeyResult]) -> None:
        self._results: dict[str, PublicKeyResult] = results
        self.active_count: int = 0
        self.max_active_count: int = 0
        self.requests: list[PublicKeyRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []

    async def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
        self.active_count += 1
        self.max_active_count = max(self.max_active_count, self.active_count)
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        await asyncio.sleep(0)
        self.active_count -= 1
        return self._results[request.public_key_reference_id]


class _CancellingProvider:
    async def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
        del request
        raise asyncio.CancelledError


class _RaisingProvider:
    def __init__(self) -> None:
        self.requests: list[PublicKeyRequest] = []

    async def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
        self.requests.append(request)
        message = VENDOR_DETAIL
        raise RuntimeError(message)


def _resolved(public_key: bytes) -> PublicKeyResult:
    return PublicKeyResult(kind=ResultKind.RESOLVED, public_key=public_key)


def _provider(*, old_public_key: bytes = OLD_PUBLIC_KEY) -> _AsyncProvider:
    return _AsyncProvider({
        OLD_REFERENCE_ID: _resolved(old_public_key),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, None),
) -> ManifestEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return ManifestEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _manifest(*, same_key_id: bool = False) -> SignatureManifest:
    return build_ticket_admission_telemetry_lineage_signature_trust_manifest((
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(window=(GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID)),
    ))


def _run(
    manifest: SignatureManifest,
    provider: AsyncProvider,
    *,
    provider_id: str = PROVIDER_ID,
    max_requests: int = TWO_REQUESTS,
) -> ProviderTrust:
    return asyncio.run(
        resolve_ticket_admission_telemetry_lineage_signature_trust_async(
            manifest,
            provider,
            provider_id=provider_id,
            max_requests=max_requests,
        )
    )


def test_empty_manifest_is_stable_and_makes_no_provider_calls() -> None:
    provider = _AsyncProvider({})
    manifest = (
        build_ticket_admission_telemetry_lineage_signature_trust_manifest(())
    )

    resolved = _run(manifest, provider, max_requests=1)

    assert (
        ticket_admission_telemetry_lineage_async_public_key_provider_id()
        == PORT_ID
    )
    assert provider.requests == []
    assert resolved.request_count == 0
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            manifest
        )
    )


def test_coroutine_does_not_start_before_caller_runs_it() -> None:
    provider = _provider()
    coroutine = (
        resolve_ticket_admission_telemetry_lineage_signature_trust_async(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )
    )

    assert provider.requests == []
    resolved = asyncio.run(coroutine)

    assert resolved.request_count == TWO_REQUESTS


def test_requests_follow_composite_order_sequentially() -> None:
    provider = _provider()
    manifest = _manifest()

    resolved = _run(manifest, provider)

    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert tuple(request.request_index for request in provider.requests) == (
        0,
        1,
    )
    assert provider.max_active_count == 1
    assert len(set(provider.tasks)) == 1
    assert all(
        request.manifest_fingerprint
        == ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            manifest
        )
        for request in provider.requests
    )


def test_repeated_resolution_has_no_cache() -> None:
    provider = _provider()
    manifest = _manifest()

    first = _run(manifest, provider)
    second = _run(manifest, provider)

    assert first == second
    assert len(provider.requests) == TWO_REQUESTS * 2


def test_request_budget_fails_before_first_await() -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="request count exceeds"):
        _ = _run(_manifest(), provider, max_requests=1)

    assert provider.requests == []


@pytest.mark.parametrize("max_requests", [0, True])
def test_invalid_request_limit_fails_before_first_await(
    max_requests: int,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="positive integer"):
        _ = _run(_manifest(), provider, max_requests=max_requests)

    assert provider.requests == []


@pytest.mark.parametrize(
    "provider_id", ["bad provider", "", cast("str", object())]
)
def test_invalid_provider_identity_fails_before_first_await(
    provider_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="provider identity must use"):
        _ = _run(_manifest(), provider, provider_id=provider_id)

    assert provider.requests == []


def test_tampered_manifest_fails_before_first_await() -> None:
    provider = _provider()
    manifest = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(
        AsyncProviderError, match="manifest identity is unsupported"
    ):
        _ = _run(manifest, provider)

    assert provider.requests == []


@pytest.mark.parametrize("kind", [ResultKind.UNAVAILABLE, ResultKind.FAILED])
def test_typed_failure_stops_without_retry(kind: ResultKind) -> None:
    provider = _AsyncProvider({
        OLD_REFERENCE_ID: PublicKeyResult(kind=kind),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(
        AsyncProviderError,
        match=rf"provider returned {kind.value} at request index 0",
    ):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == 1


def test_provider_exception_is_wrapped_without_vendor_text() -> None:
    provider = _RaisingProvider()

    with pytest.raises(
        AsyncProviderError,
        match="provider raised during request index 0",
    ) as caught:
        _ = _run(_manifest(), provider)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(provider.requests) == 1


def test_cancellation_propagates_to_the_caller() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), _CancellingProvider())


def test_nonresolved_result_cannot_carry_public_key_bytes() -> None:
    provider = _AsyncProvider({
        OLD_REFERENCE_ID: PublicKeyResult(
            kind=ResultKind.FAILED,
            public_key=OLD_PUBLIC_KEY,
        ),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(AsyncProviderError, match="nonresolved provider result"):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == 1


def test_foreign_result_type_fails_closed() -> None:
    class ForeignProvider:
        async def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
            del request
            return cast("PublicKeyResult", cast("object", OLD_PUBLIC_KEY))

    with pytest.raises(AsyncProviderError, match="exact provider result type"):
        _ = _run(_manifest(), ForeignProvider())


def test_foreign_result_kind_fails_closed() -> None:
    result = PublicKeyResult(
        kind=cast("ResultKind", cast("object", "resolved")),
        public_key=OLD_PUBLIC_KEY,
    )
    provider = _AsyncProvider({
        OLD_REFERENCE_ID: result,
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(AsyncProviderError, match="exact provider result enum"):
        _ = _run(_manifest(), provider)


@pytest.mark.parametrize(
    "public_key",
    [None, cast("bytes | None", cast("object", bytearray(OLD_PUBLIC_KEY)))],
)
def test_resolved_result_requires_exact_bytes(
    public_key: bytes | None,
) -> None:
    provider = _AsyncProvider({
        OLD_REFERENCE_ID: PublicKeyResult(
            kind=ResultKind.RESOLVED,
            public_key=public_key,
        ),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(AsyncProviderError, match="exact public-key bytes"):
        _ = _run(_manifest(), provider)


def test_wrong_public_key_fails_manifest_fingerprint_check() -> None:
    provider = _provider(old_public_key=WRONG_PUBLIC_KEY)

    with pytest.raises(AsyncProviderError, match="fingerprint does not match"):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == TWO_REQUESTS


def test_empty_public_key_fails_trust_construction() -> None:
    provider = _provider(old_public_key=b"")

    with pytest.raises(AsyncProviderError, match="public key cannot be empty"):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == TWO_REQUESTS


def test_same_key_id_under_distinct_algorithms_is_preserved() -> None:
    provider = _provider()

    resolved = _run(_manifest(same_key_id=True), provider)

    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.trust.key_count == TWO_REQUESTS


def test_result_and_trust_hide_public_key_bytes() -> None:
    result = _resolved(OLD_PUBLIC_KEY)
    resolved = _run(_manifest(), _provider())

    result_repr = repr(result).encode("utf-8")
    trust_repr = repr(resolved).encode("utf-8")
    assert OLD_PUBLIC_KEY not in result_repr
    assert PUBLIC_KEY_FIELD not in result_repr
    assert OLD_PUBLIC_KEY not in trust_repr
    assert NEW_PUBLIC_KEY not in trust_repr
    assert PUBLIC_KEY_FIELD not in trust_repr


def test_result_kinds_remain_shared_and_stable() -> None:
    assert tuple(kind.value for kind in ResultKind) == (
        "resolved",
        "unavailable",
        "failed",
    )
