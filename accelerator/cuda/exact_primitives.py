# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Optional CUDA implementation of exact classic ternary primitive batches."""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cuda.runtime import CudaRuntime
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult

if TYPE_CHECKING:
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveBatch
    from accelerator.exact_primitives import PrimitiveExecutionResult

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


@dataclass(frozen=True, slots=True)
class CudaPreparedPrimitiveStats:
    """Observable proof that prepared CUDA input is built and reused."""

    builds: int
    evaluations: int
    packed_evaluations: int
    resident_count: int
    resident_kind: PrimitiveKind | None
    reuses: int


@dataclass(frozen=True, slots=True)
class CudaPreparedPrimitivePhaseProfile:
    """Diagnostic wall-clock phases for one resident prepared evaluation."""

    download_ns: int
    immutable_bytes_ns: int
    launch_sync_ns: int
    total_ns: int


@dataclass(slots=True)
class _PreparedPointerOwner:
    runtime: CudaRuntime
    pointers: list[int]

    def allocate(self, byte_count: int) -> int:
        pointer = self.runtime.allocate(byte_count)
        self.pointers.append(pointer)
        return pointer

    def copy(self, host: ctypes.Array[ctypes.c_uint32]) -> int:
        pointer = _copy_words(self.runtime, host)
        self.pointers.append(pointer)
        return pointer

    def close(self) -> None:
        _free_all(self.runtime, self.pointers)


@dataclass(slots=True)
class _CudaPreparedPrimitiveSession:
    prepared: PreparedPrimitiveBatch
    batch: PrimitiveBatch
    device_accumulator: int | None
    device_data: int | None
    device_output: int | None
    host_output: ctypes.Array[ctypes.c_uint32]
    _closed: bool = False

    @classmethod
    def build(
        cls,
        runtime: CudaRuntime,
        prepared: PreparedPrimitiveBatch,
        batch: PrimitiveBatch,
    ) -> _CudaPreparedPrimitiveSession:
        count = len(batch.data)
        host_output = _empty_host_words(count)
        if count == 0:
            return cls(
                prepared=prepared,
                batch=batch,
                device_accumulator=None,
                device_data=None,
                device_output=None,
                host_output=host_output,
            )
        owner = _PreparedPointerOwner(runtime=runtime, pointers=[])
        try:
            device_data = owner.copy(_host_words(batch.data))
            device_accumulator = _prepared_accumulator(owner, batch)
            device_output = owner.allocate(ctypes.sizeof(host_output))
            return cls(
                prepared=prepared,
                batch=batch,
                device_accumulator=device_accumulator,
                device_data=device_data,
                device_output=device_output,
                host_output=host_output,
            )
        except AcceleratorExecutionError:
            owner.close()
            raise

    def close(self, runtime: CudaRuntime) -> None:
        if self._closed:
            return
        self._closed = True
        pointers = [
            pointer
            for pointer in (
                self.device_data,
                self.device_accumulator,
                self.device_output,
            )
            if pointer is not None
        ]
        _free_all(runtime, pointers)

    def evaluate(
        self,
        runtime: CudaRuntime,
        crazy: ctypes.c_void_p,
        rotate: ctypes.c_void_p,
    ) -> bytes:
        count = len(self.batch.data)
        if count == 0:
            return b""
        self._launch(
            runtime,
            crazy=crazy,
            rotate=rotate,
            count=count,
        )
        if self.device_output is None:
            message = "prepared CUDA primitive session has no output buffer"
            raise AcceleratorExecutionError(message)
        runtime.copy_from_device(self.host_output, self.device_output)
        return bytes(self.host_output)

    def profile_evaluate(
        self,
        runtime: CudaRuntime,
        crazy: ctypes.c_void_p,
        rotate: ctypes.c_void_p,
    ) -> tuple[bytes, CudaPreparedPrimitivePhaseProfile]:
        """Evaluate the same resident path with diagnostic phase timings.

        Returns:
            Packed words plus immutable per-phase timing evidence.

        Raises:
            AcceleratorExecutionError: If resident buffers or CUDA fail.

        """
        total_start = perf_counter_ns()
        count = len(self.batch.data)
        if count == 0:
            return b"", CudaPreparedPrimitivePhaseProfile(
                download_ns=0,
                immutable_bytes_ns=0,
                launch_sync_ns=0,
                total_ns=perf_counter_ns() - total_start,
            )
        launch_start = perf_counter_ns()
        self._launch(
            runtime,
            crazy=crazy,
            rotate=rotate,
            count=count,
        )
        launch_sync_ns = perf_counter_ns() - launch_start
        if self.device_output is None:
            message = "prepared CUDA primitive session has no output buffer"
            raise AcceleratorExecutionError(message)
        download_start = perf_counter_ns()
        runtime.copy_from_device(self.host_output, self.device_output)
        download_ns = perf_counter_ns() - download_start
        bytes_start = perf_counter_ns()
        words_u32le = bytes(self.host_output)
        immutable_bytes_ns = perf_counter_ns() - bytes_start
        return words_u32le, CudaPreparedPrimitivePhaseProfile(
            download_ns=download_ns,
            immutable_bytes_ns=immutable_bytes_ns,
            launch_sync_ns=launch_sync_ns,
            total_ns=perf_counter_ns() - total_start,
        )

    def _launch(
        self,
        runtime: CudaRuntime,
        *,
        crazy: ctypes.c_void_p,
        rotate: ctypes.c_void_p,
        count: int,
    ) -> None:
        if self.device_data is None or self.device_output is None:
            message = "prepared CUDA primitive session has missing buffers"
            raise AcceleratorExecutionError(message)
        if self.batch.kind is PrimitiveKind.ROTATE:
            runtime.launch(
                rotate,
                (self.device_data, self.device_output),
                count,
            )
            return
        if self.device_accumulator is None:
            message = "prepared CUDA crazy session has no accumulator"
            raise AcceleratorExecutionError(message)
        runtime.launch(
            crazy,
            (
                self.device_data,
                self.device_accumulator,
                self.device_output,
            ),
            count,
        )


