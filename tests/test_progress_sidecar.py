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
#   - Progress-sidecar schema, identity, transition, and persistence
#     regressions.
# - Must-Not:
#   - Claim compiler or accelerator checkpoint integration exists.
# - Allows:
#   - Inputs: temporary output paths and immutable sidecar fixtures.
#   - Outputs: exact acceptance/rejection, timing-summary, and persistence
#     assertions.
#   - Side effects: temporary generation writes and captured inspector I/O.
# - Split-When:
#   - Product checkpoint integration gains independent crash fixtures.
# - Merge-When:
#   - Another suite owns this exact sidecar reference boundary.
# - Summary:
#   - Adversarial tests for `malbolge-progress-v1`.
# - Description:
#   - Exercises canonical identity and fail-closed persistence invariants.
# - Usage:
#   - Runs with the repository Python validation suite.
# - Defaults:
#   - Invalid, stale, overwritten, or torn state is rejected before admission.
#

"""Progress-sidecar reference contract regressions."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import time
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts import progress_sidecar as progress

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

SOURCE_HASH = "sha256:" + ("1" * 64)
TOOLCHAIN_HASH = "sha256:" + ("2" * 64)
PROFILE_HASH = "malbolge-profile-v1:sha256:" + ("3" * 64)
REPOSITORY_REVISION = "a" * 40
STARTED = "2026-08-06T14:00:00Z"
UPDATED = "2026-08-06T14:00:01Z"
COMPLETED = "2026-08-06T14:00:02Z"
ERROR = progress.ProgressSidecarError
SCHEMA_FIELD = '"schema":"malbolge-progress-v1"'
PROGRESS_NAME = "program.malbolge.progress.json"
CHECKPOINT_NAME = "program.malbolge.checkpoint.00000000000000000001"
PARTIAL_NAME = "program.malbolge.partial.00000000000000000001"
SUMMARY_FIELDS = (
    "status=checkpointed",
    "stage=candidate-search",
    "units=14/unknown",
    "active_ns=700",
    "wall_ns=870",
    "paused_ns=100",
    "verification_ns=30",
    "serialization_ns=10",
    "checkpoint_ns=30",
)
INSPECTION_FAILED_PREFIX = "progress sidecar inspection failed:"
WINDOWS_PAYLOAD = b"windows-payload"
POSIX_PAYLOAD = b"posix-payload"
EMPTY_PAYLOAD = b""
CRASH_EXIT = 73
AFTER_CHECKPOINT = "after-checkpoint"
BEFORE_SIDECAR = "before-sidecar"
CRASH_BOUNDARIES = (AFTER_CHECKPOINT, BEFORE_SIDECAR)
CHECKPOINT_BEFORE_CRASH = b"checkpoint-before-crash"
PARTIAL_BEFORE_CRASH = b"partial-before-crash"
CHECKPOINT_AFTER_CRASH = b"checkpoint-after-crash"
PARTIAL_AFTER_CRASH = b"partial-after-crash"
LOCK_ACQUIRED = "acquired"
LOCK_CRASH_EXIT = 74
WRITER_LOCK_SCRIPT = """
from pathlib import Path
import os
import sys
import time
from scripts import progress_sidecar as progress

destination = Path(sys.argv[1])
role = sys.argv[2]
held = Path(sys.argv[3])
attempted = Path(sys.argv[4])
release = Path(sys.argv[5])
acquired = Path(sys.argv[6])
writer_lock = vars(progress)["_writer_lock"]
if role == "holder":
    with writer_lock(destination):
        held.write_text("held", encoding="utf-8")
        deadline = time.monotonic() + 20.0
        while not release.exists():
            if time.monotonic() >= deadline:
                raise SystemExit(91)
            time.sleep(0.01)
elif role == "crasher":
    with writer_lock(destination):
        held.write_text("held", encoding="utf-8")
        os._exit(74)
elif role == "contender":
    attempted.write_text("attempted", encoding="utf-8")
    with writer_lock(destination):
        acquired.write_text("acquired", encoding="utf-8")
else:
    raise SystemExit(92)
""".strip()

STALE_WRITER_EXIT = 75
MOVED_BACKWARD = b"moved backward"
STALE_WRITER_SCRIPT = """
from pathlib import Path
import sys
from scripts import progress_sidecar as progress

candidate = progress.read(Path(sys.argv[1]))
attempted = Path(sys.argv[2])
attempted.write_text("attempted", encoding="utf-8")
try:
    progress.write_atomic(candidate)
except progress.ProgressSidecarError as error:
    sys.stderr.write(str(error))
    raise SystemExit(75) from error
raise SystemExit(0)
""".strip()

CRASH_SCRIPT = """
from pathlib import Path
import os
import sys
from scripts import progress_sidecar as progress

sidecar = progress.read(Path(sys.argv[1]))
checkpoint = Path(sys.argv[2]).read_bytes()
partial = Path(sys.argv[3]).read_bytes()
exit_code = int(sys.argv[4])
boundary = sys.argv[5]
original_write_immutable = progress._write_immutable
publication_count = 0

def write_then_maybe_crash(destination, payload):
    global publication_count
    result = original_write_immutable(destination, payload)
    publication_count += 1
    if boundary == "after-checkpoint" and publication_count == 1:
        os._exit(exit_code)
    return result

def crash_before_sidecar(_sidecar):
    os._exit(exit_code)

progress._write_immutable = write_then_maybe_crash
if boundary == "before-sidecar":
    progress.write_atomic = crash_before_sidecar
