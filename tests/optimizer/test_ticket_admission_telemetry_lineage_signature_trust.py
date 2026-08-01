# File:
#   - test_ticket_admission_telemetry_lineage_signature_trust.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage_signature_trust.py
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
#   - Bounded caller-owned public-key signature trust regressions.
# - Must-Not:
#   - Require CUDA, claim test cryptography is secure, load trust, or change
#     admission policy.
# - Allows:
#   - Inputs: synthetic signature items, public keys, trust windows, verifier.
#   - Outputs: ordering, selection, rotation, comparison, and failure
#     assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when native async HTTPS, async memory auth, external
#     credentials, hosted APIs, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact signature trust behavior.
# - Summary:
#   - Caller-owned detached lineage public-key trust regressions.
# - Description:
#   - Proves exact algorithm/key/window selection occurs before verification.
# - Usage:
#   - Runs without accelerator hardware, files, or external key services.
# - Defaults:
#   - Uses deterministic insecure digest ports only as protocol test evidence.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
#
# Large file:
#   - false
#

"""Bounded caller-owned public-key lineage signature trust tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageSignatureAttestation,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageSignatureRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageVerificationRequest,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
        TicketAdmissionTelemetryLineageSignatureTrust,
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
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureClaim,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureItem,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignerResult,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignerResultKind,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageVerifierResult,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageVerifierResultKind,
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
    TicketAdmissionTelemetryLineageSignatureTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    TicketAdmissionTelemetryLineageSignatureTrustKey,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    build_ticket_admission_telemetry_lineage_signature_trust,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    compare_ticket_admission_telemetry_lineage_signatures_with_trust,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    ticket_admission_telemetry_lineage_signature_trust_id,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    verify_ticket_admission_telemetry_lineage_signature_with_trust,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

TRUST_ID = "caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
UNKNOWN_KEY_ID = "public.test-key.unknown"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "signature-trust-test-workload-v1"
BENCHMARK_ID = "signature-trust-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
WINDOW_FIRST_SEQUENCE_ID = 1
WINDOW_LAST_SEQUENCE_ID = 2
GAP_SEQUENCE_ID = 3
TWO_KEYS = 2
PUBLIC_KEY_ASSIGNMENT = b"public_key=b"


@dataclass(frozen=True, slots=True)
class _PublicKeySpec:
    """Test-only algorithm, public-key identity, and exact key bytes."""

    algorithm_id: str
    public_key: bytes
    public_key_id: str


def _spec(
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
) -> _PublicKeySpec:
    return _PublicKeySpec(
        algorithm_id=algorithm_id,
        public_key=public_key,
        public_key_id=public_key_id,
    )


OLD_SPEC = _spec()
NEW_SPEC = _spec(public_key=NEW_PUBLIC_KEY, public_key_id=NEW_KEY_ID)
NEW_ALGORITHM_SPEC = _spec(
    algorithm_id=NEW_ALGORITHM_ID,
    public_key=NEW_PUBLIC_KEY,
    public_key_id=NEW_KEY_ID,
)


class _DigestSigner:
    """Insecure deterministic signer used only to exercise the port contract."""

    def __init__(self, public_key: bytes) -> None:
        self.public_key: bytes = public_key
        self.requests: list[
            TicketAdmissionTelemetryLineageSignatureRequest
        ] = []

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSignatureRequest,
    ) -> TicketAdmissionTelemetryLineageSignerResult:
        self.requests.append(request)
        signature = sha256(self.public_key + request.payload).digest()
        return TicketAdmissionTelemetryLineageSignerResult(
            kind=TicketAdmissionTelemetryLineageSignerResultKind.SIGNED,
            signature=signature,
        )


class _DigestVerifier:
    """Insecure deterministic verifier used only for exact protocol tests."""

    def __init__(
        self,
        *,
        forced_kind: (
            TicketAdmissionTelemetryLineageVerifierResultKind | None
        ) = None,
    ) -> None:
        self.forced_kind: (
            TicketAdmissionTelemetryLineageVerifierResultKind | None
        ) = forced_kind
        self.requests: list[
            TicketAdmissionTelemetryLineageVerificationRequest
        ] = []

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageVerificationRequest,
    ) -> TicketAdmissionTelemetryLineageVerifierResult:
        self.requests.append(request)
        kind = self.forced_kind
        if kind is None:
            expected = sha256(request.public_key + request.payload).digest()
            kind = (
                TicketAdmissionTelemetryLineageVerifierResultKind.VERIFIED
                if expected == request.signature
                else TicketAdmissionTelemetryLineageVerifierResultKind.INVALID
            )
        return TicketAdmissionTelemetryLineageVerifierResult(kind=kind)


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


def _attempts() -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=2),
        failed=TicketAdmissionFailureTelemetry(capacity=2),
    )


def _document(
    elapsed_ns: int | None = None,
) -> TicketAdmissionTelemetryDocument:
    attempts = _attempts()
    if elapsed_ns is not None:
        _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def _claim(
    capture_sequence_id: int,
    *,
    key: _PublicKeySpec = OLD_SPEC,
    previous_attestation_fingerprint: str | None = None,
) -> TicketAdmissionTelemetryLineageSignatureClaim:
    return TicketAdmissionTelemetryLineageSignatureClaim(
        algorithm_id=key.algorithm_id,
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        public_key_fingerprint=(
            ticket_admission_telemetry_lineage_public_key_fingerprint(
                key.public_key
            )
        ),
        public_key_id=key.public_key_id,
        recorder_id=RECORDER_ID,
    )


def _attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageSignatureClaim,
    *,
    key: _PublicKeySpec = OLD_SPEC,
) -> TicketAdmissionTelemetryLineageSignatureAttestation:
    return create_ticket_admission_telemetry_lineage_signature_attestation(
        document,
        claim,
        _DigestSigner(key.public_key),
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> TicketAdmissionTelemetryLineageSignatureItem:
    return TicketAdmissionTelemetryLineageSignatureItem(
        attestation=attestation,
        document=document,
    )


def _trust_key(
    *,
    key: _PublicKeySpec = OLD_SPEC,
    public_key_fingerprint: str | None = None,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, None),
) -> TicketAdmissionTelemetryLineageSignatureTrustKey:
    first_capture_sequence_id, last_capture_sequence_id = window
    fingerprint = (
        ticket_admission_telemetry_lineage_public_key_fingerprint(
            key.public_key
        )
        if public_key_fingerprint is None
        else public_key_fingerprint
    )
    return TicketAdmissionTelemetryLineageSignatureTrustKey(
        algorithm_id=key.algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key=key.public_key,
        public_key_fingerprint=fingerprint,
        public_key_id=key.public_key_id,
    )


def _rotation_trust(
    *,
    rotate_algorithm: bool = False,
) -> TicketAdmissionTelemetryLineageSignatureTrust:
    return build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(
            key=(NEW_ALGORITHM_SPEC if rotate_algorithm else NEW_SPEC),
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _trust_key(
            window=(GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
        ),
    ))


def test_empty_trust_is_stable_and_calls_no_verifier() -> None:
    """An empty public-key trust set is valid but trusts no signature."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust(())
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    assert ticket_admission_telemetry_lineage_signature_trust_id() == TRUST_ID
    assert trust.trust_id == TRUST_ID
    assert trust.key_count == 0
    assert trust.keys == ()
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="algorithm and public-key identity are not in trust set",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert verifier.requests == []


