# File:
#   - test_ticket_admission_public_key_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_public_key_provider.py
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
#   - Explicit detached-lineage public-key provider regressions.
# - Must-Not:
#   - Require CUDA, discover providers, cache keys, claim secure test
#     cryptography, or modify admission policy.
# - Allows:
#   - Inputs: synthetic manifests, providers, keys, and signature items.
#   - Outputs: request, resolution, rotation, and failure assertions.
#   - Side effects: explicit in-process provider calls only.
# - Split-When:
#   - Split when memory session adapter, external services, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact public-key provider behavior.
# - Summary:
#   - Explicit public-key provider port regressions.
# - Description:
#   - Proves one-pass manifest resolution and exact fingerprint checks.
# - Usage:
#   - Runs without accelerator hardware or external key services.
# - Defaults:
#   - Uses deterministic insecure digest signatures for protocol tests only.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Explicit detached-lineage public-key provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import TYPE_CHECKING
from typing import cast

import pytest

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
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyProviderError as ProviderError,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResult as PublicKeyResult,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    TicketAdmissionTelemetryLineagePublicKeyResultKind as ResultKind,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    ticket_admission_telemetry_lineage_public_key_provider_id,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureClaim as SignatureClaim,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureItem as SignatureItem,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignerResult as SignerResult,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignerResultKind as SignerKind,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageVerifierResult as VerifierResult,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageVerifierResultKind as VerifierKind,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    create_ticket_admission_telemetry_lineage_signature_attestation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_signature_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    compare_ticket_admission_telemetry_lineage_signatures_with_trust,
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
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_signature_trust_manifest as manifest_types,
    )
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
        TicketAdmissionTelemetryLineagePublicKeyRequest as PublicKeyRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageSignatureRequest as SignatureRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageVerificationRequest as VerificationRequest,
    )

    SignatureManifest = (
        manifest_types.TicketAdmissionTelemetryLineageSignatureTrustManifest
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

PORT_ID = "explicit-ticket-admission-telemetry-lineage-public-key-provider-v1"
PROVIDER_ID = "provider.test.public-keys"
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
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "public-key-provider-test-workload-v1"
BENCHMARK_ID = "public-key-provider-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_REQUESTS = 2


class _Provider:
    def __init__(self, results: dict[str, PublicKeyResult]) -> None:
        self._results: dict[str, PublicKeyResult] = results
        self.requests: list[PublicKeyRequest] = []

    def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
        self.requests.append(request)
        return self._results[request.public_key_reference_id]


class _DigestSigner:
    def __init__(self, public_key: bytes) -> None:
        self.public_key: bytes = public_key

    def __call__(self, request: SignatureRequest) -> SignerResult:
        signature = sha256(self.public_key + request.payload).digest()
        return SignerResult(kind=SignerKind.SIGNED, signature=signature)


class _DigestVerifier:
    def __call__(self, request: VerificationRequest) -> VerifierResult:
        expected = sha256(request.public_key + request.payload).digest()
        kind = (
            VerifierKind.VERIFIED
            if expected == request.signature
            else VerifierKind.INVALID
        )
        return VerifierResult(kind=kind)


def _resolved(public_key: bytes) -> PublicKeyResult:
    return PublicKeyResult(kind=ResultKind.RESOLVED, public_key=public_key)


def _provider(*, old_public_key: bytes = OLD_PUBLIC_KEY) -> _Provider:
    return _Provider({
        OLD_REFERENCE_ID: _resolved(old_public_key),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })


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


def _manifest(*, rotate_algorithm: bool = False) -> SignatureManifest:
    return build_ticket_admission_telemetry_lineage_signature_trust_manifest((
        _entry(
            algorithm_id=(
                NEW_ALGORITHM_ID if rotate_algorithm else OLD_ALGORITHM_ID
            ),
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(window=(GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID)),
    ))


def _claim(  # ruff: ignore[too-many-arguments]
    capture_sequence_id: int,
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    previous_attestation_fingerprint: str | None = None,
) -> SignatureClaim:
    return SignatureClaim(
        algorithm_id=algorithm_id,
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        recorder_id=RECORDER_ID,
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    claim: SignatureClaim,
    *,
    public_key: bytes = OLD_PUBLIC_KEY,
) -> SignatureItem:
    attestation = (
        create_ticket_admission_telemetry_lineage_signature_attestation(
            document,
            claim,
            _DigestSigner(public_key),
        )
    )
    return SignatureItem(attestation=attestation, document=document)


def test_empty_manifest_is_stable_and_makes_no_provider_calls() -> None:
    """An empty manifest resolves without discovering or calling a provider."""
    provider = _Provider({})
    built = (
        build_ticket_admission_telemetry_lineage_signature_trust_manifest(())
    )

    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        built,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert (
        ticket_admission_telemetry_lineage_public_key_provider_id() == PORT_ID
    )
    assert provider.requests == []
    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == 0
    assert resolved.algorithm_ids == ()
    assert resolved.public_key_ids == ()
    assert resolved.public_key_reference_ids == ()
    assert resolved.public_key_fingerprints == ()
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            built
        )
    )


