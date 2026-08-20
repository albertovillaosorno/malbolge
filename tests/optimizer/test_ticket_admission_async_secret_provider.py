# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Sequential caller-driven async lineage secret-provider regressions.
# - Must-Not:
#   - Require CUDA, external stores, hidden tasks, retries, caches, persistence,
#     secret logging, async plugins, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic manifests, async providers, secrets, and failures.
#   - Outputs: preflight, ordering, awaiting, resolution, and failure
#     assertions.
#   - Side effects: caller-owned standard-library event loops only.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI gain
#     tests.
# - Merge-When:
#   - Merge when another suite owns this exact async secret-provider behavior.
# - Summary:
#   - Explicit sequential async HMAC-secret provider regressions.
# - Description:
#   - Proves canonical awaits reuse exact synchronous validation and trust.
# - Usage:
#   - Runs without files, network, async plugins, or external secret services.
# - Defaults:
#   - Uses two synthetic 32-byte secrets and the shared 256-request default.
#

"""Sequential caller-driven async lineage secret-provider tests."""

# ruff: file-ignore[undocumented-public-function]

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

from accelerator import (
    ticket_admission_telemetry_lineage_async_secret_provider as async_port,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as sync_port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MIN_TELEMETRY_LINEAGE_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestEntry,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    build_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_fingerprint,
)
import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
        TicketAdmissionTelemetryLineageProviderTrust,
    )
    from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
        TicketAdmissionTelemetryLineageSecretRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )

AsyncProviderError = (
    async_port.TicketAdmissionTelemetryLineageAsyncSecretProviderError
)
SecretResult = sync_port.TicketAdmissionTelemetryLineageSecretResult
SecretKind = sync_port.TicketAdmissionTelemetryLineageSecretResultKind
AsyncProvider = async_port.TicketAdmissionTelemetryLineageAsyncSecretProvider
_resolve_async = (
    async_port.resolve_ticket_admission_telemetry_lineage_trust_async
)
_resolve_sync = (
    sync_port.resolve_ticket_admission_telemetry_lineage_trust_with_provider
)

PORT_ID = "explicit-async-ticket-admission-telemetry-lineage-secret-provider-v1"
PROVIDER_ID = "provider.test.async-lineage-secrets"
OTHER_PROVIDER_ID = "provider.test.other-lineage-secrets"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "vault.lineage-key.2026-07"
NEW_REFERENCE_ID = "vault.lineage-key.2026-08"
OLD_SECRET = b"o" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
NEW_SECRET = b"n" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
WRONG_SECRET = b"z" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
VENDOR_DETAIL = "secret backend detail must not cross boundary"
SECRET_FIELD = b"secret_key"
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
ONE_REQUEST = 1
TWO_REQUESTS = 2
DEFAULT_REQUESTS = 256


class _AsyncProvider:
    def __init__(
        self,
        results: dict[str, SecretResult],
        *,
        suspend: bool = True,
    ) -> None:
        self._results: dict[str, SecretResult] = results
        self.suspend: bool = suspend
        self.active_count: int = 0
        self.max_active_count: int = 0
        self.requests: list[TicketAdmissionTelemetryLineageSecretRequest] = []
        self.tasks: list[asyncio.Task[object] | None] = []

    async def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> SecretResult:
        self.active_count += 1
        self.max_active_count = max(self.max_active_count, self.active_count)
        self.requests.append(request)
        self.tasks.append(asyncio.current_task())
        if self.suspend:
            await asyncio.sleep(0)
        self.active_count -= 1
        return self._results[request.key_reference_id]


class _SyncProvider:
    def __init__(self, results: dict[str, SecretResult]) -> None:
        self._results: dict[str, SecretResult] = results

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> SecretResult:
        return self._results[request.key_reference_id]


class _CancellingProvider:
    async def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> SecretResult:
        del request
        raise asyncio.CancelledError


class _RaisingProvider:
    def __init__(self) -> None:
        self.requests: list[TicketAdmissionTelemetryLineageSecretRequest] = []

    async def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> SecretResult:
        self.requests.append(request)
        raise RuntimeError(VENDOR_DETAIL)


def _resolved(secret: bytes) -> SecretResult:
    return SecretResult(kind=SecretKind.RESOLVED, secret_key=secret)


def _results(*, old_secret: bytes = OLD_SECRET) -> dict[str, SecretResult]:
    return {
        OLD_REFERENCE_ID: _resolved(old_secret),
        NEW_REFERENCE_ID: _resolved(NEW_SECRET),
    }


def _manifest() -> TicketAdmissionTelemetryLineageTrustManifest:
    return build_ticket_admission_telemetry_lineage_trust_manifest((
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
        ),
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            key_id=OLD_KEY_ID,
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
        ),
    ))


def _provider(
    *,
    old_secret: bytes = OLD_SECRET,
    suspend: bool = True,
) -> _AsyncProvider:
    return _AsyncProvider(_results(old_secret=old_secret), suspend=suspend)


