# File:
#   - classic_run.py
# Path:
#   - accelerator/cuda/classic_run.py
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
#   - CUDA resident full-memory bounded execution for classic Malbolge.
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

"""CUDA resident full-memory bounded execution for classic Malbolge."""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import final

from accelerator.classic_run import ClassicRunObservation
from accelerator.classic_run import ClassicRunResult
from accelerator.classic_run import MAX_U32
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_run import STATE_WORDS
from accelerator.classic_run import validate_classic_run_requests
from accelerator.classic_step import StepTermination
from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.resource_budget import ResourceBudgetError
from accelerator.resource_budget import plan_resident_batches

if TYPE_CHECKING:
    from collections.abc import Sequence

    from accelerator.classic_run import ClassicRunRequest
    from accelerator.resource_budget import ResourcePlan

_STATUS_INDEX: Final = 11
_ERROR_INDEX: Final = 12
_ERROR_POINTER_INDEX: Final = 13
_ERROR_VALUE_INDEX: Final = 14
_STEPS_INDEX: Final = 15
_DEVICE_WORD_BYTES: Final = 4
_FIXED_CHUNK_BYTES: Final = 2 * _DEVICE_WORD_BYTES
_MAX_CLASSIC_CHUNK_ITEMS: Final = (MAX_U32 // MEMORY_WORDS) + 1

type HostWords = ctypes.Array[ctypes.c_uint32]


@dataclass(frozen=True, slots=True)
class ClassicRunPhaseProfile:
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
    ) -> ClassicRunPhaseProfile:
        """Freeze accumulated phase counters into public evidence.

        Returns:
            Immutable aggregate timing evidence.

        """
        return ClassicRunPhaseProfile(
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
    """Contiguous unsigned-word owner plus zero-copy ctypes view."""

    owner: array[int]
    view: HostWords


@dataclass(frozen=True, slots=True)
class _HostBatch:
    states: _WordBuffer
    memories: _WordBuffer
    inputs: _WordBuffer
    outputs: _WordBuffer


@dataclass(frozen=True, slots=True)
class _ResidentChunk:
    """One device-resident independently launchable classic batch chunk."""

    count: int
    hosts: _HostBatch
    pointers: tuple[int, int, int, int]


@final
class CudaClassicRunAdapter:
    """Specification-only resident classic full-memory CUDA adapter."""

    def __init__(self, device_id: int = 0) -> None:
        """Compile and load the bounded resident classic VM kernel.

        Raises:
            AcceleratorExecutionError: If compilation or module loading fails.

        """
        runtime = CudaRuntime(device_id)
        try:
            info = runtime.device_info
            module = runtime.compile_module(
                resident_kernel_source(
                    ResidentGeometry(
                        eof_word=MEMORY_WORDS - 1,
                        memory_words=MEMORY_WORDS,
                        word_modulus=MEMORY_WORDS,
                        word_trits=10,
                    ),
                    "malbolge_classic_run_batch",
                ),
                info.arch,
            )
            kernel = runtime.get_kernel(module, b"malbolge_classic_run_batch")
        except AcceleratorExecutionError:
            runtime.close()
            raise
        self._capability = AcceleratorCapability(
            backend_id="cuda-classic-run",
            device_arch=info.arch,
            device_name=info.name,
        )
        self._closed = False
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
        requests: Sequence[ClassicRunRequest],
    ) -> tuple[ClassicRunResult, ...]:
        """Run complete classic states resident for each bounded budget.

        Returns:
            Complete final states in exact request order.

        Raises:
            AcceleratorExecutionError: If CUDA execution is unavailable after
                adapter construction or the adapter is closed.

        """
        if self._closed:
            message = "CUDA classic-run adapter is closed"
            raise AcceleratorExecutionError(message)
        if not requests:
            return ()
        validated = validate_classic_run_requests(tuple(requests))
        plan = self._plan_validated(validated)
        results: list[ClassicRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._evaluate_chunk(validated[chunk.start : chunk.stop])
            )
        return tuple(results)

    def open_session(
        self,
        requests: Sequence[ClassicRunRequest],
        *,
        max_runs: int,
    ) -> CudaClassicRunSession:
        """Upload complete classic states once for repeated resident launches.

        Returns:
            Scoped session that retains all chunk state in device memory.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or allocation
                fails.
            InvalidPrimitiveBatchError: If `max_runs` or output capacity is
                outside the supported unsigned domain.

        """
        if self._closed:
            message = "CUDA classic-run adapter is closed"
            raise AcceleratorExecutionError(message)
        if max_runs <= 0:
            message = f"resident max runs must be positive: {max_runs}"
            raise InvalidPrimitiveBatchError(message)
        validated = _validate_session_requests(
            tuple(requests),
            max_runs=max_runs,
        )
        plan = self._plan_session_validated(validated, max_runs=max_runs)
        chunks: list[_ResidentChunk] = []
        try:
            for chunk in plan.chunks:
                chunk_requests = validated[chunk.start : chunk.stop]
                hosts = _build_host_batch(
                    chunk_requests,
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
        return CudaClassicRunSession(
            runtime=self._runtime,
            kernel=self._kernel,
            chunks=tuple(chunks),
            max_runs=max_runs,
        )

    def profile_evaluate(
        self,
        requests: Sequence[ClassicRunRequest],
    ) -> tuple[tuple[ClassicRunResult, ...], ClassicRunPhaseProfile]:
        """Run the same CUDA path while recording diagnostic wall-clock phases.

        Returns:
            Exact results plus aggregate per-phase timing for this evaluation.

        Raises:
            AcceleratorExecutionError: If CUDA execution is unavailable after
                adapter construction or the adapter is closed.

        """
        total_start = perf_counter_ns()
        if self._closed:
            message = "CUDA classic-run adapter is closed"
            raise AcceleratorExecutionError(message)
        phase = _PhaseCounter()
        plan_start = perf_counter_ns()
        validated = validate_classic_run_requests(tuple(requests))
        plan = self._plan_validated(validated) if validated else None
        validation_plan_ns = perf_counter_ns() - plan_start
        if plan is None:
            total_ns = perf_counter_ns() - total_start
            return (), phase.freeze(
                chunks=0,
                total_ns=total_ns,
                validation_plan_ns=validation_plan_ns,
            )
        results: list[ClassicRunResult] = []
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
        requests: Sequence[ClassicRunRequest],
    ) -> ResourcePlan:
        """Plan safe input-order resident chunks from measured device resources.

        Returns:
            Deterministic memory-bounded chunks and measured compute capacity.

        Raises:
            AcceleratorExecutionError: If even one request cannot fit safely.

        """
        if self._closed:
            message = "CUDA classic-run adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = validate_classic_run_requests(tuple(requests))
        return self._plan_validated(validated)

    def _plan_validated(
        self,
        requests: tuple[ClassicRunRequest, ...],
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(request) for request in requests
        )
        try:
            return plan_resident_batches(
                item_bytes,
                self._runtime.resources.snapshot(),
                fixed_chunk_bytes=_FIXED_CHUNK_BYTES,
                max_items_per_chunk=_MAX_CLASSIC_CHUNK_ITEMS,
            )
        except ResourceBudgetError as error:
            message = f"CUDA resident resource budget rejected batch: {error}"
            raise AcceleratorExecutionError(message) from error

    def _plan_session_validated(
        self,
        requests: tuple[ClassicRunRequest, ...],
        *,
        max_runs: int,
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(request, output_budget_multiplier=max_runs)
            for request in requests
        )
        try:
            return plan_resident_batches(
                item_bytes,
                self._runtime.resources.snapshot(),
                fixed_chunk_bytes=_FIXED_CHUNK_BYTES,
                max_items_per_chunk=_MAX_CLASSIC_CHUNK_ITEMS,
            )
        except ResourceBudgetError as error:
            message = f"CUDA resident resource budget rejected session: {error}"
            raise AcceleratorExecutionError(message) from error

    def _profile_chunk(
        self,
        requests: tuple[ClassicRunRequest, ...],
        phase: _PhaseCounter,
    ) -> tuple[ClassicRunResult, ...]:
        start = perf_counter_ns()
        hosts = _build_host_batch(requests)
        phase.host_build_ns += perf_counter_ns() - start
        pointers = self._profile_uploads(hosts, phase)
        try:
            start = perf_counter_ns()
            self._runtime.launch(self._kernel, tuple(pointers), len(requests))
            phase.kernel_ns += perf_counter_ns() - start
            self._profile_downloads(hosts, pointers, phase)
            start = perf_counter_ns()
            results = _decode_results(hosts, count=len(requests))
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

    def _profile_uploads(
        self,
        hosts: _HostBatch,
        phase: _PhaseCounter,
    ) -> list[int]:
        pointers: list[int] = []
        try:
            pointers.extend(
                self._profile_upload(host, phase)
                for host in (
                    hosts.states,
                    hosts.memories,
                    hosts.inputs,
                    hosts.outputs,
                )
            )
        except AcceleratorExecutionError:
            _free_all(self._runtime, pointers)
            raise
        return pointers

    def _evaluate_chunk(
        self,
        requests: tuple[ClassicRunRequest, ...],
    ) -> tuple[ClassicRunResult, ...]:
        hosts = _build_host_batch(requests)
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
            return _decode_results(hosts, count=len(requests))
        finally:
            _free_all(self._runtime, pointers)