def test_provider_requests_follow_canonical_composite_order() -> None:
    """Manifest entries produce immutable requests in composite identity order."""
    built = _manifest(rotate_algorithm=True)
    provider = _provider()
    fingerprint = (
        ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
            built
        )
    )

    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        built,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.request_count == TWO_REQUESTS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.public_key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert resolved.public_key_fingerprints == (
        _fingerprint(OLD_PUBLIC_KEY),
        _fingerprint(NEW_PUBLIC_KEY),
    )
    assert tuple(request.request_index for request in provider.requests) == (
        0,
        1,
    )
    assert all(
        request.manifest_fingerprint == fingerprint
        for request in provider.requests
    )
    assert all(
        request.provider_id == PROVIDER_ID for request in provider.requests
    )
    assert provider.requests[0].first_capture_sequence_id == GENESIS_SEQUENCE_ID
    assert provider.requests[0].last_capture_sequence_id == GENESIS_SEQUENCE_ID
    assert (
        provider.requests[1].first_capture_sequence_id == SUCCESSOR_SEQUENCE_ID
    )
    assert provider.requests[1].last_capture_sequence_id is None


def test_provider_result_and_trust_hide_public_key_bytes() -> None:
    """Provider and resolved trust representations expose no key bytes."""
    result = _resolved(OLD_PUBLIC_KEY)
    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        _manifest(),
        _provider(),
        provider_id=PROVIDER_ID,
    )

    result_repr = repr(result).encode("utf-8")
    trust_repr = repr(resolved).encode("utf-8")
    assert OLD_PUBLIC_KEY not in result_repr
    assert PUBLIC_KEY_FIELD not in result_repr
    assert OLD_PUBLIC_KEY not in trust_repr
    assert NEW_PUBLIC_KEY not in trust_repr
    assert PUBLIC_KEY_FIELD not in trust_repr


def test_each_resolution_calls_provider_once_per_entry_without_cache() -> None:
    """Repeated explicit resolution performs a fresh provider walk."""
    provider = _provider()
    built = _manifest()

    first = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        built,
        provider,
        provider_id=PROVIDER_ID,
    )
    second = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        built,
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
    """An undersized request budget fails before external resolution."""
    provider = _provider()

    with pytest.raises(ProviderError, match="request count exceeds"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
            max_requests=1,
        )

    assert provider.requests == []


