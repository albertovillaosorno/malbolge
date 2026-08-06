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
#   - Progress-sidecar schema, identity, timing, and atomic-write regressions.
# - Must-Not:
#   - Claim compiler or accelerator checkpoint integration exists.
# - Allows:
#   - Inputs: temporary output paths and immutable sidecar fixtures.
#   - Outputs: exact acceptance/rejection and persistence assertions.
#   - Side effects: temporary sidecar writes only.
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
#   - Invalid or torn state is rejected before persistence.
#

"""Progress-sidecar reference contract regressions."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest
from scripts import progress_sidecar as progress

SOURCE_HASH = "sha256:" + ("1" * 64)
TOOLCHAIN_HASH = "sha256:" + ("2" * 64)
PROFILE_HASH = "malbolge-profile-v1:sha256:" + ("3" * 64)
CHECKPOINT_HASH = "sha256:" + ("4" * 64)
PARTIAL_HASH = "sha256:" + ("5" * 64)
STARTED = "2026-08-06T14:00:00Z"
UPDATED = "2026-08-06T14:00:01Z"
COMPLETED = "2026-08-06T14:00:02Z"
ERROR = progress.ProgressSidecarError
PARTIAL_NAME = "program.malbolge.partial"
SCHEMA_FIELD = '"schema":"malbolge-progress-v1"'


def _sidecar(
    tmp_path: Path,
    *,
    status: progress.ProgressStatus = progress.ProgressStatus.RUNNING,
) -> progress.ProgressSidecar:
    output = tmp_path / "program.malbolge"
    identity = progress.ResumeIdentity(
        algorithm_id="search.enumerative",
        algorithm_version="1",
        schema=progress.SCHEMA_ID,
        seed=7,
        source_sha256=SOURCE_HASH,
        target_profile_fingerprint=PROFILE_HASH,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=TOOLCHAIN_HASH,
    )
    compatibility = progress.resume_compatibility_fingerprint(identity)
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
        compatibility_fingerprint=compatibility,
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
        wall_elapsed_ns=1_000,
    )


def test_paths_and_resume_identity_are_backend_neutral(tmp_path: Path) -> None:
    """Paths are predictable and devices are not resume identity."""
    sidecar = _sidecar(tmp_path)
    output = tmp_path / "program.malbolge"
    progress_name = "program.malbolge.progress.json"
    checkpoint_name = "program.malbolge.checkpoint"
    assert progress.progress_path(output).name == progress_name
    assert progress.checkpoint_path(output).name == checkpoint_name
    assert progress.partial_path(output).name == PARTIAL_NAME
    assert sidecar.compatibility_fingerprint == (
        progress.resume_compatibility_fingerprint(
            progress.ResumeIdentity(
                algorithm_id=sidecar.algorithm_id,
                algorithm_version=sidecar.algorithm_version,
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
        wall_elapsed_ns=1_200,
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
    duplicate = text.replace(
        '"schema":"malbolge-progress-v1"',
        duplicate_schema,
        1,
    )
    with pytest.raises(ERROR, match="duplicate"):
        _ = progress.loads(duplicate)

    document = progress.to_document(sidecar)
    document["future_field"] = True
    with pytest.raises(ERROR, match="unknown"):
        _ = progress.loads(json.dumps(document))


def test_impossible_timing_and_units_fail(tmp_path: Path) -> None:
    """Impossible counters or elapsed-time partitions are rejected."""
    sidecar = _sidecar(tmp_path)
    invalid_units = replace(sidecar, units_completed=2, units_total=1)
    with pytest.raises(ERROR, match="units_completed"):
        _ = progress.validate(invalid_units)
    with pytest.raises(ERROR, match="active plus paused"):
        _ = progress.validate(
            replace(
                sidecar,
                active_elapsed_ns=800,
                paused_elapsed_ns=300,
            )
        )
    stale_time = replace(sidecar, updated_at="2026-08-06T13:59:59Z")
    with pytest.raises(ERROR, match="precedes"):
        _ = progress.validate(stale_time)


def test_resume_identity_mismatch_fails(tmp_path: Path) -> None:
    """A changed source/profile/toolchain identity cannot reuse a checkpoint."""
    sidecar = _sidecar(tmp_path)
    stale = replace(sidecar, source_sha256="sha256:" + ("9" * 64))
    with pytest.raises(ERROR, match="fingerprint mismatch"):
        _ = progress.write_atomic(stale)
    assert not Path(stale.progress_path).exists()


def test_checkpoint_and_partial_members_are_atomic(tmp_path: Path) -> None:
    """Torn checkpoint or partial metadata is never admitted."""
    sidecar = _sidecar(tmp_path)
    checkpoint = str(progress.checkpoint_path(sidecar.output_path))
    partial = str(progress.partial_path(sidecar.output_path))
    with pytest.raises(ERROR, match="checkpoint path/hash"):
        _ = progress.validate(
            replace(
                sidecar,
                checkpoint_path=checkpoint,
                checkpoint_sequence=1,
            )
        )
    torn = replace(sidecar, partial_bytes=7, partial_path=partial)
    with pytest.raises(ERROR, match="partial path/bytes"):
        _ = progress.validate(torn)

    checkpointed = replace(
        sidecar,
        checkpoint_path=checkpoint,
        checkpoint_sequence=1,
        checkpoint_sha256=CHECKPOINT_HASH,
        partial_bytes=7,
        partial_path=partial,
        partial_sha256=PARTIAL_HASH,
        status=progress.ProgressStatus.CHECKPOINTED,
    )
    assert progress.validate(checkpointed) == checkpointed


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

    completed = _sidecar(tmp_path, status=progress.ProgressStatus.COMPLETED)
    with pytest.raises(ERROR, match="partial artifact"):
        _ = progress.validate(
            replace(
                completed,
                partial_bytes=7,
                partial_path=str(progress.partial_path(completed.output_path)),
                partial_sha256=PARTIAL_HASH,
            )
        )
