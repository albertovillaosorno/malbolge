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
#   - Reproducible resource-plan scenarios for accelerator budgeting research.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Reproducible resource-plan scenarios for accelerator budgeting research."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import sys
from typing import Final

from accelerator.classic_run import MAX_U32
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import STATE_WORDS
from accelerator.cuda.runtime import CudaRuntime
from accelerator.profile_run import WORD_BYTES
from accelerator.resource_budget import AcceleratorResources
from accelerator.resource_budget import plan_resident_batches

from benchmarks.accelerator.profile_workload import PROFILE_WORDS

MIB: Final = 1024 * 1024
GIB: Final = 1024 * MIB
CURRENT_STATE_BYTES: Final = (PROFILE_WORDS + STATE_WORDS) * WORD_BYTES
CLASSIC_STATE_BYTES: Final = (MEMORY_WORDS + STATE_WORDS) * WORD_BYTES
FIXED_CHUNK_BYTES: Final = 2 * WORD_BYTES
MINIMUM_ADAPTIVE_WIDTH: Final = 10
MAXIMUM_ADAPTIVE_WIDTH: Final = 14
SCENARIO_ITEMS: Final = 10_000
HUGE_GIB: Final = 100_000
HUGE_ITEMS: Final = 100_000
CLASSIC_PROTOCOL_ITEMS: Final = 72_736
CUDA_FLAG: Final = "--cuda"


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Static inputs for one reproducible planning scenario."""

    item_bytes: int
    label: str
    fixed_chunk_bytes: int = 0
    max_items_per_chunk: int | None = None
    memory_words: int | None = None
    requested_items: int = SCENARIO_ITEMS
    synthetic: bool = True
    word_trits: int | None = None


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Serializable summary of one resource-plan scenario."""

    first_chunk_items: int
    fixed_chunk_bytes: int
    item_bytes: int
    label: str
    max_items_per_chunk: int | None
    memory_words: int | None
    requested_items: int
    reserve_bytes: int
    synthetic: bool
    total_chunks: int
    usable_memory_bytes: int
    word_trits: int | None


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
    results = list(synthetic_results())
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
                ScenarioSpec(
                    item_bytes=CLASSIC_STATE_BYTES,
                    label="live-classic",
                    synthetic=False,
                ),
                resources,
            ),
            _scenario(
                ScenarioSpec(
                    item_bytes=CURRENT_STATE_BYTES,
                    label="live-current-model",
                    synthetic=False,
                ),
                resources,
            ),
        )
        return device, results
    finally:
        runtime.close()


def synthetic_results() -> tuple[ScenarioResult, ...]:
    """Return deterministic capacity-only resource planning evidence.

    Returns:
        Synthetic planner results, including the adaptive width sweep.

    """
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
    huge = AcceleratorResources(
        free_memory_bytes=HUGE_GIB * GIB,
        max_threads_per_block=1024,
        multiprocessor_count=1000,
        total_memory_bytes=HUGE_GIB * GIB,
    )
    adaptive = tuple(
        _scenario(spec, tiny) for spec in _adaptive_width_specs()
    )
    baseline = (
        _scenario(
            ScenarioSpec(
                item_bytes=CURRENT_STATE_BYTES,
                label="synthetic-128m-current",
            ),
            tiny,
        ),
        _scenario(
            ScenarioSpec(
                item_bytes=CURRENT_STATE_BYTES,
                label="synthetic-80g-current",
            ),
            large,
        ),
        _scenario(
            ScenarioSpec(
                item_bytes=CLASSIC_STATE_BYTES,
                label="synthetic-100000g-classic-protocol",
                max_items_per_chunk=CLASSIC_PROTOCOL_ITEMS,
                requested_items=HUGE_ITEMS,
            ),
            huge,
        ),
    )
    return (*adaptive, *baseline)


def _adaptive_width_specs() -> tuple[ScenarioSpec, ...]:
    return tuple(
        _adaptive_width_spec(width)
        for width in range(MINIMUM_ADAPTIVE_WIDTH, MAXIMUM_ADAPTIVE_WIDTH + 1)
    )


def _adaptive_width_spec(word_trits: int) -> ScenarioSpec:
    memory_words = 1
    for _ in range(word_trits):
        memory_words *= 3
    return ScenarioSpec(
        fixed_chunk_bytes=FIXED_CHUNK_BYTES,
        item_bytes=(memory_words + STATE_WORDS) * WORD_BYTES,
        label=f"synthetic-128m-width-{word_trits}",
        max_items_per_chunk=(MAX_U32 // memory_words) + 1,
        memory_words=memory_words,
        word_trits=word_trits,
    )


def _scenario(
    spec: ScenarioSpec,
    resources: AcceleratorResources,
) -> ScenarioResult:
    plan = plan_resident_batches(
        (spec.item_bytes,) * spec.requested_items,
        resources,
        fixed_chunk_bytes=spec.fixed_chunk_bytes,
        max_items_per_chunk=spec.max_items_per_chunk,
    )
    first = plan.chunks[0]
    return ScenarioResult(
        first_chunk_items=first.item_count,
        fixed_chunk_bytes=spec.fixed_chunk_bytes,
        item_bytes=spec.item_bytes,
        label=spec.label,
        max_items_per_chunk=spec.max_items_per_chunk,
        memory_words=spec.memory_words,
        requested_items=spec.requested_items,
        reserve_bytes=plan.reserve_bytes,
        synthetic=spec.synthetic,
        total_chunks=len(plan.chunks),
        usable_memory_bytes=plan.usable_memory_bytes,
        word_trits=spec.word_trits,
    )


if __name__ == "__main__":
    raise SystemExit(main())