@final
class CudaClassicRunSession:
    """Scoped classic CUDA state that remains allocated across launches."""

    def __init__(
        self,
        *,
        runtime: CudaRuntime,
        kernel: ctypes.c_void_p,
        chunks: tuple[_ResidentChunk, ...],
        max_runs: int,
    ) -> None:
        """Adopt already-uploaded resident chunks owned by one live adapter."""
        self._chunks = chunks
        self._closed = False
        self._failed = False
        self._kernel = kernel
        self._max_runs = max_runs
        self._runs_executed = 0
        self._runtime = runtime

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
        """Execute one declared step-budget segment without a host snapshot.

        Raises:
            AcceleratorExecutionError: If the session is unavailable, poisoned,
                exhausted, or a CUDA launch fails.

        """
        self._ensure_usable()
        if self._runs_executed >= self._max_runs:
            message = "resident CUDA session run budget exhausted"
            raise AcceleratorExecutionError(message)
        try:
            for chunk in self._chunks:
                self._runtime.launch(
                    self._kernel,
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
        _free_resident_chunks(self._runtime, self._chunks)

    def observe(self) -> tuple[ClassicRunObservation, ...]:
        """Download compact scalar/I/O-length outcomes without full memory.

        Returns:
            Compact observations in original request order.

        """
        self._ensure_usable()
        observations: list[ClassicRunObservation] = []
        for chunk in self._chunks:
            self._runtime.copy_from_device(
                chunk.hosts.states.view,
                chunk.pointers[0],
            )
            observations.extend(
                _decode_observations(chunk.hosts.states.owner, chunk.count)
            )
        return tuple(observations)

    def snapshot(self) -> tuple[ClassicRunResult, ...]:
        """Materialize complete resident states on the host on explicit demand.

        Returns:
            Complete classic results in original request order.

        """
        self._ensure_usable()
        results: list[ClassicRunResult] = []
        for chunk in self._chunks:
            self._runtime.copy_from_device(
                chunk.hosts.states.view,
                chunk.pointers[0],
            )
            self._runtime.copy_from_device(
                chunk.hosts.memories.view,
                chunk.pointers[1],
            )
            self._runtime.copy_from_device(
                chunk.hosts.outputs.view,
                chunk.pointers[3],
            )
            results.extend(_decode_results(chunk.hosts, count=chunk.count))
        return tuple(results)

    def _ensure_usable(self) -> None:
        if self._closed:
            message = "resident CUDA session is closed"
            raise AcceleratorExecutionError(message)
        if self._failed:
            message = (
                "resident CUDA session is poisoned after execution failure"
            )
            raise AcceleratorExecutionError(message)


def _validate_session_requests(
    requests: tuple[ClassicRunRequest, ...],
    *,
    max_runs: int,
) -> tuple[ClassicRunRequest, ...]:
    validated = validate_classic_run_requests(requests)
    for request in validated:
        _ = _session_output_capacity(request, max_runs=max_runs)
    return validated


def _session_output_capacity(
    request: ClassicRunRequest,
    *,
    max_runs: int,
) -> int:
    output_capacity = len(request.output_bytes) + (
        request.step_budget * max_runs
    )
    if output_capacity > MAX_U32:
        message = (
            "resident session output capacity exceeds unsigned 32-bit domain: "
            f"{output_capacity}"
        )
        raise InvalidPrimitiveBatchError(message)
    return output_capacity


def _resident_item_bytes(
    request: ClassicRunRequest,
    *,
    output_budget_multiplier: int = 1,
) -> int:
    output_capacity = _session_output_capacity(
        request,
        max_runs=output_budget_multiplier,
    )
    words = (
        STATE_WORDS + MEMORY_WORDS + len(request.input_bytes) + output_capacity
    )
    return words * _DEVICE_WORD_BYTES


def _encode_variable_state(
    requests: tuple[ClassicRunRequest, ...],
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
        additional_output = output_capacity - len(request.output_bytes)
        outputs.extend(request.output_bytes)
        outputs.extend(0 for _slot in range(additional_output))
        for value, label in (
            (input_offset, "resident input offset"),
            (output_offset, "resident output offset"),
            (output_capacity, "resident output capacity"),
        ):
            if value > MAX_U32:
                message = f"{label} outside unsigned 32-bit domain: {value}"
                raise InvalidPrimitiveBatchError(message)
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


def _build_memory_owner(
    requests: tuple[ClassicRunRequest, ...],
) -> array[int]:
    first = requests[0].memory
    if all(request.memory is first for request in requests):
        return array("I", first) * len(requests)
    memories = array("I")
    for request in requests:
        memories.extend(request.memory)
    return memories


def _build_host_batch(
    requests: tuple[ClassicRunRequest, ...],
    *,
    output_budget_multiplier: int = 1,
) -> _HostBatch:
    states, inputs, outputs = _encode_variable_state(
        requests,
        output_budget_multiplier=output_budget_multiplier,
    )
    memories = _build_memory_owner(requests)
    if not inputs:
        inputs.append(0)
    if not outputs:
        outputs.append(0)
    return _HostBatch(
        states=_word_buffer(states),
        memories=_word_buffer(memories),
        inputs=_word_buffer(inputs),
        outputs=_word_buffer(outputs),
    )


def _decode_observations(
    states: array[int],
    count: int,
) -> tuple[ClassicRunObservation, ...]:
    observations: list[ClassicRunObservation] = []
    for index in range(count):
        base = index * STATE_WORDS
        observations.append(
            ClassicRunObservation(
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


def _free_resident_chunks(
    runtime: CudaRuntime,
    chunks: list[_ResidentChunk] | tuple[_ResidentChunk, ...],
) -> None:
    for chunk in reversed(chunks):
        _free_all(runtime, list(chunk.pointers))


def _upload_host_batch(
    runtime: CudaRuntime,
    hosts: _HostBatch,
) -> tuple[int, int, int, int]:
    pointers: list[int] = []
    try:
        pointers.extend(
            _copy_words(runtime, host)
            for host in (
                hosts.states,
                hosts.memories,
                hosts.inputs,
                hosts.outputs,
            )
        )
    except AcceleratorExecutionError:
        _free_all(runtime, pointers)
        raise
    return pointers[0], pointers[1], pointers[2], pointers[3]


def _copy_words(runtime: CudaRuntime, host: _WordBuffer) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host.view))
    try:
        runtime.copy_to_device(pointer, host.view)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _decode_results(
    hosts: _HostBatch,
    *,
    count: int,
) -> tuple[ClassicRunResult, ...]:
    states = hosts.states.owner
    memories = hosts.memories.owner
    outputs = hosts.outputs.owner
    results: list[ClassicRunResult] = []
    for index in range(count):
        base = index * STATE_WORDS
        memory_base = index * MEMORY_WORDS
        output_offset = states[base + 6]
        output_len = states[base + 7]
        results.append(
            ClassicRunResult(
                accumulator=states[base],
                code_pointer=states[base + 1],
                data_pointer=states[base + 2],
                error=RunError(states[base + _ERROR_INDEX]),
                error_pointer=states[base + _ERROR_POINTER_INDEX],
                error_value=states[base + _ERROR_VALUE_INDEX],
                input_consumed=states[base + 5],
                memory=tuple(
                    memories[memory_base : memory_base + MEMORY_WORDS]
                ),
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
    if owner.itemsize != _DEVICE_WORD_BYTES:
        message = (
            "host unsigned-int width is incompatible with CUDA u32 buffers: "
            f"{owner.itemsize} bytes"
        )
        raise AcceleratorExecutionError(message)
    host_type = ctypes.c_uint32 * len(owner)
    return _WordBuffer(owner=owner, view=host_type.from_buffer(owner))
