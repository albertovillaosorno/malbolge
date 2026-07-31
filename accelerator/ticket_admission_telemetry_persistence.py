# File:
#   - ticket_admission_telemetry_persistence.py
# Path:
#   - accelerator/ticket_admission_telemetry_persistence.py
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
#   - Canonical bounded persistence for caller-owned ticket telemetry snapshots.
# - Must-Not:
#   - Load automatically, change admission, learn routes, or retain error text.
# - Allows:
#   - Inputs: validated completed/failed snapshots and explicit file paths.
#   - Outputs: canonical schema-v1 JSON bytes and restored caller-owned
#     recorders.
#   - Side effects: explicit bounded file reads and atomic file replacement
#     only.
# - Split-When:
#   - Split when another telemetry family gains its own schema.
# - Merge-When:
#   - Merge when another module owns this exact persistence contract.
# - Summary:
#   - Canonical opt-in ticket telemetry persistence.
# - Description:
#   - Encodes and restores bounded snapshots without granting policy authority.
# - Usage:
#   - Capture explicitly, write/read explicitly, then restore explicitly.
# - Defaults:
#   - Noncanonical, oversized, duplicate, unknown, or malformed input fails
#     closed.
#
# Related documents:
# - accelerator/ticket_admission_telemetry.py
# - accelerator/ticket_admission_telemetry_summary.py
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_overlap.py
# - accelerator/ticket_admission_telemetry_overlap_index.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Canonical opt-in persistence for bounded ticket admission telemetry."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final
from typing import Never
from typing import cast

from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionFailureKind
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureObservation,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetrySnapshot,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionObservation
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetryError
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionTelemetrySnapshot,
)

TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID: Final = (
    "ticket-admission-telemetry-document-v1"
)
TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION: Final = 1
DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES: Final = 1_048_576
DEFAULT_MAX_TELEMETRY_OBSERVATIONS: Final = 4_096

_ROOT_KEYS: Final = frozenset(
    ("completed", "document_id", "failed", "schema_version")
)
_SNAPSHOT_KEYS: Final = frozenset(
    (
        "capacity",
        "dropped_observation_count",
        "next_sequence_id",
        "observations",
        "telemetry_id",
    )
)
_COMPLETED_OBSERVATION_KEYS: Final = frozenset(
    (
        "admission_id",
        "backend_id",
        "chunk_count",
        "device_arch",
        "device_name",
        "elapsed_ns",
        "estimate_delta_ns",
        "estimated_ns",
        "fallback_ticket_count",
        "report_id",
        "selected_evidence_ids",
        "selected_streamed_ticket_count",
        "selected_synchronous_ticket_count",
        "sequence_id",
        "ticket_count",
        "workload_id",
    )
)
_FAILURE_OBSERVATION_KEYS: Final = frozenset(
    (*_COMPLETED_OBSERVATION_KEYS, "failure_kind")
)


