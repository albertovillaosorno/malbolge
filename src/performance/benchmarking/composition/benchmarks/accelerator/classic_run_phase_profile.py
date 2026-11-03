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
#   - Phase-separated diagnostics for resident classic CUDA execution.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Phase-separated diagnostics for resident classic CUDA execution."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from statistics import median
from typing import TYPE_CHECKING, Final

from accelerator.cuda.classic_run import CudaClassicRunAdapter

from benchmarks.accelerator.classic_workload import (
    STEP_BUDGET,
    WORKLOAD_DESCRIPTION,
    classic_noop_request,
    validate_classic_noop_results,
)

if TYPE_CHECKING:
    from accelerator.classic_run import ClassicRunRequest
    from accelerator.cuda.classic_run import ClassicRunPhaseProfile

BATCH_SIZES: Final = (1, 8, 32, 128)
SAMPLE_COUNT: Final = 15
_SOURCE_JSON_ENCODER: Final = json.JSONEncoder


@dataclass(frozen=True, slots=True)
class PhaseSummary:
    """Median phase costs for one batch size."""

    allocate_ns: int
    batch_size: int
    decode_ns: int
    download_ns: int
    host_build_ns: int
    kernel_ns: int
    release_ns: int
    total_ns: int
    upload_ns: int
    validation_plan_ns: int


class ClassicPhaseReportError(ValueError):
    """Retained classic CUDA evidence could not be published."""


def _render_report(payload: object) -> str:
    """Corroborate public JSON against source-bound native encoding."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"classic phase JSON writer failed: {type(error).__name__}"
        raise ClassicPhaseReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "classic phase JSON writer differs from source"
        raise ClassicPhaseReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Reject incomplete native write acknowledgements and failed flushes."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"classic phase stdout write failed: {type(error).__name__}"
        raise ClassicPhaseReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "classic phase stdout write incomplete"
        raise ClassicPhaseReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"classic phase stdout flush failed: {type(error).__name__}"
        raise ClassicPhaseReportError(message) from error
    if flushed is not None:
        message = "classic phase stdout flush incomplete"
        raise ClassicPhaseReportError(message)


def main() -> int:
    """Measure exact classic CUDA phases using adapter diagnostics.

    Returns:
        Zero after emitting raw and median phase evidence as JSON.

    """
    request = classic_noop_request()
    with CudaClassicRunAdapter() as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
        plan = adapter.plan((request,) * max(BATCH_SIZES))
    payload = {
        "backend": capability.backend_id,
        "device": {
            "arch": capability.device_arch,
            "free_memory_bytes": plan.resources.free_memory_bytes,
            "max_threads_per_block": plan.resources.max_threads_per_block,
            "multiprocessor_count": plan.resources.multiprocessor_count,
            "name": capability.device_name,
            "total_memory_bytes": plan.resources.total_memory_bytes,
        },
        "rows": [
            {
                "batch_size": summary.batch_size,
                "median": asdict(summary),
                "samples": [asdict(sample) for sample in samples],
            }
            for summary, samples in rows
        ],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "workload": WORKLOAD_DESCRIPTION,
    }
    _publish_report(_render_report(payload))
    return 0


def _measure(
    adapter: CudaClassicRunAdapter,
    request: ClassicRunRequest,
    batch_size: int,
) -> tuple[PhaseSummary, tuple[ClassicRunPhaseProfile, ...]]:
    requests = (request,) * batch_size
    validate_classic_noop_results(adapter.evaluate(requests), batch_size)
    samples: list[ClassicRunPhaseProfile] = []
    for _ in range(SAMPLE_COUNT):
        results, profile = adapter.profile_evaluate(requests)
        validate_classic_noop_results(results, batch_size)
        samples.append(profile)
    frozen = tuple(samples)
    return _summarize(batch_size, frozen), frozen


def _summarize(
    batch_size: int,
    samples: tuple[ClassicRunPhaseProfile, ...],
) -> PhaseSummary:
    return PhaseSummary(
        allocate_ns=_median_values(tuple(sample.allocate_ns for sample in samples)),
        batch_size=batch_size,
        decode_ns=_median_values(tuple(sample.decode_ns for sample in samples)),
        download_ns=_median_values(tuple(sample.download_ns for sample in samples)),
        host_build_ns=_median_values(tuple(sample.host_build_ns for sample in samples)),
        kernel_ns=_median_values(tuple(sample.kernel_ns for sample in samples)),
        release_ns=_median_values(tuple(sample.release_ns for sample in samples)),
        total_ns=_median_values(tuple(sample.total_ns for sample in samples)),
        upload_ns=_median_values(tuple(sample.upload_ns for sample in samples)),
        validation_plan_ns=_median_values(
            tuple(sample.validation_plan_ns for sample in samples)
        ),
    )


def _median_values(values: tuple[int, ...]) -> int:
    return int(median(values))


if __name__ == "__main__":
    raise SystemExit(main())
