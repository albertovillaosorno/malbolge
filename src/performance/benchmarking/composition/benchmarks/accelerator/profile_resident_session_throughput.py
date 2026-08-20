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
#   - Steady-state throughput of resident current-profile CUDA sessions.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Steady-state throughput of resident current-profile CUDA sessions."""

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

from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.profile_run import CudaProfileRunAdapter

from benchmarks.accelerator.profile_workload import GEOMETRY
from benchmarks.accelerator.profile_workload import PROFILE_TRITS
from benchmarks.accelerator.profile_workload import PROFILE_WORDS
from benchmarks.accelerator.profile_workload import WORD_BYTES
from benchmarks.accelerator.profile_workload import profile_noop_request

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunObservation
    from accelerator.profile_run import ProfileRunRequest

BATCH_SIZES: Final = (1, 8, 32, 128)
SAMPLE_COUNT: Final = 15
SEGMENT_STEPS: Final = 64
PREPARED_STEPS: Final = SAMPLE_COUNT * SEGMENT_STEPS


@dataclass(frozen=True, slots=True)
class ResidentProfileThroughputRow:
    """Raw steady-resident launch samples for one current-profile batch."""

    batch_size: int
    median_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    vm_segments_per_second: float
    vm_steps_per_second: float


def main() -> int:
    """Measure repeated current-profile launches with state already resident.

    Returns:
        Zero after emitting raw steady-resident timing evidence as JSON.

    """
    request = profile_noop_request(
        step_budget=SEGMENT_STEPS,
        prepared_steps=PREPARED_STEPS,
    )
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
    payload = {
        "backend": capability.backend_id,
        "batch_sizes": BATCH_SIZES,
        "device": {
            "arch": capability.device_arch,
            "name": capability.device_name,
        },
        "geometry": {
            "memory_bytes_per_vm": PROFILE_WORDS * WORD_BYTES,
            "memory_words": PROFILE_WORDS,
            "word_trits": PROFILE_TRITS,
        },
        "prepared_steps": PREPARED_STEPS,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": SEGMENT_STEPS,
        "timed_region": "CudaProfileRunSession.advance only",
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> ResidentProfileThroughputRow:
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
    return ResidentProfileThroughputRow(
        batch_size=batch_size,
        median_ns=median_ns,
        pstdev_ns=pstdev(raw),
        raw_ns=tuple(raw),
        vm_segments_per_second=segments_per_second,
        vm_steps_per_second=segments_per_second * SEGMENT_STEPS,
    )


def _validate_observations(
    observations: tuple[ProfileRunObservation, ...],
    batch_size: int,
) -> None:
    if len(observations) != batch_size:
        message = "resident profile benchmark returned wrong observation count"
        raise RuntimeError(message)
    for observation in observations:
        _validate_observation(observation)


def _validate_observation(observation: ProfileRunObservation) -> None:
    if observation.code_pointer != PREPARED_STEPS:
        message = (
            "resident profile benchmark executed wrong cumulative code span"
        )
        raise RuntimeError(message)
    if observation.steps != SEGMENT_STEPS:
        message = "resident profile benchmark last segment has wrong step count"
        raise RuntimeError(message)
    if observation.status != RunStatus.BUDGET_EXHAUSTED:
        message = "resident profile benchmark unexpectedly terminated"
        raise RuntimeError(message)
    if observation.termination != StepTermination.NONE:
        message = "resident profile benchmark gained unexpected termination"
        raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
