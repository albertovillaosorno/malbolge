# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
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
#   - Pinned CUDA, optional NVML, and host/Python identity boundary.
# - Description:
#   - Owns exact CUDA execution and optional environment identity.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Pinned CUDA plus optional NVML and host/Python identity boundary."""

from __future__ import annotations

from collections.abc import Callable
import ctypes
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import platform
from typing import Final
from typing import TYPE_CHECKING
from typing import cast
from typing import final

from accelerator.cuda.toolchain import CudaToolchainSelectionError
from accelerator.cuda.toolchain import select_cuda_toolchain
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.resource_budget import AcceleratorResources

if TYPE_CHECKING:
    from accelerator.cuda.toolchain import CudaToolchainSelection


def _repository_root(start: Path) -> Path:
    """Resolve the source checkout that owns the CUDA adapter.

    Returns:
        Nearest ancestor carrying the canonical repository markers.

    Raises:
        RuntimeError: No ancestor carries every required marker.

    """
    resolved = start.resolve()
    directory = resolved.parent if resolved.is_file() else resolved
    markers = (
        Path("Cargo.toml"),
        Path("malbolge.json"),
        Path(".jig/jig.toml"),
    )
    for candidate in (directory, *directory.parents):
        if all((candidate / marker).is_file() for marker in markers):
            return candidate
    message = f"CUDA adapter repository root not found from: {start}"
    raise RuntimeError(message)


ROOT: Final = _repository_root(Path(__file__))
NVML_DLL: Final = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "nvml.dll"
)
CUDA_TOOLCHAIN_MANIFEST: Final = (
    ROOT
    / "src/optimization/accelerator/adapter-outbound/accelerator/cuda"
    / "toolchain.json"
)
CUDA_RUNTIME_IDENTITY_ID: Final = "cuda-runtime-toolchain-identity-v1"
CUDA_HOST_RUNTIME_IDENTITY_ID: Final = "cuda-host-runtime-identity-v1"
_HEX_DIGITS: Final = frozenset("0123456789abcdef")
_SHA256_HEX_LENGTH: Final = 64
CUDA_SUCCESS: Final = 0
NVRTC_SUCCESS: Final = 0
NVML_SUCCESS: Final = 0
NVML_VERSION_BUFFER_BYTES: Final = 96
_DISPLAY_DRIVER_MIN_COMPONENTS: Final = 2
_WINDOWS_SYSTEM: Final = "Windows"
_WINDOWS_LOADER_KIND: Final = "windll"
THREADS_PER_BLOCK: Final = 256
CUDA_ATTRIBUTE_MAX_THREADS_PER_BLOCK: Final = 1
CUDA_ATTRIBUTE_MULTIPROCESSOR_COUNT: Final = 16
CUDA_STREAM_DEFAULT: Final = 0
CUDA_STREAM_NON_BLOCKING: Final = 1
CUDA_ORDERED_DTOH_STREAM_ID: Final = "cuda-ordered-registered-dtoh-stream-v1"
CUDA_KERNEL_LAUNCH_ID: Final = "cuda-default-stream-kernel-launch-v1"
CUDA_INDEPENDENT_KERNEL_LAUNCH_ID: Final = (
    "cuda-independent-stream-kernel-launch-v1"
)
CUDA_INDEPENDENT_KERNEL_TIMELINE_ID: Final = (
    "cuda-independent-stream-kernel-timeline-v1"
)
CUDA_INDEPENDENT_TICKET_TRANSFER_ID: Final = (
    "cuda-independent-stream-ticket-transfer-v1"
)
CUDA_INDEPENDENT_TICKET_TRANSFER_TIMELINE_ID: Final = (
    "cuda-independent-stream-ticket-transfer-timeline-v1"
)
CUDA_EVENT_DEFAULT: Final = 0

_CudaFn = Callable[..., int]
type _NvmlBindings = tuple[_CudaFn, _CudaFn, _CudaFn]
type _NvmlLoader = Callable[[Path], _NvmlBindings | None]
type _LibraryLoader = Callable[[str], ctypes.CDLL]
type _DllDirectoryOpener = Callable[[Path], object]
type HostWords = ctypes.Array[ctypes.c_uint32]


@dataclass(frozen=True, slots=True)
class _LoadedCudaLibraries:
    """Loaded Driver/NVRTC handles plus optional Windows search lifetime."""

    driver: ctypes.CDLL
    nvrtc: ctypes.CDLL
    search_directory: object | None


@dataclass(frozen=True, slots=True)
class CudaHostRuntimeIdentity:
    """Measured host OS and Python runtime identity."""

    host_edition: str | None
    host_machine: str
    host_release: str
    host_system: str
    host_version: str
    identity_id: str
    python_implementation: str
    python_version: str

    def validated(self) -> CudaHostRuntimeIdentity:
        """Validate one host/Python identity.

        Returns:
            The unchanged identity after fail-closed validation.

        Raises:
            AcceleratorUnavailableError: If any identity field is invalid.

        """
        if self.identity_id != CUDA_HOST_RUNTIME_IDENTITY_ID:
            message = "CUDA host runtime identity protocol mismatched"
            raise AcceleratorUnavailableError(message)
        required = (
            self.host_machine,
            self.host_release,
            self.host_system,
            self.host_version,
            self.python_implementation,
            self.python_version,
        )
        if any(not value or value.strip() != value for value in required):
            message = "CUDA host runtime identity contains invalid text"
            raise AcceleratorUnavailableError(message)
        edition = self.host_edition
        if edition is not None and (not edition or edition.strip() != edition):
            message = "CUDA host edition is invalid"
            raise AcceleratorUnavailableError(message)
        return self


@dataclass(frozen=True, slots=True)
class CudaRuntimeEnvironment:
    """Optional environment identities composed into one CUDA identity."""

    display_driver_version: str | None = None
    host_runtime_identity: CudaHostRuntimeIdentity | None = None


@dataclass(frozen=True, slots=True)
class CudaRuntimeIdentity:
    """Measured CUDA, toolchain, display-driver, and host identity."""

    driver_api_version: int
    identity_id: str
    nvrtc_major: int
    nvrtc_minor: int
    toolchain_manifest_sha256: str
    display_driver_version: str | None = None
    host_runtime_identity: CudaHostRuntimeIdentity | None = None

    def validated(self) -> CudaRuntimeIdentity:
        """Validate runtime/toolchain identity shape.

        Returns:
            The unchanged identity after fail-closed validation.

        """
        _validate_cuda_runtime_protocol(self)
        _validate_cuda_runtime_versions(self)
        _validate_display_driver_version(self.display_driver_version)
        _validate_host_runtime_identity(self.host_runtime_identity)
        _validate_sha256(self.toolchain_manifest_sha256)
        return self


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
        self._in_flight: dict[int, int] = {}
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
        if self._in_flight.get(address, 0) != 0:
            message = "CUDA host buffer has asynchronous transfers in flight"
            raise AcceleratorExecutionError(message)
        _check_execution(
            self._unregister_fn(ctypes.c_void_p(address)),
            "cuMemHostUnregister",
        )
        del self._registrations[address]

    def acquire_for_async(self, host: HostWords) -> int:
        """Retain one registered host buffer through asynchronous completion.

        Returns:
            Registered address whose in-flight count was incremented.

        Raises:
            AcceleratorExecutionError: If the exact buffer is not registered.

        """
        self._ensure_open()
        address = ctypes.addressof(host)
        registered = self._registrations.get(address)
        if registered is None or ctypes.sizeof(registered) != ctypes.sizeof(
            host
        ):
            message = "CUDA asynchronous copy requires a registered host buffer"
            raise AcceleratorExecutionError(message)
        self._in_flight[address] = self._in_flight.get(address, 0) + 1
        return address

    def release_async(self, addresses: tuple[int, ...]) -> None:
        """Release exact asynchronous leases after stream synchronization.

        Raises:
            AcceleratorExecutionError: If an internal lease is missing.

        """
        for address in addresses:
            count = self._in_flight.get(address, 0)
            if count <= 0:
                message = "CUDA asynchronous host lease is not owned"
                raise AcceleratorExecutionError(message)
            if count == 1:
                del self._in_flight[address]
            else:
                self._in_flight[address] = count - 1

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
        self._in_flight.clear()
        self._registrations.clear()


def cuda_ordered_dtoh_stream_id() -> str:
    """Return the ordered registered D-to-H stream identity.

    Returns:
        Stable identity for contract and evidence provenance.

    """
    return CUDA_ORDERED_DTOH_STREAM_ID


@dataclass(frozen=True, slots=True)
class CudaOrderedTransferBatch:
    """One synchronized batch of ordered D-to-H submissions."""

    bytes: int
    copies: int


@dataclass(frozen=True, slots=True)
class _CudaOrderedStreamBinding:
    copy_fn: _CudaFn
    destroy_fn: _CudaFn
    ensure_open: Callable[[], None]
    forget: Callable[[CudaOrderedDtoHStream], None]
    handle: ctypes.c_void_p
    host_memory: CudaHostMemoryRegistry
    synchronize_fn: _CudaFn