progress.write_checkpoint_generation(sidecar, checkpoint, partial)
raise AssertionError("configured crash boundary was not reached")
""".strip()


def _digest(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


class WriterLock(Protocol):
    """Typed view of the internal cross-process writer lock."""

    def __call__(self, destination: Path) -> AbstractContextManager[None]:
        """Acquire one destination-scoped writer lock."""
        ...


class AtomicByteWriter(Protocol):
    """Typed view of the internal atomic mutable-byte publisher."""

    def __call__(self, destination: Path, payload: bytes) -> Path:
        """Replace one mutable byte record atomically."""
        ...


class ImmutableWriter(Protocol):
    """Typed view of the internal immutable publication primitive."""

    def __call__(
        self,
        destination: Path,
        payload: bytes,
        *,
        platform: str,
    ) -> Path:
        """Publish one immutable payload without replacement."""
        ...


@dataclass(frozen=True, slots=True)
class CrashFixture:
    """Two committed generations plus child-process input artifacts."""

    checkpoint_input: Path
    checkpoint_one: bytes
    checkpoint_two: bytes
    destination: Path
    first: progress.ProgressSidecar
    partial_input: Path
    partial_one: bytes
    partial_two: bytes
    second: progress.ProgressSidecar
    sidecar_input: Path


@dataclass(slots=True)
class SequenceClock:
    """Deterministic monotonic-clock fixture."""

    values: list[int]

    def __call__(self) -> int:
        """Return the next deterministic clock sample.

        Returns:
            Next monotonic nanosecond fixture value.

        """
        assert self.values
        return self.values.pop(0)


def _sidecar(
    tmp_path: Path,
    *,
    status: progress.ProgressStatus = progress.ProgressStatus.RUNNING,
) -> progress.ProgressSidecar:
    output = tmp_path / "program.malbolge"
    identity = progress.ResumeIdentity(
        algorithm_id="search.enumerative",
        algorithm_version="1",
        repository_revision=REPOSITORY_REVISION,
        schema=progress.SCHEMA_ID,
        seed=7,
        source_sha256=SOURCE_HASH,
        target_profile_fingerprint=PROFILE_HASH,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=TOOLCHAIN_HASH,
    )
    terminal = status in {
        progress.ProgressStatus.CANCELLED,
        progress.ProgressStatus.COMPLETED,
        progress.ProgressStatus.FAILED,
    }
    failed = status in {
        progress.ProgressStatus.CANCELLED,
        progress.ProgressStatus.FAILED,
    }
    return progress.ProgressSidecar(
        active_elapsed_ns=600,
        algorithm_id="search.enumerative",
        algorithm_version="1",
        backend="cpu",
        checkpoint_elapsed_ns=20,
        checkpoint_path=None,
        checkpoint_sequence=0,
        checkpoint_sha256=None,
        compatibility_fingerprint=(
            progress.resume_compatibility_fingerprint(identity)
        ),
        completed_at=COMPLETED if terminal else None,
        device=None,
        diagnostic_code="MALBOLGE-JOB-001" if failed else None,
        diagnostic_message="cancelled" if failed else None,
        operation_id="compile-0001",
        output_path=str(output),
        partial_bytes=None,
        partial_path=None,
        partial_sha256=None,
        paused_elapsed_ns=100,
        progress_path=str(progress.progress_path(output)),
        repository_revision=REPOSITORY_REVISION,
        schema=progress.SCHEMA_ID,
        seed=7,
        serialization_elapsed_ns=10,
        source_path="input.c",
        source_sha256=SOURCE_HASH,
        stage="candidate-search",
        started_at=STARTED,
        status=status,
        target_profile_fingerprint=PROFILE_HASH,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=TOOLCHAIN_HASH,
        units_completed=13,
        units_total=None,
        updated_at=UPDATED,
        verification_elapsed_ns=30,
        wall_elapsed_ns=760,
    )


def _checkpointed(
    sidecar: progress.ProgressSidecar,
    *,
    sequence: int = 1,
    checkpoint: bytes = b"checkpoint-state-v1",
    partial: bytes | None = b"partial-malbolge-v1",
) -> progress.ProgressSidecar:
    return replace(
        sidecar,
        active_elapsed_ns=sidecar.active_elapsed_ns + 100,
        checkpoint_elapsed_ns=sidecar.checkpoint_elapsed_ns + 10,
        checkpoint_path=str(
            progress.checkpoint_path(sidecar.output_path, sequence)
        ),
        checkpoint_sequence=sequence,
        checkpoint_sha256=_digest(checkpoint),
        partial_bytes=len(partial) if partial is not None else None,
        partial_path=(
            str(progress.partial_path(sidecar.output_path, sequence))
            if partial is not None
            else None
        ),
        partial_sha256=_digest(partial) if partial is not None else None,
        status=progress.ProgressStatus.CHECKPOINTED,
        units_completed=sidecar.units_completed + 1,
        updated_at="2026-08-06T14:00:02Z",
        wall_elapsed_ns=sidecar.wall_elapsed_ns + 110,
    )


def test_resume_fingerprint_rejects_invalid_direct_identity() -> None:
    """Fingerprinting validates resume identity before hashing."""
    identity = progress.ResumeIdentity(
        algorithm_id="search.enumerative",
        algorithm_version="1",
        repository_revision=REPOSITORY_REVISION,
        schema=progress.SCHEMA_ID,
        seed=7,
        source_sha256=SOURCE_HASH,
        target_profile_fingerprint=PROFILE_HASH,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=TOOLCHAIN_HASH,
    )
    boolean_alias = bool(1)
    invalid = (
        replace(identity, algorithm_id=cast("str", object())),
        replace(identity, repository_revision="not-a-revision"),
        replace(identity, schema="malbolge-progress-v2"),
        replace(identity, seed=cast("int", cast("object", boolean_alias))),
        replace(identity, source_sha256="sha256:bad"),
        replace(identity, target_profile_fingerprint="bad-profile"),
    )
    for candidate in invalid:
        with pytest.raises(ERROR):
            _ = progress.resume_compatibility_fingerprint(candidate)
    with pytest.raises(ERROR, match="exact immutable type"):
        _ = progress.resume_compatibility_fingerprint(
            cast("progress.ResumeIdentity", object())
        )


def test_direct_sidecar_foreign_fields_fail_typed(tmp_path: Path) -> None:
    """Direct dataclass misuse never leaks Python type exceptions."""
    sidecar = _sidecar(tmp_path)
    for field_name in (
        "algorithm_id",
        "compatibility_fingerprint",
        "diagnostic_message",
        "repository_revision",
        "started_at",
        "status",
        "target_profile_fingerprint",
    ):
        candidate = replace(sidecar, **{field_name: object()})
        with pytest.raises(ERROR):
            _ = progress.validate(candidate)
    with pytest.raises(ERROR, match="exact immutable type"):
        _ = progress.validate(cast("progress.ProgressSidecar", object()))


def test_paths_and_resume_identity_are_backend_neutral(tmp_path: Path) -> None:
    """Generation paths are predictable and devices are not resume identity."""
    sidecar = _sidecar(tmp_path)
    output = tmp_path / "program.malbolge"
    assert progress.progress_path(output).name == PROGRESS_NAME
    assert progress.checkpoint_path(output, 1).name == CHECKPOINT_NAME
    assert progress.partial_path(output, 1).name == PARTIAL_NAME
    with pytest.raises(ERROR, match="positive integer"):
        _ = progress.checkpoint_path(output, 0)
    with pytest.raises(ERROR, match="positive integer"):
        _ = progress.partial_path(output, -1)
    with pytest.raises(ERROR, match="positive integer"):
        _ = progress.checkpoint_path(output, sequence=True)
    with pytest.raises(ERROR, match="positive integer"):
        _ = progress.partial_path(output, sequence=True)
    with pytest.raises(ERROR, match="output path"):
        _ = progress.progress_path(cast("str | Path", object()))
    with pytest.raises(ERROR, match="output path"):
        _ = progress.checkpoint_path(cast("str | Path", object()), 1)
    with pytest.raises(ERROR, match="output path"):
        _ = progress.partial_path(cast("str | Path", object()), 1)
    assert sidecar.compatibility_fingerprint == (
        progress.resume_compatibility_fingerprint(
            progress.ResumeIdentity(
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
        )
    )


def test_read_rejects_foreign_path_type() -> None:
    """Direct read misuse remains inside the progress-sidecar error boundary."""
    with pytest.raises(ERROR, match="read path must use pathlib Path"):
        _ = progress.read(cast("Path", cast("object", "not-a-path-object")))


def test_read_wraps_missing_storage_as_sidecar_error(tmp_path: Path) -> None:
    """Direct reads keep missing storage inside the stable error boundary."""
    missing = tmp_path / PROGRESS_NAME
    with pytest.raises(ERROR, match="progress sidecar is unavailable"):
        _ = progress.read(missing)


def test_read_rejects_linked_progress_path(tmp_path: Path) -> None:
    """Reading a sidecar never follows a redirected canonical leaf."""
    sidecar = _sidecar(tmp_path)
    destination = Path(sidecar.progress_path)
    foreign = tmp_path / "foreign-readable-progress.json"
    payload = progress.encode(sidecar)
    _ = foreign.write_bytes(payload)
    try:
        destination.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    with pytest.raises(ERROR, match="progress sidecar path is linked"):
        _ = progress.read(destination)
    assert destination.is_symlink()
    assert foreign.read_bytes() == payload


def _linked_directory(tmp_path: Path, name: str) -> tuple[Path, Path]:
    target = tmp_path / f"{name}-target"
    target.mkdir()
    linked = tmp_path / name
    try:
        linked.symlink_to(target.resolve(), target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable on this host: {error}")
    return linked, target


def test_read_rejects_linked_progress_parent(tmp_path: Path) -> None:
    """Reading a sidecar never follows a redirected parent directory."""
    linked, target = _linked_directory(tmp_path, "linked-read-parent")
    sidecar = _sidecar(tmp_path / "read-fixture")
    payload = progress.encode(sidecar)
    real = target / PROGRESS_NAME
    _ = real.write_bytes(payload)

    with pytest.raises(ERROR, match="progress sidecar path is linked"):
        _ = progress.read(linked / PROGRESS_NAME)
    assert real.read_bytes() == payload


def test_write_atomic_rejects_linked_progress_parent(tmp_path: Path) -> None:
    """Writing a sidecar never follows a redirected parent directory."""
    linked, target = _linked_directory(tmp_path, "linked-write-parent")
    base = _sidecar(tmp_path / "write-fixture")
    sidecar = replace(
        base,
        output_path=str(linked / "program.malbolge"),
        progress_path=str(linked / PROGRESS_NAME),
    )

    with pytest.raises(ERROR, match="progress sidecar path is linked"):
        _ = progress.write_atomic(sidecar)
    assert not (target / PROGRESS_NAME).exists()
    assert not (target / f"{PROGRESS_NAME}.lock").exists()


@pytest.mark.skipif(
    os.name != progress.WINDOWS_PLATFORM,
    reason="NTFS junctions are a Windows path-redirection boundary",
)
def test_write_atomic_rejects_junction_progress_parent(tmp_path: Path) -> None:
    """Writing a sidecar never follows an NTFS junction parent."""
    target = (tmp_path / "junction-target").resolve()
    target.mkdir()
    linked = (tmp_path / "junction-parent").resolve()
    command_interpreter = Path(os.environ["COMSPEC"])
    created = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(command_interpreter),
            "/d",
            "/c",
            "mklink",
            "/J",
            str(linked),
            str(target),
        ],
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    if created.returncode != 0 or not linked.is_junction():
        pytest.skip("directory junction creation is unavailable on this host")
    base = _sidecar(tmp_path / "junction-fixture")
    sidecar = replace(
        base,
        output_path=str(linked / "program.malbolge"),
        progress_path=str(linked / PROGRESS_NAME),
    )

    with pytest.raises(ERROR, match="progress sidecar path is linked"):
        _ = progress.write_atomic(sidecar)
    assert not (target / PROGRESS_NAME).exists()
    assert not (target / f"{PROGRESS_NAME}.lock").exists()


def test_write_atomic_rejects_linked_progress_path(tmp_path: Path) -> None:
    """A linked mutable sidecar leaf is preserved rather than followed."""
    sidecar = _sidecar(tmp_path)
    destination = Path(sidecar.progress_path)
    foreign = tmp_path / "foreign-progress.json"
    payload = progress.encode(sidecar)
    _ = foreign.write_bytes(payload)
    try:
        destination.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    with pytest.raises(ERROR, match="progress sidecar path is linked"):
        _ = progress.write_atomic(sidecar)
    assert destination.is_symlink()
    assert foreign.read_bytes() == payload


def test_write_atomic_rejects_linked_writer_lock(tmp_path: Path) -> None:
    """A linked lock leaf cannot redirect process serialization."""
    sidecar = _sidecar(tmp_path)
    destination = Path(sidecar.progress_path)
    lock_path = Path(f"{destination}.lock")
    foreign = tmp_path / "foreign-lock"
    _ = foreign.write_bytes(EMPTY_PAYLOAD)
    try:
        lock_path.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    with pytest.raises(ERROR, match="progress writer lock path is linked"):
        _ = progress.write_atomic(sidecar)
    assert lock_path.is_symlink()
    assert foreign.read_bytes() == EMPTY_PAYLOAD
    assert not destination.exists()


def test_writer_lock_rejects_linked_parent(tmp_path: Path) -> None:
    """The internal lock primitive rejects a redirected parent directory."""
    linked, target = _linked_directory(tmp_path, "linked-lock-parent")
    destination = linked / PROGRESS_NAME
    writer_lock = cast("WriterLock", vars(progress)["_writer_lock"])

    with (
        pytest.raises(ERROR, match="progress writer lock path is linked"),
        writer_lock(destination),
    ):
        pass
    assert not (target / f"{PROGRESS_NAME}.lock").exists()


def test_canonical_roundtrip_and_atomic_replace(tmp_path: Path) -> None:
    """Write, replace, and read one complete canonical sidecar."""
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    assert progress.read(destination) == original

    updated = replace(
        original,
        active_elapsed_ns=700,
        updated_at="2026-08-06T14:00:03Z",
        units_completed=21,
        wall_elapsed_ns=860,
    )
    assert progress.write_atomic(updated) == destination
    assert progress.read(destination) == updated
    assert not tuple(destination.parent.glob(f".{destination.name}.*.tmp"))
    document = progress.to_document(progress.read(destination))
    assert document["units_total"] is None


def test_loads_rejects_foreign_text_types() -> None:
    """Direct JSON parsing admits exact text and never decoder aliases."""
    foreign_values = (object(), b"{}", bytearray(b"{}"))
    for value in foreign_values:
        with pytest.raises(ERROR, match="JSON text must use exact string type"):
            _ = progress.loads(cast("str", value))


def test_duplicate_and_unknown_json_keys_fail_closed(tmp_path: Path) -> None:
    """JSON transport cannot overwrite authority or extend v1 silently."""
    sidecar = _sidecar(tmp_path)
    text = progress.encode(sidecar).decode("utf-8")
    duplicate_schema = f"{SCHEMA_FIELD},{SCHEMA_FIELD}"
    duplicate = text.replace(SCHEMA_FIELD, duplicate_schema, 1)
    with pytest.raises(ERROR, match="duplicate"):
        _ = progress.loads(duplicate)

    document = progress.to_document(sidecar)
    document["future_field"] = True
    with pytest.raises(ERROR, match="unknown"):
        _ = progress.loads(json.dumps(document))

    missing_revision = progress.to_document(sidecar)
    del missing_revision["repository_revision"]
    with pytest.raises(ERROR, match="missing progress keys"):
        _ = progress.loads(json.dumps(missing_revision))

    huge_integer = '{"x":' + ("9" * 5_000) + "}"
    with pytest.raises(ERROR, match="invalid progress JSON"):
        _ = progress.loads(huge_integer)


def test_impossible_timing_and_units_fail(tmp_path: Path) -> None:
    """Impossible counters or elapsed-time partitions are rejected."""
    sidecar = _sidecar(tmp_path)
    with pytest.raises(ERROR, match="units_completed"):
        _ = progress.validate(
            replace(sidecar, units_completed=2, units_total=1)
        )
    with pytest.raises(ERROR, match="exactly partition"):
        _ = progress.validate(replace(sidecar, active_elapsed_ns=601))
    with pytest.raises(ERROR, match="precedes"):
        _ = progress.validate(
            replace(sidecar, updated_at="2026-08-06T13:59:59Z")
        )
    with pytest.raises(ERROR, match="valid UTC timestamp"):
        _ = progress.validate(
            replace(sidecar, updated_at="2026-02-30T14:00:01Z")
        )


def test_direct_records_reject_negative_or_boolean_numbers(
    tmp_path: Path,
) -> None:
    """In-memory construction has the same numeric domain as JSON parsing."""
    sidecar = _sidecar(tmp_path)
    for field_name in (
        "active_elapsed_ns",
        "checkpoint_elapsed_ns",
        "checkpoint_sequence",
        "partial_bytes",
        "paused_elapsed_ns",
        "seed",
        "serialization_elapsed_ns",
        "units_completed",
        "units_total",
        "verification_elapsed_ns",
        "wall_elapsed_ns",
    ):
        with pytest.raises(ERROR, match="non-negative integer"):
            _ = progress.validate(replace(sidecar, **{field_name: -1}))
    with pytest.raises(ERROR, match="non-negative integer"):
        _ = progress.validate(replace(sidecar, units_completed=True))


def test_resume_identity_mismatch_fails(tmp_path: Path) -> None:
    """Changed source or repository identity cannot reuse a checkpoint."""
    sidecar = _sidecar(tmp_path)
    stale_source = replace(sidecar, source_sha256="sha256:" + ("9" * 64))
    with pytest.raises(ERROR, match="fingerprint mismatch"):
        _ = progress.write_atomic(stale_source)

    stale_revision = replace(sidecar, repository_revision="b" * 40)
    with pytest.raises(ERROR, match="fingerprint mismatch"):
        _ = progress.write_atomic(stale_revision)

    invalid_revision = replace(sidecar, repository_revision="short")
    with pytest.raises(ERROR, match="lowercase 40-hex Git commit"):
        _ = progress.validate(invalid_revision)
    assert not Path(sidecar.progress_path).exists()


def test_checkpoint_and_partial_members_are_atomic(tmp_path: Path) -> None:
    """Torn or sequence-inconsistent generation metadata is never admitted."""
    sidecar = _sidecar(tmp_path)
    checkpoint = str(progress.checkpoint_path(sidecar.output_path, 1))
    partial = str(progress.partial_path(sidecar.output_path, 1))
    with pytest.raises(ERROR, match="checkpoint path/hash"):
        _ = progress.validate(
            replace(
                sidecar,
                checkpoint_path=checkpoint,
                checkpoint_sequence=1,
            )
        )
    with pytest.raises(ERROR, match="partial path/bytes"):
        _ = progress.validate(
            replace(
                sidecar,
                checkpoint_sequence=1,
                checkpoint_path=checkpoint,
                checkpoint_sha256=_digest(b"checkpoint"),
                partial_bytes=7,
                partial_path=partial,
            )
        )
    with pytest.raises(ERROR, match="does not match output and sequence"):
        _ = progress.validate(
            replace(
                _checkpointed(sidecar),
                checkpoint_path=str(
                    progress.checkpoint_path(sidecar.output_path, 2)
                ),
            )
        )
    assert progress.validate(_checkpointed(sidecar)) == _checkpointed(sidecar)


def test_transition_validation_rejects_stale_or_skipped_state(
    tmp_path: Path,
) -> None:
    """Lifecycle, counters, totals, and generations advance monotonically."""
    running = _sidecar(tmp_path)
    checkpointed = _checkpointed(running)
    assert progress.validate_transition(running, checkpointed) == checkpointed

    resumed = replace(
        checkpointed,
        active_elapsed_ns=checkpointed.active_elapsed_ns + 100,
        status=progress.ProgressStatus.RUNNING,
        updated_at="2026-08-06T14:00:03Z",
        wall_elapsed_ns=checkpointed.wall_elapsed_ns + 100,
    )
    assert progress.validate_transition(checkpointed, resumed) == resumed

    with pytest.raises(ERROR, match="skipped a generation"):
        _ = progress.validate_transition(
            running,
            _checkpointed(running, sequence=2),
        )
    with pytest.raises(ERROR, match="units_completed moved backward"):
        _ = progress.validate_transition(
            checkpointed,
            replace(resumed, units_completed=running.units_completed),
        )
    known_total = replace(running, units_total=100)
    with pytest.raises(ERROR, match="known units_total changed"):
        _ = progress.validate_transition(
            known_total,
            replace(
                known_total,
                units_total=101,
                updated_at="2026-08-06T14:00:03Z",
            ),
        )
    completed = replace(
        resumed,
        completed_at="2026-08-06T14:00:04Z",
        partial_bytes=None,
        partial_path=None,
        partial_sha256=None,
        status=progress.ProgressStatus.COMPLETED,
        updated_at="2026-08-06T14:00:04Z",
    )
    assert progress.validate_transition(resumed, completed) == completed
    with pytest.raises(ERROR, match="invalid progress transition"):
        _ = progress.validate_transition(completed, completed)


def test_immutable_publication_selects_platform_no_replace_primitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows rename and POSIX link publication both preserve exact bytes."""
    writer = cast(
        "ImmutableWriter",
        vars(progress)["_write_immutable"],
    )
    windows_destination = tmp_path / "windows-generation"
    _ = writer(
        windows_destination,
        WINDOWS_PAYLOAD,
        platform=progress.WINDOWS_PLATFORM,
    )
    assert windows_destination.read_bytes() == WINDOWS_PAYLOAD

    link_calls: list[tuple[Path, Path]] = []
    original_link = os.link

    def record_link(source: Path, destination: Path) -> None:
        link_calls.append((source, destination))
        original_link(source, destination)

    monkeypatch.setattr(os, "link", record_link)
    posix_destination = tmp_path / "posix-generation"
    _ = writer(
        posix_destination,
        POSIX_PAYLOAD,
        platform="posix",
    )
    assert posix_destination.read_bytes() == POSIX_PAYLOAD
    assert len(link_calls) == 1