def _run(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    provider: AsyncProvider,
    *,
    provider_id: str = PROVIDER_ID,
    max_requests: int = TWO_REQUESTS,
) -> TicketAdmissionTelemetryLineageProviderTrust:
    return asyncio.run(
        _resolve_async(
            manifest,
            provider,
            provider_id=provider_id,
            max_requests=max_requests,
        )
    )


def test_identity_and_default_request_limit_are_stable() -> None:
    assert (
        async_port.ticket_admission_telemetry_lineage_async_secret_provider_id()
        == PORT_ID
    )
    assert (
        async_port.DEFAULT_MAX_TELEMETRY_LINEAGE_ASYNC_SECRET_PROVIDER_REQUESTS
        == DEFAULT_REQUESTS
    )


def test_coroutine_does_not_start_before_caller_runs_it() -> None:
    provider = _provider()
    coroutine = _resolve_async(
        _manifest(),
        provider,
        provider_id=PROVIDER_ID,
    )

    assert provider.requests == []
    resolved = asyncio.run(coroutine)

    assert resolved.request_count == TWO_REQUESTS


def test_empty_manifest_makes_no_provider_calls() -> None:
    provider = _AsyncProvider({})
    manifest = build_ticket_admission_telemetry_lineage_trust_manifest(())

    resolved = _run(manifest, provider, max_requests=ONE_REQUEST)

    assert provider.requests == []
    assert resolved.request_count == 0
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_trust_manifest_fingerprint(manifest)
    )


def test_requests_follow_canonical_order_sequentially() -> None:
    provider = _provider()
    manifest = _manifest()

    resolved = _run(manifest, provider)

    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert tuple(request.request_index for request in provider.requests) == (
        0,
        1,
    )
    assert provider.max_active_count == ONE_REQUEST
    assert len(set(provider.tasks)) == ONE_REQUEST
    assert all(
        request.manifest_fingerprint
        == ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
            manifest
        )
        for request in provider.requests
    )


def test_inline_provider_introduces_no_scheduling_point() -> None:
    provider = _provider(suspend=False)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> TicketAdmissionTelemetryLineageProviderTrust:
        marker_task = asyncio.create_task(marker())
        result = await _resolve_async(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )
        assert events == []
        await marker_task
        return result

    resolved = asyncio.run(resolve())

    assert resolved.request_count == TWO_REQUESTS
    assert events == ["marker"]


def test_suspending_provider_controls_scheduling_point() -> None:
    provider = _provider(suspend=True)
    events: list[str] = []

    async def marker() -> None:
        await asyncio.sleep(0)
        events.append("marker")

    async def resolve() -> TicketAdmissionTelemetryLineageProviderTrust:
        marker_task = asyncio.create_task(marker())
        result = await _resolve_async(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )
        assert events == ["marker"]
        await marker_task
        return result

    resolved = asyncio.run(resolve())

    assert resolved.request_count == TWO_REQUESTS


def test_sync_and_async_paths_materialize_identical_trust() -> None:
    results = _results()

    synchronous = _resolve_sync(
        _manifest(),
        _SyncProvider(results),
        provider_id=PROVIDER_ID,
    )
    asynchronous = _run(
        _manifest(),
        _AsyncProvider(results, suspend=False),
    )

    assert asynchronous == synchronous


def test_repeated_resolution_has_no_cache() -> None:
    provider = _provider(suspend=False)
    manifest = _manifest()

    first = _run(manifest, provider)
    second = _run(manifest, provider)

    assert first == second
    assert len(provider.requests) == TWO_REQUESTS * 2


def test_request_budget_fails_before_first_await() -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="request count exceeds"):
        _ = _run(_manifest(), provider, max_requests=ONE_REQUEST)

    assert provider.requests == []


@pytest.mark.parametrize("max_requests", [0, -1, True])
def test_invalid_request_limit_fails_before_first_await(
    max_requests: int,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="positive integer"):
        _ = _run(_manifest(), provider, max_requests=max_requests)

    assert provider.requests == []


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_invalid_provider_identity_fails_before_first_await(
    provider_id: str,
) -> None:
    provider = _provider()

    with pytest.raises(AsyncProviderError, match="canonical ASCII"):
        _ = _run(_manifest(), provider, provider_id=provider_id)

    assert provider.requests == []


def test_tampered_manifest_fails_before_first_await() -> None:
    provider = _provider()
    manifest = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(AsyncProviderError, match="manifest identity"):
        _ = _run(manifest, provider)

    assert provider.requests == []


def test_noncallable_provider_fails_before_first_await() -> None:
    with pytest.raises(AsyncProviderError, match="provider must be callable"):
        _ = _run(
            _manifest(),
            cast("AsyncProvider", object()),
        )


