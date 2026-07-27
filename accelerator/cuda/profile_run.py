# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""CUDA resident bounded execution for scalable modular Malbolge profiles."""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass
import mmap
from time import perf_counter_ns
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
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.profile_run import ProfileRunObservation
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
class ProfileRunPhaseProfile:
    """Diagnostic wall-clock phase totals for one profiled evaluation."""

    allocate_ns: int
    chunks: int
    decode_ns: int
    download_ns: int
    host_build_ns: int
    kernel_ns: int
    release_ns: int
    total_ns: int
    upload_ns: int
    validation_plan_ns: int


@dataclass(slots=True)
class _PhaseCounter:
    allocate_ns: int = 0
    decode_ns: int = 0
    download_ns: int = 0
    host_build_ns: int = 0
    kernel_ns: int = 0
    release_ns: int = 0
    upload_ns: int = 0

    def freeze(
        self,
        *,
        chunks: int,
        total_ns: int,
        validation_plan_ns: int,
    ) -> ProfileRunPhaseProfile:
        """Freeze accumulated phase counters into public evidence.

        Returns:
            Immutable aggregate timing evidence.

        """
        return ProfileRunPhaseProfile(
            allocate_ns=self.allocate_ns,
            chunks=chunks,
            decode_ns=self.decode_ns,
            download_ns=self.download_ns,
            host_build_ns=self.host_build_ns,
            kernel_ns=self.kernel_ns,
            release_ns=self.release_ns,
            total_ns=total_ns,
            upload_ns=self.upload_ns,
            validation_plan_ns=validation_plan_ns,
        )


@dataclass(frozen=True, slots=True)
class _WordBuffer:
    owner: array[int]
    view: HostWords


@dataclass(frozen=True, slots=True)
class _MemoryBuffer:
    owner: array[int] | mmap.mmap
    view: HostWords


@dataclass(frozen=True, slots=True)
class _HostBatch:
    states: _WordBuffer
    memories: _MemoryBuffer
    shared_memory_source: _WordBuffer | None
    inputs: _WordBuffer
    outputs: _WordBuffer