def test_immutable_publication_wraps_disappearing_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A raced-away immutable destination remains a typed sidecar failure."""
    writer = cast(
        "ImmutableWriter",
        vars(progress)["_write_immutable"],
    )

    def collide_then_disappear(
        _temporary: Path,
        _destination: Path,
        *,
        platform: str = os.name,
    ) -> None:
        del _temporary, _destination, platform
        raise FileExistsError

    monkeypatch.setattr(progress, "_publish_no_replace", collide_then_disappear)
    destination = tmp_path / "raced-generation"
    with pytest.raises(ERROR, match="publication failed"):
        _ = writer(destination, b"payload", platform="posix")


def test_write_atomic_rejects_unavailable_or_corrupt_generation(
    tmp_path: Path,
) -> None:
    """Direct pointer publication cannot reference missing or corrupt bytes."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    destination = Path(sidecar.progress_path)
    with pytest.raises(ERROR, match="checkpoint payload is unavailable"):
        _ = progress.write_atomic(sidecar)
    assert not destination.exists()

    checkpoint_path = Path(sidecar.checkpoint_path or "")
    _ = checkpoint_path.write_bytes(b"corrupt-checkpoint")
    with pytest.raises(ERROR, match="checkpoint bytes do not match"):
        _ = progress.write_atomic(sidecar)
    assert not destination.exists()

    _ = checkpoint_path.write_bytes(checkpoint)
    partial_path = Path(sidecar.partial_path or "")
    _ = partial_path.write_bytes(b"corrupt-partial")
    with pytest.raises(ERROR, match="partial bytes do not match"):
        _ = progress.write_atomic(sidecar)
    assert not destination.exists()

    _ = partial_path.write_bytes(partial)
    assert progress.write_atomic(sidecar) == destination
    assert progress.read(destination) == sidecar