def test_trust_sorts_composite_identity_and_hides_public_keys() -> None:
    """Construction orders algorithm/key pairs without exposing key bytes."""
    trust = _rotation_trust(rotate_algorithm=True)

    assert trust.key_count == TWO_KEYS
    assert tuple(
        (key.algorithm_id, key.public_key_id) for key in trust.keys
    ) == (
        (OLD_ALGORITHM_ID, OLD_KEY_ID),
        (NEW_ALGORITHM_ID, NEW_KEY_ID),
    )
    rendered = repr(trust).encode("utf-8")
    assert OLD_PUBLIC_KEY not in rendered
    assert NEW_PUBLIC_KEY not in rendered
    assert PUBLIC_KEY_ASSIGNMENT not in rendered


@pytest.mark.parametrize(
    ("keys", "max_keys", "message"),
    [
        (
            cast(
                "tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...]",
                cast("object", [_trust_key()]),
            ),
            1,
            "keys must use the exact immutable tuple type",
        ),
        ((), True, "key limit must be a positive integer"),
        (
            (
                _trust_key(),
                _trust_key(key=NEW_SPEC),
            ),
            1,
            "key count exceeds configured limit",
        ),
    ],
)
def test_invalid_build_container_or_limit_fails_closed(
    keys: tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...],
    max_keys: int,
    message: str,
) -> None:
    """Construction requires an exact bounded immutable key tuple."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_signature_trust(
            keys,
            max_keys=max_keys,
        )


def test_duplicate_algorithm_and_key_identity_fails_closed() -> None:
    """One algorithm/key pair cannot resolve to multiple keys or windows."""
    keys = (
        _trust_key(window=(0, 0)),
        _trust_key(key=_spec(public_key=NEW_PUBLIC_KEY), window=(1, None)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="duplicate algorithm and public-key identity",
    ):
        _ = build_ticket_admission_telemetry_lineage_signature_trust(keys)


def test_same_key_identity_is_allowed_under_distinct_algorithms() -> None:
    """Algorithm identity is an exact part of public-key trust selection."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
        _trust_key(
            key=_spec(
                algorithm_id=NEW_ALGORITHM_ID,
                public_key=NEW_PUBLIC_KEY,
            )
        ),
    ))

    assert trust.key_count == TWO_KEYS
    assert tuple(key.algorithm_id for key in trust.keys) == (
        OLD_ALGORITHM_ID,
        NEW_ALGORITHM_ID,
    )


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (
            _trust_key(key=_spec(algorithm_id="bad algorithm")),
            "algorithm identity must use canonical ASCII identity form",
        ),
        (
            _trust_key(key=_spec(public_key_id="bad key")),
            "public-key identity must use canonical ASCII identity form",
        ),
        (
            _trust_key(
                key=_spec(
                    public_key=cast(
                        "bytes",
                        cast("object", bytearray(OLD_PUBLIC_KEY)),
                    )
                ),
                public_key_fingerprint="invalid",
            ),
            "public key must use the exact bytes type",
        ),
        (
            _trust_key(
                key=_spec(public_key=b""),
                public_key_fingerprint="invalid",
            ),
            "public key cannot be empty",
        ),
        (
            _trust_key(public_key_fingerprint="invalid"),
            "public-key fingerprint does not match exact key bytes",
        ),
        (
            _trust_key(window=(True, None)),
            "first capture sequence identity must be a nonnegative integer",
        ),
        (
            _trust_key(window=(2, 1)),
            "last capture sequence precedes first capture sequence",
        ),
    ],
)
def test_invalid_trust_key_fields_fail_closed(
    key: TicketAdmissionTelemetryLineageSignatureTrustKey,
    message: str,
) -> None:
    """Malformed identities, key bytes, fingerprints, and windows fail."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_signature_trust((key,))


def test_oversized_public_key_fails_without_large_parameter_id() -> None:
    """Public-key bounds are inherited before trust construction succeeds."""
    key = b"x" * (DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES + 1)
    trust_key = TicketAdmissionTelemetryLineageSignatureTrustKey(
        algorithm_id=OLD_ALGORITHM_ID,
        first_capture_sequence_id=0,
        last_capture_sequence_id=None,
        public_key=key,
        public_key_fingerprint="invalid",
        public_key_id=OLD_KEY_ID,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="public key exceeds configured byte limit",
    ):
        _ = build_ticket_admission_telemetry_lineage_signature_trust((
            trust_key,
        ))


@pytest.mark.parametrize(
    "capture_sequence_id",
    [WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID],
)
def test_capture_window_endpoints_are_inclusive(
    capture_sequence_id: int,
) -> None:
    """Both trusted public-key window endpoints verify successfully."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(window=(WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID)),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(capture_sequence_id)),
    )
    verifier = _DigestVerifier()

    trusted = verify_ticket_admission_telemetry_lineage_signature_with_trust(
        item,
        verifier,
        trust,
    )

    assert len(verifier.requests) == 1
    assert trusted.trust_id == TRUST_ID
    assert trusted.algorithm_id == OLD_ALGORITHM_ID
    assert trusted.public_key_id == OLD_KEY_ID
    assert trusted.first_capture_sequence_id == WINDOW_FIRST_SEQUENCE_ID
    assert trusted.last_capture_sequence_id == WINDOW_LAST_SEQUENCE_ID
    assert (
        trusted.verified_signature.verified_item.verified.capture_sequence_id
        == capture_sequence_id
    )


