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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic tests for in-memory compatible tree planning.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for in-memory compatible tree planning."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import shutil
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import compatible as compatible_module
from algorithms.diff.admission import AdmissionError
from algorithms.diff.admission import AdmissionPolicy
from algorithms.diff.admission import identity_tree
from algorithms.diff.behavior import BehaviorEvidence
from algorithms.diff.compatible import CompatibleBuildRequest
from algorithms.diff.compatible import CompatibleFileKind
from algorithms.diff.compatible import CompatibleInstruction
from algorithms.diff.compatible import CompatibleMaterializeRequest
from algorithms.diff.compatible import CompatiblePlanError
from algorithms.diff.compatible import build_compatible_plan
from algorithms.diff.compatible import materialize_compatible_plan
from algorithms.diff.mapped import MappedUnit
from algorithms.diff.mapped import MappedView
from algorithms.diff.model import ExactInstruction
from algorithms.diff.model import ExactInstructionKind
import pytest

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.compatible import CompatibleAuthoringPlan
    from algorithms.diff.compatible import Mapper
    from algorithms.diff.compatible import Postcondition

_TOKEN = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]")
_SOURCE_CODE = b"alpha = old ; omega"
_TARGET_CODE = b"alpha = new ; omega"
_LINEAGE = b"stable-lineage-evidence" * 8
_BLOB = b"opaque-stable"
_CREATED = b"created-target"
_REMOVED = b"historical-remove"
_CANDIDATE_ONLY = b"candidate-only"
_CANDIDATE_CODE = b"extra ; alpha   = old ; omega tail"
_EXPECTED_CODE = b"extra ; alpha   = new ; omega tail"
_FOREIGN_OUTPUT = b"foreign-output"
_FOREIGN_STAGING = b"foreign-writer"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, path: str, data: bytes) -> None:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_bytes(data)


def _map_bytes(raw: bytes) -> MappedView:
    return MappedView(
        raw=raw,
        units=tuple(
            MappedUnit(match.group(0), match.start(), match.end())
            for match in _TOKEN.finditer(raw)
        ),
    )


def _mapper(path: str, raw: bytes) -> MappedView | None:
    return _map_bytes(raw) if path.endswith(".src") else None


def _identity(root: Path) -> IdentityTree:
    lineage = (root / "identity.txt").read_bytes()
    return identity_tree({"identity.txt": lineage})


def _policy() -> AdmissionPolicy:
    return AdmissionPolicy(
        minimum_source_similarity=0.40,
        minimum_anchor_coverage=0.40,
        minimum_anchor_files=1,
        minimum_anchors_per_file=1,
    )