def test_checkpoint_generation_wraps_immutable_publication_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep immutable filesystem failures inside the sidecar boundary."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )

    def fail_publication(
        destination: Path,
        payload: bytes,
        *,
        platform: str = os.name,
    ) -> Path:
        del destination, payload, platform
        message = "injected immutable publication failure"
        raise OSError(message)

    monkeypatch.setattr(progress, "_write_immutable", fail_publication)
    with pytest.raises(
        ERROR,
        match="immutable progress payload publication failed",
    ):
        _ = progress.write_checkpoint_generation(sidecar, checkpoint)
    assert not Path(sidecar.progress_path).exists()


def test_checkpoint_generation_publishes_payloads_before_pointer(
    tmp_path: Path,
) -> None:
    """Immutable generation payloads round-trip under the sidecar pointer."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    destination = progress.write_checkpoint_generation(
        sidecar,
        checkpoint,
        partial,
    )
    assert progress.read(destination) == sidecar
    assert progress.read_checkpoint_generation(sidecar) == (
        checkpoint,
        partial,
    )
    assert Path(sidecar.checkpoint_path or "").read_bytes() == checkpoint
    assert Path(sidecar.partial_path or "").read_bytes() == partial


def test_checkpoint_generation_rejects_linked_immutable_path(
    tmp_path: Path,
) -> None:
    """Reject a linked immutable generation even when its bytes match."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    foreign = tmp_path / "foreign-checkpoint"
    _ = foreign.write_bytes(checkpoint)
    try:
        checkpoint_path.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    with pytest.raises(
        ERROR,
        match="immutable progress payload path is linked",
    ):
        _ = progress.write_checkpoint_generation(sidecar, checkpoint)
    assert checkpoint_path.is_symlink()
    assert foreign.read_bytes() == checkpoint
    assert not Path(sidecar.progress_path).exists()


