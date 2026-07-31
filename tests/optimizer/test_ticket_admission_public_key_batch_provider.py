# File:
#   - test_ticket_admission_public_key_batch_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_public_key_batch_provider.py
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
#   - Caller-controlled async batch public-key provider regressions.
# - Must-Not:
#   - Require CUDA, external services, library-owned tasks, retries, caches, or
#     admission-policy changes.
# - Allows:
#   - Inputs: synthetic manifests, batch providers, keys, and failures.
#   - Outputs: batch, concurrency, cardinality, resolution, and failure checks.
#   - Side effects: caller-owned standard-library event loops and tasks only.
# - Split-When:
#   - Split when built-in services, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact async batch behavior.
# - Summary:
#   - Explicit caller-controlled detached-key batch regressions.
# - Description:
#   - Proves one canonical batch await delegates scheduling to the provider.
# - Usage:
#   - Runs without pytest async plugins or external key services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and 256-request defaults.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Caller-controlled async batch public-key provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from accelerator.ticket_admission_telemetry_lineage_public_key_batch_provider import (
    TicketAdmissionTelemetryLineagePublicKeyBatchProviderError as BatchProviderError,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_batch_provider import (
    TicketAdmissionTelemetryLineagePublicKeyBatchResult as BatchResult,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_batch_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_batch_provider import (
    ticket_admission_telemetry_lineage_public_key_batch_provider_id,
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
        ticket_admission_telemetry_lineage_public_key_batch_provider as batch_types,
    )
    from accelerator import (
        ticket_admission_telemetry_lineage_signature_trust_manifest as manifest_types,
    )
    BatchRequest = (
        batch_types.TicketAdmissionTelemetryLineagePublicKeyBatchRequest
    )
    from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
        TicketAdmissionTelemetryLineagePublicKeyProviderTrust as ProviderTrust,
    )

    BatchProvider = (
        batch_types.TicketAdmissionTelemetryLineagePublicKeyBatchProvider
    )
    SignatureManifest = (
        manifest_types.TicketAdmissionTelemetryLineageSignatureTrustManifest
    )

PORT_ID_PREFIX = "explicit-async-batch-ticket-admission-"
PORT_ID_SUFFIX = "telemetry-lineage-public-key-provider-v1"
PORT_ID = f"{PORT_ID_PREFIX}{PORT_ID_SUFFIX}"
PROVIDER_ID = "provider.test.batch-public-keys"
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
VENDOR_DETAIL = "vendor batch details must not cross the boundary"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_REQUESTS = 2
TWO_BATCH_CALLS = 2


class _BatchProvider:
    def __init__(
        self,
        results: dict[str, PublicKeyResult],
        *,
        concurrent: bool = False,
    ) -> None:
        self._results: dict[str, PublicKeyResult] = results
        self._concurrent: bool = concurrent
        self.active_count: int = 0
        self.call_count: int = 0
        self.max_active_count: int = 0
        self.requests: list[BatchRequest] = []

    async def _resolve(self, reference_id: str) -> PublicKeyResult:
        self.active_count += 1
        self.max_active_count = max(self.max_active_count, self.active_count)
        await asyncio.sleep(0)
        self.active_count -= 1
        return self._results[reference_id]

    async def __call__(self, request: BatchRequest) -> BatchResult:
        self.call_count += 1
        self.requests.append(request)
        references = tuple(
            item.public_key_reference_id for item in request.requests
        )
        if self._concurrent:
            results = await asyncio.gather(
                *(self._resolve(reference) for reference in references)
            )
        else:
            results = [
                await self._resolve(reference) for reference in references
            ]
        return BatchResult(results=tuple(results))


class _CancellingProvider:
    async def __call__(self, request: BatchRequest) -> BatchResult:
        del request
        raise asyncio.CancelledError


class _RaisingProvider:
    def __init__(self) -> None:
        self.call_count: int = 0

    async def __call__(self, request: BatchRequest) -> BatchResult:
        del request
        self.call_count += 1
        message = VENDOR_DETAIL
        raise RuntimeError(message)


def _resolved(public_key: bytes) -> PublicKeyResult:
    return PublicKeyResult(kind=ResultKind.RESOLVED, public_key=public_key)


def _provider(
    *,
    old_public_key: bytes = OLD_PUBLIC_KEY,
    concurrent: bool = False,
) -> _BatchProvider:
    return _BatchProvider(
        {
            OLD_REFERENCE_ID: _resolved(old_public_key),
            NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
        },
        concurrent=concurrent,
    )


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
    provider: BatchProvider,
    *,
    provider_id: str = PROVIDER_ID,
    max_requests: int = TWO_REQUESTS,
) -> ProviderTrust:
    return asyncio.run(
        resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch(
            manifest,
            provider,
            provider_id=provider_id,
            max_requests=max_requests,
        )
    )


