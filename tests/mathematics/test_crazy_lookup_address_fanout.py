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
#   - Deterministic protocol checks for crazy lookup address fanout evidence.
# - Must-Not:
#   - Require CUDA hardware or reinterpret fanout as physical cache counters.
# - Allows:
#   - Inputs: canonical full-domain and exact projected search workloads.
#   - Outputs: exact route, histogram, and serialization-pressure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another memory-space diagnostic gains a distinct protocol.
# - Merge-When:
#   - Merge when another test owns these exact fanout distributions.
# - Summary:
#   - Protocol regressions for CUDA crazy lookup address fanout.
# - Description:
#   - Locks canonical search order and exact unique-address counts by warp.
# - Usage:
#   - Run before using fanout as structural lookup/cache evidence.
# - Defaults:
#   - Fanout is deterministic address evidence, never cache hit-rate evidence.
#

"""Protocol tests for canonical crazy lookup constant-memory address fanout."""

from __future__ import annotations

from benchmarks.accelerator import crazy_lookup_address_fanout as fanout

EXPECTED_BENCHMARK_ID = "cuda-crazy-lookup-address-fanout-v1"
EXPECTED_CHUNK_VALUES = 243
EXPECTED_WARP_SIZE = 32
CACHE_SCOPE_TEXT = "not cache hit/miss data"
EXPECTED_ROWS = {
    (fanout.ORDINARY_ROUTE, "low"): {
        "candidate_count": 59_049,
        "histogram": ((9, 1), (32, 1_845)),
        "total": 59_049,
        "warps": 1_846,
    },
    (fanout.ORDINARY_ROUTE, "middle"): {
        "candidate_count": 59_049,
        "histogram": ((1, 1_611), (2, 235)),
        "total": 2_081,
        "warps": 1_846,
    },
    (fanout.PREPARED_ROUTE, "low"): {
        "candidate_count": 1_024,
        "histogram": ((32, 32),),
        "total": 1_024,
        "warps": 32,
    },
    (fanout.PREPARED_ROUTE, "middle"): {
        "candidate_count": 1_024,
        "histogram": ((1, 32),),
        "total": 32,
        "warps": 32,
    },
}


def test_fanout_identity_uses_reviewed_cuda_and_crazy_geometry() -> None:
    """Bind the diagnostic to current warp and five-trit table geometry."""
    assert fanout.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert fanout.CRAZY_CHUNK_VALUES == EXPECTED_CHUNK_VALUES
    assert fanout.WARP_SIZE == EXPECTED_WARP_SIZE
    assert CACHE_SCOPE_TEXT in fanout.INTERPRETATION


def test_canonical_search_routes_have_exact_address_fanout() -> None:
    """Ordinary and exact projection preserve their known warp distributions."""
    rows = fanout.crazy_lookup_address_fanout()
    assert len(rows) == len(EXPECTED_ROWS)
    for row in rows:
        expected = EXPECTED_ROWS[row.route_id, row.lookup_chunk]
        histogram = tuple(
            (item.unique_addresses, item.warp_count) for item in row.histogram
        )
        assert row.candidate_count == expected["candidate_count"]
        assert histogram == expected["histogram"]
        assert row.total_unique_address_requests == expected["total"]
        assert row.warp_count == expected["warps"]


def test_raw_fanout_and_histograms_have_exact_accounting() -> None:
    """Summary counts cannot drift away from retained per-warp cardinalities."""
    for row in fanout.crazy_lookup_address_fanout():
        assert len(row.raw_unique_addresses_per_warp) == row.warp_count
        assert sum(row.raw_unique_addresses_per_warp) == (
            row.total_unique_address_requests
        )
        assert (
            min(row.raw_unique_addresses_per_warp)
            == row.min_unique_addresses
        )
        assert (
            max(row.raw_unique_addresses_per_warp)
            == row.max_unique_addresses
        )
        assert sum(item.warp_count for item in row.histogram) == row.warp_count