def test_immutable_writer_rejects_linked_parent(tmp_path: Path) -> None:
    """Immutable publication rejects a redirected parent directory."""
    linked, target = _linked_directory(tmp_path, "linked-immutable-parent")
    destination = linked / "checkpoint.bin"
    writer = cast("ImmutableWriter", vars(progress)["_write_immutable"])

    with pytest.raises(
        ERROR, match="immutable progress payload path is linked"
    ):
        _ = writer(destination, b"checkpoint", platform=os.name)
    assert not (target / "checkpoint.bin").exists()


def test_checkpoint_read_rejects_link_replacing_published_generation(
    tmp_path: Path,
) -> None:
    """A post-publication link cannot satisfy an immutable payload hash."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    _ = progress.write_checkpoint_generation(sidecar, checkpoint)
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    checkpoint_path.unlink()
    foreign = tmp_path / "foreign-checkpoint-after-publish"
    _ = foreign.write_bytes(checkpoint)
    try:
        checkpoint_path.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    with pytest.raises(ERROR, match="checkpoint payload path is linked"):
        _ = progress.read_checkpoint_generation(sidecar)
    with pytest.raises(ERROR, match="checkpoint payload path is linked"):
        _ = progress.write_atomic(sidecar)
    assert checkpoint_path.is_symlink()
    assert foreign.read_bytes() == checkpoint


def test_checkpoint_generation_rejects_overwrite_hash_and_missing_payload(
    tmp_path: Path,
) -> None:
    """Generation files are immutable and every read rechecks their hashes."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    _ = checkpoint_path.write_bytes(b"conflicting-state")
    with pytest.raises(
        ERROR,
        match="immutable progress payload already differs",
    ):
        _ = progress.write_checkpoint_generation(sidecar, checkpoint)
    assert not Path(sidecar.progress_path).exists()

    _ = checkpoint_path.write_bytes(checkpoint)
    _ = progress.write_checkpoint_generation(sidecar, checkpoint)
    checkpoint_path.unlink()
    with pytest.raises(ERROR, match="unavailable"):
        _ = progress.read_checkpoint_generation(sidecar)


def test_write_atomic_preserves_previous_state_after_rejected_transition(
    tmp_path: Path,
) -> None:
    """A rejected update never replaces the last valid sidecar."""
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    stale = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns - 1,
        updated_at="2026-08-06T14:00:03Z",
        wall_elapsed_ns=original.wall_elapsed_ns - 1,
    )
    with pytest.raises(ERROR, match="active_elapsed_ns moved backward"):
        _ = progress.write_atomic(stale)
    assert progress.read(destination) == original


