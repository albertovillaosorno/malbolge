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
#   - Tests for deterministic content-defined stable anchors.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for deterministic content-defined stable anchors."""

import hashlib

from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.fingerprints import anchor_coverage
from algorithms.diff.fingerprints import stable_anchors

_BLOCK_COUNT = 256
_INSERTION = b"target-only insertion that shifts all later offsets"
_MINIMUM_EXPECTED_COVERAGE = 0.90
_MAXIMUM_UNRELATED_COVERAGE = 0.10


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _synthetic_bytes(label: str) -> bytes:
    blocks = (
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCK_COUNT)
    )
    return b"".join(blocks)


def test_stable_anchors_are_deterministic() -> None:
    """Repeated anchor extraction must produce byte-identical evidence."""
    source = _synthetic_bytes("source")
    first = stable_anchors(source)
    second = stable_anchors(source)
    _expect(first == second, "repeated anchor extraction differs")
    _expect(bool(first), "synthetic source produced no anchors")


def test_content_defined_anchors_survive_insertion_shift() -> None:
    """Insertion offsets may move while unchanged content digests survive."""
    source = _synthetic_bytes("source")
    midpoint = len(source) // 2
    candidate = source[:midpoint] + _INSERTION + source[midpoint:]
    reference_anchors = stable_anchors(source)
    candidate_anchors = stable_anchors(candidate)
    coverage = anchor_coverage(reference_anchors, candidate_anchors)
    _expect(
        coverage.ratio >= _MINIMUM_EXPECTED_COVERAGE,
        "insertion destroyed too many content-defined anchors",
    )


def test_unrelated_content_has_low_anchor_coverage() -> None:
    """Aggregate size alone must not create convincing source lineage."""
    source = _synthetic_bytes("source")
    unrelated = _synthetic_bytes("unrelated")
    coverage = anchor_coverage(
        stable_anchors(source),
        stable_anchors(unrelated),
    )
    _expect(
        coverage.ratio <= _MAXIMUM_UNRELATED_COVERAGE,
        "unrelated content retained too many source anchors",
    )


def test_anchor_policy_controls_sampling_density() -> None:
    """A deterministic denser policy should not yield fewer sampled anchors."""
    source = _synthetic_bytes("source")
    dense = stable_anchors(source, AnchorPolicy(selection_modulus=16))
    sparse = stable_anchors(source, AnchorPolicy(selection_modulus=128))
    _expect(len(dense) >= len(sparse), "denser policy yielded fewer anchors")
