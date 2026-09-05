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
#   - CUDA-event kernel durations for benchmark-only CRAZY candidate geometries.
# - Must-Not:
#   - Change product adapters, reuse wall timing as device timing, or verify
#     semantics from CUDA output alone.
# - Allows:
#   - Inputs: canonical ordinary/projected CRAZY candidate orders and kernels.
#   - Outputs: raw CUDA-event duration samples after trusted CPU equality.
#   - Side effects: CUDA execution and stdout JSON only.
# - Split-When:
#   - Split when another event-timing protocol or arithmetic width is admitted.
# - Merge-When:
#   - Merge when another benchmark owns this exact isolated-stream comparison.
# - Summary:
#   - Device-timeline CRAZY tritwise versus five-trit lookup comparison.
# - Description:
#   - Separates CUDA-event kernel duration from host launch and synchronization.
# - Usage:
#   - Run from a clean commit and retain only after exact validation.
# - Defaults:
#   - One warmup and fifteen serial samples with alternating first geometry.
#

"""CUDA-event CRAZY candidate arithmetic on canonical search orders."""

from __future__ import annotations

import ctypes
from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
from statistics import pstdev
import sys
from typing import Final

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import create_independent_kernel_timeline
from accelerator.cuda import cuda_independent_kernel_launch_id
from accelerator.cuda import cuda_independent_kernel_timeline_id
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import PreparedCrazyTargetSelection
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import prepare_crazy_target_selection

from benchmarks.accelerator import crazy_lookup_candidate_throughput as baseline
from benchmarks.accelerator.crazy_lookup_address_fanout import ORDINARY_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import PREPARED_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import WORKLOAD_ID
from benchmarks.accelerator.crazy_search_workload import ACCUMULATOR
from benchmarks.accelerator.crazy_search_workload import (
    full_domain_crazy_target_workload,
)

BENCHMARK_ID: Final = "cuda-crazy-lookup-candidate-event-timeline-v1"
SAMPLE_COUNT: Final = baseline.SAMPLE_COUNT
WARMUP_COUNT: Final = baseline.WARMUP_COUNT
TRITWISE: Final = baseline.TRITWISE
LOOKUP: Final = baseline.LOOKUP
GEOMETRIES: Final = baseline.GEOMETRIES
WORD_BYTES: Final = baseline.WORD_BYTES
EXPECTED_TIMELINE_ID: Final = "cuda-independent-stream-kernel-timeline-v1"
EXPECTED_LAUNCH_ID: Final = "cuda-independent-stream-kernel-launch-v1"
INTERPRETATION_LIMIT: Final = (
    "CUDA events delimit one kernel on a fresh isolated nonblocking stream; "
    "they do not measure default-stream wall time, transfers, or verification"
)


@dataclass(frozen=True, slots=True)
class CandidateEventRow:
    """Raw CUDA-event kernel durations for one route and geometry."""

    candidate_count: int
    geometry: str
    median_duration_ms: float
    pstdev_duration_ms: float
    raw_duration_ms: tuple[float, ...]
    route_id: str


@dataclass(frozen=True, slots=True)
class _Workload:
    data: tuple[int, ...]
    expected: tuple[int, ...]
    route_id: str


@dataclass(slots=True)
class _DeviceWorkload:
    host_output: ctypes.Array[ctypes.c_uint32]
    pointers: tuple[int, int, int]
    workload: _Workload


def sample_order(sample_index: int) -> tuple[str, ...]:
    """Return alternating first-geometry order for one retained sample.

    Returns:
        Exact geometry order for the requested sample index.

    """
    if sample_index % 2 == 0:
        return GEOMETRIES
    return (LOOKUP, TRITWISE)


def main() -> int:
    """Measure device-event duration for exact classic candidate CRAZY.

    Returns:
        Zero after every event-timed result passes trusted CPU equality.

    """
    runtime = CudaRuntime()
    module: ctypes.c_void_p | None = None
    try:
        module = runtime.compile_module(
            baseline.candidate_lookup_kernel_source(),
            runtime.device_info.arch,
        )
        kernels = {
            TRITWISE: runtime.get_kernel(module, b"crazy_tritwise"),
            LOOKUP: runtime.get_kernel(module, b"crazy_lookup"),
        }
        rows = tuple(
            row
            for workload in _workloads()
            for row in _measure_workload(runtime, kernels, workload)
        )
        payload = {
            "benchmark_id": BENCHMARK_ID,
            "device": {
                "arch": runtime.device_info.arch,
                "name": runtime.device_info.name,
            },
            "geometries": GEOMETRIES,
            "identities": {
                "kernel_launch": _validated_identity(
                    cuda_independent_kernel_launch_id(), EXPECTED_LAUNCH_ID
                ),
                "kernel_timeline": _validated_identity(
                    cuda_independent_kernel_timeline_id(), EXPECTED_TIMELINE_ID
                ),
            },
            "interpretation_limit": INTERPRETATION_LIMIT,
            "measurement": {
                "event_origin_setup_timed": False,
                "independent_stream": True,
                "result_download_timed": False,
                "sample_count": SAMPLE_COUNT,
                "stream_create_destroy_timed": False,
                "validation_timed": False,
                "warmup_count": WARMUP_COUNT,
            },
            "rows": [asdict(row) for row in rows],
            "workload_id": WORKLOAD_ID,
        }
        encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        _ = sys.stdout.write(encoded)
        return 0
    finally:
        if module is not None:
            runtime.unload_module(module)
        runtime.close()


