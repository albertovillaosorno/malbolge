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
import stat
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
AFTER_CHECKPOINT_PUBLISH = "after-checkpoint-publish"
AFTER_CHECKPOINT_SYNC = "after-checkpoint-sync"
AFTER_PARTIAL_PUBLISH = "after-partial-publish"
AFTER_PARTIAL_SYNC = "after-partial-sync"
AFTER_SIDECAR_REPLACE = "after-sidecar-replace"
AFTER_SIDECAR_SYNC = "after-sidecar-sync"
BEFORE_CHECKPOINT_FILE_SYNC = "before-checkpoint-file-sync"
BEFORE_CHECKPOINT_PUBLISH = "before-checkpoint-publish"
BEFORE_PARTIAL_FILE_SYNC = "before-partial-file-sync"
BEFORE_PARTIAL_PUBLISH = "before-partial-publish"
BEFORE_SIDECAR_FILE_SYNC = "before-sidecar-file-sync"
BEFORE_SIDECAR_REPLACE = "before-sidecar-replace"
BEFORE_SIDECAR = "before-sidecar"
CRASH_BOUNDARIES = (
    BEFORE_CHECKPOINT_FILE_SYNC,
    BEFORE_CHECKPOINT_PUBLISH,
    AFTER_CHECKPOINT_PUBLISH,
    AFTER_CHECKPOINT_SYNC,
    AFTER_CHECKPOINT,
    BEFORE_PARTIAL_FILE_SYNC,
    BEFORE_PARTIAL_PUBLISH,
    AFTER_PARTIAL_PUBLISH,
    AFTER_PARTIAL_SYNC,
    BEFORE_SIDECAR_FILE_SYNC,
    BEFORE_SIDECAR_REPLACE,
    AFTER_SIDECAR_REPLACE,
    AFTER_SIDECAR_SYNC,
    BEFORE_SIDECAR,
)
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
import stat
import sys
from scripts import progress_sidecar as progress

sidecar = progress.read(Path(sys.argv[1]))
checkpoint = Path(sys.argv[2]).read_bytes()
partial = Path(sys.argv[3]).read_bytes()
exit_code = int(sys.argv[4])
boundary = sys.argv[5]
original_write_immutable = progress._write_immutable
original_publish_immutable_payload = progress._publish_immutable_payload
original_confirm_durability = progress._confirm_publication_durability
original_fsync = os.fsync
original_replace = Path.replace
publication_count = 0
regular_sync_count = 0

def fsync_then_maybe_crash(descriptor):
    global regular_sync_count
    mode = os.fstat(descriptor).st_mode
    if not stat.S_ISREG(mode):
        return original_fsync(descriptor)
    regular_sync_count += 1
    if boundary == "before-checkpoint-file-sync" and regular_sync_count == 1:
        os._exit(exit_code)
    if boundary == "before-partial-file-sync" and regular_sync_count == 2:
        os._exit(exit_code)
    if boundary == "before-sidecar-file-sync" and regular_sync_count == 3:
        os._exit(exit_code)
    return original_fsync(descriptor)

def publish_then_maybe_crash(temporary, destination, payload, *, platform):
    global publication_count
    publication_number = publication_count + 1
    if boundary == "before-checkpoint-publish" and publication_number == 1:
        os._exit(exit_code)
    if boundary == "before-partial-publish" and publication_number == 2:
        os._exit(exit_code)
    result = original_publish_immutable_payload(
        temporary,
        destination,
        payload,
        platform=platform,
    )
    publication_count = publication_number
    if boundary == "after-checkpoint-publish" and publication_count == 1:
        os._exit(exit_code)
    if boundary == "after-partial-publish" and publication_count == 2:
        os._exit(exit_code)
    return result

def write_then_maybe_crash(destination, payload):
    result = original_write_immutable(destination, payload)
    if boundary == "after-checkpoint" and publication_count == 1:
        os._exit(exit_code)
    return result

def confirm_then_maybe_crash(published_path, *, context, platform=os.name):
    result = original_confirm_durability(
        published_path,
        context=context,
        platform=platform,
    )
    if context == "immutable progress payload":
        if boundary == "after-checkpoint-sync" and publication_count == 1:
            os._exit(exit_code)
        if boundary == "after-partial-sync" and publication_count == 2:
            os._exit(exit_code)
    if context == "progress sidecar" and boundary == "after-sidecar-sync":
        os._exit(exit_code)
    return result

def crash_before_sidecar(_sidecar):
    os._exit(exit_code)

def replace_then_maybe_crash(source, destination):
    if boundary == "before-sidecar-replace":
        os._exit(exit_code)
    result = original_replace(source, destination)
    if boundary == "after-sidecar-replace":
        os._exit(exit_code)
    return result

progress._publish_immutable_payload = publish_then_maybe_crash
progress._confirm_publication_durability = confirm_then_maybe_crash
progress._write_immutable = write_then_maybe_crash
os.fsync = fsync_then_maybe_crash
if boundary == "before-sidecar":
    progress.write_atomic = crash_before_sidecar
