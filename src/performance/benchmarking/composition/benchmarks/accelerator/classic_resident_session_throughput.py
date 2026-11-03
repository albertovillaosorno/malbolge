# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Steady-state throughput of already-resident classic CUDA sessions.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Steady-state throughput of already-resident classic CUDA sessions."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from statistics import median, pstdev
from time import perf_counter_ns
from typing import TYPE_CHECKING, Final

from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_run import CudaClassicRunAdapter

from benchmarks.accelerator.classic_workload import classic_noop_request

if TYPE_CHECKING:
    from accelerator.classic_run import ClassicRunObservation, ClassicRunRequest

BATCH_SIZES: Final = (1, 8, 32, 128)
SAMPLE_COUNT: Final = 15
SEGMENT_STEPS: Final = 64
PREPARED_STEPS: Final = SAMPLE_COUNT * SEGMENT_STEPS
_SOURCE_JSON_ENCODER: Final = json.JSONEncoder


@dataclass(frozen=True, slots=True)
class ResidentThroughputRow:
    """Raw steady-resident launch samples for one batch size."""

    batch_size: int
    median_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    vm_segments_per_second: float
    vm_steps_per_second: float


class ResidentClassicReportError(ValueError):
    """Retained resident CUDA throughput evidence could not be published."""


def _render_report(payload: object) -> str:
    """Require public JSON to match source-bound native encoding."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"resident classic JSON writer failed: {type(error).__name__}"
        raise ResidentClassicReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "resident classic JSON writer differs from source"
        raise ResidentClassicReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Require an exact stdout write receipt and a successful void flush."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"resident classic stdout write failed: {type(error).__name__}"
        raise ResidentClassicReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "resident classic stdout write incomplete"
        raise ResidentClassicReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"resident classic stdout flush failed: {type(error).__name__}"
        raise ResidentClassicReportError(message) from error
    if flushed is not None:
        message = "resident classic stdout flush incomplete"
        raise ResidentClassicReportError(message)


def main() -> int:
    """Measure repeated kernel launches with VM state already resident.

    Returns:
        Zero after emitting raw steady-resident timing evidence as JSON.

    """
    request = classic_noop_request(
        step_budget=SEGMENT_STEPS,
        prepared_steps=PREPARED_STEPS,
    )
    with CudaClassicRunAdapter() as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
    payload = {
        "backend": capability.backend_id,
        "batch_sizes": BATCH_SIZES,
        "device": {
            "arch": capability.device_arch,
            "name": capability.device_name,
        },
        "prepared_steps": PREPARED_STEPS,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": SEGMENT_STEPS,
        "timed_region": "CudaClassicRunSession.advance only",
    }
    _publish_report(_render_report(payload))
    return 0


def _measure(
    adapter: CudaClassicRunAdapter,
    request: ClassicRunRequest,
    batch_size: int,
) -> ResidentThroughputRow:
    requests = (request,) * batch_size
    raw: list[int] = []
    with adapter.open_session(requests, max_runs=SAMPLE_COUNT) as session:
        for _ in range(SAMPLE_COUNT):
            start = perf_counter_ns()
            session.advance()
            raw.append(perf_counter_ns() - start)
        observations = session.observe()
    _validate_observations(observations, batch_size)
    median_ns = int(median(raw))
    segments_per_second = (batch_size * 1_000_000_000) / median_ns
    return ResidentThroughputRow(
        batch_size=batch_size,
        median_ns=median_ns,
        pstdev_ns=pstdev(raw),
        raw_ns=tuple(raw),
        vm_segments_per_second=segments_per_second,
        vm_steps_per_second=segments_per_second * SEGMENT_STEPS,
    )


def _validate_observations(
    observations: tuple[ClassicRunObservation, ...],
    batch_size: int,
) -> None:
    if len(observations) != batch_size:
        message = "resident benchmark returned wrong observation count"
        raise RuntimeError(message)
    for observation in observations:
        _validate_observation(observation)


def _validate_observation(observation: ClassicRunObservation) -> None:
    if observation.code_pointer != PREPARED_STEPS:
        message = "resident benchmark executed wrong cumulative code span"
        raise RuntimeError(message)
    if observation.steps != SEGMENT_STEPS:
        message = "resident benchmark last segment has wrong step count"
        raise RuntimeError(message)
    if observation.status != RunStatus.BUDGET_EXHAUSTED:
        message = "resident benchmark unexpectedly terminated"
        raise RuntimeError(message)
    if observation.termination != StepTermination.NONE:
        message = "resident benchmark gained unexpected termination"
        raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
