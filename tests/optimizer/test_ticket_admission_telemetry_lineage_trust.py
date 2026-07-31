# File:
#   - test_ticket_admission_telemetry_lineage_trust.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage_trust.py
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
#   - Bounded caller-owned lineage trust and key-rotation regressions.
# - Must-Not:
#   - Require CUDA, load keys, persist secrets, or modify admission policy.
# - Allows:
#   - Inputs: synthetic lineage items and explicit in-memory trust keys.
#   - Outputs: ordering, window, rotation, comparison, and failure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric signatures or external trust stores gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact lineage trust behavior.
# - Summary:
#   - Caller-owned telemetry lineage rotation regressions.
# - Description:
#   - Proves exact key selection and inclusive capture windows fail closed.
# - Usage:
#   - Runs without accelerator hardware, files, or external key services.
# - Defaults:
#   - Uses two deterministic caller-owned HMAC keys.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_trust.py
#
# Large file:
#   - false
#

"""Bounded caller-owned telemetry lineage trust tests."""

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
    from accelerator.ticket_admission_telemetry_lineage_trust import (
        TicketAdmissionTelemetryLineageTrust,
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
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    create_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustKey,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    build_ticket_admission_telemetry_lineage_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    compare_ticket_admission_telemetry_lineage_with_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    ticket_admission_telemetry_lineage_trust_id,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    verify_ticket_admission_telemetry_lineage_with_trust,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

TRUST_ID = "caller-owned-ticket-admission-telemetry-lineage-trust-v1"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
UNKNOWN_KEY_ID = "local.lineage-key.unknown"
OLD_SECRET = b"old-caller-owned-lineage-secret!!"
NEW_SECRET = b"new-caller-owned-lineage-secret!!"
WRONG_SECRET = b"wrong-caller-owned-lineage-key!!"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "lineage-trust-test-workload-v1"
BENCHMARK_ID = "lineage-trust-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
GAP_SEQUENCE_ID = 3
ROTATION_SEQUENCE_ID = 1
TWO_KEYS = 2
WINDOW_FIRST_SEQUENCE_ID = 1
WINDOW_LAST_SEQUENCE_ID = 2
SECRET_FIELD_NAME = b"secret_key"


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


def _trust_key(
    key_id: str,
    secret_key: bytes,
    window: tuple[int, int | None],
) -> TicketAdmissionTelemetryLineageTrustKey:
    first_capture_sequence_id, last_capture_sequence_id = window
    return TicketAdmissionTelemetryLineageTrustKey(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        last_capture_sequence_id=last_capture_sequence_id,
        secret_key=secret_key,
    )


def _rotation_trust() -> TicketAdmissionTelemetryLineageTrust:
    return build_ticket_admission_telemetry_lineage_trust(
        (
            _trust_key(NEW_KEY_ID, NEW_SECRET, (ROTATION_SEQUENCE_ID, None)),
            _trust_key(
                OLD_KEY_ID,
                OLD_SECRET,
                (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
            ),
        )
    )


def test_empty_trust_is_stable_and_trusts_nothing() -> None:
    """An empty bounded trust set is valid but cannot verify any key."""
    trust = build_ticket_admission_telemetry_lineage_trust(())
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )

    assert ticket_admission_telemetry_lineage_trust_id() == TRUST_ID
    assert trust.trust_id == TRUST_ID
    assert trust.key_count == 0
    assert trust.keys == ()
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="key identity is not present in trust set",
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            trust,
        )


def test_trust_keys_are_sorted_and_secrets_are_hidden_from_repr() -> None:
    """Trust construction sorts identities without displaying key bytes."""
    trust = _rotation_trust()

    assert trust.key_count == TWO_KEYS
    assert tuple(key.key_id for key in trust.keys) == (OLD_KEY_ID, NEW_KEY_ID)
    rendered = repr(trust).encode("utf-8")
    assert OLD_SECRET not in rendered
    assert NEW_SECRET not in rendered
    assert SECRET_FIELD_NAME not in rendered


