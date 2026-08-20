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
#   - CUDA implementation of compact normative classic one-step transitions.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""CUDA implementation of compact normative classic one-step transitions."""

from __future__ import annotations

import ctypes
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import final

from accelerator.classic_step import ClassicStepResult
from accelerator.classic_step import REQUEST_WORDS
from accelerator.classic_step import RESULT_WORDS
from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from accelerator.classic_step import ClassicStepRequest

XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    b".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)
XLAT2: Final = (
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C"
    b"B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
)


def _kernel_source() -> str:
    xlat1 = ",".join(str(value) for value in XLAT1)
    xlat2 = ",".join(str(value) for value in XLAT2)
    return f"""
#define REQUEST_WORDS {REQUEST_WORDS}u
#define RESULT_WORDS {RESULT_WORDS}u
#define MAX_WORD 59048u
#define MAX_SLOTS 4u
#define STATUS_CONTINUED 0u
#define STATUS_TERMINATED 1u
#define STATUS_ERROR 2u
#define ERROR_NONE 0u
#define ERROR_INVALID_ENCRYPTION 1u
#define ERROR_INVALID_REQUEST 2u
#define TERMINATION_NONE 0u
#define TERMINATION_HALT 1u
#define TERMINATION_NON_GRAPHICAL 2u
#define INPUT_NONE 0u
#define INPUT_BYTE 1u
#define INPUT_EOF 2u

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

static __device__ bool read_cell(
    const unsigned int* request,
    unsigned int address,
    unsigned int* value
) {{
    for (unsigned int slot = 0u; slot < MAX_SLOTS; ++slot) {{
        unsigned int base = 8u + (slot * 3u);
        if (request[base] != 0u && request[base + 1u] == address) {{
            *value = request[base + 2u];
            return true;
        }}
    }}
    return false;
}}

static __device__ void initialize_result(
    const unsigned int* request,
    unsigned int* result
) {{
    for (unsigned int index = 0u; index < RESULT_WORDS; ++index) {{
        result[index] = 0u;
    }}
    result[2] = request[0];
    result[3] = request[1];
    result[4] = request[2];
    result[5] = request[3];
    result[6] = request[4];
    result[7] = request[5];
}}

static __device__ void invalid_request(unsigned int* result) {{
    result[0] = STATUS_ERROR;
    result[1] = ERROR_INVALID_REQUEST;
}}

extern "C" __global__ void malbolge_classic_step_batch(
    const unsigned int* requests,
    unsigned int* results,
    unsigned int count
) {{
    unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= count) {{
        return;
    }}
    const unsigned int* request = requests + (index * REQUEST_WORDS);
    unsigned int* result = results + (index * RESULT_WORDS);
    initialize_result(request, result);

    unsigned int a = request[0];
    unsigned int c = request[1];
    unsigned int d = request[2];
    unsigned int input_consumed = request[3];
    unsigned int output_len = request[4];
    unsigned int termination = request[5];
    if (a > MAX_WORD || c > MAX_WORD || d > MAX_WORD || termination > 2u) {{
        invalid_request(result);
        return;
    }}
    if (termination != TERMINATION_NONE) {{
        result[0] = STATUS_TERMINATED;
        return;
    }}

    unsigned int cell = 0u;
    if (!read_cell(request, c, &cell) || cell > MAX_WORD) {{
        invalid_request(result);
        return;
    }}
    result[8] = 1u;
    result[9] = cell;
    if (!graphical(cell)) {{
        result[0] = STATUS_CONTINUED;
        result[7] = TERMINATION_NONE;
        return;
    }}

    unsigned int phase = c % 94u;
    unsigned int decoded = XLAT1[((cell - 33u) + phase) % 94u];
    result[10] = 1u;
    result[11] = decoded;
    if (decoded == (unsigned int)'v') {{
        result[0] = STATUS_TERMINATED;
        result[7] = TERMINATION_HALT;
        return;
    }}

    unsigned int planned_a = a;
    unsigned int planned_c = c;
    unsigned int planned_d = d;
    unsigned int data_before = 0u;
    unsigned int data_after = 0u;
    bool data_write = false;
    unsigned int input_kind = INPUT_NONE;
    unsigned int input_value = 0u;
    bool input_advance = false;
    bool output_present = false;
    unsigned int output_value = 0u;

    if (decoded == (unsigned int)'p' || decoded == (unsigned int)'*'
        || decoded == (unsigned int)'i' || decoded == (unsigned int)'j') {{
        if (!read_cell(request, d, &data_before) || data_before > MAX_WORD) {{
            invalid_request(result);
            return;
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
        if (output_len == 0xffffffffu) {{
            invalid_request(result);
            return;
        }}
        output_present = true;
        output_value = a & 255u;
    }} else if (decoded == (unsigned int)'/') {{
        if (request[6] != 0u) {{
            if (request[7] > 255u || input_consumed == 0xffffffffu) {{
                invalid_request(result);
                return;
            }}
            planned_a = request[7];
            input_kind = INPUT_BYTE;
            input_value = request[7];
            input_advance = true;
        }} else {{
            planned_a = MAX_WORD;
            input_kind = INPUT_EOF;
        }}
    }}

    unsigned int encryption_pointer = planned_c;
    unsigned int encryption_before = 0u;
    if (!read_cell(request, encryption_pointer, &encryption_before)
        || encryption_before > MAX_WORD) {{
        invalid_request(result);
        return;
    }}
    unsigned int encryption_input = encryption_before;
    if (data_write && d == encryption_pointer) {{
        encryption_input = data_after;
    }}
    if (!graphical(encryption_input)) {{
        result[0] = STATUS_ERROR;
        result[1] = ERROR_INVALID_ENCRYPTION;
        result[24] = encryption_pointer;
        result[25] = encryption_input;
        return;
    }}
    unsigned int encryption_after = XLAT2[encryption_input - 33u];

    result[0] = STATUS_CONTINUED;
    result[2] = planned_a;
    result[3] = successor(planned_c);
    result[4] = successor(planned_d);
    result[5] = input_consumed + (input_advance ? 1u : 0u);
    result[6] = output_len + (output_present ? 1u : 0u);
    result[7] = TERMINATION_NONE;
    result[12] = input_kind;
    result[13] = input_value;
    result[14] = output_present ? 1u : 0u;
    result[15] = output_value;

    if (data_write && d != encryption_pointer && data_before != data_after) {{
        result[16] = 1u;
        result[17] = d;
        result[18] = data_before;
        result[19] = data_after;
    }}
    if (encryption_before != encryption_after) {{
        result[20] = 1u;
        result[21] = encryption_pointer;
        result[22] = encryption_before;
        result[23] = encryption_after;
    }}
}}
"""


