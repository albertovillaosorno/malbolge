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
#   - Lossless schema-v1/schema-v2 telemetry compatibility regressions.
# - Must-Not:
#   - Require CUDA, auto-upgrade, reinterpret snapshots, merge, or change
#     policy.
# - Allows:
#   - Inputs: synthetic schema-v1/v2 documents, canonical bytes, and mutations.
#   - Outputs: matrix, dispatch, roundtrip, limit, and fail-closed assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when schema-v3 or a lossy migration gains independent tests.
# - Merge-When:
#   - Merge when persistence owns this exact compatibility matrix.
# - Summary:
#   - Canonical lossless ticket telemetry schema migration regressions.
# - Description:
#   - Proves schema-v2 preserves exact canonical schema-v1 source bytes.
# - Usage:
#   - Runs without accelerator hardware or filesystem access.
# - Defaults:
#   - Uses exact schema-v1 bytes and bounded schema-v2 Base64 wrappers.
#

"""Lossless schema-v1/schema-v2 ticket telemetry migration tests."""

from __future__ import annotations

from base64 import b64decode
from base64 import b64encode
from dataclasses import asdict
from dataclasses import replace
from hashlib import sha256
import json
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_migration import (
        TicketAdmissionTelemetryVersionedDocument,
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
from accelerator.ticket_admission_telemetry_migration import (
    TicketAdmissionTelemetryDocumentV2,
)
from accelerator.ticket_admission_telemetry_migration import (
    TicketAdmissionTelemetryMigrationError,
)
from accelerator.ticket_admission_telemetry_migration import (
    decode_ticket_admission_telemetry_document_versioned,
)
from accelerator.ticket_admission_telemetry_migration import (
    encode_ticket_admission_telemetry_document_versioned,
)
from accelerator.ticket_admission_telemetry_migration import (
    migrate_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_migration import (
    ticket_admission_telemetry_schema_compatibility,
)
from accelerator.ticket_admission_telemetry_migration import (
    ticket_admission_telemetry_schema_migration_id,
)
from accelerator.ticket_admission_telemetry_migration import (
    ticket_admission_telemetry_versioned_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

MIGRATION_ID = "ticket-admission-telemetry-schema-migration-v1"
DOCUMENT_V1_ID = "ticket-admission-telemetry-document-v1"
DOCUMENT_V2_ID = "ticket-admission-telemetry-document-v2"
SOURCE_ENCODING = "base64-standard-canonical-v1"
V1_FINGERPRINT_PREFIX = "ticket-admission-telemetry-document-v1:sha256:"
V2_FINGERPRINT_PREFIX = "ticket-admission-telemetry-document-v2:sha256:"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "migration-test-workload-v1"
BENCHMARK_ID = "migration-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
COMPLETED_NS = 125
FAILED_NS = 145
SCHEMA_V2 = 2
SPACE = b" "


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


def _document(*, populated: bool = False) -> TicketAdmissionTelemetryDocument:
    attempts = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=2),
        failed=TicketAdmissionFailureTelemetry(capacity=2),
    )
    if populated:
        report = _report()
        _ = attempts.record_completed(report, elapsed_ns=COMPLETED_NS)
        _ = attempts.record_failed(
            report,
            elapsed_ns=FAILED_NS,
            error=AcceleratorExecutionError("private migration detail"),
        )
    return capture_ticket_admission_telemetry_document(attempts)


def _v2(
    document: TicketAdmissionTelemetryDocument | None = None,
) -> TicketAdmissionTelemetryDocumentV2:
    source = _document() if document is None else document
    migrated = migrate_ticket_admission_telemetry_document(
        source,
        target_schema_version=2,
    )
    assert type(migrated) is TicketAdmissionTelemetryDocumentV2
    return migrated


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


def _json_mutation(
    encoded: bytes,
    mutate: Callable[[dict[str, object]], None],
) -> bytes:
    value = cast("dict[str, object]", json.loads(encoded))
    mutate(value)
    return _canonical(value)


def test_migration_identity_and_compatibility_matrix_are_stable() -> None:
    """The fixed matrix names all four lossless conversion routes."""
    matrix = ticket_admission_telemetry_schema_compatibility()

    assert ticket_admission_telemetry_schema_migration_id() == MIGRATION_ID
    assert tuple(
        (entry.source_schema_version, entry.target_schema_version)
        for entry in matrix
    ) == ((1, 1), (1, 2), (2, 1), (2, 2))
    assert all(entry.lossless for entry in matrix)
    assert all(entry.preserves_schema_v1_canonical_bytes for entry in matrix)


def test_schema_v1_versioned_encoding_is_byte_identical() -> None:
    """The versioned encoder does not rewrite existing canonical schema-v1."""
    document = _document(populated=True)

    encoded = encode_ticket_admission_telemetry_document_versioned(document)

    assert encoded == encode_ticket_admission_telemetry_document(document)
    assert decode_ticket_admission_telemetry_document_versioned(encoded) == (
        document
    )


def test_schema_v1_identity_route_is_lossless() -> None:
    """The 1-to-1 route validates without changing document content or bytes."""
    document = _document(populated=True)

    migrated = migrate_ticket_admission_telemetry_document(
        document,
        target_schema_version=1,
    )

    assert migrated == document
    assert encode_ticket_admission_telemetry_document_versioned(migrated) == (
        encode_ticket_admission_telemetry_document(document)
    )


def test_schema_v1_to_v2_binds_exact_source_bytes_and_identity() -> None:
    """The 1-to-2 route binds exact source bytes and fingerprint."""
    document = _document(populated=True)
    source_bytes = encode_ticket_admission_telemetry_document(document)

    migrated = _v2(document)

    assert migrated.document_id == DOCUMENT_V2_ID
    assert migrated.schema_version == SCHEMA_V2
    assert migrated.source_document_encoding == SOURCE_ENCODING
    assert migrated.source_document_id == DOCUMENT_V1_ID
    assert migrated.source_schema_version == 1
    assert b64decode(migrated.source_document_payload) == source_bytes
    assert migrated.source_document_fingerprint == (
        f"{V1_FINGERPRINT_PREFIX}{sha256(source_bytes).hexdigest()}"
    )


def test_schema_v2_encoding_is_canonical_and_roundtrips() -> None:
    """Schema-v2 is compact sorted JSON with one trailing newline."""
    document = _v2(_document(populated=True))

    encoded = encode_ticket_admission_telemetry_document_versioned(document)

    assert encoded == _canonical(asdict(document))
    assert encoded.endswith(b"\n")
    assert SPACE not in encoded
    assert decode_ticket_admission_telemetry_document_versioned(encoded) == (
        document
    )


def test_schema_v2_to_v1_reproduces_exact_original_bytes() -> None:
    """The 2-to-1 route reconstructs byte-identical canonical schema-v1."""
    original = _document(populated=True)
    original_bytes = encode_ticket_admission_telemetry_document(original)
    migrated = _v2(original)

    downgraded = migrate_ticket_admission_telemetry_document(
        migrated,
        target_schema_version=1,
    )

    assert type(downgraded) is type(original)
    assert downgraded == original
    assert encode_ticket_admission_telemetry_document_versioned(downgraded) == (
        original_bytes
    )


def test_schema_v2_identity_route_preserves_exact_wrapper_bytes() -> None:
    """The 2-to-2 route validates without changing canonical wrapper bytes."""
    document = _v2(_document(populated=True))
    encoded = encode_ticket_admission_telemetry_document_versioned(document)

    migrated = migrate_ticket_admission_telemetry_document(
        document,
        target_schema_version=2,
    )

    assert migrated == document
    assert encode_ticket_admission_telemetry_document_versioned(migrated) == (
        encoded
    )


def test_populated_snapshots_survive_both_migration_directions() -> None:
    """Completed and failed snapshots retain every exact observation field."""
    original = _document(populated=True)

    migrated = _v2(original)
    downgraded = migrate_ticket_admission_telemetry_document(
        decode_ticket_admission_telemetry_document_versioned(
            encode_ticket_admission_telemetry_document_versioned(migrated)
        ),
        target_schema_version=1,
    )

    assert type(downgraded) is type(original)
    downgraded_v1 = cast("TicketAdmissionTelemetryDocument", downgraded)
    assert downgraded_v1.completed == original.completed
    assert downgraded_v1.failed == original.failed


def test_versioned_fingerprints_are_schema_specific_and_exact() -> None:
    """Each schema hashes its own canonical bytes under a distinct prefix."""
    v1 = _document(populated=True)
    v2 = _v2(v1)
    v1_bytes = encode_ticket_admission_telemetry_document_versioned(v1)
    v2_bytes = encode_ticket_admission_telemetry_document_versioned(v2)

    assert ticket_admission_telemetry_versioned_document_fingerprint(v1) == (
        f"{V1_FINGERPRINT_PREFIX}{sha256(v1_bytes).hexdigest()}"
    )
    assert ticket_admission_telemetry_versioned_document_fingerprint(v2) == (
        f"{V2_FINGERPRINT_PREFIX}{sha256(v2_bytes).hexdigest()}"
    )


@pytest.mark.parametrize("target_schema_version", [0, 3, True])
def test_unsupported_target_schema_fails_closed(
    target_schema_version: int,
) -> None:
    """Only exact integer target schemas one and two are accepted."""
    pattern = (
        "target schema must be an integer"
        if target_schema_version is True
        else "target schema is unsupported"
    )

    with pytest.raises(TicketAdmissionTelemetryMigrationError, match=pattern):
        _ = migrate_ticket_admission_telemetry_document(
            _document(),
            target_schema_version=target_schema_version,
        )


def test_foreign_document_type_fails_all_public_document_operations() -> None:
    """Equal-looking foreign objects cannot enter migration or encoding."""
    foreign = cast("TicketAdmissionTelemetryVersionedDocument", object())

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="document type is unsupported",
    ):
        _ = migrate_ticket_admission_telemetry_document(
            foreign,
            target_schema_version=1,
        )
    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="document type is unsupported",
    ):
        _ = encode_ticket_admission_telemetry_document_versioned(foreign)
    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="document type is unsupported",
    ):
        _ = ticket_admission_telemetry_versioned_document_fingerprint(foreign)