@pytest.mark.parametrize(
    ("keys", "max_keys", "message"),
    [
        (
            cast(
                "tuple[TicketAdmissionTelemetryLineageTrustKey, ...]",
                cast(
                    "object",
                    [_trust_key(OLD_KEY_ID, OLD_SECRET, (0, None))],
                ),
            ),
            1,
            "keys must use the exact immutable tuple type",
        ),
        ((), True, "key limit must be a positive integer"),
        (
            (
                _trust_key(OLD_KEY_ID, OLD_SECRET, (0, None)),
                _trust_key(NEW_KEY_ID, NEW_SECRET, (1, None)),
            ),
            1,
            "key count exceeds configured limit",
        ),
    ],
)
def test_invalid_build_container_or_limit_fails_closed(
    keys: tuple[TicketAdmissionTelemetryLineageTrustKey, ...],
    max_keys: int,
    message: str,
) -> None:
    """Trust construction requires an exact bounded immutable key tuple."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_trust(
            keys,
            max_keys=max_keys,
        )


def test_duplicate_key_identity_fails_closed() -> None:
    """One key identity cannot resolve to multiple secret or window entries."""
    keys = (
        _trust_key(OLD_KEY_ID, OLD_SECRET, (0, 0)),
        _trust_key(OLD_KEY_ID, NEW_SECRET, (1, None)),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="duplicate key identity",
    ):
        _ = build_ticket_admission_telemetry_lineage_trust(keys)


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (
            _trust_key("bad key", OLD_SECRET, (0, None)),
            "key identity must use canonical ASCII identity form",
        ),
        (
            _trust_key(OLD_KEY_ID, b"short", (0, None)),
            "secret key is shorter than the configured minimum",
        ),
        (
            _trust_key(OLD_KEY_ID, OLD_SECRET, (True, None)),
            "first capture sequence identity must be a nonnegative integer",
        ),
        (
            _trust_key(OLD_KEY_ID, OLD_SECRET, (2, 1)),
            "last capture sequence precedes first capture sequence",
        ),
    ],
)
def test_invalid_trust_key_fields_fail_closed(
    key: TicketAdmissionTelemetryLineageTrustKey,
    message: str,
) -> None:
    """Malformed identities, secrets, and windows never enter a trust set."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_trust((key,))


@pytest.mark.parametrize(
    "capture_sequence_id",
    [WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID],
)
def test_capture_window_endpoints_are_inclusive(
    capture_sequence_id: int,
) -> None:
    """Both configured capture-window endpoints authenticate successfully."""
    key = _trust_key(
        OLD_KEY_ID,
        OLD_SECRET,
        (WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID),
    )
    trust = build_ticket_admission_telemetry_lineage_trust((key,))
    document = _document()
    attestation = _attestation(
        document,
        _claim(capture_sequence_id, OLD_KEY_ID),
        OLD_SECRET,
    )

    trusted = verify_ticket_admission_telemetry_lineage_with_trust(
        _item(document, attestation),
        trust,
    )

    assert trusted.trust_id == TRUST_ID
    assert trusted.key_id == OLD_KEY_ID
    assert trusted.first_capture_sequence_id == WINDOW_FIRST_SEQUENCE_ID
    assert trusted.last_capture_sequence_id == WINDOW_LAST_SEQUENCE_ID
    assert (
        trusted.verified_item.verified.capture_sequence_id
        == capture_sequence_id
    )


@pytest.mark.parametrize(
    ("capture_sequence_id", "message"),
    [
        (0, "capture sequence precedes trusted key window"),
        (3, "capture sequence exceeds trusted key window"),
    ],
)
def test_capture_outside_trusted_window_fails_closed(
    capture_sequence_id: int,
    message: str,
) -> None:
    """A valid MAC is insufficient outside the selected key window."""
    trust = build_ticket_admission_telemetry_lineage_trust(
        (_trust_key(
        OLD_KEY_ID,
        OLD_SECRET,
        (WINDOW_FIRST_SEQUENCE_ID, WINDOW_LAST_SEQUENCE_ID),
    ),)
    )
    document = _document()
    attestation = _attestation(
        document,
        _claim(capture_sequence_id, OLD_KEY_ID),
        OLD_SECRET,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match=message,
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            trust,
        )