elif boundary in {"before-sidecar-replace", "after-sidecar-replace"}:
    Path.replace = replace_then_maybe_crash
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


class PayloadDescriptorWriter(Protocol):
    """Typed view of the shared temporary-payload descriptor writer."""

    def __call__(self, descriptor: int, payload: bytes) -> None:
        """Write one payload and own the supplied descriptor lifecycle."""
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
class FailingPayloadStream:
    """Temporary payload stream with deterministic write and close failures."""

    write_failure: str
    close_failure: str

    def write(self, payload: bytes) -> int:
        """Raise the configured primary write failure.

        Raises:
            OSError: Always, from the configured write failure.

        """
        del payload
        raise OSError(self.write_failure)

    def close(self) -> None:
        """Raise the configured secondary close failure.

        Raises:
            OSError: Always, from the configured close failure.

        """
        raise OSError(self.close_failure)


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


@dataclass(slots=True)
class FlushFailure:
    """Inject one filesystem sync failure on an exact callback invocation."""

    fail_on: int
    message: str
    calls: int = 0

    def __call__(
        self,
        _path: Path,
        *,
        platform: str = os.name,
    ) -> None:
        """Fail on the configured invocation and otherwise accept the flush.

        Raises:
            OSError: When this is the configured failing invocation.

        """
        del _path, platform
        self.calls += 1
        if self.calls == self.fail_on:
            raise OSError(self.message)


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


def test_directory_close_after_sync_reports_committed_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Directory close failure cannot make confirmed durability uncertain."""
    published_path = tmp_path / PROGRESS_NAME
    descriptor = 71
    calls: list[tuple[str, int]] = []
    confirm = cast(
        "Callable[..., None]",
        vars(progress)["_confirm_publication_durability"],
    )

    def open_directory(path: Path, flags: int) -> int:
        del path, flags
        return descriptor

    def sync_directory(observed: int) -> None:
        calls.append(("sync", observed))

    def fail_close(observed: int) -> None:
        calls.append(("close", observed))
        message = "injected directory close failure"
        raise OSError(message)

    with monkeypatch.context() as context:
        context.setattr(os, "open", open_directory)
        context.setattr(os, "fsync", sync_directory)
        context.setattr(os, "close", fail_close)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match="committed durably but directory close failed",
        ) as captured:
            confirm(published_path, context="progress sidecar")

    assert not isinstance(
        captured.value,
        progress.ProgressSidecarDurabilityError,
    )
    assert captured.value.published_path == published_path
    assert calls == [("sync", descriptor), ("close", descriptor)]


def test_directory_close_failure_preserves_primary_sync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Directory close failure remains secondary to failed durability sync."""
    published_path = tmp_path / PROGRESS_NAME
    descriptor = 73
    sync_failure = "injected directory sync failure"
    close_failure = "injected directory close failure"
    confirm = cast(
        "Callable[..., None]",
        vars(progress)["_confirm_publication_durability"],
    )

    def open_directory(path: Path, flags: int) -> int:
        del path, flags
        return descriptor

    def fail_sync(observed: int) -> None:
        del observed
        raise OSError(sync_failure)

    def fail_close(observed: int) -> None:
        del observed
        raise OSError(close_failure)

    with monkeypatch.context() as context:
        context.setattr(os, "open", open_directory)
        context.setattr(os, "fsync", fail_sync)
        context.setattr(os, "close", fail_close)
        with pytest.raises(
            progress.ProgressSidecarDurabilityError,
            match=sync_failure,
        ) as captured:
            confirm(published_path, context="progress sidecar")

    primary_error = captured.value.__cause__
    assert isinstance(primary_error, OSError)
    assert str(primary_error) == sync_failure
    expected_note = f"directory descriptor close also failed: {close_failure}"
    assert getattr(primary_error, "__notes__", None) == [expected_note]


