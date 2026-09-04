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
#   - Raw CUDA throughput across adaptive crazy arithmetic geometries.
# - Must-Not:
#   - Change the reviewed crazy-heavy workload or treat timing as verification.
# - Allows:
#   - Inputs: exact N10-N14 v1 workload and explicit resident crazy modes.
#   - Outputs: raw resident/end-to-end samples and summary JSON.
#   - Side effects: CUDA execution and stdout JSON only.
# - Split-When:
#   - Split when another arithmetic geometry needs an independent workload.
# - Merge-When:
#   - Merge when another benchmark owns this exact three-route comparison.
# - Summary:
#   - N10-N14 tritwise, residual, and padded CUDA crazy throughput comparison.
# - Description:
#   - Measures the frozen v1 `p` workload by explicit crazy arithmetic route.
# - Usage:
#   - Run from a clean commit and retain output with exact device provenance.
# - Defaults:
#   - One warmup and fifteen route-block samples; first route rotates by width.
#

"""CUDA crazy-geometry throughput comparison for adaptive widths N10-N14."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.cuda.resident_kernel import CRAZY_TABLE_ENTRIES
from accelerator.cuda.resident_kernel import ResidentCrazyGeometry

from benchmarks.accelerator import profile_width_crazy_throughput as baseline

if TYPE_CHECKING:
    from array import array

    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.profile_run import ProfileRunGeometry
    from accelerator.profile_run import ProfileRunRequest
    from accelerator.profile_run import ProfileRunResult

BENCHMARK_ID: Final = "cuda-profile-width-crazy-geometry-throughput-v1"
BASELINE_BENCHMARK_ID: Final = (
    baseline.BENCHMARK_ID
)
BATCH_SIZE: Final = baseline.BATCH_SIZE
END_TO_END_REGION: Final = baseline.END_TO_END_REGION
RESIDENT_REGION: Final = baseline.RESIDENT_REGION
SAMPLE_COUNT: Final = baseline.SAMPLE_COUNT
STEP_BUDGET: Final = baseline.STEP_BUDGET
WARMUP_COUNT: Final = baseline.WARMUP_COUNT
WIDTHS: Final = baseline.WIDTHS
WORD_BYTES: Final = baseline.WORD_BYTES
WORKLOAD_ID: Final = baseline.WORKLOAD_ID
CRAZY_GEOMETRIES: Final = (
    ResidentCrazyGeometry.TRITWISE,
    ResidentCrazyGeometry.NATIVE,
    ResidentCrazyGeometry.PADDED,
)
ROUTE_ORDER: Final = "cyclic first-route by width; fifteen-sample route blocks"
COMMON_CONSTANT_BYTES: Final = 94 + 94


@dataclass(frozen=True, slots=True)
class CrazyGeometryThroughputRow:
    """Raw and summary measurements for one width and crazy geometry."""

    crazy_geometry: str
    declared_constant_bytes: int
    end_to_end_median_ns: int
    end_to_end_pstdev_ns: float
    end_to_end_raw_ns: tuple[int, ...]
    end_to_end_vm_steps_per_second: float
    memory_bytes_per_vm: int
    memory_words: int
    resident_median_ns: int
    resident_pstdev_ns: float
    resident_raw_ns: tuple[int, ...]
    resident_vm_steps_per_second: float
    word_trits: int


@dataclass(frozen=True, slots=True)
class _WidthWorkload:
    """Frozen equivalent work shared by all arithmetic routes at one width."""

    expected_memory: array[int]
    geometry: ProfileRunGeometry
    request: ProfileRunRequest


@dataclass(frozen=True, slots=True)
class _RouteWorkload:
    """One explicit arithmetic route over a frozen width workload."""

    crazy_geometry: ResidentCrazyGeometry
    width: _WidthWorkload


def rotated_crazy_geometry_order(
    width_index: int,
) -> tuple[ResidentCrazyGeometry, ...]:
    """Rotate which arithmetic route is measured first for one width.

    Returns:
        Every configured geometry exactly once in cyclic order.

    """
    offset = width_index % len(CRAZY_GEOMETRIES)
    return CRAZY_GEOMETRIES[offset:] + CRAZY_GEOMETRIES[:offset]


def declared_constant_bytes(crazy_geometry: ResidentCrazyGeometry) -> int:
    """Return source-declared CUDA constant bytes for one arithmetic route.

    Returns:
        Shared XLAT bytes plus the crazy table only for lookup routes.

    """
    if crazy_geometry is ResidentCrazyGeometry.TRITWISE:
        return COMMON_CONSTANT_BYTES
    return COMMON_CONSTANT_BYTES + CRAZY_TABLE_ENTRIES


def main() -> int:
    """Measure identical crazy-heavy work at every admitted benchmark width.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    rows: list[CrazyGeometryThroughputRow] = []
    device: dict[str, str] | None = None
    backend: str | None = None
    for width_index, word_trits in enumerate(WIDTHS):
        measured, capability = _measure_width(width_index, word_trits)
        rows.extend(measured)
        if device is None:
            backend = capability.backend_id
            device = {
                "arch": capability.device_arch,
                "name": capability.device_name,
            }
    payload = {
        "backend": backend,
        "batch_size": BATCH_SIZE,
        "benchmark_id": BENCHMARK_ID,
        "crazy_geometries": tuple(
            geometry.value for geometry in CRAZY_GEOMETRIES
        ),
        "device": device,
        "end_to_end_region": END_TO_END_REGION,
        "resident_region": RESIDENT_REGION,
        "route_order": ROUTE_ORDER,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "warmup_count": WARMUP_COUNT,
        "widths": WIDTHS,
        "workload_id": WORKLOAD_ID,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_width(
    width_index: int,
    word_trits: int,
) -> tuple[tuple[CrazyGeometryThroughputRow, ...], AcceleratorCapability]:
    width = _WidthWorkload(
        expected_memory=(
            baseline.expected_profile_width_crazy_memory(word_trits)
        ),
        geometry=baseline.profile_width_crazy_geometry(word_trits),
        request=baseline.profile_width_crazy_request(word_trits),
    )
    rows: list[CrazyGeometryThroughputRow] = []
    capability: AcceleratorCapability | None = None
    for crazy_geometry in rotated_crazy_geometry_order(width_index):
        route = _RouteWorkload(crazy_geometry=crazy_geometry, width=width)
        with CudaProfileRunAdapter(
            width.geometry,
            crazy_geometry=crazy_geometry,
        ) as adapter:
            if capability is None:
                capability = adapter.capability()
            rows.append(_measure(adapter, route))
    if capability is None:
        message = "crazy geometry benchmark has no configured routes"
        raise RuntimeError(message)
    return tuple(rows), capability


def _measure(
    adapter: CudaProfileRunAdapter,
    route: _RouteWorkload,
) -> CrazyGeometryThroughputRow:
    for _ in range(WARMUP_COUNT):
        results = adapter.evaluate((route.width.request,))
        _validate(results, route)
        _ = _resident_elapsed(adapter, route)
    end_to_end = [
        _evaluate_elapsed(adapter, route) for _ in range(SAMPLE_COUNT)
    ]
    resident = [
        _resident_elapsed(adapter, route) for _ in range(SAMPLE_COUNT)
    ]
    return _row(route, end_to_end, resident)


def _evaluate_elapsed(
    adapter: CudaProfileRunAdapter,
    route: _RouteWorkload,
) -> int:
    start = perf_counter_ns()
    results = adapter.evaluate((route.width.request,))
    elapsed = perf_counter_ns() - start
    _validate(results, route)
    return elapsed


def _resident_elapsed(
    adapter: CudaProfileRunAdapter,
    route: _RouteWorkload,
) -> int:
    with adapter.open_session((route.width.request,), max_runs=1) as session:
        start = perf_counter_ns()
        session.advance()
        elapsed = perf_counter_ns() - start
        results = session.snapshot()
    _validate(results, route)
    return elapsed


def _validate(
    results: tuple[ProfileRunResult, ...],
    route: _RouteWorkload,
) -> None:
    baseline.validate_profile_width_crazy_results(
        results,
        route.width.geometry,
        route.width.expected_memory,
    )


def _row(
    route: _RouteWorkload,
    end_to_end: list[int],
    resident: list[int],
) -> CrazyGeometryThroughputRow:
    end_median = int(median(end_to_end))
    resident_median = int(median(resident))
    geometry = route.width.geometry
    return CrazyGeometryThroughputRow(
        crazy_geometry=route.crazy_geometry.value,
        declared_constant_bytes=declared_constant_bytes(route.crazy_geometry),
        end_to_end_median_ns=end_median,
        end_to_end_pstdev_ns=pstdev(end_to_end),
        end_to_end_raw_ns=tuple(end_to_end),
        end_to_end_vm_steps_per_second=_steps_per_second(end_median),
        memory_bytes_per_vm=geometry.memory_words * WORD_BYTES,
        memory_words=geometry.memory_words,
        resident_median_ns=resident_median,
        resident_pstdev_ns=pstdev(resident),
        resident_raw_ns=tuple(resident),
        resident_vm_steps_per_second=_steps_per_second(resident_median),
        word_trits=geometry.word_trits,
    )


def _steps_per_second(elapsed_ns: int) -> float:
    return (STEP_BUDGET * 1_000_000_000) / elapsed_ns


if __name__ == "__main__":
    raise SystemExit(main())
