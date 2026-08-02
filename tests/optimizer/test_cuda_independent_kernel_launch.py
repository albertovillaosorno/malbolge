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
#   - Deterministic contract evidence for isolated CUDA kernel streams.
# - Must-Not:
#   - Claim device overlap, speedup, or candidate acceptance authority.
# - Allows:
#   - Inputs: fake Driver handles and exact launch arguments.
#   - Outputs: stream creation, synchronization, and destruction assertions.
#   - Side effects: in-memory fake CUDA call logs only.
# - Split-When:
#   - Split when event dependencies or asynchronous transfers gain a contract.
# - Merge-When:
#   - Merge when another test owns the same one-stream-per-launch lifetime.
# - Summary:
#   - Independent CUDA kernel launch lifetime regressions.
# - Description:
#   - Proves one nonblocking stream per kernel and stream-specific completion.
# - Usage:
#   - Runs without CUDA hardware as part of the optimizer test suite.
# - Defaults:
#   - Every created stream is destroyed on completion or submission failure.
#

"""Independent CUDA kernel stream lifetime without hardware dependency."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING
from typing import final

from accelerator.cuda.runtime import CUDA_STREAM_NON_BLOCKING
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFactory
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFunctions
from accelerator.cuda.runtime import cuda_independent_kernel_launch_id
from accelerator.cuda.runtime import cuda_kernel_launch_id
from accelerator.exact_primitives import AcceleratorExecutionError
import pytest

if TYPE_CHECKING:
    from accelerator.cuda.runtime import CudaIndependentKernelLaunch

EXPECTED_ID = "cuda-independent-stream-kernel-launch-v1"
DEFAULT_ID = "cuda-default-stream-kernel-launch-v1"
SYNCHRONIZE_OPERATION = "cuStreamSynchronize"
FIRST_STREAM = 101
SECOND_STREAM = 202
KERNEL_ADDRESS = 303


@final
class _FakeDriver:
    """Record exact stream calls while returning configured CUDA statuses."""

    def __init__(
        self,
        *,
        launch_status: int = 0,
        synchronize_status: int = 0,
    ) -> None:
        self.created_flags: list[int] = []
        self.destroyed: list[int] = []
        self.launched: list[int] = []
        self.launch_status: int = launch_status
        self.next_handles: list[int] = [FIRST_STREAM, SECOND_STREAM]
        self.synchronize_status: int = synchronize_status
        self.synchronized: list[int] = []

    def create(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Assign one deterministic opaque stream handle.

        Returns:
            CUDA success.

        """
        self.created_flags.append(flags)
        handle = self.next_handles.pop(0)
        target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))
        target[0] = ctypes.c_void_p(handle)
        return 0

    def destroy(self, handle: ctypes.c_void_p) -> int:
        """Record exact stream destruction.

        Returns:
            CUDA success.

        """
        self.destroyed.append(_handle_value(handle))
        return 0

    def launch(self, *arguments: object) -> int:
        """Record the stream argument passed to ``cuLaunchKernel``.

        Returns:
            Configured CUDA launch status.

        Raises:
            TypeError: If the stream argument has the wrong representation.

        """
        handle = arguments[8]
        if not isinstance(handle, ctypes.c_void_p):
            message = "fake CUDA launch received a non-stream handle"
            raise TypeError(message)
        self.launched.append(_handle_value(handle))
        return self.launch_status

    def synchronize(self, handle: ctypes.c_void_p) -> int:
        """Record exact stream synchronization.

        Returns:
            CUDA success.

        """
        self.synchronized.append(_handle_value(handle))
        return self.synchronize_status


def _copy_success(*arguments: object) -> int:
    """Return CUDA success for transfer functions unused in this suite.

    Returns:
        CUDA success.

    """
    del arguments
    return 0


def _handle_value(handle: ctypes.c_void_p) -> int:
    value = handle.value
    if value is None:
        message = "fake CUDA stream handle is null"
        raise AssertionError(message)
    return value


def _factory(fake: _FakeDriver) -> CudaIndependentKernelLaunchFactory:
    return CudaIndependentKernelLaunchFactory(
        CudaIndependentKernelLaunchFunctions(
            copy_from_device_fn=_copy_success,
            copy_to_device_fn=_copy_success,
            create_fn=fake.create,
            destroy_fn=fake.destroy,
            ensure_open=lambda: None,
            host_memory=CudaHostMemoryRegistry(
                lambda: None,
                _copy_success,
                _copy_success,
            ),
            launch_fn=fake.launch,
            synchronize_fn=fake.synchronize,
        )
    )


def _submit(
    factory: CudaIndependentKernelLaunchFactory,
) -> CudaIndependentKernelLaunch:
    return factory.submit(
        ctypes.c_void_p(KERNEL_ADDRESS),
        (11, 22),
        257,
    )


def test_independent_kernel_launch_identity_is_stable() -> None:
    """Evidence names the exact one-stream-per-kernel lifetime."""
    assert cuda_independent_kernel_launch_id() == EXPECTED_ID


def test_default_kernel_launch_identity_remains_stable() -> None:
    """Synchronous runtime launch identity is unchanged by ticket isolation."""
    assert cuda_kernel_launch_id() == DEFAULT_ID


def test_wait_synchronizes_only_the_selected_stream() -> None:
    """Reverse waiting never synchronizes or destroys the other launch."""
    fake = _FakeDriver()
    factory = _factory(fake)
    first = _submit(factory)
    second = _submit(factory)

    assert fake.created_flags == [
        CUDA_STREAM_NON_BLOCKING,
        CUDA_STREAM_NON_BLOCKING,
    ]
    assert fake.launched == [FIRST_STREAM, SECOND_STREAM]

    second.wait()

    assert second.completed
    assert not first.completed
    assert fake.synchronized == [SECOND_STREAM]
    assert fake.destroyed == []

    second.close()
    assert fake.destroyed == [SECOND_STREAM]
    assert factory.release_failure() is None
    assert fake.synchronized == [SECOND_STREAM, FIRST_STREAM]
    assert fake.destroyed == [SECOND_STREAM, FIRST_STREAM]


def test_launch_failure_destroys_the_new_stream() -> None:
    """A rejected kernel never leaves its isolated stream owned."""
    fake = _FakeDriver(launch_status=7)
    factory = _factory(fake)

    with pytest.raises(AcceleratorExecutionError, match="cuLaunchKernel"):
        _ = _submit(factory)

    assert fake.created_flags == [CUDA_STREAM_NON_BLOCKING]
    assert fake.launched == [FIRST_STREAM]
    assert fake.synchronized == []
    assert fake.destroyed == [FIRST_STREAM]
    assert factory.release_failure() is None


def test_synchronize_failure_still_destroys_the_stream() -> None:
    """Teardown reports sync failure after attempting exact destruction."""
    fake = _FakeDriver(synchronize_status=9)
    factory = _factory(fake)
    _ = _submit(factory)

    failure = factory.release_failure()

    assert failure is not None
    assert SYNCHRONIZE_OPERATION in str(failure)
    assert fake.synchronized == [FIRST_STREAM]
    assert fake.destroyed == [FIRST_STREAM]
    assert factory.release_failure() is None