@final
class CudaOrderedDtoHStream:
    """One ordered CUDA stream retaining registered host buffers until wait."""

    def __init__(self, binding: _CudaOrderedStreamBinding) -> None:
        """Adopt one ordered CUDA stream with default-stream dependencies."""
        self._binding = binding
        self._closed = False
        self._pending_addresses: list[int] = []
        self._pending_bytes = 0

    @property
    def pending_bytes(self) -> int:
        """Bytes whose host lifetime remains bound to stream completion."""
        return self._pending_bytes

    @property
    def pending_copies(self) -> int:
        """Ordered copies not yet released by ``wait`` or ``close``."""
        return len(self._pending_addresses)

    def close(self) -> None:
        """Synchronize pending work and destroy the CUDA stream exactly once."""
        if self._closed:
            return
        wait_failure = self._wait_failure()
        destroy_failure = self._destroy_failure()
        self._closed = True
        self._binding.forget(self)
        _raise_first_failure(wait_failure, destroy_failure)

    def _destroy_failure(self) -> AcceleratorExecutionError | None:
        try:
            _check_execution(
                self._binding.destroy_fn(self._binding.handle),
                "cuStreamDestroy_v2",
            )
        except AcceleratorExecutionError as error:
            return error
        return None

    def _wait_failure(self) -> AcceleratorExecutionError | None:
        if not self._pending_addresses:
            return None
        try:
            _ = self.wait()
        except AcceleratorExecutionError as error:
            return error
        return None

    def submit_copy_from_device(
        self,
        host: HostWords,
        device_pointer: int,
    ) -> None:
        """Enqueue one copy after acquiring the registered host lifetime.

        Raises:
            AcceleratorExecutionError: If state, registration, or CUDA
                rejects the submission.

        """
        self._ensure_usable()
        if type(device_pointer) is not int or device_pointer <= 0:
            message = (
                "CUDA asynchronous copy requires a positive device pointer"
            )
            raise AcceleratorExecutionError(message)
        address = self._binding.host_memory.acquire_for_async(host)
        byte_count = ctypes.sizeof(host)
        try:
            _check_execution(
                self._binding.copy_fn(
                    host,
                    ctypes.c_uint64(device_pointer),
                    byte_count,
                    self._binding.handle,
                ),
                "cuMemcpyDtoHAsync_v2",
            )
        except AcceleratorExecutionError:
            self._binding.host_memory.release_async((address,))
            raise
        self._pending_addresses.append(address)
        self._pending_bytes += byte_count

    def wait(self) -> CudaOrderedTransferBatch:
        """Synchronize every ordered copy and release all host lifetimes.

        Returns:
            Completed copy and byte counts for the exact pending batch.

        Raises:
            AcceleratorExecutionError: If no work is pending or CUDA fails.

        """
        self._ensure_usable()
        if not self._pending_addresses:
            message = "CUDA ordered transfer stream has no pending copies"
            raise AcceleratorExecutionError(message)
        addresses = tuple(self._pending_addresses)
        summary = CudaOrderedTransferBatch(
            bytes=self._pending_bytes,
            copies=len(addresses),
        )
        failure: AcceleratorExecutionError | None = None
        try:
            _check_execution(
                self._binding.synchronize_fn(self._binding.handle),
                "cuStreamSynchronize",
            )
        except AcceleratorExecutionError as error:
            failure = error
        finally:
            self._binding.host_memory.release_async(addresses)
            self._pending_addresses.clear()
            self._pending_bytes = 0
        if failure is not None:
            raise failure
        return summary

    def _ensure_usable(self) -> None:
        self._binding.ensure_open()
        if self._closed:
            message = "CUDA ordered transfer stream is closed"
            raise AcceleratorExecutionError(message)


@dataclass(frozen=True, slots=True)
class _CudaOrderedFactoryBinding:
    copy_fn: _CudaFn
    create_fn: _CudaFn
    destroy_fn: _CudaFn
    ensure_open: Callable[[], None]
    host_memory: CudaHostMemoryRegistry
    synchronize_fn: _CudaFn