@dataclass(frozen=True, slots=True)
class _ResidentChunk:
    """One independently launchable device-resident profile batch chunk."""

    count: int
    hosts: _HostBatch
    pointers: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _ResidentContext:
    """CUDA handles and geometry shared by one scalable resident session."""

    geometry: ProfileRunGeometry
    kernel: ctypes.c_void_p
    runtime: CudaRuntime


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

    def open_session(
        self,
        requests: Sequence[ProfileRunRequest],
        *,
        max_runs: int,
    ) -> CudaProfileRunSession:
        """Upload scalable states once for repeated resident launches.

        Returns:
            Scoped session retaining complete state in device memory.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.
            InvalidPrimitiveBatchError: If session capacity is invalid.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        if max_runs <= 0:
            message = f"resident max runs must be positive: {max_runs}"
            raise InvalidPrimitiveBatchError(message)
        validated = _validate_session_requests(
            self._geometry,
            tuple(requests),
            max_runs=max_runs,
        )
        chunks = self._build_session_chunks(validated, max_runs=max_runs)
        context = _ResidentContext(
            geometry=self._geometry,
            kernel=self._kernel,
            runtime=self._runtime,
        )
        return CudaProfileRunSession(
            context=context,
            chunks=chunks,
            max_runs=max_runs,
        )

    def profile_evaluate(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> tuple[tuple[ProfileRunResult, ...], ProfileRunPhaseProfile]:
        """Execute the ordinary path while recording diagnostic wall time.

        Returns:
            Exact results plus aggregate per-phase timing for this evaluation.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.

        """
        total_start = perf_counter_ns()
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        phase = _PhaseCounter()
        plan_start = perf_counter_ns()
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        plan = self._plan_validated(validated) if validated else None
        validation_plan_ns = perf_counter_ns() - plan_start
        if plan is None:
            total_ns = perf_counter_ns() - total_start
            return (), phase.freeze(
                chunks=0,
                total_ns=total_ns,
                validation_plan_ns=validation_plan_ns,
            )
        results: list[ProfileRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._profile_chunk(
                    validated[chunk.start : chunk.stop],
                    phase,
                )
            )
        total_ns = perf_counter_ns() - total_start
        return tuple(results), phase.freeze(
            chunks=len(plan.chunks),
            total_ns=total_ns,
            validation_plan_ns=validation_plan_ns,
        )

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

    def _profile_chunk(
        self,
        requests: tuple[ProfileRunRequest, ...],
        phase: _PhaseCounter,
    ) -> tuple[ProfileRunResult, ...]:
        start = perf_counter_ns()
        hosts = _build_host_batch(self._geometry, requests)
        phase.host_build_ns += perf_counter_ns() - start
        pointers = self._profile_uploads(hosts, phase)
        try:
            start = perf_counter_ns()
            self._runtime.launch(self._kernel, tuple(pointers), len(requests))
            phase.kernel_ns += perf_counter_ns() - start
            self._profile_downloads(hosts, pointers, phase)
            start = perf_counter_ns()
            results = _decode_results(
                self._geometry,
                hosts,
                count=len(requests),
            )
            phase.decode_ns += perf_counter_ns() - start
            return results
        finally:
            start = perf_counter_ns()
            _free_all(self._runtime, pointers)
            phase.release_ns += perf_counter_ns() - start

    def _profile_downloads(
        self,
        hosts: _HostBatch,
        pointers: list[int],
        phase: _PhaseCounter,
    ) -> None:
        start = perf_counter_ns()
        self._runtime.copy_from_device(hosts.states.view, pointers[0])
        self._runtime.copy_from_device(hosts.memories.view, pointers[1])
        self._runtime.copy_from_device(hosts.outputs.view, pointers[3])
        phase.download_ns += perf_counter_ns() - start

    def _profile_upload(
        self,
        host: _WordBuffer,
        phase: _PhaseCounter,
    ) -> int:
        start = perf_counter_ns()
        pointer = self._runtime.allocate(ctypes.sizeof(host.view))
        phase.allocate_ns += perf_counter_ns() - start
        try:
            start = perf_counter_ns()
            self._runtime.copy_to_device(pointer, host.view)
            phase.upload_ns += perf_counter_ns() - start
        except AcceleratorExecutionError:
            self._runtime.free(pointer)
            raise
        return pointer

    def _profile_memory_upload(
        self,
        hosts: _HostBatch,
        phase: _PhaseCounter,
    ) -> int:
        start = perf_counter_ns()
        pointer = self._runtime.allocate(ctypes.sizeof(hosts.memories.view))
        phase.allocate_ns += perf_counter_ns() - start
        try:
            start = perf_counter_ns()
            _initialize_device_memories(self._runtime, pointer, hosts)
            phase.upload_ns += perf_counter_ns() - start
        except AcceleratorExecutionError:
            self._runtime.free(pointer)
            raise
        return pointer

    def _profile_uploads(
        self,
        hosts: _HostBatch,
        phase: _PhaseCounter,
    ) -> list[int]:
        pointers: list[int] = []
        try:
            pointers.extend((self._profile_upload(hosts.states, phase),))
            pointers.extend((self._profile_memory_upload(hosts, phase),))
            pointers.extend((self._profile_upload(hosts.inputs, phase),))
            pointers.extend((self._profile_upload(hosts.outputs, phase),))
        except AcceleratorExecutionError:
            _free_all(self._runtime, pointers)
            raise
        return pointers

    def _evaluate_chunk(
        self,
        requests: tuple[ProfileRunRequest, ...],
    ) -> tuple[ProfileRunResult, ...]:
        hosts = _build_host_batch(self._geometry, requests)
        pointers: list[int] = []
        try:
            pointers.extend((_copy_words(self._runtime, hosts.states),))
            pointers.extend((_copy_memories(self._runtime, hosts),))
            pointers.extend((_copy_words(self._runtime, hosts.inputs),))
            pointers.extend((_copy_words(self._runtime, hosts.outputs),))
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

    def _build_session_chunks(
        self,
        requests: tuple[ProfileRunRequest, ...],
        *,
        max_runs: int,
    ) -> tuple[_ResidentChunk, ...]:
        if not requests:
            return ()
        plan = self._plan_session_validated(requests, max_runs=max_runs)
        chunks: list[_ResidentChunk] = []
        try:
            for chunk in plan.chunks:
                chunk_requests = requests[chunk.start : chunk.stop]
                hosts = _build_host_batch(
                    self._geometry,
                    chunk_requests,
                    lazy_shared_memory=True,
                    output_budget_multiplier=max_runs,
                )
                pointers = _upload_host_batch(self._runtime, hosts)
                chunks.append(
                    _ResidentChunk(
                        count=len(chunk_requests),
                        hosts=hosts,
                        pointers=pointers,
                    )
                )
        except AcceleratorExecutionError, InvalidPrimitiveBatchError:
            _free_resident_chunks(self._runtime, chunks)
            raise
        return tuple(chunks)

    def _plan_session_validated(
        self,
        requests: tuple[ProfileRunRequest, ...],
        *,
        max_runs: int,
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(
                self._geometry,
                request,
                output_budget_multiplier=max_runs,
            )
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
            message = f"CUDA profile resource budget rejected session: {error}"
            raise AcceleratorExecutionError(message) from error

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


@final
class CudaProfileRunSession:
    """Repeated scalable CUDA execution with complete state kept resident."""

    def __init__(
        self,
        *,
        context: _ResidentContext,
        chunks: tuple[_ResidentChunk, ...],
        max_runs: int,
    ) -> None:
        """Adopt already-uploaded resident chunks owned by one live adapter."""
        self._chunks = chunks
        self._closed = False
        self._context = context
        self._failed = False
        self._max_runs = max_runs
        self._runs_executed = 0

    def __enter__(self) -> Self:
        """Return this live resident session for scoped use.

        Returns:
            This session.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release all resident device allocations at scope exit."""
        self.close()

    @property
    def runs_executed(self) -> int:
        """Number of complete resident launches committed by this session."""
        return self._runs_executed

    def advance(self) -> None:
        """Execute one bounded segment without materializing a host snapshot.

        Raises:
            AcceleratorExecutionError: If the session is closed, poisoned,
                exhausted, or a CUDA launch fails.

        """
        self._ensure_usable()
        if self._runs_executed >= self._max_runs:
            message = "resident CUDA profile session run budget exhausted"
            raise AcceleratorExecutionError(message)
        try:
            for chunk in self._chunks:
                self._context.runtime.launch(
                    self._context.kernel,
                    chunk.pointers,
                    chunk.count,
                )
        except AcceleratorExecutionError:
            self._failed = True
            raise
        self._runs_executed += 1

    def close(self) -> None:
        """Release all device allocations exactly once."""
        if self._closed:
            return
        self._closed = True
        _free_resident_chunks(self._context.runtime, self._chunks)

    def observe(self) -> tuple[ProfileRunObservation, ...]:
        """Download compact scalar outcomes without full resident memory.

        Returns:
            Compact observations in original request order.

        """
        self._ensure_usable()
        observations: list[ProfileRunObservation] = []
        for chunk in self._chunks:
            self._context.runtime.copy_from_device(
                chunk.hosts.states.view,
                chunk.pointers[0],
            )
            observations.extend(
                _decode_observations(chunk.hosts.states.owner, chunk.count)
            )
        return tuple(observations)

    def snapshot(self) -> tuple[ProfileRunResult, ...]:
        """Materialize complete resident profile states on explicit demand.

        Returns:
            Complete scalable results in original request order.

        """
        self._ensure_usable()
        results: list[ProfileRunResult] = []
        for chunk in self._chunks:
            self._context.runtime.copy_from_device(
                chunk.hosts.states.view,
                chunk.pointers[0],
            )
            self._context.runtime.copy_from_device(
                chunk.hosts.memories.view,
                chunk.pointers[1],
            )
            self._context.runtime.copy_from_device(
                chunk.hosts.outputs.view,
                chunk.pointers[3],
            )
            results.extend(
                _decode_results(
                    self._context.geometry,
                    chunk.hosts,
                    count=chunk.count,
                )
            )
        return tuple(results)

    def _ensure_usable(self) -> None:
        if self._closed:
            message = "resident CUDA profile session is closed"
            raise AcceleratorExecutionError(message)
        if self._failed:
            message = (
                "resident CUDA profile session is poisoned after execution "
                "failure"
            )
            raise AcceleratorExecutionError(message)


def _validate_session_requests(
    geometry: ProfileRunGeometry,
    requests: tuple[ProfileRunRequest, ...],
    *,
    max_runs: int,
) -> tuple[ProfileRunRequest, ...]:
    validated = validate_profile_run_requests(geometry, requests)
    for request in validated:
        _ = _session_output_capacity(request, max_runs=max_runs)
    return validated


def _session_output_capacity(
    request: ProfileRunRequest,
    *,
    max_runs: int,
) -> int:
    output_capacity = len(request.output_bytes) + (
        request.step_budget * max_runs
    )
    if output_capacity > MAX_U32:
        message = (
            "resident profile session output capacity exceeds unsigned 32-bit "
            f"domain: {output_capacity}"
        )
        raise InvalidPrimitiveBatchError(message)
    return output_capacity


def _resident_item_bytes(
    geometry: ProfileRunGeometry,
    request: ProfileRunRequest,
    *,
    output_budget_multiplier: int = 1,
) -> int:
    output_capacity = _session_output_capacity(
        request,
        max_runs=output_budget_multiplier,
    )
    words = (
        STATE_WORDS
        + geometry.memory_words
        + len(request.input_bytes)
        + output_capacity
    )
    return words * _DEVICE_WORD_BYTES


def _encode_variable_state(
    requests: tuple[ProfileRunRequest, ...],
    *,
    output_budget_multiplier: int = 1,
) -> tuple[array[int], array[int], array[int]]:
    states = array("I")
    inputs = array("I")
    outputs = array("I")
    for request in requests:
        input_offset = len(inputs)
        inputs.extend(request.input_bytes)
        output_offset = len(outputs)
        output_capacity = _session_output_capacity(
            request,
            max_runs=output_budget_multiplier,
        )
        outputs.extend(request.output_bytes)
        additional_output = output_capacity - len(request.output_bytes)
        outputs.extend(0 for _slot in range(additional_output))
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
    *,
    lazy_shared_memory: bool = False,
    output_budget_multiplier: int = 1,
) -> _HostBatch:
    states, inputs, outputs = _encode_variable_state(
        requests,
        output_budget_multiplier=output_budget_multiplier,
    )
    memories, shared_memory_source = _build_memory_buffers(
        requests,
        lazy_shared_memory=lazy_shared_memory,
    )
    if not inputs:
        inputs.append(0)
    if not outputs:
        outputs.append(0)
    expected_memory_bytes = (
        geometry.memory_words * len(requests) * _DEVICE_WORD_BYTES
    )
    if ctypes.sizeof(memories.view) != expected_memory_bytes:
        message = "profile host memory assembly invariant failed"
        raise AcceleratorExecutionError(message)
    return _HostBatch(
        states=_word_buffer(states),
        memories=memories,
        shared_memory_source=shared_memory_source,
        inputs=_word_buffer(inputs),
        outputs=_word_buffer(outputs),
    )


def _build_memory_buffers(
    requests: tuple[ProfileRunRequest, ...],
    *,
    lazy_shared_memory: bool,
) -> tuple[_MemoryBuffer, _WordBuffer | None]:
    first = requests[0].memory
    if all(request.memory is first for request in requests):
        if lazy_shared_memory:
            word_count = len(first) * len(requests)
            memories = _mapped_memory_buffer(word_count)
        else:
            memories = _memory_buffer(array("I", first) * len(requests))
        return memories, _word_buffer(first)
    memories = array("I")
    for request in requests:
        memories.extend(request.memory)
    return _memory_buffer(memories), None


def _upload_host_batch(
    runtime: CudaRuntime,
    hosts: _HostBatch,
) -> tuple[int, int, int, int]:
    pointers: list[int] = []
    try:
        pointers.extend((_copy_words(runtime, hosts.states),))
        pointers.extend((_copy_memories(runtime, hosts),))
        pointers.extend((_copy_words(runtime, hosts.inputs),))
        pointers.extend((_copy_words(runtime, hosts.outputs),))
    except AcceleratorExecutionError:
        _free_all(runtime, pointers)
        raise
    return (pointers[0], pointers[1], pointers[2], pointers[3])


def _copy_memories(runtime: CudaRuntime, hosts: _HostBatch) -> int:
    pointer = runtime.allocate(ctypes.sizeof(hosts.memories.view))
    try:
        _initialize_device_memories(runtime, pointer, hosts)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _initialize_device_memories(
    runtime: CudaRuntime,
    pointer: int,
    hosts: _HostBatch,
) -> None:
    source = hosts.shared_memory_source
    if source is None:
        runtime.copy_to_device(pointer, hosts.memories.view)
        return
    stride_bytes = ctypes.sizeof(source.view)
    total_bytes = ctypes.sizeof(hosts.memories.view)
    if stride_bytes == 0 or total_bytes % stride_bytes != 0:
        message = "profile shared-memory replication invariant failed"
        raise AcceleratorExecutionError(message)
    repeat_count = total_bytes // stride_bytes
    runtime.copy_to_device(
        pointer,
        source.view,
        repeat_count=repeat_count,
    )


def _copy_words(runtime: CudaRuntime, host: _WordBuffer) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host.view))
    try:
        runtime.copy_to_device(pointer, host.view)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _decode_observations(
    states: array[int],
    count: int,
) -> tuple[ProfileRunObservation, ...]:
    observations: list[ProfileRunObservation] = []
    for index in range(count):
        base = index * STATE_WORDS
        observations.append(
            ProfileRunObservation(
                accumulator=states[base],
                code_pointer=states[base + 1],
                data_pointer=states[base + 2],
                error=RunError(states[base + _ERROR_INDEX]),
                error_pointer=states[base + _ERROR_POINTER_INDEX],
                error_value=states[base + _ERROR_VALUE_INDEX],
                input_consumed=states[base + 5],
                output_length=states[base + 7],
                status=RunStatus(states[base + _STATUS_INDEX]),
                steps=states[base + _STEPS_INDEX],
                termination=StepTermination(states[base + 10]),
            )
        )
    return tuple(observations)


def _decode_results(
    geometry: ProfileRunGeometry,
    hosts: _HostBatch,
    *,
    count: int,
) -> tuple[ProfileRunResult, ...]:
    states = hosts.states.owner
    outputs = hosts.outputs.owner
    memory_bytes = memoryview(hosts.memories.view).cast("B")
    results: list[ProfileRunResult] = []
    try:
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
                    memory=_decode_memory(
                        memory_bytes,
                        memory_base,
                        geometry.memory_words,
                    ),
                    output_bytes=tuple(
                        outputs[output_offset : output_offset + output_len]
                    ),
                    status=RunStatus(states[base + _STATUS_INDEX]),
                    steps=states[base + _STEPS_INDEX],
                    termination=StepTermination(states[base + 10]),
                )
            )
    finally:
        memory_bytes.release()
    return tuple(results)


def _decode_memory(
    memory_bytes: memoryview,
    word_offset: int,
    word_count: int,
) -> array[int]:
    byte_start = word_offset * _DEVICE_WORD_BYTES
    byte_stop = byte_start + (word_count * _DEVICE_WORD_BYTES)
    result = array("I")
    result.frombytes(memory_bytes[byte_start:byte_stop])
    return result


def _free_resident_chunks(
    runtime: CudaRuntime,
    chunks: list[_ResidentChunk] | tuple[_ResidentChunk, ...],
) -> None:
    for chunk in reversed(chunks):
        _free_all(runtime, list(chunk.pointers))


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _mapped_memory_buffer(word_count: int) -> _MemoryBuffer:
    byte_count = word_count * _DEVICE_WORD_BYTES
    try:
        owner = mmap.mmap(-1, byte_count)
    except (MemoryError, OSError, OverflowError) as error:
        message = f"profile host memory mapping failed: {error}"
        raise AcceleratorExecutionError(message) from error
    view_type = ctypes.c_uint32 * word_count
    try:
        view = view_type.from_buffer(owner)
    except (BufferError, ValueError) as error:
        owner.close()
        message = f"profile host memory view failed: {error}"
        raise AcceleratorExecutionError(message) from error
    return _MemoryBuffer(owner=owner, view=view)


def _memory_buffer(owner: array[int]) -> _MemoryBuffer:
    view_type = ctypes.c_uint32 * len(owner)
    return _MemoryBuffer(owner=owner, view=view_type.from_buffer(owner))


def _word_buffer(owner: array[int]) -> _WordBuffer:
    view_type = ctypes.c_uint32 * len(owner)
    return _WordBuffer(owner=owner, view=view_type.from_buffer(owner))