def test_unknown_attestation_key_fails_closed() -> None:
    """An unknown key identity is never guessed or substituted."""
    trust = _rotation_trust()
    document = _document()
    attestation = _attestation(
        document,
        _claim(SUCCESSOR_SEQUENCE_ID, UNKNOWN_KEY_ID),
        NEW_SECRET,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="key identity is not present in trust set",
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            trust,
        )


def test_selected_trust_secret_must_authenticate_attestation() -> None:
    """The selected key identity cannot conceal incorrect secret material."""
    trust = build_ticket_admission_telemetry_lineage_trust(
        (_trust_key(OLD_KEY_ID, WRONG_SECRET, (0, None)),)
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
            trust,
        )


def test_direct_successor_can_rotate_to_a_new_trusted_key() -> None:
    """An adjacent predecessor link remains valid across key rotation."""
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
    first = _item(first_document, first_attestation)
    second = _item(second_document, second_attestation)
    trust = _rotation_trust()

    forward = compare_ticket_admission_telemetry_lineage_with_trust(
        first,
        second,
        trust,
    )
    reverse = compare_ticket_admission_telemetry_lineage_with_trust(
        second,
        first,
        trust,
    )

    assert forward == reverse
    assert forward.common_recorder_lineage
    assert forward.direct_chain_link
    assert forward.relation == (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert forward.first.key_id == OLD_KEY_ID
    assert forward.second.key_id == NEW_KEY_ID


def test_rotated_ordered_gap_is_common_lineage_without_direct_link() -> None:
    """A rotated key may authenticate a later capture with an explicit gap."""
    first_document = _document(LOW_ELAPSED_NS)
    second_document = _document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(
            first_document,
            _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
            OLD_SECRET,
        ),
    )
    second = _item(
        second_document,
        _attestation(
            second_document,
            _claim(GAP_SEQUENCE_ID, NEW_KEY_ID),
            NEW_SECRET,
        ),
    )

    comparison = compare_ticket_admission_telemetry_lineage_with_trust(
        first,
        second,
        _rotation_trust(),
    )

    assert comparison.common_recorder_lineage
    assert not comparison.direct_chain_link
    assert comparison.relation == (
        TicketAdmissionTelemetryLineageRelation.ORDERED_GAP
    )
    assert comparison.sequence_gap == GAP_SEQUENCE_ID


def test_same_key_comparison_remains_supported_by_trust_set() -> None:
    """A trust set preserves ordinary same-key lineage comparison semantics."""
    trust = build_ticket_admission_telemetry_lineage_trust(
        (_trust_key(OLD_KEY_ID, OLD_SECRET, (0, None)),)
    )
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )
    item = _item(document, attestation)

    comparison = compare_ticket_admission_telemetry_lineage_with_trust(
        item,
        item,
        trust,
    )

    assert comparison.common_recorder_lineage
    assert comparison.exact_attestation_match
    assert comparison.exact_document_match
    assert comparison.relation == (
        TicketAdmissionTelemetryLineageRelation.SAME_CAPTURE
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
            "trust keys must be uniquely ordered by identity",
        ),
    ],
)
def test_tampered_trust_metadata_fails_closed(
    trust: TicketAdmissionTelemetryLineageTrust,
    message: str,
) -> None:
    """Trust identity, count, and canonical ordering are revalidated on use."""
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match=message,
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            trust,
        )


def test_rotated_same_sequence_fork_still_fails_closed() -> None:
    """Key rotation cannot authorize two documents at one capture sequence."""
    trust = build_ticket_admission_telemetry_lineage_trust(
        (
            _trust_key(OLD_KEY_ID, OLD_SECRET, (0, None)),
            _trust_key(NEW_KEY_ID, NEW_SECRET, (0, None)),
        )
    )
    first_document = _document(LOW_ELAPSED_NS)
    second_document = _document(HIGH_ELAPSED_NS)
    first = _item(
        first_document,
        _attestation(
            first_document,
            _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
            OLD_SECRET,
        ),
    )
    second = _item(
        second_document,
        _attestation(
            second_document,
            _claim(GENESIS_SEQUENCE_ID, NEW_KEY_ID),
            NEW_SECRET,
        ),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="capture sequence fork detected",
    ):
        _ = compare_ticket_admission_telemetry_lineage_with_trust(
            first,
            second,
            trust,
        )
