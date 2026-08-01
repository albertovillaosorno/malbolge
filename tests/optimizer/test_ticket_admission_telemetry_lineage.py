# File:
#   - test_ticket_admission_telemetry_lineage.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage.py
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
#   - Canonical authenticated telemetry lineage regressions.
# - Must-Not:
#   - Require CUDA, persist secrets, infer unsigned lineage, or change
#     admission.
# - Allows:
#   - Inputs: synthetic documents, explicit claims, and caller-owned test keys.
#   - Outputs: canonical, authentication, chain, collision, and failure
#     assertions.
#   - Side effects: temporary monkeypatching of local digest and identity
#     helpers.
# - Split-When:
#   - Split when concrete signature algorithms, PKI, or provider lifecycles
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact authenticated-lineage behavior.
# - Summary:
#   - Caller-trusted telemetry lineage regressions.
# - Description:
#   - Proves explicit HMAC claims bind exact documents and fail closed.
# - Usage:
#   - Runs without accelerator hardware, filesystem access, or external keys.
# - Defaults:
#   - Uses deterministic 32-byte test keys and schema-v1 canonical JSON.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
#
# Large file:
#   - false
#

"""Canonical caller-trusted telemetry lineage tests."""

from __future__ import annotations

from dataclasses import replace
from json import dumps
from json import loads
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryLineageAttestation,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator import ticket_admission_telemetry_lineage as lineage_module
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
    TicketAdmissionTelemetryLineageError,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageItem,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    compare_ticket_admission_telemetry_lineage,
)
from accelerator.ticket_admission_telemetry_lineage import (
    create_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    decode_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    encode_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_id,
)
from accelerator.ticket_admission_telemetry_lineage import (
    verify_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

LINEAGE_ID = "authenticated-ticket-admission-telemetry-lineage-v1"
LINEAGE_PREFIX = "ticket-admission-telemetry-lineage-v1:sha256:"
DOCUMENT_PREFIX = "ticket-admission-telemetry-document-v1:sha256:"
KEY_ID = "local.test-key"
SECRET_KEY = b"caller-owned-lineage-test-secret!!"
WRONG_KEY = b"different-caller-owned-test-key!!"
RECORDER_ID = "recorder.test"
OTHER_RECORDER_ID = "recorder.other"
COMPLETED_STREAM_ID = "completed.main"
OTHER_COMPLETED_STREAM_ID = "completed.other"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "lineage-test-workload-v1"
BENCHMARK_ID = "lineage-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
GAP_SEQUENCE_ID = 2
SEQUENCE_GAP = 2
UNKNOWN_MUTATION = "unknown"
NONCANONICAL_MUTATION = "noncanonical"
OVERSIZED_MUTATION = "oversized"


class _ConstantDigest:
    @staticmethod
    def hexdigest() -> str:
        """Return one deterministic forged digest.

        Returns:
            A fixed 64-character hexadecimal string.

        """
        return "0" * 64


def _constant_sha256(payload: bytes) -> _ConstantDigest:
    _ = payload
    return _ConstantDigest()


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


def _empty_document() -> TicketAdmissionTelemetryDocument:
    return capture_ticket_admission_telemetry_document(_attempts())


def _completed_document(elapsed_ns: int) -> TicketAdmissionTelemetryDocument:
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def _claim(
    capture_sequence_id: int,
) -> TicketAdmissionTelemetryLineageClaim:
    return TicketAdmissionTelemetryLineageClaim(
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        key_id=KEY_ID,
        previous_attestation_fingerprint=None,
        recorder_id=RECORDER_ID,
    )


def _attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageClaim,
) -> TicketAdmissionTelemetryLineageAttestation:
    return create_ticket_admission_telemetry_lineage_attestation(
        document,
        claim,
        secret_key=SECRET_KEY,
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> TicketAdmissionTelemetryLineageItem:
    return TicketAdmissionTelemetryLineageItem(
        attestation=attestation,
        document=document,
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


def test_genesis_round_trip_and_verification_are_stable() -> None:
    """A canonical genesis claim round-trips and verifies explicitly."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))

    encoded = encode_ticket_admission_telemetry_lineage_attestation(attestation)
    decoded = decode_ticket_admission_telemetry_lineage_attestation(encoded)
    verified = verify_ticket_admission_telemetry_lineage_attestation(
        _item(document, decoded),
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )

    assert ticket_admission_telemetry_lineage_id() == LINEAGE_ID
    assert decoded == attestation
    assert verified.capture_sequence_id == GENESIS_SEQUENCE_ID
    assert verified.recorder_id == RECORDER_ID
    assert verified.document_fingerprint.startswith(DOCUMENT_PREFIX)
    assert verified.attestation_fingerprint.startswith(LINEAGE_PREFIX)
    assert verified.canonical_byte_count == len(encoded)
    assert ticket_admission_telemetry_lineage_attestation_fingerprint(
        attestation
    ) == verified.attestation_fingerprint


def test_creation_is_deterministic_and_never_persists_secret_key() -> None:
    """Equal inputs yield equal bytes without retaining secret material."""
    document = _empty_document()
    claim = _claim(GENESIS_SEQUENCE_ID)

    first = _attestation(document, claim)
    second = _attestation(document, claim)
    encoded = encode_ticket_admission_telemetry_lineage_attestation(first)

    assert first == second
    assert SECRET_KEY not in encoded
    assert SECRET_KEY not in repr(first).encode("utf-8")


@pytest.mark.parametrize(
    ("secret_key", "trusted_key_id", "message"),
    [
        (WRONG_KEY, KEY_ID, "authentication failed"),
        (SECRET_KEY, "local.other-key", "key identity is not trusted"),
    ],
)
def test_untrusted_key_material_fails_closed(
    secret_key: bytes,
    trusted_key_id: str,
    message: str,
) -> None:
    """Verification requires both the selected key identity and secret."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))

    with pytest.raises(TicketAdmissionTelemetryLineageError, match=message):
        _ = verify_ticket_admission_telemetry_lineage_attestation(
            _item(document, attestation),
            secret_key=secret_key,
            trusted_key_id=trusted_key_id,
        )


def test_attestation_is_bound_to_exact_document_bytes() -> None:
    """A valid MAC cannot authenticate a different telemetry document."""
    first = _completed_document(LOW_ELAPSED_NS)
    second = _completed_document(HIGH_ELAPSED_NS)
    attestation = _attestation(first, _claim(GENESIS_SEQUENCE_ID))

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="document fingerprint does not match",
    ):
        _ = verify_ticket_admission_telemetry_lineage_attestation(
            _item(second, attestation),
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


def test_tampered_authenticated_field_fails_closed() -> None:
    """Changing a structurally valid claim invalidates its MAC."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    tampered = replace(attestation, recorder_id=OTHER_RECORDER_ID)

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="authentication failed",
    ):
        _ = verify_ticket_admission_telemetry_lineage_attestation(
            _item(document, tampered),
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


def test_direct_successor_is_authenticated_and_order_independent() -> None:
    """An adjacent capture names its exact immediate predecessor."""
    first_document = _completed_document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _completed_document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        replace(
            _claim(SUCCESSOR_SEQUENCE_ID),
            previous_attestation_fingerprint=first_fingerprint,
        ),
    )
    first = _item(first_document, first_attestation)
    second = _item(second_document, second_attestation)

    forward = compare_ticket_admission_telemetry_lineage(
        first,
        second,
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )
    reverse = compare_ticket_admission_telemetry_lineage(
        second,
        first,
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )

    assert forward == reverse
    assert forward.common_recorder_lineage
    assert forward.direct_chain_link
    assert forward.relation == (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert forward.sequence_gap == SUCCESSOR_SEQUENCE_ID
    assert not forward.exact_document_match
    assert not forward.exact_attestation_match


def test_same_capture_requires_exact_attestation_identity() -> None:
    """The same signed capture compares as one authenticated capture."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    item = _item(document, attestation)

    comparison = compare_ticket_admission_telemetry_lineage(
        item,
        item,
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )

    assert comparison.common_recorder_lineage
    assert not comparison.direct_chain_link
    assert comparison.exact_attestation_match
    assert comparison.exact_document_match
    assert comparison.relation == (
        TicketAdmissionTelemetryLineageRelation.SAME_CAPTURE
    )
    assert comparison.sequence_gap == GENESIS_SEQUENCE_ID


def test_ordered_gap_preserves_common_lineage_without_direct_link() -> None:
    """A missing intermediate attestation leaves a sequence gap."""
    first_document = _completed_document(LOW_ELAPSED_NS)
    second_document = _completed_document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(second_document, _claim(GAP_SEQUENCE_ID)),
    )

    comparison = compare_ticket_admission_telemetry_lineage(
        first,
        second,
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )

    assert comparison.common_recorder_lineage
    assert not comparison.direct_chain_link
    assert comparison.relation == (
        TicketAdmissionTelemetryLineageRelation.ORDERED_GAP
    )
    assert comparison.sequence_gap == SEQUENCE_GAP


@pytest.mark.parametrize(
    ("recorder_id", "completed_stream_id", "expected"),
    [
        (
            OTHER_RECORDER_ID,
            COMPLETED_STREAM_ID,
            TicketAdmissionTelemetryLineageRelation.DIFFERENT_RECORDER,
        ),
        (
            RECORDER_ID,
            OTHER_COMPLETED_STREAM_ID,
            TicketAdmissionTelemetryLineageRelation.DIFFERENT_STREAMS,
        ),
    ],
)
def test_authenticated_identity_mismatch_is_not_common_lineage(
    recorder_id: str,
    completed_stream_id: str,
    expected: TicketAdmissionTelemetryLineageRelation,
) -> None:
    """Authenticated recorder or stream mismatches remain separate lineages."""
    document = _empty_document()
    first = _item(
        document,
        _attestation(document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second_attestation = _attestation(
        document,
        replace(
            _claim(GENESIS_SEQUENCE_ID),
            completed_stream_id=completed_stream_id,
            recorder_id=recorder_id,
        ),
    )

    comparison = compare_ticket_admission_telemetry_lineage(
        first,
        _item(document, second_attestation),
        secret_key=SECRET_KEY,
        trusted_key_id=KEY_ID,
    )

    assert not comparison.common_recorder_lineage
    assert not comparison.direct_chain_link
    assert comparison.relation == expected
    assert comparison.sequence_gap is None


def test_same_sequence_authenticated_fork_fails_closed() -> None:
    """Two different signed documents cannot occupy one capture sequence."""
    first_document = _completed_document(LOW_ELAPSED_NS)
    second_document = _completed_document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(second_document, _claim(GENESIS_SEQUENCE_ID)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="capture sequence fork detected",
    ):
        _ = compare_ticket_admission_telemetry_lineage(
            first,
            second,
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


def test_adjacent_capture_requires_exact_predecessor() -> None:
    """An adjacent signed capture cannot omit its predecessor fingerprint."""
    first_document = _completed_document(LOW_ELAPSED_NS)
    second_document = _completed_document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(second_document, _claim(SUCCESSOR_SEQUENCE_ID)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="adjacent capture predecessor does not match",
    ):
        _ = compare_ticket_admission_telemetry_lineage(
            first,
            second,
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


def test_nonadjacent_capture_cannot_name_direct_predecessor() -> None:
    """A direct predecessor link requires an adjacent capture sequence."""
    first_document = _completed_document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _completed_document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        replace(
            _claim(GAP_SEQUENCE_ID),
            previous_attestation_fingerprint=first_fingerprint,
        ),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="predecessor link requires adjacent capture sequence",
    ):
        _ = compare_ticket_admission_telemetry_lineage(
            _item(first_document, first_attestation),
            _item(second_document, second_attestation),
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


@pytest.mark.parametrize(
    ("claim", "secret_key", "message"),
    [
        (
            replace(_claim(0), capture_sequence_id=True),
            SECRET_KEY,
            "capture sequence identity must be a nonnegative integer",
        ),
        (
            replace(_claim(GENESIS_SEQUENCE_ID), recorder_id="bad identity"),
            SECRET_KEY,
            "recorder identity must use canonical ASCII identity form",
        ),
        (
            replace(
                _claim(GENESIS_SEQUENCE_ID),
                previous_attestation_fingerprint=f"{LINEAGE_PREFIX}{'0' * 64}",
            ),
            SECRET_KEY,
            "genesis capture cannot name a predecessor",
        ),
        (
            _claim(GENESIS_SEQUENCE_ID),
            b"short",
            "secret key is shorter than the configured minimum",
        ),
    ],
)
def test_invalid_creation_inputs_fail_closed(
    claim: TicketAdmissionTelemetryLineageClaim,
    secret_key: bytes,
    message: str,
) -> None:
    """Malformed claims and weak keys fail before an attestation exists."""
    with pytest.raises(TicketAdmissionTelemetryLineageError, match=message):
        _ = create_ticket_admission_telemetry_lineage_attestation(
            _empty_document(),
            claim,
            secret_key=secret_key,
        )


def test_duplicate_encoded_key_fails_closed() -> None:
    """Duplicate JSON keys cannot alter a decoded authenticated claim."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    encoded = encode_ticket_admission_telemetry_lineage_attestation(attestation)
    duplicate = encoded.replace(
        b'{"algorithm_id":',
        b'{"algorithm_id":"hmac-sha256","algorithm_id":',
        1,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="contains duplicate keys",
    ):
        _ = decode_ticket_admission_telemetry_lineage_attestation(duplicate)


@pytest.mark.parametrize(
    "mutation",
    [UNKNOWN_MUTATION, NONCANONICAL_MUTATION, OVERSIZED_MUTATION],
)
def test_noncanonical_or_bounded_decode_input_fails_closed(
    mutation: str,
) -> None:
    """Unknown, reformatted, and over-limit encodings remain untrusted."""
    document = _empty_document()
    attestation = _attestation(document, _claim(GENESIS_SEQUENCE_ID))
    encoded = encode_ticket_admission_telemetry_lineage_attestation(attestation)
    mapping = _mapping(encoded)
    if mutation == UNKNOWN_MUTATION:
        mapping["unknown"] = 1
        data = _encoded_mapping(mapping)
        match = "keys are unsupported"
        max_bytes = len(data)
    elif mutation == NONCANONICAL_MUTATION:
        data = dumps(mapping, indent=2, sort_keys=True).encode("utf-8")
        match = "must use canonical JSON"
        max_bytes = len(data)
    else:
        data = encoded
        match = "exceeds configured byte limit"
        max_bytes = len(data) - 1

    with pytest.raises(TicketAdmissionTelemetryLineageError, match=match):
        _ = decode_ticket_admission_telemetry_lineage_attestation(
            data,
            max_bytes=max_bytes,
        )


def test_attestation_fingerprint_collision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct authenticated attestations cannot share one identity."""
    monkeypatch.setattr(lineage_module, "sha256", _constant_sha256)
    first_document = _completed_document(LOW_ELAPSED_NS)
    second_document = _completed_document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(second_document, _claim(GENESIS_SEQUENCE_ID)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="attestation fingerprint collision detected",
    ):
        _ = compare_ticket_admission_telemetry_lineage(
            first,
            second,
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )


def _constant_document_fingerprint(
    document: TicketAdmissionTelemetryDocument,
) -> str:
    _ = document
    return f"{DOCUMENT_PREFIX}{'0' * 64}"


def test_document_fingerprint_collision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct canonical documents cannot share one authenticated identity."""
    monkeypatch.setattr(
        lineage_module,
        "ticket_admission_telemetry_document_fingerprint",
        _constant_document_fingerprint,
    )
    first_document = _completed_document(LOW_ELAPSED_NS)
    second_document = _completed_document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(first_document, _claim(GENESIS_SEQUENCE_ID)),
    )
    second = _item(
        second_document,
        _attestation(second_document, _claim(GAP_SEQUENCE_ID)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageError,
        match="document fingerprint collision detected",
    ):
        _ = compare_ticket_admission_telemetry_lineage(
            first,
            second,
            secret_key=SECRET_KEY,
            trusted_key_id=KEY_ID,
        )