def test_payload_descriptor_fdopen_failure_closes_raw_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed stream ownership transfer still closes the raw descriptor."""
    writer = cast(
        "PayloadDescriptorWriter",
        vars(progress)["_write_payload_descriptor"],
    )
    descriptor = 101
    binary_mode = "wb"
    open_failure = "injected payload fdopen failure"
    close_failure = "injected raw descriptor close failure"

    def fail_fdopen(observed: int, mode: str) -> FailingPayloadStream:
        assert observed == descriptor
        assert mode == binary_mode
        raise OSError(open_failure)

    def fail_close(observed: int) -> None:
        assert observed == descriptor
        raise OSError(close_failure)

    with monkeypatch.context() as context:
        context.setattr(os, "fdopen", fail_fdopen)
        context.setattr(os, "close", fail_close)
        with pytest.raises(OSError, match=open_failure) as captured:
            writer(descriptor, b"payload")

    assert str(captured.value) == open_failure
    expected_note = (
        f"payload descriptor ownership cleanup also failed: {close_failure}"
    )
    assert getattr(captured.value, "__notes__", None) == [expected_note]


def test_checkpoint_generation_preserves_write_before_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Immutable temp-stream close cannot mask its primary write failure."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    write_failure = "injected payload write failure"
    close_failure = "injected payload close failure"

    def failing_fdopen(descriptor: int, mode: str) -> FailingPayloadStream:
        del descriptor, mode
        return FailingPayloadStream(write_failure, close_failure)

    with monkeypatch.context() as context:
        context.setattr(os, "fdopen", failing_fdopen)
        expected_message = (
            f"immutable progress payload publication failed: {write_failure}"
        )
        with pytest.raises(ERROR, match=expected_message) as captured:
            _ = progress.write_checkpoint_generation(sidecar, checkpoint)

    primary_error = captured.value.__context__
    assert isinstance(primary_error, OSError)
    assert str(primary_error) == write_failure
    expected_note = f"payload descriptor close also failed: {close_failure}"
    assert getattr(primary_error, "__notes__", None) == [expected_note]
    assert not Path(sidecar.progress_path).exists()


def test_checkpoint_generation_file_sync_failure_is_prepublication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Temporary checkpoint file sync failure cannot publish generation data."""
    checkpoint = b"checkpoint-file-sync-failure"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    failure_message = "injected temporary file sync failure"

    def fail_file_sync(descriptor: int) -> None:
        del descriptor
        raise OSError(failure_message)

    with monkeypatch.context() as context:
        context.setattr(os, "fsync", fail_file_sync)
        expected_message = (
            f"immutable progress payload publication failed: {failure_message}"
        )
        with pytest.raises(ERROR, match=expected_message) as captured:
            _ = progress.write_checkpoint_generation(sidecar, checkpoint)

    committed_error = progress.ProgressSidecarCommittedError
    assert not isinstance(captured.value, committed_error)
    assert not checkpoint_path.exists()
    assert not Path(sidecar.progress_path).exists()
    assert not tuple(
        checkpoint_path.parent.glob(f".{checkpoint_path.name}.*.tmp")
    )


def test_checkpoint_generation_reports_committed_durability_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-publication sync failure preserves exact committed evidence."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")

    def fail_parent_flush(
        _path: Path,
        *,
        platform: str = os.name,
    ) -> None:
        del _path, platform
        message = "injected checkpoint directory sync failure"
        raise OSError(message)

    with monkeypatch.context() as context:
        context.setattr(progress, "_flush_parent", fail_parent_flush)
        with pytest.raises(
            progress.ProgressSidecarDurabilityError,
            match=(
                "immutable progress payload committed but durability "
                "confirmation failed"
            ),
        ) as captured:
            _ = progress.write_checkpoint_generation(sidecar, checkpoint)

    assert captured.value.published_path == checkpoint_path
    assert checkpoint_path.read_bytes() == checkpoint
    destination = Path(sidecar.progress_path)
    assert not destination.exists()
    assert (
        progress.write_checkpoint_generation(sidecar, checkpoint) == destination
    )
    assert progress.read(destination) == sidecar


def test_partial_file_sync_failure_reports_committed_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retain the committed checkpoint across partial prepublication failure."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    partial_path = Path(sidecar.partial_path or "")
    original_fsync = os.fsync
    regular_syncs, partial_sync_number = 0, 2
    failure_message = "injected partial temporary file sync failure"

    def fail_partial_file_sync(descriptor: int) -> None:
        nonlocal regular_syncs
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            regular_syncs += 1
            if regular_syncs == partial_sync_number:
                raise OSError(failure_message)
        original_fsync(descriptor)

    with monkeypatch.context() as context:
        context.setattr(os, "fsync", fail_partial_file_sync)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match=(
                "checkpoint progress payload committed durably but later "
                "generation member publication failed"
            ),
        ) as captured:
            _ = progress.write_checkpoint_generation(
                sidecar,
                checkpoint,
                partial,
            )

    assert captured.value.published_path == checkpoint_path
    assert checkpoint_path.read_bytes() == checkpoint
    assert not partial_path.exists()
    assert not Path(sidecar.progress_path).exists()
    assert progress.write_checkpoint_generation(
        sidecar,
        checkpoint,
        partial,
    ) == Path(sidecar.progress_path)


