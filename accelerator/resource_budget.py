# File:
#   - resource_budget.py
# Path:
#   - accelerator/resource_budget.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Hardware-neutral accelerator resource snapshots and batch planning.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Hardware-neutral accelerator resource snapshots and batch planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MINIMUM_RESERVE_BYTES: Final = 8 * 1024 * 1024
RESERVE_DIVISOR: Final = 16


class ResourceBudgetError(ValueError):
    """Accelerator resources cannot admit the requested resident workload."""


@dataclass(frozen=True, slots=True)
class AcceleratorResources:
    """Measured accelerator memory and coarse compute capacity."""

    free_memory_bytes: int
    max_threads_per_block: int
    multiprocessor_count: int
    total_memory_bytes: int

    def validated(self) -> AcceleratorResources:
        """Validate measured resource invariants.

        Returns:
            The unchanged resource snapshot.

        Raises:
            ResourceBudgetError: If a measured value is contradictory.

        """
        if self.total_memory_bytes <= 0:
            message = "total accelerator memory must be positive"
            raise ResourceBudgetError(message)
        if not 0 <= self.free_memory_bytes <= self.total_memory_bytes:
            message = "free accelerator memory is inconsistent"
            raise ResourceBudgetError(message)
        if self.max_threads_per_block <= 0:
            message = "max threads per block must be positive"
            raise ResourceBudgetError(message)
        if self.multiprocessor_count <= 0:
            message = "multiprocessor count must be positive"
            raise ResourceBudgetError(message)
        return self


@dataclass(frozen=True, slots=True)
class BatchChunk:
    """One input-order-preserving resident allocation chunk."""

    bytes_required: int
    start: int
    stop: int

    @property
    def item_count(self) -> int:
        """Number of items in this half-open chunk."""
        return self.stop - self.start


@dataclass(frozen=True, slots=True)
class ResourcePlan:
    """Deterministic resident batching plan for one measured device snapshot."""

    chunks: tuple[BatchChunk, ...]
    compute_wave_items: int
    reserve_bytes: int
    resources: AcceleratorResources
    usable_memory_bytes: int


def plan_resident_batches(
    item_bytes: tuple[int, ...],
    resources: AcceleratorResources,
    *,
    fixed_chunk_bytes: int = 0,
    max_items_per_chunk: int | None = None,
) -> ResourcePlan:
    """Partition resident items under measured memory without a fixed batch cap.

    Returns:
        Stable input-order chunks whose requested bytes fit the measured budget.
        An optional per-chunk item bound represents backend integer/layout
        limits, never an accelerator-memory ceiling.

    Raises:
        ResourceBudgetError: If the snapshot, layout, or one item cannot fit.

    """
    snapshot = resources.validated()
    if fixed_chunk_bytes < 0:
        message = "fixed chunk bytes cannot be negative"
        raise ResourceBudgetError(message)
    if any(value <= 0 for value in item_bytes):
        message = "resident item bytes must all be positive"
        raise ResourceBudgetError(message)
    if max_items_per_chunk is not None and max_items_per_chunk <= 0:
        message = "maximum items per chunk must be positive when declared"
        raise ResourceBudgetError(message)
    reserve = max(
        MINIMUM_RESERVE_BYTES,
        snapshot.total_memory_bytes // RESERVE_DIVISOR,
    )
    usable = max(0, snapshot.free_memory_bytes - reserve)
    compute_wave = (
        snapshot.multiprocessor_count * snapshot.max_threads_per_block
    )
    if not item_bytes:
        return ResourcePlan((), compute_wave, reserve, snapshot, usable)
    chunks = _greedy_chunks(
        item_bytes,
        usable,
        fixed_chunk_bytes,
        max_items_per_chunk=max_items_per_chunk,
    )
    return ResourcePlan(tuple(chunks), compute_wave, reserve, snapshot, usable)


def _greedy_chunks(
    item_bytes: tuple[int, ...],
    usable_bytes: int,
    fixed_chunk_bytes: int,
    *,
    max_items_per_chunk: int | None,
) -> list[BatchChunk]:
    chunks: list[BatchChunk] = []
    start = 0
    required = fixed_chunk_bytes
    for index, byte_count in enumerate(item_bytes):
        single = fixed_chunk_bytes + byte_count
        if single > usable_bytes:
            message = (
                f"resident item {index} requires {single} bytes but only "
                f"{usable_bytes} bytes are budgeted"
            )
            raise ResourceBudgetError(message)
        memory_full = required + byte_count > usable_bytes
        count_full = (
            max_items_per_chunk is not None
            and index - start >= max_items_per_chunk
        )
        if index > start and (memory_full or count_full):
            chunks.append(BatchChunk(required, start, index))
            start = index
            required = fixed_chunk_bytes
        required += byte_count
    chunks.append(BatchChunk(required, start, len(item_bytes)))
    return chunks