class TicketAdmissionTelemetryPersistenceError(ValueError):
    """Persisted ticket telemetry bytes or storage operation are invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryDocument:
    """One canonical completed/failed telemetry persistence document."""

    completed: TicketAdmissionTelemetrySnapshot
    document_id: str
    failed: TicketAdmissionFailureTelemetrySnapshot
    schema_version: int


@dataclass(frozen=True, slots=True)
class _ObservationFields:
    admission_id: str
    backend_id: str
    chunk_count: int
    device_arch: str
    device_name: str
    elapsed_ns: int
    estimate_delta_ns: int
    estimated_ns: int
    fallback_ticket_count: int
    report_id: str
    selected_evidence_ids: tuple[str, ...]
    selected_streamed_ticket_count: int
    selected_synchronous_ticket_count: int
    sequence_id: int
    ticket_count: int
    workload_id: str


@dataclass(frozen=True, slots=True)
class _SnapshotFields:
    capacity: int
    dropped_observation_count: int
    next_sequence_id: int
    telemetry_id: str


def ticket_admission_telemetry_document_id() -> str:
    """Return the stable canonical telemetry document identity.

    Returns:
        Versioned persistence document identity.

    """
    return TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID


def capture_ticket_admission_telemetry_document(
    telemetry: TicketAdmissionAttemptTelemetry,
) -> TicketAdmissionTelemetryDocument:
    """Capture both caller-owned FIFO snapshots at one explicit boundary.

    Returns:
        Validated immutable persistence document.

    """
    if type(telemetry) is not TicketAdmissionAttemptTelemetry:
        _raise_persistence("attempt telemetry type is invalid")
    if type(telemetry.completed) is not TicketAdmissionTelemetry:
        _raise_persistence("completed telemetry type is invalid")
    if type(telemetry.failed) is not TicketAdmissionFailureTelemetry:
        _raise_persistence("failure telemetry type is invalid")
    return _validated_document(TicketAdmissionTelemetryDocument(
        completed=telemetry.completed.snapshot(),
        document_id=TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID,
        failed=telemetry.failed.snapshot(),
        schema_version=TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION,
    ))


def encode_ticket_admission_telemetry_document(
    document: TicketAdmissionTelemetryDocument,
) -> bytes:
    """Encode one validated document as canonical compact UTF-8 JSON.

    Returns:
        Sorted-key, separator-minimized JSON with one trailing newline.

    """
    state = _validated_document(document)
    text = json.dumps(
        asdict(state),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def decode_ticket_admission_telemetry_document(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
    max_observations: int = DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
) -> TicketAdmissionTelemetryDocument:
    """Decode canonical bounded telemetry bytes with strict schema validation.

    Returns:
        Validated immutable telemetry document.

    """
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    observation_limit = _validated_positive_limit(
        max_observations,
        "observation limit",
    )
    payload = _validated_payload(data, byte_limit)
    document = _document(_json_document(payload), observation_limit)
    if encode_ticket_admission_telemetry_document(document) != payload:
        _raise_persistence("document bytes are not canonical")
    return document


def restore_ticket_admission_telemetry(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionAttemptTelemetry:
    """Restore caller-owned recorders without changing retained sequence state.

    Returns:
        Explicit completed/failed recorder pair continuing both FIFOs.

    """
    state = _validated_document(document)
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry.from_snapshot(state.completed),
        failed=TicketAdmissionFailureTelemetry.from_snapshot(state.failed),
    )


def write_ticket_admission_telemetry_document(
    path: Path,
    document: TicketAdmissionTelemetryDocument,
) -> None:
    """Atomically replace one explicit path with canonical telemetry bytes.

    Raises:
        TicketAdmissionTelemetryPersistenceError: If encoding or writing fails.

    """
    destination = _validated_path(path)
    payload = encode_ticket_admission_telemetry_document(document)
    temporary = _write_temporary(destination, payload)
    try:
        _ = temporary.replace(destination)
    except OSError as error:
        _remove_temporary(temporary)
        message = f"cannot replace telemetry document: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error


def read_ticket_admission_telemetry_document(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
    max_observations: int = DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
) -> TicketAdmissionTelemetryDocument:
    """Read one explicit path under bounded byte and observation limits.

    Returns:
        Validated canonical telemetry document.

    Raises:
        TicketAdmissionTelemetryPersistenceError: If reading or decoding fails.

    """
    source = _validated_path(path)
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    try:
        with source.open("rb") as input_file:
            payload = input_file.read(byte_limit + 1)
    except OSError as error:
        message = f"cannot read telemetry document: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error
    return decode_ticket_admission_telemetry_document(
        payload,
        max_bytes=byte_limit,
        max_observations=max_observations,
    )


def _validated_document(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocument:
    if type(document) is not TicketAdmissionTelemetryDocument:
        _raise_persistence("document type is invalid")
    if (
        type(document.document_id) is not str
        or document.document_id != TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID
    ):
        _raise_persistence("document identity mismatched")
    if (
        type(document.schema_version) is not int
        or document.schema_version != TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION
    ):
        _raise_persistence("document schema is unsupported")
    try:
        _ = TicketAdmissionTelemetry.from_snapshot(document.completed)
        _ = TicketAdmissionFailureTelemetry.from_snapshot(document.failed)
    except TicketAdmissionTelemetryError as error:
        message = f"invalid telemetry document state: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error
    return document


def _validated_payload(data: bytes, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_persistence("document payload must be bytes")
    if not data:
        _raise_persistence("document payload must not be empty")
    if len(data) > max_bytes:
        _raise_persistence("document exceeds configured byte limit")
    return data


def _json_document(data: bytes) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        message = f"telemetry document is not UTF-8: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error
    try:
        parsed = cast(
            "object",
            json.loads(
                text,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            ),
        )
    except json.JSONDecodeError as error:
        message = f"invalid telemetry document JSON: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error
    return _expect_mapping(parsed, "telemetry document")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _raise_persistence(f"duplicate telemetry JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Never:
    _raise_persistence(f"invalid telemetry JSON constant: {value}")


def _document(
    mapping: dict[str, object],
    max_observations: int,
) -> TicketAdmissionTelemetryDocument:
    _expect_exact_keys(mapping, _ROOT_KEYS, "telemetry document")
    document_id = _expect_string(
        mapping["document_id"],
        "telemetry document.document_id",
    )
    schema_version = _expect_int(
        mapping["schema_version"],
        "telemetry document.schema_version",
    )
    completed = _completed_snapshot(
        mapping["completed"],
        max_observations=max_observations,
    )
    failed = _failure_snapshot(
        mapping["failed"],
        max_observations=max_observations,
    )
    return _validated_document(TicketAdmissionTelemetryDocument(
        completed=completed,
        document_id=document_id,
        failed=failed,
        schema_version=schema_version,
    ))


def _completed_snapshot(
    value: object,
    *,
    max_observations: int,
) -> TicketAdmissionTelemetrySnapshot:
    mapping = _expect_mapping(value, "completed snapshot")
    fields = _snapshot_fields(mapping, "completed snapshot")
    entries = _bounded_observations(
        mapping["observations"],
        max_observations=max_observations,
        context="completed snapshot.observations",
    )
    observations = tuple(
        _completed_observation(entry, index)
        for index, entry in enumerate(entries)
    )
    _validate_snapshot_capacity(fields.capacity, max_observations)
    return TicketAdmissionTelemetrySnapshot(
        capacity=fields.capacity,
        dropped_observation_count=fields.dropped_observation_count,
        next_sequence_id=fields.next_sequence_id,
        observations=observations,
        telemetry_id=fields.telemetry_id,
    )


def _failure_snapshot(
    value: object,
    *,
    max_observations: int,
) -> TicketAdmissionFailureTelemetrySnapshot:
    mapping = _expect_mapping(value, "failure snapshot")
    fields = _snapshot_fields(mapping, "failure snapshot")
    entries = _bounded_observations(
        mapping["observations"],
        max_observations=max_observations,
        context="failure snapshot.observations",
    )
    observations = tuple(
        _failure_observation(entry, index)
        for index, entry in enumerate(entries)
    )
    _validate_snapshot_capacity(fields.capacity, max_observations)
    return TicketAdmissionFailureTelemetrySnapshot(
        capacity=fields.capacity,
        dropped_observation_count=fields.dropped_observation_count,
        next_sequence_id=fields.next_sequence_id,
        observations=observations,
        telemetry_id=fields.telemetry_id,
    )


def _snapshot_fields(
    mapping: dict[str, object],
    context: str,
) -> _SnapshotFields:
    _expect_exact_keys(mapping, _SNAPSHOT_KEYS, context)
    return _SnapshotFields(
        capacity=_expect_int(mapping["capacity"], f"{context}.capacity"),
        dropped_observation_count=_expect_int(
            mapping["dropped_observation_count"],
            f"{context}.dropped_observation_count",
        ),
        next_sequence_id=_expect_int(
            mapping["next_sequence_id"],
            f"{context}.next_sequence_id",
        ),
        telemetry_id=_expect_string(
            mapping["telemetry_id"],
            f"{context}.telemetry_id",
        ),
    )


def _completed_observation(
    value: object,
    index: int,
) -> TicketAdmissionObservation:
    context = f"completed observation[{index}]"
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _COMPLETED_OBSERVATION_KEYS, context)
    fields = _observation_fields(mapping, context)
    return TicketAdmissionObservation(
        admission_id=fields.admission_id,
        backend_id=fields.backend_id,
        chunk_count=fields.chunk_count,
        device_arch=fields.device_arch,
        device_name=fields.device_name,
        elapsed_ns=fields.elapsed_ns,
        estimate_delta_ns=fields.estimate_delta_ns,
        estimated_ns=fields.estimated_ns,
        fallback_ticket_count=fields.fallback_ticket_count,
        report_id=fields.report_id,
        selected_evidence_ids=fields.selected_evidence_ids,
        selected_streamed_ticket_count=fields.selected_streamed_ticket_count,
        selected_synchronous_ticket_count=(
            fields.selected_synchronous_ticket_count
        ),
        sequence_id=fields.sequence_id,
        ticket_count=fields.ticket_count,
        workload_id=fields.workload_id,
    )


def _failure_observation(
    value: object,
    index: int,
) -> TicketAdmissionFailureObservation:
    context = f"failure observation[{index}]"
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _FAILURE_OBSERVATION_KEYS, context)
    fields = _observation_fields(mapping, context)
    failure_kind = _failure_kind(mapping["failure_kind"], context)
    return TicketAdmissionFailureObservation(
        admission_id=fields.admission_id,
        backend_id=fields.backend_id,
        chunk_count=fields.chunk_count,
        device_arch=fields.device_arch,
        device_name=fields.device_name,
        elapsed_ns=fields.elapsed_ns,
        estimate_delta_ns=fields.estimate_delta_ns,
        estimated_ns=fields.estimated_ns,
        failure_kind=failure_kind,
        fallback_ticket_count=fields.fallback_ticket_count,
        report_id=fields.report_id,
        selected_evidence_ids=fields.selected_evidence_ids,
        selected_streamed_ticket_count=fields.selected_streamed_ticket_count,
        selected_synchronous_ticket_count=(
            fields.selected_synchronous_ticket_count
        ),
        sequence_id=fields.sequence_id,
        ticket_count=fields.ticket_count,
        workload_id=fields.workload_id,
    )


def _observation_fields(
    mapping: dict[str, object],
    context: str,
) -> _ObservationFields:
    return _ObservationFields(
        admission_id=_expect_string(
            mapping["admission_id"],
            f"{context}.admission_id",
        ),
        backend_id=_expect_string(
            mapping["backend_id"],
            f"{context}.backend_id",
        ),
        chunk_count=_expect_int(
            mapping["chunk_count"],
            f"{context}.chunk_count",
        ),
        device_arch=_expect_string(
            mapping["device_arch"],
            f"{context}.device_arch",
        ),
        device_name=_expect_string(
            mapping["device_name"],
            f"{context}.device_name",
        ),
        elapsed_ns=_expect_int(
            mapping["elapsed_ns"],
            f"{context}.elapsed_ns",
        ),
        estimate_delta_ns=_expect_int(
            mapping["estimate_delta_ns"],
            f"{context}.estimate_delta_ns",
            allow_negative=True,
        ),
        estimated_ns=_expect_int(
            mapping["estimated_ns"],
            f"{context}.estimated_ns",
        ),
        fallback_ticket_count=_expect_int(
            mapping["fallback_ticket_count"],
            f"{context}.fallback_ticket_count",
        ),
        report_id=_expect_string(
            mapping["report_id"],
            f"{context}.report_id",
        ),
        selected_evidence_ids=_evidence_ids(
            mapping["selected_evidence_ids"],
            context,
        ),
        selected_streamed_ticket_count=_expect_int(
            mapping["selected_streamed_ticket_count"],
            f"{context}.selected_streamed_ticket_count",
        ),
        selected_synchronous_ticket_count=_expect_int(
            mapping["selected_synchronous_ticket_count"],
            f"{context}.selected_synchronous_ticket_count",
        ),
        sequence_id=_expect_int(
            mapping["sequence_id"],
            f"{context}.sequence_id",
        ),
        ticket_count=_expect_int(
            mapping["ticket_count"],
            f"{context}.ticket_count",
        ),
        workload_id=_expect_string(
            mapping["workload_id"],
            f"{context}.workload_id",
        ),
    )


def _failure_kind(value: object, context: str) -> TicketAdmissionFailureKind:
    text = _expect_string(value, f"{context}.failure_kind")
    try:
        return TicketAdmissionFailureKind(text)
    except ValueError as error:
        message = f"{context}.failure_kind is unsupported: {text}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error


def _evidence_ids(value: object, context: str) -> tuple[str, ...]:
    entries = _expect_array(value, f"{context}.selected_evidence_ids")
    return tuple(
        _expect_string(entry, f"{context}.selected_evidence_ids[{index}]")
        for index, entry in enumerate(entries)
    )


def _bounded_observations(
    value: object,
    *,
    max_observations: int,
    context: str,
) -> list[object]:
    entries = _expect_array(value, context)
    if len(entries) > max_observations:
        _raise_persistence(f"{context} exceeds configured observation limit")
    return entries


def _validate_snapshot_capacity(capacity: int, max_observations: int) -> None:
    if capacity > max_observations:
        _raise_persistence("snapshot capacity exceeds observation limit")


def _expect_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _raise_persistence(f"{context} must be a JSON object")
    mapping = cast("dict[object, object]", value)
    if any(type(key) is not str for key in mapping):
        _raise_persistence(f"{context} contains a non-string key")
    return cast("dict[str, object]", mapping)


def _expect_array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        _raise_persistence(f"{context} must be a JSON array")
    return cast("list[object]", value)


def _expect_exact_keys(
    mapping: dict[str, object],
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        _raise_persistence(f"{context} is missing key: {missing[0]}")
    if unknown:
        _raise_persistence(f"{context} contains unknown key: {unknown[0]}")


def _expect_string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        _raise_persistence(f"{context} must be a non-empty string")
    return value


def _expect_int(
    value: object,
    context: str,
    *,
    allow_negative: bool = False,
) -> int:
    if type(value) is not int:
        _raise_persistence(f"{context} must be an integer")
    if not allow_negative and value < 0:
        _raise_persistence(f"{context} must be non-negative")
    return value


def _validated_positive_limit(value: int, label: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_persistence(f"{label} must be a positive integer")
    return value


def _validated_path(path: object) -> Path:
    if not isinstance(path, Path):
        _raise_persistence("telemetry path must be a pathlib Path")
    if not path.name:
        _raise_persistence("telemetry path must name a file")
    return path


def _write_temporary(destination: Path, payload: bytes) -> Path:
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            _ = output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        if temporary is not None:
            _remove_temporary(temporary)
        message = f"cannot write telemetry document: {error}"
        raise TicketAdmissionTelemetryPersistenceError(message) from error
    return temporary


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _raise_persistence(detail: str) -> Never:
    message = f"ticket admission telemetry persistence {detail}"
    raise TicketAdmissionTelemetryPersistenceError(message)