def test_partial_collision_reports_committed_checkpoint(tmp_path: Path) -> None:
    """A divergent partial collision retains the committed checkpoint path."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    foreign_partial = b"foreign-partial-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    partial_path = Path(sidecar.partial_path or "")
    _ = partial_path.write_bytes(foreign_partial)

    with pytest.raises(
        progress.ProgressSidecarCommittedError,
        match=(
            "checkpoint progress payload committed durably but later "
            "generation member publication failed"
        ),
    ) as captured:
        _ = progress.write_checkpoint_generation(sidecar, checkpoint, partial)

    assert captured.value.published_path == checkpoint_path
    assert checkpoint_path.read_bytes() == checkpoint
    assert partial_path.read_bytes() == foreign_partial
    assert not Path(sidecar.progress_path).exists()


def test_sidecar_file_sync_failure_reports_committed_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pointer prepublication failure retains the last generation member."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    partial_path = Path(sidecar.partial_path or "")
    original_fsync = os.fsync
    regular_syncs, sidecar_sync_number = 0, 3
    failure_message = "injected sidecar temporary file sync failure"

    def fail_sidecar_file_sync(descriptor: int) -> None:
        nonlocal regular_syncs
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            regular_syncs += 1
            if regular_syncs == sidecar_sync_number:
                raise OSError(failure_message)
        original_fsync(descriptor)

    with monkeypatch.context() as context:
        context.setattr(os, "fsync", fail_sidecar_file_sync)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match=(
                "generation payload committed durably but progress sidecar "
                "publication failed"
            ),
        ) as captured:
            _ = progress.write_checkpoint_generation(
                sidecar,
                checkpoint,
                partial,
            )

    assert captured.value.published_path == partial_path
    assert checkpoint_path.read_bytes() == checkpoint
    assert partial_path.read_bytes() == partial
    assert not Path(sidecar.progress_path).exists()
    assert progress.write_checkpoint_generation(
        sidecar,
        checkpoint,
        partial,
    ) == Path(sidecar.progress_path)


def test_partial_generation_reports_committed_durability_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial-member sync failure reports that member as committed."""
    checkpoint = b"checkpoint-state-v1"
    partial = b"partial-malbolge-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    fail_partial_flush = FlushFailure(
        fail_on=2,
        message="injected partial directory sync failure",
    )

    with monkeypatch.context() as context:
        context.setattr(progress, "_flush_parent", fail_partial_flush)
        with pytest.raises(
            progress.ProgressSidecarDurabilityError,
            match=(
                "immutable progress payload committed but durability "
                "confirmation failed"
            ),
        ) as captured:
            _ = progress.write_checkpoint_generation(
                sidecar,
                checkpoint,
                partial,
            )

    checkpoint_path = Path(sidecar.checkpoint_path or "")
    partial_path = Path(sidecar.partial_path or "")
    assert captured.value.published_path == partial_path
    assert checkpoint_path.read_bytes() == checkpoint
    assert partial_path.read_bytes() == partial
    destination = Path(sidecar.progress_path)
    assert not destination.exists()
    assert (
        progress.write_checkpoint_generation(sidecar, checkpoint, partial)
        == destination
    )
    assert progress.read(destination) == sidecar


