# File:
#   - test_ticket_admission_telemetry_lineage_signature.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage_signature.py
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
#   - Detached public-key lineage signature-port regressions.
# - Must-Not:
#   - Require CUDA, claim test cryptography is secure, discover trust, or
#     change admission.
# - Allows:
#   - Inputs: synthetic documents, claims, public keys, and caller test ports.
#   - Outputs: canonical, call-count, key-binding, chain, and failure
#     assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when provider sessions, concrete algorithms, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact detached-signature behavior.
# - Summary:
#   - Caller-supplied public-key lineage signature regressions.
# - Description:
#   - Proves exact bytes cross signer/verifier ports without selecting crypto.
# - Usage:
#   - Runs without accelerator hardware, filesystem access, or external keys.
# - Defaults:
#   - Uses a deterministic insecure digest port only as protocol test evidence.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage.py
#
# Large file:
#   - false
#

"""Detached caller-supplied public-key lineage signature tests."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import replace
from hashlib import sha256
from json import dumps
from json import loads
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
        TicketAdmissionTelemetryLineageSigner,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageVerificationRequest,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.exact_primitives import AcceleratorExecutionError
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
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    compare_verified_ticket_admission_telemetry_lineage,
)
from accelerator.ticket_admission_telemetry_lineage import (
    create_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage import (
    verify_ticket_admission_telemetry_lineage_item,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureClaim,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureError,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureItem,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureVerificationItem,
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
    compare_ticket_admission_telemetry_lineage_signatures,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    create_ticket_admission_telemetry_lineage_signature_attestation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    decode_ticket_admission_telemetry_lineage_signature_attestation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    encode_ticket_admission_telemetry_lineage_signature_attestation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_signature_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_signature_id,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    verify_ticket_admission_telemetry_lineage_signature_item,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

SIGNATURE_ID = "caller-owned-ticket-admission-telemetry-lineage-signature-v1"
SIGNATURE_PREFIX = "ticket-admission-telemetry-lineage-signature-v1:sha256:"
PUBLIC_KEY_PREFIX = (
    "ticket-admission-telemetry-lineage-public-key-v1:sha256:"
)
HMAC_PREFIX = "ticket-admission-telemetry-lineage-v1:sha256:"
ALGORITHM_ID = "test-only-public-digest-v1"
PUBLIC_KEY_ID = "public.test-key"
ROTATED_PUBLIC_KEY_ID = "public.rotated-key"
PUBLIC_KEY = b"caller-owned-test-public-key"
ROTATED_PUBLIC_KEY = b"caller-owned-rotated-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-public-key"
HMAC_KEY_ID = "hmac.test-key"
HMAC_SECRET = b"caller-owned-hmac-transition-key!!"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "signature-test-workload-v1"
BENCHMARK_ID = "signature-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
GAP_SEQUENCE_ID = 2
SIGNATURE_BYTES = 32
TWO_CALLS = 2
SIGNATURE_FIELD = b"signature_base64"
SIGNATURE_ENCODING_FIELD = b"signature_encoding_id"
SPACE = b" "
UNSUPPORTED_PREDECESSOR = "unsupported:sha256:" + "0" * 64


class _DigestSigner:
    """Insecure deterministic signer used only to exercise the port contract."""

    def __init__(
        self,
        public_key: bytes,
        *,
        kind: TicketAdmissionTelemetryLineageSignerResultKind = (
            TicketAdmissionTelemetryLineageSignerResultKind.SIGNED
        ),
        signature: bytes | None = None,
    ) -> None:
        self.public_key: bytes = public_key
        self.kind: TicketAdmissionTelemetryLineageSignerResultKind = kind
        self.requests: list[
            TicketAdmissionTelemetryLineageSignatureRequest
        ] = []
        self.signature: bytes | None = signature

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSignatureRequest,
    ) -> TicketAdmissionTelemetryLineageSignerResult:
        self.requests.append(request)
        signature = self.signature
        if signature is None and self.kind is (
            TicketAdmissionTelemetryLineageSignerResultKind.SIGNED
        ):
            signature = sha256(self.public_key + request.payload).digest()
        return TicketAdmissionTelemetryLineageSignerResult(
            kind=self.kind,
            signature=signature,
        )


class _StaticSigner:
    """Return one exact signer result without substituting test bytes."""

    def __init__(
        self,
        result: TicketAdmissionTelemetryLineageSignerResult,
    ) -> None:
        self.result: TicketAdmissionTelemetryLineageSignerResult = result
        self.requests: list[
            TicketAdmissionTelemetryLineageSignatureRequest
        ] = []

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSignatureRequest,
    ) -> TicketAdmissionTelemetryLineageSignerResult:
        self.requests.append(request)
        return self.result


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
        report = _report()
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
        _ = attempts.record_failed(
            report,
            elapsed_ns=elapsed_ns + 1,
            error=AcceleratorExecutionError("private signature detail"),
        )
    return capture_ticket_admission_telemetry_document(attempts)


def _claim(
    capture_sequence_id: int,
    *,
    public_key: bytes = PUBLIC_KEY,
    public_key_id: str = PUBLIC_KEY_ID,
    previous_attestation_fingerprint: str | None = None,
) -> TicketAdmissionTelemetryLineageSignatureClaim:
    return TicketAdmissionTelemetryLineageSignatureClaim(
        algorithm_id=ALGORITHM_ID,
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        public_key_fingerprint=(
            ticket_admission_telemetry_lineage_public_key_fingerprint(
                public_key
            )
        ),
        public_key_id=public_key_id,
        recorder_id=RECORDER_ID,
    )


def _attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageSignatureClaim,
    *,
    public_key: bytes = PUBLIC_KEY,
    signer: TicketAdmissionTelemetryLineageSigner | None = None,
) -> TicketAdmissionTelemetryLineageSignatureAttestation:
    selected = _DigestSigner(public_key) if signer is None else signer
    return create_ticket_admission_telemetry_lineage_signature_attestation(
        document,
        claim,
        selected,
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> TicketAdmissionTelemetryLineageSignatureItem:
    return TicketAdmissionTelemetryLineageSignatureItem(
        attestation=attestation,
        document=document,
    )


def _verification_item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
    public_key: bytes,
) -> TicketAdmissionTelemetryLineageSignatureVerificationItem:
    return TicketAdmissionTelemetryLineageSignatureVerificationItem(
        item=_item(document, attestation),
        public_key=public_key,
    )


def _mapping(encoded: bytes) -> dict[str, object]:
    return cast("dict[str, object]", loads(encoded.decode("utf-8")))


def _encoded_mapping(mapping: dict[str, object]) -> bytes:
    return dumps(
        mapping,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def test_signature_identity_and_public_key_fingerprint_are_stable() -> None:
    """Port and exact public-key identities have stable versioned prefixes."""
    fingerprint = ticket_admission_telemetry_lineage_public_key_fingerprint(
        PUBLIC_KEY
    )

    assert ticket_admission_telemetry_lineage_signature_id() == SIGNATURE_ID
    assert fingerprint == f"{PUBLIC_KEY_PREFIX}{sha256(PUBLIC_KEY).hexdigest()}"


def test_signer_receives_exact_canonical_unsigned_payload_once() -> None:
    """Creation makes one signer call with exact immutable claim metadata."""
    signer = _DigestSigner(PUBLIC_KEY)
    document = _document(LOW_ELAPSED_NS)
    claim = _claim(GENESIS_SEQUENCE_ID)

    attestation = _attestation(
        document,
        claim,
        signer=signer,
    )

    assert len(signer.requests) == 1
    request = signer.requests[0]
    assert request.algorithm_id == ALGORITHM_ID
    assert request.public_key_id == PUBLIC_KEY_ID
    assert request.public_key_fingerprint == claim.public_key_fingerprint
    assert SIGNATURE_FIELD not in request.payload
    assert SIGNATURE_ENCODING_FIELD in request.payload
    expected = sha256(PUBLIC_KEY + request.payload).digest()
    assert b64encode(expected).decode("ascii") == attestation.signature_base64


def test_attestation_is_canonical_and_roundtrips() -> None:
    """Detached attestations use compact sorted JSON and exact Base64."""
    document = _document(LOW_ELAPSED_NS)
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))

    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        attestation
    )

    assert encoded == _encoded_mapping(_mapping(encoded))
    assert decode_ticket_admission_telemetry_lineage_signature_attestation(
        encoded
    ) == attestation
    assert SPACE not in encoded


def test_attestation_fingerprint_hashes_exact_canonical_bytes() -> None:
    """Detached attestation identity uses its own canonical SHA-256 prefix."""
    attestation = _attestation(_document(), _claim(GENESIS_SEQUENCE_ID))
    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        attestation
    )

    assert ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
        attestation
    ) == f"{SIGNATURE_PREFIX}{sha256(encoded).hexdigest()}"


def test_verifier_receives_exact_bound_material_once() -> None:
    """Verification gets one exact key, signature, and payload call."""
    document = _document(LOW_ELAPSED_NS)
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    verifier = _DigestVerifier()

    verified = verify_ticket_admission_telemetry_lineage_signature_item(
        _item(document, attestation),
        verifier,
        public_key=PUBLIC_KEY,
    )

    assert len(verifier.requests) == 1
    request = verifier.requests[0]
    assert request.algorithm_id == ALGORITHM_ID
    assert request.public_key == PUBLIC_KEY
    assert request.public_key_id == PUBLIC_KEY_ID
    assert request.public_key_fingerprint == (
        ticket_admission_telemetry_lineage_public_key_fingerprint(PUBLIC_KEY)
    )
    assert request.signature == sha256(PUBLIC_KEY + request.payload).digest()
    assert verified.signature_byte_count == SIGNATURE_BYTES
    assert verified.algorithm_id == ALGORITHM_ID
    assert verified.public_key_id == PUBLIC_KEY_ID
    assert verified.verified_item.verified.key_id == PUBLIC_KEY_ID


def test_repeated_explicit_sign_and_verify_operations_do_not_cache() -> None:
    """Every explicit operation performs a fresh single signer/verifier call."""
    document = _document()
    signer = _DigestSigner(PUBLIC_KEY)
    verifier = _DigestVerifier()

    first = _attestation(document, _claim(GENESIS_SEQUENCE_ID), signer=signer)
    second = _attestation(document, _claim(GENESIS_SEQUENCE_ID), signer=signer)
    _ = verify_ticket_admission_telemetry_lineage_signature_item(
        _item(document, first),
        verifier,
        public_key=PUBLIC_KEY,
    )
    _ = verify_ticket_admission_telemetry_lineage_signature_item(
        _item(document, second),
        verifier,
        public_key=PUBLIC_KEY,
    )

    assert len(signer.requests) == TWO_CALLS
    assert len(verifier.requests) == TWO_CALLS
    assert first == second


def test_port_objects_hide_payload_key_and_signature_bytes_from_repr() -> None:
    """Public representations do not expose bulk key or signature material."""
    signer = _DigestSigner(PUBLIC_KEY)
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID),
        signer=signer,
    )
    verifier = _DigestVerifier()
    _ = verify_ticket_admission_telemetry_lineage_signature_item(
        _item(document, attestation),
        verifier,
        public_key=PUBLIC_KEY,
    )
    signature = sha256(PUBLIC_KEY + signer.requests[0].payload).digest()

    assert PUBLIC_KEY not in repr(verifier.requests[0]).encode("utf-8")
    assert signature not in repr(verifier.requests[0]).encode("utf-8")
    assert signer.requests[0].payload not in repr(signer.requests[0]).encode(
        "utf-8"
    )
    result = TicketAdmissionTelemetryLineageSignerResult(
        kind=TicketAdmissionTelemetryLineageSignerResultKind.SIGNED,
        signature=signature,
    )
    assert signature not in repr(result).encode("utf-8")


def test_direct_successor_comparison_works_with_one_public_key() -> None:
    """Two independently verified signatures retain direct chain semantics."""
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
            previous_attestation_fingerprint=first_fingerprint,
        ),
    )
    verifier = _DigestVerifier()

    comparison = compare_ticket_admission_telemetry_lineage_signatures(
        _verification_item(first_document, first_attestation, PUBLIC_KEY),
        _verification_item(second_document, second_attestation, PUBLIC_KEY),
        verifier,
    )

    assert len(verifier.requests) == TWO_CALLS
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.common_recorder_lineage
    assert comparison.direct_chain_link
    assert comparison.sequence_gap == SUCCESSOR_SEQUENCE_ID


def test_direct_successor_comparison_supports_public_key_rotation() -> None:
    """A direct successor may bind a different exact public key and key ID."""
    first_document = _document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
        public_key=PUBLIC_KEY,
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_claim = _claim(
        SUCCESSOR_SEQUENCE_ID,
        public_key=ROTATED_PUBLIC_KEY,
        public_key_id=ROTATED_PUBLIC_KEY_ID,
        previous_attestation_fingerprint=first_fingerprint,
    )
    second_attestation = _attestation(
        second_document,
        second_claim,
        public_key=ROTATED_PUBLIC_KEY,
    )

    comparison = compare_ticket_admission_telemetry_lineage_signatures(
        _verification_item(first_document, first_attestation, PUBLIC_KEY),
        _verification_item(
            second_document,
            second_attestation,
            ROTATED_PUBLIC_KEY,
        ),
        _DigestVerifier(),
    )

    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == PUBLIC_KEY_ID
    assert comparison.second.key_id == ROTATED_PUBLIC_KEY_ID


def test_signature_successor_can_follow_verified_hmac_capture() -> None:
    """An explicit signature capture can succeed a verified HMAC capture."""
    first_document = _document(LOW_ELAPSED_NS)
    hmac_claim = TicketAdmissionTelemetryLineageClaim(
        capture_sequence_id=GENESIS_SEQUENCE_ID,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        key_id=HMAC_KEY_ID,
        previous_attestation_fingerprint=None,
        recorder_id=RECORDER_ID,
    )
    hmac_attestation = create_ticket_admission_telemetry_lineage_attestation(
        first_document,
        hmac_claim,
        secret_key=HMAC_SECRET,
    )
    hmac_fingerprint = (
        ticket_admission_telemetry_lineage_attestation_fingerprint(
            hmac_attestation
        )
    )
    first_verified = verify_ticket_admission_telemetry_lineage_item(
        TicketAdmissionTelemetryLineageItem(
            attestation=hmac_attestation,
            document=first_document,
        ),
        secret_key=HMAC_SECRET,
        trusted_key_id=HMAC_KEY_ID,
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            previous_attestation_fingerprint=hmac_fingerprint,
        ),
    )
    second_verified = verify_ticket_admission_telemetry_lineage_signature_item(
        _item(second_document, second_attestation),
        _DigestVerifier(),
        public_key=PUBLIC_KEY,
    )

    comparison = compare_verified_ticket_admission_telemetry_lineage(
        first_verified,
        second_verified.verified_item,
    )

    assert hmac_fingerprint.startswith(HMAC_PREFIX)
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == HMAC_KEY_ID
    assert comparison.second.key_id == PUBLIC_KEY_ID


def test_wrong_public_key_fails_before_verifier_call() -> None:
    """A mismatched exact public-key fingerprint never reaches the verifier."""
    document = _document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="public-key fingerprint does not match",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(document, attestation),
            verifier,
            public_key=WRONG_PUBLIC_KEY,
        )

    assert verifier.requests == []


def test_wrong_document_fails_before_verifier_call() -> None:
    """A signature cannot be replayed against a different telemetry document."""
    original = _document(LOW_ELAPSED_NS)
    attestation = _attestation(original, _claim(GENESIS_SEQUENCE_ID))
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="document fingerprint does not match",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(_document(HIGH_ELAPSED_NS), attestation),
            verifier,
            public_key=PUBLIC_KEY,
        )

    assert verifier.requests == []


def test_tampered_signature_is_rejected_by_explicit_verifier() -> None:
    """Structurally valid signature bytes still require caller verification."""
    document = _document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    tampered = replace(
        attestation,
        signature_base64=b64encode(b"x" * SIGNATURE_BYTES).decode("ascii"),
    )
    verifier = _DigestVerifier()

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="verifier returned invalid",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(document, tampered),
            verifier,
            public_key=PUBLIC_KEY,
        )

    assert len(verifier.requests) == 1


@pytest.mark.parametrize(
    "kind",
    [
        TicketAdmissionTelemetryLineageSignerResultKind.UNAVAILABLE,
        TicketAdmissionTelemetryLineageSignerResultKind.FAILED,
    ],
)
def test_typed_signer_failure_stops_after_one_call(
    kind: TicketAdmissionTelemetryLineageSignerResultKind,
) -> None:
    """Unavailable and failed signer outcomes stop without retry."""
    signer = _DigestSigner(PUBLIC_KEY, kind=kind)

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=rf"signer returned {kind.value}",
    ):
        _ = _attestation(
            _document(),
            _claim(GENESIS_SEQUENCE_ID),
            signer=signer,
        )

    assert len(signer.requests) == 1


@pytest.mark.parametrize(
    "kind",
    [
        TicketAdmissionTelemetryLineageVerifierResultKind.INVALID,
        TicketAdmissionTelemetryLineageVerifierResultKind.UNAVAILABLE,
        TicketAdmissionTelemetryLineageVerifierResultKind.FAILED,
    ],
)
def test_typed_verifier_failure_stops_after_one_call(
    kind: TicketAdmissionTelemetryLineageVerifierResultKind,
) -> None:
    """Invalid, unavailable, and failed verification never retry."""
    document = _document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    verifier = _DigestVerifier(forced_kind=kind)

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=rf"verifier returned {kind.value}",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(document, attestation),
            verifier,
            public_key=PUBLIC_KEY,
        )

    assert len(verifier.requests) == 1


def test_nonsigned_result_cannot_contain_signature_bytes() -> None:
    """Failure outcomes cannot smuggle detached signature material."""
    signer = _DigestSigner(
        PUBLIC_KEY,
        kind=TicketAdmissionTelemetryLineageSignerResultKind.FAILED,
        signature=b"private-vendor-detail",
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="nonsigned result cannot contain signature bytes",
    ):
        _ = _attestation(
            _document(),
            _claim(GENESIS_SEQUENCE_ID),
            signer=signer,
        )


def test_signed_result_requires_exact_nonempty_bounded_bytes() -> None:
    """Signed outcomes enforce exact bytes and the fixed signature limit."""
    foreign = cast("bytes | None", cast("object", bytearray(b"x")))
    cases = (
        (None, "signed result must contain exact signature bytes"),
        (foreign, "signed result must contain exact signature bytes"),
        (b"", "signature cannot be empty"),
        (
            b"x" * (DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES + 1),
            "signature exceeds configured byte limit",
        ),
    )
    for signature, pattern in cases:
        signer = _StaticSigner(TicketAdmissionTelemetryLineageSignerResult(
            kind=TicketAdmissionTelemetryLineageSignerResultKind.SIGNED,
            signature=signature,
        ))
        with pytest.raises(
            TicketAdmissionTelemetryLineageSignatureError,
            match=pattern,
        ):
            _ = _attestation(
                _document(),
                _claim(GENESIS_SEQUENCE_ID),
                signer=signer,
            )


def test_exact_maximum_signature_size_is_accepted() -> None:
    """The fixed signature byte limit is inclusive at its exact boundary."""
    signature = b"x" * DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES
    signer = _DigestSigner(PUBLIC_KEY, signature=signature)

    attestation = _attestation(
        _document(),
        _claim(GENESIS_SEQUENCE_ID),
        signer=signer,
    )

    assert attestation.signature_base64 == b64encode(signature).decode("ascii")


def test_foreign_signer_result_type_and_kind_fail_closed() -> None:
    """Equal-looking foreign signer values cannot enter the contract."""

    class ForeignResultSigner:
        def __call__(
            self,
            request: TicketAdmissionTelemetryLineageSignatureRequest,
        ) -> TicketAdmissionTelemetryLineageSignerResult:
            del request
            return cast(
                "TicketAdmissionTelemetryLineageSignerResult",
                cast("object", b"foreign"),
            )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="signer result must use the exact result type",
    ):
        _ = create_ticket_admission_telemetry_lineage_signature_attestation(
            _document(),
            _claim(GENESIS_SEQUENCE_ID),
            ForeignResultSigner(),
        )

    malformed_kind = TicketAdmissionTelemetryLineageSignerResult(
        kind=cast(
            "TicketAdmissionTelemetryLineageSignerResultKind",
            cast("object", "signed"),
        ),
        signature=b"x",
    )
    signer = _StaticSigner(malformed_kind)
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="signer result kind must use the exact enum",
    ):
        _ = _attestation(
            _document(),
            _claim(GENESIS_SEQUENCE_ID),
            signer=signer,
        )


def test_foreign_verifier_result_type_and_kind_fail_closed() -> None:
    """Equal-looking foreign verifier values cannot enter the contract."""
    document = _document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))

    class ForeignResultVerifier:
        def __call__(
            self,
            request: TicketAdmissionTelemetryLineageVerificationRequest,
        ) -> TicketAdmissionTelemetryLineageVerifierResult:
            del request
            return cast(
                "TicketAdmissionTelemetryLineageVerifierResult",
                cast("object", "verified"),
            )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="verifier result must use the exact result type",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(document, attestation),
            ForeignResultVerifier(),
            public_key=PUBLIC_KEY,
        )

    class ForeignKindVerifier:
        def __call__(
            self,
            request: TicketAdmissionTelemetryLineageVerificationRequest,
        ) -> TicketAdmissionTelemetryLineageVerifierResult:
            del request
            return TicketAdmissionTelemetryLineageVerifierResult(
                kind=cast(
                    "TicketAdmissionTelemetryLineageVerifierResultKind",
                    cast("object", "verified"),
                )
            )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="verifier result kind must use the exact enum",
    ):
        _ = verify_ticket_admission_telemetry_lineage_signature_item(
            _item(document, attestation),
            ForeignKindVerifier(),
            public_key=PUBLIC_KEY,
        )


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("algorithm_id", "bad algorithm", "algorithm identity"),
        ("capture_sequence_id", True, "capture sequence identity"),
        ("capture_sequence_id", -1, "capture sequence identity"),
        ("completed_stream_id", "bad stream", "completed stream identity"),
        ("failed_stream_id", "bad stream", "failed stream identity"),
        ("public_key_id", "bad key", "public-key identity"),
        ("recorder_id", "bad recorder", "recorder identity"),
        (
            "public_key_fingerprint",
            "invalid",
            "public-key fingerprint is malformed",
        ),
    ],
)
def test_invalid_claim_fields_fail_before_signer_call(
    field: str,
    value: object,
    pattern: str,
) -> None:
    """All claim identities and sequence values fail before external signing."""
    signer = _DigestSigner(PUBLIC_KEY)
    malformed = replace(_claim(GENESIS_SEQUENCE_ID), **{field: value})

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=pattern,
    ):
        _ = create_ticket_admission_telemetry_lineage_signature_attestation(
            _document(),
            malformed,
            signer,
        )

    assert signer.requests == []


def test_predecessor_rules_accept_hmac_or_signature() -> None:
    """Predecessors are absent at genesis and may name either lineage family."""
    signature_predecessor = f"{SIGNATURE_PREFIX}{'0' * 64}"
    hmac_predecessor = f"{HMAC_PREFIX}{'1' * 64}"

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="genesis capture cannot name a predecessor",
    ):
        _ = _attestation(
            _document(),
            _claim(
                GENESIS_SEQUENCE_ID,
                previous_attestation_fingerprint=signature_predecessor,
            ),
        )

    for predecessor in (signature_predecessor, hmac_predecessor):
        attestation = _attestation(
            _document(),
            _claim(
                SUCCESSOR_SEQUENCE_ID,
                previous_attestation_fingerprint=predecessor,
            ),
        )
        assert attestation.previous_attestation_fingerprint == predecessor


def test_invalid_predecessor_prefix_fails_before_signer_call() -> None:
    """Only exact HMAC or detached-signature fingerprints may link captures."""
    signer = _DigestSigner(PUBLIC_KEY)

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="previous attestation fingerprint is malformed",
    ):
        _ = _attestation(
            _document(),
            _claim(
                SUCCESSOR_SEQUENCE_ID,
                previous_attestation_fingerprint=UNSUPPORTED_PREDECESSOR,
            ),
            signer=signer,
        )

    assert signer.requests == []


@pytest.mark.parametrize(
    ("public_key", "pattern"),
    [
        (cast("bytes", cast("object", bytearray(PUBLIC_KEY))), "exact bytes"),
        (b"", "cannot be empty"),
    ],
)
def test_public_key_fingerprint_rejects_invalid_key_bytes(
    public_key: bytes,
    pattern: str,
) -> None:
    """Public-key identity accepts only nonempty bounded immutable bytes."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=pattern,
    ):
        _ = ticket_admission_telemetry_lineage_public_key_fingerprint(
            public_key
        )


