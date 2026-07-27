# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""CUDA resident full-memory bounded execution for classic Malbolge."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import cast
from typing import final

from accelerator.classic_run import ClassicRunResult
from accelerator.classic_run import MAX_U32
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_run import STATE_WORDS
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.classic_step import XLAT2
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
class _HostBatch:
    states: HostWords
    memories: HostWords
    inputs: HostWords
    outputs: HostWords


def _kernel_source() -> str:
    xlat1 = ",".join(str(value) for value in XLAT1)
    xlat2 = ",".join(str(value) for value in XLAT2)
    return f"""
#define MEMORY_WORDS {MEMORY_WORDS}u
#define STATE_WORDS {STATE_WORDS}u
#define MAX_WORD 59048u
#define STATUS_BUDGET 0u
#define STATUS_TERMINATED 1u
#define STATUS_ERROR 2u
#define ERROR_NONE 0u
#define ERROR_INVALID_ENCRYPTION 1u
#define ERROR_INVALID_REQUEST 2u
#define TERMINATION_NONE 0u
#define TERMINATION_HALT 1u
#define TERMINATION_NON_GRAPHICAL 2u

static __device__ __constant__ unsigned char XLAT1[94] = {{{xlat1}}};
static __device__ __constant__ unsigned char XLAT2[94] = {{{xlat2}}};

static __device__ unsigned int successor(unsigned int value) {{
    return value == MAX_WORD ? 0u : value + 1u;
}}

static __device__ unsigned int rotate_word(unsigned int value) {{
    return (value / 3u) + ((value % 3u) * 19683u);
}}

static __device__ unsigned int crazy_trit(
    unsigned int data,
    unsigned int acc
) {{
    if (((data == 0u || data == 1u) && acc == 0u)
        || (data == 2u && acc == 2u)) {{
        return 1u;
    }}
    if ((data == 1u && acc == 2u)
        || (data == 2u && (acc == 0u || acc == 1u))) {{
        return 2u;
    }}
    return 0u;
}}

static __device__ unsigned int crazy_word(
    unsigned int data,
    unsigned int acc
) {{
    unsigned int result = 0u;
    unsigned int place = 1u;
    for (unsigned int trit = 0u; trit < 10u; ++trit) {{
        result += crazy_trit(data % 3u, acc % 3u) * place;
        place *= 3u;
        data /= 3u;
        acc /= 3u;
    }}
    return result;
}}

static __device__ bool graphical(unsigned int value) {{
    return value >= 33u && value <= 126u;
}}

static __device__ void reject(
    unsigned int* state,
    unsigned int error,
    unsigned int pointer,
    unsigned int value
) {{
    state[11] = STATUS_ERROR;
    state[12] = error;
    state[13] = pointer;
    state[14] = value;
}}

extern "C" __global__ void malbolge_classic_run_batch(
    unsigned int* states,
    unsigned int* memories,
    const unsigned int* inputs,
    unsigned int* outputs,
    unsigned int count
) {{
    unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= count) {{
        return;
    }}
    unsigned int* state = states + (index * STATE_WORDS);
    unsigned int* memory = memories + (index * MEMORY_WORDS);
    unsigned int a = state[0];
    unsigned int c = state[1];
    unsigned int d = state[2];
    unsigned int input_offset = state[3];
    unsigned int input_len = state[4];
    unsigned int input_consumed = state[5];
    unsigned int output_offset = state[6];
    unsigned int output_len = state[7];
    unsigned int output_capacity = state[8];
    unsigned int step_budget = state[9];
    unsigned int termination = state[10];

    state[11] = STATUS_BUDGET;
    state[12] = ERROR_NONE;
    state[13] = 0u;
    state[14] = 0u;
    state[15] = 0u;
    if (a > MAX_WORD || c > MAX_WORD || d > MAX_WORD
        || termination > TERMINATION_NON_GRAPHICAL
        || input_consumed > input_len || output_len > output_capacity) {{
        reject(state, ERROR_INVALID_REQUEST, 0u, 0u);
        return;
    }}
    if (termination != TERMINATION_NONE) {{
        state[11] = STATUS_TERMINATED;
        return;
    }}

    for (unsigned int step = 0u; step < step_budget; ++step) {{
        unsigned int cell = memory[c];
        if (cell > MAX_WORD) {{
            reject(state, ERROR_INVALID_REQUEST, c, cell);
            break;
        }}
        if (!graphical(cell)) {{
            termination = TERMINATION_NON_GRAPHICAL;
            state[11] = STATUS_TERMINATED;
            state[15] += 1u;
            break;
        }}
        unsigned int decoded = XLAT1[((cell - 33u) + (c % 94u)) % 94u];
        if (decoded == (unsigned int)'v') {{
            termination = TERMINATION_HALT;
            state[11] = STATUS_TERMINATED;
            state[15] += 1u;
            break;
        }}
        unsigned int planned_a = a;
        unsigned int planned_c = c;
        unsigned int planned_d = d;
        unsigned int data_before = 0u;
        unsigned int data_after = 0u;
        bool data_write = false;
        bool input_advance = false;
        bool output_present = false;
        unsigned int output_value = 0u;

        if (decoded == (unsigned int)'p' || decoded == (unsigned int)'*'
            || decoded == (unsigned int)'i' || decoded == (unsigned int)'j') {{
            data_before = memory[d];
            if (data_before > MAX_WORD) {{
                reject(state, ERROR_INVALID_REQUEST, d, data_before);
                break;
            }}
        }}
        if (decoded == (unsigned int)'p') {{
            data_after = crazy_word(data_before, a);
            planned_a = data_after;
            data_write = true;
        }} else if (decoded == (unsigned int)'*') {{
            data_after = rotate_word(data_before);
            planned_a = data_after;
            data_write = true;
        }} else if (decoded == (unsigned int)'i') {{
            planned_c = data_before;
        }} else if (decoded == (unsigned int)'j') {{
            planned_d = data_before;
        }} else if (decoded == (unsigned int)'<') {{
            if (input_consumed < input_len) {{
                planned_a = inputs[input_offset + input_consumed];
                input_advance = true;
            }} else {{
                planned_a = MAX_WORD;
            }}
        }} else if (decoded == (unsigned int)'/') {{
            if (output_len >= output_capacity) {{
                reject(state, ERROR_INVALID_REQUEST, 0u, 0u);
                break;
            }}
            output_present = true;
            output_value = a & 255u;
        }}

        unsigned int encryption_pointer = planned_c;
        unsigned int encryption_before = memory[encryption_pointer];
        if (encryption_before > MAX_WORD) {{
            reject(
                state,
                ERROR_INVALID_REQUEST,
                encryption_pointer,
                encryption_before
            );
            break;
        }}
        unsigned int encryption_input = encryption_before;
        if (data_write && d == encryption_pointer) {{
            encryption_input = data_after;
        }}
        if (!graphical(encryption_input)) {{
            reject(
                state,
                ERROR_INVALID_ENCRYPTION,
                encryption_pointer,
                encryption_input
            );
            break;
        }}
        unsigned int encryption_after = XLAT2[encryption_input - 33u];

        if (data_write && d != encryption_pointer) {{
            memory[d] = data_after;
        }}
        memory[encryption_pointer] = encryption_after;
        a = planned_a;
        c = successor(planned_c);
        d = successor(planned_d);
        if (input_advance) {{
            input_consumed += 1u;
        }}
        if (output_present) {{
            outputs[output_offset + output_len] = output_value;
            output_len += 1u;
        }}
        state[15] += 1u;
    }}

    state[0] = a;
    state[1] = c;
    state[2] = d;
    state[5] = input_consumed;
    state[7] = output_len;
    state[10] = termination;
}}
"""


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
            module = runtime.compile_module(_kernel_source(), info.arch)
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
        validated = tuple(request.validated() for request in requests)
        plan = self.plan(validated)
        results: list[ClassicRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._evaluate_chunk(validated[chunk.start : chunk.stop])
            )
        return tuple(results)

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
        validated = tuple(request.validated() for request in requests)
        item_bytes = tuple(
            _resident_item_bytes(request) for request in validated
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
            self._runtime.copy_from_device(hosts.states, pointers[0])
            self._runtime.copy_from_device(hosts.memories, pointers[1])
            self._runtime.copy_from_device(hosts.outputs, pointers[3])
            return _decode_results(hosts, count=len(requests))
        finally:
            _free_all(self._runtime, pointers)


def _resident_item_bytes(request: ClassicRunRequest) -> int:
    output_capacity = len(request.output_bytes) + request.step_budget
    words = (
        STATE_WORDS
        + MEMORY_WORDS
        + len(request.input_bytes)
        + output_capacity
    )
    return words * _DEVICE_WORD_BYTES


def _encode_variable_state(
    requests: tuple[ClassicRunRequest, ...],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    states: list[int] = []
    inputs: list[int] = []
    outputs: list[int] = []
    for request in requests:
        input_offset = len(inputs)
        inputs.extend(request.input_bytes)
        output_offset = len(outputs)
        output_capacity = len(request.output_bytes) + request.step_budget
        outputs.extend(request.output_bytes)
        outputs.extend(0 for _slot in range(request.step_budget))
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
    return tuple(states), tuple(inputs), tuple(outputs)


def _build_host_batch(
    requests: tuple[ClassicRunRequest, ...],
) -> _HostBatch:
    state_values, input_values, output_values = _encode_variable_state(requests)
    memory_values = tuple(
        value for request in requests for value in request.memory
    )
    return _HostBatch(
        states=_host_words(state_values),
        memories=_host_words(memory_values),
        inputs=_host_words(input_values or (0,)),
        outputs=_host_words(output_values or (0,)),
    )


def _copy_words(
    runtime: CudaRuntime, host: HostWords
) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host))
    try:
        runtime.copy_to_device(pointer, host)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _decode_results(
    hosts: _HostBatch,
    *,
    count: int,
) -> tuple[ClassicRunResult, ...]:
    state_values = _host_values(hosts.states)
    memory_values = _host_values(hosts.memories)
    output_values = _host_values(hosts.outputs)
    results: list[ClassicRunResult] = []
    for index in range(count):
        base = index * STATE_WORDS
        state = state_values[base : base + STATE_WORDS]
        memory_base = index * MEMORY_WORDS
        output_offset = state[6]
        output_len = state[7]
        results.append(ClassicRunResult(
            accumulator=state[0],
            code_pointer=state[1],
            data_pointer=state[2],
            error=RunError(state[_ERROR_INDEX]),
            error_pointer=state[_ERROR_POINTER_INDEX],
            error_value=state[_ERROR_VALUE_INDEX],
            input_consumed=state[5],
            memory=memory_values[memory_base : memory_base + MEMORY_WORDS],
            output_bytes=output_values[
                output_offset : output_offset + output_len
            ],
            status=RunStatus(state[_STATUS_INDEX]),
            steps=state[_STEPS_INDEX],
            termination=StepTermination(state[10]),
        ))
    return tuple(results)


def _host_values(host: HostWords) -> tuple[int, ...]:
    return tuple(cast("Sequence[int]", cast("object", host)))


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _host_words(values: tuple[int, ...]) -> HostWords:
    host_type = ctypes.c_uint32 * len(values)
    return host_type(*values)