@final
class CudaClassicStepAdapter:
    """Specification-only compact classic one-step CUDA adapter."""

    def __init__(self, device_id: int = 0) -> None:
        """Compile the reviewed compact classic transition kernel.

        Raises:
            AcceleratorExecutionError: If kernel compilation/loading fails.

        """
        runtime = CudaRuntime(device_id)
        try:
            info = runtime.device_info
            module = runtime.compile_module(_kernel_source(), info.arch)
            kernel = runtime.get_kernel(module, b"malbolge_classic_step_batch")
        except AcceleratorExecutionError:
            runtime.close()
            raise
        self._capability = AcceleratorCapability(
            backend_id="cuda-classic-step",
            device_arch=info.arch,
            device_name=info.name,
        )
        self._closed = False
        self._kernel = kernel
        self._module = module
        self._runtime = runtime

    def __enter__(self) -> Self:
        """Return the live adapter for scoped use.

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
        """Release the CUDA module/context at scope exit."""
        self.close()

    def capability(self) -> AcceleratorCapability:
        """Return selected CUDA device identity.

        Returns:
            Stable accelerator/device metadata.

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
        requests: Sequence[ClassicStepRequest],
    ) -> tuple[ClassicStepResult, ...]:
        """Evaluate independent compact classic transitions on CUDA.

        Returns:
            Results in exact request order.

        Raises:
            AcceleratorExecutionError: If this adapter was already closed.

        """
        if self._closed:
            message = "CUDA classic-step adapter is closed"
            raise AcceleratorExecutionError(message)
        if not requests:
            return ()
        request_words = tuple(
            word for request in requests for word in request.to_words()
        )
        host_requests = _host_words(request_words)
        host_results = _host_words((0,) * (len(requests) * RESULT_WORDS))
        pointers: list[int] = []
        try:
            device_requests = _copy_words(self._runtime, host_requests)
            pointers.append(device_requests)
            device_results = self._runtime.allocate(ctypes.sizeof(host_results))
            pointers.append(device_results)
            self._runtime.launch(
                self._kernel,
                (device_requests, device_results),
                len(requests),
            )
            self._runtime.copy_from_device(host_results, device_results)
            return _decode_results(host_results, len(requests))
        finally:
            _free_all(self._runtime, pointers)


def _copy_words(
    runtime: CudaRuntime, host: ctypes.Array[ctypes.c_uint32]
) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host))
    try:
        runtime.copy_to_device(pointer, host)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _decode_results(
    host: ctypes.Array[ctypes.c_uint32],
    count: int,
) -> tuple[ClassicStepResult, ...]:
    values = tuple(host)
    return tuple(
        ClassicStepResult.from_words(
            values[index * RESULT_WORDS : (index + 1) * RESULT_WORDS]
        )
        for index in range(count)
    )


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _host_words(values: tuple[int, ...]) -> ctypes.Array[ctypes.c_uint32]:
    host_type = ctypes.c_uint32 * len(values)
    return host_type(*values)
