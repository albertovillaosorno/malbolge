# File:
#   - runtime.py
# Path:
#   - accelerator/cuda/runtime.py
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
#   - Pinned CUDA 13 Driver/NVRTC boundary using standard-library ctypes.
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

"""Pinned CUDA 13 Driver/NVRTC boundary using standard-library ctypes."""

from __future__ import annotations

from collections.abc import Callable
import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final
from typing import cast
from typing import final

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.resource_budget import AcceleratorResources

ROOT: Final = Path(__file__).resolve().parents[2]
CUDA_TOOLKIT: Final = ROOT / ".dependencies" / "cuda" / "13.3.1" / "toolkit"
NVRTC_DLL: Final = CUDA_TOOLKIT / "bin" / "x64" / "nvrtc64_130_0.dll"
CUDA_SUCCESS: Final = 0
NVRTC_SUCCESS: Final = 0
THREADS_PER_BLOCK: Final = 256
CUDA_ATTRIBUTE_MAX_THREADS_PER_BLOCK: Final = 1
CUDA_ATTRIBUTE_MULTIPROCESSOR_COUNT: Final = 16

_CudaFn = Callable[..., int]
type HostWords = ctypes.Array[ctypes.c_uint32]


@dataclass(frozen=True, slots=True)
class CudaDeviceInfo:
    """Stable metadata exposed to hardware-neutral accelerator adapters."""

    arch: str
    max_threads_per_block: int
    multiprocessor_count: int
    name: str


