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
#   - Protocol checks for benchmark-only CUDA CRAZY candidate throughput.
# - Must-Not:
#   - Require CUDA hardware or promote a benchmark route into production.
# - Allows:
#   - Inputs: benchmark identity, kernel source, and canonical search workloads.
#   - Outputs: deterministic protocol and lookup-table construction assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another width or candidate arithmetic gains an experiment.
# - Merge-When:
#   - Merge when another test owns this exact benchmark protocol.
# - Summary:
#   - Protocol regressions for candidate CRAZY lookup throughput.
# - Description:
#   - Locks route identity and exact five-trit table construction.
# - Usage:
#   - Run before collecting candidate lookup performance evidence.
# - Defaults:
#   - Timing is evidence only; CPU equality remains mandatory.
#

"""Protocol tests for benchmark-only CUDA CRAZY candidate throughput."""

from benchmarks.accelerator import crazy_lookup_candidate_throughput as bench

EXPECTED_ID = "cuda-crazy-lookup-candidate-throughput-v1"
EXPECTED_TABLE_ENTRIES = 59_049
EXPECTED_GEOMETRIES = ("tritwise", "lookup-5+5")
EXPECTED_SAMPLE_COUNT = 15
EXPECTED_WARMUP_COUNT = 1
TRITWISE_DECLARATION = 'extern "C" __global__ void crazy_tritwise'
LOOKUP_DECLARATION = 'extern "C" __global__ void crazy_lookup'
TABLE_DECLARATION = "__constant__ unsigned char TABLE"


def test_candidate_lookup_benchmark_identity_and_order_are_stable() -> None:
    """Benchmark identity, routes, and repetition counts remain explicit."""
    assert bench.BENCHMARK_ID == EXPECTED_ID
    assert bench.GEOMETRIES == EXPECTED_GEOMETRIES
    assert bench.SAMPLE_COUNT == EXPECTED_SAMPLE_COUNT
    assert bench.WARMUP_COUNT == EXPECTED_WARMUP_COUNT


def test_candidate_lookup_table_covers_exact_five_trit_domain() -> None:
    """The benchmark table covers every pair of five-trit chunk values."""
    table = bench.crazy_chunk_table()
    assert len(table) == EXPECTED_TABLE_ENTRIES
    assert min(table) >= 0
    assert max(table) < bench.CRAZY_CHUNK_VALUES


def test_candidate_lookup_kernel_exports_both_benchmark_routes() -> None:
    """Generated source keeps both candidate arithmetic paths reviewable."""
    source = bench.candidate_lookup_kernel_source()
    assert TRITWISE_DECLARATION in source
    assert LOOKUP_DECLARATION in source
    assert TABLE_DECLARATION in source