def _workloads() -> tuple[_Workload, ...]:
    workload = full_domain_crazy_target_workload()
    problem = CrazyTargetProblem.decode(workload.problem)
    batch = build_crazy_target_batch(workload.request).validated()
    selection = prepare_crazy_target_selection(workload.request, batch)
    if not isinstance(selection, PreparedCrazyTargetSelection):
        message = "candidate event timeline received invalid CRAZY proof"
        raise TypeError(message)
    _, accumulator, positions = selection.for_selection(workload.request, batch)
    if accumulator != ACCUMULATOR:
        message = "candidate event timeline accumulator identity drifted"
        raise RuntimeError(message)
    projected = tuple(problem.candidates[index] for index in positions)
    return (
        _trusted_workload(ORDINARY_ROUTE, problem.candidates),
        _trusted_workload(PREPARED_ROUTE, projected),
    )


def _trusted_workload(route_id: str, data: tuple[int, ...]) -> _Workload:
    expected = CpuExactPrimitiveAdapter().evaluate(
        PrimitiveBatch(
            accumulators=(ACCUMULATOR,) * len(data),
            data=data,
            kind=PrimitiveKind.CRAZY,
        )
    ).values
    return _Workload(data=data, expected=expected, route_id=route_id)


def _measure_workload(
    runtime: CudaRuntime,
    kernels: dict[str, ctypes.c_void_p],
    workload: _Workload,
) -> tuple[CandidateEventRow, ...]:
    device = _prepare_device_workload(runtime, workload)
    try:
        samples = _collect_samples(runtime, kernels, device)
        return tuple(
            _row(workload, geometry, samples[geometry])
            for geometry in GEOMETRIES
        )
    finally:
        for pointer in reversed(device.pointers):
            runtime.free(pointer)


def _collect_samples(
    runtime: CudaRuntime,
    kernels: dict[str, ctypes.c_void_p],
    device: _DeviceWorkload,
) -> dict[str, list[float]]:
    for _ in range(WARMUP_COUNT):
        for geometry in GEOMETRIES:
            _ = _event_duration(runtime, kernels[geometry], device)
    samples: dict[str, list[float]] = {
        geometry: [] for geometry in GEOMETRIES
    }
    for sample_index in range(SAMPLE_COUNT):
        for geometry in sample_order(sample_index):
            duration = _event_duration(runtime, kernels[geometry], device)
            samples[geometry].append(duration)
    return samples


def _prepare_device_workload(
    runtime: CudaRuntime,
    workload: _Workload,
) -> _DeviceWorkload:
    host_data = _words(workload.data)
    host_acc = _words((ACCUMULATOR,) * len(workload.data))
    host_output = _words((0,) * len(workload.data))
    byte_count = len(workload.data) * WORD_BYTES
    pointers = (
        runtime.allocate(byte_count),
        runtime.allocate(byte_count),
        runtime.allocate(byte_count),
    )
    runtime.copy_to_device(pointers[0], host_data)
    runtime.copy_to_device(pointers[1], host_acc)
    return _DeviceWorkload(
        host_output=host_output,
        pointers=pointers,
        workload=workload,
    )


def _event_duration(
    runtime: CudaRuntime,
    kernel: ctypes.c_void_p,
    device: _DeviceWorkload,
) -> float:
    timeline = create_independent_kernel_timeline(runtime)
    try:
        launch = timeline.submit(
            kernel,
            device.pointers,
            len(device.workload.data),
        )
        launch.close()
        (sample,) = timeline.samples()
        runtime.copy_from_device(device.host_output, device.pointers[-1])
        if tuple(device.host_output) != device.workload.expected:
            message = (
                "event-timed CUDA CRAZY diverged from trusted CPU semantics"
            )
            raise RuntimeError(message)
        return sample.duration_ms
    finally:
        timeline.close()


def _row(
    workload: _Workload,
    geometry: str,
    samples: list[float],
) -> CandidateEventRow:
    if len(samples) != SAMPLE_COUNT:
        message = "candidate event timeline retained wrong sample count"
        raise RuntimeError(message)
    return CandidateEventRow(
        candidate_count=len(workload.data),
        geometry=geometry,
        median_duration_ms=median(samples),
        pstdev_duration_ms=pstdev(samples),
        raw_duration_ms=tuple(samples),
        route_id=workload.route_id,
    )


def _words(values: tuple[int, ...]) -> ctypes.Array[ctypes.c_uint32]:
    return (ctypes.c_uint32 * len(values))(*values)


def _validated_identity(observed: str, expected: str) -> str:
    if observed != expected:
        message = f"candidate event timeline identity drifted: {observed}"
        raise RuntimeError(message)
    return observed


if __name__ == "__main__":
    raise SystemExit(main())
