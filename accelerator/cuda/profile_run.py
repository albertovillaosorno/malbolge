# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""CUDA resident bounded execution for scalable modular Malbolge profiles."""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import final

from accelerator.classic_run import MAX_U32
from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_run import STATE_WORDS
from accelerator.classic_step import StepTermination
from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.profile_run import ProfileRunResult
from accelerator.profile_run import validate_profile_run_requests
from accelerator.resource_budget import ResourceBudgetError
from accelerator.resource_budget import plan_resident_batches

if TYPE_CHECKING:
    from collections.abc import Sequence

    from accelerator.profile_run import ProfileRunGeometry
    from accelerator.profile_run import ProfileRunRequest
    from accelerator.resource_budget import ResourcePlan

_STATUS_INDEX: Final = 11
_ERROR_INDEX: Final = 12
_ERROR_POINTER_INDEX: Final = 13
_ERROR_VALUE_INDEX: Final = 14
_STEPS_INDEX: Final = 15
_DEVICE_WORD_BYTES: Final = 4
_FIXED_CHUNK_BYTES: Final = 2 * _DEVICE_WORD_BYTES
_KERNEL_NAME: Final = "malbolge_profile_run_batch"

type HostWords = ctypes.Array[ctypes.c_uint32]


@dataclass(frozen=True, slots=True)
class _WordBuffer:
    owner: array[int]
    view: HostWords


@dataclass(frozen=True, slots=True)
class _HostBatch:
    states: _WordBuffer
    memories: _WordBuffer
    inputs: _WordBuffer
    outputs: _WordBuffer


