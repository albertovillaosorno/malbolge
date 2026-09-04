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
#   - Benchmark-only tritwise versus lookup CUDA CRAZY candidate throughput.
# - Must-Not:
#   - Change product adapters, search semantics, or treat timing as
#     verification.
# - Allows:
#   - Inputs: canonical ordinary and projected full-domain CRAZY search words.
#   - Outputs: raw synchronous launch samples after exact CPU equality checks.
#   - Side effects: CUDA execution and stdout JSON only.
# - Split-When:
#   - Split when another candidate arithmetic width gains independent evidence.
# - Merge-When:
#   - Merge when another benchmark owns this exact two-kernel comparison.
# - Summary:
#   - Classic candidate CRAZY tritwise versus five-trit lookup throughput.
# - Description:
#   - Measures canonical search orders without changing the production kernel.
# - Usage:
#   - Run on a clean commit and retain results only after exact validation.
# - Defaults:
#   - One warmup and fifteen samples with alternating first-kernel order.
#

"""Benchmark-only CUDA CRAZY candidate arithmetic on canonical search orders."""

from __future__ import annotations

import ctypes
from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import CRAZY_TRIT_TABLE
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import PreparedCrazyTargetSelection
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import prepare_crazy_target_selection

from benchmarks.accelerator.crazy_lookup_address_fanout import (
    CRAZY_CHUNK_VALUES as FANOUT_CRAZY_CHUNK_VALUES,
)
from benchmarks.accelerator.crazy_lookup_address_fanout import ORDINARY_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import PREPARED_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import WORKLOAD_ID
from benchmarks.accelerator.crazy_search_workload import ACCUMULATOR
from benchmarks.accelerator.crazy_search_workload import (
    full_domain_crazy_target_workload,
)

BENCHMARK_ID: Final = "cuda-crazy-lookup-candidate-throughput-v1"
CRAZY_CHUNK_VALUES: Final = FANOUT_CRAZY_CHUNK_VALUES
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
TRITWISE: Final = "tritwise"
LOOKUP: Final = "lookup-5+5"
GEOMETRIES: Final = (TRITWISE, LOOKUP)
WORD_BYTES: Final = ctypes.sizeof(ctypes.c_uint32)


@dataclass(frozen=True, slots=True)
class CandidateThroughputRow:
    """Raw synchronous launch timing for one route and arithmetic geometry."""

    candidate_count: int
    geometry: str
    median_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    route_id: str


@dataclass(frozen=True, slots=True)
class _Workload:
    """One exact candidate order plus its trusted CRAZY outputs."""

    data: tuple[int, ...]
    expected: tuple[int, ...]
    route_id: str


@dataclass(slots=True)
class _DeviceWorkload:
    """Resident benchmark buffers for one exact candidate order."""

    host_output: ctypes.Array[ctypes.c_uint32]
    pointers: tuple[int, int, int]
    workload: _Workload


def crazy_chunk_table() -> tuple[int, ...]:
    """Return the exact row-major five-trit CRAZY lookup table.

    Returns:
        59,049 outputs indexed by ``data * 243 + accumulator``.

    """
    values = [
        _crazy_chunk(data, accumulator)
        for data in range(CRAZY_CHUNK_VALUES)
        for accumulator in range(CRAZY_CHUNK_VALUES)
    ]
    return tuple(values)


