# File:
#   - test_admission.py
# Path:
#   - algorithms/diff/tests/test_admission.py
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
#   - Tests for tree-level structural and distributed-anchor admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Tests for tree-level structural and distributed-anchor admission."""

import hashlib
import math
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.admission import AdmissionError
from algorithms.diff.admission import AdmissionPolicy
from algorithms.diff.admission import evaluate_admission
from algorithms.diff.admission import identity_tree
from algorithms.diff.admission import require_admission

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityTree

_FILE_COUNT = 4
_BLOCKS_PER_FILE = 128
_INSERTION = b"compatible insertion"
_MINIMUM_ANCHOR_FILES = 3
_MINIMUM_ANCHORS_PER_FILE = 2
_DISTRIBUTION_REASON = "stable-anchor evidence is not sufficiently distributed"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _content(label: str, file_index: int) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{file_index}:{block}".encode()).digest()
        for block in range(_BLOCKS_PER_FILE)
    )


def _reference_files() -> dict[str, bytes]:
    return {
        f"src/file-{index}.txt": _content("reference", index)
        for index in range(_FILE_COUNT)
    }


def _policy(
    *,
    source_similarity: float = 0.50,
    anchor_coverage: float = 0.66,
) -> AdmissionPolicy:
    return AdmissionPolicy(
        minimum_source_similarity=source_similarity,
        minimum_anchor_coverage=anchor_coverage,
        minimum_anchor_files=_MINIMUM_ANCHOR_FILES,
        minimum_anchors_per_file=_MINIMUM_ANCHORS_PER_FILE,
    )


def _candidate_with_first_insertion() -> tuple[IdentityTree, IdentityTree]:
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    first_path = min(candidate_files)
    content = candidate_files[first_path]
    midpoint = len(content) // 2
    candidate_files[first_path] = (
        content[:midpoint] + _INSERTION + content[midpoint:]
    )
    return identity_tree(reference_files), identity_tree(candidate_files)


def test_exact_identity_tree_is_admitted() -> None:
    """Exact source lineage satisfies both independent source metrics."""
    files = _reference_files()
    evidence = require_admission(
        identity_tree(files), identity_tree(files), _policy()
    )
    _expect(
        math.isclose(evidence.source_similarity, 1.0),
        "exact structural score changed",
    )
    _expect(
        math.isclose(evidence.anchor_coverage, 1.0),
        "exact anchor score changed",
    )
    _expect(
        evidence.satisfied_anchor_files == _FILE_COUNT,
        "files not distributed",
    )


def test_compatible_insertions_preserve_distributed_evidence() -> None:
    """Keep distributed evidence across offset-shifting insertions."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    for path, content in tuple(candidate_files.items()):
        midpoint = len(content) // 2
        candidate_files[path] = (
            content[:midpoint] + _INSERTION + content[midpoint:]
        )
    evidence = require_admission(
        identity_tree(reference_files),
        identity_tree(candidate_files),
        _policy(),
    )
    _expect(evidence.source_similarity < 1.0, "insertion looked byte-exact")
    _expect(evidence.anchor_coverage < 1.0, "insertion kept every anchor")
    _expect(evidence.admitted, "compatible insertion was rejected")


def test_unrelated_source_fails_closed() -> None:
    """Same paths and sizes cannot replace structural source lineage."""
    reference = identity_tree(_reference_files())
    unrelated = identity_tree({
        f"src/file-{index}.txt": _content("unrelated", index)
        for index in range(_FILE_COUNT)
    })
    with pytest.raises(AdmissionError, match="structural source similarity"):
        _ = require_admission(reference, unrelated, _policy())


def test_structural_threshold_boundary_is_fail_closed() -> None:
    """Reject the next representable threshold above measured similarity."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    candidate_files[min(candidate_files)] = _content("different", 0)
    reference = identity_tree(reference_files)
    candidate = identity_tree(candidate_files)
    baseline = evaluate_admission(
        reference, candidate, _policy(source_similarity=0.0)
    )
    below = math.nextafter(baseline.source_similarity, 0.0)
    above = math.nextafter(baseline.source_similarity, 1.0)
    passing = evaluate_admission(
        reference, candidate, _policy(source_similarity=below)
    )
    failing = evaluate_admission(
        reference, candidate, _policy(source_similarity=above)
    )
    _expect(passing.admitted, "threshold immediately below score rejected")
    _expect(not failing.admitted, "threshold immediately above score admitted")


def test_anchor_threshold_boundary_is_fail_closed() -> None:
    """Change acceptance exactly across the measured anchor boundary."""
    reference, candidate = _candidate_with_first_insertion()
    baseline = evaluate_admission(
        reference,
        candidate,
        _policy(anchor_coverage=0.0),
    )
    below = math.nextafter(baseline.anchor_coverage, 0.0)
    above = math.nextafter(baseline.anchor_coverage, 1.0)
    passing = evaluate_admission(
        reference, candidate, _policy(anchor_coverage=below)
    )
    failing = evaluate_admission(
        reference, candidate, _policy(anchor_coverage=above)
    )
    _expect(passing.admitted, "threshold immediately below coverage rejected")
    _expect(
        not failing.admitted,
        "threshold immediately above coverage admitted",
    )


def test_anchor_distribution_rejects_single_file_concentration() -> None:
    """Reject one strong file as evidence for a multi-file identity."""
    reference_files = _reference_files()
    first_path = min(reference_files)
    candidate_files = {first_path: reference_files[first_path]}
    evidence = evaluate_admission(
        identity_tree(reference_files),
        identity_tree(candidate_files),
        _policy(source_similarity=0.0, anchor_coverage=0.0),
    )
    _expect(not evidence.admitted, "single-file evidence admitted whole tree")
    _expect(
        _DISTRIBUTION_REASON in evidence.reasons,
        "distribution rejection reason is missing",
    )


def test_opaque_asset_size_cannot_dominate_explicit_identity_view() -> None:
    """Ignore candidate-only opaque size in reference-driven aggregation."""
    reference_files = _reference_files()
    candidate_files = dict(reference_files)
    candidate_files[min(candidate_files)] = _content("different", 0)
    reference = identity_tree(reference_files)
    policy = _policy(source_similarity=0.0)
    baseline = evaluate_admission(
        reference,
        identity_tree(candidate_files),
        policy,
    )
    candidate_files["data/opaque.bin"] = b"opaque" * 1_000_000
    with_asset = evaluate_admission(
        reference,
        identity_tree(candidate_files),
        policy,
    )
    _expect(
        baseline == with_asset, "candidate-only asset changed source evidence"
    )
    _expect(len(with_asset.files) == _FILE_COUNT, "asset changed identity size")