@final
class CudaOrderedDtoHStreamFactory:
    """Own every ordered D-to-H stream created for one CUDA context."""

    def __init__(self, binding: _CudaOrderedFactoryBinding) -> None:
        """Bind one live runtime's reviewed stream functions."""
        self._binding = binding
        self._streams: list[CudaOrderedDtoHStream] = []

    def create(self) -> CudaOrderedDtoHStream:
        """Create one ordered D-to-H stream with default dependencies.

        Returns:
            Stream that accepts only host buffers registered by this runtime.

        """
        self._binding.ensure_open()
        handle = ctypes.c_void_p()
        _check_execution(
            self._binding.create_fn(
                ctypes.byref(handle),
                CUDA_STREAM_DEFAULT,
            ),
            "cuStreamCreate",
        )
        stream = CudaOrderedDtoHStream(
            _CudaOrderedStreamBinding(
                copy_fn=self._binding.copy_fn,
                destroy_fn=self._binding.destroy_fn,
                ensure_open=self._binding.ensure_open,
                forget=self._forget,
                handle=handle,
                host_memory=self._binding.host_memory,
                synchronize_fn=self._binding.synchronize_fn,
            )
        )
        self._streams.append(stream)
        return stream

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Close every owned stream before context and host-memory teardown.

        Returns:
            First synchronization/destruction failure, or ``None``.

        """
        return _release_ordered_dtoh_streams(self._streams)

    def _forget(self, stream: CudaOrderedDtoHStream) -> None:
        try:
            self._streams.remove(stream)
        except ValueError:
            return


def cuda_kernel_launch_id() -> str:
    """Return the explicit default-stream kernel-launch identity.

    Returns:
        Stable identity for contract and evidence provenance.

    """
    return CUDA_KERNEL_LAUNCH_ID


def cuda_independent_kernel_launch_id() -> str:
    """Return the isolated one-stream-per-launch identity.

    Returns:
        Stable identity for independent CUDA ticket provenance.

    """
    return CUDA_INDEPENDENT_KERNEL_LAUNCH_ID


def cuda_independent_kernel_timeline_id() -> str:
    """Return the CUDA-event independent-stream timeline identity.

    Returns:
        Stable identity for diagnostic launch interval provenance.

    """
    return CUDA_INDEPENDENT_KERNEL_TIMELINE_ID


def cuda_independent_ticket_transfer_id() -> str:
    """Return the same-stream asynchronous ticket transfer identity.

    Returns:
        Stable identity for registered H-to-D/kernel/D-to-H provenance.

    """
    return CUDA_INDEPENDENT_TICKET_TRANSFER_ID


def cuda_independent_ticket_transfer_timeline_id() -> str:
    """Return the CUDA-event ticket transfer phase timeline identity.

    Returns:
        Stable identity for H-to-D/kernel/D-to-H phase attribution.

    """
    return CUDA_INDEPENDENT_TICKET_TRANSFER_TIMELINE_ID


@dataclass(frozen=True, slots=True)
class CudaHostToDeviceTransfer:
    """One registered host buffer queued for stream-local H-to-D copy."""

    device_pointer: int
    host: HostWords


@dataclass(frozen=True, slots=True)
class CudaDeviceToHostTransfer:
    """One registered host buffer queued for stream-local D-to-H copy."""

    device_pointer: int
    host: HostWords


@dataclass(frozen=True, slots=True)
class CudaIndependentTransferSubmission:
    """Exact uploads, kernel, and downloads for one isolated CUDA stream."""

    count: int
    device_pointers: tuple[int, ...]
    downloads: tuple[CudaDeviceToHostTransfer, ...]
    kernel: ctypes.c_void_p
    uploads: tuple[CudaHostToDeviceTransfer, ...]


@dataclass(frozen=True, slots=True)
class _CudaKernelLaunchBinding:
    ensure_open: Callable[[], None]
    forget: Callable[[CudaKernelLaunch], None]
    synchronize_fn: _CudaFn


@final
class CudaKernelLaunch:
    """One default-stream launch retaining parameter owners until completion."""

    def __init__(
        self,
        binding: _CudaKernelLaunchBinding,
        owners: tuple[object, ...],
    ) -> None:
        """Adopt one submitted launch and its exact parameter lifetimes."""
        self._binding = binding
        self._closed = False
        self._completed = False
        self._owners = owners

    @property
    def completed(self) -> bool:
        """Whether context synchronization completed this launch."""
        return self._completed

    def close(self) -> None:
        """Synchronize pending work and close the launch exactly once."""
        if self._closed:
            return
        if not self._completed:
            self.wait()
        self._closed = True

    def wait(self) -> None:
        """Synchronize the CUDA context and release parameter lifetimes.

        Raises:
            AcceleratorExecutionError: If closed or synchronization fails.

        """
        self._binding.ensure_open()
        if self._closed:
            message = "CUDA kernel launch is closed"
            raise AcceleratorExecutionError(message)
        if self._completed:
            return
        _check_execution(self._binding.synchronize_fn(), "cuCtxSynchronize")
        self._completed = True
        self._owners = ()
        self._binding.forget(self)


@dataclass(frozen=True, slots=True)
class _CudaKernelLaunchArguments:
    blocks: int
    owners: tuple[object, ...]
    params: ctypes.Array[ctypes.c_void_p]


@dataclass(frozen=True, slots=True)
class _CudaKernelLaunchFactoryBinding:
    ensure_open: Callable[[], None]
    launch_fn: _CudaFn
    synchronize_fn: _CudaFn


@final
class CudaKernelLaunchFactory:
    """Own submitted default-stream launches until synchronization."""

    def __init__(self, binding: _CudaKernelLaunchFactoryBinding) -> None:
        """Bind one live context's launch and synchronization functions."""
        self._binding = binding
        self._launches: list[CudaKernelLaunch] = []

    def submit(
        self,
        kernel: ctypes.c_void_p,
        device_pointers: tuple[int, ...],
        count: int,
    ) -> CudaKernelLaunch:
        """Submit one launch without synchronizing the owned context.

        Returns:
            Runtime-owned launch retaining every kernel parameter owner.

        """
        self._binding.ensure_open()
        arguments = _kernel_launch_arguments(device_pointers, count)
        _check_execution(
            self._binding.launch_fn(
                kernel,
                arguments.blocks,
                1,
                1,
                THREADS_PER_BLOCK,
                1,
                1,
                0,
                None,
                arguments.params,
                None,
            ),
            "cuLaunchKernel",
        )
        launch = CudaKernelLaunch(
            _CudaKernelLaunchBinding(
                ensure_open=self._binding.ensure_open,
                forget=self._forget,
                synchronize_fn=self._binding.synchronize_fn,
            ),
            (*arguments.owners, arguments.params),
        )
        self._launches.append(launch)
        return launch

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Close every launch before stream, module, or context teardown.

        Returns:
            First synchronization failure, or ``None`` after complete release.

        """
        return _release_kernel_launches(self._launches)

    def _forget(self, launch: CudaKernelLaunch) -> None:
        try:
            self._launches.remove(launch)
        except ValueError:
            return


@dataclass(frozen=True, slots=True)
class _CudaIndependentKernelLaunchBinding:
    destroy_fn: _CudaFn
    ensure_open: Callable[[], None]
    forget: Callable[[CudaIndependentKernelLaunch], None]
    handle: ctypes.c_void_p
    host_memory: CudaHostMemoryRegistry
    kernel_timeline: _CudaIndependentKernelTimelineLaunch | None
    synchronize_fn: _CudaFn
    transfer_timeline: _CudaIndependentTicketTransferTimelineLaunch | None


@final
class CudaIndependentKernelLaunch:
    """One nonblocking CUDA stream retaining exact launch parameters."""

    def __init__(
        self,
        binding: _CudaIndependentKernelLaunchBinding,
        owners: tuple[object, ...],
        pending_addresses: tuple[int, ...],
    ) -> None:
        """Adopt one submitted stream, kernel, and transfer lifetime."""
        self._binding = binding
        self._closed = False
        self._completed = False
        self._owners = owners
        self._pending_addresses = pending_addresses

    @property
    def completed(self) -> bool:
        """Whether this exact stream has completed its submitted kernel."""
        return self._completed

    def close(self) -> None:
        """Synchronize and destroy this launch stream exactly once."""
        if self._closed:
            return
        wait_failure = self._wait_failure()
        timeline_failure = self._timeline_failure(
            completed=wait_failure is None,
        )
        destroy_failure = self._destroy_failure()
        self._closed = True
        self._owners = ()
        self._binding.forget(self)
        _raise_first_failure(
            wait_failure,
            timeline_failure,
            destroy_failure,
        )

    def _destroy_failure(self) -> AcceleratorExecutionError | None:
        try:
            _check_execution(
                self._binding.destroy_fn(self._binding.handle),
                "cuStreamDestroy_v2",
            )
        except AcceleratorExecutionError as error:
            return error
        return None

    def _timeline_failure(
        self,
        *,
        completed: bool,
    ) -> AcceleratorExecutionError | None:
        failure: AcceleratorExecutionError | None = None
        for timeline in (
            self._binding.kernel_timeline,
            self._binding.transfer_timeline,
        ):
            if timeline is None:
                continue
            try:
                timeline.finish(completed=completed)
            except AcceleratorExecutionError as error:
                if failure is None:
                    failure = error
        return failure

    def _wait_failure(self) -> AcceleratorExecutionError | None:
        if self._completed:
            return None
        try:
            self.wait()
        except AcceleratorExecutionError as error:
            return error
        return None

    def wait(self) -> None:
        """Synchronize this stream and release transfer/parameter lifetimes.

        Raises:
            AcceleratorExecutionError: If closed or synchronization fails.

        """
        self._binding.ensure_open()
        if self._closed:
            message = "CUDA independent kernel launch is closed"
            raise AcceleratorExecutionError(message)
        if self._completed:
            return
        synchronize_failure: AcceleratorExecutionError | None = None
        try:
            _check_execution(
                self._binding.synchronize_fn(self._binding.handle),
                "cuStreamSynchronize",
            )
        except AcceleratorExecutionError as error:
            synchronize_failure = error
        lease_failure = self._release_transfer_leases_failure()
        if synchronize_failure is None:
            self._completed = True
            self._owners = ()
        _raise_first_failure(synchronize_failure, lease_failure)

    def _release_transfer_leases_failure(
        self,
    ) -> AcceleratorExecutionError | None:
        addresses = self._pending_addresses
        if not addresses:
            return None
        self._pending_addresses = ()
        try:
            self._binding.host_memory.release_async(addresses)
        except AcceleratorExecutionError as error:
            return error
        return None


@dataclass(frozen=True, slots=True)
class CudaIndependentKernelTimelineSample:
    """One CUDA-event interval observed for an isolated kernel stream."""

    duration_ms: float
    end_ms: float
    start_ms: float
    submission_index: int


@dataclass(frozen=True, slots=True)
class CudaIndependentKernelTimelineFunctions:
    """Reviewed Driver functions required by CUDA-event timelines."""

    create_fn: _CudaFn
    destroy_fn: _CudaFn
    elapsed_fn: _CudaFn
    ensure_open: Callable[[], None]
    record_fn: _CudaFn
    synchronize_fn: _CudaFn


@dataclass(frozen=True, slots=True)
class _CudaIndependentKernelTimelineLaunch:
    end: ctypes.c_void_p
    start: ctypes.c_void_p
    submission_index: int
    timeline: CudaIndependentKernelTimeline

    def finish(self, *, completed: bool) -> None:
        """Publish one completed interval or discard failed event state."""
        self.timeline.finish_launch(self, completed=completed)


@final
class CudaIndependentKernelTimeline:
    """Diagnostic CUDA-event origin and isolated launch interval owner."""

    def __init__(
        self,
        functions: CudaIndependentKernelTimelineFunctions,
        launch_factory: CudaIndependentKernelLaunchFactory,
        forget: Callable[[CudaIndependentKernelTimeline], None],
    ) -> None:
        """Create and synchronize one untimed origin event.

        Raises:
            AcceleratorExecutionError: If event setup fails.

        """
        self._active = 0
        self._closed = False
        self._forget = forget
        self._functions = functions
        self._launch_factory = launch_factory
        self._next_submission_index = 0
        self._origin = _create_cuda_event(functions.create_fn)
        self._samples: list[CudaIndependentKernelTimelineSample] = []
        try:
            _check_execution(
                functions.record_fn(self._origin, None),
                "cuEventRecord",
            )
            _check_execution(
                functions.synchronize_fn(self._origin),
                "cuEventSynchronize",
            )
        except AcceleratorExecutionError:
            _destroy_cuda_event(functions.destroy_fn, self._origin)
            raise

    def __enter__(self) -> CudaIndependentKernelTimeline:
        """Return this diagnostic timeline for scoped use.

        Returns:
            The same live timeline.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Destroy the event origin after every launch closes."""
        self.close()

    def close(self) -> None:
        """Destroy the origin after all profiled launches finish.

        Raises:
            AcceleratorExecutionError:
                If launches remain active or event destruction fails.

        """
        if self._closed:
            return
        self._functions.ensure_open()
        if self._active != 0:
            message = "CUDA independent kernel timeline has active launches"
            raise AcceleratorExecutionError(message)
        _destroy_cuda_event(self._functions.destroy_fn, self._origin)
        self._closed = True
        self._forget(self)

    def samples(self) -> tuple[CudaIndependentKernelTimelineSample, ...]:
        """Return completed samples in submission order.

        Returns:
            Immutable CUDA-event intervals after every launch cleanup.

        Raises:
            AcceleratorExecutionError: If launches remain active.

        """
        self._ensure_usable()
        if self._active != 0:
            message = "CUDA independent kernel timeline has active launches"
            raise AcceleratorExecutionError(message)
        return tuple(
            sorted(self._samples, key=lambda sample: sample.submission_index)
        )

    def submit(
        self,
        kernel: ctypes.c_void_p,
        device_pointers: tuple[int, ...],
        count: int,
    ) -> CudaIndependentKernelLaunch:
        """Submit one isolated launch with CUDA-event start/end markers.

        Returns:
            Runtime-owned launch whose close publishes one interval.

        """
        self._ensure_usable()
        return self._launch_factory.submit_profiled(
            kernel,
            device_pointers,
            count,
            timeline=self,
        )

    def submit_with_transfers(
        self,
        submission: CudaIndependentTransferSubmission,
    ) -> CudaIndependentKernelLaunch:
        """Submit transfers with events delimiting only the exact kernel.

        Returns:
            Runtime-owned launch retaining every registered host lifetime.

        """
        self._ensure_usable()
        return self._launch_factory.submit_profiled_with_transfers(
            submission,
            timeline=self,
        )

    def begin_launch(
        self,
        stream: ctypes.c_void_p,
    ) -> _CudaIndependentKernelTimelineLaunch:
        """Create and record one start/end event pair for a stream.

        Returns:
            Active event resources bound to the next submission index.

        Raises:
            AcceleratorExecutionError: If event setup or recording fails.

        """
        self._ensure_usable()
        start = _create_cuda_event(self._functions.create_fn)
        try:
            end = _create_cuda_event(self._functions.create_fn)
        except AcceleratorExecutionError:
            _destroy_cuda_event(self._functions.destroy_fn, start)
            raise
        try:
            _check_execution(
                self._functions.record_fn(start, stream),
                "cuEventRecord",
            )
        except AcceleratorExecutionError:
            _destroy_cuda_event(self._functions.destroy_fn, end)
            _destroy_cuda_event(self._functions.destroy_fn, start)
            raise
        launch = _CudaIndependentKernelTimelineLaunch(
            end=end,
            start=start,
            submission_index=self._next_submission_index,
            timeline=self,
        )
        self._next_submission_index += 1
        self._active += 1
        return launch

    def record_end(
        self,
        launch: _CudaIndependentKernelTimelineLaunch,
        stream: ctypes.c_void_p,
    ) -> None:
        """Record the exact end event after one kernel launch."""
        _check_execution(
            self._functions.record_fn(launch.end, stream),
            "cuEventRecord",
        )

    def finish_launch(
        self,
        launch: _CudaIndependentKernelTimelineLaunch,
        *,
        completed: bool,
    ) -> None:
        """Publish one completed interval and destroy its event pair."""
        failure: AcceleratorExecutionError | None = None
        if completed:
            try:
                sample = CudaIndependentKernelTimelineSample(
                    duration_ms=_event_elapsed_ms(
                        self._functions.elapsed_fn,
                        launch.start,
                        launch.end,
                    ),
                    end_ms=_event_elapsed_ms(
                        self._functions.elapsed_fn,
                        self._origin,
                        launch.end,
                    ),
                    start_ms=_event_elapsed_ms(
                        self._functions.elapsed_fn,
                        self._origin,
                        launch.start,
                    ),
                    submission_index=launch.submission_index,
                )
                self._samples.append(sample)
            except AcceleratorExecutionError as error:
                failure = error
        end_failure = _destroy_cuda_event_failure(
            self._functions.destroy_fn,
            launch.end,
        )
        start_failure = _destroy_cuda_event_failure(
            self._functions.destroy_fn,
            launch.start,
        )
        self._active -= 1
        _raise_first_failure(failure, end_failure, start_failure)

    def _ensure_usable(self) -> None:
        self._functions.ensure_open()
        if self._closed:
            message = "CUDA independent kernel timeline is closed"
            raise AcceleratorExecutionError(message)


@final
class CudaIndependentKernelTimelineFactory:
    """Own CUDA-event timelines created for one live context."""

    def __init__(
        self,
        functions: CudaIndependentKernelTimelineFunctions,
        launch_factory: CudaIndependentKernelLaunchFactory,
    ) -> None:
        """Bind event functions and the matching isolated launch factory."""
        self._functions = functions
        self._launch_factory = launch_factory
        self._timelines: list[CudaIndependentKernelTimeline] = []

    def create(self) -> CudaIndependentKernelTimeline:
        """Create one synchronized CUDA-event origin timeline.

        Returns:
            Runtime-owned diagnostic timeline for isolated launches.

        """
        timeline = CudaIndependentKernelTimeline(
            self._functions,
            self._launch_factory,
            self._forget,
        )
        self._timelines.append(timeline)
        return timeline

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Close every timeline after independent launches drain.

        Returns:
            First event cleanup failure, or ``None``.

        """
        failure: AcceleratorExecutionError | None = None
        for timeline in tuple(self._timelines):
            try:
                timeline.close()
            except AcceleratorExecutionError as error:
                if failure is None:
                    failure = error
        if failure is None:
            self._timelines.clear()
        return failure

    def _forget(self, timeline: CudaIndependentKernelTimeline) -> None:
        try:
            self._timelines.remove(timeline)
        except ValueError:
            return