def _behavior(
    *, admitted: bool = True, routed: bool = False
) -> BehaviorEvidence:
    return BehaviorEvidence(
        similarity=1.0 if admitted else 0.0,
        matched_identity_probes=1 if admitted else 0,
        total_identity_probes=1,
        corrections_to_apply=("fix",) if routed else (),
        corrections_to_skip=(),
        reasons=() if admitted else ("synthetic behavior rejection",),
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    _write(source, "code.src", _SOURCE_CODE)
    _write(source, "identity.txt", _LINEAGE)
    _write(source, "blob.bin", _BLOB)
    _write(source, "removed.cfg", _REMOVED)
    _write(oracle, "code.src", _TARGET_CODE)
    _write(oracle, "identity.txt", _LINEAGE)
    _write(oracle, "blob.bin", _BLOB)
    _write(oracle, "created.bin", _CREATED)
    return source, oracle


def _plan(tmp_path: Path) -> CompatibleAuthoringPlan:
    source, oracle = _roots(tmp_path)
    return build_compatible_plan(
        CompatibleBuildRequest(
            source_root=source,
            oracle_root=oracle,
            reference_identity=_identity(source),
            admission_policy=_policy(),
            mapper=_mapper,
        )
    )


def _candidate(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate"
    _write(candidate, "code.src", _CANDIDATE_CODE)
    _write(candidate, "identity.txt", _LINEAGE)
    _write(candidate, "blob.bin", _BLOB)
    _write(candidate, "removed.cfg", _REMOVED)
    _write(candidate, "upstream.cfg", _CANDIDATE_ONLY)
    return candidate


def _request(
    candidate: Path,
    plan: CompatibleAuthoringPlan,
    output: Path,
    *,
    behavior: BehaviorEvidence | None = None,
) -> CompatibleMaterializeRequest:
    return CompatibleMaterializeRequest(
        candidate_root=candidate,
        candidate_identity=_identity(candidate),
        behavior=behavior or _behavior(),
        plan=plan,
        mapper=_mapper,
        output_root=output,
    )


def test_compatible_instruction_rejects_foreign_metadata() -> None:
    """Reject malformed direct instruction evidence at construction time."""
    with pytest.raises(CompatiblePlanError, match="output path"):
        _ = CompatibleInstruction(
            output_path=cast("str", 1),
            kind=CompatibleFileKind.COPY_CANDIDATE,
            source_path="file.bin",
        )
    with pytest.raises(CompatiblePlanError, match="exact enum type"):
        _ = CompatibleInstruction(
            output_path="file.bin",
            kind=cast("CompatibleFileKind", "copy-candidate"),
            source_path="file.bin",
        )
    with pytest.raises(CompatiblePlanError, match="unsafe compatible tree path"):
        _ = CompatibleInstruction(
            output_path="file.bin",
            kind=CompatibleFileKind.COPY_CANDIDATE,
            source_path="../file.bin",
        )

    exact = ExactInstruction(
        output_path="file.bin",
        kind=ExactInstructionKind.COPY_SOURCE,
        expected_sha256="0" * 64,
        source_path="file.bin",
    )
    with pytest.raises(CompatiblePlanError, match="64 lowercase hex digits"):
        _ = CompatibleInstruction(
            output_path="file.bin",
            kind=CompatibleFileKind.EXACT_GATED,
            source_path="file.bin",
            source_sha256="A" * 64,
            exact=exact,
        )
    with pytest.raises(CompatiblePlanError, match="exact bytes"):
        _ = CompatibleInstruction(
            output_path="created.bin",
            kind=CompatibleFileKind.CREATE_LITERAL,
            literal=cast("bytes", bytearray(b"created")),
        )



def test_compatible_request_envelopes_reject_foreign_fields(
    tmp_path: Path,
) -> None:
    """Reject malformed request fields before filesystem or admission work."""
    source, oracle = _roots(tmp_path)
    reference = _identity(source)
    policy = _policy()
    with pytest.raises(CompatiblePlanError, match="source root.*Path"):
        _ = CompatibleBuildRequest(
            source_root=cast("Path", "source"),
            oracle_root=oracle,
            reference_identity=reference,
            admission_policy=policy,
            mapper=_mapper,
        )
    with pytest.raises(CompatiblePlanError, match="mapper must be callable"):
        _ = CompatibleBuildRequest(
            source_root=source,
            oracle_root=oracle,
            reference_identity=reference,
            admission_policy=policy,
            mapper=cast("Mapper", object()),
        )
    with pytest.raises(CompatiblePlanError, match="exact boolean"):
        _ = CompatibleBuildRequest(
            source_root=source,
            oracle_root=oracle,
            reference_identity=reference,
            admission_policy=policy,
            mapper=_mapper,
            preserve_candidate_only=cast("bool", 1),
        )

    plan = _plan(tmp_path / "materialize")
    candidate = _candidate(tmp_path / "materialize")
    output = tmp_path / "materialize" / "out"
    request = _request(candidate, plan, output)
    with pytest.raises(CompatiblePlanError, match="behavior evidence"):
        _ = replace(request, behavior=cast("BehaviorEvidence", object()))
    with pytest.raises(CompatiblePlanError, match="exact CompatibleAuthoringPlan"):
        _ = replace(request, plan=cast("CompatibleAuthoringPlan", object()))
    with pytest.raises(CompatiblePlanError, match="postcondition"):
        _ = replace(request, postcondition=cast("Postcondition", object()))

def test_compatible_public_apis_reject_foreign_request_records(
    tmp_path: Path,
) -> None:
    """Reject foreign request objects before compatible filesystem work."""
    with pytest.raises(
        CompatiblePlanError, match="exact CompatibleBuildRequest"
    ):
        _ = build_compatible_plan(cast("CompatibleBuildRequest", object()))

    output = tmp_path / "out"
    with pytest.raises(
        CompatiblePlanError, match="exact CompatibleMaterializeRequest"
    ):
        _ = materialize_compatible_plan(
            cast("CompatibleMaterializeRequest", object())
        )
    _expect(not output.exists(), "foreign materialize request wrote output")



def test_compatible_plan_rejects_forged_topology_and_bindings(
    tmp_path: Path,
) -> None:
    """Keep target topology and exact evidence bound to plan snapshots."""
    plan = _plan(tmp_path)
    with pytest.raises(CompatiblePlanError, match="exactly cover target paths"):
        _ = replace(plan, instructions=plan.instructions[:-1])
    with pytest.raises(CompatiblePlanError, match="exact boolean"):
        _ = replace(plan, preserve_candidate_only=cast("bool", 1))

    exact_index = next(
        index
        for index, instruction in enumerate(plan.instructions)
        if instruction.kind is CompatibleFileKind.EXACT_GATED
    )
    exact = plan.instructions[exact_index]
    forged_exact = replace(exact, source_sha256="f" * 64)
    forged_instructions = list(plan.instructions)
    forged_instructions[exact_index] = forged_exact
    with pytest.raises(CompatiblePlanError, match="plan source hash"):
        _ = replace(plan, instructions=tuple(forged_instructions))

    literal_index = next(
        index
        for index, instruction in enumerate(plan.instructions)
        if instruction.kind is CompatibleFileKind.CREATE_LITERAL
    )
    literal = plan.instructions[literal_index]
    forged_literal = replace(literal, literal=b"forged target")
    forged_instructions = list(plan.instructions)
    forged_instructions[literal_index] = forged_literal
    with pytest.raises(CompatiblePlanError, match="target snapshot"):
        _ = replace(plan, instructions=tuple(forged_instructions))

def test_compatible_tree_preserves_candidate_and_target_topology(
    tmp_path: Path,
) -> None:
    """Apply semantic target changes while preserving candidate differences."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"

    evidence = materialize_compatible_plan(_request(candidate, plan, output))

    _expect(evidence.admitted, "compatible candidate was not admitted")
    _expect(
        (output / "code.src").read_bytes() == _EXPECTED_CODE, "code changed"
    )
    _expect((output / "blob.bin").read_bytes() == _BLOB, "opaque file changed")
    _expect((output / "created.bin").read_bytes() == _CREATED, "create failed")
    _expect(
        (output / "upstream.cfg").read_bytes() == _CANDIDATE_ONLY,
        "candidate-only file was lost",
    )
    _expect(
        not (output / "removed.cfg").exists(), "historical removal was undone"
    )


def test_source_or_behavior_rejection_happens_before_output(
    tmp_path: Path,
) -> None:
    """Require both independent admission families before creating staging."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    bad_identity = identity_tree({"identity.txt": b"unrelated"})
    lineage_request = _request(candidate, plan, output)
    lineage_request = CompatibleMaterializeRequest(
        candidate_root=lineage_request.candidate_root,
        candidate_identity=bad_identity,
        behavior=lineage_request.behavior,
        plan=lineage_request.plan,
        mapper=lineage_request.mapper,
        output_root=lineage_request.output_root,
    )

    with pytest.raises(AdmissionError, match="source lineage admission failed"):
        _ = materialize_compatible_plan(lineage_request)
    _expect(not output.exists(), "lineage-rejected output exists")

    with pytest.raises(AdmissionError, match="behavior admission failed"):
        _ = materialize_compatible_plan(
            _request(
                candidate, plan, output, behavior=_behavior(admitted=False)
            )
        )
    _expect(not output.exists(), "behavior-rejected output exists")


def test_opaque_candidate_change_fails_exact_gate(tmp_path: Path) -> None:
    """Reject changes to files outside semantic mapper coverage."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    _write(candidate, "blob.bin", b"opaque-upstream-change")
    output = tmp_path / "out"

    with pytest.raises(
        CompatiblePlanError, match="opaque compatible source changed"
    ):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "opaque-rejected output was published")


def test_compatible_materialization_wraps_path_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep path resolution failures inside compatible materialization."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    blocked = candidate / "blob.bin"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == blocked:
            message = "blocked compatible path"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    output = tmp_path / "out"
    with pytest.raises(CompatiblePlanError, match="path resolution failed"):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "resolution failure published output")


def test_compatible_cleanup_failure_preserves_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup failure augments rather than replaces the staging write error."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    blocked = tmp_path / ".out.compatible-staging" / "created.bin"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked compatible write"
            raise PermissionError(message)
        return original_write(path, data)

    def fail_cleanup(path: Path) -> None:
        _ = path
        message = "blocked compatible cleanup"
        raise PermissionError(message)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        CompatiblePlanError,
        match=r"instruction output write failed.*staging cleanup failed",
    ):
        _ = materialize_compatible_plan(_request(candidate, plan, output))


def test_compatible_staging_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible staging path cannot masquerade as absent."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    staging = tmp_path / ".out.compatible-staging"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == staging:
            message = "blocked compatible staging status"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(CompatiblePlanError, match="staging root status failed"):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "status failure published compatible output")


def test_compatible_output_write_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staging write failure remains inside CompatiblePlanError."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    blocked = tmp_path / ".out.compatible-staging" / "created.bin"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked compatible output write"
            raise PermissionError(message)
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with pytest.raises(
        CompatiblePlanError,
        match="compatible instruction output write failed",
    ):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "write failure published compatible output")
    _expect(
        not (tmp_path / ".out.compatible-staging").exists(),
        "compatible staging survived write failure",
    )


def test_target_only_path_conflict_fails_closed(tmp_path: Path) -> None:
    """Reject upstream conflict with required target-only material."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    _write(candidate, "created.bin", b"upstream-conflict")
    output = tmp_path / "out"

    with pytest.raises(CompatiblePlanError, match="conflicts"):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "conflicting target-only output was published")


def test_bug_routing_fails_closed_until_edits_are_named(tmp_path: Path) -> None:
    """Reject apply/skip routing until correction IDs are attached to edits."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"

    with pytest.raises(CompatiblePlanError, match="routing is not wired"):
        _ = materialize_compatible_plan(
            _request(candidate, plan, output, behavior=_behavior(routed=True))
        )
    _expect(not output.exists(), "unwired bug routing published output")


def _reject_postcondition(root: Path) -> bool:
    return not root.name


def test_existing_compatible_staging_is_preserved(tmp_path: Path) -> None:
    """Never delete a staging tree that may belong to another writer."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    staging = tmp_path / ".out.compatible-staging"
    _write(staging, "owner.txt", _FOREIGN_STAGING)

    with pytest.raises(
        CompatiblePlanError, match="staging root already exists"
    ):
        _ = materialize_compatible_plan(_request(candidate, plan, output))
    _expect(
        (staging / "owner.txt").read_bytes() == _FOREIGN_STAGING,
        "preexisting compatible staging was modified",
    )
    _expect(not output.exists(), "staging conflict published output")


def test_compatible_publication_collision_preserves_foreign_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late destination race cannot be replaced by compatible output."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"

    def collide(staging: Path, destination: Path) -> None:
        _ = staging
        destination.mkdir()
        _ = (destination / "foreign.txt").write_bytes(_FOREIGN_OUTPUT)
        raise FileExistsError(destination)

    monkeypatch.setattr(
        compatible_module, "publish_directory_no_replace", collide
    )
    with pytest.raises(CompatiblePlanError, match="output publication failed"):
        _ = materialize_compatible_plan(_request(candidate, plan, output))

    assert (output / "foreign.txt").read_bytes() == _FOREIGN_OUTPUT
    assert not (tmp_path / ".out.compatible-staging").exists()


def test_postcondition_rejects_staging_before_publish(tmp_path: Path) -> None:
    """Keep downstream quality validation inside the transactional boundary."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"
    request = _request(candidate, plan, output)
    request = CompatibleMaterializeRequest(
        candidate_root=request.candidate_root,
        candidate_identity=request.candidate_identity,
        behavior=request.behavior,
        plan=request.plan,
        mapper=request.mapper,
        output_root=request.output_root,
        postcondition=_reject_postcondition,
    )

    with pytest.raises(CompatiblePlanError, match="postcondition"):
        _ = materialize_compatible_plan(request)
    _expect(not output.exists(), "postcondition-rejected output was published")
