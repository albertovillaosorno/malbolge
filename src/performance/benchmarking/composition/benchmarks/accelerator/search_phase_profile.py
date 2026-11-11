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
#   - Raw phase samples for one identical CPU/CUDA bounded search.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Raw phase samples for one identical CPU/CUDA bounded search."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import median, pstdev
from typing import TYPE_CHECKING, Final

from accelerator.cuda import CudaExactPrimitiveAdapter
from optimizer.rotate_target import (
    ROTATE_TARGET_ALGORITHM_ID,
    cpu_rotate_target_search_adapter,
    rotate_target_search_adapter,
)

from benchmarks.accelerator.search_workload import (
    CORPUS_SIZE,
    CPU_BACKEND,
    CUDA_BACKEND,
    SEED,
    TARGET,
    WORKLOAD_ID,
    full_domain_rotate_target_workload,
    validate_search_benchmark_result,
)

if TYPE_CHECKING:
    from accelerator.evaluated_search import (
        EvaluatedSearchExecutionAdapter,
        EvaluatedSearchPhaseProfile,
    )

    from benchmarks.accelerator.search_workload import SearchBenchmarkWorkload

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
_SOURCE_JSON_ENCODER: Final = json.JSONEncoder
PHASE_NAMES: Final = (
    "request_validation_ns",
    "batch_build_ns",
    "batch_validation_ns",
    "backend_evaluation_ns",
    "proposal_selection_ns",
    "result_validation_ns",
    "total_ns",
)


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    """Raw and summary timing for one named search phase."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


class SearchPhaseReportError(ValueError):
    """Retained CPU/CUDA search evidence could not be published."""


def _render_report(payload: object) -> str:
    """Compare public search JSON to source-bound native encoding."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"search phase JSON writer failed: {type(error).__name__}"
        raise SearchPhaseReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "search phase JSON writer differs from source"
        raise SearchPhaseReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Reject incomplete native write and nonvoid flush acknowledgements."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"search phase stdout write failed: {type(error).__name__}"
        raise SearchPhaseReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "search phase stdout write incomplete"
        raise SearchPhaseReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"search phase stdout flush failed: {type(error).__name__}"
        raise SearchPhaseReportError(message) from error
    if flushed is not None:
        message = "search phase stdout flush incomplete"
        raise SearchPhaseReportError(message)


def main() -> int:
    """Measure identical full-domain search phases on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    cpu = cpu_rotate_target_search_adapter()
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        cpu_phases = _measure(cpu, workload, CPU_BACKEND)
        cuda_phases = _measure(cuda, workload, CUDA_BACKEND)
        capability = primitive.capability()
    payload = {
        "benchmark_id": "rotate-target-search-phase-profile-v1",
        "workload": {
            "algorithm_id": ROTATE_TARGET_ALGORITHM_ID,
            "corpus_size": CORPUS_SIZE,
            "evaluation_budget": CORPUS_SIZE,
            "identity": WORKLOAD_ID,
            "problem_sha256": sha256(workload.problem).hexdigest(),
            "seed": SEED,
            "target": TARGET,
        },
        "measurement": {
            "adapter_setup_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": capability.device_arch,
            "backend": capability.backend_id,
            "name": capability.device_name,
        },
        "cpu": {name: asdict(value) for name, value in cpu_phases.items()},
        "cuda": {name: asdict(value) for name, value in cuda_phases.items()},
    }
    _publish_report(_render_report(payload))
    return 0


def _measure(
    adapter: EvaluatedSearchExecutionAdapter,
    workload: SearchBenchmarkWorkload,
    backend_id: str,
) -> dict[str, PhaseTiming]:
    for _ in range(WARMUP_COUNT):
        profiled = adapter.profile_search(workload.request)
        _validate_profile(profiled.phases)
        validate_search_benchmark_result(
            profiled.result,
            backend_id,
            workload.verifier,
        )
    raw: dict[str, list[int]] = {name: [] for name in PHASE_NAMES}
    for _ in range(SAMPLE_COUNT):
        profiled = adapter.profile_search(workload.request)
        _validate_profile(profiled.phases)
        validate_search_benchmark_result(
            profiled.result,
            backend_id,
            workload.verifier,
        )
        values = _phase_values(profiled.phases)
        for name in PHASE_NAMES:
            raw[name].append(values[name])
    return {name: _timing(samples) for name, samples in raw.items()}


def _phase_values(
    phases: EvaluatedSearchPhaseProfile,
) -> dict[str, int]:
    return {
        "request_validation_ns": phases.request_validation_ns,
        "batch_build_ns": phases.batch_build_ns,
        "batch_validation_ns": phases.batch_validation_ns,
        "backend_evaluation_ns": phases.backend_evaluation_ns,
        "proposal_selection_ns": phases.proposal_selection_ns,
        "result_validation_ns": phases.result_validation_ns,
        "total_ns": phases.total_ns,
    }


def _validate_profile(phases: EvaluatedSearchPhaseProfile) -> None:
    measured = (
        phases.request_validation_ns,
        phases.batch_build_ns,
        phases.batch_validation_ns,
        phases.backend_evaluation_ns,
        phases.proposal_selection_ns,
        phases.result_validation_ns,
    )
    if any(value < 0 for value in measured):
        message = "search phase benchmark returned a negative duration"
        raise RuntimeError(message)
    if phases.total_ns < sum(measured):
        message = "search phase benchmark total is smaller than named phases"
        raise RuntimeError(message)


def _timing(samples: list[int]) -> PhaseTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "search phase benchmark retained the wrong sample count"
        raise RuntimeError(message)
    return PhaseTiming(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


if __name__ == "__main__":
    raise SystemExit(main())