def test_exact_request_budget_allows_one_call_per_entry() -> None:
    """A budget equal to manifest size permits the canonical provider walk."""
    provider = _provider()

    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
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

    with pytest.raises(ProviderError, match="request limit must be a positive"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
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
    """Provider identity uses canonical ASCII identity form."""
    provider = _provider()

    with pytest.raises(ProviderError, match="provider identity must use"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=provider_id,
        )

    assert provider.requests == []


def test_tampered_manifest_fails_before_provider_calls() -> None:
    """Manifest identity and ordering are checked before live resolution."""
    provider = _provider()
    built = replace(_manifest(), manifest_id="unsupported")

    with pytest.raises(ProviderError, match="manifest identity is unsupported"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            built,
            provider,
            provider_id=PROVIDER_ID,
        )

    assert provider.requests == []


@pytest.mark.parametrize("kind", [ResultKind.UNAVAILABLE, ResultKind.FAILED])
def test_typed_provider_failure_stops_without_retry(kind: ResultKind) -> None:
    """Unavailable and failed outcomes stop after the first exact request."""
    provider = _Provider({
        OLD_REFERENCE_ID: PublicKeyResult(kind=kind),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(
        ProviderError,
        match=rf"provider returned {kind.value} at request index 0",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == 1
    assert provider.requests[0].public_key_reference_id == OLD_REFERENCE_ID


def test_nonresolved_result_cannot_carry_public_key_bytes() -> None:
    """Failure outcomes cannot smuggle key material into resolution."""
    provider = _Provider({
        OLD_REFERENCE_ID: PublicKeyResult(
            kind=ResultKind.FAILED,
            public_key=OLD_PUBLIC_KEY,
        ),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(ProviderError, match="nonresolved provider result"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == 1


def test_foreign_provider_result_type_fails_closed() -> None:
    """Providers must return the exact immutable result contract."""

    class ForeignProvider:
        def __call__(self, request: PublicKeyRequest) -> PublicKeyResult:
            del request
            return cast("PublicKeyResult", cast("object", OLD_PUBLIC_KEY))

    with pytest.raises(ProviderError, match="exact provider result type"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            ForeignProvider(),
            provider_id=PROVIDER_ID,
        )


def test_foreign_provider_result_kind_fails_closed() -> None:
    """Result kinds cannot be substituted by equal-looking strings."""
    result = PublicKeyResult(
        kind=cast("ResultKind", cast("object", "resolved")),
        public_key=OLD_PUBLIC_KEY,
    )
    provider = _Provider({
        OLD_REFERENCE_ID: result,
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(ProviderError, match="exact provider result enum"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )


@pytest.mark.parametrize(
    "public_key",
    [None, cast("bytes | None", cast("object", bytearray(OLD_PUBLIC_KEY)))],
)
def test_resolved_result_requires_exact_bytes(
    public_key: bytes | None,
) -> None:
    """A resolved outcome requires exact immutable bytes."""
    provider = _Provider({
        OLD_REFERENCE_ID: PublicKeyResult(
            kind=ResultKind.RESOLVED,
            public_key=public_key,
        ),
        NEW_REFERENCE_ID: _resolved(NEW_PUBLIC_KEY),
    })

    with pytest.raises(ProviderError, match="exact public-key bytes"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )


def test_empty_public_key_fails_during_trust_construction() -> None:
    """Provider resolution cannot bypass the nonempty-key contract."""
    provider = _provider(old_public_key=b"")

    with pytest.raises(ProviderError, match="public key cannot be empty"):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == TWO_REQUESTS


def test_wrong_public_key_fails_during_manifest_resolution() -> None:
    """Resolved bytes must match the fingerprint persisted in the manifest."""
    provider = _provider(old_public_key=WRONG_PUBLIC_KEY)

    with pytest.raises(
        ProviderError, match="fingerprint does not match manifest"
    ):
        _ = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
            _manifest(),
            provider,
            provider_id=PROVIDER_ID,
        )

    assert len(provider.requests) == TWO_REQUESTS


def test_same_key_id_under_distinct_algorithms_uses_exact_requests() -> None:
    """Composite identity remains exact when a key ID is reused."""
    built = build_ticket_admission_telemetry_lineage_signature_trust_manifest((
        _entry(),
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
    ))
    provider = _provider()

    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        built,
        provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert tuple(request.algorithm_id for request in provider.requests) == (
        OLD_ALGORITHM_ID,
        NEW_ALGORITHM_ID,
    )


def test_provider_resolved_key_rotation_verifies_direct_successor() -> None:
    """Explicit resolution preserves direct lineage across public-key rotation."""
    first_document = _document(LOW_ELAPSED_NS)
    first = _item(first_document, _claim(GENESIS_SEQUENCE_ID))
    first_id = (
        ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
            first.attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second = _item(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            previous_attestation_fingerprint=first_id,
        ),
        public_key=NEW_PUBLIC_KEY,
    )
    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        _manifest(),
        _provider(),
        provider_id=PROVIDER_ID,
    )

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            first,
            second,
            _DigestVerifier(),
            trust=resolved.trust,
        )
    )

    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


def test_provider_resolved_algorithm_rotation_verifies_direct_successor() -> (
    None
):
    """Explicit resolution also preserves direct lineage across algorithms."""
    first_document = _document(LOW_ELAPSED_NS)
    first = _item(first_document, _claim(GENESIS_SEQUENCE_ID))
    first_id = (
        ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
            first.attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second = _item(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            previous_attestation_fingerprint=first_id,
        ),
        public_key=NEW_PUBLIC_KEY,
    )
    resolved = resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider(
        _manifest(rotate_algorithm=True),
        _provider(),
        provider_id=PROVIDER_ID,
    )

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            first,
            second,
            _DigestVerifier(),
            trust=resolved.trust,
        )
    )

    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


def test_provider_result_kinds_have_stable_string_values() -> None:
    """Provider failures expose only stable non-vendor categories."""
    assert tuple(ResultKind) == (
        ResultKind.RESOLVED,
        ResultKind.UNAVAILABLE,
        ResultKind.FAILED,
    )
    assert tuple(kind.value for kind in ResultKind) == (
        "resolved",
        "unavailable",
        "failed",
    )
