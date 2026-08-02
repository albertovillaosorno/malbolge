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
#   - Paired synchronous-copy versus streamed CUDA ticket measurements.
# - Must-Not:
#   - Infer transfer overlap, cross-device speedup, or semantic authority.
# - Allows:
#   - Inputs: one exact full-domain CRAZY workload and groups 1/2/4/8.
#   - Outputs: route timings, paired comparisons, and proof identities.
#   - Side effects: scoped CUDA execution and JSON output only.
# - Split-When:
#   - Split when transfer-event attribution gains an independent protocol.
# - Merge-When:
#   - Merge when another benchmark owns this exact ticket-copy comparison.
# - Summary:
#   - CUDA one-shot ticket transfer throughput matrix.
# - Description:
#   - Compares default synchronous copies with registered stream copies.
# - Usage:
#   - Run from a clean commit and retain output under accelerator evidence.
# - Defaults:
#   - One warmup and fifteen retained cyclic-order samples per route.
#

"""CUDA synchronous-copy versus streamed one-shot ticket benchmark."""

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
from accelerator.cuda import cuda_independent_ticket_transfer_id
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
GROUP_SIZES: Final = (1, 2, 4, 8)
GROUPED_SIZES: Final = (2, 4, 8)
HYPOTHESIS_GROUP_SIZE: Final = 8
CUDA_BACKEND_ID: Final = "cuda"
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
WORKLOAD_ID: Final = "classic-crazy-full-domain-ticket-transfer-v1"
BENCHMARK_ID: Final = "cuda-independent-ticket-transfer-throughput-v1"
EXPECTED_LAUNCH_ID: Final = "cuda-independent-stream-kernel-launch-v1"
EXPECTED_TRANSFER_ID: Final = "cuda-independent-stream-ticket-transfer-v1"
EXPECTED_STORAGE_ID: Final = "proof-bound-u32le-primitive-input-v1"
SYNC_SEQUENTIAL: Final = "synchronous-sequential"
SYNC_GROUPED: Final = "synchronous-grouped"
STREAMED_SEQUENTIAL: Final = "streamed-sequential"
STREAMED_GROUPED: Final = "streamed-grouped"
ROUTE_ORDER: Final = (
    "cyclic first-route rotation across synchronous and streamed ticket routes"
)
HYPOTHESIS: Final = (
    "group-eight streamed submit-all/reverse-wait lowers median wall time "
    "versus both synchronous grouped and streamed sequential execution while "
    "every full-domain result stays byte-exact"
)
REJECTION_RULE: Final = (
    "reject streamed group-eight promotion when its median is not lower than "
    "both controls, either paired-win count does not exceed seven, or any "
    "identity/result check fails"
)
INTERPRETATION_LIMIT: Final = (
    "wall time includes allocation, optional host registration, transfers, "
    "launch, synchronization, result materialization, unregistration, and "
    "free; it does not attribute physical transfer/kernel overlap"
)


@dataclass(frozen=True, slots=True)
class RouteTiming:
    """Raw and summary wall time for one exact ticket route."""

    group_size: int
    max_ns: int
    median_ns: int
    min_ns: int
    mode: str
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    route_id: str


@dataclass(frozen=True, slots=True)
class Comparison:
    """Paired route relationships for one ticket group size."""

    group_size: int
    streamed_grouped_over_streamed_sequential: float | None
    streamed_grouped_over_synchronous_grouped: float | None
    streamed_grouped_wins_over_streamed_sequential: int | None
    streamed_grouped_wins_over_synchronous_grouped: int | None
    streamed_sequential_over_synchronous_sequential: float
    streamed_sequential_wins: int
    synchronous_grouped_over_synchronous_sequential: float | None
    synchronous_grouped_wins: int | None


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
    """Run the paired ticket-transfer matrix and emit JSON evidence.

    Returns:
        Zero after every identity and exact-output check passes.

    """
    prepared = _prepared_workload()
    expected = _reference_words(prepared)
    measured = _measure(prepared, expected)
    rows = {row.route_id: row for row in measured.rows}
    comparisons = {
        str(group_size): _comparison(rows, group_size)
        for group_size in GROUP_SIZES
    }
    outcome = _hypothesis_outcome(comparisons[str(HYPOTHESIS_GROUP_SIZE)])
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "hypothesis": HYPOTHESIS,
        "rejection_rule": REJECTION_RULE,
        "interpretation_limit": INTERPRETATION_LIMIT,
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
            "cpu_reference_timed": False,
            "ordering": ROUTE_ORDER,
            "preparation_timed": False,
            "result_validation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": measured.arch,
            "backend": CUDA_BACKEND_ID,
            "name": measured.device_name,
        },
        "identities": {
            "kernel_launch": _validated_identity(
                cuda_independent_kernel_launch_id(),
                EXPECTED_LAUNCH_ID,
                "kernel launch",
            ),
            "prepared_storage": _validated_identity(
                prepared_primitive_storage_id(),
                EXPECTED_STORAGE_ID,
                "prepared storage",
            ),
            "streamed_transfer": _validated_identity(
                cuda_independent_ticket_transfer_id(),
                EXPECTED_TRANSFER_ID,
                "streamed transfer",
            ),
        },
        "routes": {key: asdict(value) for key, value in rows.items()},
        "comparisons": {
            key: asdict(value) for key, value in comparisons.items()
        },
        "hypothesis_outcome": outcome,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _prepared_workload() -> PreparedPrimitiveBatch:
    data = b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in range(CORPUS_SIZE)
    )
    prepared = prepare_packed_primitive_batch(
        accumulators_u32le=b"\0" * len(data),
        data_u32le=data,
        kind=PrimitiveKind.CRAZY,
    )
    if prepared.count() != CORPUS_SIZE:
        message = "ticket transfer workload cardinality drifted"
        raise RuntimeError(message)
    return prepared