@pytest.mark.parametrize("kind", [SecretKind.UNAVAILABLE, SecretKind.FAILED])
def test_typed_failure_stops_without_retry(kind: SecretKind) -> None:
    provider = _AsyncProvider(
        {
            OLD_REFERENCE_ID: SecretResult(kind=kind),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        },
        suspend=False,
    )

    with pytest.raises(
        AsyncProviderError,
        match=rf"provider returned {kind.value} at request index 0",
    ):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == ONE_REQUEST


def test_provider_exception_is_wrapped_without_vendor_text() -> None:
    provider = _RaisingProvider()

    with pytest.raises(
        AsyncProviderError,
        match="provider raised during request index 0",
    ) as caught:
        _ = _run(_manifest(), provider)

    assert VENDOR_DETAIL not in str(caught.value)
    assert len(provider.requests) == ONE_REQUEST


def test_cancellation_propagates_to_caller() -> None:
    with pytest.raises(asyncio.CancelledError, match=r"^$"):
        _ = _run(_manifest(), _CancellingProvider())


def test_nonresolved_result_cannot_carry_secret_bytes() -> None:
    provider = _AsyncProvider(
        {
            OLD_REFERENCE_ID: SecretResult(
                kind=SecretKind.FAILED,
                secret_key=OLD_SECRET,
            ),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        },
        suspend=False,
    )

    with pytest.raises(AsyncProviderError, match="nonresolved provider result"):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == ONE_REQUEST


def test_foreign_result_type_fails_closed() -> None:
    class ForeignProvider:
        async def __call__(
            self,
            request: TicketAdmissionTelemetryLineageSecretRequest,
        ) -> SecretResult:
            del request
            return cast("SecretResult", cast("object", OLD_SECRET))

    with pytest.raises(AsyncProviderError, match="exact provider result type"):
        _ = _run(_manifest(), ForeignProvider())


def test_foreign_result_kind_fails_closed() -> None:
    result = SecretResult(
        kind=cast("SecretKind", cast("object", "resolved")),
        secret_key=OLD_SECRET,
    )
    provider = _AsyncProvider(
        {
            OLD_REFERENCE_ID: result,
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        },
        suspend=False,
    )

    with pytest.raises(AsyncProviderError, match="exact provider result enum"):
        _ = _run(_manifest(), provider)


@pytest.mark.parametrize(
    "secret_key",
    [
        None,
        cast("bytes | None", cast("object", bytearray(OLD_SECRET))),
    ],
)
def test_resolved_result_requires_exact_bytes(
    secret_key: bytes | None,
) -> None:
    provider = _AsyncProvider(
        {
            OLD_REFERENCE_ID: SecretResult(
                kind=SecretKind.RESOLVED,
                secret_key=secret_key,
            ),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        },
        suspend=False,
    )

    with pytest.raises(AsyncProviderError, match="exact secret bytes"):
        _ = _run(_manifest(), provider)


def test_short_secret_fails_during_shared_trust_materialization() -> None:
    provider = _provider(old_secret=b"short", suspend=False)

    with pytest.raises(AsyncProviderError, match="shorter than"):
        _ = _run(_manifest(), provider)

    assert len(provider.requests) == TWO_REQUESTS


def test_wrong_secret_remains_caller_owned_until_authentication() -> None:
    resolved = _run(
        _manifest(),
        _provider(old_secret=WRONG_SECRET, suspend=False),
    )

    assert resolved.trust.keys[0].secret_key is WRONG_SECRET
    assert resolved.trust.keys[1].secret_key is NEW_SECRET


def test_rotation_trust_preserves_exact_windows_and_secrets() -> None:
    resolved = _run(_manifest(), _provider(suspend=False))

    assert resolved.trust.key_count == TWO_REQUESTS
    assert tuple(key.key_id for key in resolved.trust.keys) == (
        OLD_KEY_ID,
        NEW_KEY_ID,
    )
    assert tuple(key.secret_key for key in resolved.trust.keys) == (
        OLD_SECRET,
        NEW_SECRET,
    )
    assert resolved.trust.keys[0].first_capture_sequence_id == 0
    assert resolved.trust.keys[0].last_capture_sequence_id == 0
    assert resolved.trust.keys[1].first_capture_sequence_id == 1
    assert resolved.trust.keys[1].last_capture_sequence_id is None


def test_result_and_resolved_trust_hide_secret_bytes() -> None:
    result = _resolved(OLD_SECRET)
    resolved = _run(_manifest(), _provider(suspend=False))

    result_repr = repr(result).encode("utf-8")
    trust_repr = repr(resolved).encode("utf-8")
    assert OLD_SECRET not in result_repr
    assert SECRET_FIELD not in result_repr
    assert OLD_SECRET not in trust_repr
    assert NEW_SECRET not in trust_repr
    assert SECRET_FIELD not in trust_repr


def test_result_kinds_remain_shared_and_stable() -> None:
    assert tuple(kind.value for kind in SecretKind) == (
        "resolved",
        "unavailable",
        "failed",
    )