def test_terminal_status_controls_metadata(tmp_path: Path) -> None:
    """Terminal timestamps and diagnostics match exact lifecycle states."""
    running = _sidecar(tmp_path)
    with pytest.raises(ERROR, match="completed_at"):
        _ = progress.validate(replace(running, completed_at=COMPLETED))

    failed = _sidecar(tmp_path, status=progress.ProgressStatus.FAILED)
    assert progress.validate(failed) == failed
    with pytest.raises(ERROR, match="diagnostic presence"):
        _ = progress.validate(
            replace(failed, diagnostic_code=None, diagnostic_message=None)
        )

    checkpointed = _checkpointed(running, partial=None)
    completed = replace(
        checkpointed,
        completed_at="2026-08-06T14:00:03Z",
        status=progress.ProgressStatus.COMPLETED,
        updated_at="2026-08-06T14:00:03Z",
    )
    partial = b"forbidden-partial"
    with pytest.raises(ERROR, match="partial artifact"):
        _ = progress.validate(
            replace(
                completed,
                partial_bytes=len(partial),
                partial_path=str(
                    progress.partial_path(completed.output_path, 1)
                ),
                partial_sha256=_digest(partial),
            )
        )


def test_transition_validation_is_monotonic_and_terminal(
    tmp_path: Path,
) -> None:
    """Progress cannot regress, change identity, or reopen terminal work."""
    running = _sidecar(tmp_path)
    backward = replace(
        running,
        active_elapsed_ns=599,
        updated_at="2026-08-06T14:00:03Z",
        wall_elapsed_ns=759,
    )
    with pytest.raises(ERROR, match="active_elapsed_ns moved backward"):
        _ = progress.validate_transition(running, backward)

    known_total = replace(running, units_total=100)
    forgotten_total = replace(
        known_total,
        updated_at="2026-08-06T14:00:03Z",
        units_total=None,
    )
    with pytest.raises(ERROR, match="known units_total changed"):
        _ = progress.validate_transition(known_total, forgotten_total)

    completed = _sidecar(tmp_path, status=progress.ProgressStatus.COMPLETED)
    reopened = replace(
        completed,
        completed_at=None,
        status=progress.ProgressStatus.RUNNING,
        updated_at="2026-08-06T14:00:03Z",
    )
    with pytest.raises(ERROR, match="invalid progress transition"):
        _ = progress.validate_transition(completed, reopened)


def test_generation_publication_preserves_last_committed_resume(
    tmp_path: Path,
) -> None:
    """Unpublished next-generation files cannot invalidate the old pointer."""
    checkpoint_one = b"checkpoint-generation-one"
    partial_one = b"partial-generation-one"
    first = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint_one,
        partial=partial_one,
    )
    destination = progress.write_checkpoint_generation(
        first,
        checkpoint_one,
        partial_one,
    )
    assert progress.read(destination) == first
    assert progress.read_checkpoint_generation(first) == (
        checkpoint_one,
        partial_one,
    )

    checkpoint_two = b"checkpoint-generation-two"
    partial_two = b"partial-generation-two"
    second = _checkpointed(
        first,
        sequence=2,
        checkpoint=checkpoint_two,
        partial=partial_two,
    )
    _ = Path(second.checkpoint_path or "").write_bytes(checkpoint_two)
    _ = Path(second.partial_path or "").write_bytes(partial_two)

    assert progress.read(destination) == first
    assert progress.read_checkpoint_generation(first) == (
        checkpoint_one,
        partial_one,
    )

    _ = progress.write_checkpoint_generation(
        second,
        checkpoint_two,
        partial_two,
    )
    assert progress.read(destination) == second
    assert Path(first.checkpoint_path or "").is_file()
    assert Path(first.partial_path or "").is_file()


def _subprocess_environment() -> dict[str, str]:
    module_file = progress.__file__
    assert module_file is not None
    composition_root = Path(module_file).resolve().parents[1]
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    paths = [str(composition_root)]
    if existing:
        paths.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    return environment


@dataclass(frozen=True, slots=True)
class StaleWriterFixture:
    """One committed predecessor plus stale/newer competing updates."""

    attempted: Path
    candidate: Path
    destination: Path
    newer: progress.ProgressSidecar


def _stale_writer_fixture(tmp_path: Path) -> StaleWriterFixture:
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    stale = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns + 100,
        units_completed=original.units_completed + 1,
        updated_at="2026-08-06T14:00:02Z",
        wall_elapsed_ns=original.wall_elapsed_ns + 100,
    )
    newer = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns + 200,
        units_completed=original.units_completed + 2,
        updated_at="2026-08-06T14:00:03Z",
        wall_elapsed_ns=original.wall_elapsed_ns + 200,
    )
    candidate = tmp_path / "stale-candidate.json"
    _ = candidate.write_bytes(progress.encode(stale))
    return StaleWriterFixture(
        attempted=tmp_path / "stale-attempted",
        candidate=candidate,
        destination=destination,
        newer=newer,
    )


@dataclass(frozen=True, slots=True)
class WriterLockSignals:
    """Filesystem rendezvous points for two child lock contenders."""

    acquired: Path
    attempted: Path
    held: Path
    release: Path


def _wait_for_signal(path: Path, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            message = f"timed out waiting for {path}"
            raise AssertionError(message)
        time.sleep(0.01)


def _writer_lock_signals(tmp_path: Path) -> WriterLockSignals:
    return WriterLockSignals(
        acquired=tmp_path / "contender-acquired",
        attempted=tmp_path / "contender-attempted",
        held=tmp_path / "holder-held",
        release=tmp_path / "release-holder",
    )


def _spawn_writer_lock(
    destination: Path,
    role: str,
    signals: WriterLockSignals,
    *,
    environment: dict[str, str],
) -> sp.Popen[bytes]:
    return sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            "-c",
            WRITER_LOCK_SCRIPT,
            str(destination),
            role,
            str(signals.held),
            str(signals.attempted),
            str(signals.release),
            str(signals.acquired),
        ],
        env=environment,
        shell=False,
        stdout=sp.PIPE,
        stderr=sp.PIPE,
    )


def _terminate_child(process: sp.Popen[bytes]) -> None:
    if process.poll() is None:
        process.kill()
        _ = process.wait(timeout=10)


def test_writer_lock_serializes_cross_process_sidecar_updates(
    tmp_path: Path,
) -> None:
    """A competing writer cannot enter while another process owns the lock."""
    destination = tmp_path / PROGRESS_NAME
    signals = _writer_lock_signals(tmp_path)
    environment = _subprocess_environment()
    holder = _spawn_writer_lock(
        destination,
        "holder",
        signals,
        environment=environment,
    )
    try:
        _wait_for_signal(signals.held)
        contender = _spawn_writer_lock(
            destination, "contender", signals, environment=environment
        )
        try:
            _wait_for_signal(signals.attempted)
            time.sleep(0.2)
            assert not signals.acquired.exists()
            _ = signals.release.write_text("release", encoding="utf-8")
            stdout, stderr = contender.communicate(timeout=10)
            assert contender.returncode == 0, (stdout, stderr)
            assert signals.acquired.read_text(encoding="utf-8") == LOCK_ACQUIRED
        finally:
            _terminate_child(contender)
    finally:
        _ = signals.release.write_text("release", encoding="utf-8")
        stdout, stderr = holder.communicate(timeout=10)
        assert holder.returncode == 0, (stdout, stderr)
    assert Path(f"{destination}.lock").is_file()


