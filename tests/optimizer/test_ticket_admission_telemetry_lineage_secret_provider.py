# File:
#   - test_ticket_admission_telemetry_lineage_secret_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage_secret_provider.py
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
#   - Explicit live secret-provider port regressions.
# - Must-Not:
#   - Require CUDA, discover providers, retain caches, or modify admission
#     policy.
# - Allows:
#   - Inputs: synthetic manifests, provider ports, results, and lineage items.
#   - Outputs: request, budget, failure, rotation, and noncaching assertions.
#   - Side effects: in-memory provider-call recording only.
# - Split-When:
#   - Split when asynchronous providers or provider lifecycles gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact provider-port behavior.
# - Summary:
#   - One-pass telemetry lineage secret-provider regressions.
# - Description:
#   - Proves explicit synchronous resolution has no discovery, retry, or cache.
# - Usage:
#   - Runs without accelerator hardware, files, or external key services.
# - Defaults:
#   - Uses two deterministic references and typed provider outcomes.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
#
# Large file:
#   - false
#

"""Explicit telemetry lineage secret-provider port tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryLineageAttestation,
    )
    from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
        TicketAdmissionTelemetryLineageSecretRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageClaim,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageItem,
)
from accelerator.ticket_admission_telemetry_lineage import (
    create_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
    TicketAdmissionTelemetryLineageSecretProviderError,
)
from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
    TicketAdmissionTelemetryLineageSecretResult,
)
from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
    TicketAdmissionTelemetryLineageSecretResultKind,
)
from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
    resolve_ticket_admission_telemetry_lineage_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
    ticket_admission_telemetry_lineage_secret_provider_id,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    compare_ticket_admission_telemetry_lineage_with_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    verify_ticket_admission_telemetry_lineage_with_trust,
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
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

PORT_ID = "explicit-ticket-admission-telemetry-lineage-secret-provider-v1"
PROVIDER_ID = "provider.test"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "vault.lineage-key.2026-07"
NEW_REFERENCE_ID = "vault.lineage-key.2026-08"
OLD_SECRET = b"old-caller-owned-lineage-secret!!"
NEW_SECRET = b"new-caller-owned-lineage-secret!!"
WRONG_SECRET = b"wrong-caller-owned-lineage-key!!"
SHORT_SECRET = b"short"
SECRET_FIELD_NAME = b"secret_key"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "lineage-provider-test-workload-v1"
BENCHMARK_ID = "lineage-provider-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_REQUESTS = 2


class _Provider:
    def __init__(
        self,
        results: dict[str, TicketAdmissionTelemetryLineageSecretResult],
    ) -> None:
        self._results: dict[
            str,
            TicketAdmissionTelemetryLineageSecretResult,
        ] = results
        self.requests: list[TicketAdmissionTelemetryLineageSecretRequest] = []

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSecretRequest,
    ) -> TicketAdmissionTelemetryLineageSecretResult:
        self.requests.append(request)
        return self._results[request.key_reference_id]


def _resolved(secret_key: bytes) -> TicketAdmissionTelemetryLineageSecretResult:
    return TicketAdmissionTelemetryLineageSecretResult(
        kind=TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED,
        secret_key=secret_key,
    )


def _provider(
    *,
    old_secret: bytes = OLD_SECRET,
) -> _Provider:
    return _Provider(
        {
            OLD_REFERENCE_ID: _resolved(old_secret),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        }
    )


def _report() -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=TICKET_COUNT,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=TICKET_COUNT,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _document(
    elapsed_ns: int | None = None,
) -> TicketAdmissionTelemetryDocument:
    attempts = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=2),
        failed=TicketAdmissionFailureTelemetry(capacity=2),
    )
    if elapsed_ns is not None:
        _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def _claim(
    capture_sequence_id: int,
    key_id: str,
    previous_attestation_fingerprint: str | None = None,
) -> TicketAdmissionTelemetryLineageClaim:
    return TicketAdmissionTelemetryLineageClaim(
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        key_id=key_id,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        recorder_id=RECORDER_ID,
    )


def _attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageClaim,
    secret_key: bytes,
) -> TicketAdmissionTelemetryLineageAttestation:
    return create_ticket_admission_telemetry_lineage_attestation(
        document,
        claim,
        secret_key=secret_key,
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> TicketAdmissionTelemetryLineageItem:
    return TicketAdmissionTelemetryLineageItem(
        attestation=attestation,
        document=document,
    )


def _entry(
    key_id: str,
    key_reference_id: str,
    window: tuple[int, int | None],
) -> TicketAdmissionTelemetryLineageTrustManifestEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return TicketAdmissionTelemetryLineageTrustManifestEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
    )


def _manifest() -> TicketAdmissionTelemetryLineageTrustManifest:
    return build_ticket_admission_telemetry_lineage_trust_manifest(
        (
            _entry(
                NEW_KEY_ID,
                NEW_REFERENCE_ID,
                (SUCCESSOR_SEQUENCE_ID, None),
            ),
            _entry(
                OLD_KEY_ID,
                OLD_REFERENCE_ID,
                (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
            ),
        )
    )


def test_empty_manifest_is_stable_and_makes_no_provider_calls() -> None:
    """An empty manifest resolves without discovering or calling a provider."""
    provider = _Provider({})
    manifest = build_ticket_admission_telemetry_lineage_trust_manifest(())

    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        manifest,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert ticket_admission_telemetry_lineage_secret_provider_id() == PORT_ID
    assert provider.requests == []
    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == 0
    assert resolved.key_ids == ()
    assert resolved.key_reference_ids == ()
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_trust_manifest_fingerprint(manifest)
    )


def test_provider_requests_follow_canonical_manifest_order() -> None:
    """Each manifest entry produces one immutable request in key order."""
    manifest = _manifest()
    provider = _provider()
    fingerprint = (
        ticket_admission_telemetry_lineage_trust_manifest_fingerprint(manifest)
    )

    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        manifest,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.request_count == TWO_REQUESTS
    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert tuple(
        request.request_index for request in provider.requests
    ) == (0, 1)
    assert tuple(request.key_id for request in provider.requests) == (
        OLD_KEY_ID,
        NEW_KEY_ID,
    )
    assert all(
        request.manifest_fingerprint == fingerprint
        for request in provider.requests
    )
    assert all(
        request.provider_id == PROVIDER_ID
        for request in provider.requests
    )
    assert provider.requests[0].first_capture_sequence_id == GENESIS_SEQUENCE_ID
    assert provider.requests[0].last_capture_sequence_id == GENESIS_SEQUENCE_ID
    assert (
        provider.requests[1].first_capture_sequence_id
        == SUCCESSOR_SEQUENCE_ID
    )
    assert provider.requests[1].last_capture_sequence_id is None


def test_provider_result_and_resolved_trust_hide_secret_bytes() -> None:
    """Provider and trust representations expose no resolved key material."""
    result = _resolved(OLD_SECRET)
    provider = _provider()

    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        _manifest(),
        provider,
        provider_id=PROVIDER_ID,
    )

    result_repr = repr(result).encode("utf-8")
    trust_repr = repr(resolved).encode("utf-8")
    assert OLD_SECRET not in result_repr
    assert SECRET_FIELD_NAME not in result_repr
    assert OLD_SECRET not in trust_repr
    assert NEW_SECRET not in trust_repr
    assert SECRET_FIELD_NAME not in trust_repr


def test_each_resolution_calls_provider_once_per_entry_without_cache() -> None:
    """Repeated explicit resolution performs a fresh one-pass provider walk."""
    provider = _provider()
    manifest = _manifest()

    first = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        manifest,
        provider,
        provider_id=PROVIDER_ID,
    )
    second = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        manifest,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert first == second
    assert len(provider.requests) == TWO_REQUESTS * 2
    assert tuple(request.request_index for request in provider.requests) == (
        0,
        1,
        0,
        1,
    )


def test_request_budget_is_checked_before_provider_calls() -> None:
    """An undersized request budget fails before any external resolution."""
    provider = _provider()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="request count exceeds configured limit",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
            max_requests=1,
        )

    assert provider.requests == []


def test_exact_request_budget_allows_one_call_per_entry() -> None:
    """A budget equal to manifest size permits the canonical provider walk."""
    provider = _provider()

    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        _manifest(),
        provider,
        provider_id=PROVIDER_ID,
        max_requests=TWO_REQUESTS,
    )

    assert resolved.request_count == TWO_REQUESTS
    assert len(provider.requests) == TWO_REQUESTS


@pytest.mark.parametrize("max_requests", [0, True])
def test_invalid_request_limit_fails_before_provider_calls(
    max_requests: int,
) -> None:
    """Request limits must be positive exact integers."""
    provider = _provider()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="request limit must be a positive integer",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
            max_requests=max_requests,
        )

    assert provider.requests == []


@pytest.mark.parametrize(
    "provider_id",
    ["bad provider", "", cast("str", object())],
)
def test_invalid_provider_identity_fails_before_provider_calls(
    provider_id: str,
) -> None:
    """Provider identity uses the same canonical ASCII identity form."""
    provider = _provider()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="provider identity must use canonical ASCII identity form",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=provider_id,
        )

    assert provider.requests == []


def test_tampered_manifest_fails_before_provider_calls() -> None:
    """Manifest identity and ordering are validated before live resolution."""
    provider = _provider()
    manifest = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="manifest identity is unsupported",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            manifest,
            provider,
            provider_id=PROVIDER_ID,
        )

    assert provider.requests == []


@pytest.mark.parametrize(
    "kind",
    [
        TicketAdmissionTelemetryLineageSecretResultKind.UNAVAILABLE,
        TicketAdmissionTelemetryLineageSecretResultKind.FAILED,
    ],
)
def test_typed_provider_failure_stops_without_retry(
    kind: TicketAdmissionTelemetryLineageSecretResultKind,
) -> None:
    """Unavailable and failed outcomes stop after the first exact request."""
    provider = _Provider(
        {
            OLD_REFERENCE_ID: TicketAdmissionTelemetryLineageSecretResult(
                kind=kind
            ),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        }
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match=rf"provider returned {kind.value} at request index 0",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == 1
    assert provider.requests[0].key_reference_id == OLD_REFERENCE_ID


def test_nonresolved_result_cannot_carry_secret_bytes() -> None:
    """Failure outcomes cannot smuggle secret material into diagnostics."""
    provider = _Provider(
        {
            OLD_REFERENCE_ID: TicketAdmissionTelemetryLineageSecretResult(
                kind=TicketAdmissionTelemetryLineageSecretResultKind.FAILED,
                secret_key=OLD_SECRET,
            ),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        }
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="nonresolved provider result cannot contain secret bytes",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == 1


def test_foreign_provider_result_type_fails_closed() -> None:
    """Providers must return the exact immutable result contract."""

    class ForeignProvider:
        def __call__(
            self,
            request: TicketAdmissionTelemetryLineageSecretRequest,
        ) -> TicketAdmissionTelemetryLineageSecretResult:
            del request
            return cast(
                "TicketAdmissionTelemetryLineageSecretResult",
                cast("object", OLD_SECRET),
            )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="result must use the exact provider result type",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            ForeignProvider(),
            provider_id=PROVIDER_ID,
        )


def test_foreign_provider_result_kind_fails_closed() -> None:
    """Result kinds cannot be substituted by equal-looking strings."""
    result = TicketAdmissionTelemetryLineageSecretResult(
        kind=cast(
            "TicketAdmissionTelemetryLineageSecretResultKind",
            cast("object", "resolved"),
        ),
        secret_key=OLD_SECRET,
    )
    provider = _Provider(
        {
            OLD_REFERENCE_ID: result,
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        }
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="result kind must use the exact provider result enum",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )


@pytest.mark.parametrize(
    "secret_key",
    [None, cast("bytes | None", cast("object", bytearray(OLD_SECRET)))],
)
def test_resolved_result_requires_exact_bytes(
    secret_key: bytes | None,
) -> None:
    """A resolved outcome requires exact immutable bytes."""
    provider = _Provider(
        {
            OLD_REFERENCE_ID: TicketAdmissionTelemetryLineageSecretResult(
                kind=TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED,
                secret_key=secret_key,
            ),
            NEW_REFERENCE_ID: _resolved(NEW_SECRET),
        }
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="resolved provider result must use exact secret bytes",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )


def test_short_provider_secret_fails_during_trust_construction() -> None:
    """Provider resolution cannot bypass the trust key-length contract."""
    provider = _provider(old_secret=SHORT_SECRET)

    with pytest.raises(
        TicketAdmissionTelemetryLineageSecretProviderError,
        match="secret key is shorter than the configured minimum",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == TWO_REQUESTS


def test_wrong_provider_secret_fails_only_on_attestation_verification() -> None:
    """Live resolution does not certify secret correctness before MAC use."""
    provider = _provider(old_secret=WRONG_SECRET)
    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        _manifest(),
        provider,
        provider_id=PROVIDER_ID,
    )
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="authentication failed",
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            resolved.trust,
        )


def test_provider_resolved_rotation_verifies_direct_successor() -> None:
    """Explicit live resolution preserves authenticated cross-key succession."""
    first_document = _document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            NEW_KEY_ID,
            first_fingerprint,
        ),
        NEW_SECRET,
    )
    resolved = resolve_ticket_admission_telemetry_lineage_trust_with_provider(
        _manifest(),
        _provider(),
        provider_id=PROVIDER_ID,
    )

    comparison = compare_ticket_admission_telemetry_lineage_with_trust(
        _item(first_document, first_attestation),
        _item(second_document, second_attestation),
        resolved.trust,
    )

    assert comparison.common_recorder_lineage
    assert comparison.direct_chain_link
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


def test_provider_result_kinds_have_stable_string_values() -> None:
    """Provider failures expose only stable non-vendor outcome categories."""
    assert tuple(TicketAdmissionTelemetryLineageSecretResultKind) == (
        TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED,
        TicketAdmissionTelemetryLineageSecretResultKind.UNAVAILABLE,
        TicketAdmissionTelemetryLineageSecretResultKind.FAILED,
    )
    assert tuple(
        kind.value for kind in TicketAdmissionTelemetryLineageSecretResultKind
    ) == ("resolved", "unavailable", "failed")