def candidate_lookup_kernel_source() -> str:
    """Return benchmark-only tritwise and five-trit lookup CUDA source.

    Returns:
        One NVRTC source exporting both exact classic CRAZY kernels.

    """
    table = ",".join(str(value) for value in crazy_chunk_table())
    table_size = CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES
    return f"""
#define CHUNK {CRAZY_CHUNK_VALUES}u
static __device__ __constant__ unsigned char TABLE[{table_size}] = {{
{table}
}};
static __device__ unsigned int ct(unsigned int d, unsigned int a) {{
    if (((d == 0u || d == 1u) && a == 0u) ||
        (d == 2u && a == 2u)) {{
        return 1u;
    }}
    if ((d == 1u && a == 2u) ||
        (d == 2u && (a == 0u || a == 1u))) {{
        return 2u;
    }}
    return 0u;
}}
extern "C" __global__ void crazy_tritwise(
    const unsigned int* d,
    const unsigned int* a,
    unsigned int* o,
    unsigned int n
) {{
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    unsigned int x = d[i], y = a[i], r = 0u, p = 1u;
    for (unsigned int t = 0u; t < 10u; ++t) {{
        r += ct(x % 3u, y % 3u) * p;
        p *= 3u; x /= 3u; y /= 3u;
    }}
    o[i] = r;
}}
extern "C" __global__ void crazy_lookup(
    const unsigned int* d,
    const unsigned int* a,
    unsigned int* o,
    unsigned int n
) {{
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    unsigned int x = d[i], y = a[i];
    unsigned int lo = TABLE[(x % CHUNK) * CHUNK + (y % CHUNK)];
    x /= CHUNK; y /= CHUNK;
    unsigned int hi = TABLE[(x % CHUNK) * CHUNK + (y % CHUNK)];
    o[i] = lo + (hi * CHUNK);
}}
"""


def main() -> int:
    """Measure exact classic candidate CRAZY on two CUDA arithmetic kernels.

    Returns:
        Zero after emitting complete raw timing and device identity JSON.

    """
    runtime = CudaRuntime()
    module: ctypes.c_void_p | None = None
    try:
        module = runtime.compile_module(
            candidate_lookup_kernel_source(),
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
            "rows": [asdict(row) for row in rows],
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
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
        message = "candidate throughput received invalid CRAZY selection proof"
        raise TypeError(message)
    _, accumulator, positions = selection.for_selection(workload.request, batch)
    if accumulator != ACCUMULATOR:
        message = "candidate throughput accumulator identity drifted"
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
) -> tuple[CandidateThroughputRow, ...]:
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
) -> dict[str, list[int]]:
    for _ in range(WARMUP_COUNT):
        for geometry in GEOMETRIES:
            _ = _sample(runtime, kernels[geometry], device)
    samples: dict[str, list[int]] = {
        geometry: [] for geometry in GEOMETRIES
    }
    for sample_index in range(SAMPLE_COUNT):
        for geometry in _sample_order(sample_index):
            elapsed = _sample(runtime, kernels[geometry], device)
            samples[geometry].append(elapsed)
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


def _sample(
    runtime: CudaRuntime,
    kernel: ctypes.c_void_p,
    device: _DeviceWorkload,
) -> int:
    start = perf_counter_ns()
    runtime.launch(kernel, device.pointers, len(device.workload.data))
    elapsed = perf_counter_ns() - start
    runtime.copy_from_device(device.host_output, device.pointers[-1])
    if tuple(device.host_output) != device.workload.expected:
        message = "benchmark CUDA CRAZY diverged from trusted CPU semantics"
        raise RuntimeError(message)
    return elapsed


def _sample_order(sample_index: int) -> tuple[str, ...]:
    if sample_index % 2 == 0:
        return GEOMETRIES
    return (LOOKUP, TRITWISE)


def _row(
    workload: _Workload,
    geometry: str,
    samples: list[int],
) -> CandidateThroughputRow:
    return CandidateThroughputRow(
        candidate_count=len(workload.data),
        geometry=geometry,
        median_ns=int(median(samples)),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
        route_id=workload.route_id,
    )


def _words(values: tuple[int, ...]) -> ctypes.Array[ctypes.c_uint32]:
    return (ctypes.c_uint32 * len(values))(*values)


def _crazy_chunk(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(5):
        result += CRAZY_TRIT_TABLE[data % 3][accumulator % 3] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


if __name__ == "__main__":
    raise SystemExit(main())
