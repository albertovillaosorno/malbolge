# File:
#   - independent_ticket_stream_throughput.py
# Path:
#   - benchmarks/accelerator/independent_ticket_stream_throughput.py
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
#   - Paired sequential-versus-grouped CUDA primitive ticket measurements.
# - Must-Not:
#   - Change primitive semantics or infer overlap from stream configuration.
# - Allows:
#   - Inputs: exact full-domain crazy prepared input and group sizes 2/4/8.
#   - Outputs: raw route timings, paired comparisons, and proof identities.
#   - Side effects: scoped CUDA execution and JSON output only.
# - Split-When:
#   - Split when asynchronous transfers or another kernel needs an independent
#     protocol.
# - Merge-When:
#   - Merge when another benchmark owns this exact grouped-ticket question.
# - Summary:
#   - Independent CUDA ticket stream throughput benchmark.
# - Description:
#   - Compares submit/wait serial execution with submit-all/reverse-wait groups.
# - Usage:
#   - Run from a clean commit and retain output under accelerator evidence.
# - Defaults:
#   - One warmup and fifteen retained cyclic-order samples per route.
#
# Related documents:
# - docs/research/methodology/benchmark-protocol.md
#
# Large file:
#   - false
#

"""Independent CUDA primitive ticket stream throughput benchmark."""

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
from accelerator.cuda import cuda_independent_kernel_launch_id
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_packed_primitive_batch
from accelerator.exact_primitives import prepared_primitive_storage_id

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda import CudaPrimitiveEvaluationTicket
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveExecutionResult

WORD_BYTES: Final = 4
CORPUS_SIZE: Final = MAX_WORD + 1
GROUP_SIZES: Final = (2, 4, 8)
HYPOTHESIS_GROUP_SIZE: Final = 8
CUDA_BACKEND_ID: Final = "cuda"
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
WORKLOAD_ID: Final = "classic-crazy-full-domain-independent-ticket-group-v1"
BENCHMARK_ID: Final = "cuda-independent-ticket-stream-throughput-v1"
EXPECTED_LAUNCH_ID: Final = "cuda-independent-stream-kernel-launch-v1"
EXPECTED_STORAGE_ID: Final = "proof-bound-u32le-primitive-input-v1"
ROUTE_ORDER: Final = (
    "cyclic first-route rotation across sequential/grouped groups 2, 4, and 8"
)
HYPOTHESIS: Final = (
    "grouped submit-all/reverse-wait lowers group-eight median versus "
    "sequential submit/wait while every full-domain result stays byte-exact"
)
REJECTION_RULE: Final = (
    "reject group-eight throughput promotion when grouped median is not lower, "
    "paired wins do not exceed seven, or any identity/result check fails"
)


@dataclass(frozen=True, slots=True)
class RouteTiming:
    """Raw and summary timing for one exact ticket-group route."""

    group_size: int
    max_ns: int
    median_ns: int
    min_ns: int
    mode: str
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    route_id: str


@dataclass(frozen=True, slots=True)
class _Route:
    action: Callable[[], tuple[PackedPrimitiveResult, ...]]
    group_size: int
    mode: str
    route_id: str


@dataclass(frozen=True, slots=True)
class _Measured:
    arch: str
    device_name: str
    rows: tuple[RouteTiming, ...]


def main() -> int:
    """Run paired grouped-ticket measurements and emit JSON evidence.

    Returns:
        Zero after all exact result and identity checks pass.

    """
    prepared = _prepared_workload()
    expected = _reference_words(prepared)
    measured = _measure(prepared, expected)
    rows = {row.route_id: row for row in measured.rows}
    comparisons = {
        str(group_size): _comparison(rows, group_size)
        for group_size in GROUP_SIZES
    }
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "hypothesis": HYPOTHESIS,
        "rejection_rule": REJECTION_RULE,
        "workload": {
            "count_per_ticket": CORPUS_SIZE,
            "group_sizes": GROUP_SIZES,
            "identity": WORKLOAD_ID,
            "kind": PrimitiveKind.CRAZY.value,
            "sha256": _workload_sha256(prepared),
            "total_words_by_group": {
                str(size): size * CORPUS_SIZE for size in GROUP_SIZES
            },
        },
        "measurement": {
            "adapter_setup_timed": False,
            "ordering": ROUTE_ORDER,
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "validation_timed": False,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": measured.arch,
            "backend": CUDA_BACKEND_ID,
            "name": measured.device_name,
        },
        "identities": {
            "kernel_launch": _validated_launch_id(
                cuda_independent_kernel_launch_id()
            ),
            "prepared_storage": _validated_storage_id(
                prepared_primitive_storage_id()
            ),
        },
        "routes": {key: asdict(value) for key, value in rows.items()},
        "comparisons": comparisons,
    }
    _validate_hypothesis_boundary(comparisons[str(HYPOTHESIS_GROUP_SIZE)])
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _prepared_workload() -> PreparedPrimitiveBatch:
    data = b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in range(CORPUS_SIZE)
    )
    accumulators = b"\0" * len(data)
    prepared = prepare_packed_primitive_batch(
        accumulators_u32le=accumulators,
        data_u32le=data,
        kind=PrimitiveKind.CRAZY,
    )
    if prepared.count() != CORPUS_SIZE:
        message = "independent ticket workload cardinality drifted"
        raise RuntimeError(message)
    return prepared


