# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Synthetic tests for in-memory compatible tree planning."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.admission import AdmissionError
from algorithms.diff.admission import AdmissionPolicy
from algorithms.diff.admission import identity_tree
from algorithms.diff.behavior import BehaviorEvidence
from algorithms.diff.compatible import CompatibleBuildRequest
from algorithms.diff.compatible import CompatibleMaterializeRequest
from algorithms.diff.compatible import CompatiblePlanError
from algorithms.diff.compatible import build_compatible_plan
from algorithms.diff.compatible import materialize_compatible_plan
from algorithms.diff.mapped import MappedUnit
from algorithms.diff.mapped import MappedView

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.compatible import CompatibleAuthoringPlan

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


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, path: str, data: bytes) -> None:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


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
        materialize_compatible_plan(lineage_request)
    _expect(not output.exists(), "lineage-rejected output exists")

    with pytest.raises(AdmissionError, match="behavior admission failed"):
        materialize_compatible_plan(
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
        materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "opaque-rejected output was published")


def test_target_only_path_conflict_fails_closed(tmp_path: Path) -> None:
    """Reject upstream conflict with required target-only material."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    _write(candidate, "created.bin", b"upstream-conflict")
    output = tmp_path / "out"

    with pytest.raises(CompatiblePlanError, match="conflicts"):
        materialize_compatible_plan(_request(candidate, plan, output))
    _expect(not output.exists(), "conflicting target-only output was published")


def test_bug_routing_fails_closed_until_edits_are_named(tmp_path: Path) -> None:
    """Reject apply/skip routing until correction IDs are attached to edits."""
    plan = _plan(tmp_path)
    candidate = _candidate(tmp_path)
    output = tmp_path / "out"

    with pytest.raises(CompatiblePlanError, match="routing is not wired"):
        materialize_compatible_plan(
            _request(candidate, plan, output, behavior=_behavior(routed=True))
        )
    _expect(not output.exists(), "unwired bug routing published output")


def _reject_postcondition(root: Path) -> bool:
    return not root.name


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
        materialize_compatible_plan(request)
    _expect(not output.exists(), "postcondition-rejected output was published")