@dataclass(frozen=True, slots=True)
class CudaIndependentTicketTransferTimelineSample:
    """CUDA-event phase attribution for one same-stream transfer ticket."""

    download_duration_ms: float
    end_ms: float
    kernel_duration_ms: float
    kernel_end_ms: float
    start_ms: float
    submission_index: int
    total_duration_ms: float
    upload_duration_ms: float
    upload_end_ms: float


@dataclass(frozen=True, slots=True)
class _CudaIndependentTicketTransferTimelineLaunch:
    end: ctypes.c_void_p
    kernel_end: ctypes.c_void_p
    start: ctypes.c_void_p
    submission_index: int
    timeline: CudaIndependentTicketTransferTimeline
    upload_end: ctypes.c_void_p

    def finish(self, *, completed: bool) -> None:
        """Publish completed transfer phases or discard failed event state."""
        # jig-ignore-next-line: indivisible reviewed identifier
        self.timeline._finish_launch(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
            self,
            completed=completed,
        )


@final
class CudaIndependentTicketTransferTimeline:
    """Diagnostic event phases for registered same-stream ticket work."""

    def __init__(
        self,
        functions: CudaIndependentKernelTimelineFunctions,
        launch_factory: CudaIndependentKernelLaunchFactory,
        forget: Callable[[CudaIndependentTicketTransferTimeline], None],
    ) -> None:
        """Create and synchronize one untimed event origin.

        Raises:
            AcceleratorExecutionError: If event setup fails.

        """
        self._active = 0
        self._closed = False
        self._forget = forget
        self._functions = functions
        self._launch_factory = launch_factory
        self._next_submission_index = 0
        self._origin = _create_cuda_event(functions.create_fn)
        self._samples: list[CudaIndependentTicketTransferTimelineSample] = []
        try:
            _check_execution(
                functions.record_fn(self._origin, None),
                "cuEventRecord",
            )
            _check_execution(
                functions.synchronize_fn(self._origin),
                "cuEventSynchronize",
            )
        except AcceleratorExecutionError:
            _destroy_cuda_event(functions.destroy_fn, self._origin)
            raise

    def __enter__(self) -> CudaIndependentTicketTransferTimeline:
        """Return this transfer timeline for scoped use.

        Returns:
            The same live transfer timeline.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Destroy the origin after every profiled ticket finishes."""
        self.close()

    def close(self) -> None:
        """Destroy the origin after all profiled tickets finish.

        Raises:
            AcceleratorExecutionError:
                If launches remain active or cleanup fails.

        """
        if self._closed:
            return
        self._functions.ensure_open()
        if self._active != 0:
            message = "CUDA ticket transfer timeline has active launches"
            raise AcceleratorExecutionError(message)
        _destroy_cuda_event(self._functions.destroy_fn, self._origin)
        self._closed = True
        self._forget(self)

    def samples(
        self,
    ) -> tuple[CudaIndependentTicketTransferTimelineSample, ...]:
        """Return completed phase samples in submission order.

        Returns:
            Immutable phase samples after every launch cleanup.

        Raises:
            AcceleratorExecutionError: If launches remain active or closed.

        """
        self._ensure_usable()
        if self._active != 0:
            message = "CUDA ticket transfer timeline has active launches"
            raise AcceleratorExecutionError(message)
        return tuple(
            sorted(self._samples, key=lambda sample: sample.submission_index)
        )

    def submit(
        self,
        submission: CudaIndependentTransferSubmission,
    ) -> CudaIndependentKernelLaunch:
        """Submit one transfer ticket with four contiguous event markers.

        Returns:
            Runtime-owned launch whose close publishes phase attribution.

        Raises:
            AcceleratorExecutionError: If the timeline or submission is invalid.

        """
        self._ensure_usable()
        if not submission.uploads or not submission.downloads:
            message = "CUDA transfer timeline requires uploads and downloads"
            raise AcceleratorExecutionError(message)
        return self._launch_factory.submit_transfer_profiled(
            submission,
            timeline=self,
        )

    def begin_submission(
        self,
        stream: ctypes.c_void_p,
    ) -> _CudaIndependentTicketTransferTimelineLaunch:
        """Create four events and record the pre-upload marker.

        Returns:
            Active transfer phase resources bound to one submission index.

        Raises:
            AcceleratorExecutionError: If event setup or recording fails.

        """
        self._ensure_usable()
        events = _create_cuda_events(
            self._functions.create_fn, self._functions.destroy_fn, count=4
        )
        start, upload_end, kernel_end, end = events
        try:
            _check_execution(
                self._functions.record_fn(start, stream),
                "cuEventRecord",
            )
        except AcceleratorExecutionError:
            _destroy_cuda_events(self._functions.destroy_fn, events)
            raise
        launch = _CudaIndependentTicketTransferTimelineLaunch(
            end=end,
            kernel_end=kernel_end,
            start=start,
            submission_index=self._next_submission_index,
            timeline=self,
            upload_end=upload_end,
        )
        self._next_submission_index += 1
        self._active += 1
        return launch

    def record_upload_end(
        self,
        launch: _CudaIndependentTicketTransferTimelineLaunch,
        stream: ctypes.c_void_p,
    ) -> None:
        """Record the marker after all H-to-D copies."""
        self._record(launch.upload_end, stream)

    def record_kernel_end(
        self,
        launch: _CudaIndependentTicketTransferTimelineLaunch,
        stream: ctypes.c_void_p,
    ) -> None:
        """Record the marker after the exact kernel launch."""
        self._record(launch.kernel_end, stream)

    def record_end(
        self,
        launch: _CudaIndependentTicketTransferTimelineLaunch,
        stream: ctypes.c_void_p,
    ) -> None:
        """Record the marker after all D-to-H copies."""
        self._record(launch.end, stream)

    def _finish_launch(
        self,
        launch: _CudaIndependentTicketTransferTimelineLaunch,
        *,
        completed: bool,
    ) -> None:
        """Publish one completed phase sample and destroy all four events."""
        sample_failure: AcceleratorExecutionError | None = None
        if completed:
            try:
                self._samples.append(self._sample(launch))
            except AcceleratorExecutionError as error:
                sample_failure = error
        event_failure = _destroy_cuda_events_failure(
            self._functions.destroy_fn,
            (
                launch.start,
                launch.upload_end,
                launch.kernel_end,
                launch.end,
            ),
        )
        self._active -= 1
        _raise_first_failure(sample_failure, event_failure)

    def _sample(
        self,
        launch: _CudaIndependentTicketTransferTimelineLaunch,
    ) -> CudaIndependentTicketTransferTimelineSample:
        elapsed = self._functions.elapsed_fn
        return CudaIndependentTicketTransferTimelineSample(
            download_duration_ms=_event_elapsed_ms(
                elapsed,
                launch.kernel_end,
                launch.end,
            ),
            end_ms=_event_elapsed_ms(elapsed, self._origin, launch.end),
            kernel_duration_ms=_event_elapsed_ms(
                elapsed,
                launch.upload_end,
                launch.kernel_end,
            ),
            kernel_end_ms=_event_elapsed_ms(
                elapsed,
                self._origin,
                launch.kernel_end,
            ),
            start_ms=_event_elapsed_ms(elapsed, self._origin, launch.start),
            submission_index=launch.submission_index,
            total_duration_ms=_event_elapsed_ms(
                elapsed,
                launch.start,
                launch.end,
            ),
            upload_duration_ms=_event_elapsed_ms(
                elapsed,
                launch.start,
                launch.upload_end,
            ),
            upload_end_ms=_event_elapsed_ms(
                elapsed,
                self._origin,
                launch.upload_end,
            ),
        )

    def _record(
        self,
        event: ctypes.c_void_p,
        stream: ctypes.c_void_p,
    ) -> None:
        _check_execution(
            self._functions.record_fn(event, stream),
            "cuEventRecord",
        )

    def _ensure_usable(self) -> None:
        self._functions.ensure_open()
        if self._closed:
            message = "CUDA ticket transfer timeline is closed"
            raise AcceleratorExecutionError(message)