def test_forged_schema_v1_document_fails_before_upgrade() -> None:
    """Typed schema-v1 still requires the persistence contract."""
    malformed = replace(_document(), schema_version=True)

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="invalid schema-v1 document",
    ):
        _ = migrate_ticket_admission_telemetry_document(
            malformed,
            target_schema_version=2,
        )


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("document_id", "unsupported", "document identity is unsupported"),
        ("schema_version", True, "document schema is unsupported"),
        ("schema_version", 3, "document schema is unsupported"),
        ("source_document_encoding", "hex", "source encoding is unsupported"),
        (
            "source_document_id",
            "unsupported",
            "source document identity is unsupported",
        ),
        ("source_schema_version", True, "source schema is unsupported"),
        ("source_schema_version", 2, "source schema is unsupported"),
        (
            "source_document_fingerprint",
            "invalid",
            "source document fingerprint is invalid",
        ),
    ],
)
def test_forged_schema_v2_header_fails_closed(
    field: str,
    value: object,
    pattern: str,
) -> None:
    """Every schema-v2 identity and source-header field is exact."""
    malformed = replace(_v2(), **{field: value})

    with pytest.raises(TicketAdmissionTelemetryMigrationError, match=pattern):
        _ = encode_ticket_admission_telemetry_document_versioned(malformed)


