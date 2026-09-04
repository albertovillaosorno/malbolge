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
#   - Deterministic CUDA constant-table address fanout for canonical crazy
#     search.
# - Must-Not:
#   - Claim hardware cache hits, profile counters, or change search semantics.
# - Allows:
#   - Inputs: canonical ordinary and exact projected crazy-target execution
#     order.
#   - Outputs: unique lookup addresses per CUDA warp and deterministic
#     summaries.
#   - Side effects: stdout JSON only.
# - Split-When:
#   - Split when physical cache counters gain an independently reviewed
#     boundary.
# - Merge-When:
#   - Merge when another diagnostic owns this exact lookup-address model.
# - Summary:
#   - Constant-memory lookup fanout for full and projected crazy search.
# - Description:
#   - Models the lookup geometry over existing search order without timing CUDA.
# - Usage:
#   - Run to inspect address serialization pressure before lookup search ports.
# - Defaults:
#   - Thirty-two lanes per current CUDA warp and two classic five-trit chunks.
#

"""Constant-memory address fanout for canonical crazy-target search order."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import sys
from typing import Final

from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import PreparedCrazyTargetSelection
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import crazy_target_projected_evaluation_id
from optimizer.crazy_target import crazy_target_selection_preparer_id
from optimizer.crazy_target import prepare_crazy_target_selection

from benchmarks.accelerator.crazy_search_workload import ACCUMULATOR
from benchmarks.accelerator.crazy_search_workload import CORPUS_SIZE
from benchmarks.accelerator.crazy_search_workload import PREIMAGE_COUNT
from benchmarks.accelerator.crazy_search_workload import (
    WORKLOAD_ID as CRAZY_SEARCH_WORKLOAD_ID,
)
from benchmarks.accelerator.crazy_search_workload import (
    full_domain_crazy_target_workload,
)

BENCHMARK_ID: Final = "cuda-crazy-lookup-address-fanout-v1"
WORKLOAD_ID: Final = CRAZY_SEARCH_WORKLOAD_ID
CRAZY_CHUNK_VALUES: Final = 243
WARP_SIZE: Final = 32
LOOKUP_CHUNKS: Final = ("low", "middle")
LOOKUP_DIVISORS: Final = (1, CRAZY_CHUNK_VALUES)
ORDINARY_ROUTE: Final = "ordinary-full-domain"
PREPARED_ROUTE: Final = "prepared-exact-projection"
INTERPRETATION: Final = (
    "unique constant-table addresses requested by active lanes in execution "
    "order; this is serialization-pressure evidence, not cache hit/miss data"
)


@dataclass(frozen=True, slots=True)
class FanoutHistogramBin:
    """Warp count sharing one exact unique-address cardinality."""

    unique_addresses: int
    warp_count: int


@dataclass(frozen=True, slots=True)
class CrazyLookupFanoutRow:
    """Exact per-warp lookup-address fanout for one route and chunk."""

    candidate_count: int
    histogram: tuple[FanoutHistogramBin, ...]
    lookup_chunk: str
    max_unique_addresses: int
    min_unique_addresses: int
    raw_unique_addresses_per_warp: tuple[int, ...]
    route_id: str
    total_unique_address_requests: int
    warp_count: int


def crazy_lookup_address_fanout() -> tuple[CrazyLookupFanoutRow, ...]:
    """Model ordinary and production-projected lookup address fanout.

    Returns:
        Four deterministic rows: two lookup chunks for each search route.

    """
    ordinary, projected = _execution_words()
    rows: list[CrazyLookupFanoutRow] = []
    for route_id, data in (
        (ORDINARY_ROUTE, ordinary),
        (PREPARED_ROUTE, projected),
    ):
        for chunk_index, chunk_name in enumerate(LOOKUP_CHUNKS):
            rows.append(
                _fanout_row(
                    route_id,
                    data,
                    chunk_index=chunk_index,
                    chunk_name=chunk_name,
                )
            )
    return tuple(rows)


def main() -> int:
    """Emit deterministic address-fanout evidence as JSON.

    Returns:
        Zero after writing one canonical diagnostic document.

    """
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "crazy_chunk_values": CRAZY_CHUNK_VALUES,
        "interpretation": INTERPRETATION,
        "lookup_chunks": LOOKUP_CHUNKS,
        "projection_id": crazy_target_projected_evaluation_id(),
        "rows": [asdict(row) for row in crazy_lookup_address_fanout()],
        "selection_id": crazy_target_selection_preparer_id(),
        "warp_size": WARP_SIZE,
        "workload_id": WORKLOAD_ID,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _execution_words() -> tuple[tuple[int, ...], tuple[int, ...]]:
    workload = full_domain_crazy_target_workload()
    problem = CrazyTargetProblem.decode(workload.problem)
    if len(problem.candidates) != CORPUS_SIZE:
        message = "crazy lookup fanout requires the complete canonical corpus"
        raise RuntimeError(message)
    batch = build_crazy_target_batch(workload.request).validated()
    selection = prepare_crazy_target_selection(workload.request, batch)
    if not isinstance(selection, PreparedCrazyTargetSelection):
        message = "crazy lookup fanout received invalid selection proof"
        raise TypeError(message)
    _, accumulator, positions = selection.for_selection(workload.request, batch)
    if accumulator != ACCUMULATOR or len(positions) != PREIMAGE_COUNT:
        message = "crazy lookup fanout projection identity drifted"
        raise RuntimeError(message)
    projected = tuple(problem.candidates[position] for position in positions)
    return (problem.candidates, projected)


def _fanout_row(
    route_id: str,
    data: tuple[int, ...],
    *,
    chunk_index: int,
    chunk_name: str,
) -> CrazyLookupFanoutRow:
    divisor: int = LOOKUP_DIVISORS[chunk_index]
    raw = tuple(
        _warp_unique_addresses(data[start : start + WARP_SIZE], divisor)
        for start in range(0, len(data), WARP_SIZE)
    )
    histogram = tuple(
        FanoutHistogramBin(unique_addresses=count, warp_count=raw.count(count))
        for count in sorted(set(raw))
    )
    return CrazyLookupFanoutRow(
        candidate_count=len(data),
        histogram=histogram,
        lookup_chunk=chunk_name,
        max_unique_addresses=max(raw),
        min_unique_addresses=min(raw),
        raw_unique_addresses_per_warp=raw,
        route_id=route_id,
        total_unique_address_requests=sum(raw),
        warp_count=len(raw),
    )


def _warp_unique_addresses(data: tuple[int, ...], divisor: int) -> int:
    accumulator_chunk = (ACCUMULATOR // divisor) % CRAZY_CHUNK_VALUES
    return len({
        (((value // divisor) % CRAZY_CHUNK_VALUES) * CRAZY_CHUNK_VALUES)
        + accumulator_chunk
        for value in data
    })


if __name__ == "__main__":
    raise SystemExit(main())
