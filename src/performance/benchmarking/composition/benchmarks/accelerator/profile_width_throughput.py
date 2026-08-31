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
#   - Equivalent-work CUDA throughput evidence across adaptive widths.
# - Must-Not:
#   - Treat synthetic geometry as a canonical profile or time result validation.
# - Allows:
#   - Inputs: reviewed adaptive widths supported by resident profile execution.
#   - Outputs: raw timing samples and exact workload/device/geometry identity.
#   - Side effects: CUDA evaluation and JSON output only.
# - Split-When:
#   - Split when compute/search-heavy width evidence gains a separate workload.
# - Merge-When:
#   - Merge when another benchmark owns this exact width-sweep measurement.
# - Summary:
#   - Equivalent 64-step full-snapshot CUDA throughput from N10 through N15.
# - Description:
#   - Measures identical no-op work while full-state size varies by width.
# - Usage:
#   - Run from a clean commit and retain output with exact device provenance.
# - Defaults:
#   - One warmup and fifteen retained samples per width; batch size is one.
#

"""Equivalent 64-step full-snapshot CUDA throughput from N10 through N15."""

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
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest
from accelerator.profile_run import validate_profile_run_requests

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunResult

BENCHMARK_ID: Final = "cuda-profile-width-throughput-v1"
BATCH_SIZE: Final = 1
MINIMUM_WIDTH: Final = 10
MAXIMUM_WIDTH: Final = 15
WIDTHS: Final = tuple(range(MINIMUM_WIDTH, MAXIMUM_WIDTH + 1))
INPUT_INSTRUCTION: Final = ord("/")
OUTPUT_INSTRUCTION: Final = ord("<")
NOOP_DECODED: Final = ord("+")
SAMPLE_COUNT: Final = 15
STEP_BUDGET: Final = 64
WARMUP_COUNT: Final = 1
WORD_BYTES: Final = 4
WORKLOAD_ID: Final = "profile-64-noop-full-snapshot-v1"
TIMED_REGION: Final = "CudaProfileRunAdapter.evaluate"


@dataclass(frozen=True, slots=True)
class WidthThroughputRow:
    """Raw and summary measurements for one exact adaptive width."""

    items_per_second_at_median: float
    median_ns: int
    memory_bytes_per_vm: int
    memory_words: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    vm_steps_per_second_at_median: float
    word_trits: int


def profile_width_geometry(word_trits: int) -> ProfileRunGeometry:
    """Build one exact resident geometry for an admitted adaptive width.

    Returns:
        Validated geometry preserving the canonical profile I/O assignment.

    Raises:
        ValueError: If width is outside the reviewed benchmark set.

    """
    if word_trits not in WIDTHS:
        message = (
            f"profile width benchmark requires one of {WIDTHS}: {word_trits}"
        )
        raise ValueError(message)
    memory_words = _ternary_cardinality(word_trits)
    return ProfileRunGeometry(
        eof_word=memory_words - 1,
        input_instruction=INPUT_INSTRUCTION,
        memory_words=memory_words,
        output_instruction=OUTPUT_INSTRUCTION,
        word_modulus=memory_words,
        word_trits=word_trits,
    ).validated()


def profile_width_noop_request(word_trits: int) -> ProfileRunRequest:
    """Build one geometry-bound request with exactly 64 prepared no-op steps.

    Returns:
        Validated request whose complete memory size is determined by width.

    """
    geometry = profile_width_geometry(word_trits)
    memory = array("I", [0]) * geometry.memory_words
    target_index = _noop_target_index()
    for code_pointer in range(STEP_BUDGET):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        memory[code_pointer] = 33 + encoded_index
    request = ProfileRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=ProfileMemoryImage(geometry, memory),
        output_bytes=(),
        step_budget=STEP_BUDGET,
        termination=StepTermination.NONE,
    )
    return validate_profile_run_requests(geometry, (request,))[0]


def main() -> int:
    """Measure one equivalent semantic workload at every reviewed width.

    Returns:
        Zero after emitting raw timing evidence as one JSON document.

    """
    rows: list[WidthThroughputRow] = []
    device: dict[str, str | int] | None = None
    backend: str | None = None
    for word_trits in WIDTHS:
        geometry = profile_width_geometry(word_trits)
        request = profile_width_noop_request(word_trits)
        with CudaProfileRunAdapter(geometry) as adapter:
            if device is None:
                capability = adapter.capability()
                backend = capability.backend_id
                device = {
                    "arch": capability.device_arch,
                    "name": capability.device_name,
                }
            rows.append(_measure(adapter, request, geometry))
    payload = {
        "backend": backend,
        "batch_size": BATCH_SIZE,
        "benchmark_id": BENCHMARK_ID,
        "device": device,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "timed_region": TIMED_REGION,
        "warmup_count": WARMUP_COUNT,
        "widths": WIDTHS,
        "workload_id": WORKLOAD_ID,
        "workload": (
            "64 committed no-op transitions with one complete result snapshot "
            "per adaptive-width profile VM"
        ),
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    geometry: ProfileRunGeometry,
) -> WidthThroughputRow:
    for _ in range(WARMUP_COUNT):
        validate_profile_width_results(adapter.evaluate((request,)), geometry)
    raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        start = perf_counter_ns()
        results = adapter.evaluate((request,))
        elapsed = perf_counter_ns() - start
        validate_profile_width_results(results, geometry)
        raw.append(elapsed)
    median_ns = int(median(raw))
    items_per_second = 1_000_000_000 / median_ns
    return WidthThroughputRow(
        items_per_second_at_median=items_per_second,
        median_ns=median_ns,
        memory_bytes_per_vm=geometry.memory_words * WORD_BYTES,
        memory_words=geometry.memory_words,
        pstdev_ns=pstdev(raw),
        raw_ns=tuple(raw),
        vm_steps_per_second_at_median=items_per_second * STEP_BUDGET,
        word_trits=geometry.word_trits,
    )


def validate_profile_width_results(
    results: tuple[ProfileRunResult, ...],
    geometry: ProfileRunGeometry,
) -> None:
    """Require exact complete-snapshot completion for one timed width.

    Raises:
        RuntimeError: If observable execution or materialized state drifts.

    """
    if len(results) != BATCH_SIZE:
        message = "profile width benchmark returned wrong result count"
        raise RuntimeError(message)
    result = results[0]
    observed = (
        result.status,
        result.error,
        result.steps,
        result.termination,
        result.code_pointer,
        result.data_pointer,
        result.input_consumed,
        result.output_bytes,
        len(result.memory),
    )
    expected = (
        RunStatus.BUDGET_EXHAUSTED,
        RunError.NONE,
        STEP_BUDGET,
        StepTermination.NONE,
        STEP_BUDGET,
        STEP_BUDGET,
        0,
        (),
        geometry.memory_words,
    )
    if observed != expected:
        message = "profile width benchmark result drifted from equivalent work"
        raise RuntimeError(message)


def _ternary_cardinality(word_trits: int) -> int:
    value = 1
    for _ in range(word_trits):
        value *= 3
    return value


def _noop_target_index() -> int:
    try:
        return XLAT1.index(NOOP_DECODED)
    except ValueError as error:
        message = "reviewed XLAT1 table has no benchmark no-op decode"
        raise RuntimeError(message) from error


if __name__ == "__main__":
    raise SystemExit(main())
