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
#   - Deterministic contract tests for CUDA function-resource observation.
# - Must-Not:
#   - Require CUDA hardware or infer occupancy from function attributes.
# - Allows:
#   - Inputs: fake `cuFuncGetAttribute` results and one opaque function handle.
#   - Outputs: exact resource observations or fail-closed execution errors.
#   - Side effects: none.
# - Split-When:
#   - Split when another Driver API resource surface gains separate semantics.
# - Merge-When:
#   - Merge when another test owns these exact function-attribute invariants.
# - Summary:
#   - Unit evidence for Driver API kernel-resource measurement.
# - Description:
#   - Locks attribute IDs, result mapping, context guard, and failure handling.
# - Usage:
#   - Run without CUDA before retaining any kernel-resource evidence.
# - Defaults:
#   - Resource values are observations only; verifier authority is unchanged.
#

"""Contract tests for CUDA function-resource observation."""

from __future__ import annotations

from collections.abc import Callable
import ctypes
from typing import Final
from typing import cast

from accelerator.cuda.runtime import CUDA_FUNCTION_ATTRIBUTE_CONST_SIZE_BYTES
from accelerator.cuda.runtime import CUDA_FUNCTION_ATTRIBUTE_LOCAL_SIZE_BYTES
from accelerator.cuda.runtime import (
    CUDA_FUNCTION_ATTRIBUTE_MAX_THREADS_PER_BLOCK,
)
from accelerator.cuda.runtime import CUDA_FUNCTION_ATTRIBUTE_NUM_REGS
from accelerator.cuda.runtime import CUDA_FUNCTION_ATTRIBUTE_SHARED_SIZE_BYTES
from accelerator.cuda.runtime import CudaKernelResourceProbe
from accelerator.exact_primitives import AcceleratorExecutionError
import pytest

KERNEL_ADDRESS: Final = 303
CUDA_SUCCESS: Final = 0
CUDA_FAILURE: Final = 7
EXPECTED_MAX_THREADS: Final = 1024
EXPECTED_SHARED_BYTES: Final = 128
EXPECTED_CONSTANT_BYTES: Final = 59_237
EXPECTED_LOCAL_BYTES: Final = 16
EXPECTED_REGISTERS: Final = 48
EXPECTED_ACTIVE_BLOCKS: Final = 6
EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR: Final = 1536
EXPECTED_LAUNCH_THREADS: Final = 256
OCCUPANCY_ARGUMENT_COUNT: Final = 4
EXPECTED_NEGATIVE_QUERY_COUNT: Final = 2
CLOSED_MESSAGE: Final = "closed"
type _AttributeQuery = Callable[..., int]

EXPECTED_VALUES = {
    CUDA_FUNCTION_ATTRIBUTE_MAX_THREADS_PER_BLOCK: EXPECTED_MAX_THREADS,
    CUDA_FUNCTION_ATTRIBUTE_SHARED_SIZE_BYTES: EXPECTED_SHARED_BYTES,
    CUDA_FUNCTION_ATTRIBUTE_CONST_SIZE_BYTES: EXPECTED_CONSTANT_BYTES,
    CUDA_FUNCTION_ATTRIBUTE_LOCAL_SIZE_BYTES: EXPECTED_LOCAL_BYTES,
    CUDA_FUNCTION_ATTRIBUTE_NUM_REGS: EXPECTED_REGISTERS,
}
EXPECTED_QUERY_ORDER = (
    CUDA_FUNCTION_ATTRIBUTE_CONST_SIZE_BYTES,
    CUDA_FUNCTION_ATTRIBUTE_LOCAL_SIZE_BYTES,
    CUDA_FUNCTION_ATTRIBUTE_MAX_THREADS_PER_BLOCK,
    CUDA_FUNCTION_ATTRIBUTE_NUM_REGS,
    CUDA_FUNCTION_ATTRIBUTE_SHARED_SIZE_BYTES,
)


def _attribute_query(
    calls: list[tuple[int, int]],
    values: dict[int, int],
    *,
    status: int = CUDA_SUCCESS,
) -> _AttributeQuery:
    def query(
        output: int,
        attribute: int,
        kernel: ctypes.c_void_p,
    ) -> int:
        kernel_value = kernel.value
        if kernel_value is None:
            message = "fake kernel handle is null"
            raise AssertionError(message)
        calls.append((attribute, kernel_value))
        target = ctypes.cast(output, ctypes.POINTER(ctypes.c_int))
        target[0] = values.get(attribute, 0)
        return status

    return query


def _occupancy_query(
    calls: list[tuple[int, int, int]],
    *,
    active_blocks: int = EXPECTED_ACTIVE_BLOCKS,
    status: int = CUDA_SUCCESS,
) -> _AttributeQuery:
    def query(*arguments: object) -> int:
        if len(arguments) != OCCUPANCY_ARGUMENT_COUNT:
            message = "fake occupancy query requires four arguments"
            raise AssertionError(message)
        output, kernel_value, block_size, dynamic_shared_bytes = arguments
        kernel = cast("ctypes.c_void_p", kernel_value)
        if kernel.value is None:
            message = "fake occupancy kernel handle is null"
            raise AssertionError(message)
        if not isinstance(block_size, int) or not isinstance(
            dynamic_shared_bytes,
            int,
        ):
            message = "fake occupancy geometry must be integer-valued"
            raise TypeError(message)
        calls.append((kernel.value, block_size, dynamic_shared_bytes))
        target = ctypes.cast(cast("int", output), ctypes.POINTER(ctypes.c_int))
        target[0] = active_blocks
        return status

    return query