def test_schema_v2_rejects_source_fingerprint_mismatch() -> None:
    """A valid-looking fingerprint cannot identify different canonical bytes."""
    malformed = replace(
        _v2(),
        source_document_fingerprint=f"{V1_FINGERPRINT_PREFIX}{"0" * 64}",
    )

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="source document fingerprint mismatched",
    ):
        _ = encode_ticket_admission_telemetry_document_versioned(malformed)


@pytest.mark.parametrize("payload", ["", "not-base64", "===="])
def test_schema_v2_rejects_empty_or_invalid_base64(payload: str) -> None:
    """Embedded source payloads require non-empty valid standard Base64."""
    malformed = replace(_v2(), source_document_payload=payload)

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="source payload",
    ):
        _ = encode_ticket_admission_telemetry_document_versioned(malformed)


def test_schema_v2_rejects_noncanonical_embedded_schema_v1() -> None:
    """A wrapper cannot preserve whitespace-mutated schema-v1 as canonical."""
    source_bytes = SPACE + encode_ticket_admission_telemetry_document(
        _document()
    )
    malformed = replace(
        _v2(),
        source_document_fingerprint=(
            f"{V1_FINGERPRINT_PREFIX}{sha256(source_bytes).hexdigest()}"
        ),
        source_document_payload=b64encode(source_bytes).decode("ascii"),
    )

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="invalid schema-v2 source document",
    ):
        _ = encode_ticket_admission_telemetry_document_versioned(malformed)