def test_public_key_fingerprint_rejects_oversized_key() -> None:
    """An oversized key fails without a huge parametrized test ID."""
    public_key = b"x" * (
        DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES + 1
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="exceeds configured byte limit",
    ):
        _ = ticket_admission_telemetry_lineage_public_key_fingerprint(
            public_key
        )


def test_exact_maximum_public_key_size_is_accepted() -> None:
    """The fixed public-key byte limit is inclusive at its exact boundary."""
    key = b"x" * DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES

    fingerprint = ticket_admission_telemetry_lineage_public_key_fingerprint(key)

    assert fingerprint.startswith(PUBLIC_KEY_PREFIX)


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("attestation_id", "unsupported", "attestation identity"),
        ("schema_version", True, "attestation schema"),
        ("schema_version", 2, "attestation schema"),
        (
            "signature_encoding_id",
            "hex",
            "signature encoding is unsupported",
        ),
        ("document_fingerprint", "invalid", "document fingerprint"),
        (
            "public_key_fingerprint",
            "invalid",
            "public-key fingerprint is malformed",
        ),
    ],
)
def test_forged_attestation_header_fails_encoding(
    field: str,
    value: object,
    pattern: str,
) -> None:
    """Typed attestations revalidate every identity before encoding."""
    attestation = _attestation(_document(), _claim(GENESIS_SEQUENCE_ID))
    malformed = replace(attestation, **{field: value})

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=pattern,
    ):
        _ = encode_ticket_admission_telemetry_lineage_signature_attestation(
            malformed
        )