class CloseFailingStream:
    """Minimal lock stream whose close operation fails."""

    def __init__(self) -> None:
        """Initialize the deterministic close failure message."""
        self.message: str = "injected writer lock close failure"

    def close(self) -> None:
        """Raise the injected descriptor-close failure.

        Raises:
            OSError: Always, with the deterministic injected failure.

        """
        raise OSError(self.message)


def test_writer_lock_wraps_descriptor_close_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Descriptor close remains inside the progress error boundary."""
    writer_lock = cast("WriterLock", vars(progress)["_writer_lock"])

    def fake_open(
        _path: Path,
        *_args: object,
        **_kwargs: object,
    ) -> CloseFailingStream:
        del _path, _args, _kwargs
        return CloseFailingStream()

    def release() -> None:
        return None

    def fake_acquire(_stream: object) -> Callable[[], None]:
        del _stream
        return release

    monkeypatch.setattr(Path, "open", fake_open)
    monkeypatch.setattr(progress, "_acquire_writer_lock", fake_acquire)
    destination = tmp_path / PROGRESS_NAME
    with (
        pytest.raises(ERROR, match="writer lock cannot be closed"),
        writer_lock(destination),
    ):
        pass


def test_write_atomic_wraps_mutable_publication_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable filesystem failures remain inside the sidecar error boundary."""
    candidate = _sidecar(tmp_path)

    def fail_publication(destination: Path, payload: bytes) -> Path:
        del destination, payload
        message = "injected mutable publication failure"
        raise OSError(message)

    monkeypatch.setattr(progress, "_write_atomic_bytes", fail_publication)
    with pytest.raises(ERROR, match="progress sidecar publication failed"):
        _ = progress.write_atomic(candidate)


def test_write_atomic_revalidates_stale_candidate_after_lock(
    tmp_path: Path,
) -> None:
    """A waiting stale writer cannot replace a newer committed sidecar."""
    fixture = _stale_writer_fixture(tmp_path)
    writer_lock = cast("WriterLock", vars(progress)["_writer_lock"])
    write_bytes = cast(
        "AtomicByteWriter",
        vars(progress)["_write_atomic_bytes"],
    )
    with writer_lock(fixture.destination):
        # jig-ignore-next-line: Ruff suppression is indivisible
        contender = sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
            [
                sys.executable,
                "-c",
                STALE_WRITER_SCRIPT,
                str(fixture.candidate),
                str(fixture.attempted),
            ],
            env=_subprocess_environment(),
            shell=False,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
        )
        try:
            _wait_for_signal(fixture.attempted)
            time.sleep(0.2)
            assert contender.poll() is None
            _ = write_bytes(fixture.destination, progress.encode(fixture.newer))
        except BaseException:
            _terminate_child(contender)
            raise
    stdout, stderr = contender.communicate(timeout=10)
    assert contender.returncode == STALE_WRITER_EXIT, (stdout, stderr)
    assert MOVED_BACKWARD in stderr
    assert progress.read(fixture.destination) == fixture.newer


def test_writer_lock_is_released_after_process_death(tmp_path: Path) -> None:
    """The operating system releases a writer lock when its process dies."""
    destination = tmp_path / PROGRESS_NAME
    signals = _writer_lock_signals(tmp_path)
    environment = _subprocess_environment()
    crasher = _spawn_writer_lock(
        destination, "crasher", signals, environment=environment
    )
    _wait_for_signal(signals.held)
    stdout, stderr = crasher.communicate(timeout=10)
    assert crasher.returncode == LOCK_CRASH_EXIT, (stdout, stderr)
    contender = _spawn_writer_lock(
        destination, "contender", signals, environment=environment
    )
    try:
        _wait_for_signal(signals.attempted)
        stdout, stderr = contender.communicate(timeout=10)
        assert contender.returncode == 0, (stdout, stderr)
        assert signals.acquired.read_text(encoding="utf-8") == LOCK_ACQUIRED
    finally:
        _terminate_child(contender)


def _crash_fixture(tmp_path: Path) -> CrashFixture:
    first = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=CHECKPOINT_BEFORE_CRASH,
        partial=PARTIAL_BEFORE_CRASH,
    )
    destination = progress.write_checkpoint_generation(
        first,
        CHECKPOINT_BEFORE_CRASH,
        PARTIAL_BEFORE_CRASH,
    )
    second = _checkpointed(
        first,
        sequence=2,
        checkpoint=CHECKPOINT_AFTER_CRASH,
        partial=PARTIAL_AFTER_CRASH,
    )
    sidecar_input = tmp_path / "pending-sidecar.json"
    checkpoint_input = tmp_path / "pending-checkpoint.bin"
    partial_input = tmp_path / "pending-partial.bin"
    _ = sidecar_input.write_bytes(progress.encode(second))
    _ = checkpoint_input.write_bytes(CHECKPOINT_AFTER_CRASH)
    _ = partial_input.write_bytes(PARTIAL_AFTER_CRASH)
    return CrashFixture(
        checkpoint_input=checkpoint_input,
        checkpoint_one=CHECKPOINT_BEFORE_CRASH,
        checkpoint_two=CHECKPOINT_AFTER_CRASH,
        destination=destination,
        first=first,
        partial_input=partial_input,
        partial_one=PARTIAL_BEFORE_CRASH,
        partial_two=PARTIAL_AFTER_CRASH,
        second=second,
        sidecar_input=sidecar_input,
    )


@pytest.mark.parametrize("boundary", CRASH_BOUNDARIES)
def test_process_crash_preserves_last_committed_generation(
    tmp_path: Path,
    boundary: str,
) -> None:
    """A child-process crash cannot publish or corrupt the next pointer."""
    fixture = _crash_fixture(tmp_path)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            "-c",
            CRASH_SCRIPT,
            str(fixture.sidecar_input),
            str(fixture.checkpoint_input),
            str(fixture.partial_input),
            str(CRASH_EXIT),
            boundary,
        ],
        check=False,
        capture_output=True,
        env=_subprocess_environment(),
        shell=False,
        timeout=30,
    )
    assert completed.returncode == CRASH_EXIT, completed.stderr.decode(
        errors="replace"
    )
    assert progress.read(fixture.destination) == fixture.first
    assert progress.read_checkpoint_generation(fixture.first) == (
        fixture.checkpoint_one,
        fixture.partial_one,
    )
    checkpoint_path = Path(fixture.second.checkpoint_path or "")
    partial_path = Path(fixture.second.partial_path or "")
    assert checkpoint_path.read_bytes() == fixture.checkpoint_two
    if boundary == AFTER_CHECKPOINT:
        assert not partial_path.exists()
    else:
        assert partial_path.read_bytes() == fixture.partial_two

    _ = progress.write_checkpoint_generation(
        fixture.second,
        fixture.checkpoint_two,
        fixture.partial_two,
    )
    assert progress.read(fixture.destination) == fixture.second


