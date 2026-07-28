# File:
#   - test_search_preparation_crossover.py
# Path:
#   - tests/optimizer/test_search_preparation_crossover.py
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
#   - Correctness checks for prepared-search crossover benchmark logic.
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

"""Correctness checks for prepared-search crossover benchmark logic."""

from __future__ import annotations

from accelerator.exact_primitives import prepared_primitive_storage_id
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import indexed_candidate_items_id
from benchmarks.accelerator.search_preparation_crossover import CORPUS_SIZES
from benchmarks.accelerator.search_preparation_crossover import (
    MembershipMeasurementPlan,
)
from benchmarks.accelerator.search_preparation_crossover import (
    build_scale_workload,
)
from benchmarks.accelerator.search_preparation_crossover import (
    measure_membership_index_comparison,
)
from benchmarks.accelerator.search_preparation_crossover import (
    preparation_crossover_runs,
)
from benchmarks.accelerator.search_preparation_crossover import (
    validate_prepared_scale,
)
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_batch_builder_id

EXPECTED_CANDIDATE_ITEMS_ID = "u32-index-fixed-width-payloads-rotation-v1"
EXPECTED_PREPARED_PRIMITIVE_STORAGE_ID = "proof-bound-u32le-primitive-input-v1"
EXPECTED_BATCH_BUILDER_ID = "classic-u32le-bitset-first-representatives-v1"
EXPECTED_CROSSOVER_RUNS = 5
TEST_LOOKUP_ITERATIONS = 8
TEST_SAMPLE_COUNT = 2


def test_strict_crossover_requires_first_profitable_run() -> None:
    """Exact equality at four runs crosses only on the fifth run."""
    runs = preparation_crossover_runs(
        preparation_ns=8,
        first_build_ns=10,
        reuse_ns=2,
        ordinary_ns=6,
    )

    assert runs == EXPECTED_CROSSOVER_RUNS
    assert 8 + 10 + ((runs - 1) * 2) < runs * 6
    previous = runs - 1
    assert 8 + 10 + ((previous - 1) * 2) >= previous * 6


def test_crossover_handles_immediate_and_impossible_cases() -> None:
    """Immediate and impossible crossover cases remain explicit."""
    assert (
        preparation_crossover_runs(
            preparation_ns=0,
            first_build_ns=1,
            reuse_ns=2,
            ordinary_ns=6,
        )
        == 1
    )
    assert (
        preparation_crossover_runs(
            preparation_ns=10,
            first_build_ns=10,
            reuse_ns=6,
            ordinary_ns=6,
        )
        is None
    )


def test_scale_workloads_keep_one_exact_admissible_candidate() -> None:
    """Every measured size retains one canonical rotate preimage proposal."""
    for size in CORPUS_SIZES:
        workload = build_scale_workload(size)
        problem = RotateTargetProblem.decode(workload.problem)
        expected_id = "corpus-0" if size == 1 else "corpus-1"

        assert len(problem.candidates) == size
        assert 1 in problem.candidates
        assert workload.expected == (
            CandidateProposal(
                logical_id=expected_id,
                payload=(1).to_bytes(4, "little"),
            ),
        )


def test_benchmark_uses_packed_rotate_batch_builder_identity() -> None:
    """Protocol identity tracks packed first-representative construction."""
    assert rotate_target_batch_builder_id() == EXPECTED_BATCH_BUILDER_ID


def test_benchmark_uses_packed_prepared_primitive_identity() -> None:
    """Protocol identity tracks proof-bound packed primitive input."""
    assert (
        prepared_primitive_storage_id()
        == EXPECTED_PREPARED_PRIMITIVE_STORAGE_ID
    )


def test_benchmark_uses_indexed_candidate_storage_identity() -> None:
    """Protocol identity tracks the active fixed-width candidate store."""
    assert indexed_candidate_items_id() == EXPECTED_CANDIDATE_ITEMS_ID


def test_prepared_scale_proofs_match_candidate_count() -> None:
    """Reference, membership, and selector proofs bind the measured size."""
    size = 64
    workload = build_scale_workload(size)
    adapter = cpu_rotate_target_search_adapter()
    prepared = adapter.prepare(workload.request)

    assert validate_prepared_scale(adapter, prepared, size) == (size, size, 1)


def test_membership_comparison_preserves_exact_hit_and_miss() -> None:
    """Component benchmark validates compact and historical lookup semantics."""
    size = 64
    workload = build_scale_workload(size)
    adapter = cpu_rotate_target_search_adapter()
    prepared = adapter.prepare(workload.request)

    plan = MembershipMeasurementPlan(
        lookup_iterations=TEST_LOOKUP_ITERATIONS,
        memory_sample_count=TEST_SAMPLE_COUNT,
        sample_count=TEST_SAMPLE_COUNT,
    )
    comparison = measure_membership_index_comparison(
        prepared.batch,
        workload.expected[0],
        plan,
    )

    assert comparison.lookup.iterations_per_sample == TEST_LOOKUP_ITERATIONS
    assert len(comparison.compact_prepare.raw_ns) == TEST_SAMPLE_COUNT
    assert len(comparison.legacy_prepare.raw_ns) == TEST_SAMPLE_COUNT
    assert (
        len(comparison.compact_memory.retained.raw_bytes) == TEST_SAMPLE_COUNT
    )
    assert len(comparison.legacy_memory.retained.raw_bytes) == TEST_SAMPLE_COUNT
    assert comparison.lookup.compact_hit.median_ns > 0
    assert comparison.lookup.compact_miss.median_ns > 0
    assert comparison.lookup.legacy_hit.median_ns > 0
    assert comparison.lookup.legacy_miss.median_ns > 0
