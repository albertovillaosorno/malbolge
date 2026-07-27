# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Deterministic accelerator resource budgeting contract tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accelerator.resource_budget import AcceleratorResources
from accelerator.resource_budget import MINIMUM_RESERVE_BYTES
from accelerator.resource_budget import ResourceBudgetError
from accelerator.resource_budget import plan_resident_batches

if TYPE_CHECKING:
    from collections.abc import Callable

MIB = 1024 * 1024
GIB = 1024 * MIB
CLASSIC_STATE_BYTES = (59_049 * 4) + 64
CURRENT_STATE_BYTES = (4_782_969 * 4) + 64
FIXED_CHUNK_BYTES = 8
OVERSIZED_ITEM = "resident item 0 requires"
TOTAL_MEMORY_ERROR = "total accelerator memory must be positive"
TINY_CURRENT_CAPACITY = 6
LARGE_CURRENT_CAPACITY = 4209


def test_tiny_device_still_admits_resident_current_state() -> None:
    """A nominal 128 MiB device can schedule a current state."""
    resources = _resources(128 * MIB, multiprocessors=2, threads=256)
    plan = plan_resident_batches(
        (CURRENT_STATE_BYTES,) * 8,
        resources,
        fixed_chunk_bytes=FIXED_CHUNK_BYTES,
    )
    assert plan.reserve_bytes == MINIMUM_RESERVE_BYTES
    assert plan.chunks
    assert all(chunk.item_count >= 1 for chunk in plan.chunks)
    assert all(
        chunk.bytes_required <= plan.usable_memory_bytes
        for chunk in plan.chunks
    )


def test_large_memory_expands_search_breadth_without_fixed_cap() -> None:
    """An 80 GiB snapshot admits strictly more resident states than 128 MiB."""
    tiny = plan_resident_batches(
        (CURRENT_STATE_BYTES,) * 5000,
        _resources(128 * MIB, multiprocessors=2, threads=256),
    )
    large = plan_resident_batches(
        (CURRENT_STATE_BYTES,) * 5000,
        _resources(80 * GIB, multiprocessors=120, threads=1024),
    )
    tiny_first = tiny.chunks[0].item_count
    large_first = large.chunks[0].item_count
    assert tiny_first == TINY_CURRENT_CAPACITY
    assert large_first == LARGE_CURRENT_CAPACITY
    assert large_first > tiny_first
    assert large.compute_wave_items > tiny.compute_wave_items


def test_mixed_layout_preserves_order_and_budget() -> None:
    """Greedy chunks preserve every input exactly once."""
    resources = _resources(64 * MIB, multiprocessors=4, threads=512)
    sizes = (
        CLASSIC_STATE_BYTES,
        5 * MIB,
        20 * MIB,
        CLASSIC_STATE_BYTES,
        18 * MIB,
    )
    plan = plan_resident_batches(sizes, resources, fixed_chunk_bytes=4096)
    observed = [
        index
        for chunk in plan.chunks
        for index in range(chunk.start, chunk.stop)
    ]
    assert observed == list(range(len(sizes)))
    assert all(
        chunk.bytes_required <= plan.usable_memory_bytes
        for chunk in plan.chunks
    )


def test_single_item_larger_than_budget_fails_closed() -> None:
    """A state that cannot fit alone is rejected before backend allocation."""
    resources = _resources(32 * MIB, multiprocessors=1, threads=128)
    error = _resource_error(
        lambda: plan_resident_batches((64 * MIB,), resources)
    )
    assert OVERSIZED_ITEM in error


def test_invalid_resource_snapshot_fails_closed() -> None:
    """Contradictory measured resources never produce a scheduler plan."""
    resources = AcceleratorResources(
        free_memory_bytes=0,
        max_threads_per_block=1,
        multiprocessor_count=1,
        total_memory_bytes=0,
    )
    error = _resource_error(
        lambda: plan_resident_batches((CLASSIC_STATE_BYTES,), resources)
    )
    assert TOTAL_MEMORY_ERROR in error


def _resources(
    total: int,
    *,
    multiprocessors: int,
    threads: int,
) -> AcceleratorResources:
    return AcceleratorResources(
        free_memory_bytes=total,
        max_threads_per_block=threads,
        multiprocessor_count=multiprocessors,
        total_memory_bytes=total,
    )


def _resource_error(call: Callable[[], object]) -> str:
    try:
        _ = call()
    except ResourceBudgetError as error:
        return str(error)
    message = "expected ResourceBudgetError"
    raise AssertionError(message)
