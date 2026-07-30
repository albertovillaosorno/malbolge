# File:
#   - test_cuda_independent_ticket_transfers.py
# Path:
#   - tests/optimizer/test_cuda_independent_ticket_transfers.py
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
#   - Deterministic same-stream CUDA ticket transfer lifetime evidence.
# - Must-Not:
#   - Claim physical transfer overlap, speedup, or semantic authority.
# - Allows:
#   - Inputs: fake Driver calls and registered host word buffers.
#   - Outputs: exact enqueue, synchronization, lease, and cleanup assertions.
#   - Side effects: in-memory fake CUDA logs and host-registration state only.
# - Split-When:
#   - Split when transfer-event attribution gains an independent contract.
# - Merge-When:
#   - Merge when another test owns this exact same-stream transfer lifetime.
# - Summary:
#   - Independent CUDA ticket transfer lifetime regressions.
# - Description:
#   - Proves registered H-to-D/kernel/D-to-H ordering and fail-closed cleanup.
# - Usage:
#   - Runs without CUDA hardware as part of the optimizer test suite.
# - Defaults:
#   - Every acquired host lease is released before stream destruction returns.
#
# Related documents:
# - accelerator/cuda/runtime.py
#
# Large file:
#   - false
#

"""Independent registered CUDA ticket transfers without hardware dependency."""

from __future__ import annotations

import ctypes
from typing import final

import pytest

from accelerator.cuda import cuda_independent_ticket_transfer_id
from accelerator.cuda.runtime import CUDA_STREAM_NON_BLOCKING
from accelerator.cuda.runtime import CudaDeviceToHostTransfer
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.cuda.runtime import CudaHostToDeviceTransfer
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFactory
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFunctions
from accelerator.cuda.runtime import CudaIndependentTransferSubmission
from accelerator.exact_primitives import AcceleratorExecutionError

CUDA_SUCCESS = 0
COPY_FAILURE = 17
SYNCHRONIZE_FAILURE = 19
STREAM_HANDLE = 101
KERNEL_ADDRESS = 303
INPUT_POINTER = 401
OUTPUT_POINTER = 402
EXPECTED_ID = "cuda-independent-stream-ticket-transfer-v1"