@pytest.mark.parametrize(
    ("signature_base64", "pattern"),
    [
        ("", "signature payload must be a non-empty string"),
        ("not-base64", "signature is not Base64"),
        (
            b64encode(
                b"x" * (DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES + 1)
            ).decode("ascii"),
            "signature exceeds configured byte limit",
        ),
    ],
)
def test_forged_signature_payload_fails_encoding(
    signature_base64: str,
    pattern: str,
) -> None:
    """Detached signature payloads require bounded canonical Base64 bytes."""
    malformed = replace(
        _attestation(_document(), _claim(GENESIS_SEQUENCE_ID)),
        signature_base64=signature_base64,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=pattern,
    ):
        _ = encode_ticket_admission_telemetry_lineage_signature_attestation(
            malformed
        )


def test_decoder_rejects_duplicate_unknown_and_noncanonical_json() -> None:
    """Duplicate, unknown, and whitespace-mutated attestation JSON fails."""
    attestation = _attestation(_document(), _claim(GENESIS_SEQUENCE_ID))
    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        attestation
    )
    duplicate = encoded.replace(
        b'"schema_version":1',
        b'"schema_version":1,"schema_version":1',
        1,
    )
    mapping = _mapping(encoded)
    mapping["unknown"] = 0
    unknown = _encoded_mapping(mapping)

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="contains duplicate keys",
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            duplicate
        )
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="encoded attestation keys are unsupported",
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            unknown
        )
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="canonical JSON",
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            SPACE + encoded
        )