@final
class CudaIndependentTicketTransferTimelineFactory:
    """Own transfer phase timelines created for one live CUDA context."""

    def __init__(
        self,
        functions: CudaIndependentKernelTimelineFunctions,
        launch_factory: CudaIndependentKernelLaunchFactory,
    ) -> None:
        """Bind event functions and the isolated launch factory."""
        self._functions = functions
        self._launch_factory = launch_factory
        self._timelines: list[CudaIndependentTicketTransferTimeline] = []

    def create(self) -> CudaIndependentTicketTransferTimeline:
        """Create one synchronized transfer phase timeline.

        Returns:
            Runtime-owned diagnostic timeline for streamed tickets.

        """
        timeline = CudaIndependentTicketTransferTimeline(
            self._functions,
            self._launch_factory,
            self._forget,
        )
        self._timelines.append(timeline)
        return timeline

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Close every transfer timeline after launches drain.

        Returns:
            First event cleanup failure, or ``None``.

        """
        failure: AcceleratorExecutionError | None = None
        for timeline in tuple(self._timelines):
            try:
                timeline.close()
            except AcceleratorExecutionError as error:
                if failure is None:
                    failure = error
        if failure is None:
            self._timelines.clear()
        return failure

    def _forget(self, timeline: CudaIndependentTicketTransferTimeline) -> None:
        try:
            self._timelines.remove(timeline)
        except ValueError:
            return


@dataclass(frozen=True, slots=True)
class CudaIndependentKernelLaunchFunctions:
    """Reviewed Driver functions required by isolated kernel streams."""

    copy_from_device_fn: _CudaFn
    copy_to_device_fn: _CudaFn
    create_fn: _CudaFn
    destroy_fn: _CudaFn
    ensure_open: Callable[[], None]
    host_memory: CudaHostMemoryRegistry
    launch_fn: _CudaFn
    synchronize_fn: _CudaFn


@dataclass(slots=True)
class _CudaIndependentSubmissionState:
    kernel_timeline: _CudaIndependentKernelTimelineLaunch | None = None
    pending_addresses: tuple[int, ...] = ()
    submitted_work: bool = False
    transfer_timeline: _CudaIndependentTicketTransferTimelineLaunch | None = (
        None
    )


@dataclass(frozen=True, slots=True)
class _CudaIndependentEnqueueRequest:
    arguments: _CudaKernelLaunchArguments
    handle: ctypes.c_void_p
    kernel_timeline: CudaIndependentKernelTimeline | None
    state: _CudaIndependentSubmissionState
    submission: CudaIndependentTransferSubmission
    transfer_timeline: CudaIndependentTicketTransferTimeline | None


@dataclass(frozen=True, slots=True)
class _CudaIndependentFailedSubmit:
    handle: ctypes.c_void_p
    kernel_timeline: _CudaIndependentKernelTimelineLaunch | None
    pending_addresses: tuple[int, ...]
    submitted_work: bool
    transfer_timeline: _CudaIndependentTicketTransferTimelineLaunch | None


@final
class CudaIndependentKernelLaunchFactory:
    """Own one nonblocking CUDA stream for every submitted kernel."""

    def __init__(
        self,
        binding: CudaIndependentKernelLaunchFunctions,
    ) -> None:
        """Bind one live context's stream, copy, and kernel functions."""
        self._binding = binding
        self._launches: list[CudaIndependentKernelLaunch] = []

    def submit(
        self,
        kernel: ctypes.c_void_p,
        device_pointers: tuple[int, ...],
        count: int,
    ) -> CudaIndependentKernelLaunch:
        """Submit one kernel on a new nonblocking CUDA stream.

        Returns:
            Runtime-owned isolated launch retaining all parameter owners.

        """
        return self._submit(
            CudaIndependentTransferSubmission(
                count=count,
                device_pointers=device_pointers,
                downloads=(),
                kernel=kernel,
                uploads=(),
            ),
            kernel_timeline=None,
            transfer_timeline=None,
        )

    def submit_with_transfers(
        self,
        submission: CudaIndependentTransferSubmission,
    ) -> CudaIndependentKernelLaunch:
        """Submit registered H-to-D, kernel, and D-to-H work on one stream.

        Returns:
            Runtime-owned launch retaining every host lease until completion.

        """
        return self._submit(
            submission,
            kernel_timeline=None,
            transfer_timeline=None,
        )

    def submit_profiled(
        self,
        kernel: ctypes.c_void_p,
        device_pointers: tuple[int, ...],
        count: int,
        *,
        timeline: CudaIndependentKernelTimeline,
    ) -> CudaIndependentKernelLaunch:
        """Submit one kernel with opt-in CUDA-event interval capture.

        Returns:
            Isolated launch that publishes one sample during close.

        """
        return self._submit(
            CudaIndependentTransferSubmission(
                count=count,
                device_pointers=device_pointers,
                downloads=(),
                kernel=kernel,
                uploads=(),
            ),
            kernel_timeline=timeline,
            transfer_timeline=None,
        )

    def submit_profiled_with_transfers(
        self,
        submission: CudaIndependentTransferSubmission,
        *,
        timeline: CudaIndependentKernelTimeline,
    ) -> CudaIndependentKernelLaunch:
        """Submit transfers while events delimit only the exact kernel.

        Returns:
            Isolated launch with registered copies and kernel-only events.

        """
        return self._submit(
            submission,
            kernel_timeline=timeline,
            transfer_timeline=None,
        )

    def submit_transfer_profiled(
        self,
        submission: CudaIndependentTransferSubmission,
        *,
        timeline: CudaIndependentTicketTransferTimeline,
    ) -> CudaIndependentKernelLaunch:
        """Submit transfers with contiguous upload/kernel/download markers.

        Returns:
            Isolated launch that publishes one transfer phase sample.

        """
        return self._submit(
            submission,
            kernel_timeline=None,
            transfer_timeline=timeline,
        )

    def _submit(
        self,
        submission: CudaIndependentTransferSubmission,
        *,
        kernel_timeline: CudaIndependentKernelTimeline | None,
        transfer_timeline: CudaIndependentTicketTransferTimeline | None,
    ) -> CudaIndependentKernelLaunch:
        self._binding.ensure_open()
        arguments = _kernel_launch_arguments(
            submission.device_pointers,
            submission.count,
        )
        handle = self._create_stream()
        state = _CudaIndependentSubmissionState()
        try:
            self._enqueue_submission(
                _CudaIndependentEnqueueRequest(
                    arguments=arguments,
                    handle=handle,
                    kernel_timeline=kernel_timeline,
                    state=state,
                    submission=submission,
                    transfer_timeline=transfer_timeline,
                )
            )
        except AcceleratorExecutionError as launch_error:
            cleanup_failure = self._failed_submit_cleanup(
                _CudaIndependentFailedSubmit(
                    handle=handle,
                    kernel_timeline=state.kernel_timeline,
                    pending_addresses=state.pending_addresses,
                    submitted_work=state.submitted_work,
                    transfer_timeline=state.transfer_timeline,
                )
            )
            if cleanup_failure is not None:
                raise launch_error from cleanup_failure
            raise launch_error from None
        launch = CudaIndependentKernelLaunch(
            _CudaIndependentKernelLaunchBinding(
                destroy_fn=self._binding.destroy_fn,
                ensure_open=self._binding.ensure_open,
                forget=self._forget,
                handle=handle,
                host_memory=self._binding.host_memory,
                kernel_timeline=state.kernel_timeline,
                synchronize_fn=self._binding.synchronize_fn,
                transfer_timeline=state.transfer_timeline,
            ),
            (
                *arguments.owners,
                arguments.params,
                *submission.uploads,
                *submission.downloads,
            ),
            state.pending_addresses,
        )
        self._launches.append(launch)
        return launch

    def _enqueue_submission(
        self,
        request: _CudaIndependentEnqueueRequest,
    ) -> None:
        submission = request.submission
        state = request.state
        state.pending_addresses = self._acquire_transfer_leases(submission)
        state.transfer_timeline = self._begin_transfer_timeline(
            request.transfer_timeline,
            request.handle,
        )
        state.submitted_work = state.transfer_timeline is not None
        if self._enqueue_uploads(submission.uploads, request.handle):
            state.submitted_work = True
        self._record_transfer_upload_end(
            request.transfer_timeline,
            state.transfer_timeline,
            request.handle,
        )
        state.kernel_timeline = self._begin_kernel_timeline(
            request.kernel_timeline,
            request.handle,
        )
        state.submitted_work = (
            state.submitted_work or state.kernel_timeline is not None
        )
        self._launch_kernel(
            submission.kernel,
            request.arguments,
            request.handle,
        )
        state.submitted_work = True
        self._record_kernel_timeline_end(
            request.kernel_timeline,
            state.kernel_timeline,
            request.handle,
        )
        self._record_transfer_kernel_end(
            request.transfer_timeline,
            state.transfer_timeline,
            request.handle,
        )
        _ = self._enqueue_downloads(submission.downloads, request.handle)
        self._record_transfer_end(
            request.transfer_timeline,
            state.transfer_timeline,
            request.handle,
        )

    def _acquire_transfer_leases(
        self,
        submission: CudaIndependentTransferSubmission,
    ) -> tuple[int, ...]:
        addresses: list[int] = []
        try:
            for transfer in (*submission.uploads, *submission.downloads):
                _validate_async_transfer_pointer(transfer.device_pointer)
                addresses.append(
                    self._binding.host_memory.acquire_for_async(transfer.host)
                )
        except AcceleratorExecutionError:
            self._binding.host_memory.release_async(tuple(addresses))
            raise
        return tuple(addresses)

    @staticmethod
    def _begin_kernel_timeline(
        timeline: CudaIndependentKernelTimeline | None,
        handle: ctypes.c_void_p,
    ) -> _CudaIndependentKernelTimelineLaunch | None:
        if timeline is None:
            return None
        return timeline.begin_launch(handle)

    @staticmethod
    def _begin_transfer_timeline(
        timeline: CudaIndependentTicketTransferTimeline | None,
        handle: ctypes.c_void_p,
    ) -> _CudaIndependentTicketTransferTimelineLaunch | None:
        if timeline is None:
            return None
        return timeline.begin_submission(handle)

    def _create_stream(self) -> ctypes.c_void_p:
        handle = ctypes.c_void_p()
        _check_execution(
            self._binding.create_fn(
                ctypes.byref(handle),
                CUDA_STREAM_NON_BLOCKING,
            ),
            "cuStreamCreate",
        )
        return handle

    def _enqueue_downloads(
        self,
        downloads: tuple[CudaDeviceToHostTransfer, ...],
        handle: ctypes.c_void_p,
    ) -> bool:
        submitted = False
        for transfer in downloads:
            _check_execution(
                self._binding.copy_from_device_fn(
                    transfer.host,
                    ctypes.c_uint64(transfer.device_pointer),
                    ctypes.sizeof(transfer.host),
                    handle,
                ),
                "cuMemcpyDtoHAsync_v2",
            )
            submitted = True
        return submitted

    def _enqueue_uploads(
        self,
        uploads: tuple[CudaHostToDeviceTransfer, ...],
        handle: ctypes.c_void_p,
    ) -> bool:
        submitted = False
        for transfer in uploads:
            _check_execution(
                self._binding.copy_to_device_fn(
                    ctypes.c_uint64(transfer.device_pointer),
                    transfer.host,
                    ctypes.sizeof(transfer.host),
                    handle,
                ),
                "cuMemcpyHtoDAsync_v2",
            )
            submitted = True
        return submitted

    def _failed_submit_cleanup(
        self,
        failed: _CudaIndependentFailedSubmit,
    ) -> AcceleratorExecutionError | None:
        synchronize_failure = (
            self._synchronize_failure(failed.handle)
            if failed.submitted_work
            else None
        )
        kernel_timeline_failure = self._finish_timeline_failure(
            failed.kernel_timeline
        )
        transfer_timeline_failure = self._finish_timeline_failure(
            failed.transfer_timeline
        )
        lease_failure = _release_async_addresses_failure(
            self._binding.host_memory,
            failed.pending_addresses,
        )
        stream_failure: AcceleratorExecutionError | None = None
        try:
            _check_execution(
                self._binding.destroy_fn(failed.handle),
                "cuStreamDestroy_v2",
            )
        except AcceleratorExecutionError as error:
            stream_failure = error
        return (
            synchronize_failure
            or kernel_timeline_failure
            or transfer_timeline_failure
            or lease_failure
            or stream_failure
        )

    @staticmethod
    def _finish_timeline_failure(
        timeline: (
            _CudaIndependentKernelTimelineLaunch
            | _CudaIndependentTicketTransferTimelineLaunch
            | None
        ),
    ) -> AcceleratorExecutionError | None:
        if timeline is None:
            return None
        try:
            timeline.finish(completed=False)
        except AcceleratorExecutionError as error:
            return error
        return None

    def _launch_kernel(
        self,
        kernel: ctypes.c_void_p,
        arguments: _CudaKernelLaunchArguments,
        handle: ctypes.c_void_p,
    ) -> None:
        _check_execution(
            self._binding.launch_fn(
                kernel,
                arguments.blocks,
                1,
                1,
                THREADS_PER_BLOCK,
                1,
                1,
                0,
                handle,
                arguments.params,
                None,
            ),
            "cuLaunchKernel",
        )

    @staticmethod
    def _record_kernel_timeline_end(
        timeline: CudaIndependentKernelTimeline | None,
        timeline_launch: _CudaIndependentKernelTimelineLaunch | None,
        handle: ctypes.c_void_p,
    ) -> None:
        if timeline is None or timeline_launch is None:
            return
        timeline.record_end(timeline_launch, handle)

    @staticmethod
    def _record_transfer_upload_end(
        timeline: CudaIndependentTicketTransferTimeline | None,
        timeline_launch: _CudaIndependentTicketTransferTimelineLaunch | None,
        handle: ctypes.c_void_p,
    ) -> None:
        if timeline is None or timeline_launch is None:
            return
        timeline.record_upload_end(timeline_launch, handle)

    @staticmethod
    def _record_transfer_kernel_end(
        timeline: CudaIndependentTicketTransferTimeline | None,
        timeline_launch: _CudaIndependentTicketTransferTimelineLaunch | None,
        handle: ctypes.c_void_p,
    ) -> None:
        if timeline is None or timeline_launch is None:
            return
        timeline.record_kernel_end(timeline_launch, handle)

    @staticmethod
    def _record_transfer_end(
        timeline: CudaIndependentTicketTransferTimeline | None,
        timeline_launch: _CudaIndependentTicketTransferTimelineLaunch | None,
        handle: ctypes.c_void_p,
    ) -> None:
        if timeline is None or timeline_launch is None:
            return
        timeline.record_end(timeline_launch, handle)

    def _synchronize_failure(
        self,
        handle: ctypes.c_void_p,
    ) -> AcceleratorExecutionError | None:
        try:
            _check_execution(
                self._binding.synchronize_fn(handle),
                "cuStreamSynchronize",
            )
        except AcceleratorExecutionError as error:
            return error
        return None

    def release_failure(self) -> AcceleratorExecutionError | None:
        """Close every isolated launch before context destruction.

        Returns:
            First synchronization/destruction failure, or ``None``.

        """
        return _release_independent_kernel_launches(self._launches)

    def _forget(self, launch: CudaIndependentKernelLaunch) -> None:
        try:
            self._launches.remove(launch)
        except ValueError:
            return