def test_empty_manifest_is_stable_and_makes_no_batch_call() -> None:
    provider = _BatchProvider({})
    manifest = (
        build_ticket_admission_telemetry_lineage_signature_trust_manifest(())
    )

    resolved = _run(manifest, provider, max_requests=1)

    assert (
        ticket_admission_telemetry_lineage_public_key_batch_provider_id()
        == PORT_ID
    )
    assert provider.call_count == 0
    assert provider.requests == []
    assert resolved.request_count == 0
    assert resolved.trust.key_count == 0


def test_coroutine_does_not_start_before_caller_runs_it() -> None:
    provider = _provider()
    coroutine = (
        resolve_ticket_admission_telemetry_lineage_signature_trust_async_batch(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )
    )

    assert provider.call_count == 0
    resolved = asyncio.run(coroutine)

    assert resolved.request_count == TWO_REQUESTS
    assert provider.call_count == 1


def test_one_batch_contains_canonical_composite_order() -> None:
    provider = _provider()
    manifest = _manifest()

    resolved = _run(manifest, provider)

    assert provider.call_count == 1
    assert len(provider.requests) == 1
    batch = provider.requests[0]
    assert batch.provider_id == PROVIDER_ID
    assert batch.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            manifest
        )
    )
    assert tuple(request.request_index for request in batch.requests) == (0, 1)
    assert tuple(request.algorithm_id for request in batch.requests) == (
        OLD_ALGORITHM_ID,
        NEW_ALGORITHM_ID,
    )
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)


def test_provider_controls_concurrency_inside_one_batch() -> None:
    provider = _provider(concurrent=True)

    resolved = _run(_manifest(), provider)

    assert resolved.request_count == TWO_REQUESTS
    assert provider.call_count == 1
    assert provider.max_active_count == TWO_REQUESTS


def test_provider_may_resolve_batch_sequentially() -> None:
    provider = _provider(concurrent=False)

    resolved = _run(_manifest(), provider)

    assert resolved.request_count == TWO_REQUESTS
    assert provider.call_count == 1
    assert provider.max_active_count == 1


def test_repeated_resolution_has_no_cache() -> None:
    provider = _provider()
    manifest = _manifest()

    first = _run(manifest, provider)
    second = _run(manifest, provider)

    assert first == second
    assert provider.call_count == TWO_BATCH_CALLS


def test_request_budget_fails_before_batch_call() -> None:
    provider = _provider()

    with pytest.raises(BatchProviderError, match="request count exceeds"):
        _ = _run(_manifest(), provider, max_requests=1)

    assert provider.call_count == 0


@pytest.mark.parametrize("max_requests", [0, True])
def test_invalid_request_limit_fails_before_batch_call(
    max_requests: int,
) -> None:
    provider = _provider()

    with pytest.raises(BatchProviderError, match="positive integer"):
        _ = _run(_manifest(), provider, max_requests=max_requests)

    assert provider.call_count == 0


