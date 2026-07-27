# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Reproducible resource-plan scenarios for accelerator budgeting research."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import sys
from typing import Final

from accelerator.cuda.runtime import CudaRuntime
from accelerator.resource_budget import AcceleratorResources
from accelerator.resource_budget import plan_resident_batches

MIB: Final = 1024 * 1024
GIB: Final = 1024 * MIB
CURRENT_STATE_BYTES: Final = (4_782_969 * 4) + 64
CLASSIC_STATE_BYTES: Final = (59_049 * 4) + 64
SCENARIO_ITEMS: Final = 10_000
CUDA_FLAG: Final = "--cuda"


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Serializable summary of one resource-plan scenario."""

    first_chunk_items: int
    item_bytes: int
    label: str
    reserve_bytes: int
    synthetic: bool
    total_chunks: int
    usable_memory_bytes: int


def main() -> int:
    """Emit deterministic synthetic scenarios and optional live CUDA evidence.

    Returns:
        Zero after writing one JSON document to stdout.

    Raises:
        SystemExit: If an unsupported command-line argument is present.

    """
    arguments = tuple(sys.argv[1:])
    unknown = tuple(value for value in arguments if value != CUDA_FLAG)
    if unknown:
        message = f"unknown arguments: {unknown!r}"
        raise SystemExit(message)
    include_cuda = CUDA_FLAG in arguments
    results = list(_synthetic_results())
    device: dict[str, str | int] | None = None
    if include_cuda:
        device, live_results = _cuda_results()
        results.extend(live_results)
    payload = {
        "device": device,
        "research_id": "adaptive-accelerator-resource-budgeting",
        "scenarios": [asdict(result) for result in results],
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _cuda_results() -> tuple[dict[str, str | int], tuple[ScenarioResult, ...]]:
    runtime = CudaRuntime()
    try:
        resources = runtime.resources.snapshot()
        info = runtime.device_info
        device = {
            "arch": info.arch,
            "free_memory_bytes": resources.free_memory_bytes,
            "max_threads_per_block": info.max_threads_per_block,
            "multiprocessor_count": info.multiprocessor_count,
            "name": info.name,
            "total_memory_bytes": resources.total_memory_bytes,
        }
        results = (
            _scenario(
                "live-classic",
                CLASSIC_STATE_BYTES,
                resources,
                synthetic=False,
            ),
            _scenario(
                "live-current-model",
                CURRENT_STATE_BYTES,
                resources,
                synthetic=False,
            ),
        )
        return device, results
    finally:
        runtime.close()


def _synthetic_results() -> tuple[ScenarioResult, ...]:
    tiny = AcceleratorResources(
        free_memory_bytes=128 * MIB,
        max_threads_per_block=1,
        multiprocessor_count=1,
        total_memory_bytes=128 * MIB,
    )
    large = AcceleratorResources(
        free_memory_bytes=80 * GIB,
        max_threads_per_block=1,
        multiprocessor_count=1,
        total_memory_bytes=80 * GIB,
    )
    return (
        _scenario(
            "synthetic-128m-current",
            CURRENT_STATE_BYTES,
            tiny,
            synthetic=True,
        ),
        _scenario(
            "synthetic-80g-current",
            CURRENT_STATE_BYTES,
            large,
            synthetic=True,
        ),
    )


def _scenario(
    label: str,
    item_bytes: int,
    resources: AcceleratorResources,
    *,
    synthetic: bool,
) -> ScenarioResult:
    plan = plan_resident_batches((item_bytes,) * SCENARIO_ITEMS, resources)
    first = plan.chunks[0]
    return ScenarioResult(
        first_chunk_items=first.item_count,
        item_bytes=item_bytes,
        label=label,
        reserve_bytes=plan.reserve_bytes,
        synthetic=synthetic,
        total_chunks=len(plan.chunks),
        usable_memory_bytes=plan.usable_memory_bytes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