@final
class CudaProfileRunAdapter:
    """Resident CUDA executor for one validated modular profile geometry."""

    def __init__(
        self,
        geometry: ProfileRunGeometry,
        device_id: int = 0,
    ) -> None:
        """Compile one geometry-bound resident profile kernel.

        Raises:
            AcceleratorExecutionError: If CUDA compilation or loading fails.

        """
        admitted = geometry.validated()
        runtime = CudaRuntime(device_id)
        try:
            info = runtime.device_info
            source = resident_kernel_source(
                ResidentGeometry(
                    eof_word=admitted.eof_word,
                    memory_words=admitted.memory_words,
                    word_modulus=admitted.word_modulus,
                    word_trits=admitted.word_trits,
                ),
                _KERNEL_NAME,
            )
            module = runtime.compile_module(source, info.arch)
            kernel = runtime.get_kernel(module, _KERNEL_NAME.encode("ascii"))
        except AcceleratorExecutionError:
            runtime.close()
            raise
        self._capability = AcceleratorCapability(
            backend_id="cuda-profile-run",
            device_arch=info.arch,
            device_name=info.name,
        )
        self._closed = False
        self._geometry = admitted
        self._kernel = kernel
        self._module = module
        self._runtime = runtime

    def __enter__(self) -> Self:
        """Return this live adapter for scoped use.

        Returns:
            This adapter instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release the CUDA module and context at scope exit."""
        self.close()

    def capability(self) -> AcceleratorCapability:
        """Return stable backend and selected-device identity.

        Returns:
            Stable CUDA backend and device metadata.

        """
        return self._capability

    def close(self) -> None:
        """Release module and CUDA context exactly once."""
        if self._closed:
            return
        self._closed = True
        try:
            self._runtime.unload_module(self._module)
        finally:
            self._runtime.close()

    def evaluate(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> tuple[ProfileRunResult, ...]:
        """Execute complete scalable states in deterministic request order.

        Returns:
            Complete final states in request order.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        if not validated:
            return ()
        plan = self._plan_validated(validated)
        results: list[ProfileRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._evaluate_chunk(validated[chunk.start : chunk.stop])
            )
        return tuple(results)

    def plan(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> ResourcePlan:
        """Plan memory-safe scalable resident chunks from live device resources.

        Returns:
            Deterministic resource plan for the validated homogeneous batch.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or planning
                rejects the measured resource budget.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        return self._plan_validated(validated)

    def _evaluate_chunk(
        self,
        requests: tuple[ProfileRunRequest, ...],
    ) -> tuple[ProfileRunResult, ...]:
        hosts = _build_host_batch(self._geometry, requests)
        pointers: list[int] = []
        try:
            pointers.extend(
                _copy_words(self._runtime, host)
                for host in (
                    hosts.states,
                    hosts.memories,
                    hosts.inputs,
                    hosts.outputs,
                )
            )
            self._runtime.launch(self._kernel, tuple(pointers), len(requests))
            self._runtime.copy_from_device(hosts.states.view, pointers[0])
            self._runtime.copy_from_device(hosts.memories.view, pointers[1])
            self._runtime.copy_from_device(hosts.outputs.view, pointers[3])
            return _decode_results(
                self._geometry,
                hosts,
                count=len(requests),
            )
        finally:
            _free_all(self._runtime, pointers)

    def _plan_validated(
        self,
        requests: tuple[ProfileRunRequest, ...],
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(self._geometry, request)
            for request in requests
        )
        max_items = (MAX_U32 // self._geometry.memory_words) + 1
        try:
            return plan_resident_batches(
                item_bytes,
                self._runtime.resources.snapshot(),
                fixed_chunk_bytes=_FIXED_CHUNK_BYTES,
                max_items_per_chunk=max_items,
            )
        except ResourceBudgetError as error:
            message = f"CUDA profile resource budget rejected batch: {error}"
            raise AcceleratorExecutionError(message) from error


def _resident_item_bytes(
    geometry: ProfileRunGeometry,
    request: ProfileRunRequest,
) -> int:
    output_capacity = len(request.output_bytes) + request.step_budget
    words = (
        STATE_WORDS
        + geometry.memory_words
        + len(request.input_bytes)
        + output_capacity
    )
    return words * _DEVICE_WORD_BYTES


def _encode_variable_state(
    requests: tuple[ProfileRunRequest, ...],
) -> tuple[array[int], array[int], array[int]]:
    states = array("I")
    inputs = array("I")
    outputs = array("I")
    for request in requests:
        input_offset = len(inputs)
        inputs.extend(request.input_bytes)
        output_offset = len(outputs)
        output_capacity = len(request.output_bytes) + request.step_budget
        outputs.extend(request.output_bytes)
        outputs.extend(0 for _slot in range(request.step_budget))
        _validate_buffer_offsets(input_offset, output_offset, output_capacity)
        states.extend((
            request.accumulator,
            request.code_pointer,
            request.data_pointer,
            input_offset,
            len(request.input_bytes),
            request.input_consumed,
            output_offset,
            len(request.output_bytes),
            output_capacity,
            request.step_budget,
            int(request.termination),
            int(RunStatus.BUDGET_EXHAUSTED),
            int(RunError.NONE),
            0,
            0,
            0,
        ))
    return states, inputs, outputs


def _validate_buffer_offsets(
    input_offset: int,
    output_offset: int,
    output_capacity: int,
) -> None:
    for value, label in (
        (input_offset, "resident input offset"),
        (output_offset, "resident output offset"),
        (output_capacity, "resident output capacity"),
    ):
        if value > MAX_U32:
            message = f"{label} outside unsigned 32-bit domain: {value}"
            raise AcceleratorExecutionError(message)


def _build_host_batch(
    geometry: ProfileRunGeometry,
    requests: tuple[ProfileRunRequest, ...],
) -> _HostBatch:
    states, inputs, outputs = _encode_variable_state(requests)
    memories = _build_memory_owner(requests)
    if not inputs:
        inputs.append(0)
    if not outputs:
        outputs.append(0)
    expected_memory_words = geometry.memory_words * len(requests)
    if len(memories) != expected_memory_words:
        message = "profile host memory assembly invariant failed"
        raise AcceleratorExecutionError(message)
    return _HostBatch(
        states=_word_buffer(states),
        memories=_word_buffer(memories),
        inputs=_word_buffer(inputs),
        outputs=_word_buffer(outputs),
    )


def _build_memory_owner(
    requests: tuple[ProfileRunRequest, ...],
) -> array[int]:
    first = requests[0].memory
    if all(request.memory is first for request in requests):
        return array("I", first) * len(requests)
    memories = array("I")
    for request in requests:
        memories.extend(request.memory)
    return memories


def _copy_words(runtime: CudaRuntime, host: _WordBuffer) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host.view))
    try:
        runtime.copy_to_device(pointer, host.view)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _decode_results(
    geometry: ProfileRunGeometry,
    hosts: _HostBatch,
    *,
    count: int,
) -> tuple[ProfileRunResult, ...]:
    states = hosts.states.owner
    memories = hosts.memories.owner
    outputs = hosts.outputs.owner
    results: list[ProfileRunResult] = []
    for index in range(count):
        base = index * STATE_WORDS
        memory_base = index * geometry.memory_words
        output_offset = states[base + 6]
        output_len = states[base + 7]
        results.append(
            ProfileRunResult(
                accumulator=states[base],
                code_pointer=states[base + 1],
                data_pointer=states[base + 2],
                error=RunError(states[base + _ERROR_INDEX]),
                error_pointer=states[base + _ERROR_POINTER_INDEX],
                error_value=states[base + _ERROR_VALUE_INDEX],
                input_consumed=states[base + 5],
                memory=memories[
                    memory_base : memory_base + geometry.memory_words
                ],
                output_bytes=tuple(
                    outputs[output_offset : output_offset + output_len]
                ),
                status=RunStatus(states[base + _STATUS_INDEX]),
                steps=states[base + _STEPS_INDEX],
                termination=StepTermination(states[base + 10]),
            )
        )
    return tuple(results)


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _word_buffer(owner: array[int]) -> _WordBuffer:
    view_type = ctypes.c_uint32 * len(owner)
    return _WordBuffer(owner=owner, view=view_type.from_buffer(owner))
