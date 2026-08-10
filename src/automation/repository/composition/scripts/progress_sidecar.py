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
#   - Outputs: canonical JSON, validated records, exact timing summaries,
#     immutable generations, and atomic sidecar replacement.
#   - Side effects: immutable generation creation and atomic sidecar update.
# - Split-When:
#   - Product compiler or accelerator adapters gain independent persistence.
# - Merge-When:
#   - Another module owns this exact cross-language sidecar contract.
# - Summary:
#   - Fail-closed reference implementation of `malbolge-progress-v1`.
# - Description:
#   - Validates identity, timing, checkpoint, and publication invariants.
# - Usage:
#   - Construct, validate, encode, inspect, or durably write one sidecar.
# - Defaults:
#   - Unknown keys, duplicate keys, stale fingerprints, and torn pairs fail.
#

"""Reference implementation of the versioned Malbolge progress sidecar."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from datetime import UTC
from datetime import datetime
from enum import Enum
from hashlib import sha256
from importlib import import_module
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from time import monotonic_ns
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

SCHEMA_ID: Final = "malbolge-progress-v1"
COMPATIBILITY_PREFIX: Final = "malbolge-progress-compat-v1:sha256:"
TERMINAL_STATUSES: Final = frozenset({"cancelled", "completed", "failed"})
WINDOWS_PLATFORM: Final = "nt"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_PROFILE = re.compile(r"malbolge-profile-v1:sha256:[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40}")
_COMPATIBILITY = re.compile(r"malbolge-progress-compat-v1:sha256:[0-9a-f]{64}")
_UTC_DATE: Final = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
_UTC_TIME: Final = r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z"
_UTC = re.compile(f"{_UTC_DATE}{_UTC_TIME}")

type JsonScalar = str | int | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class ProgressSidecarError(ValueError):
    """One progress sidecar is malformed or internally inconsistent."""


class _LockStream(Protocol):
    """Seekable descriptor surface required by platform lock primitives."""

    def fileno(self) -> int:
        """Return the operating-system file descriptor."""
        ...

    def seek(self, target: int, whence: int = 0, /) -> int:
        """Move the descriptor-relative file position."""
        ...

    def close(self) -> None:
        """Close the operating-system lock stream."""
        ...


class _WindowsLockModule(Protocol):
    """Typed subset of the Windows CRT region-lock API."""

    LK_LOCK: int
    LK_UNLCK: int

    def locking(self, fd: int, mode: int, nbytes: int) -> None:
        """Lock or unlock one file region."""
        ...


class _PosixLockModule(Protocol):
    """Typed subset of the POSIX advisory flock API."""

    LOCK_EX: int
    LOCK_UN: int

    def flock(self, fd: int, operation: int) -> None:
        """Acquire or release one advisory file lock."""
        ...


class ProgressStatus(Enum):
    """Stable lifecycle state for one long-running operation."""

    CANCELLED = "cancelled"
    CHECKPOINTED = "checkpointed"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"
    RUNNING = "running"


class TimingPhase(Enum):
    """Exclusive monotonic timing phase for one long-running operation."""

    ACTIVE = "active"
    CHECKPOINT = "checkpoint"
    PAUSED = "paused"
    SERIALIZATION = "serialization"
    VERIFICATION = "verification"


def _validate_timing_phase(value: TimingPhase) -> None:
    if type(value) is not TimingPhase:
        _fail("timing phase must use the exact enum type")


def _monotonic_sample(value: object) -> int:
    if type(value) is not int or value < 0:
        _fail("monotonic clock must return a non-negative integer")
    return value


def _sample_clock(clock: object) -> int:
    if not callable(clock):
        _fail("monotonic clock must be callable")
    try:
        value = clock()
    except ProgressSidecarError:
        raise
    except Exception as error:  # ruff: ignore[blind-except] -- consumer clock boundary.
        _fail(f"monotonic clock failed: {error}")
    return _monotonic_sample(value)


@dataclass(frozen=True, slots=True)
class ProgressTiming:
    """One exact snapshot of accumulated monotonic durations."""

    active_elapsed_ns: int
    checkpoint_elapsed_ns: int
    paused_elapsed_ns: int
    serialization_elapsed_ns: int
    verification_elapsed_ns: int
    wall_elapsed_ns: int


@dataclass(slots=True)
class ProgressTimer:
    """Injectable monotonic phase timer for sidecar timing fields."""

    _clock: Callable[[], int]
    _phase: TimingPhase
    _segment_started_ns: int
    _started_ns: int
    _active_elapsed_ns: int = 0
    _checkpoint_elapsed_ns: int = 0
    _paused_elapsed_ns: int = 0
    _serialization_elapsed_ns: int = 0
    _verification_elapsed_ns: int = 0

    @classmethod
    def start(
        cls,
        phase: TimingPhase = TimingPhase.ACTIVE,
        clock: Callable[[], int] = monotonic_ns,
    ) -> ProgressTimer:
        """Start one timer using an injectable monotonic nanosecond clock.

        Returns:
            Timer whose first segment begins at the sampled clock value.

        """
        _validate_timing_phase(phase)
        now = _sample_clock(clock)
        return cls(
            _clock=clock,
            _phase=phase,
            _segment_started_ns=now,
            _started_ns=now,
        )

    def _validate_state(self) -> None:
        _validate_timing_phase(self._phase)
        if not callable(self._clock):
            _fail("monotonic clock must be callable")
        values = (
            (self._segment_started_ns, "timer segment start"),
            (self._started_ns, "timer start"),
            (self._active_elapsed_ns, "timer active elapsed"),
            (self._checkpoint_elapsed_ns, "timer checkpoint elapsed"),
            (self._paused_elapsed_ns, "timer paused elapsed"),
            (self._serialization_elapsed_ns, "timer serialization elapsed"),
            (self._verification_elapsed_ns, "timer verification elapsed"),
        )
        for value, context in values:
            _ = _nonnegative_integer(value, context)
        if self._segment_started_ns < self._started_ns:
            _fail("timer segment start precedes timer start")
        accumulated = (
            self._active_elapsed_ns
            + self._checkpoint_elapsed_ns
            + self._paused_elapsed_ns
            + self._serialization_elapsed_ns
            + self._verification_elapsed_ns
        )
        closed_elapsed = self._segment_started_ns - self._started_ns
        if accumulated != closed_elapsed:
            _fail("timer accumulated phases do not match closed elapsed time")

    @property
    def phase(self) -> TimingPhase:
        """The currently accumulating exclusive phase."""
        self._validate_state()
        return self._phase

    def _sample(self) -> int:
        self._validate_state()
        now = _sample_clock(self._clock)
        if now < self._segment_started_ns:
            _fail("monotonic clock moved backward")
        return now

    def _snapshot_at(self, now: int) -> ProgressTiming:
        active = self._active_elapsed_ns
        checkpoint = self._checkpoint_elapsed_ns
        paused = self._paused_elapsed_ns
        serialization = self._serialization_elapsed_ns
        verification = self._verification_elapsed_ns
        delta = now - self._segment_started_ns
        if self._phase is TimingPhase.ACTIVE:
            active += delta
        elif self._phase is TimingPhase.CHECKPOINT:
            checkpoint += delta
        elif self._phase is TimingPhase.PAUSED:
            paused += delta
        elif self._phase is TimingPhase.SERIALIZATION:
            serialization += delta
        else:
            verification += delta
        return ProgressTiming(
            active_elapsed_ns=active,
            checkpoint_elapsed_ns=checkpoint,
            paused_elapsed_ns=paused,
            serialization_elapsed_ns=serialization,
            verification_elapsed_ns=verification,
            wall_elapsed_ns=now - self._started_ns,
        )

    def snapshot(self) -> ProgressTiming:
        """Capture exact durations without changing the active phase.

        Returns:
            Exact timing snapshot at the sampled monotonic time.

        """
        return self._snapshot_at(self._sample())

    def switch(self, phase: TimingPhase) -> ProgressTiming:
        """Finish the current segment and begin one new exclusive phase.

        Returns:
            Exact timing snapshot at the phase boundary.

        """
        _validate_timing_phase(phase)
        now = self._sample()
        timing = self._snapshot_at(now)
        self._active_elapsed_ns = timing.active_elapsed_ns
        self._checkpoint_elapsed_ns = timing.checkpoint_elapsed_ns
        self._paused_elapsed_ns = timing.paused_elapsed_ns
        self._serialization_elapsed_ns = timing.serialization_elapsed_ns
        self._verification_elapsed_ns = timing.verification_elapsed_ns
        self._phase = phase
        self._segment_started_ns = now
        return timing


@dataclass(frozen=True, slots=True)
class ResumeIdentity:
    """Backend-neutral identity required to reuse a checkpoint."""

    algorithm_id: str
    algorithm_version: str
    repository_revision: str
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
    repository_revision: str
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


def _output_path_text(output: object) -> str:
    if type(output) is str:
        return output
    if isinstance(output, Path):
        return str(output)
    _fail("output path must use an exact string or pathlib Path")


def _read_path(path: object) -> Path:
    if not isinstance(path, Path):
        _fail("progress sidecar read path must use pathlib Path")
    return path


def progress_path(output: str | Path) -> Path:
    """Return the canonical progress sidecar path.

    Returns:
        `<output>.progress.json` beside the requested artifact.

    """
    return Path(f"{_output_path_text(output)}.progress.json")


def checkpoint_path(output: str | Path, sequence: int) -> Path:
    """Return one immutable sequence-addressed checkpoint path.

    Returns:
        `<output>.checkpoint.<sequence>` beside the requested artifact.

    """
    if type(sequence) is not int or sequence <= 0:
        _fail("checkpoint sequence must be a positive integer")
    return Path(f"{_output_path_text(output)}.checkpoint.{sequence:020d}")


def partial_path(output: str | Path, sequence: int) -> Path:
    """Return one immutable sequence-addressed partial-artifact path.

    Returns:
        `<output>.partial.<sequence>` beside the requested artifact.

    """
    if type(sequence) is not int or sequence <= 0:
        _fail("partial sequence must be a positive integer")
    return Path(f"{_output_path_text(output)}.partial.{sequence:020d}")


def resume_compatibility_fingerprint(identity: ResumeIdentity) -> str:
    """Hash backend-neutral identity required to resume a checkpoint.

    Returns:
        Stable versioned SHA-256 compatibility fingerprint.

    """
    validated = _validate_resume_identity(identity)
    encoded = json.dumps(
        asdict(validated),
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


def _string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{context} must be a non-empty string")
    return value


def _optional_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context)


def _nonnegative_integer(value: object, context: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{context} must be a non-negative integer")
    return value


def _integer(value: JsonValue, context: str) -> int:
    return _nonnegative_integer(value, context)


def _optional_integer(value: JsonValue, context: str) -> int | None:
    if value is None:
        return None
    return _integer(value, context)


def _identifier(value: object, context: str) -> None:
    text = _string(value, context)
    if _IDENTIFIER.fullmatch(text) is None:
        _fail(f"{context} is not a stable identifier")


def _digest(value: object, context: str) -> None:
    text = _string(value, context)
    if _DIGEST.fullmatch(text) is None:
        _fail(f"{context} must use sha256 plus 64 lowercase hex digits")


def _timestamp(value: object, context: str) -> datetime:
    text = _string(value, context)
    if _UTC.fullmatch(text) is None:
        _fail(f"{context} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(text.removesuffix("Z") + "+00:00")
    except ValueError as error:
        _fail(f"{context} is not a valid UTC timestamp: {error}")
    if parsed.tzinfo != UTC:
        _fail(f"{context} must be UTC")
    return parsed


def _validate_revision(value: object) -> None:
    text = _string(value, "repository_revision")
    if _REVISION.fullmatch(text) is None:
        _fail("repository_revision must be a lowercase 40-hex Git commit")


def _validate_profile_fingerprint(value: object) -> None:
    text = _string(value, "target_profile_fingerprint")
    if _PROFILE.fullmatch(text) is None:
        _fail("target_profile_fingerprint is invalid")


def _validate_resume_identity(identity: ResumeIdentity) -> ResumeIdentity:
    if type(identity) is not ResumeIdentity:
        _fail("resume identity must use the exact immutable type")
    for value, context in (
        (identity.algorithm_id, "algorithm_id"),
        (identity.algorithm_version, "algorithm_version"),
        (identity.target_profile_id, "target_profile_id"),
    ):
        _identifier(value, context)
    if identity.schema != SCHEMA_ID:
        _fail(f"unsupported progress schema: {identity.schema}")
    if identity.seed is not None:
        _ = _nonnegative_integer(identity.seed, "seed")
    _digest(identity.source_sha256, "source_sha256")
    _digest(identity.toolchain_fingerprint, "toolchain_fingerprint")
    _validate_revision(identity.repository_revision)
    _validate_profile_fingerprint(identity.target_profile_fingerprint)
    return identity


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
        repository_revision=_str_field(document, "repository_revision"),
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


def _validate_identity_formats(sidecar: ProgressSidecar) -> None:
    _ = _validate_resume_identity(_resume_identity(sidecar))
    for value, context in (
        (sidecar.operation_id, "operation_id"),
        (sidecar.backend, "backend"),
        (sidecar.stage, "stage"),
    ):
        _identifier(value, context)
    compatibility = _string(
        sidecar.compatibility_fingerprint,
        "compatibility_fingerprint",
    )
    if _COMPATIBILITY.fullmatch(compatibility) is None:
        _fail("compatibility_fingerprint is invalid")


def _resume_identity(sidecar: ProgressSidecar) -> ResumeIdentity:
    return ResumeIdentity(
        algorithm_id=sidecar.algorithm_id,
        algorithm_version=sidecar.algorithm_version,
        repository_revision=sidecar.repository_revision,
        schema=sidecar.schema,
        seed=sidecar.seed,
        source_sha256=sidecar.source_sha256,
        target_profile_fingerprint=sidecar.target_profile_fingerprint,
        target_profile_id=sidecar.target_profile_id,
        toolchain_fingerprint=sidecar.toolchain_fingerprint,
    )


def _validate_identity(sidecar: ProgressSidecar) -> None:
    _validate_identity_formats(sidecar)
    expected = resume_compatibility_fingerprint(_resume_identity(sidecar))
    if sidecar.compatibility_fingerprint != expected:
        _fail("resume compatibility fingerprint mismatch")


def _validate_checkpoint_path(sidecar: ProgressSidecar) -> None:
    if sidecar.checkpoint_path is None:
        return
    expected = str(
        checkpoint_path(sidecar.output_path, sidecar.checkpoint_sequence)
    )
    if sidecar.checkpoint_path != expected:
        _fail("checkpoint_path does not match output and sequence")


def _validate_partial_path(sidecar: ProgressSidecar) -> None:
    if sidecar.partial_path is None:
        return
    expected = str(
        partial_path(sidecar.output_path, sidecar.checkpoint_sequence)
    )
    if sidecar.partial_path != expected:
        _fail("partial_path does not match output and sequence")


def _validate_paths(sidecar: ProgressSidecar) -> None:
    if sidecar.progress_path != str(progress_path(sidecar.output_path)):
        _fail("progress_path does not match output_path")
    _validate_checkpoint_path(sidecar)
    _validate_partial_path(sidecar)


def _validate_numeric_domain(sidecar: ProgressSidecar) -> None:
    required = (
        (sidecar.active_elapsed_ns, "active_elapsed_ns"),
        (sidecar.checkpoint_elapsed_ns, "checkpoint_elapsed_ns"),
        (sidecar.checkpoint_sequence, "checkpoint_sequence"),
        (sidecar.paused_elapsed_ns, "paused_elapsed_ns"),
        (sidecar.serialization_elapsed_ns, "serialization_elapsed_ns"),
        (sidecar.units_completed, "units_completed"),
        (sidecar.verification_elapsed_ns, "verification_elapsed_ns"),
        (sidecar.wall_elapsed_ns, "wall_elapsed_ns"),
    )
    optional = (
        (sidecar.partial_bytes, "partial_bytes"),
        (sidecar.seed, "seed"),
        (sidecar.units_total, "units_total"),
    )
    for value, context in required:
        _ = _nonnegative_integer(value, context)
    for value, context in optional:
        if value is not None:
            _ = _nonnegative_integer(value, context)


def _validate_units(sidecar: ProgressSidecar) -> None:
    if (
        sidecar.units_total is not None
        and sidecar.units_completed > sidecar.units_total
    ):
        _fail("units_completed exceeds units_total")


def _validate_elapsed_times(sidecar: ProgressSidecar) -> None:
    phases = (
        sidecar.active_elapsed_ns,
        sidecar.checkpoint_elapsed_ns,
        sidecar.paused_elapsed_ns,
        sidecar.serialization_elapsed_ns,
        sidecar.verification_elapsed_ns,
    )
    if sum(phases) != sidecar.wall_elapsed_ns:
        _fail("elapsed phases do not exactly partition wall_elapsed_ns")


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


def _validate_direct_text_fields(sidecar: ProgressSidecar) -> None:
    required = (
        (sidecar.algorithm_id, "algorithm_id"),
        (sidecar.algorithm_version, "algorithm_version"),
        (sidecar.backend, "backend"),
        (sidecar.compatibility_fingerprint, "compatibility_fingerprint"),
        (sidecar.operation_id, "operation_id"),
        (sidecar.output_path, "output_path"),
        (sidecar.progress_path, "progress_path"),
        (sidecar.repository_revision, "repository_revision"),
        (sidecar.schema, "schema"),
        (sidecar.source_path, "source_path"),
        (sidecar.source_sha256, "source_sha256"),
        (sidecar.stage, "stage"),
        (sidecar.started_at, "started_at"),
        (sidecar.target_profile_fingerprint, "target_profile_fingerprint"),
        (sidecar.target_profile_id, "target_profile_id"),
        (sidecar.toolchain_fingerprint, "toolchain_fingerprint"),
        (sidecar.updated_at, "updated_at"),
    )
    optional = (
        (sidecar.checkpoint_path, "checkpoint_path"),
        (sidecar.checkpoint_sha256, "checkpoint_sha256"),
        (sidecar.completed_at, "completed_at"),
        (sidecar.device, "device"),
        (sidecar.diagnostic_code, "diagnostic_code"),
        (sidecar.diagnostic_message, "diagnostic_message"),
        (sidecar.partial_path, "partial_path"),
        (sidecar.partial_sha256, "partial_sha256"),
    )
    for value, context in required:
        _ = _string(value, context)
    for value, context in optional:
        if value is not None:
            _ = _string(value, context)


def validate(sidecar: ProgressSidecar) -> ProgressSidecar:
    """Validate one complete sidecar fail-closed.

    Returns:
        The same immutable sidecar after all invariants pass.

    """
    if type(sidecar) is not ProgressSidecar:
        _fail("sidecar must use the exact immutable type")
    _validate_direct_text_fields(sidecar)
    if type(sidecar.status) is not ProgressStatus:
        _fail("status must use the exact enum type")
    if sidecar.schema != SCHEMA_ID:
        _fail(f"unsupported progress schema: {sidecar.schema}")
    _validate_numeric_domain(sidecar)
    _validate_identity(sidecar)
    _validate_paths(sidecar)
    _validate_timing(sidecar)
    _validate_checkpoint(sidecar)
    _validate_partial(sidecar)
    _validate_diagnostic(sidecar)
    return sidecar


_ALLOWED_TRANSITIONS: Final = {
    ProgressStatus.QUEUED: frozenset({
        ProgressStatus.CANCELLED,
        ProgressStatus.FAILED,
        ProgressStatus.QUEUED,
        ProgressStatus.RUNNING,
    }),
    ProgressStatus.RUNNING: frozenset({
        ProgressStatus.CANCELLED,
        ProgressStatus.CHECKPOINTED,
        ProgressStatus.COMPLETED,
        ProgressStatus.FAILED,
        ProgressStatus.RUNNING,
    }),
    ProgressStatus.CHECKPOINTED: frozenset({
        ProgressStatus.CANCELLED,
        ProgressStatus.CHECKPOINTED,
        ProgressStatus.COMPLETED,
        ProgressStatus.FAILED,
        ProgressStatus.RUNNING,
    }),
}


def _validate_total_transition(
    previous: ProgressSidecar,
    current: ProgressSidecar,
) -> None:
    if previous.units_total is not None and (
        current.units_total != previous.units_total
    ):
        _fail("known units_total changed across progress transition")


def _validate_same_generation(
    previous: ProgressSidecar,
    current: ProgressSidecar,
) -> None:
    if current.checkpoint_sequence != previous.checkpoint_sequence:
        return
    previous_checkpoint = (
        previous.checkpoint_path,
        previous.checkpoint_sha256,
    )
    current_checkpoint = (
        current.checkpoint_path,
        current.checkpoint_sha256,
    )
    if current_checkpoint != previous_checkpoint:
        _fail("checkpoint generation changed without sequence advance")
    previous_partial = (
        previous.partial_path,
        previous.partial_bytes,
        previous.partial_sha256,
    )
    current_partial = (
        current.partial_path,
        current.partial_bytes,
        current.partial_sha256,
    )
    cleared_for_completion = (
        current.status is ProgressStatus.COMPLETED
        and current_partial == (None, None, None)
    )
    if current_partial != previous_partial and not cleared_for_completion:
        _fail("partial generation changed without sequence advance")


def _validate_checkpoint_transition(
    previous: ProgressSidecar,
    current: ProgressSidecar,
) -> None:
    if current.checkpoint_sequence < previous.checkpoint_sequence:
        _fail("checkpoint sequence moved backward")
    if current.checkpoint_sequence > previous.checkpoint_sequence + 1:
        _fail("checkpoint sequence skipped a generation")
    _validate_same_generation(previous, current)


def _validate_elapsed_transition(
    previous: ProgressSidecar,
    current: ProgressSidecar,
) -> None:
    fields_to_check = (
        "active_elapsed_ns",
        "checkpoint_elapsed_ns",
        "paused_elapsed_ns",
        "serialization_elapsed_ns",
        "units_completed",
        "verification_elapsed_ns",
        "wall_elapsed_ns",
    )
    for field_name in fields_to_check:
        if getattr(current, field_name) < getattr(previous, field_name):
            _fail(f"{field_name} moved backward")


def validate_transition(
    previous: ProgressSidecar,
    current: ProgressSidecar,
) -> ProgressSidecar:
    """Validate one monotonic update of an existing operation.

    Returns:
        The current sidecar after identity and transition checks pass.

    """
    old = validate(previous)
    new = validate(current)
    stable_fields = (
        "compatibility_fingerprint",
        "operation_id",
        "output_path",
        "progress_path",
        "repository_revision",
        "source_path",
        "started_at",
    )
    for field_name in stable_fields:
        if getattr(new, field_name) != getattr(old, field_name):
            _fail(f"{field_name} changed across progress transition")
    allowed = _ALLOWED_TRANSITIONS.get(old.status, frozenset())
    if new.status not in allowed:
        transition = f"{old.status.value}->{new.status.value}"
        _fail(f"invalid progress transition: {transition}")
    if _timestamp(new.updated_at, "updated_at") < _timestamp(
        old.updated_at,
        "previous.updated_at",
    ):
        _fail("updated_at moved backward")
    _validate_total_transition(old, new)
    _validate_checkpoint_transition(old, new)
    _validate_elapsed_transition(old, new)
    return new


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

    Raises:
        ProgressSidecarError: If JSON or sidecar invariants are invalid.

    """
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except ProgressSidecarError:
        raise
    except ValueError as error:
        _fail(f"invalid progress JSON: {error}")
    return validate(_from_document(_mapping(parsed, "progress sidecar")))