def _workload_sha256(prepared: PreparedPrimitiveBatch) -> str:
    storage = prepared.validated_storage()
    digest = sha256()
    digest.update(storage.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(storage.accumulators_u32le)
    digest.update(storage.data_u32le)
    return digest.hexdigest()


def _reference_words(prepared: PreparedPrimitiveBatch) -> bytes:
    result = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    words = _packed_words(result)
    expected_bytes = CORPUS_SIZE * WORD_BYTES
    if len(words) != expected_bytes:
        message = "ticket transfer CPU reference size drifted"
        raise RuntimeError(message)
    return words


def _measure(prepared: PreparedPrimitiveBatch, expected: bytes) -> _Measured:
    with CudaExactPrimitiveAdapter() as adapter:
        routes = _routes(adapter, prepared)
        _warmup(routes, expected)
        raw: dict[str, list[int]] = {route.route_id: [] for route in routes}
        for sample_index in range(SAMPLE_COUNT):
            first = sample_index % len(routes)
            for route in routes[first:] + routes[:first]:
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


def _warmup(routes: tuple[_Route, ...], expected: bytes) -> None:
    for _ in range(WARMUP_COUNT):
        for route in routes:
            _validate_results(route.action(), route.group_size, expected)


def _routes(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
) -> tuple[_Route, ...]:
    routes: list[_Route] = []
    for group_size in GROUP_SIZES:
        routes.extend((
            _Route(
                action=lambda size=group_size: _run_sequential(
                    adapter.submit_prepared,
                    prepared,
                    size,
                ),
                group_size=group_size,
                mode=SYNC_SEQUENTIAL,
                route_id=_route_id(SYNC_SEQUENTIAL, group_size),
            ),
            _Route(
                action=lambda size=group_size: _run_sequential(
                    adapter.ticket_transfers.submit,
                    prepared,
                    size,
                ),
                group_size=group_size,
                mode=STREAMED_SEQUENTIAL,
                route_id=_route_id(STREAMED_SEQUENTIAL, group_size),
            ),
        ))
        if group_size in GROUPED_SIZES:
            routes.extend((
                _Route(
                    action=lambda size=group_size: _run_grouped(
                        adapter.submit_prepared,
                        prepared,
                        size,
                    ),
                    group_size=group_size,
                    mode=SYNC_GROUPED,
                    route_id=_route_id(SYNC_GROUPED, group_size),
                ),
                _Route(
                    action=lambda size=group_size: _run_grouped(
                        adapter.ticket_transfers.submit,
                        prepared,
                        size,
                    ),
                    group_size=group_size,
                    mode=STREAMED_GROUPED,
                    route_id=_route_id(STREAMED_GROUPED, group_size),
                ),
            ))
    return tuple(routes)


def _run_sequential(
    submit: Callable[[PreparedPrimitiveBatch], CudaPrimitiveEvaluationTicket],
    prepared: PreparedPrimitiveBatch,
    group_size: int,
) -> tuple[PackedPrimitiveResult, ...]:
    return tuple(submit(prepared).wait() for _ in range(group_size))


def _run_grouped(
    submit: Callable[[PreparedPrimitiveBatch], CudaPrimitiveEvaluationTicket],
    prepared: PreparedPrimitiveBatch,
    group_size: int,
) -> tuple[PackedPrimitiveResult, ...]:
    tickets: list[CudaPrimitiveEvaluationTicket] = []
    try:
        tickets.extend(submit(prepared) for _ in range(group_size))
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
        message = "ticket transfer route returned the wrong result count"
        raise RuntimeError(message)
    for result in results:
        if result.capability.backend_id != CUDA_BACKEND_ID:
            message = "ticket transfer route changed backend identity"
            raise RuntimeError(message)
        if result.words_u32le != expected:
            message = "ticket transfer route changed exact primitive output"
            raise RuntimeError(message)


def _timing(route: _Route, samples: list[int]) -> RouteTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "ticket transfer route retained the wrong sample count"
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


def _route_id(mode: str, group_size: int) -> str:
    return f"{mode}-{group_size}"


def _comparison(
    rows: dict[str, RouteTiming],
    group_size: int,
) -> Comparison:
    sync_sequential = rows[_route_id(SYNC_SEQUENTIAL, group_size)]
    streamed_sequential = rows[_route_id(STREAMED_SEQUENTIAL, group_size)]
    if group_size not in GROUPED_SIZES:
        return Comparison(
            group_size=group_size,
            streamed_grouped_over_streamed_sequential=None,
            streamed_grouped_over_synchronous_grouped=None,
            streamed_grouped_wins_over_streamed_sequential=None,
            streamed_grouped_wins_over_synchronous_grouped=None,
            streamed_sequential_over_synchronous_sequential=(
                sync_sequential.median_ns / streamed_sequential.median_ns
            ),
            streamed_sequential_wins=_paired_wins(
                sync_sequential.raw_ns,
                streamed_sequential.raw_ns,
            ),
            synchronous_grouped_over_synchronous_sequential=None,
            synchronous_grouped_wins=None,
        )
    sync_grouped = rows[_route_id(SYNC_GROUPED, group_size)]
    streamed_grouped = rows[_route_id(STREAMED_GROUPED, group_size)]
    return Comparison(
        group_size=group_size,
        streamed_grouped_over_streamed_sequential=(
            streamed_sequential.median_ns / streamed_grouped.median_ns
        ),
        streamed_grouped_over_synchronous_grouped=(
            sync_grouped.median_ns / streamed_grouped.median_ns
        ),
        streamed_grouped_wins_over_streamed_sequential=_paired_wins(
            streamed_sequential.raw_ns,
            streamed_grouped.raw_ns,
        ),
        streamed_grouped_wins_over_synchronous_grouped=_paired_wins(
            sync_grouped.raw_ns,
            streamed_grouped.raw_ns,
        ),
        streamed_sequential_over_synchronous_sequential=(
            sync_sequential.median_ns / streamed_sequential.median_ns
        ),
        streamed_sequential_wins=_paired_wins(
            sync_sequential.raw_ns,
            streamed_sequential.raw_ns,
        ),
        synchronous_grouped_over_synchronous_sequential=(
            sync_sequential.median_ns / sync_grouped.median_ns
        ),
        synchronous_grouped_wins=_paired_wins(
            sync_sequential.raw_ns,
            sync_grouped.raw_ns,
        ),
    )


def _paired_wins(baseline: tuple[int, ...], candidate: tuple[int, ...]) -> int:
    return sum(
        baseline_ns > candidate_ns
        for baseline_ns, candidate_ns in zip(
            baseline,
            candidate,
            strict=True,
        )
    )


def _hypothesis_outcome(comparison: Comparison) -> dict[str, object]:
    if comparison.group_size != HYPOTHESIS_GROUP_SIZE:
        message = "ticket transfer hypothesis selected the wrong group"
        raise RuntimeError(message)
    sync_ratio = _required_float(
        comparison.streamed_grouped_over_synchronous_grouped,
        "streamed versus synchronous grouped ratio",
    )
    sequential_ratio = _required_float(
        comparison.streamed_grouped_over_streamed_sequential,
        "streamed grouped versus sequential ratio",
    )
    sync_wins = _required_int(
        comparison.streamed_grouped_wins_over_synchronous_grouped,
        "streamed wins over synchronous grouped",
    )
    sequential_wins = _required_int(
        comparison.streamed_grouped_wins_over_streamed_sequential,
        "streamed grouped wins over sequential",
    )
    passed = (
        sync_ratio > 1.0
        and sequential_ratio > 1.0
        and sync_wins > SAMPLE_COUNT // 2
        and sequential_wins > SAMPLE_COUNT // 2
    )
    return {
        "group_size": HYPOTHESIS_GROUP_SIZE,
        "passed": passed,
        "reason": (
            "streamed grouped route beats both controls"
            if passed
            else "streamed grouped route does not beat both controls"
        ),
    }


def _required_float(value: float | None, label: str) -> float:
    if value is None:
        message = f"ticket transfer comparison lacks {label}"
        raise RuntimeError(message)
    return value


def _required_int(value: int | None, label: str) -> int:
    if value is None:
        message = f"ticket transfer comparison lacks {label}"
        raise RuntimeError(message)
    return value


def _validated_identity(identifier: str, expected: str, label: str) -> str:
    if identifier != expected:
        message = f"ticket transfer {label} identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