def test_checkpoint_generation_reports_committed_temp_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Immutable temp cleanup cannot hide a durable generation member."""
    checkpoint = b"checkpoint-state-v1"
    sidecar = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(sidecar.checkpoint_path or "")
    original_unlink = Path.unlink

    def fail_temporary_unlink(
        path: Path,
        *,
        missing_ok: bool = False,
    ) -> None:
        if path.name.endswith(".tmp"):
            message = "injected immutable temporary cleanup failure"
            raise OSError(message)
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", fail_temporary_unlink)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match="committed durably but temporary cleanup failed",
        ) as captured:
            _ = progress.write_checkpoint_generation(sidecar, checkpoint)

    assert captured.value.published_path == checkpoint_path
    assert checkpoint_path.read_bytes() == checkpoint
    destination = Path(sidecar.progress_path)
    assert not destination.exists()
    assert (
        progress.write_checkpoint_generation(sidecar, checkpoint) == destination
    )


def test_write_atomic_skips_cleanup_after_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A moved mutable temporary path is never cleaned up after commit."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    original_unlink = Path.unlink

    def reject_temporary_unlink(
        path: Path,
        *,
        missing_ok: bool = False,
    ) -> None:
        if path.name.endswith(".tmp"):
            message = "mutable temporary path was unlinked after replacement"
            raise OSError(message)
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "unlink", reject_temporary_unlink)
        assert progress.write_atomic(candidate) == destination
    assert progress.read(destination) == candidate


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


def test_partial_read_rejects_link_replacing_published_generation(
    tmp_path: Path,
) -> None:
    """A post-publication link cannot satisfy a partial payload hash."""
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
    partial_path = Path(sidecar.partial_path or "")
    partial_path.unlink()
    foreign = tmp_path / "foreign-partial-after-publish"
    _ = foreign.write_bytes(partial)
    try:
        partial_path.symlink_to(foreign)
    except OSError as error:
        pytest.skip(f"file symlinks unavailable on this host: {error}")

    original_pointer = destination.read_bytes()
    with pytest.raises(ERROR, match="partial payload path is linked"):
        _ = progress.read_checkpoint_generation(sidecar)
    with pytest.raises(ERROR, match="partial payload path is linked"):
        _ = progress.write_atomic(sidecar)
    assert destination.read_bytes() == original_pointer
    assert partial_path.is_symlink()
    assert foreign.read_bytes() == partial


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


def test_cancelled_job_persists_resume_and_rejects_restart(
    tmp_path: Path,
) -> None:
    """Orderly cancellation preserves its latest resumable generation."""
    checkpoint = b"cancelled-checkpoint"
    partial = b"cancelled-partial"
    running = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    destination = progress.write_checkpoint_generation(
        running,
        checkpoint,
        partial,
    )
    cancelled = replace(
        running,
        completed_at="2026-08-06T14:00:03Z",
        diagnostic_code="MALBOLGE-JOB-001",
        diagnostic_message="cancelled",
        status=progress.ProgressStatus.CANCELLED,
        updated_at="2026-08-06T14:00:03Z",
    )
    assert progress.write_atomic(cancelled) == destination
    assert progress.read(destination) == cancelled
    assert progress.read_checkpoint_generation(cancelled) == (
        checkpoint,
        partial,
    )

    reopened = replace(
        cancelled,
        completed_at=None,
        diagnostic_code=None,
        diagnostic_message=None,
        status=progress.ProgressStatus.RUNNING,
        updated_at="2026-08-06T14:00:04Z",
    )
    with pytest.raises(ERROR, match="cancelled->running"):
        _ = progress.write_atomic(reopened)
    assert progress.read(destination) == cancelled


def test_failed_job_persists_resume_and_rejects_restart(
    tmp_path: Path,
) -> None:
    """Handled failure preserves its latest resumable generation."""
    checkpoint = b"failed-checkpoint"
    partial = b"failed-partial"
    running = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=partial,
    )
    destination = progress.write_checkpoint_generation(
        running,
        checkpoint,
        partial,
    )
    failed = replace(
        running,
        completed_at="2026-08-06T14:00:03Z",
        diagnostic_code="MALBOLGE-JOB-002",
        diagnostic_message="verification failed",
        status=progress.ProgressStatus.FAILED,
        updated_at="2026-08-06T14:00:03Z",
    )
    assert progress.write_atomic(failed) == destination
    assert progress.read(destination) == failed
    assert progress.read_checkpoint_generation(failed) == (
        checkpoint,
        partial,
    )

    reopened = replace(
        failed,
        completed_at=None,
        diagnostic_code=None,
        diagnostic_message=None,
        status=progress.ProgressStatus.RUNNING,
        updated_at="2026-08-06T14:00:04Z",
    )
    with pytest.raises(ERROR, match="failed->running"):
        _ = progress.write_atomic(reopened)
    assert progress.read(destination) == failed


def test_completed_job_persists_terminal_pointer_and_rejects_restart(
    tmp_path: Path,
) -> None:
    """Completed publication remains terminal across durable reload."""
    checkpoint = b"completed-checkpoint"
    running = _checkpointed(
        _sidecar(tmp_path),
        checkpoint=checkpoint,
        partial=None,
    )
    destination = progress.write_checkpoint_generation(running, checkpoint)
    completed = replace(
        running,
        completed_at="2026-08-06T14:00:03Z",
        status=progress.ProgressStatus.COMPLETED,
        updated_at="2026-08-06T14:00:03Z",
    )
    assert progress.write_atomic(completed) == destination
    assert progress.read(destination) == completed
    assert progress.read_checkpoint_generation(completed) == (checkpoint, None)

    reopened = replace(
        completed,
        completed_at=None,
        status=progress.ProgressStatus.RUNNING,
        updated_at="2026-08-06T14:00:04Z",
    )
    with pytest.raises(ERROR, match="completed->running"):
        _ = progress.write_atomic(reopened)
    assert progress.read(destination) == completed


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


def test_writer_lock_preserves_acquire_failure_before_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock-stream close cleanup cannot mask acquisition failure."""
    writer_lock = cast("WriterLock", vars(progress)["_writer_lock"])
    acquire_failure = "injected writer lock acquisition failure"
    close_failure = "injected writer lock close failure"

    def fail_acquire(stream: object) -> Callable[[], None]:
        del stream
        raise OSError(acquire_failure)

    def fail_close(stream: object) -> None:
        del stream
        raise progress.ProgressSidecarError(close_failure)

    with monkeypatch.context() as context:
        context.setattr(progress, "_acquire_writer_lock", fail_acquire)
        context.setattr(progress, "_close_writer_lock_stream", fail_close)
        with (
            pytest.raises(
                ERROR,
                match=f"writer lock cannot be acquired: {acquire_failure}",
            ) as captured,
            writer_lock(tmp_path / PROGRESS_NAME),
        ):
            pytest.fail(
                "writer lock body executed after acquisition failure"
            )

    expected_note = f"writer lock close also failed: {close_failure}"
    assert getattr(captured.value, "__notes__", None) == [expected_note]


