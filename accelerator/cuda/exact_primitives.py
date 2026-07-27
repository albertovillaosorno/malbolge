# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Optional CUDA implementation of exact classic ternary primitive batches."""

from __future__ import annotations

from array import array
import ctypes
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult

if TYPE_CHECKING:
    from accelerator.exact_primitives import PrimitiveBatch

KERNEL_SOURCE: Final = r"""
static __device__ unsigned int crazy_trit(
    unsigned int data,
    unsigned int accumulator
) {
    if (((data == 0u || data == 1u) && accumulator == 0u)
        || (data == 2u && accumulator == 2u)) {
        return 1u;
    }
    if ((data == 1u && accumulator == 2u)
        || (data == 2u && (accumulator == 0u || accumulator == 1u))) {
        return 2u;
    }
    return 0u;
}

extern "C" __global__ void malbolge_crazy_batch(
    const unsigned int* data,
    const unsigned int* accumulator,
    unsigned int* output,
    unsigned int count
) {
    unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= count) {
        return;
    }
    unsigned int left = data[index];
    unsigned int right = accumulator[index];
    unsigned int result = 0u;
    unsigned int place = 1u;
    for (unsigned int trit = 0u; trit < 10u; ++trit) {
        result += crazy_trit(left % 3u, right % 3u) * place;
        place *= 3u;
        left /= 3u;
        right /= 3u;
    }
    output[index] = result;
}

extern "C" __global__ void malbolge_rotate_batch(
    const unsigned int* data,
    unsigned int* output,
    unsigned int count
) {
    unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index < count) {
        unsigned int value = data[index];
        output[index] = (value / 3u) + ((value % 3u) * 19683u);
    }
}
"""


@final
class CudaExactPrimitiveAdapter(ExactPrimitiveAdapter):
    """Exact integer CUDA batch adapter with no semantic authority."""

    _closed: bool
    _crazy: ctypes.c_void_p
    _module: ctypes.c_void_p
    _rotate: ctypes.c_void_p
    _runtime: CudaRuntime

    def __init__(self, device_id: int = 0) -> None:
        """Create one optional CUDA adapter and compile reviewed kernels.

        Raises:
            AcceleratorExecutionError: If kernel compilation/loading fails.

        """
        runtime = CudaRuntime(device_id)
        try:
            info = runtime.device_info
            module = runtime.compile_module(KERNEL_SOURCE, info.arch)
            crazy = runtime.get_kernel(module, b"malbolge_crazy_batch")
            rotate = runtime.get_kernel(module, b"malbolge_rotate_batch")
        except AcceleratorExecutionError:
            runtime.close()
            raise
        self._capability = AcceleratorCapability(
            backend_id="cuda",
            device_arch=info.arch,
            device_name=info.name,
        )
        self._closed = False
        self._crazy = crazy
        self._module = module
        self._rotate = rotate
        self._runtime = runtime

    def __enter__(self) -> Self:
        """Return this adapter for scoped use.

        Returns:
            The same live adapter instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release CUDA resources at scope exit."""
        self.close()

    @override
    def capability(self) -> AcceleratorCapability:
        """Return exact CUDA backend/device identity.

        Returns:
            Stable capability identity for this adapter instance.

        """
        return self._capability

    def close(self) -> None:
        """Release the loaded module and CUDA context exactly once."""
        if self._closed:
            return
        self._closed = True
        try:
            self._runtime.unload_module(self._module)
        finally:
            self._runtime.close()

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        """Evaluate one exact primitive batch on CUDA.

        Returns:
            Exact integer outputs copied back in input order.

        Raises:
            AcceleratorExecutionError: If the adapter has already been closed.

        """
        if self._closed:
            message = "CUDA adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = batch.validated()
        if not validated.data:
            return PrimitiveResult(capability=self._capability, values=())
        if validated.kind is PrimitiveKind.ROTATE:
            values = self._evaluate_rotate(validated.data)
        else:
            values = self._evaluate_crazy(
                validated.data, validated.accumulators
            )
        return PrimitiveResult(capability=self._capability, values=values)

    def _evaluate_crazy(
        self,
        data: tuple[int, ...],
        accumulator: tuple[int, ...],
    ) -> tuple[int, ...]:
        host_data = _host_words(data)
        host_accumulator = _host_words(accumulator)
        host_output = _host_words((0,) * len(data))
        pointers: list[int] = []
        try:
            device_data = _copy_words(self._runtime, host_data)
            pointers.append(device_data)
            device_accumulator = _copy_words(self._runtime, host_accumulator)
            pointers.append(device_accumulator)
            device_output = self._runtime.allocate(ctypes.sizeof(host_output))
            pointers.append(device_output)
            self._runtime.launch(
                self._crazy,
                (device_data, device_accumulator, device_output),
                len(data),
            )
            self._runtime.copy_from_device(host_output, device_output)
            return _host_values(host_output)
        finally:
            _free_all(self._runtime, pointers)

    def _evaluate_rotate(self, data: tuple[int, ...]) -> tuple[int, ...]:
        host_data = _host_words(data)
        host_output = _host_words((0,) * len(data))
        pointers: list[int] = []
        try:
            device_data = _copy_words(self._runtime, host_data)
            pointers.append(device_data)
            device_output = self._runtime.allocate(ctypes.sizeof(host_output))
            pointers.append(device_output)
            self._runtime.launch(
                self._rotate,
                (device_data, device_output),
                len(data),
            )
            self._runtime.copy_from_device(host_output, device_output)
            return _host_values(host_output)
        finally:
            _free_all(self._runtime, pointers)


def _copy_words(
    runtime: CudaRuntime,
    host: ctypes.Array[ctypes.c_uint32],
) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host))
    try:
        runtime.copy_to_device(pointer, host)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _host_values(host: ctypes.Array[ctypes.c_uint32]) -> tuple[int, ...]:
    words = array("I")
    words.frombytes(bytes(host))
    return tuple(words)


def _host_words(values: tuple[int, ...]) -> ctypes.Array[ctypes.c_uint32]:
    host_type = ctypes.c_uint32 * len(values)
    return host_type(*values)
