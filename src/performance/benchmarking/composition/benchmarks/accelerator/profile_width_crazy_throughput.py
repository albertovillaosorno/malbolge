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
#   - Equivalent-work crazy-heavy CUDA throughput across adaptive widths.
# - Must-Not:
#   - Treat timing as width-proof authority or time result validation.
# - Allows:
#   - Inputs: reviewed adaptive widths N10 through N14.
#   - Outputs: raw resident and end-to-end timing samples with exact identity.
#   - Side effects: CUDA execution and JSON output only.
# - Split-When:
#   - Split when another compute-heavy workload needs separate semantics.
# - Merge-When:
#   - Merge when another benchmark owns this exact crazy-heavy width sweep.
# - Summary:
#   - Equivalent 16,384-step crazy-heavy CUDA throughput for N10 through N14.
# - Description:
#   - Measures identical `p` work both resident-only and end-to-end by width.
# - Usage:
#   - Run from a clean commit and retain output with exact device provenance.
# - Defaults:
#   - One warmup and fifteen retained samples per route and width.
#

"""Equivalent crazy-heavy CUDA throughput for adaptive widths N10-N14."""

from __future__ import annotations

from array import array
from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.classic_step import XLAT2
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunRequest
from accelerator.profile_run import validate_profile_run_requests

from benchmarks.accelerator.profile_width_throughput import (
    profile_width_geometry,
)

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunGeometry
    from accelerator.profile_run import ProfileRunResult

BENCHMARK_ID: Final = "cuda-profile-width-crazy-throughput-v1"
BATCH_SIZE: Final = 1
MINIMUM_WIDTH: Final = 10
MAXIMUM_WIDTH: Final = 14
WIDTHS: Final = tuple(range(MINIMUM_WIDTH, MAXIMUM_WIDTH + 1))
CRAZY_DECODED: Final = ord("p")
ENCODING_BASE: Final = 33
DATA_START: Final = 32_768
STEP_BUDGET: Final = 16_384
DATA_STOP: Final = DATA_START + STEP_BUDGET
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
WORD_BYTES: Final = 4
WORKLOAD_ID: Final = "profile-16384-crazy-disjoint-data-v1"
END_TO_END_REGION: Final = "CudaProfileRunAdapter.evaluate"
RESIDENT_REGION: Final = "CudaProfileRunSession.advance"


@dataclass(frozen=True, slots=True)
class CrazyWidthThroughputRow:
    """Raw and summary measurements for one exact crazy-heavy width."""

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


def profile_width_crazy_geometry(word_trits: int) -> ProfileRunGeometry:
    """Return exact resident geometry for one benchmark-admitted width.

    Returns:
        Validated explicit resident geometry.

    Raises:
        ValueError: If width is outside N10 through N14.

    """
    if word_trits not in WIDTHS:
        message = (
            f"crazy width benchmark requires one of {WIDTHS}: {word_trits}"
        )
        raise ValueError(message)
    return profile_width_geometry(word_trits)


def profile_width_crazy_request(word_trits: int) -> ProfileRunRequest:
    """Build one request with 16,384 disjoint sequential crazy transitions.

    Returns:
        Validated complete-state request for the exact benchmark width.

    """
    geometry = profile_width_crazy_geometry(word_trits)
    request = ProfileRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=DATA_START,
        input_bytes=(),
        input_consumed=0,
        memory=ProfileMemoryImage(geometry, _initial_memory(geometry)),
        output_bytes=(),
        step_budget=STEP_BUDGET,
        termination=StepTermination.NONE,
    )
    return validate_profile_run_requests(geometry, (request,))[0]


def expected_profile_width_crazy_memory(word_trits: int) -> array[int]:
    """Return exact full memory after the benchmark's crazy-heavy run.

    Returns:
        Complete expected post-run memory image.

    """
    geometry = profile_width_crazy_geometry(word_trits)
    memory = _initial_memory(geometry)
    for code_pointer in range(STEP_BUDGET):
        value = memory[code_pointer]
        memory[code_pointer] = XLAT2[value - ENCODING_BASE]
    alternating = (geometry.word_modulus - 1) // 2
    for offset in range(STEP_BUDGET):
        memory[DATA_START + offset] = alternating if offset % 2 == 0 else 0
    return memory