def test_writer_lock_preserves_body_failure_before_teardown_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep release and close cleanup secondary to a lock-body failure.

    Raises:
        ProgressSidecarError: Injected and captured inside the regression.

    """
    writer_lock = cast("WriterLock", vars(progress)["_writer_lock"])
    body_failure = "injected writer lock body failure"
    release_failure = "injected writer lock release failure"
    close_failure = "injected writer lock close failure"

    def fail_release(release: Callable[[], None]) -> None:
        del release
        raise progress.ProgressSidecarError(release_failure)

    def fail_close(stream: object) -> None:
        del stream
        raise progress.ProgressSidecarError(close_failure)

    with monkeypatch.context() as context:
        context.setattr(progress, "_release_writer_lock", fail_release)
        context.setattr(progress, "_close_writer_lock_stream", fail_close)
        with (
            pytest.raises(ERROR, match=body_failure) as captured,
            writer_lock(tmp_path / PROGRESS_NAME),
        ):
            raise progress.ProgressSidecarError(body_failure)

    assert getattr(captured.value, "__notes__", None) == [
        f"writer lock release also failed: {release_failure}",
        f"writer lock close also failed: {close_failure}",
    ]


def test_write_atomic_reports_committed_lock_release_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lock-release failure cannot hide a durably committed pointer."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    original_acquire = cast(
        "Callable[[object], Callable[[], None]]",
        vars(progress)["_acquire_writer_lock"],
    )

    def acquire_with_failing_release(stream: object) -> Callable[[], None]:
        release = original_acquire(stream)

        def release_then_fail() -> None:
            release()
            message = "injected post-commit writer lock release failure"
            raise OSError(message)

        return release_then_fail

    with monkeypatch.context() as context:
        context.setattr(
            progress,
            "_acquire_writer_lock",
            acquire_with_failing_release,
        )
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match="committed durably but writer lock cleanup failed",
        ) as captured:
            _ = progress.write_atomic(candidate)

    assert captured.value.published_path == destination
    assert progress.read(destination) == candidate


def test_write_atomic_preserves_release_before_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-commit lock close cleanup cannot mask release failure."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    release_failure = "injected writer lock release failure"
    close_failure = "injected writer lock close failure"

    def fail_release(release: Callable[[], None]) -> None:
        del release
        raise progress.ProgressSidecarError(release_failure)

    def fail_close(stream: object) -> None:
        del stream
        raise progress.ProgressSidecarError(close_failure)

    with monkeypatch.context() as context:
        context.setattr(progress, "_release_writer_lock", fail_release)
        context.setattr(progress, "_close_writer_lock_stream", fail_close)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match=(
                "committed durably but writer lock cleanup failed: "
                f"{release_failure}"
            ),
        ) as captured:
            _ = progress.write_atomic(candidate)

    assert captured.value.published_path == destination
    primary_error = captured.value.__cause__
    assert isinstance(primary_error, progress.ProgressSidecarError)
    assert str(primary_error) == release_failure
    expected_note = f"writer lock close also failed: {close_failure}"
    assert getattr(primary_error, "__notes__", None) == [expected_note]
    assert progress.read(destination) == candidate


def test_write_atomic_reports_committed_lock_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lock-close failure cannot hide a durably committed pointer."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    original_close = cast(
        "Callable[[object], None]",
        vars(progress)["_close_writer_lock_stream"],
    )

    def close_then_fail(stream: object) -> None:
        original_close(stream)
        message = "progress writer lock cannot be closed: injected failure"
        raise progress.ProgressSidecarError(message)

    with monkeypatch.context() as context:
        context.setattr(progress, "_close_writer_lock_stream", close_then_fail)
        with pytest.raises(
            progress.ProgressSidecarCommittedError,
            match="committed durably but writer lock cleanup failed",
        ) as captured:
            _ = progress.write_atomic(candidate)

    assert captured.value.published_path == destination
    assert progress.read(destination) == candidate


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


def test_write_atomic_preserves_write_before_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable temp-stream close cannot mask its primary write failure."""
    candidate = _sidecar(tmp_path)
    write_failure = "injected payload write failure"
    close_failure = "injected payload close failure"

    def failing_fdopen(descriptor: int, mode: str) -> FailingPayloadStream:
        del descriptor, mode
        return FailingPayloadStream(write_failure, close_failure)

    with monkeypatch.context() as context:
        context.setattr(os, "fdopen", failing_fdopen)
        with pytest.raises(
            ERROR,
            match=f"progress sidecar publication failed: {write_failure}",
        ) as captured:
            _ = progress.write_atomic(candidate)

    primary_error = captured.value.__context__
    assert isinstance(primary_error, OSError)
    assert str(primary_error) == write_failure
    expected_note = f"payload descriptor close also failed: {close_failure}"
    assert getattr(primary_error, "__notes__", None) == [expected_note]
    assert not Path(candidate.progress_path).exists()