@pytest.mark.parametrize(
    ("capture_sequence_id", "message"),
    [
        (GENESIS_SEQUENCE_ID, "precedes trusted public-key window"),
        (GAP_SEQUENCE_ID, "exceeds trusted public-key window"),
    ],
)
def test_capture_outside_trusted_window_calls_no_verifier(
    capture_sequence_id: int,
    message: str,
) -> None:
    """A valid signature is insufficient outside the selected key window."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(window=(WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID)),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(capture_sequence_id)),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match=message,
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert verifier.requests == []


@pytest.mark.parametrize(
    ("algorithm_id", "public_key_id"),
    [
        (NEW_ALGORITHM_ID, OLD_KEY_ID),
        (OLD_ALGORITHM_ID, UNKNOWN_KEY_ID),
    ],
)
def test_unknown_algorithm_or_key_identity_calls_no_verifier(
    algorithm_id: str,
    public_key_id: str,
) -> None:
    """Trust never substitutes an equal-looking algorithm or key identity."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(
            document,
            _claim(
                GENESIS_SEQUENCE_ID,
                key=_spec(
                    algorithm_id=algorithm_id,
                    public_key_id=public_key_id,
                ),
            ),
        ),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="algorithm and public-key identity are not in trust set",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert verifier.requests == []