def validate_profile_width_crazy_results(
    results: tuple[ProfileRunResult, ...],
    geometry: ProfileRunGeometry,
    expected_memory: array[int],
) -> None:
    """Require exact completion and full memory for one crazy-heavy run.

    Raises:
        RuntimeError: If observable execution or materialized state drifts.

    """
    if len(results) != BATCH_SIZE:
        message = "crazy width benchmark returned wrong result count"
        raise RuntimeError(message)
    result = results[0]
    if _result_identity(result) != _expected_identity():
        message = "crazy width benchmark result drifted from equivalent work"
        raise RuntimeError(message)
    if len(result.memory) != geometry.memory_words:
        message = "crazy width benchmark returned wrong memory geometry"
        raise RuntimeError(message)
    if result.memory != expected_memory:
        message = "crazy width benchmark returned wrong final memory"
        raise RuntimeError(message)


def main() -> int:
    """Measure identical crazy-heavy work at every admitted benchmark width.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    rows: list[CrazyWidthThroughputRow] = []
    device: dict[str, str] | None = None
    backend: str | None = None
    for word_trits in WIDTHS:
        geometry = profile_width_crazy_geometry(word_trits)
        request = profile_width_crazy_request(word_trits)
        expected = expected_profile_width_crazy_memory(word_trits)
        with CudaProfileRunAdapter(geometry) as adapter:
            if device is None:
                capability = adapter.capability()
                backend = capability.backend_id
                device = {
                    "arch": capability.device_arch,
                    "name": capability.device_name,
                }
            rows.append(
                _measure(
                    adapter,
                    request,
                    geometry,
                    expected_memory=expected,
                )
            )
    payload = {
        "backend": backend,
        "batch_size": BATCH_SIZE,
        "benchmark_id": BENCHMARK_ID,
        "device": device,
        "end_to_end_region": END_TO_END_REGION,
        "resident_region": RESIDENT_REGION,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "warmup_count": WARMUP_COUNT,
        "widths": WIDTHS,
        "workload_id": WORKLOAD_ID,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    geometry: ProfileRunGeometry,
    *,
    expected_memory: array[int],
) -> CrazyWidthThroughputRow:
    for _ in range(WARMUP_COUNT):
        results = adapter.evaluate((request,))
        validate_profile_width_crazy_results(results, geometry, expected_memory)
        _ = _resident_elapsed(
            adapter, request, geometry, expected_memory=expected_memory
        )
    end_to_end = [
        _evaluate_elapsed(
            adapter, request, geometry, expected_memory=expected_memory
        )
        for _ in range(SAMPLE_COUNT)
    ]
    resident = [
        _resident_elapsed(
            adapter, request, geometry, expected_memory=expected_memory
        )
        for _ in range(SAMPLE_COUNT)
    ]
    return _row(geometry, end_to_end, resident)


def _evaluate_elapsed(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    geometry: ProfileRunGeometry,
    *,
    expected_memory: array[int],
) -> int:
    start = perf_counter_ns()
    results = adapter.evaluate((request,))
    elapsed = perf_counter_ns() - start
    validate_profile_width_crazy_results(results, geometry, expected_memory)
    return elapsed


def _resident_elapsed(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    geometry: ProfileRunGeometry,
    *,
    expected_memory: array[int],
) -> int:
    with adapter.open_session((request,), max_runs=1) as session:
        start = perf_counter_ns()
        session.advance()
        elapsed = perf_counter_ns() - start
        results = session.snapshot()
    validate_profile_width_crazy_results(results, geometry, expected_memory)
    return elapsed


def _row(
    geometry: ProfileRunGeometry,
    end_to_end: list[int],
    resident: list[int],
) -> CrazyWidthThroughputRow:
    end_median = int(median(end_to_end))
    resident_median = int(median(resident))
    return CrazyWidthThroughputRow(
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


def _initial_memory(geometry: ProfileRunGeometry) -> array[int]:
    memory = array("I", [0]) * geometry.memory_words
    target_index = _crazy_target_index()
    for code_pointer in range(STEP_BUDGET):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        memory[code_pointer] = ENCODING_BASE + encoded_index
    return memory


def _crazy_target_index() -> int:
    try:
        return XLAT1.index(CRAZY_DECODED)
    except ValueError as error:
        message = "reviewed XLAT1 table has no benchmark crazy decode"
        raise RuntimeError(message) from error


def _result_identity(result: ProfileRunResult) -> tuple[object, ...]:
    return (
        result.status,
        result.error,
        result.steps,
        result.termination,
        result.accumulator,
        result.code_pointer,
        result.data_pointer,
        result.input_consumed,
        result.output_bytes,
    )


def _expected_identity() -> tuple[object, ...]:
    return (
        RunStatus.BUDGET_EXHAUSTED,
        RunError.NONE,
        STEP_BUDGET,
        StepTermination.NONE,
        0,
        STEP_BUDGET,
        DATA_STOP,
        0,
        (),
    )


if __name__ == "__main__":
    raise SystemExit(main())