def test_generation_payloads_reject_mutable_foreign_bytes(
    tmp_path: Path,
) -> None:
    """Mutable payload aliases cannot cross immutable generation admission."""
    checkpoint = b"checkpoint-generation-one"
    partial = b"partial-generation-one"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    with pytest.raises(ERROR, match="checkpoint payload must use exact bytes"):
        _ = progress.write_checkpoint_generation(
            sidecar,
            cast("bytes", cast("object", bytearray(checkpoint))),
            partial,
        )
    with pytest.raises(ERROR, match="partial payload must use exact bytes"):
        _ = progress.write_checkpoint_generation(
            sidecar,
            checkpoint,
            cast("bytes", cast("object", bytearray(partial))),
        )
    assert not Path(sidecar.progress_path).exists()
    assert not Path(sidecar.checkpoint_path or "").exists()
    assert not Path(sidecar.partial_path or "").exists()


def test_generation_payloads_fail_closed_before_pointer_update(
    tmp_path: Path,
) -> None:
    """Hash mismatches, missing files, and immutable conflicts are rejected."""
    checkpoint = b"checkpoint-generation-one"
    partial = b"partial-generation-one"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    with pytest.raises(ERROR, match="checkpoint bytes do not match"):
        _ = progress.write_checkpoint_generation(
            sidecar,
            b"wrong checkpoint",
            partial,
        )
    assert not Path(sidecar.progress_path).exists()

    with pytest.raises(ERROR, match="payload is unavailable"):
        _ = progress.read_checkpoint_generation(sidecar)

    checkpoint_path = Path(sidecar.checkpoint_path or "")
    _ = checkpoint_path.write_bytes(b"conflicting checkpoint")
    with pytest.raises(ERROR, match="immutable progress payload"):
        _ = progress.write_checkpoint_generation(
            sidecar,
            checkpoint,
            partial,
        )


def test_operator_summary_reports_exact_timing_and_resume_paths(
    tmp_path: Path,
) -> None:
    """Human inspection exposes exact counters and timing without rounding."""
    sidecar = _checkpointed(_sidecar(tmp_path))
    summary = progress.render_summary(sidecar)
    assert summary.count("\n") == 1
    for expected in SUMMARY_FIELDS:
        assert expected in summary
    assert f"progress={sidecar.progress_path}" in summary
    assert f"checkpoint={sidecar.checkpoint_path}" in summary
    assert f"partial={sidecar.partial_path}" in summary


def test_inspector_cli_prints_summary_and_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The reference CLI prints valid timing and rejects absent sidecars."""
    sidecar = _sidecar(tmp_path)
    destination = progress.write_atomic(sidecar)
    assert progress.main([str(destination)]) == 0
    captured = capsys.readouterr()
    assert captured.out == progress.render_summary(sidecar)
    assert not captured.err

    missing = tmp_path / "missing.progress.json"
    assert progress.main([str(missing)]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert INSPECTION_FAILED_PREFIX in captured.err


def test_inspector_rejects_invalid_utf8_as_stable_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Malformed sidecar encoding never escapes the inspector boundary."""
    path = tmp_path / "invalid-utf8.progress.json"
    _ = path.write_bytes(bytes((0x7B, 0xFF, 0x7D)))
    assert progress.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert INSPECTION_FAILED_PREFIX in captured.err


def test_monotonic_timer_separates_every_scientific_phase() -> None:
    """Exclusive phases sum to wall time without UTC arithmetic."""
    clock = SequenceClock([100, 150, 170, 200, 230, 250, 290])
    timer = progress.ProgressTimer.start(clock=clock)
    assert timer.phase is progress.TimingPhase.ACTIVE
    _ = timer.switch(progress.TimingPhase.PAUSED)
    _ = timer.switch(progress.TimingPhase.VERIFICATION)
    _ = timer.switch(progress.TimingPhase.SERIALIZATION)
    _ = timer.switch(progress.TimingPhase.CHECKPOINT)
    _ = timer.switch(progress.TimingPhase.ACTIVE)
    timing = timer.snapshot()
    assert timing == progress.ProgressTiming(
        active_elapsed_ns=90,
        checkpoint_elapsed_ns=20,
        paused_elapsed_ns=20,
        serialization_elapsed_ns=30,
        verification_elapsed_ns=30,
        wall_elapsed_ns=190,
    )


def test_monotonic_timer_rejects_corrupt_direct_state() -> None:
    """Directly constructed timer state cannot masquerade as timing evidence."""
    foreign_phase = cast("progress.TimingPhase", cast("object", "foreign"))
    timer = progress.ProgressTimer(
        _clock=SequenceClock([100]),
        _phase=foreign_phase,
        _segment_started_ns=0,
        _started_ns=0,
    )
    with pytest.raises(ERROR, match="exact enum type"):
        _ = timer.snapshot()

    inconsistent = progress.ProgressTimer(
        _clock=SequenceClock([110]),
        _phase=progress.TimingPhase.ACTIVE,
        _segment_started_ns=100,
        _started_ns=90,
        _active_elapsed_ns=9,
    )
    with pytest.raises(ERROR, match="do not match closed elapsed time"):
        _ = inconsistent.snapshot()


def test_monotonic_timer_contains_foreign_clock_failures() -> None:
    """Foreign or failing clocks stay inside the sidecar error boundary."""
    with pytest.raises(ERROR, match="clock must be callable"):
        _ = progress.ProgressTimer.start(
            clock=cast("Callable[[], int]", object())
        )

    def fail_clock() -> int:
        message = "synthetic clock failure"
        raise RuntimeError(message)

    with pytest.raises(ERROR, match="monotonic clock failed"):
        _ = progress.ProgressTimer.start(clock=fail_clock)

    direct = progress.ProgressTimer(
        _clock=cast("Callable[[], int]", object()),
        _phase=progress.TimingPhase.ACTIVE,
        _segment_started_ns=0,
        _started_ns=0,
    )
    with pytest.raises(ERROR, match="clock must be callable"):
        _ = direct.snapshot()


def test_monotonic_timer_rejects_invalid_phases_and_clock_samples() -> None:
    """Invalid phases or clocks fail before corrupting elapsed-time evidence."""
    with pytest.raises(ERROR, match="exact enum type"):
        _ = progress.ProgressTimer.start(
            phase=cast("progress.TimingPhase", cast("object", "active"))
        )
    with pytest.raises(ERROR, match="non-negative integer"):
        _ = progress.ProgressTimer.start(clock=SequenceClock([-1]))
    with pytest.raises(ERROR, match="non-negative integer"):
        _ = progress.ProgressTimer.start(
            clock=cast("SequenceClock", lambda: True)
        )

    timer = progress.ProgressTimer.start(clock=SequenceClock([100, 99]))
    with pytest.raises(ERROR, match="exact enum type"):
        _ = timer.switch(cast("progress.TimingPhase", cast("object", "paused")))
    with pytest.raises(ERROR, match="moved backward"):
        _ = timer.snapshot()