def test_untrusted_exact_public_key_fingerprint_calls_no_verifier() -> None:
    """A selected algorithm/key identity still requires exact trusted bytes."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(key=_spec(public_key=WRONG_PUBLIC_KEY)),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="public-key fingerprint is not trusted",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert verifier.requests == []


def test_trusted_verification_returns_exact_selected_metadata() -> None:
    """Expose only selected nonsecret trust metadata after verification."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(window=(GENESIS_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID)),
    ))
    document = _document(LOW_ELAPSED_NS)
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    trusted = verify_ticket_admission_telemetry_lineage_signature_with_trust(
        item,
        verifier,
        trust,
    )

    assert len(verifier.requests) == 1
    assert trusted.algorithm_id == OLD_ALGORITHM_ID
    assert trusted.public_key_id == OLD_KEY_ID
    assert trusted.public_key_fingerprint == (
        ticket_admission_telemetry_lineage_public_key_fingerprint(
            OLD_PUBLIC_KEY
        )
    )
    assert trusted.first_capture_sequence_id == GENESIS_SEQUENCE_ID
    assert trusted.last_capture_sequence_id == WINDOW_LAST_SEQUENCE_ID
    assert trusted.trust_id == TRUST_ID
    assert trusted.verified_signature.algorithm_id == OLD_ALGORITHM_ID


def test_verifier_failure_is_wrapped_without_retry() -> None:
    """A typed invalid verifier outcome is one terminal trust failure."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier(
        forced_kind=TicketAdmissionTelemetryLineageVerifierResultKind.INVALID
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match=r"invalid trusted signature item:.*verifier returned invalid",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert len(verifier.requests) == 1


def test_same_key_comparison_preserves_same_capture() -> None:
    """Preserve ordinary same-key signature comparison semantics."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            item,
            item,
            verifier,
            trust=trust,
        )
    )

    assert len(verifier.requests) == TWO_KEYS
    assert comparison.common_recorder_lineage
    assert comparison.exact_attestation_match
    assert comparison.exact_document_match
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.SAME_CAPTURE
    )


def test_direct_successor_can_rotate_public_key() -> None:
    """Keep an adjacent predecessor valid across public-key rotation."""
    first_document = _document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            key=NEW_SPEC,
            previous_attestation_fingerprint=first_fingerprint,
        ),
        key=NEW_SPEC,
    )
    verifier = _DigestVerifier()

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            _item(first_document, first_attestation),
            _item(second_document, second_attestation),
            verifier,
            trust=_rotation_trust(),
        )
    )

    assert len(verifier.requests) == TWO_KEYS
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID
    assert comparison.direct_chain_link