def test_write_atomic_preserves_primary_before_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable temp cleanup cannot mask a prepublication replace failure."""
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    candidate = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns + 100,
        units_completed=original.units_completed + 1,
        updated_at="2026-08-06T14:00:02Z",
        wall_elapsed_ns=original.wall_elapsed_ns + 100,
    )
    original_unlink = Path.unlink
    replace_failure = "injected mutable replace failure"
    cleanup_failure = "injected mutable temporary cleanup failure"

    def fail_replace(path: Path, destination: Path) -> Path:
        del path, destination
        raise OSError(replace_failure)

    def fail_temporary_unlink(
        path: Path,
        *,
        missing_ok: bool = False,
    ) -> None:
        if path.name.endswith(".tmp"):
            raise OSError(cleanup_failure)
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as context:
        context.setattr(Path, "replace", fail_replace)
        context.setattr(Path, "unlink", fail_temporary_unlink)
        with pytest.raises(
            ERROR,
            match=(
                "progress sidecar publication failed: "
                "injected mutable replace failure"
            ),
        ) as captured:
            _ = progress.write_atomic(candidate)

    primary_error = captured.value.__context__
    assert isinstance(primary_error, OSError)
    assert str(primary_error) == replace_failure
    expected_note = f"mutable temporary cleanup also failed: {cleanup_failure}"
    assert getattr(primary_error, "__notes__", None) == [expected_note]
    assert progress.read(destination) == original


def test_write_atomic_file_sync_failure_preserves_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Temporary pointer file sync failure cannot replace committed state."""
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    candidate = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns + 1,
        updated_at="2026-08-06T14:00:03Z",
        units_completed=original.units_completed + 1,
        wall_elapsed_ns=original.wall_elapsed_ns + 1,
    )
    failure_message = "injected temporary file sync failure"

    def fail_file_sync(descriptor: int) -> None:
        del descriptor
        raise OSError(failure_message)

    with monkeypatch.context() as context:
        context.setattr(os, "fsync", fail_file_sync)
        with pytest.raises(
            ERROR,
            match=f"progress sidecar publication failed: {failure_message}",
        ) as captured:
            _ = progress.write_atomic(candidate)

    committed_error = progress.ProgressSidecarCommittedError
    assert not isinstance(captured.value, committed_error)
    assert progress.read(destination) == original
    assert not tuple(destination.parent.glob(f".{destination.name}.*.tmp"))


