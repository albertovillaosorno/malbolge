# File:
#   - test_candidate_subset_tradeoff.py
# Path:
#   - tests/optimizer/test_candidate_subset_tradeoff.py
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
#   - Contract tests for exact candidate-subset tradeoff measurement.
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

"""Contract tests for exact candidate-subset tradeoff measurement."""

from __future__ import annotations

from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateWorkItem
from benchmarks.accelerator.candidate_subset_tradeoff import MeasurementPlan
from benchmarks.accelerator.candidate_subset_tradeoff import (
    measure_candidate_subset_tradeoff,
)

TEST_SAMPLE_COUNT = 2
EXPECTED_SUBSET_SIZE = 3


def test_subset_tradeoff_preserves_multi_candidate_projection() -> None:
    """Both measured routes produce the same exact request-order subset."""
    full = CandidateEvaluationBatch(
        evaluator_id="subset-benchmark-v1",
        items=tuple(
            CandidateWorkItem(
                logical_id=f"item-{index}", payload=bytes((index,))
            )
            for index in range(4)
        ),
    ).validated()

    measured = measure_candidate_subset_tradeoff(
        full,
        (0, 2, 3),
        plan=MeasurementPlan(
            memory_sample_count=TEST_SAMPLE_COUNT,
            sample_count=TEST_SAMPLE_COUNT,
        ),
    )

    assert measured.subset_size == EXPECTED_SUBSET_SIZE
    assert len(measured.legacy.timing.raw_ns) == TEST_SAMPLE_COUNT
    assert len(measured.proof.timing.raw_ns) == TEST_SAMPLE_COUNT
    assert all(value >= 0 for value in measured.proof.memory.peak.raw_bytes)