@final
class _FakeDriver:
    """Record exact stream/copy/kernel calls with configurable failures."""

    def __init__(
        self,
        *,
        dtoh_status: int = CUDA_SUCCESS,
        htod_status: int = CUDA_SUCCESS,
        synchronize_status: int = CUDA_SUCCESS,
    ) -> None:
        self.destroyed: list[int] = []
        self.dtoh_status = dtoh_status
        self.htod_status = htod_status
        self.log: list[str] = []
        self.synchronize_status = synchronize_status
        self.synchronized: list[int] = []
        self.unregistered: list[int] = []

    def copy_from_device(self, *arguments: object) -> int:
        """Record one D-to-H enqueue.

        Returns:
            Configured CUDA copy status.

        """
        self.log.append(f"dtoh:{_stream_argument(arguments, 3)}")
        return self.dtoh_status

    def copy_to_device(self, *arguments: object) -> int:
        """Record one H-to-D enqueue.

        Returns:
            Configured CUDA copy status.

        """
        self.log.append(f"htod:{_stream_argument(arguments, 3)}")
        return self.htod_status

    def create(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Create one deterministic stream.

        Returns:
            CUDA success.

        """
        self.log.append(f"create:{flags}")
        target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))
        target[0] = ctypes.c_void_p(STREAM_HANDLE)
        return CUDA_SUCCESS

    def destroy(self, handle: ctypes.c_void_p) -> int:
        """Record exact stream destruction.

        Returns:
            CUDA success.

        """
        value = _handle_value(handle)
        self.destroyed.append(value)
        self.log.append(f"destroy:{value}")
        return CUDA_SUCCESS

    def launch(self, *arguments: object) -> int:
        """Record one kernel enqueue.

        Returns:
            CUDA success.

        """
        self.log.append(f"kernel:{_stream_argument(arguments, 8)}")
        return CUDA_SUCCESS

    @staticmethod
    def register(*arguments: object) -> int:
        """Accept one host registration.

        Returns:
            CUDA success.

        """
        del arguments
        return CUDA_SUCCESS

    def synchronize(self, handle: ctypes.c_void_p) -> int:
        """Record stream synchronization.

        Returns:
            Configured CUDA synchronization status.

        """
        value = _handle_value(handle)
        self.synchronized.append(value)
        self.log.append(f"sync:{value}")
        return self.synchronize_status

    def unregister(self, pointer: ctypes.c_void_p) -> int:
        """Record one host unregistration.

        Returns:
            CUDA success.

        """
        value = _handle_value(pointer)
        self.unregistered.append(value)
        return CUDA_SUCCESS


def _handle_value(handle: ctypes.c_void_p) -> int:
    value = handle.value
    if value is None:
        message = "fake CUDA handle is null"
        raise AssertionError(message)
    return value


def _stream_argument(arguments: tuple[object, ...], index: int) -> int:
    stream = arguments[index]
    if not isinstance(stream, ctypes.c_void_p):
        message = "fake CUDA copy/launch received a non-stream handle"
        raise TypeError(message)
    return _handle_value(stream)


def _runtime_parts(
    fake: _FakeDriver,
) -> tuple[CudaHostMemoryRegistry, CudaIndependentKernelLaunchFactory]:
    registry = CudaHostMemoryRegistry(
        lambda: None,
        fake.register,
        fake.unregister,
    )
    factory = CudaIndependentKernelLaunchFactory(
        CudaIndependentKernelLaunchFunctions(
            copy_from_device_fn=fake.copy_from_device,
            copy_to_device_fn=fake.copy_to_device,
            create_fn=fake.create,
            destroy_fn=fake.destroy,
            ensure_open=lambda: None,
            host_memory=registry,
            launch_fn=fake.launch,
            synchronize_fn=fake.synchronize,
        )
    )
    return registry, factory


def _submission(
    registry: CudaHostMemoryRegistry,
) -> tuple[CudaIndependentTransferSubmission, int, int]:
    host_input = (ctypes.c_uint32 * 2)(7, 11)
    host_output = (ctypes.c_uint32 * 2)()
    input_address = registry.register(host_input)
    output_address = registry.register(host_output)
    return (
        CudaIndependentTransferSubmission(
            count=2,
            device_pointers=(INPUT_POINTER, OUTPUT_POINTER),
            downloads=(
                CudaDeviceToHostTransfer(
                    device_pointer=OUTPUT_POINTER,
                    host=host_output,
                ),
            ),
            kernel=ctypes.c_void_p(KERNEL_ADDRESS),
            uploads=(
                CudaHostToDeviceTransfer(
                    device_pointer=INPUT_POINTER,
                    host=host_input,
                ),
            ),
        ),
        input_address,
        output_address,
    )


def test_independent_ticket_transfer_identity_is_stable() -> None:
    """Evidence names the exact same-stream registered transfer lifetime."""
    assert cuda_independent_ticket_transfer_id() == EXPECTED_ID


def test_transfers_enqueue_in_one_stream_and_hold_host_leases() -> None:
    """Copies surround the kernel and block unregistration until wait."""
    fake = _FakeDriver()
    registry, factory = _runtime_parts(fake)
    submission, input_address, output_address = _submission(registry)

    launch = factory.submit_with_transfers(submission)

    assert fake.log == [
        f"create:{CUDA_STREAM_NON_BLOCKING}",
        f"htod:{STREAM_HANDLE}",
        f"kernel:{STREAM_HANDLE}",
        f"dtoh:{STREAM_HANDLE}",
    ]
    with pytest.raises(AcceleratorExecutionError, match="in flight"):
        registry.unregister(input_address)
    with pytest.raises(AcceleratorExecutionError, match="in flight"):
        registry.unregister(output_address)

    launch.wait()
    registry.unregister(input_address)
    registry.unregister(output_address)
    launch.close()

    assert fake.synchronized == [STREAM_HANDLE]
    assert fake.destroyed == [STREAM_HANDLE]
    assert fake.unregistered == [input_address, output_address]
    assert factory.release_failure() is None


def test_htod_failure_releases_leases_without_stream_sync() -> None:
    """A rejected first upload releases every acquired lease before destroy."""
    fake = _FakeDriver(htod_status=COPY_FAILURE)
    registry, factory = _runtime_parts(fake)
    submission, input_address, output_address = _submission(registry)

    with pytest.raises(AcceleratorExecutionError, match="cuMemcpyHtoDAsync"):
        _ = factory.submit_with_transfers(submission)

    registry.unregister(input_address)
    registry.unregister(output_address)
    assert fake.synchronized == []
    assert fake.destroyed == [STREAM_HANDLE]
    assert factory.release_failure() is None


def test_dtoh_failure_synchronizes_queued_work_before_cleanup() -> None:
    """A rejected download drains prior upload/kernel work before release."""
    fake = _FakeDriver(dtoh_status=COPY_FAILURE)
    registry, factory = _runtime_parts(fake)
    submission, input_address, output_address = _submission(registry)

    with pytest.raises(AcceleratorExecutionError, match="cuMemcpyDtoHAsync"):
        _ = factory.submit_with_transfers(submission)

    registry.unregister(input_address)
    registry.unregister(output_address)
    assert fake.synchronized == [STREAM_HANDLE]
    assert fake.destroyed == [STREAM_HANDLE]
    assert factory.release_failure() is None


def test_synchronize_failure_releases_leases_and_destroys_stream() -> None:
    """Failed completion still releases host locks and destroys the stream."""
    fake = _FakeDriver(synchronize_status=SYNCHRONIZE_FAILURE)
    registry, factory = _runtime_parts(fake)
    submission, input_address, output_address = _submission(registry)
    launch = factory.submit_with_transfers(submission)

    with pytest.raises(AcceleratorExecutionError, match="cuStreamSynchronize"):
        launch.close()

    registry.unregister(input_address)
    registry.unregister(output_address)
    assert fake.synchronized == [STREAM_HANDLE]
    assert fake.destroyed == [STREAM_HANDLE]
    assert factory.release_failure() is None