@final
class CudaHostMemoryRegistry:
    """Own page-locked host buffers for one live CUDA context."""

    def __init__(
        self,
        ensure_open: Callable[[], None],
        register_fn: _CudaFn,
        unregister_fn: _CudaFn,
    ) -> None:
        """Bind one context's registration functions and lifetime guard."""
        self._ensure_open = ensure_open
        self._register_fn = register_fn
        self._registrations: dict[int, HostWords] = {}
        self._unregister_fn = unregister_fn

    def register(self, host: HostWords) -> int:
        """Page-lock one stable nonempty host buffer.

        Returns:
            Exact address token required for later unregistration.

        Raises:
            AcceleratorExecutionError: If validation or registration fails.

        """
        self._ensure_open()
        byte_count = ctypes.sizeof(host)
        if byte_count <= 0:
            message = "CUDA host registration requires a nonempty buffer"
            raise AcceleratorExecutionError(message)
        address = ctypes.addressof(host)
        if address in self._registrations:
            message = "CUDA host buffer is already registered"
            raise AcceleratorExecutionError(message)
        _check_execution(
            self._register_fn(ctypes.c_void_p(address), byte_count, 0),
            "cuMemHostRegister_v2",
        )
        self._registrations[address] = host
        return address

    def unregister(self, address: int) -> None:
        """Release one exact page-locked host-address token.

        Raises:
            AcceleratorExecutionError: If the token is invalid or CUDA fails.

        """
        self._ensure_open()
        if type(address) is not int or address <= 0:
            message = "CUDA host unregistration requires a positive address"
            raise AcceleratorExecutionError(message)
        if address not in self._registrations:
            message = "CUDA host unregistration token is not owned"
            raise AcceleratorExecutionError(message)
        _check_execution(
            self._unregister_fn(ctypes.c_void_p(address)),
            "cuMemHostUnregister",
        )
        del self._registrations[address]

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Attempt every owned unregistration.

        Returns:
            First Driver API failure, or ``None`` after complete release.

        """
        failure: AcceleratorExecutionError | None = None
        for address in tuple(self._registrations):
            try:
                self.unregister(address)
            except AcceleratorExecutionError as error:
                if failure is None:
                    failure = error
        return failure

    def clear(self) -> None:
        """Drop retained buffers after the owning context is destroyed."""
        self._registrations.clear()


class CudaResourceProbe:
    """Read dynamic CUDA memory with stable device compute metadata."""

    _device_info: CudaDeviceInfo
    _get_info: _CudaFn

    def __init__(self, get_info: _CudaFn, device_info: CudaDeviceInfo) -> None:
        """Bind memory-info query and immutable device compute metadata."""
        self._device_info = device_info
        self._get_info = get_info

    def snapshot(self) -> AcceleratorResources:
        """Measure current free memory and stable compute capacity.

        Returns:
            Hardware-neutral accelerator resource evidence.

        """
        free_bytes = ctypes.c_size_t()
        total_bytes = ctypes.c_size_t()
        _check_execution(
            self._get_info(
                ctypes.byref(free_bytes),
                ctypes.byref(total_bytes),
            ),
            "cuMemGetInfo_v2",
        )
        return AcceleratorResources(
            free_memory_bytes=free_bytes.value,
            max_threads_per_block=self._device_info.max_threads_per_block,
            multiprocessor_count=self._device_info.multiprocessor_count,
            total_memory_bytes=total_bytes.value,
        ).validated()


class CudaRuntime:
    """Minimal reviewed CUDA Driver/NVRTC surface for optional accelerators."""

    _closed: bool
    _context: ctypes.c_void_p
    _device: int
    _dll_directory: object
    _driver: ctypes.WinDLL
    _nvrtc: ctypes.WinDLL
    device_info: CudaDeviceInfo
    host_memory: CudaHostMemoryRegistry
    resources: CudaResourceProbe

    _cu_ctx_create: _CudaFn
    _cu_ctx_destroy: _CudaFn
    _cu_ctx_synchronize: _CudaFn
    _cu_device_compute_capability: _CudaFn
    _cu_device_get: _CudaFn
    _cu_device_get_attribute: _CudaFn
    _cu_device_get_name: _CudaFn
    _cu_init: _CudaFn
    _cu_launch_kernel: _CudaFn
    _cu_mem_alloc: _CudaFn
    _cu_mem_get_info: _CudaFn
    _cu_mem_host_register: _CudaFn
    _cu_mem_host_unregister: _CudaFn
    _cu_mem_free: _CudaFn
    _cu_memcpy_dtod: _CudaFn
    _cu_memcpy_dtoh: _CudaFn
    _cu_memcpy_htod: _CudaFn
    _cu_module_get_function: _CudaFn
    _cu_module_load_data: _CudaFn
    _cu_module_unload: _CudaFn

    _nvrtc_compile_program: _CudaFn
    _nvrtc_create_program: _CudaFn
    _nvrtc_destroy_program: _CudaFn
    _nvrtc_get_log: _CudaFn
    _nvrtc_get_log_size: _CudaFn
    _nvrtc_get_ptx: _CudaFn
    _nvrtc_get_ptx_size: _CudaFn

    def __init__(self, device_id: int = 0) -> None:
        """Load pinned CUDA runtime components and create one device context.

        Raises:
            AcceleratorUnavailableError:
                If toolkit, driver, or device is absent.

        """
        _configure_toolkit_environment()
        self._dll_directory = _add_cuda_dll_directory()
        try:
            self._driver = ctypes.WinDLL("nvcuda.dll")
            self._nvrtc = ctypes.WinDLL(str(NVRTC_DLL))
        except OSError as error:
            message = f"CUDA runtime DLL unavailable: {error}"
            raise AcceleratorUnavailableError(message) from error
        self._bind_driver()
        self._bind_nvrtc()
        self._closed = False
        self._device = self._open_device(device_id)
        self._context = self._create_context(self._device)
        self.device_info = self._read_device_info(self._device)
        self.host_memory = CudaHostMemoryRegistry(
            self._ensure_open,
            self._cu_mem_host_register,
            self._cu_mem_host_unregister,
        )
        self.resources = CudaResourceProbe(
            self._cu_mem_get_info,
            self.device_info,
        )

    def allocate(self, byte_count: int) -> int:
        """Allocate device memory.

        Returns:
            Raw CUDA device pointer encoded as an unsigned host integer.

        """
        self._ensure_open()
        pointer = ctypes.c_uint64()
        _check_execution(
            self._cu_mem_alloc(ctypes.byref(pointer), byte_count),
            "cuMemAlloc_v2",
        )
        return pointer.value

    def close(self) -> None:
        """Release registered host buffers and destroy the CUDA context."""
        if self._closed:
            return
        registration_failure = self.host_memory.release_failure()
        self._closed = True
        context_failure: AcceleratorExecutionError | None = None
        try:
            _check_execution(
                self._cu_ctx_destroy(self._context),
                "cuCtxDestroy_v2",
            )
        except AcceleratorExecutionError as error:
            context_failure = error
        self.host_memory.clear()
        if registration_failure is not None:
            raise registration_failure
        if context_failure is not None:
            raise context_failure

    def _compile_ptx(self, source: str, arch: str) -> bytes:
        """Compile reviewed CUDA C++ source to PTX with pinned NVRTC.

        Returns:
            Null-terminated PTX bytes accepted by the CUDA Driver API.

        Raises:
            AcceleratorExecutionError: If NVRTC compilation fails.

        """
        self._ensure_open()
        program = ctypes.c_void_p()
        _check_nvrtc(
            self._nvrtc_create_program(
                ctypes.byref(program),
                source.encode("ascii"),
                b"malbolge-exact-primitives.cu",
                0,
                None,
                None,
            ),
            "nvrtcCreateProgram",
        )
        try:
            options = (
                f"--gpu-architecture=compute_{arch.removeprefix("sm_")}".encode(),
                b"--std=c++17",
                b"--fmad=false",
            )
            option_array = (ctypes.c_char_p * len(options))(*options)
            compile_status = self._nvrtc_compile_program(
                program,
                len(options),
                option_array,
            )
            if compile_status != NVRTC_SUCCESS:
                log = self._program_log(program)
                message = f"NVRTC compilation failed ({compile_status}): {log}"
                raise AcceleratorExecutionError(message)
            size = ctypes.c_size_t()
            _check_nvrtc(
                self._nvrtc_get_ptx_size(program, ctypes.byref(size)),
                "nvrtcGetPTXSize",
            )
            ptx = ctypes.create_string_buffer(size.value)
            _check_nvrtc(self._nvrtc_get_ptx(program, ptx), "nvrtcGetPTX")
            return ptx.raw
        finally:
            _check_nvrtc(
                self._nvrtc_destroy_program(ctypes.byref(program)),
                "nvrtcDestroyProgram",
            )

    def compile_module(self, source: str, arch: str) -> ctypes.c_void_p:
        """Compile reviewed CUDA source and load its PTX module.

        Returns:
            Opaque CUDA module handle ready for kernel lookup.

        """
        ptx = self._compile_ptx(source, arch)
        return self._load_module(ptx)

    def copy_from_device(self, host: HostWords, device_pointer: int) -> None:
        """Copy one exact host buffer from device memory synchronously."""
        self._ensure_open()
        _check_execution(
            self._cu_memcpy_dtoh(
                host,
                ctypes.c_uint64(device_pointer),
                ctypes.sizeof(host),
            ),
            "cuMemcpyDtoH_v2",
        )

    def copy_to_device(
        self,
        device_pointer: int,
        host: HostWords,
        *,
        repeat_count: int = 1,
    ) -> None:
        """Copy one host buffer and optionally replicate it contiguously.

        Raises:
            AcceleratorExecutionError: If the count is invalid or CUDA fails.

        """
        self._ensure_open()
        if repeat_count < 1:
            message = (
                "CUDA host-to-device repeat count must be positive: "
                f"{repeat_count}"
            )
            raise AcceleratorExecutionError(message)
        byte_count = ctypes.sizeof(host)
        _check_execution(
            self._cu_memcpy_htod(
                ctypes.c_uint64(device_pointer),
                host,
                byte_count,
            ),
            "cuMemcpyHtoD_v2",
        )
        for index in range(1, repeat_count):
            _check_execution(
                self._cu_memcpy_dtod(
                    ctypes.c_uint64(device_pointer + (index * byte_count)),
                    ctypes.c_uint64(device_pointer),
                    byte_count,
                ),
                "cuMemcpyDtoD_v2",
            )

    def free(self, device_pointer: int) -> None:
        """Release one device allocation."""
        self._ensure_open()
        _check_execution(
            self._cu_mem_free(ctypes.c_uint64(device_pointer)),
            "cuMemFree_v2",
        )

    def get_kernel(
        self, module: ctypes.c_void_p, name: bytes
    ) -> ctypes.c_void_p:
        """Resolve one exported kernel from a loaded PTX module.

        Returns:
            Opaque CUDA function handle.

        """
        self._ensure_open()
        function = ctypes.c_void_p()
        _check_execution(
            self._cu_module_get_function(
                ctypes.byref(function),
                module,
                name,
            ),
            "cuModuleGetFunction",
        )
        return function

    def launch(
        self,
        kernel: ctypes.c_void_p,
        device_pointers: tuple[int, ...],
        count: int,
    ) -> None:
        """Launch one homogeneous one-dimensional kernel and synchronize."""
        self._ensure_open()
        device_arguments = tuple(
            ctypes.c_uint64(pointer) for pointer in device_pointers
        )
        count_argument = ctypes.c_uint32(count)
        owners: tuple[object, ...] = (*device_arguments, count_argument)
        params_type = ctypes.c_void_p * len(owners)
        params = params_type(*(ctypes.addressof(owner) for owner in owners))
        blocks = (count + THREADS_PER_BLOCK - 1) // THREADS_PER_BLOCK
        _check_execution(
            self._cu_launch_kernel(
                kernel,
                blocks,
                1,
                1,
                THREADS_PER_BLOCK,
                1,
                1,
                0,
                None,
                params,
                None,
            ),
            "cuLaunchKernel",
        )
        _ = owners
        _check_execution(self._cu_ctx_synchronize(), "cuCtxSynchronize")

    def _load_module(self, ptx: bytes) -> ctypes.c_void_p:
        """Load one PTX image into the owned context.

        Returns:
            Opaque CUDA module handle.

        """
        self._ensure_open()
        image = ctypes.create_string_buffer(ptx)
        module = ctypes.c_void_p()
        _check_execution(
            self._cu_module_load_data(
                ctypes.byref(module),
                ctypes.cast(image, ctypes.c_void_p),
            ),
            "cuModuleLoadData",
        )
        return module

    def unload_module(self, module: ctypes.c_void_p) -> None:
        """Unload one CUDA module from the owned context."""
        self._ensure_open()
        _check_execution(self._cu_module_unload(module), "cuModuleUnload")

    def _bind_driver(self) -> None:
        context = _bind_driver_context(self._driver)
        memory = _bind_driver_memory(self._driver)
        module = _bind_driver_module(self._driver)
        (
            self._cu_init,
            self._cu_device_get,
            self._cu_device_get_attribute,
            self._cu_ctx_create,
            self._cu_ctx_destroy,
            self._cu_ctx_synchronize,
            self._cu_device_get_name,
            self._cu_device_compute_capability,
        ) = context
        (
            self._cu_mem_alloc,
            self._cu_mem_get_info,
            self._cu_mem_free,
            self._cu_mem_host_register,
            self._cu_mem_host_unregister,
            self._cu_memcpy_htod,
            self._cu_memcpy_dtoh,
            self._cu_memcpy_dtod,
        ) = memory
        (
            self._cu_module_load_data,
            self._cu_module_unload,
            self._cu_module_get_function,
            self._cu_launch_kernel,
        ) = module

    def _bind_nvrtc(self) -> None:
        (
            self._nvrtc_create_program,
            self._nvrtc_compile_program,
            self._nvrtc_get_ptx_size,
            self._nvrtc_get_ptx,
            self._nvrtc_get_log_size,
            self._nvrtc_get_log,
            self._nvrtc_destroy_program,
        ) = _bind_nvrtc(self._nvrtc)

    def _create_context(self, device: int) -> ctypes.c_void_p:
        context = ctypes.c_void_p()
        _check_available(
            self._cu_ctx_create(ctypes.byref(context), 0, device),
            "cuCtxCreate_v2",
        )
        return context

    def _ensure_open(self) -> None:
        if self._closed:
            message = "CUDA runtime is closed"
            raise AcceleratorExecutionError(message)

    def _open_device(self, device_id: int) -> int:
        _check_available(self._cu_init(0), "cuInit")
        device = ctypes.c_int()
        _check_available(
            self._cu_device_get(ctypes.byref(device), device_id),
            "cuDeviceGet",
        )
        return device.value

    def _read_device_info(self, device: int) -> CudaDeviceInfo:
        name = ctypes.create_string_buffer(256)
        _check_available(
            self._cu_device_get_name(name, len(name), device),
            "cuDeviceGetName",
        )
        major = ctypes.c_int()
        minor = ctypes.c_int()
        _check_available(
            self._cu_device_compute_capability(
                ctypes.byref(major),
                ctypes.byref(minor),
                device,
            ),
            "cuDeviceComputeCapability",
        )
        device_name = bytes(name).split(b"\x00", maxsplit=1)[0].decode("utf-8")
        return CudaDeviceInfo(
            arch=f"sm_{major.value}{minor.value}",
            max_threads_per_block=self._read_device_attribute(
                device, CUDA_ATTRIBUTE_MAX_THREADS_PER_BLOCK
            ),
            multiprocessor_count=self._read_device_attribute(
                device, CUDA_ATTRIBUTE_MULTIPROCESSOR_COUNT
            ),
            name=device_name,
        )

    def _read_device_attribute(self, device: int, attribute: int) -> int:
        value = ctypes.c_int()
        _check_available(
            self._cu_device_get_attribute(
                ctypes.byref(value),
                attribute,
                device,
            ),
            "cuDeviceGetAttribute",
        )
        return value.value

    def _program_log(self, program: ctypes.c_void_p) -> str:
        size = ctypes.c_size_t()
        _check_nvrtc(
            self._nvrtc_get_log_size(program, ctypes.byref(size)),
            "nvrtcGetProgramLogSize",
        )
        log = ctypes.create_string_buffer(size.value)
        _check_nvrtc(self._nvrtc_get_log(program, log), "nvrtcGetProgramLog")
        return (
            bytes(log)
            .split(b"\x00", maxsplit=1)[0]
            .decode("utf-8", errors="replace")
        )


def _add_cuda_dll_directory() -> object:
    try:
        return os.add_dll_directory(str(CUDA_TOOLKIT / "bin" / "x64"))
    except OSError as error:
        message = f"CUDA DLL directory unavailable: {error}"
        raise AcceleratorUnavailableError(message) from error


def _bind_driver_context(dll: ctypes.WinDLL) -> tuple[_CudaFn, ...]:
    raw_init = dll.cuInit
    raw_init.argtypes = [ctypes.c_uint]
    raw_init.restype = ctypes.c_int
    raw_device_get = dll.cuDeviceGet
    raw_device_get.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    raw_device_get.restype = ctypes.c_int
    raw_attribute = dll.cuDeviceGetAttribute
    raw_attribute.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
        ctypes.c_int,
    ]
    raw_attribute.restype = ctypes.c_int
    raw_ctx_create = dll.cuCtxCreate_v2
    raw_ctx_create.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_uint,
        ctypes.c_int,
    ]
    raw_ctx_create.restype = ctypes.c_int
    raw_ctx_destroy = dll.cuCtxDestroy_v2
    raw_ctx_destroy.argtypes = [ctypes.c_void_p]
    raw_ctx_destroy.restype = ctypes.c_int
    raw_sync = dll.cuCtxSynchronize
    raw_sync.argtypes = []
    raw_sync.restype = ctypes.c_int
    raw_name = dll.cuDeviceGetName
    raw_name.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    raw_name.restype = ctypes.c_int
    raw_capability = dll.cuDeviceComputeCapability
    raw_capability.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_int,
    ]
    raw_capability.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (
            raw_init,
            raw_device_get,
            raw_attribute,
            raw_ctx_create,
            raw_ctx_destroy,
            raw_sync,
            raw_name,
            raw_capability,
        )
    )


def _bind_driver_memory(dll: ctypes.WinDLL) -> tuple[_CudaFn, ...]:
    raw_alloc = dll.cuMemAlloc_v2
    raw_alloc.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]
    raw_alloc.restype = ctypes.c_int
    raw_info = dll.cuMemGetInfo_v2
    raw_info.argtypes = [
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    raw_info.restype = ctypes.c_int
    raw_free = dll.cuMemFree_v2
    raw_free.argtypes = [ctypes.c_uint64]
    raw_free.restype = ctypes.c_int
    raw_host_register = dll.cuMemHostRegister_v2
    raw_host_register.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint,
    ]
    raw_host_register.restype = ctypes.c_int
    raw_host_unregister = dll.cuMemHostUnregister
    raw_host_unregister.argtypes = [ctypes.c_void_p]
    raw_host_unregister.restype = ctypes.c_int
    raw_htod = dll.cuMemcpyHtoD_v2
    raw_htod.argtypes = [ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
    raw_htod.restype = ctypes.c_int
    raw_dtoh = dll.cuMemcpyDtoH_v2
    raw_dtoh.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t]
    raw_dtoh.restype = ctypes.c_int
    raw_dtod = dll.cuMemcpyDtoD_v2
    raw_dtod.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_size_t]
    raw_dtod.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (
            raw_alloc,
            raw_info,
            raw_free,
            raw_host_register,
            raw_host_unregister,
            raw_htod,
            raw_dtoh,
            raw_dtod,
        )
    )


def _bind_driver_module(dll: ctypes.WinDLL) -> tuple[_CudaFn, ...]:
    raw_load = dll.cuModuleLoadData
    raw_load.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    raw_load.restype = ctypes.c_int
    raw_unload = dll.cuModuleUnload
    raw_unload.argtypes = [ctypes.c_void_p]
    raw_unload.restype = ctypes.c_int
    raw_function = dll.cuModuleGetFunction
    raw_function.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
        ctypes.c_char_p,
    ]
    raw_function.restype = ctypes.c_int
    raw_launch = dll.cuLaunchKernel
    raw_launch.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    raw_launch.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (raw_load, raw_unload, raw_function, raw_launch)
    )


def _bind_nvrtc(dll: ctypes.WinDLL) -> tuple[_CudaFn, ...]:
    raw_create = dll.nvrtcCreateProgram
    raw_create.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_char_p),
    ]
    raw_create.restype = ctypes.c_int
    raw_compile = dll.nvrtcCompileProgram
    raw_compile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_char_p),
    ]
    raw_compile.restype = ctypes.c_int
    raw_ptx_size = dll.nvrtcGetPTXSize
    raw_ptx_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    raw_ptx_size.restype = ctypes.c_int
    raw_ptx = dll.nvrtcGetPTX
    raw_ptx.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    raw_ptx.restype = ctypes.c_int
    raw_log_size = dll.nvrtcGetProgramLogSize
    raw_log_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    raw_log_size.restype = ctypes.c_int
    raw_log = dll.nvrtcGetProgramLog
    raw_log.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    raw_log.restype = ctypes.c_int
    raw_destroy = dll.nvrtcDestroyProgram
    raw_destroy.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    raw_destroy.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (
            raw_create,
            raw_compile,
            raw_ptx_size,
            raw_ptx,
            raw_log_size,
            raw_log,
            raw_destroy,
        )
    )


def _check_available(result: int, operation: str) -> None:
    if result != CUDA_SUCCESS:
        message = f"{operation} unavailable: CUDA error {result}"
        raise AcceleratorUnavailableError(message)


def _check_execution(result: int, operation: str) -> None:
    if result != CUDA_SUCCESS:
        message = f"{operation} failed: CUDA error {result}"
        raise AcceleratorExecutionError(message)


def _check_nvrtc(result: int, operation: str) -> None:
    if result != NVRTC_SUCCESS:
        message = f"{operation} failed: NVRTC error {result}"
        raise AcceleratorExecutionError(message)


def _configure_toolkit_environment() -> None:
    if not CUDA_TOOLKIT.is_dir() or not NVRTC_DLL.is_file():
        message = f"pinned CUDA toolkit missing: {CUDA_TOOLKIT}"
        raise AcceleratorUnavailableError(message)
    os.environ["CUDA_PATH"] = str(CUDA_TOOLKIT)
    bin_path = CUDA_TOOLKIT / "bin"
    x64_path = bin_path / "x64"
    os.environ["PATH"] = os.pathsep.join((
        str(bin_path),
        str(x64_path),
        os.environ.get("PATH", ""),
    ))
