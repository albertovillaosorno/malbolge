# File:
#   - crazy_search_performance_matrix.py
# Path:
#   - benchmarks/accelerator/crazy_search_performance_matrix.py
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
#   - Full-domain crazy-target CPU/CUDA and ticket performance matrix.
# - Must-Not:
#   - Change search semantics, discard samples, or infer independent overlap.
# - Allows:
#   - Inputs: one exact 59,049-member and 1,024-preimage workload.
#   - Outputs: raw interleaved route timings and proof/session counters.
#   - Side effects: CPU/CUDA execution and JSON output only.
# - Split-When:
#   - Split when another workload or statistical question needs a new protocol.
# - Merge-When:
#   - Merge when another benchmark owns this exact five-route comparison.
# - Summary:
#   - Multiposition crazy-target search performance matrix.
# - Description:
#   - Separates ordinary, amortized prepared, and one-shot ticket costs.
# - Usage:
#   - Run from a clean commit and retain output under accelerator evidence.
# - Defaults:
#   - One warmup, fifteen retained samples, cyclic route-first ordering.
#
# Related documents:
# - docs/research/methodology/benchmark-protocol.md
#
# Large file:
#   - false
#

"""Multiposition crazy-target CPU/CUDA and ticket performance matrix."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaPrimitiveCandidateSubmissionAdapter
from accelerator.exact_primitives import PrimitiveKind
from accelerator.search_submission import submit_search
from benchmarks.accelerator.crazy_search_workload import ACCUMULATOR
from benchmarks.accelerator.crazy_search_workload import CORPUS_SIZE
from benchmarks.accelerator.crazy_search_workload import CPU_BACKEND
from benchmarks.accelerator.crazy_search_workload import CUDA_BACKEND
from benchmarks.accelerator.crazy_search_workload import PREIMAGE_COUNT
from benchmarks.accelerator.crazy_search_workload import SEED
from benchmarks.accelerator.crazy_search_workload import TARGET
from benchmarks.accelerator.crazy_search_workload import WORKLOAD_ID
from benchmarks.accelerator.crazy_search_workload import (
    full_domain_crazy_target_workload,
)
from benchmarks.accelerator.crazy_search_workload import (
    validate_crazy_search_benchmark_result,
)
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import crazy_target_projected_evaluation_id
from optimizer.crazy_target import crazy_target_search_adapter
from optimizer.crazy_target_submission import CrazyTargetSearchSubmissionAdapter
from optimizer.crazy_target_submission import crazy_target_submission_id

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cpu import CpuPreparedPrimitiveStats
    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.search_submission import SearchSubmissionAdapter
    from accelerator.work_ports import SearchExecutionAdapter
    from accelerator.work_ports import SearchResult
    from benchmarks.accelerator.crazy_search_workload import (
        CrazySearchBenchmarkWorkload,
    )

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
CPU_ORDINARY: Final = "cpu-ordinary"
CPU_PREPARED: Final = "cpu-prepared"
CUDA_ORDINARY: Final = "cuda-ordinary"
CUDA_PREPARED: Final = "cuda-prepared"
CUDA_TICKET: Final = "cuda-ticket-one-shot"
ROUTE_ORDER: Final = (
    "cyclic first-route rotation over CPU ordinary, CPU prepared, "
    "CUDA ordinary, CUDA prepared, and CUDA ticket"
)
HYPOTHESIS: Final = (
    "exact 1,024-position projection lowers prepared CPU/CUDA medians "
    "versus 59,049-item ordinary search; report the one-shot ticket separately"
)
REJECTION_RULE: Final = (
    "reject prepared improvement when either prepared median is not lower; "
    "do not promote the ticket when it is not lower than CUDA ordinary"
)


@dataclass(frozen=True, slots=True)
class SearchTiming:
    """Raw and summary timing for one exact search execution route."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    route_id: str


@dataclass(frozen=True, slots=True)
class _SearchRoutes:
    cpu: EvaluatedSearchExecutionAdapter
    cuda: EvaluatedSearchExecutionAdapter
    ticket: SearchSubmissionAdapter


@dataclass(frozen=True, slots=True)
class _MeasuredSearch:
    capability: AcceleratorCapability
    cpu_stats: CpuPreparedPrimitiveStats
    cuda_stats: CudaPreparedPrimitiveStats
    membership_count: int
    reference_word_count: int
    rows: tuple[SearchTiming, ...]
    selection_count: int