def test_schema_v2_rejects_recursive_schema_v2_source() -> None:
    """Schema-v2 may embed only exact schema-v1, never another wrapper."""
    nested_bytes = encode_ticket_admission_telemetry_document_versioned(_v2())
    malformed = replace(
        _v2(),
        source_document_fingerprint=(
            f"{V1_FINGERPRINT_PREFIX}{sha256(nested_bytes).hexdigest()}"
        ),
        source_document_payload=b64encode(nested_bytes).decode("ascii"),
    )

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="invalid schema-v2 source document",
    ):
        _ = encode_ticket_admission_telemetry_document_versioned(malformed)


def _add_unknown(mapping: dict[str, object]) -> None:
    mapping["unknown"] = 0


def _remove_source_id(mapping: dict[str, object]) -> None:
    _ = mapping.pop("source_document_id")


def _unsupported_schema(mapping: dict[str, object]) -> None:
    mapping["schema_version"] = 3


@pytest.mark.parametrize(
    ("mutate", "pattern"),
    [
        (_add_unknown, "contains unknown key: unknown"),
        (_remove_source_id, "is missing key: source_document_id"),
        (_unsupported_schema, "document schema is unsupported"),
    ],
)
def test_versioned_decoder_rejects_root_schema_drift(
    mutate: Callable[[dict[str, object]], None],
    pattern: str,
) -> None:
    """Unknown, missing, and unsupported schema-v2 roots fail closed."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())

    with pytest.raises(TicketAdmissionTelemetryMigrationError, match=pattern):
        _ = decode_ticket_admission_telemetry_document_versioned(
            _json_mutation(encoded, mutate)
        )


def test_versioned_decoder_rejects_duplicate_schema_key() -> None:
    """Duplicate dispatch keys fail before selecting any schema decoder."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())
    malformed = encoded.replace(
        b'"schema_version":2',
        b'"schema_version":2,"schema_version":2',
        1,
    )

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="duplicate versioned JSON key: schema_version",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(malformed)


