# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Reference validation and atomic persistence for progress sidecar v1.
# - Must-Not:
#   - Publish final artifacts or infer compiler/checkpoint semantics.
# - Allows:
#   - Inputs: one explicit progress record and same-filesystem output path.
#   - Outputs: canonical JSON, validated records, and atomic sidecar
#     replacement.
#   - Side effects: sidecar-directory creation and atomic file replacement.
# - Split-When:
#   - Product compiler or accelerator adapters gain independent persistence.
# - Merge-When:
#   - Another module owns this exact cross-language sidecar contract.
# - Summary:
#   - Fail-closed reference implementation of `malbolge-progress-v1`.
# - Description:
#   - Validates identity, timing, checkpoint, and publication invariants.
# - Usage:
#   - Construct, validate, encode, read, or atomically write one sidecar.
# - Defaults:
#   - Unknown keys, duplicate keys, stale fingerprints, and torn pairs fail.
#

"""Reference implementation of the versioned Malbolge progress sidecar."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from datetime import UTC
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Final
from typing import Never
from typing import cast

SCHEMA_ID: Final = "malbolge-progress-v1"
COMPATIBILITY_PREFIX: Final = "malbolge-progress-compat-v1:sha256:"
TERMINAL_STATUSES: Final = frozenset({"cancelled", "completed", "failed"})
WINDOWS_PLATFORM: Final = "nt"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_PROFILE = re.compile(r"malbolge-profile-v1:sha256:[0-9a-f]{64}")
_COMPATIBILITY = re.compile(r"malbolge-progress-compat-v1:sha256:[0-9a-f]{64}")
_UTC_DATE: Final = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
_UTC_TIME: Final = r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z"
_UTC = re.compile(f"{_UTC_DATE}{_UTC_TIME}")

type JsonScalar = str | int | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class ProgressSidecarError(ValueError):
    """One progress sidecar is malformed or internally inconsistent."""


class ProgressStatus(Enum):
    """Stable lifecycle state for one long-running operation."""

    CANCELLED = "cancelled"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"
    RUNNING = "running"


@dataclass(frozen=True, slots=True)
class ResumeIdentity:
    """Backend-neutral identity required to reuse a checkpoint."""

    algorithm_id: str
    algorithm_version: str
    schema: str
    seed: int | None
    source_sha256: str
    target_profile_fingerprint: str
    target_profile_id: str
    toolchain_fingerprint: str


@dataclass(frozen=True, slots=True)
class ProgressSidecar:
    """One exact `malbolge-progress-v1` document."""

    active_elapsed_ns: int
    algorithm_id: str
    algorithm_version: str
    backend: str
    checkpoint_elapsed_ns: int
    checkpoint_path: str | None
    checkpoint_sequence: int
    checkpoint_sha256: str | None
    compatibility_fingerprint: str
    completed_at: str | None
    device: str | None
    diagnostic_code: str | None
    diagnostic_message: str | None
    operation_id: str
    output_path: str
    partial_bytes: int | None
    partial_path: str | None
    partial_sha256: str | None
    paused_elapsed_ns: int
    progress_path: str
    schema: str
    seed: int | None
    serialization_elapsed_ns: int
    source_path: str
    source_sha256: str
    stage: str
    started_at: str
    status: ProgressStatus
    target_profile_fingerprint: str
    target_profile_id: str
    toolchain_fingerprint: str
    units_completed: int
    units_total: int | None
    updated_at: str
    verification_elapsed_ns: int
    wall_elapsed_ns: int


def _fail(message: str) -> Never:
    raise ProgressSidecarError(message)


def progress_path(output: str | Path) -> Path:
    """Return the canonical progress sidecar path.

    Returns:
        `<output>.progress.json` beside the requested artifact.

    """
    return Path(f"{output}.progress.json")


def checkpoint_path(output: str | Path) -> Path:
    """Return the canonical checkpoint path.

    Returns:
        `<output>.checkpoint` beside the requested artifact.

    """
    return Path(f"{output}.checkpoint")


def partial_path(output: str | Path) -> Path:
    """Return the canonical partial-artifact path.

    Returns:
        `<output>.partial` beside the requested artifact.

    """
    return Path(f"{output}.partial")


def resume_compatibility_fingerprint(identity: ResumeIdentity) -> str:
    """Hash backend-neutral identity required to resume a checkpoint.

    Returns:
        Stable versioned SHA-256 compatibility fingerprint.

    """
    encoded = json.dumps(
        asdict(identity),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return COMPATIBILITY_PREFIX + sha256(encoded).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate progress JSON key: {key}")
        result[key] = cast("JsonValue", value)
    return result


def _mapping(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    result: JsonObject = {}
    mapping = cast("dict[object, object]", value)
    for key, item in mapping.items():
        if type(key) is not str:
            _fail(f"{context} contains a non-string key")
        result[key] = cast("JsonValue", item)
    return result


def _string(value: JsonValue, context: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{context} must be a non-empty string")
    return value


def _optional_string(value: JsonValue, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context)


def _integer(value: JsonValue, context: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{context} must be a non-negative integer")
    return value


def _optional_integer(value: JsonValue, context: str) -> int | None:
    if value is None:
        return None
    return _integer(value, context)


def _identifier(value: str, context: str) -> None:
    if _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{context} is not a stable identifier")


def _digest(value: str, context: str) -> None:
    if _DIGEST.fullmatch(value) is None:
        _fail(f"{context} must use sha256 plus 64 lowercase hex digits")


def _timestamp(value: str, context: str) -> datetime:
    if _UTC.fullmatch(value) is None:
        _fail(f"{context} must be an ISO-8601 UTC timestamp ending in Z")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    if parsed.tzinfo != UTC:
        _fail(f"{context} must be UTC")
    return parsed


def _status(value: JsonValue) -> ProgressStatus:
    raw = _string(value, "status")
    try:
        return ProgressStatus(raw)
    except ValueError:
        _fail(f"unsupported progress status: {raw}")


def _str_field(document: JsonObject, key: str) -> str:
    return _string(document[key], key)


def _opt_str_field(document: JsonObject, key: str) -> str | None:
    return _optional_string(document[key], key)


def _int_field(document: JsonObject, key: str) -> int:
    return _integer(document[key], key)


def _opt_int_field(document: JsonObject, key: str) -> int | None:
    return _optional_integer(document[key], key)


def _from_document(document: JsonObject) -> ProgressSidecar:
    expected = frozenset(field.name for field in fields(ProgressSidecar))
    actual = frozenset(document)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        _fail("missing progress keys: " + ",".join(missing))
    if unknown:
        _fail("unknown progress keys: " + ",".join(unknown))
    compatibility = _str_field(document, "compatibility_fingerprint")
    serialization = _int_field(document, "serialization_elapsed_ns")
    profile_fingerprint = _str_field(document, "target_profile_fingerprint")
    return ProgressSidecar(
        active_elapsed_ns=_int_field(document, "active_elapsed_ns"),
        algorithm_id=_str_field(document, "algorithm_id"),
        algorithm_version=_str_field(document, "algorithm_version"),
        backend=_str_field(document, "backend"),
        checkpoint_elapsed_ns=_int_field(document, "checkpoint_elapsed_ns"),
        checkpoint_path=_opt_str_field(document, "checkpoint_path"),
        checkpoint_sequence=_int_field(document, "checkpoint_sequence"),
        checkpoint_sha256=_opt_str_field(document, "checkpoint_sha256"),
        compatibility_fingerprint=compatibility,
        completed_at=_opt_str_field(document, "completed_at"),
        device=_opt_str_field(document, "device"),
        diagnostic_code=_opt_str_field(document, "diagnostic_code"),
        diagnostic_message=_opt_str_field(document, "diagnostic_message"),
        operation_id=_str_field(document, "operation_id"),
        output_path=_str_field(document, "output_path"),
        partial_bytes=_opt_int_field(document, "partial_bytes"),
        partial_path=_opt_str_field(document, "partial_path"),
        partial_sha256=_opt_str_field(document, "partial_sha256"),
        paused_elapsed_ns=_int_field(document, "paused_elapsed_ns"),
        progress_path=_str_field(document, "progress_path"),
        schema=_str_field(document, "schema"),
        seed=_opt_int_field(document, "seed"),
        serialization_elapsed_ns=serialization,
        source_path=_str_field(document, "source_path"),
        source_sha256=_str_field(document, "source_sha256"),
        stage=_str_field(document, "stage"),
        started_at=_str_field(document, "started_at"),
        status=_status(document["status"]),
        target_profile_fingerprint=profile_fingerprint,
        target_profile_id=_str_field(document, "target_profile_id"),
        toolchain_fingerprint=_str_field(document, "toolchain_fingerprint"),
        units_completed=_int_field(document, "units_completed"),
        units_total=_opt_int_field(document, "units_total"),
        updated_at=_str_field(document, "updated_at"),
        verification_elapsed_ns=_int_field(document, "verification_elapsed_ns"),
        wall_elapsed_ns=_int_field(document, "wall_elapsed_ns"),
    )


def _validate_identity(sidecar: ProgressSidecar) -> None:
    for value, context in (
        (sidecar.operation_id, "operation_id"),
        (sidecar.algorithm_id, "algorithm_id"),
        (sidecar.algorithm_version, "algorithm_version"),
        (sidecar.backend, "backend"),
        (sidecar.stage, "stage"),
        (sidecar.target_profile_id, "target_profile_id"),
    ):
        _identifier(value, context)
    _digest(sidecar.source_sha256, "source_sha256")
    _digest(sidecar.toolchain_fingerprint, "toolchain_fingerprint")
    if _PROFILE.fullmatch(sidecar.target_profile_fingerprint) is None:
        _fail("target_profile_fingerprint is invalid")
    if _COMPATIBILITY.fullmatch(sidecar.compatibility_fingerprint) is None:
        _fail("compatibility_fingerprint is invalid")
    identity = ResumeIdentity(
        algorithm_id=sidecar.algorithm_id,
        algorithm_version=sidecar.algorithm_version,
        schema=sidecar.schema,
        seed=sidecar.seed,
        source_sha256=sidecar.source_sha256,
        target_profile_fingerprint=sidecar.target_profile_fingerprint,
        target_profile_id=sidecar.target_profile_id,
        toolchain_fingerprint=sidecar.toolchain_fingerprint,
    )
    expected = resume_compatibility_fingerprint(identity)
    if sidecar.compatibility_fingerprint != expected:
        _fail("resume compatibility fingerprint mismatch")


def _validate_paths(sidecar: ProgressSidecar) -> None:
    if sidecar.progress_path != str(progress_path(sidecar.output_path)):
        _fail("progress_path does not match output_path")
    expected_checkpoint = str(checkpoint_path(sidecar.output_path))
    if sidecar.checkpoint_path not in {None, expected_checkpoint}:
        _fail("checkpoint_path does not match output_path")
    expected_partial = str(partial_path(sidecar.output_path))
    if sidecar.partial_path not in {None, expected_partial}:
        _fail("partial_path does not match output_path")


def _validate_units(sidecar: ProgressSidecar) -> None:
    if (
        sidecar.units_total is not None
        and sidecar.units_completed > sidecar.units_total
    ):
        _fail("units_completed exceeds units_total")


def _validate_elapsed_times(sidecar: ProgressSidecar) -> None:
    if sidecar.active_elapsed_ns > sidecar.wall_elapsed_ns:
        _fail("active_elapsed_ns exceeds wall_elapsed_ns")
    if sidecar.paused_elapsed_ns > sidecar.wall_elapsed_ns:
        _fail("paused_elapsed_ns exceeds wall_elapsed_ns")
    accounted = sidecar.active_elapsed_ns + sidecar.paused_elapsed_ns
    if accounted > sidecar.wall_elapsed_ns:
        _fail("active plus paused elapsed time exceeds wall time")
    phases = (
        sidecar.checkpoint_elapsed_ns,
        sidecar.serialization_elapsed_ns,
        sidecar.verification_elapsed_ns,
    )
    if any(value > sidecar.wall_elapsed_ns for value in phases):
        _fail("phase elapsed time exceeds wall_elapsed_ns")


def _validate_timestamps(sidecar: ProgressSidecar) -> None:
    started = _timestamp(sidecar.started_at, "started_at")
    updated = _timestamp(sidecar.updated_at, "updated_at")
    if updated < started:
        _fail("updated_at precedes started_at")
    terminal = sidecar.status.value in TERMINAL_STATUSES
    if terminal != (sidecar.completed_at is not None):
        _fail("completed_at presence does not match terminal status")
    if sidecar.completed_at is not None:
        completed = _timestamp(sidecar.completed_at, "completed_at")
        if completed < updated:
            _fail("completed_at precedes updated_at")


def _validate_timing(sidecar: ProgressSidecar) -> None:
    _validate_units(sidecar)
    _validate_elapsed_times(sidecar)
    _validate_timestamps(sidecar)


def _validate_checkpoint_pair(sidecar: ProgressSidecar) -> None:
    has_path = sidecar.checkpoint_path is not None
    has_hash = sidecar.checkpoint_sha256 is not None
    if has_path != has_hash:
        _fail("checkpoint path/hash must be present together")
    if sidecar.checkpoint_sequence == 0 and has_path:
        _fail("checkpoint sequence zero cannot name checkpoint data")
    if sidecar.checkpoint_sequence > 0 and not has_path:
        _fail("positive checkpoint sequence requires checkpoint data")
    if sidecar.checkpoint_sha256 is not None:
        _digest(sidecar.checkpoint_sha256, "checkpoint_sha256")


def _validate_checkpoint_status(sidecar: ProgressSidecar) -> None:
    if (
        sidecar.status is ProgressStatus.CHECKPOINTED
        and sidecar.checkpoint_sequence == 0
    ):
        _fail("checkpointed status requires durable checkpoint data")


def _validate_checkpoint(sidecar: ProgressSidecar) -> None:
    _validate_checkpoint_pair(sidecar)
    _validate_checkpoint_status(sidecar)


def _validate_partial(sidecar: ProgressSidecar) -> None:
    members = (
        sidecar.partial_path is not None,
        sidecar.partial_bytes is not None,
        sidecar.partial_sha256 is not None,
    )
    if len(set(members)) != 1:
        _fail("partial path/bytes/hash must be present together")
    if sidecar.partial_sha256 is not None:
        _digest(sidecar.partial_sha256, "partial_sha256")
    if sidecar.status is ProgressStatus.COMPLETED and any(members):
        _fail("completed status cannot retain a partial artifact")


def _validate_diagnostic(sidecar: ProgressSidecar) -> None:
    has_code = sidecar.diagnostic_code is not None
    has_message = sidecar.diagnostic_message is not None
    if has_code != has_message:
        _fail("diagnostic code/message must be present together")
    required = sidecar.status in {
        ProgressStatus.CANCELLED,
        ProgressStatus.FAILED,
    }
    if required != has_code:
        _fail("diagnostic presence does not match progress status")
    if sidecar.diagnostic_code is not None:
        _identifier(sidecar.diagnostic_code, "diagnostic_code")


def validate(sidecar: ProgressSidecar) -> ProgressSidecar:
    """Validate one complete sidecar fail-closed.

    Returns:
        The same immutable sidecar after all invariants pass.

    """
    if sidecar.schema != SCHEMA_ID:
        _fail(f"unsupported progress schema: {sidecar.schema}")
    _validate_identity(sidecar)
    _validate_paths(sidecar)
    _validate_timing(sidecar)
    _validate_checkpoint(sidecar)
    _validate_partial(sidecar)
    _validate_diagnostic(sidecar)
    return sidecar


def to_document(sidecar: ProgressSidecar) -> JsonObject:
    """Convert one validated sidecar to its flat JSON object.

    Returns:
        Exact v1 document with the status enum encoded as text.

    """
    validated = validate(sidecar)
    document = cast("JsonObject", asdict(validated))
    document["status"] = validated.status.value
    return document


def encode(sidecar: ProgressSidecar) -> bytes:
    """Encode one sidecar as canonical UTF-8 JSON.

    Returns:
        Sorted compact JSON with one trailing newline.

    """
    text = json.dumps(
        to_document(sidecar),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (text + "\n").encode("utf-8")


def loads(text: str) -> ProgressSidecar:
    """Parse one sidecar while rejecting duplicate keys.

    Returns:
        Immutable validated progress sidecar.

    """
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        _fail(f"invalid progress JSON: {error}")
    return validate(_from_document(_mapping(parsed, "progress sidecar")))


def read(path: Path) -> ProgressSidecar:
    """Read and validate one sidecar file.

    Returns:
        Immutable validated progress sidecar.

    """
    return loads(path.read_text(encoding="utf-8-sig"))


def _flush_parent(path: Path, *, platform: str = os.name) -> None:
    if platform == WINDOWS_PLATFORM:
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_atomic(sidecar: ProgressSidecar) -> Path:
    """Atomically replace one canonical sidecar.

    Returns:
        Canonical progress path after flush and atomic replacement.

    """
    payload = encode(sidecar)
    destination = Path(sidecar.progress_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            _ = stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _ = temporary.replace(destination)
        _flush_parent(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