def test_direct_successor_can_rotate_algorithm_and_public_key() -> None:
    """Trust selection may rotate both declared algorithm and public key."""
    first_document = _document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            key=NEW_ALGORITHM_SPEC,
            previous_attestation_fingerprint=first_fingerprint,
        ),
        key=NEW_ALGORITHM_SPEC,
    )

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            _item(first_document, first_attestation),
            _item(second_document, second_attestation),
            _DigestVerifier(),
            trust=_rotation_trust(rotate_algorithm=True),
        )
    )

    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


def test_rotated_ordered_gap_is_common_lineage_without_direct_link() -> None:
    """A trusted later key may verify a gap without claiming adjacency."""
    first_document = _document(LOW_ELAPSED_NS)
    second_document = _document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(
            second_document,
            _claim(
                GAP_SEQUENCE_ID,
                key=NEW_SPEC,
            ),
            key=NEW_SPEC,
        ),
    )

    comparison = (
        compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            first,
            second,
            _DigestVerifier(),
            trust=_rotation_trust(),
        )
    )

    assert comparison.common_recorder_lineage
    assert not comparison.direct_chain_link
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.ORDERED_GAP
    )
    assert comparison.sequence_gap == GAP_SEQUENCE_ID


def test_rotated_same_sequence_fork_still_fails_closed() -> None:
    """Distinct trusted keys cannot authorize two documents at one sequence."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
        _trust_key(key=NEW_SPEC),
    ))
    first_document = _document(LOW_ELAPSED_NS)
    second_document = _document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(
            second_document,
            _claim(
                GENESIS_SEQUENCE_ID,
                key=NEW_SPEC,
            ),
            key=NEW_SPEC,
        ),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="capture sequence fork detected",
    ):
        _ = compare_ticket_admission_telemetry_lineage_signatures_with_trust(
            first,
            second,
            _DigestVerifier(),
            trust=trust,
        )


@pytest.mark.parametrize(
    ("trust", "message"),
    [
        (
            replace(_rotation_trust(), trust_id="unsupported"),
            "trust identity is unsupported",
        ),
        (
            replace(_rotation_trust(), key_count=1),
            "trust key count is inconsistent",
        ),
        (
            replace(
                _rotation_trust(),
                keys=tuple(reversed(_rotation_trust().keys)),
            ),
            "uniquely ordered by algorithm and identity",
        ),
    ],
)
def test_tampered_trust_metadata_fails_before_verifier(
    trust: TicketAdmissionTelemetryLineageSignatureTrust,
    message: str,
) -> None:
    """Trust identity, count, and canonical ordering are revalidated on use."""
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match=message,
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            trust,
        )
    assert verifier.requests == []


def test_tampered_trust_key_fails_before_verifier() -> None:
    """Trust use recomputes the exact public-key fingerprint every time."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    tampered_key = replace(trust.keys[0], public_key=WRONG_PUBLIC_KEY)
    tampered = replace(trust, keys=(tampered_key,))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="public-key fingerprint does not match exact key bytes",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            tampered,
        )
    assert verifier.requests == []


def test_foreign_trust_and_item_types_fail_before_verifier() -> None:
    """Equal-looking foreign containers cannot enter signature trust."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    document = _document()
    item = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="trust must use the exact signature trust type",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            item,
            verifier,
            cast(
                "TicketAdmissionTelemetryLineageSignatureTrust",
                cast("object", trust.keys),
            ),
        )
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureTrustError,
        match="item must use the exact signature item type",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_with_trust(
            cast(
                "TicketAdmissionTelemetryLineageSignatureItem",
                cast("object", document),
            ),
            verifier,
            trust,
        )
    assert verifier.requests == []


def test_trusted_result_representation_contains_no_public_key_bytes() -> None:
    """Successful trust metadata does not retain or display public-key bytes."""
    trust = build_ticket_admission_telemetry_lineage_signature_trust((
        _trust_key(),
    ))
    document = _document()
    trusted = verify_ticket_admission_telemetry_lineage_signature_with_trust(
        _item(
            document,
            _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
        ),
        _DigestVerifier(),
        trust,
    )

    rendered = repr(trusted).encode("utf-8")
    assert OLD_PUBLIC_KEY not in rendered
    assert PUBLIC_KEY_ASSIGNMENT not in rendered