def _workload_sha256(prepared: PreparedPrimitiveBatch) -> str:
    validated = prepared.validated_storage()
    digest = sha256()
    digest.update(validated.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(validated.accumulators_u32le)
    digest.update(validated.data_u32le)
    return digest.hexdigest()


def _reference_words(prepared: PreparedPrimitiveBatch) -> bytes:
    result = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    words = _packed_words(result)
    expected_bytes = CORPUS_SIZE * WORD_BYTES
    if len(words) != expected_bytes:
        message = "independent ticket CPU reference size drifted"
        raise RuntimeError(message)
    return words


def _measure(prepared: PreparedPrimitiveBatch, expected: bytes) -> _Measured:
    with CudaExactPrimitiveAdapter() as adapter:
        routes = _routes(adapter, prepared)
        for _ in range(WARMUP_COUNT):
            for route in routes:
                _validate_results(route.action(), route.group_size, expected)
        raw: dict[str, list[int]] = {route.route_id: [] for route in routes}
        for sample_index in range(SAMPLE_COUNT):
            first = sample_index % len(routes)
            ordered = routes[first:] + routes[:first]
            for route in ordered:
                start = perf_counter_ns()
                results = route.action()
                elapsed = perf_counter_ns() - start
                _validate_results(results, route.group_size, expected)
                raw[route.route_id].append(elapsed)
        capability = adapter.capability()
    return _Measured(
        arch=capability.device_arch,
        device_name=capability.device_name,
        rows=tuple(_timing(route, raw[route.route_id]) for route in routes),
    )


def _routes(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
) -> tuple[_Route, ...]:
    routes: list[_Route] = []
    for group_size in GROUP_SIZES:
        routes.extend((
            _Route(
                action=lambda size=group_size: _run_sequential(
                    adapter,
                    prepared,
                    size,
                ),
                group_size=group_size,
                mode="sequential",
                route_id=f"sequential-{group_size}",
            ),
            _Route(
                action=lambda size=group_size: _run_grouped(
                    adapter,
                    prepared,
                    size,
                ),
                group_size=group_size,
                mode="grouped",
                route_id=f"grouped-{group_size}",
            ),
        ))
    return tuple(routes)


def _run_sequential(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
    group_size: int,
) -> tuple[PackedPrimitiveResult, ...]:
    return tuple(
        adapter.submit_prepared(prepared).wait() for _ in range(group_size)
    )


def _run_grouped(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
    group_size: int,
) -> tuple[PackedPrimitiveResult, ...]:
    tickets: list[CudaPrimitiveEvaluationTicket] = []
    try:
        tickets.extend(
            adapter.submit_prepared(prepared) for _ in range(group_size)
        )
        return tuple(ticket.wait() for ticket in reversed(tickets))
    finally:
        for ticket in reversed(tickets):
            ticket.close()


def _packed_words(result: PrimitiveExecutionResult) -> bytes:
    if isinstance(result, PackedPrimitiveResult):
        return result.words_u32le
    return b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in result.values
    )


def _validate_results(
    results: tuple[PackedPrimitiveResult, ...],
    group_size: int,
    expected: bytes,
) -> None:
    if len(results) != group_size:
        message = "independent ticket route returned the wrong result count"
        raise RuntimeError(message)
    for result in results:
        if result.capability.backend_id != CUDA_BACKEND_ID:
            message = "independent ticket route changed backend identity"
            raise RuntimeError(message)
        if result.words_u32le != expected:
            message = "independent ticket route changed exact primitive output"
            raise RuntimeError(message)


def _timing(route: _Route, samples: list[int]) -> RouteTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "independent ticket route retained the wrong sample count"
        raise RuntimeError(message)
    return RouteTiming(
        group_size=route.group_size,
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        mode=route.mode,
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
        route_id=route.route_id,
    )


def _comparison(
    rows: dict[str, RouteTiming],
    group_size: int,
) -> dict[str, int | float]:
    sequential = rows[f"sequential-{group_size}"]
    grouped = rows[f"grouped-{group_size}"]
    savings = tuple(
        baseline - candidate
        for baseline, candidate in zip(
            sequential.raw_ns,
            grouped.raw_ns,
            strict=True,
        )
    )
    return {
        "group_size": group_size,
        "grouped_over_sequential": (sequential.median_ns / grouped.median_ns),
        "paired_median_saving_ns": int(median(savings)),
        "paired_wins": sum(value > 0 for value in savings),
    }


def _validate_hypothesis_boundary(comparison: dict[str, int | float]) -> None:
    if comparison["group_size"] != HYPOTHESIS_GROUP_SIZE:
        message = "independent ticket hypothesis selected the wrong group"
        raise RuntimeError(message)


def _validated_launch_id(identifier: str) -> str:
    if identifier != EXPECTED_LAUNCH_ID:
        message = "independent ticket kernel-launch identity drifted"
        raise RuntimeError(message)
    return identifier


def _validated_storage_id(identifier: str) -> str:
    if identifier != EXPECTED_STORAGE_ID:
        message = "independent ticket prepared-storage identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