def test_versioned_decoder_rejects_noncanonical_schema_v2_bytes() -> None:
    """Whitespace changes fail even when the JSON value is otherwise valid."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="schema-v2 document bytes are not canonical",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(
            SPACE + encoded
        )


@pytest.mark.parametrize(
    ("payload", "pattern"),
    [
        (b"", "document payload must not be empty"),
        (b"[]\n", "versioned document must be a JSON object"),
        (b"{\n", "invalid versioned document JSON"),
        (b"\xff", "versioned document is not UTF-8"),
        (b'{"document_id":"x"}\n', "missing key: schema_version"),
    ],
)
def test_versioned_decoder_rejects_malformed_dispatch_bytes(
    payload: bytes,
    pattern: str,
) -> None:
    """Malformed dispatch bytes fail before migration or source decoding."""
    with pytest.raises(TicketAdmissionTelemetryMigrationError, match=pattern):
        _ = decode_ticket_admission_telemetry_document_versioned(payload)


@pytest.mark.parametrize(
    ("keywords", "pattern"),
    [
        ({"max_bytes": 0}, "byte limit must be a positive integer"),
        ({"max_bytes": True}, "byte limit must be a positive integer"),
        (
            {"max_source_bytes": 0},
            "source byte limit must be a positive integer",
        ),
        (
            {"max_source_bytes": True},
            "source byte limit must be a positive integer",
        ),
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
def test_versioned_decoder_rejects_invalid_limits(
    keywords: dict[str, object],
    pattern: str,
) -> None:
    """Zero and boolean limits cannot bypass versioned resource bounds."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())

    with pytest.raises(TicketAdmissionTelemetryMigrationError, match=pattern):
        _ = decode_ticket_admission_telemetry_document_versioned(
            encoded,
            **keywords,  # pyright: ignore[reportArgumentType]
        )


def test_versioned_decoder_enforces_outer_byte_limit() -> None:
    """The complete schema-v2 wrapper is bounded before JSON parsing."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="versioned document exceeds configured byte limit",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(
            encoded,
            max_bytes=len(encoded) - 1,
        )

    assert (
        decode_ticket_admission_telemetry_document_versioned(
            encoded,
            max_bytes=len(encoded),
        )
        == _v2()
    )


def test_versioned_decoder_enforces_schema_v1_source_byte_limit() -> None:
    """Direct schema-v1 dispatch preserves the independent source-byte bound."""
    document = _document()
    encoded = encode_ticket_admission_telemetry_document(document)

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="schema-v1 document exceeds source byte limit",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(
            encoded,
            max_source_bytes=len(encoded) - 1,
        )


def test_versioned_decoder_enforces_embedded_source_byte_limit() -> None:
    """Schema-v2 rejects an embedded source before schema-v1 restoration."""
    document = _document()
    source_bytes = encode_ticket_admission_telemetry_document(document)
    encoded = encode_ticket_admission_telemetry_document_versioned(
        _v2(document)
    )

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="schema-v2 source document exceeds source byte limit",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(
            encoded,
            max_source_bytes=len(source_bytes) - 1,
        )


def test_versioned_decoder_enforces_observation_limit_in_both_schemas() -> None:
    """Schema-v1 and embedded schema-v1 use the same per-FIFO bound."""
    document = _document(populated=True)
    v1_bytes = encode_ticket_admission_telemetry_document(document)
    v2_bytes = encode_ticket_admission_telemetry_document_versioned(
        _v2(document)
    )

    for payload in (v1_bytes, v2_bytes):
        with pytest.raises(
            TicketAdmissionTelemetryMigrationError,
            match="snapshot capacity exceeds observation limit",
        ):
            _ = decode_ticket_admission_telemetry_document_versioned(
                payload,
                max_observations=1,
            )


def test_outer_schema_v2_payload_tampering_fails_source_binding() -> None:
    """Changing embedded bytes without the bound fingerprint fails."""
    encoded = encode_ticket_admission_telemetry_document_versioned(_v2())

    def mutate(mapping: dict[str, object]) -> None:
        payload = cast("str", mapping["source_document_payload"])
        source = b64decode(payload)
        mapping["source_document_payload"] = b64encode(
            source.replace(b'"capacity":2', b'"capacity":3', 1)
        ).decode("ascii")

    with pytest.raises(
        TicketAdmissionTelemetryMigrationError,
        match="source document fingerprint mismatched",
    ):
        _ = decode_ticket_admission_telemetry_document_versioned(
            _json_mutation(encoded, mutate)
        )
