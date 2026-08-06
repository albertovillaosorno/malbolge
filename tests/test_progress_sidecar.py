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
from typing import Protocol
from typing import cast

import pytest
from scripts import progress_sidecar as progress

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
CRASH_EXIT = 73
AFTER_CHECKPOINT = "after-checkpoint"
BEFORE_SIDECAR = "before-sidecar"
CRASH_BOUNDARIES = (AFTER_CHECKPOINT, BEFORE_SIDECAR)
CHECKPOINT_BEFORE_CRASH = b"checkpoint-before-crash"
PARTIAL_BEFORE_CRASH = b"partial-before-crash"
CHECKPOINT_AFTER_CRASH = b"checkpoint-after-crash"
PARTIAL_AFTER_CRASH = b"partial-after-crash"
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


def test_paths_and_resume_identity_are_backend_neutral(tmp_path: Path) -> None:
    """Generation paths are predictable and devices are not resume identity."""
    sidecar = _sidecar(tmp_path)
    output = tmp_path / "program.malbolge"
    assert progress.progress_path(output).name == PROGRESS_NAME
    assert progress.checkpoint_path(output, 1).name == CHECKPOINT_NAME
    assert progress.partial_path(output, 1).name == PARTIAL_NAME
    with pytest.raises(ERROR, match="sequence must be positive"):
        _ = progress.checkpoint_path(output, 0)
    with pytest.raises(ERROR, match="sequence must be positive"):
        _ = progress.partial_path(output, -1)
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


def test_monotonic_timer_rejects_backward_or_negative_clocks() -> None:
    """Invalid clock sources fail before corrupting elapsed-time evidence."""
    with pytest.raises(ERROR, match="negative"):
        _ = progress.ProgressTimer.start(clock=SequenceClock([-1]))

    timer = progress.ProgressTimer.start(clock=SequenceClock([100, 99]))
    with pytest.raises(ERROR, match="moved backward"):
        _ = timer.snapshot()