def main() -> int:
    """Measure ordinary, prepared, and ticket full-domain crazy search.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_crazy_target_workload()
    measured = _measure_search(workload)
    routes = {row.route_id: row for row in measured.rows}
    payload = {
        "benchmark_id": "crazy-target-full-domain-performance-matrix-v1",
        "hypothesis": HYPOTHESIS,
        "rejection_rule": REJECTION_RULE,
        "workload": {
            "accumulator": ACCUMULATOR,
            "algorithm_id": CRAZY_TARGET_ALGORITHM_ID,
            "corpus_size": CORPUS_SIZE,
            "evaluation_budget": CORPUS_SIZE,
            "identity": WORKLOAD_ID,
            "preimage_count": PREIMAGE_COUNT,
            "problem_sha256": sha256(workload.problem).hexdigest(),
            "seed": SEED,
            "target": TARGET,
        },
        "measurement": {
            "adapter_setup_timed": False,
            "ordering": ROUTE_ORDER,
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "ticket_preparation_timed": True,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": measured.capability.device_arch,
            "backend": measured.capability.backend_id,
            "name": measured.capability.device_name,
        },
        "routes": {route_id: asdict(row) for route_id, row in routes.items()},
        "cpu_prepared_session": asdict(measured.cpu_stats),
        "cuda_prepared_session": asdict(measured.cuda_stats),
        "prepared_membership_count": measured.membership_count,
        "prepared_projection": _validated_projection_id(
            crazy_target_projected_evaluation_id()
        ),
        "prepared_reference_word_count": measured.reference_word_count,
        "prepared_selection_count": measured.selection_count,
        "search_submission": _validated_submission_id(
            crazy_target_submission_id()
        ),
        "median_ratios": {
            "cpu_prepared_over_ordinary": (
                routes[CPU_ORDINARY].median_ns / routes[CPU_PREPARED].median_ns
            ),
            "cuda_prepared_over_ordinary": (
                routes[CUDA_ORDINARY].median_ns
                / routes[CUDA_PREPARED].median_ns
            ),
            "cuda_prepared_over_cpu_prepared": (
                routes[CPU_PREPARED].median_ns / routes[CUDA_PREPARED].median_ns
            ),
            "cuda_ticket_over_ordinary": (
                routes[CUDA_ORDINARY].median_ns / routes[CUDA_TICKET].median_ns
            ),
            "cuda_prepared_over_ticket": (
                routes[CUDA_TICKET].median_ns / routes[CUDA_PREPARED].median_ns
            ),
        },
        "paired": {
            "cpu_prepared_wins": _paired_wins(
                routes[CPU_ORDINARY], routes[CPU_PREPARED]
            ),
            "cuda_prepared_wins": _paired_wins(
                routes[CUDA_ORDINARY], routes[CUDA_PREPARED]
            ),
            "cuda_ticket_wins": _paired_wins(
                routes[CUDA_ORDINARY], routes[CUDA_TICKET]
            ),
            "cpu_prepared_median_saving_ns": _paired_median_saving(
                routes[CPU_ORDINARY], routes[CPU_PREPARED]
            ),
            "cuda_prepared_median_saving_ns": _paired_median_saving(
                routes[CUDA_ORDINARY], routes[CUDA_PREPARED]
            ),
            "cuda_ticket_median_saving_ns": _paired_median_saving(
                routes[CUDA_ORDINARY], routes[CUDA_TICKET]
            ),
        },
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_search(workload: CrazySearchBenchmarkWorkload) -> _MeasuredSearch:
    cpu_primitive = CpuExactPrimitiveAdapter()
    cpu = crazy_target_search_adapter(cpu_primitive)
    prepared = cpu.prepare(workload.request)
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = crazy_target_search_adapter(primitive)
        ticket = CrazyTargetSearchSubmissionAdapter(
            CudaPrimitiveCandidateSubmissionAdapter(
                primitive,
                PrimitiveKind.CRAZY,
            )
        )
        rows = _measure_routes(
            _SearchRoutes(cpu=cpu, cuda=cuda, ticket=ticket),
            prepared=prepared,
            workload=workload,
        )
        cpu_stats = cpu_primitive.prepared_stats()
        cuda_stats = primitive.prepared_stats()
        _validate_cpu_prepared_stats(cpu_stats)
        _validate_cuda_prepared_stats(cuda_stats)
        return _MeasuredSearch(
            capability=primitive.capability(),
            cpu_stats=cpu_stats,
            cuda_stats=cuda_stats,
            membership_count=_validated_membership_count(
                cpu.prepared_membership_count(prepared)
            ),
            reference_word_count=_validated_reference_count(
                cpu.prepared_candidate_state_count(prepared)
            ),
            rows=rows,
            selection_count=_validated_selection_count(
                cpu.prepared_selection_count(prepared)
            ),
        )


def _measure_routes(
    adapters: _SearchRoutes,
    *,
    prepared: PreparedEvaluatedSearch,
    workload: CrazySearchBenchmarkWorkload,
) -> tuple[SearchTiming, ...]:
    routes = (
        (
            CPU_ORDINARY,
            CPU_BACKEND,
            lambda: adapters.cpu.search(workload.request),
        ),
        (
            CPU_PREPARED,
            CPU_BACKEND,
            lambda: adapters.cpu.search_prepared(prepared),
        ),
        (
            CUDA_ORDINARY,
            CUDA_BACKEND,
            lambda: adapters.cuda.search(workload.request),
        ),
        (
            CUDA_PREPARED,
            CUDA_BACKEND,
            lambda: adapters.cuda.search_prepared(prepared),
        ),
        (
            CUDA_TICKET,
            CUDA_BACKEND,
            lambda: _wait_ticket(adapters.cpu, adapters.ticket, workload),
        ),
    )
    for _ in range(WARMUP_COUNT):
        for _, backend_id, action in routes:
            validate_crazy_search_benchmark_result(
                action(), backend_id, workload
            )
    raw: dict[str, list[int]] = {route_id: [] for route_id, _, _ in routes}
    for sample_index in range(SAMPLE_COUNT):
        start = sample_index % len(routes)
        ordered = routes[start:] + routes[:start]
        for route_id, backend_id, action in ordered:
            raw[route_id].append(_timed_search(action, backend_id, workload))
    return tuple(_timing(route_id, raw[route_id]) for route_id in raw)


def _wait_ticket(
    reference: SearchExecutionAdapter,
    ticket: SearchSubmissionAdapter,
    workload: CrazySearchBenchmarkWorkload,
) -> SearchResult:
    return submit_search(workload.request, reference, ticket).wait()


def _timed_search(
    action: Callable[[], SearchResult],
    backend_id: str,
    workload: CrazySearchBenchmarkWorkload,
) -> int:
    start = perf_counter_ns()
    result = action()
    elapsed = perf_counter_ns() - start
    validate_crazy_search_benchmark_result(result, backend_id, workload)
    return elapsed


def _timing(route_id: str, samples: list[int]) -> SearchTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "crazy search benchmark retained the wrong sample count"
        raise RuntimeError(message)
    return SearchTiming(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
        route_id=route_id,
    )


def _paired_wins(baseline: SearchTiming, candidate: SearchTiming) -> int:
    return sum(
        candidate_ns < baseline_ns
        for baseline_ns, candidate_ns in zip(
            baseline.raw_ns,
            candidate.raw_ns,
            strict=True,
        )
    )


def _paired_median_saving(
    baseline: SearchTiming,
    candidate: SearchTiming,
) -> int:
    savings = tuple(
        baseline_ns - candidate_ns
        for baseline_ns, candidate_ns in zip(
            baseline.raw_ns,
            candidate.raw_ns,
            strict=True,
        )
    )
    return int(median(savings))


def _validate_cpu_prepared_stats(stats: CpuPreparedPrimitiveStats) -> None:
    evaluations = WARMUP_COUNT + SAMPLE_COUNT
    observed = (
        stats.builds,
        stats.evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
        stats.rotate_table_entries,
    )
    expected = (
        1,
        evaluations,
        PREIMAGE_COUNT,
        PrimitiveKind.CRAZY,
        evaluations - 1,
        0,
    )
    if observed != expected:
        message = "prepared CPU crazy session identity drifted"
        raise RuntimeError(message)


def _validate_cuda_prepared_stats(stats: CudaPreparedPrimitiveStats) -> None:
    evaluations = WARMUP_COUNT + SAMPLE_COUNT
    observed = (
        stats.builds,
        stats.evaluations,
        stats.packed_evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
    )
    expected = (
        1,
        evaluations,
        evaluations,
        PREIMAGE_COUNT,
        PrimitiveKind.CRAZY,
        evaluations - 1,
    )
    if observed != expected:
        message = "prepared CUDA crazy session identity drifted"
        raise RuntimeError(message)


def _validated_membership_count(count: int) -> int:
    if count != CORPUS_SIZE:
        message = "crazy prepared membership does not cover the full corpus"
        raise RuntimeError(message)
    return count


def _validated_reference_count(count: int) -> int:
    if count != PREIMAGE_COUNT:
        message = "crazy prepared reference does not cover exact projection"
        raise RuntimeError(message)
    return count


def _validated_selection_count(count: int) -> int:
    if count != PREIMAGE_COUNT:
        message = "crazy prepared selector cardinality drifted"
        raise RuntimeError(message)
    return count


def _validated_projection_id(identifier: str) -> str:
    expected = "classic-crazy-preimage-position-subset-v1"
    if identifier != expected:
        message = "crazy prepared projection identity drifted"
        raise RuntimeError(message)
    return identifier


def _validated_submission_id(identifier: str) -> str:
    expected = "classic-crazy-target-search-submission-v1"
    if identifier != expected:
        message = "crazy search submission identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
