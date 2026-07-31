# File:
#   - test_ticket_admission_telemetry_persistence.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_persistence.py
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
#   - Canonical bounded ticket telemetry persistence regressions.
# - Must-Not:
#   - Require CUDA, change admission, or treat telemetry as policy evidence.
# - Allows:
#   - Inputs: synthetic reports, canonical bytes, and temporary explicit paths.
#   - Outputs: strict schema, limit, atomic-write, and restoration assertions.
#   - Side effects: temporary-directory file replacement only.
# - Split-When:
#   - Split when schema-v3 or lossy migration changes persistence tests.
# - Merge-When:
#   - Merge when another suite owns this exact persistence contract.
# - Summary:
#   - Ticket admission telemetry persistence regressions.
# - Description:
#   - Proves explicit persistence is canonical, bounded, and non-authoritative.
# - Usage:
#   - Runs without accelerator hardware.
# - Defaults:
#   - Duplicate, unknown, noncanonical, oversized, or malformed data fails
#     closed.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_migration.py
# - accelerator/ticket_admission_telemetry_store.py
#
# Large file:
#   - false
#

"""Canonical bounded ticket admission telemetry persistence tests."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import replace
import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from accelerator.ticket_admission import TicketAdmissionReport

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
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
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    decode_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    read_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    restore_ticket_admission_telemetry,
)
from accelerator.ticket_admission_telemetry_persistence import (
    ticket_admission_telemetry_document_id,
)
from accelerator.ticket_admission_telemetry_persistence import (
    write_ticket_admission_telemetry_document,
)

DOCUMENT_ID = "ticket-admission-telemetry-document-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "exact-test-workload-v1"
BENCHMARK_ID = "test-ticket-route-v1"
FALLBACK_NS = 100
CANDIDATE_NS = 80
PAIR_GROUP_SIZE = 2
FIRST_ELAPSED_NS = 125
SECOND_ELAPSED_NS = 145
SPACE = b" "


def _report() -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=PAIR_GROUP_SIZE,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=PAIR_GROUP_SIZE,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=180,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=FALLBACK_NS,
    )


def _attempts(
    *,
    completed_capacity: int = 2,
    failed_capacity: int = 2,
) -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=completed_capacity),
        failed=TicketAdmissionFailureTelemetry(capacity=failed_capacity),
    )


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def test_empty_document_has_stable_identity_and_canonical_bytes() -> None:
    """An empty explicit capture has one stable compact schema-v1 encoding."""
    document = capture_ticket_admission_telemetry_document(_attempts())

    encoded = encode_ticket_admission_telemetry_document(document)

    assert ticket_admission_telemetry_document_id() == DOCUMENT_ID
    assert document.document_id == DOCUMENT_ID
    assert document.schema_version == 1
    assert encoded == _canonical(asdict(document))
    assert encoded.endswith(b"\n")
    assert SPACE not in encoded
    assert decode_ticket_admission_telemetry_document(encoded) == document


def test_populated_document_restores_and_continues_both_sequences() -> None:
    """Restored state preserves eviction and continues sequence identities."""
    report = _report()
    attempts = _attempts(completed_capacity=1, failed_capacity=1)
    _ = attempts.record_completed(report, elapsed_ns=FIRST_ELAPSED_NS)
    _ = attempts.record_completed(report, elapsed_ns=SECOND_ELAPSED_NS)
    _ = attempts.record_failed(
        report,
        elapsed_ns=FIRST_ELAPSED_NS,
        error=AcceleratorExecutionError("private execution detail"),
    )
    _ = attempts.record_failed(
        report,
        elapsed_ns=SECOND_ELAPSED_NS,
        error=AcceleratorUnavailableError("private unavailable detail"),
    )
    document = capture_ticket_admission_telemetry_document(attempts)

    restored = restore_ticket_admission_telemetry(
        decode_ticket_admission_telemetry_document(
            encode_ticket_admission_telemetry_document(document)
        )
    )

    assert restored.completed.snapshot() == document.completed
    assert restored.failed.snapshot() == document.failed
    completed = restored.record_completed(report, elapsed_ns=FIRST_ELAPSED_NS)
    failed = restored.record_failed(
        report,
        elapsed_ns=FIRST_ELAPSED_NS,
        error=AcceleratorExecutionError("new private detail"),
    )
    assert completed.sequence_id == PAIR_GROUP_SIZE
    assert failed.sequence_id == PAIR_GROUP_SIZE
    completed_snapshot = restored.completed.snapshot()
    failed_snapshot = restored.failed.snapshot()
    assert completed_snapshot.dropped_observation_count == PAIR_GROUP_SIZE
    assert failed_snapshot.dropped_observation_count == PAIR_GROUP_SIZE


def test_explicit_file_roundtrip_uses_atomic_replacement(
    tmp_path: Path,
) -> None:
    """Writing replaces one file and leaves no temporary sibling behind."""
    destination = tmp_path / "ticket-telemetry.json"
    document = capture_ticket_admission_telemetry_document(_attempts())

    write_ticket_admission_telemetry_document(destination, document)
    first = destination.read_bytes()
    write_ticket_admission_telemetry_document(destination, document)

    assert destination.read_bytes() == first
    assert read_ticket_admission_telemetry_document(destination) == document
    assert tuple(tmp_path.iterdir()) == (destination,)


def _encoded_with_failure() -> bytes:
    attempts = _attempts()
    _ = attempts.record_failed(
        _report(),
        elapsed_ns=FIRST_ELAPSED_NS,
        error=AcceleratorExecutionError("private detail"),
    )
    return encode_ticket_admission_telemetry_document(
        capture_ticket_admission_telemetry_document(attempts)
    )


def _duplicate_schema(payload: bytes) -> bytes:
    return payload.replace(
        b'"schema_version":1',
        b'"schema_version":1,"schema_version":1',
        1,
    )


def _unknown_root(payload: bytes) -> bytes:
    return b'{"unknown":0,' + payload[1:]


def _unsupported_schema(payload: bytes) -> bytes:
    return payload.replace(
        b'"schema_version":1',
        b'"schema_version":2',
        1,
    )


def _noncanonical(payload: bytes) -> bytes:
    return SPACE + payload


@pytest.mark.parametrize(
    ("payload_transform", "pattern"),
    [
        (_duplicate_schema, "duplicate telemetry JSON key: schema_version"),
        (_unknown_root, "contains unknown key: unknown"),
        (_unsupported_schema, "document schema is unsupported"),
        (_noncanonical, "document bytes are not canonical"),
    ],
)
def test_decoder_rejects_schema_and_canonicality_drift(
    payload_transform: Callable[[bytes], bytes],
    pattern: str,
) -> None:
    """Duplicate, unknown, unsupported, and noncanonical bytes fail closed."""
    encoded = encode_ticket_admission_telemetry_document(
        capture_ticket_admission_telemetry_document(_attempts())
    )

    with pytest.raises(TicketAdmissionTelemetryPersistenceError, match=pattern):
        _ = decode_ticket_admission_telemetry_document(
            payload_transform(encoded)
        )


def test_decoder_rejects_unknown_failure_category() -> None:
    """Persisted failures admit only stable non-message category identities."""
    malformed = _encoded_with_failure().replace(
        b'"accelerator-execution"',
        b'"private-error-message"',
        1,
    )

    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="failure_kind is unsupported",
    ):
        _ = decode_ticket_admission_telemetry_document(malformed)


def test_decoder_rejects_sequence_accounting_drift() -> None:
    """A forged retained sequence cannot be restored or silently renumbered."""
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=FIRST_ELAPSED_NS)
    encoded = encode_ticket_admission_telemetry_document(
        capture_ticket_admission_telemetry_document(attempts)
    )
    malformed = encoded.replace(
        b'"next_sequence_id":1',
        b'"next_sequence_id":2',
        1,
    )

    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="snapshot sequence accounting mismatched",
    ):
        _ = decode_ticket_admission_telemetry_document(malformed)


@pytest.mark.parametrize(
    ("keywords", "pattern"),
    [
        ({"max_bytes": 0}, "byte limit must be a positive integer"),
        ({"max_bytes": True}, "byte limit must be a positive integer"),
        (
            {"max_observations": 0},
            "observation limit must be a positive integer",
        ),
        (
            {"max_observations": True},
            "observation limit must be a positive integer",
        ),
    ],
)
def test_decoder_rejects_invalid_limits(
    keywords: dict[str, object],
    pattern: str,
) -> None:
    """Boolean, zero, and negative resource limits never bypass bounds."""
    encoded = encode_ticket_admission_telemetry_document(
        capture_ticket_admission_telemetry_document(_attempts())
    )

    with pytest.raises(TicketAdmissionTelemetryPersistenceError, match=pattern):
        _ = decode_ticket_admission_telemetry_document(
            encoded,
            **keywords,  # pyright: ignore[reportArgumentType]
        )


def test_decoder_enforces_byte_and_capacity_limits() -> None:
    """Byte and observation budgets bound input before restoration."""
    encoded = encode_ticket_admission_telemetry_document(
        capture_ticket_admission_telemetry_document(_attempts())
    )

    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="exceeds configured byte limit",
    ):
        _ = decode_ticket_admission_telemetry_document(
            encoded,
            max_bytes=len(encoded) - 1,
        )
    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="snapshot capacity exceeds observation limit",
    ):
        _ = decode_ticket_admission_telemetry_document(
            encoded,
            max_observations=1,
        )


def test_file_reader_enforces_bound_and_wraps_missing_path(
    tmp_path: Path,
) -> None:
    """Explicit file reads preserve the same bounds and stable failure type."""
    source = tmp_path / "telemetry.json"
    _ = source.write_bytes(b"x" * 16)

    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="exceeds configured byte limit",
    ):
        _ = read_ticket_admission_telemetry_document(source, max_bytes=8)
    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="cannot read telemetry document",
    ):
        _ = read_ticket_admission_telemetry_document(tmp_path / "missing.json")


def test_encoder_rejects_forged_typed_document_state() -> None:
    """Typed dataclasses still require exact schema and snapshot invariants."""
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=FIRST_ELAPSED_NS)
    document = capture_ticket_admission_telemetry_document(attempts)
    observation = document.completed.observations[0]
    malformed_snapshot = replace(
        document.completed,
        observations=(replace(observation, chunk_count=PAIR_GROUP_SIZE),),
    )

    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="document schema is unsupported",
    ):
        _ = encode_ticket_admission_telemetry_document(
            replace(document, schema_version=True)
        )
    with pytest.raises(
        TicketAdmissionTelemetryPersistenceError,
        match="snapshot chunk accounting mismatched",
    ):
        _ = encode_ticket_admission_telemetry_document(
            replace(document, completed=malformed_snapshot)
        )