@final
class CudaExactPrimitiveAdapter(ExactPrimitiveAdapter):
    """Exact integer CUDA batch adapter with no semantic authority."""

    _closed: bool
    _crazy: ctypes.c_void_p
    _module: ctypes.c_void_p
    _prepared_builds: int
    _prepared_evaluations: int
    _prepared_packed_evaluations: int
    _prepared_reuses: int
    _prepared_session: _CudaPreparedPrimitiveSession | None
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
        self._prepared_builds = 0
        self._prepared_evaluations = 0
        self._prepared_packed_evaluations = 0
        self._prepared_reuses = 0
        self._prepared_session = None
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
        """Release resident buffers, module, and CUDA context exactly once."""
        if self._closed:
            return
        self._closed = True
        try:
            try:
                self._release_prepared_session()
            finally:
                self._runtime.unload_module(self._module)
        finally:
            self._runtime.close()

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        """Evaluate one exact primitive batch on CUDA.

        Returns:
            Exact integer outputs copied back in input order.

        """
        self._ensure_open()
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

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveExecutionResult:
        """Evaluate immutable prepared input through one resident CUDA session.

        Returns:
            Exact integer outputs copied back in input order.

        Raises:
            AcceleratorExecutionError: If the adapter/session cannot execute.

        """
        self._ensure_open()
        session = self._prepared_session_for(prepared)
        try:
            words_u32le = session.evaluate(
                self._runtime,
                self._crazy,
                self._rotate,
            )
        except AcceleratorExecutionError:
            self._release_prepared_session()
            raise
        self._prepared_evaluations += 1
        self._prepared_packed_evaluations += 1
        return PackedPrimitiveResult(
            capability=self._capability,
            words_u32le=words_u32le,
        )

    def profile_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> tuple[PackedPrimitiveResult, CudaPreparedPrimitivePhaseProfile]:
        """Evaluate prepared input while recording resident CUDA phases.

        Returns:
            Packed exact output plus launch/download/materialization timings.

        Raises:
            AcceleratorExecutionError: If the adapter/session cannot execute.

        """
        self._ensure_open()
        session = self._prepared_session_for(prepared)
        try:
            words_u32le, profile = session.profile_evaluate(
                self._runtime,
                self._crazy,
                self._rotate,
            )
        except AcceleratorExecutionError:
            self._release_prepared_session()
            raise
        self._prepared_evaluations += 1
        self._prepared_packed_evaluations += 1
        return (
            PackedPrimitiveResult(
                capability=self._capability,
                words_u32le=words_u32le,
            ),
            profile,
        )

    def prepared_stats(self) -> CudaPreparedPrimitiveStats:
        """Return resident prepared-session build and reuse evidence.

        Returns:
            Immutable counters plus current resident batch identity.

        """
        session = self._prepared_session
        return CudaPreparedPrimitiveStats(
            builds=self._prepared_builds,
            evaluations=self._prepared_evaluations,
            packed_evaluations=self._prepared_packed_evaluations,
            resident_count=(0 if session is None else len(session.batch.data)),
            resident_kind=(None if session is None else session.batch.kind),
            reuses=self._prepared_reuses,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            message = "CUDA adapter is closed"
            raise AcceleratorExecutionError(message)

    def _prepared_session_for(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> _CudaPreparedPrimitiveSession:
        current = self._prepared_session
        if current is not None and current.prepared is prepared:
            self._prepared_reuses += 1
            return current
        batch = prepared.validated_batch()
        self._release_prepared_session()
        session = _CudaPreparedPrimitiveSession.build(
            self._runtime,
            prepared,
            batch,
        )
        self._prepared_session = session
        self._prepared_builds += 1
        return session

    def _release_prepared_session(self) -> None:
        session = self._prepared_session
        if session is None:
            return
        self._prepared_session = None
        session.close(self._runtime)

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


def _prepared_accumulator(
    owner: _PreparedPointerOwner,
    batch: PrimitiveBatch,
) -> int | None:
    if batch.kind is PrimitiveKind.ROTATE:
        return None
    return owner.copy(_host_words(batch.accumulators))


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


def _empty_host_words(count: int) -> ctypes.Array[ctypes.c_uint32]:
    host_type = ctypes.c_uint32 * count
    return host_type()


def _host_words(values: tuple[int, ...]) -> ctypes.Array[ctypes.c_uint32]:
    host_type = ctypes.c_uint32 * len(values)
    return host_type(*values)