def test_kernel_resource_probe_maps_reviewed_driver_attributes() -> None:
    """Each reviewed attribute lands in its distinct resource field."""
    calls: list[tuple[int, int]] = []
    probe = CudaKernelResourceProbe(
        lambda: None,
        _attribute_query(calls, EXPECTED_VALUES),
        occupancy_fn=_occupancy_query(occupancy_calls := []),
        max_threads_per_multiprocessor=EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR,
    )

    resources = probe.measure(ctypes.c_void_p(KERNEL_ADDRESS))

    assert (
        resources.active_blocks_per_multiprocessor_at_launch
        == EXPECTED_ACTIVE_BLOCKS
    )
    assert resources.launch_threads_per_block == EXPECTED_LAUNCH_THREADS
    assert (
        resources.max_threads_per_multiprocessor
        == EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR
    )
    assert occupancy_calls == [
        (KERNEL_ADDRESS, EXPECTED_LAUNCH_THREADS, 0)
    ]
    assert resources.max_threads_per_block == EXPECTED_MAX_THREADS
    assert resources.static_shared_memory_bytes == EXPECTED_SHARED_BYTES
    assert resources.constant_memory_bytes == EXPECTED_CONSTANT_BYTES
    assert resources.local_memory_bytes_per_thread == EXPECTED_LOCAL_BYTES
    assert resources.registers_per_thread == EXPECTED_REGISTERS
    assert tuple(attribute for attribute, _ in calls) == EXPECTED_QUERY_ORDER
    assert all(kernel == KERNEL_ADDRESS for _, kernel in calls)


def test_kernel_resource_probe_checks_context_before_driver_query() -> None:
    """A closed context fails before any Driver function is called."""
    calls: list[tuple[int, int]] = []
    occupancy_calls: list[tuple[int, int, int]] = []

    def closed() -> None:
        raise AcceleratorExecutionError(CLOSED_MESSAGE)

    probe = CudaKernelResourceProbe(
        closed,
        _attribute_query(calls, EXPECTED_VALUES),
        occupancy_fn=_occupancy_query(occupancy_calls),
        max_threads_per_multiprocessor=EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR,
    )
    with pytest.raises(AcceleratorExecutionError, match="closed"):
        _ = probe.measure(ctypes.c_void_p(KERNEL_ADDRESS))
    assert calls == []
    assert occupancy_calls == []


def test_kernel_resource_probe_propagates_driver_failure() -> None:
    """A rejected attribute query cannot become partial resource evidence."""
    calls: list[tuple[int, int]] = []
    occupancy_calls: list[tuple[int, int, int]] = []
    probe = CudaKernelResourceProbe(
        lambda: None,
        _attribute_query(calls, EXPECTED_VALUES, status=CUDA_FAILURE),
        occupancy_fn=_occupancy_query(occupancy_calls),
        max_threads_per_multiprocessor=EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR,
    )
    with pytest.raises(AcceleratorExecutionError, match="cuFuncGetAttribute"):
        _ = probe.measure(ctypes.c_void_p(KERNEL_ADDRESS))
    assert len(calls) == 1
    assert len(occupancy_calls) == 1


def test_kernel_resource_probe_rejects_negative_driver_value() -> None:
    """Impossible negative resource observations fail closed."""
    calls: list[tuple[int, int]] = []
    values = dict(EXPECTED_VALUES)
    values[CUDA_FUNCTION_ATTRIBUTE_LOCAL_SIZE_BYTES] = -1
    occupancy_calls: list[tuple[int, int, int]] = []
    probe = CudaKernelResourceProbe(
        lambda: None,
        _attribute_query(calls, values),
        occupancy_fn=_occupancy_query(occupancy_calls),
        max_threads_per_multiprocessor=EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR,
    )
    with pytest.raises(AcceleratorExecutionError, match="negative"):
        _ = probe.measure(ctypes.c_void_p(KERNEL_ADDRESS))
    assert len(calls) == EXPECTED_NEGATIVE_QUERY_COUNT


def test_kernel_resource_probe_propagates_occupancy_failure() -> None:
    """A rejected occupancy query cannot become partial resource evidence."""
    calls: list[tuple[int, int]] = []
    occupancy_calls: list[tuple[int, int, int]] = []
    probe = CudaKernelResourceProbe(
        lambda: None,
        _attribute_query(calls, EXPECTED_VALUES),
        occupancy_fn=_occupancy_query(
            occupancy_calls,
            status=CUDA_FAILURE,
        ),
        max_threads_per_multiprocessor=EXPECTED_MAX_THREADS_PER_MULTIPROCESSOR,
    )
    with pytest.raises(
        AcceleratorExecutionError,
        match="cuOccupancyMaxActiveBlocksPerMultiprocessor",
    ):
        _ = probe.measure(ctypes.c_void_p(KERNEL_ADDRESS))
    assert len(occupancy_calls) == 1
    assert calls == []