def read(path: Path) -> ProgressSidecar:
    """Read and validate one sidecar file.

    Returns:
        Immutable validated progress sidecar.

    """
    admitted_path = _read_path(path)
    _reject_path_redirect(admitted_path, "progress sidecar")
    try:
        text = admitted_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        _fail(f"invalid progress UTF-8: {error}")
    except OSError as error:
        _fail(f"progress sidecar is unavailable: {error}")
    return loads(text)


def _flush_parent(path: Path, *, platform: str = os.name) -> None:
    if platform == WINDOWS_PLATFORM:
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _writer_lock_path(destination: Path) -> Path:
    return Path(f"{destination}.lock")


def _acquire_writer_lock(stream: _LockStream) -> Callable[[], None]:
    file_descriptor = stream.fileno()
    _ = stream.seek(0)
    if os.name == WINDOWS_PLATFORM:
        module = cast(
            "_WindowsLockModule",
            cast("object", import_module("msvcrt")),
        )
        module.locking(file_descriptor, module.LK_LOCK, 1)

        def release() -> None:
            _ = stream.seek(0)
            module.locking(file_descriptor, module.LK_UNLCK, 1)

        return release
    module = cast("_PosixLockModule", cast("object", import_module("fcntl")))
    module.flock(file_descriptor, module.LOCK_EX)

    def release() -> None:
        module.flock(file_descriptor, module.LOCK_UN)

    return release