def test_write_atomic_reports_committed_durability_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report that atomic replacement committed before pointer sync failed."""
    original = _sidecar(tmp_path)
    destination = progress.write_atomic(original)
    candidate = replace(
        original,
        active_elapsed_ns=original.active_elapsed_ns + 100,
        units_completed=original.units_completed + 1,
        updated_at="2026-08-06T14:00:02Z",
        wall_elapsed_ns=original.wall_elapsed_ns + 100,
    )

    def fail_parent_flush(
        _path: Path,
        *,
        platform: str = os.name,
    ) -> None:
        del _path, platform
        message = "injected sidecar directory sync failure"
        raise OSError(message)

    with monkeypatch.context() as context:
        context.setattr(progress, "_flush_parent", fail_parent_flush)
        with pytest.raises(
            progress.ProgressSidecarDurabilityError,
            match=(
                "progress sidecar committed but durability "
                "confirmation failed"
            ),
        ) as captured:
            _ = progress.write_atomic(candidate)

    assert captured.value.published_path == destination
    assert progress.read(destination) == candidate


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
    """A child crash preserves the sidecar pointer that crossed commit."""
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
    if boundary in {AFTER_SIDECAR_REPLACE, AFTER_SIDECAR_SYNC}:
        assert progress.read(fixture.destination) == fixture.second
        assert progress.read_checkpoint_generation(fixture.second) == (
            fixture.checkpoint_two,
            fixture.partial_two,
        )
    else:
        assert progress.read(fixture.destination) == fixture.first
        assert progress.read_checkpoint_generation(fixture.first) == (
            fixture.checkpoint_one,
            fixture.partial_one,
        )
    checkpoint_path = Path(fixture.second.checkpoint_path or "")
    partial_path = Path(fixture.second.partial_path or "")
    unpublished_checkpoint = {
        BEFORE_CHECKPOINT_FILE_SYNC,
        BEFORE_CHECKPOINT_PUBLISH,
    }
    if boundary in unpublished_checkpoint:
        assert not checkpoint_path.exists()
    else:
        assert checkpoint_path.read_bytes() == fixture.checkpoint_two
    unpublished_partial = {
        BEFORE_CHECKPOINT_FILE_SYNC,
        BEFORE_CHECKPOINT_PUBLISH,
        AFTER_CHECKPOINT_PUBLISH,
        AFTER_CHECKPOINT_SYNC,
        AFTER_CHECKPOINT,
        BEFORE_PARTIAL_FILE_SYNC,
        BEFORE_PARTIAL_PUBLISH,
    }
    if boundary in unpublished_partial:
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


def test_progress_write_limiter_bounds_routine_publication(
    tmp_path: Path,
) -> None:
    """Routine progress writes respect one explicit monotonic interval."""
    clock = SequenceClock([100, 100, 109, 110, 111])
    limiter = progress.ProgressWriteLimiter.start(10, clock=clock)
    original = _sidecar(tmp_path)
    destination = Path(original.progress_path)
    assert limiter.publish(original) == destination

    boolean_alias = True
    malformed = replace(original, units_completed=cast("int", boolean_alias))
    with pytest.raises(ERROR, match="non-negative integer"):
        _ = limiter.publish(malformed)

    early = replace(
        original,
        active_elapsed_ns=601,
        updated_at="2026-08-06T14:00:03Z",
        units_completed=15,
        wall_elapsed_ns=761,
    )
    assert limiter.publish(early) is None
    assert progress.read(destination) == original

    due = replace(
        early,
        active_elapsed_ns=602,
        updated_at="2026-08-06T14:00:04Z",
        units_completed=16,
        wall_elapsed_ns=762,
    )
    assert limiter.publish(due) == destination
    assert progress.read(destination) == due

    completed = replace(
        due,
        completed_at="2026-08-06T14:00:05Z",
        status=progress.ProgressStatus.COMPLETED,
        updated_at="2026-08-06T14:00:05Z",
    )
    assert limiter.publish(completed) == destination
    assert progress.read(destination) == completed


def test_progress_write_limiter_always_admits_checkpoint(
    tmp_path: Path,
) -> None:
    """Checkpoint evidence bypasses the routine progress interval."""
    checkpoint = b"rate-limited-checkpoint"
    clock = SequenceClock([100, 100, 101])
    limiter = progress.ProgressWriteLimiter.start(10, clock=clock)
    running = _sidecar(tmp_path)
    destination = Path(running.progress_path)
    assert limiter.publish(running) == destination

    checkpointed = _checkpointed(
        running,
        checkpoint=checkpoint,
        partial=None,
    )
    checkpoint_path = Path(checkpointed.checkpoint_path or "")
    _ = checkpoint_path.write_bytes(checkpoint)
    assert limiter.publish(checkpointed) == destination
    assert progress.read(destination) == checkpointed


def test_progress_write_limiter_counts_committed_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-commit failure consumes the routine publication window."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    calls: list[str] = []
    committed_failure = progress.ProgressSidecarDurabilityError(
        "injected committed write failure",
        destination,
    )

    def commit_then_fail(sidecar: progress.ProgressSidecar) -> Path:
        del sidecar
        calls.append("committed")
        raise committed_failure

    limiter = progress.ProgressWriteLimiter.start(
        10,
        clock=SequenceClock([0, 0, 1]),
    )
    with monkeypatch.context() as context:
        context.setattr(progress, "write_atomic", commit_then_fail)
        with pytest.raises(
            progress.ProgressSidecarDurabilityError,
            match="injected committed write failure",
        ):
            _ = limiter.publish(candidate)
        assert limiter.publish(candidate) is None
    assert calls == ["committed"]


def test_progress_write_limiter_retries_prepublication_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prepublication failure does not consume the routine write window."""
    candidate = _sidecar(tmp_path)
    destination = Path(candidate.progress_path)
    failure_message = "injected prepublication failure"
    expected_attempts = 2
    attempts = 0

    def fail_before_commit(sidecar: progress.ProgressSidecar) -> Path:
        nonlocal attempts
        del sidecar
        attempts += 1
        if attempts == 1:
            raise progress.ProgressSidecarError(failure_message)
        return destination

    limiter = progress.ProgressWriteLimiter.start(
        10,
        clock=SequenceClock([20, 20, 21]),
    )
    with monkeypatch.context() as context:
        context.setattr(progress, "write_atomic", fail_before_commit)
        with pytest.raises(ERROR, match=failure_message):
            _ = limiter.publish(candidate)
        assert limiter.publish(candidate) == destination
    assert attempts == expected_attempts


def test_progress_write_limiter_fails_closed_on_invalid_timing(
    tmp_path: Path,
) -> None:
    """Cadence configuration and monotonic samples reject invalid values."""
    for interval in (0, -1, True):
        with pytest.raises(ERROR, match="positive integer"):
            _ = progress.ProgressWriteLimiter.start(
                cast("int", interval),
                clock=SequenceClock([0]),
            )

    candidate = _sidecar(tmp_path)
    limiter = progress.ProgressWriteLimiter.start(
        10,
        clock=SequenceClock([100, 99]),
    )
    with pytest.raises(ERROR, match="monotonic clock moved backward"):
        _ = limiter.publish(candidate)

    corrupt_interval = progress.ProgressWriteLimiter(
        _clock=SequenceClock([0]),
        _minimum_interval_ns=0,
        _started_ns=0,
    )
    with pytest.raises(ERROR, match="positive integer"):
        _ = corrupt_interval.publish(candidate)

    corrupt_commit = progress.ProgressWriteLimiter(
        _clock=SequenceClock([10]),
        _minimum_interval_ns=10,
        _started_ns=10,
        _last_committed_write_ns=9,
    )
    with pytest.raises(ERROR, match="precedes limiter start"):
        _ = corrupt_commit.publish(candidate)


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