@pytest.mark.parametrize(
    "provider_id", ["bad provider", "", cast("str", object())]
)
def test_invalid_provider_identity_fails_before_batch_call(
    provider_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(BatchProviderError, match="provider identity must use"):
        _ = _run(_manifest(), provider, provider_id=provider_id)

    assert provider.call_count == 0


def test_tampered_manifest_fails_before_batch_call() -> None:
    provider = _provider()
    manifest = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(
        BatchProviderError, match="manifest identity is unsupported"
    ):
        _ = _run(manifest, provider)

    assert provider.call_count == 0


class _FixedBatchProvider:
    def __init__(self, result: object) -> None:
        self._result: object = result
        self.call_count: int = 0

    async def __call__(self, request: BatchRequest) -> BatchResult:
        del request
        self.call_count += 1
        return cast("BatchResult", self._result)


def test_foreign_batch_result_type_fails_closed() -> None:
    provider = _FixedBatchProvider(object())

    with pytest.raises(BatchProviderError, match="exact batch result type"):
        _ = _run(_manifest(), provider)

    assert provider.call_count == 1


def test_batch_results_require_exact_tuple_type() -> None:
    foreign = BatchResult(
        results=cast(
            "tuple[PublicKeyResult, ...]",
            cast(
                "object", [_resolved(OLD_PUBLIC_KEY), _resolved(NEW_PUBLIC_KEY)]
            ),
        )
    )
    provider = _FixedBatchProvider(foreign)

    with pytest.raises(BatchProviderError, match="exact tuple type"):
        _ = _run(_manifest(), provider)


def test_batch_result_count_must_match_request_count() -> None:
    provider = _FixedBatchProvider(
        BatchResult(results=(_resolved(OLD_PUBLIC_KEY),))
    )

    with pytest.raises(BatchProviderError, match="count does not match"):
        _ = _run(_manifest(), provider)


@pytest.mark.parametrize("kind", [ResultKind.UNAVAILABLE, ResultKind.FAILED])
def test_typed_item_failure_stops_after_single_batch_call(
    kind: ResultKind,
) -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                PublicKeyResult(kind=kind),
                _resolved(NEW_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(
        BatchProviderError,
        match=rf"provider returned {kind.value} at index 0",
    ):
        _ = _run(_manifest(), provider)

    assert provider.call_count == 1


def test_nonresolved_item_cannot_carry_public_key_bytes() -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                PublicKeyResult(
                    kind=ResultKind.FAILED,
                    public_key=OLD_PUBLIC_KEY,
                ),
                _resolved(NEW_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(
        BatchProviderError, match="nonresolved result has bytes"
    ):
        _ = _run(_manifest(), provider)


def test_foreign_item_result_type_fails_closed() -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                cast("PublicKeyResult", cast("object", OLD_PUBLIC_KEY)),
                _resolved(NEW_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(BatchProviderError, match="must use the exact type"):
        _ = _run(_manifest(), provider)


def test_foreign_item_result_kind_fails_closed() -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                PublicKeyResult(
                    kind=cast("ResultKind", cast("object", "resolved")),
                    public_key=OLD_PUBLIC_KEY,
                ),
                _resolved(NEW_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(BatchProviderError, match="must use the exact enum"):
        _ = _run(_manifest(), provider)


@pytest.mark.parametrize(
    "public_key",
    [None, cast("bytes | None", cast("object", bytearray(OLD_PUBLIC_KEY)))],
)
def test_resolved_item_requires_exact_bytes(public_key: bytes | None) -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                PublicKeyResult(
                    kind=ResultKind.RESOLVED,
                    public_key=public_key,
                ),
                _resolved(NEW_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(BatchProviderError, match="needs exact bytes"):
        _ = _run(_manifest(), provider)


def test_wrong_public_key_fails_manifest_fingerprint_check() -> None:
    provider = _provider(old_public_key=WRONG_PUBLIC_KEY)

    with pytest.raises(BatchProviderError, match="fingerprint does not match"):
        _ = _run(_manifest(), provider)

    assert provider.call_count == 1


def test_reversed_positional_results_fail_closed() -> None:
    provider = _FixedBatchProvider(
        BatchResult(
            results=(
                _resolved(NEW_PUBLIC_KEY),
                _resolved(OLD_PUBLIC_KEY),
            )
        )
    )

    with pytest.raises(BatchProviderError, match="fingerprint does not match"):
        _ = _run(_manifest(), provider)


def test_empty_public_key_fails_trust_construction() -> None:
    provider = _provider(old_public_key=b"")

    with pytest.raises(BatchProviderError, match="public key cannot be empty"):
        _ = _run(_manifest(), provider)


def test_provider_exception_is_wrapped_without_vendor_text() -> None:
    provider = _RaisingProvider()

    with pytest.raises(
        BatchProviderError,
        match="batch provider raised during resolution",
    ) as caught:
        _ = _run(_manifest(), provider)

    assert VENDOR_DETAIL not in str(caught.value)
    assert provider.call_count == 1


def test_cancellation_propagates_to_the_caller() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), _CancellingProvider())


def test_same_key_id_under_distinct_algorithms_is_preserved() -> None:
    resolved = _run(_manifest(same_key_id=True), _provider())

    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.trust.key_count == TWO_REQUESTS


def test_batch_result_and_trust_hide_public_key_bytes() -> None:
    batch_result = BatchResult(
        results=(
            _resolved(OLD_PUBLIC_KEY),
            _resolved(NEW_PUBLIC_KEY),
        )
    )
    resolved = _run(_manifest(), _provider())

    batch_repr = repr(batch_result).encode("utf-8")
    trust_repr = repr(resolved).encode("utf-8")
    assert OLD_PUBLIC_KEY not in batch_repr
    assert NEW_PUBLIC_KEY not in batch_repr
    assert PUBLIC_KEY_FIELD not in batch_repr
    assert OLD_PUBLIC_KEY not in trust_repr
    assert NEW_PUBLIC_KEY not in trust_repr


def test_shared_item_result_kinds_remain_stable() -> None:
    assert tuple(kind.value for kind in ResultKind) == (
        "resolved",
        "unavailable",
        "failed",
    )