def _validate_async_transfer_pointer(device_pointer: int) -> None:
    if type(device_pointer) is not int or device_pointer <= 0:
        message = "CUDA asynchronous copy requires a positive device pointer"
        raise AcceleratorExecutionError(message)


def _release_async_addresses_failure(
    host_memory: CudaHostMemoryRegistry,
    addresses: tuple[int, ...],
) -> AcceleratorExecutionError | None:
    if not addresses:
        return None
    try:
        host_memory.release_async(addresses)
    except AcceleratorExecutionError as error:
        return error
    return None


def _kernel_launch_arguments(
    device_pointers: tuple[int, ...],
    count: int,
) -> _CudaKernelLaunchArguments:
    if type(count) is not int or count <= 0:
        message = "CUDA kernel launch count must be a positive integer"
        raise AcceleratorExecutionError(message)
    if not device_pointers or any(
        type(pointer) is not int or pointer <= 0 for pointer in device_pointers
    ):
        message = "CUDA kernel launch requires positive device pointers"
        raise AcceleratorExecutionError(message)
    device_arguments = tuple(
        ctypes.c_uint64(pointer) for pointer in device_pointers
    )
    count_argument = ctypes.c_uint32(count)
    owners: tuple[object, ...] = (*device_arguments, count_argument)
    params_type = ctypes.c_void_p * len(owners)
    params = params_type(*(ctypes.addressof(owner) for owner in owners))
    blocks = (count + THREADS_PER_BLOCK - 1) // THREADS_PER_BLOCK
    return _CudaKernelLaunchArguments(
        blocks=blocks,
        owners=owners,
        params=params,
    )


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
    _driver: ctypes.CDLL
    _nvrtc: ctypes.CDLL
    device_info: CudaDeviceInfo
    runtime_identity: CudaRuntimeIdentity
    host_memory: CudaHostMemoryRegistry
    independent_kernel_launches: CudaIndependentKernelLaunchFactory
    independent_kernel_timelines: CudaIndependentKernelTimelineFactory
    independent_ticket_transfer_timelines: (
        CudaIndependentTicketTransferTimelineFactory
    )
    kernel_launches: CudaKernelLaunchFactory
    ordered_transfers: CudaOrderedDtoHStreamFactory
    resources: CudaResourceProbe

    _cu_ctx_create: _CudaFn
    _cu_ctx_destroy: _CudaFn
    _cu_ctx_synchronize: _CudaFn
    _cu_event_create: _CudaFn
    _cu_event_destroy: _CudaFn
    _cu_event_elapsed_time: _CudaFn
    _cu_event_record: _CudaFn
    _cu_event_synchronize: _CudaFn
    _cu_device_compute_capability: _CudaFn
    _cu_device_get: _CudaFn
    _cu_device_get_attribute: _CudaFn
    _cu_device_get_name: _CudaFn
    _cu_driver_get_version: _CudaFn
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
    _cu_stream_create: _CudaFn
    _cu_stream_destroy: _CudaFn
    _cu_stream_synchronize: _CudaFn
    _cu_memcpy_dtoh_async: _CudaFn
    _cu_memcpy_htod_async: _CudaFn

    _nvrtc_compile_program: _CudaFn
    _nvrtc_create_program: _CudaFn
    _nvrtc_destroy_program: _CudaFn
    _nvrtc_get_log: _CudaFn
    _nvrtc_get_log_size: _CudaFn
    _nvrtc_get_ptx: _CudaFn
    _nvrtc_get_ptx_size: _CudaFn
    _nvrtc_version: _CudaFn

    def __init__(self, device_id: int = 0) -> None:
        """Load pinned CUDA runtime components and create one device context.

        Raises:
            AcceleratorUnavailableError:
                If toolkit, driver, or device is absent.

        """
        try:
            selection = select_cuda_toolchain(ROOT, _cuda_platform_id())
        except CudaToolchainSelectionError as error:
            message = f"CUDA toolchain unavailable: {error}"
            raise AcceleratorUnavailableError(message) from error
        _configure_toolkit_environment(selection)
        loaded = _load_cuda_libraries(selection)
        self._dll_directory = loaded.search_directory
        self._driver = loaded.driver
        self._nvrtc = loaded.nvrtc
        self._bind_driver()
        self._bind_nvrtc()
        self._closed = False
        self.runtime_identity = measure_cuda_runtime_identity(
            self._cu_driver_get_version,
            self._nvrtc_version,
            selection.manifest_path,
            environment=CudaRuntimeEnvironment(
                display_driver_version=measure_nvml_display_driver_version(),
                host_runtime_identity=measure_cuda_host_runtime_identity(),
            ),
        )
        self._device = self._open_device(device_id)
        self._context = self._create_context(self._device)
        self.device_info = self._read_device_info(self._device)
        self.host_memory = CudaHostMemoryRegistry(
            self._ensure_open,
            self._cu_mem_host_register,
            self._cu_mem_host_unregister,
        )
        self.kernel_launches = CudaKernelLaunchFactory(
            _CudaKernelLaunchFactoryBinding(
                ensure_open=self._ensure_open,
                launch_fn=self._cu_launch_kernel,
                synchronize_fn=self._cu_ctx_synchronize,
            )
        )
        self.independent_kernel_launches = CudaIndependentKernelLaunchFactory(
            CudaIndependentKernelLaunchFunctions(
                copy_from_device_fn=self._cu_memcpy_dtoh_async,
                copy_to_device_fn=self._cu_memcpy_htod_async,
                create_fn=self._cu_stream_create,
                destroy_fn=self._cu_stream_destroy,
                ensure_open=self._ensure_open,
                host_memory=self.host_memory,
                launch_fn=self._cu_launch_kernel,
                synchronize_fn=self._cu_stream_synchronize,
            )
        )
        self.independent_kernel_timelines = (
            CudaIndependentKernelTimelineFactory(
                CudaIndependentKernelTimelineFunctions(
                    create_fn=self._cu_event_create,
                    destroy_fn=self._cu_event_destroy,
                    elapsed_fn=self._cu_event_elapsed_time,
                    ensure_open=self._ensure_open,
                    record_fn=self._cu_event_record,
                    synchronize_fn=self._cu_event_synchronize,
                ),
                self.independent_kernel_launches,
            )
        )
        self.independent_ticket_transfer_timelines = (
            CudaIndependentTicketTransferTimelineFactory(
                CudaIndependentKernelTimelineFunctions(
                    create_fn=self._cu_event_create,
                    destroy_fn=self._cu_event_destroy,
                    elapsed_fn=self._cu_event_elapsed_time,
                    ensure_open=self._ensure_open,
                    record_fn=self._cu_event_record,
                    synchronize_fn=self._cu_event_synchronize,
                ),
                self.independent_kernel_launches,
            )
        )
        self.ordered_transfers = CudaOrderedDtoHStreamFactory(
            _CudaOrderedFactoryBinding(
                copy_fn=self._cu_memcpy_dtoh_async,
                create_fn=self._cu_stream_create,
                destroy_fn=self._cu_stream_destroy,
                ensure_open=self._ensure_open,
                host_memory=self.host_memory,
                synchronize_fn=self._cu_stream_synchronize,
            )
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
        launch_failure = self.kernel_launches.release_failure()
        independent_failure = self.independent_kernel_launches.release_failure()
        timeline_failure = self.independent_kernel_timelines.release_failure()
        transfer_timeline_failure = (
            self.independent_ticket_transfer_timelines.release_failure()
        )
        stream_failure = self.ordered_transfers.release_failure()
        registration_failure = self.host_memory.release_failure()
        self._closed = True
        context_failure = self._destroy_context_failure()
        self.host_memory.clear()
        _raise_first_failure(
            launch_failure,
            independent_failure,
            timeline_failure,
            transfer_timeline_failure,
            stream_failure,
            registration_failure,
            context_failure,
        )

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
                # jig-ignore-next-line: indivisible reviewed identifier
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
        """Launch one homogeneous kernel and preserve synchronous semantics."""
        launch = self.kernel_launches.submit(kernel, device_pointers, count)
        launch.wait()

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
        event = _bind_driver_event(self._driver)
        module = _bind_driver_module(self._driver)
        stream = _bind_driver_stream(self._driver)
        (
            self._cu_init,
            self._cu_driver_get_version,
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
            self._cu_event_create,
            self._cu_event_destroy,
            self._cu_event_elapsed_time,
            self._cu_event_record,
            self._cu_event_synchronize,
        ) = event
        (
            self._cu_module_load_data,
            self._cu_module_unload,
            self._cu_module_get_function,
            self._cu_launch_kernel,
        ) = module
        (
            self._cu_stream_create,
            self._cu_stream_destroy,
            self._cu_stream_synchronize,
            self._cu_memcpy_dtoh_async,
            self._cu_memcpy_htod_async,
        ) = stream

    def _bind_nvrtc(self) -> None:
        (
            self._nvrtc_version,
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

    def _destroy_context_failure(self) -> AcceleratorExecutionError | None:
        try:
            _check_execution(
                self._cu_ctx_destroy(self._context),
                "cuCtxDestroy_v2",
            )
        except AcceleratorExecutionError as error:
            return error
        return None

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


def _cuda_platform_id(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    operating_system = (system or platform.system()).strip().casefold()
    architecture = _normalize_host_machine(
        machine or platform.machine()
    ).casefold()
    return f"{operating_system}-{architecture}"


def _windows_library_loader(name: str) -> ctypes.CDLL:
    return ctypes.WinDLL(name)


def _posix_library_loader(name: str) -> ctypes.CDLL:
    return ctypes.CDLL(name)


def _open_windows_dll_directory(path: Path) -> object:
    return os.add_dll_directory(str(path))


def _library_loader_and_search_directory(
    selection: CudaToolchainSelection,
    *,
    windows_loader: _LibraryLoader | None,
    posix_loader: _LibraryLoader | None,
    dll_directory_opener: _DllDirectoryOpener | None,
) -> tuple[_LibraryLoader, object | None]:
    if selection.loader_kind != _WINDOWS_LOADER_KIND:
        return posix_loader or _posix_library_loader, None
    loader = windows_loader or _windows_library_loader
    opener = dll_directory_opener or _open_windows_dll_directory
    try:
        search_directory = opener(selection.nvrtc_library.parent)
    except (AttributeError, OSError) as error:
        message = f"CUDA DLL directory unavailable: {error}"
        raise AcceleratorUnavailableError(message) from error
    return loader, search_directory


def _load_cuda_libraries(
    selection: CudaToolchainSelection,
    *,
    windows_loader: _LibraryLoader | None = None,
    posix_loader: _LibraryLoader | None = None,
    dll_directory_opener: _DllDirectoryOpener | None = None,
) -> _LoadedCudaLibraries:
    if not selection.toolkit_root.is_dir():
        message = f"pinned CUDA toolkit missing: {selection.toolkit_root}"
        raise AcceleratorUnavailableError(message)
    if not selection.nvrtc_library.is_file():
        message = (
            f"pinned CUDA NVRTC library missing: {selection.nvrtc_library}"
        )
        raise AcceleratorUnavailableError(message)
    loader, search_directory = _library_loader_and_search_directory(
        selection,
        windows_loader=windows_loader,
        posix_loader=posix_loader,
        dll_directory_opener=dll_directory_opener,
    )
    try:
        driver = loader(selection.driver_library)
        nvrtc = loader(str(selection.nvrtc_library))
    except (AttributeError, OSError) as error:
        message = f"CUDA runtime library unavailable: {error}"
        raise AcceleratorUnavailableError(message) from error
    return _LoadedCudaLibraries(
        driver=driver,
        nvrtc=nvrtc,
        search_directory=search_directory,
    )


def cuda_host_runtime_identity_id() -> str:
    """Return the stable host/Python identity protocol.

    Returns:
        Versioned host identity used by evidence-bound CUDA profiles.

    """
    return CUDA_HOST_RUNTIME_IDENTITY_ID


def measure_cuda_host_runtime_identity() -> CudaHostRuntimeIdentity | None:
    """Measure host OS and Python identity without requiring it for CUDA.

    Returns:
        Validated identity, or ``None`` when the host cannot be measured.

    """
    try:
        host_system = platform.system()
        identity = CudaHostRuntimeIdentity(
            host_edition=_host_edition(host_system),
            host_machine=_normalize_host_machine(platform.machine()),
            host_release=platform.release(),
            host_system=host_system,
            host_version=platform.version(),
            identity_id=CUDA_HOST_RUNTIME_IDENTITY_ID,
            python_implementation=platform.python_implementation(),
            python_version=platform.python_version(),
        )
        return identity.validated()
    except AcceleratorUnavailableError, OSError, RuntimeError:
        return None


def cuda_runtime_identity_id() -> str:
    """Return the stable CUDA runtime/toolchain identity protocol.

    Returns:
        Versioned runtime identity used by evidence-bound profiles.

    """
    return CUDA_RUNTIME_IDENTITY_ID


def measure_cuda_runtime_identity(
    driver_version_fn: _CudaFn,
    nvrtc_version_fn: _CudaFn,
    manifest_path: Path,
    *,
    environment: CudaRuntimeEnvironment | None = None,
) -> CudaRuntimeIdentity:
    """Measure Driver API, NVRTC, toolchain, and optional display build.

    Returns:
        Validated immutable runtime identity.

    Raises:
        AcceleratorUnavailableError: If a query or manifest read fails.

    """
    driver_version = ctypes.c_int()
    _check_available(
        driver_version_fn(ctypes.pointer(driver_version)),
        "cuDriverGetVersion",
    )
    nvrtc_major = ctypes.c_int()
    nvrtc_minor = ctypes.c_int()
    _check_available(
        nvrtc_version_fn(
            ctypes.pointer(nvrtc_major),
            ctypes.pointer(nvrtc_minor),
        ),
        "nvrtcVersion",
    )
    try:
        manifest_sha256 = sha256(manifest_path.read_bytes()).hexdigest()
    except OSError as error:
        message = f"CUDA toolchain manifest unavailable: {error}"
        raise AcceleratorUnavailableError(message) from error
    observed_environment = environment or CudaRuntimeEnvironment()
    return CudaRuntimeIdentity(
        display_driver_version=observed_environment.display_driver_version,
        driver_api_version=driver_version.value,
        host_runtime_identity=observed_environment.host_runtime_identity,
        identity_id=CUDA_RUNTIME_IDENTITY_ID,
        nvrtc_major=nvrtc_major.value,
        nvrtc_minor=nvrtc_minor.value,
        toolchain_manifest_sha256=manifest_sha256,
    ).validated()


def measure_nvml_display_driver_version(
    dll_path: Path = NVML_DLL,
    *,
    loader: _NvmlLoader | None = None,
) -> str | None:
    """Read the NVIDIA display-driver build without requiring NVML.

    Returns:
        Normalized version text, or ``None`` when NVML cannot prove it.

    """
    bindings = _load_nvml(dll_path) if loader is None else loader(dll_path)
    return None if bindings is None else _query_nvml_display_driver(*bindings)


def _load_nvml(dll_path: Path) -> _NvmlBindings | None:
    if not dll_path.is_file():
        return None
    try:
        dll = ctypes.WinDLL(str(dll_path))
        return _bind_nvml(dll)
    except AttributeError, OSError:
        return None


def _query_nvml_display_driver(
    init_fn: _CudaFn,
    version_fn: _CudaFn,
    shutdown_fn: _CudaFn,
) -> str | None:
    if _call_nvml(init_fn) != NVML_SUCCESS:
        return None
    buffer = ctypes.create_string_buffer(NVML_VERSION_BUFFER_BYTES)
    query_result = _call_nvml(version_fn, buffer, len(buffer))
    shutdown_result = _call_nvml(shutdown_fn)
    raw = bytes(buffer).split(b"\0", maxsplit=1)[0]
    version = _decode_ascii(raw)
    valid = (
        query_result == NVML_SUCCESS
        and shutdown_result == NVML_SUCCESS
        and version is not None
        and _valid_display_driver_version(version)
    )
    return version if valid else None


def _call_nvml(function: _CudaFn, *arguments: object) -> int | None:
    try:
        return function(*arguments)
    except ctypes.ArgumentError, OSError, TypeError, ValueError:
        return None


def _decode_ascii(payload: bytes) -> str | None:
    try:
        return payload.decode("ascii")
    except UnicodeDecodeError:
        return None


def _bind_nvml(dll: ctypes.CDLL) -> _NvmlBindings:
    raw_init = dll.nvmlInit_v2
    raw_init.argtypes = []
    raw_init.restype = ctypes.c_int
    raw_version = dll.nvmlSystemGetDriverVersion
    raw_version.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    raw_version.restype = ctypes.c_int
    raw_shutdown = dll.nvmlShutdown
    raw_shutdown.argtypes = []
    raw_shutdown.restype = ctypes.c_int
    return (
        cast("_CudaFn", raw_init),
        cast("_CudaFn", raw_version),
        cast("_CudaFn", raw_shutdown),
    )


def _valid_display_driver_version(version: str) -> bool:
    components = version.split(".")
    return (
        version.strip() == version
        and len(components) >= _DISPLAY_DRIVER_MIN_COMPONENTS
        and all(
            bool(component) and component.isdigit() for component in components
        )
    )


def _host_edition(host_system: str) -> str | None:
    if host_system != _WINDOWS_SYSTEM:
        return None
    try:
        return platform.win32_edition()
    except OSError:
        return None


def _normalize_host_machine(machine: str) -> str:
    normalized = machine.strip()
    if normalized.casefold() in {"amd64", "x86_64"}:
        return "x86_64"
    return normalized


def _validate_host_runtime_identity(
    identity: CudaHostRuntimeIdentity | None,
) -> None:
    if identity is not None:
        _ = identity.validated()


def _validate_cuda_runtime_protocol(identity: CudaRuntimeIdentity) -> None:
    if identity.identity_id != CUDA_RUNTIME_IDENTITY_ID:
        message = "CUDA runtime identity protocol mismatched"
        raise AcceleratorUnavailableError(message)


def _validate_cuda_runtime_versions(identity: CudaRuntimeIdentity) -> None:
    if identity.driver_api_version <= 0:
        message = "CUDA Driver API version must be positive"
        raise AcceleratorUnavailableError(message)
    if identity.nvrtc_major <= 0 or identity.nvrtc_minor < 0:
        message = "NVRTC version is invalid"
        raise AcceleratorUnavailableError(message)


def _validate_display_driver_version(version: str | None) -> None:
    if version is not None and not _valid_display_driver_version(version):
        message = "NVIDIA display-driver version is invalid"
        raise AcceleratorUnavailableError(message)


def _validate_sha256(digest: str) -> None:
    if len(digest) != _SHA256_HEX_LENGTH or any(
        char not in _HEX_DIGITS for char in digest
    ):
        message = "CUDA toolchain manifest SHA-256 is invalid"
        raise AcceleratorUnavailableError(message)


def _bind_driver_version(dll: ctypes.CDLL) -> _CudaFn:
    raw = dll.cuDriverGetVersion
    raw.argtypes = [ctypes.POINTER(ctypes.c_int)]
    raw.restype = ctypes.c_int
    return cast("_CudaFn", raw)


def _bind_driver_context(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
    raw_init = dll.cuInit
    raw_init.argtypes = [ctypes.c_uint]
    raw_init.restype = ctypes.c_int
    raw_driver_version = _bind_driver_version(dll)
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
            raw_driver_version,
            raw_device_get,
            raw_attribute,
            raw_ctx_create,
            raw_ctx_destroy,
            raw_sync,
            raw_name,
            raw_capability,
        )
    )


def _bind_driver_memory(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
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


def _bind_driver_event(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
    raw_create = dll.cuEventCreate
    raw_create.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_uint,
    ]
    raw_create.restype = ctypes.c_int
    raw_destroy = dll.cuEventDestroy_v2
    raw_destroy.argtypes = [ctypes.c_void_p]
    raw_destroy.restype = ctypes.c_int
    raw_elapsed = dll.cuEventElapsedTime_v2
    raw_elapsed.argtypes = [
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    raw_elapsed.restype = ctypes.c_int
    raw_record = dll.cuEventRecord
    raw_record.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    raw_record.restype = ctypes.c_int
    raw_synchronize = dll.cuEventSynchronize
    raw_synchronize.argtypes = [ctypes.c_void_p]
    raw_synchronize.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (
            raw_create,
            raw_destroy,
            raw_elapsed,
            raw_record,
            raw_synchronize,
        )
    )


def _bind_driver_module(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
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


def _bind_driver_stream(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
    raw_create = dll.cuStreamCreate
    raw_create.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_uint,
    ]
    raw_create.restype = ctypes.c_int
    raw_destroy = dll.cuStreamDestroy_v2
    raw_destroy.argtypes = [ctypes.c_void_p]
    raw_destroy.restype = ctypes.c_int
    raw_synchronize = dll.cuStreamSynchronize
    raw_synchronize.argtypes = [ctypes.c_void_p]
    raw_synchronize.restype = ctypes.c_int
    raw_dtoh_async = dll.cuMemcpyDtoHAsync_v2
    raw_dtoh_async.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint64,
        ctypes.c_size_t,
        ctypes.c_void_p,
    ]
    raw_dtoh_async.restype = ctypes.c_int
    raw_htod_async = dll.cuMemcpyHtoDAsync_v2
    raw_htod_async.argtypes = [
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
    ]
    raw_htod_async.restype = ctypes.c_int
    return tuple(
        cast("_CudaFn", raw)
        for raw in (
            raw_create,
            raw_destroy,
            raw_synchronize,
            raw_dtoh_async,
            raw_htod_async,
        )
    )


def create_independent_kernel_timeline(
    runtime: CudaRuntime,
) -> CudaIndependentKernelTimeline:
    """Create one CUDA-event timeline from a live runtime.

    Returns:
        Runtime-owned diagnostic timeline for isolated kernel launches.

    """
    return runtime.independent_kernel_timelines.create()


def create_independent_ticket_transfer_timeline(
    runtime: CudaRuntime,
) -> CudaIndependentTicketTransferTimeline:
    """Create one CUDA-event transfer timeline from a live runtime.

    Returns:
        Runtime-owned phase timeline for registered ticket transfers.

    """
    return runtime.independent_ticket_transfer_timelines.create()


def create_ordered_dtoh_stream(
    runtime: CudaRuntime,
) -> CudaOrderedDtoHStream:
    """Create one ordered registered D-to-H stream from a live runtime.

    Returns:
        Runtime-owned stream with explicit submit/wait lifetime.

    """
    return runtime.ordered_transfers.create()


def _create_cuda_event(create_fn: _CudaFn) -> ctypes.c_void_p:
    event = ctypes.c_void_p()
    _check_execution(
        create_fn(ctypes.byref(event), CUDA_EVENT_DEFAULT),
        "cuEventCreate",
    )
    return event


def _create_cuda_events(
    create_fn: _CudaFn,
    destroy_fn: _CudaFn,
    *,
    count: int,
) -> tuple[ctypes.c_void_p, ...]:
    events: list[ctypes.c_void_p] = []
    try:
        events.extend(_create_cuda_event(create_fn) for _ in range(count))
    except AcceleratorExecutionError as create_error:
        cleanup_failure = _destroy_cuda_events_failure(
            destroy_fn,
            tuple(events),
        )
        if cleanup_failure is not None:
            raise create_error from cleanup_failure
        raise create_error from None
    return tuple(events)


def _destroy_cuda_event(destroy_fn: _CudaFn, event: ctypes.c_void_p) -> None:
    _check_execution(destroy_fn(event), "cuEventDestroy_v2")


def _destroy_cuda_event_failure(
    destroy_fn: _CudaFn,
    event: ctypes.c_void_p,
) -> AcceleratorExecutionError | None:
    try:
        _destroy_cuda_event(destroy_fn, event)
    except AcceleratorExecutionError as error:
        return error
    return None


def _destroy_cuda_events(
    destroy_fn: _CudaFn,
    events: tuple[ctypes.c_void_p, ...],
) -> None:
    failure = _destroy_cuda_events_failure(destroy_fn, events)
    if failure is not None:
        raise failure


def _destroy_cuda_events_failure(
    destroy_fn: _CudaFn,
    events: tuple[ctypes.c_void_p, ...],
) -> AcceleratorExecutionError | None:
    failure: AcceleratorExecutionError | None = None
    for event in reversed(events):
        event_failure = _destroy_cuda_event_failure(destroy_fn, event)
        if failure is None and event_failure is not None:
            failure = event_failure
    return failure


def _event_elapsed_ms(
    elapsed_fn: _CudaFn,
    start: ctypes.c_void_p,
    end: ctypes.c_void_p,
) -> float:
    milliseconds = ctypes.c_float()
    _check_execution(
        elapsed_fn(ctypes.byref(milliseconds), start, end),
        "cuEventElapsedTime_v2",
    )
    return float(milliseconds.value)


def _raise_first_failure(
    *failures: AcceleratorExecutionError | None,
) -> None:
    for failure in failures:
        if failure is not None:
            raise failure


def _release_kernel_launches(
    launches: list[CudaKernelLaunch],
) -> AcceleratorExecutionError | None:
    failure: AcceleratorExecutionError | None = None
    for launch in tuple(launches):
        try:
            launch.close()
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
    if failure is None:
        launches.clear()
    return failure


def _release_independent_kernel_launches(
    launches: list[CudaIndependentKernelLaunch],
) -> AcceleratorExecutionError | None:
    failure: AcceleratorExecutionError | None = None
    for launch in tuple(launches):
        try:
            launch.close()
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
    if failure is None:
        launches.clear()
    return failure


def _release_ordered_dtoh_streams(
    streams: list[CudaOrderedDtoHStream],
) -> AcceleratorExecutionError | None:
    failure: AcceleratorExecutionError | None = None
    for stream in tuple(streams):
        try:
            stream.close()
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
    if failure is None:
        streams.clear()
    return failure


def _bind_nvrtc(dll: ctypes.CDLL) -> tuple[_CudaFn, ...]:
    raw_version = dll.nvrtcVersion
    raw_version.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    raw_version.restype = ctypes.c_int
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
            raw_version,
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


def _configure_toolkit_environment(
    selection: CudaToolchainSelection,
) -> None:
    os.environ["CUDA_PATH"] = str(selection.toolkit_root)
    if selection.loader_kind != _WINDOWS_LOADER_KIND:
        return
    bin_path = selection.toolkit_root / "bin"
    os.environ["PATH"] = os.pathsep.join((
        str(bin_path),
        str(selection.nvrtc_library.parent),
        os.environ.get("PATH", ""),
    ))