@pytest.mark.parametrize(
    ("payload", "pattern"),
    [
        (b"", "cannot be empty"),
        (b"[]", "root must be an object"),
        (b"{", "not valid JSON"),
        (b"\xff", "must use UTF-8"),
    ],
)
def test_decoder_rejects_malformed_bytes(payload: bytes, pattern: str) -> None:
    """Malformed bytes fail before structural or cryptographic verification."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match=pattern,
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            payload
        )


@pytest.mark.parametrize("max_bytes", [0, True])
def test_decoder_rejects_invalid_byte_limit(max_bytes: int) -> None:
    """The decode bound must be a positive exact integer."""
    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        _attestation(_document(), _claim(GENESIS_SEQUENCE_ID))
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="decode byte limit must be a positive integer",
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            encoded,
            max_bytes=max_bytes,
        )


def test_decoder_enforces_exact_outer_byte_limit() -> None:
    """The complete canonical attestation is bounded before JSON parsing."""
    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        _attestation(_document(), _claim(GENESIS_SEQUENCE_ID))
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageSignatureError,
        match="exceeds configured byte limit",
    ):
        _ = decode_ticket_admission_telemetry_lineage_signature_attestation(
            encoded,
            max_bytes=len(encoded) - 1,
        )
    assert decode_ticket_admission_telemetry_lineage_signature_attestation(
        encoded,
        max_bytes=len(encoded),
    )