def _open_writer_lock_stream(lock_path: Path) -> _LockStream:
    try:
        _reject_path_redirect(lock_path.parent, "progress writer lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        _reject_path_redirect(lock_path, "progress writer lock")
        return lock_path.open("a+b")
    except OSError as error:
        _fail(f"progress writer lock cannot be opened: {error}")


def _release_writer_lock(release: Callable[[], None]) -> None:
    try:
        release()
    except OSError as error:
        _fail(f"progress writer lock cannot be released: {error}")


def _close_writer_lock_stream(stream: _LockStream) -> None:
    try:
        stream.close()
    except OSError as error:
        _fail(f"progress writer lock cannot be closed: {error}")


@contextmanager
def _writer_lock(destination: Path) -> Generator[None]:
    stream = _open_writer_lock_stream(_writer_lock_path(destination))
    try:
        try:
            release = _acquire_writer_lock(stream)
        except OSError as error:
            _fail(f"progress writer lock cannot be acquired: {error}")
        try:
            yield
        finally:
            _release_writer_lock(release)
    finally:
        _close_writer_lock_stream(stream)


def _write_atomic_bytes(destination: Path, payload: bytes) -> Path:
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


def _path_redirects(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _redirecting_component(path: Path) -> Path | None:
    candidate = path
    while True:
        if _path_redirects(candidate):
            return candidate
        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent


def _reject_path_redirect(path: Path, context: str) -> None:
    redirect = _redirecting_component(path)
    if redirect is not None:
        _fail(f"{context} path is linked: {redirect}")


def _publish_no_replace(
    temporary: Path,
    destination: Path,
    *,
    platform: str = os.name,
) -> None:
    if platform == WINDOWS_PLATFORM:
        _ = temporary.rename(destination)
    else:
        os.link(temporary, destination)


def _write_payload_descriptor(descriptor: int, payload: bytes) -> None:
    with os.fdopen(descriptor, "wb") as stream:
        _ = stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _admit_existing_immutable(destination: Path, payload: bytes) -> None:
    _reject_path_redirect(destination, "immutable progress payload")
    try:
        existing = destination.read_bytes()
    except OSError as error:
        _fail(f"immutable progress payload publication failed: {error}")
    if existing != payload:
        _fail(f"immutable progress payload already differs: {destination}")


def _publish_immutable_payload(
    temporary: Path,
    destination: Path,
    payload: bytes,
    *,
    platform: str,
) -> None:
    try:
        _publish_no_replace(temporary, destination, platform=platform)
    except FileExistsError:
        _admit_existing_immutable(destination, payload)
    except OSError as error:
        _fail(f"immutable progress payload publication failed: {error}")


def _write_immutable(
    destination: Path,
    payload: bytes,
    *,
    platform: str = os.name,
) -> Path:
    _reject_path_redirect(destination.parent, "immutable progress payload")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _reject_path_redirect(destination, "immutable progress payload")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        _write_payload_descriptor(descriptor, payload)
        _publish_immutable_payload(
            temporary,
            destination,
            payload,
            platform=platform,
        )
        _flush_parent(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _sha256_digest(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class _PayloadReference:
    """Expected sidecar metadata for one immutable payload."""

    byte_count: int | None
    context: str
    path: str | None
    sha256: str | None


def _validate_payload_integrity(
    payload: bytes, reference: _PayloadReference
) -> None:
    if _sha256_digest(payload) != reference.sha256:
        _fail(f"{reference.context} bytes do not match sidecar hash")
    if (
        reference.byte_count is not None
        and len(payload) != reference.byte_count
    ):
        _fail(f"{reference.context} byte count does not match sidecar")


def _validate_payload(
    payload: bytes | None,
    reference: _PayloadReference,
) -> bytes | None:
    present = payload is not None
    if present != (reference.path is not None and reference.sha256 is not None):
        _fail(f"{reference.context} bytes do not match sidecar presence")
    if payload is None:
        return None
    if type(payload) is not bytes:
        _fail(f"{reference.context} payload must use exact bytes")
    _validate_payload_integrity(payload, reference)
    return payload


def _read_payload(path: Path, context: str) -> bytes:
    _reject_path_redirect(path, f"{context} payload")
    try:
        return path.read_bytes()
    except OSError as error:
        _fail(f"{context} payload is unavailable: {error}")


def _validate_referenced_generation(sidecar: ProgressSidecar) -> None:
    if sidecar.checkpoint_path is None:
        return
    checkpoint = _read_payload(Path(sidecar.checkpoint_path), "checkpoint")
    _ = _validate_payload(
        checkpoint,
        _PayloadReference(
            byte_count=None,
            context="checkpoint",
            path=sidecar.checkpoint_path,
            sha256=sidecar.checkpoint_sha256,
        ),
    )
    if sidecar.partial_path is None:
        return
    partial = _read_payload(Path(sidecar.partial_path), "partial")
    _ = _validate_payload(
        partial,
        _PayloadReference(
            byte_count=sidecar.partial_bytes,
            context="partial",
            path=sidecar.partial_path,
            sha256=sidecar.partial_sha256,
        ),
    )


def write_atomic(sidecar: ProgressSidecar) -> Path:
    """Atomically replace one sidecar after transition and payload validation.

    Returns:
        Canonical progress path after flush and atomic replacement.

    """
    validated = validate(sidecar)
    destination = Path(validated.progress_path)
    _reject_path_redirect(destination, "progress sidecar")
    with _writer_lock(destination):
        _reject_path_redirect(destination, "progress sidecar")
        if destination.exists():
            _ = validate_transition(read(destination), validated)
        _validate_referenced_generation(validated)
        try:
            return _write_atomic_bytes(destination, encode(validated))
        except OSError as error:
            _fail(f"progress sidecar publication failed: {error}")


def _preflight_generation_destination(sidecar: ProgressSidecar) -> None:
    destination = Path(sidecar.progress_path)
    _reject_path_redirect(destination, "progress sidecar")
    if destination.exists():
        _ = validate_transition(read(destination), sidecar)


def _validated_generation_payloads(
    sidecar: ProgressSidecar,
    checkpoint: bytes,
    partial: bytes | None,
) -> tuple[bytes, bytes | None]:
    checkpoint_payload = _validate_payload(
        checkpoint,
        _PayloadReference(
            byte_count=None,
            context="checkpoint",
            path=sidecar.checkpoint_path,
            sha256=sidecar.checkpoint_sha256,
        ),
    )
    partial_payload = _validate_payload(
        partial,
        _PayloadReference(
            byte_count=sidecar.partial_bytes,
            context="partial",
            path=sidecar.partial_path,
            sha256=sidecar.partial_sha256,
        ),
    )
    if checkpoint_payload is None or sidecar.checkpoint_path is None:
        _fail("checkpoint generation requires checkpoint bytes")
    return checkpoint_payload, partial_payload


def _publish_generation_payloads(
    sidecar: ProgressSidecar,
    checkpoint: bytes,
    partial: bytes | None,
) -> None:
    checkpoint_path_value = sidecar.checkpoint_path
    if checkpoint_path_value is None:
        _fail("checkpoint generation requires checkpoint path")
    try:
        _ = _write_immutable(Path(checkpoint_path_value), checkpoint)
        if partial is not None and sidecar.partial_path is not None:
            _ = _write_immutable(Path(sidecar.partial_path), partial)
    except OSError as error:
        _fail(f"immutable progress payload publication failed: {error}")


def write_checkpoint_generation(
    sidecar: ProgressSidecar,
    checkpoint: bytes,
    partial: bytes | None = None,
) -> Path:
    """Publish immutable generation payloads and then the sidecar pointer.

    Returns:
        Canonical progress path after all durable writes complete.

    """
    validated = validate(sidecar)
    _preflight_generation_destination(validated)
    checkpoint_payload, partial_payload = _validated_generation_payloads(
        validated,
        checkpoint,
        partial,
    )
    _publish_generation_payloads(validated, checkpoint_payload, partial_payload)
    return write_atomic(validated)


def read_checkpoint_generation(
    sidecar: ProgressSidecar,
) -> tuple[bytes, bytes | None]:
    """Read and verify one sidecar-referenced immutable generation.

    Returns:
        Checkpoint bytes and optional partial-output bytes.

    """
    validated = validate(sidecar)
    if validated.checkpoint_path is None:
        _fail("sidecar does not name a checkpoint generation")
    checkpoint = _read_payload(
        Path(validated.checkpoint_path),
        "checkpoint",
    )
    _ = _validate_payload(
        checkpoint,
        _PayloadReference(
            byte_count=None,
            context="checkpoint",
            path=validated.checkpoint_path,
            sha256=validated.checkpoint_sha256,
        ),
    )
    partial = None
    if validated.partial_path is not None:
        partial = _read_payload(
            Path(validated.partial_path),
            "partial",
        )
        _ = _validate_payload(
            partial,
            _PayloadReference(
                byte_count=validated.partial_bytes,
                context="partial",
                path=validated.partial_path,
                sha256=validated.partial_sha256,
            ),
        )
    return checkpoint, partial


def render_summary(sidecar: ProgressSidecar) -> str:
    """Render one exact operator-facing progress and timing summary.

    Returns:
        One newline-terminated stable key/value record.

    """
    value = validate(sidecar)
    total = "unknown" if value.units_total is None else str(value.units_total)
    checkpoint = value.checkpoint_path or "none"
    partial = value.partial_path or "none"
    fields = (
        f"status={value.status.value}",
        f"stage={value.stage}",
        f"units={value.units_completed}/{total}",
        f"active_ns={value.active_elapsed_ns}",
        f"wall_ns={value.wall_elapsed_ns}",
        f"paused_ns={value.paused_elapsed_ns}",
        f"verification_ns={value.verification_elapsed_ns}",
        f"serialization_ns={value.serialization_elapsed_ns}",
        f"checkpoint_ns={value.checkpoint_elapsed_ns}",
        f"progress={value.progress_path}",
        f"checkpoint={checkpoint}",
        f"partial={partial}",
    )
    return " ".join(fields) + "\n"


def _inspect_path(path: Path) -> int:
    try:
        sidecar = read(path)
    except (OSError, ProgressSidecarError) as error:
        message = f"progress sidecar inspection failed: {error}\n"
        _ = sys.stderr.write(message)
        return 1
    _ = sys.stdout.write(render_summary(sidecar))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Inspect one progress sidecar from the command line.

    Returns:
        Process-style status code: zero on valid inspection, nonzero otherwise.

    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    usage = "usage: progress_sidecar.py PROGRESS.json\n"
    if arguments in (["-h"], ["--help"]):
        _ = sys.stdout.write(usage)
        status = 0
    elif len(arguments) != 1:
        _ = sys.stderr.write(usage)
        status = 2
    else:
        status = _inspect_path(Path(arguments[0]))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
