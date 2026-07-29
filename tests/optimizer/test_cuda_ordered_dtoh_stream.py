# File:
#   - test_cuda_ordered_dtoh_stream.py
# Path:
#   - tests/optimizer/test_cuda_ordered_dtoh_stream.py
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
#   - Live CUDA evidence for ordered registered D-to-H submission lifetime.
# - Must-Not:
#   - Treat asynchronous transfer as semantic authority or implicit overlap.
# - Allows:
#   - Inputs: registered ctypes u32 buffers and owned device pointers.
#   - Outputs: exact copied words and synchronized transfer counts.
#   - Side effects: explicit CUDA streams, registrations, and allocations.
# - Split-When:
#   - Split when higher-level snapshot overlap gains its own lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact runtime transfer contract.
# - Summary:
#   - Ordered CUDA D-to-H stream lifetime and failure evidence.
# - Description:
#   - Exercises the reviewed Driver stream boundary on available live hardware.
# - Usage:
#   - Runs as part of the optimizer/CUDA test suite.
# - Defaults:
#   - Missing CUDA skips; invalid ownership and ordering fail closed.
#
# Related documents:
# - docs/technical/integrations/accelerators/cuda-exact-vm-adapter.md
# - docs/technical/integrations/accelerators/replaceable-accelerator-boundary.md
#
# Large file:
#   - false
#

"""Live ordered registered CUDA D-to-H transfer evidence."""

from __future__ import annotations

import ctypes
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from unittest import SkipTest

import pytest

from accelerator.cuda.runtime import CudaRuntime
from accelerator.cuda.runtime import create_ordered_dtoh_stream
from accelerator.cuda.runtime import cuda_ordered_dtoh_stream_id
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError

if TYPE_CHECKING:
    from accelerator.cuda.runtime import CudaOrderedDtoHStream

WORD_COUNT: Final = 4
WORD_BYTES: Final = ctypes.sizeof(ctypes.c_uint32)
TRANSFER_BYTES: Final = WORD_COUNT * WORD_BYTES
ORDERED_COPY_COUNT: Final = 2
ORDERED_DTOH_STREAM_ID: Final = "cuda-ordered-registered-dtoh-stream-v1"
type Words = ctypes.Array[ctypes.c_uint32]


def _runtime() -> CudaRuntime:
    try:
        return CudaRuntime()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _words(*values: int) -> Words:
    if len(values) != WORD_COUNT:
        message = "ordered transfer fixture requires four words"
        raise RuntimeError(message)
    return (ctypes.c_uint32 * WORD_COUNT)(*values)


def _values(words: Words) -> tuple[int, ...]:
    return tuple(
        cast("int", words[index]) for index in range(WORD_COUNT)
    )


@final
class _TransferFixture:
    """Own live runtime resources for one focused transfer assertion."""

    def __init__(self) -> None:
        self.runtime: CudaRuntime = _runtime()
        self._addresses: list[int] = []
        self._pointers: list[int] = []
        self._streams: list[CudaOrderedDtoHStream] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        for stream in reversed(self._streams):
            stream.close()
        for pointer in reversed(self._pointers):
            self.runtime.free(pointer)
        for address in reversed(self._addresses):
            self.runtime.host_memory.unregister(address)
        self.runtime.close()

    def create_stream(self) -> CudaOrderedDtoHStream:
        stream = create_ordered_dtoh_stream(self.runtime)
        self._streams.append(stream)
        return stream

    def register(self, host: Words) -> int:
        address = self.runtime.host_memory.register(host)
        self._addresses.append(address)
        return address

    def unregister(self, address: int) -> None:
        self.runtime.host_memory.unregister(address)
        self._addresses.remove(address)

    def upload(self, source: Words) -> int:
        pointer = self.runtime.allocate(TRANSFER_BYTES)
        self._pointers.append(pointer)
        self.runtime.copy_to_device(pointer, source)
        return pointer


def test_cuda_ordered_dtoh_stream_copies_exact_registered_buffer() -> None:
    """One pending copy owns registration until exact synchronization."""
    source = _words(1, 2, 3, 4)
    target = _words(0, 0, 0, 0)
    with _TransferFixture() as fixture:
        pointer = fixture.upload(source)
        address = fixture.register(target)
        stream = fixture.create_stream()
        stream.submit_copy_from_device(target, pointer)

        assert stream.pending_bytes == TRANSFER_BYTES
        assert stream.pending_copies == 1
        with pytest.raises(
            AcceleratorExecutionError,
            match="transfers in flight",
        ):
            fixture.unregister(address)
        summary = stream.wait()
        fixture.unregister(address)

    assert summary.bytes == TRANSFER_BYTES
    assert summary.copies == 1
    assert stream.pending_bytes == 0
    assert stream.pending_copies == 0
    assert _values(target) == _values(source)


def test_cuda_ordered_dtoh_stream_preserves_same_host_order() -> None:
    """Later copy to the same registered host wins after one ordered wait."""
    first = _words(10, 20, 30, 40)
    second = _words(50, 60, 70, 80)
    target = _words(0, 0, 0, 0)
    with _TransferFixture() as fixture:
        pointers = (fixture.upload(first), fixture.upload(second))
        address = fixture.register(target)
        stream = fixture.create_stream()
        for pointer in pointers:
            stream.submit_copy_from_device(target, pointer)
        summary = stream.wait()
        fixture.unregister(address)
        with pytest.raises(
            AcceleratorExecutionError,
            match="no pending copies",
        ):
            _ = stream.wait()

    assert summary.bytes == ORDERED_COPY_COUNT * TRANSFER_BYTES
    assert summary.copies == ORDERED_COPY_COUNT
    assert _values(target) == _values(second)


def test_cuda_ordered_dtoh_stream_rejects_unowned_inputs() -> None:
    """Submission requires registration and a positive device pointer."""
    target = _words(0, 0, 0, 0)
    with _TransferFixture() as fixture:
        stream = fixture.create_stream()
        with pytest.raises(
            AcceleratorExecutionError,
            match="requires a registered host buffer",
        ):
            stream.submit_copy_from_device(target, 1)
        address = fixture.register(target)
        for pointer in (0, -1, True):
            with pytest.raises(
                AcceleratorExecutionError,
                match="positive device pointer",
            ):
                stream.submit_copy_from_device(target, pointer)
        fixture.unregister(address)

    assert stream.pending_copies == 0


def test_cuda_ordered_dtoh_stream_close_drains_pending_copy() -> None:
    """Explicit close waits before releasing registration ownership."""
    source = _words(101, 102, 103, 104)
    target = _words(0, 0, 0, 0)
    with _TransferFixture() as fixture:
        pointer = fixture.upload(source)
        address = fixture.register(target)
        stream = fixture.create_stream()
        stream.submit_copy_from_device(target, pointer)
        stream.close()
        fixture.unregister(address)
        with pytest.raises(
            AcceleratorExecutionError,
            match="stream is closed",
        ):
            stream.submit_copy_from_device(target, pointer)

    assert _values(target) == _values(source)
    assert stream.pending_copies == 0


def test_cuda_runtime_close_drains_owned_ordered_streams() -> None:
    """Runtime teardown synchronizes streams before host/context release."""
    runtime = _runtime()
    source = _words(201, 202, 203, 204)
    target = _words(0, 0, 0, 0)
    pointer = runtime.allocate(TRANSFER_BYTES)
    runtime.copy_to_device(pointer, source)
    _ = runtime.host_memory.register(target)
    stream = create_ordered_dtoh_stream(runtime)
    stream.submit_copy_from_device(target, pointer)

    runtime.close()

    assert _values(target) == _values(source)
    assert stream.pending_copies == 0
    stream.close()


def test_cuda_ordered_dtoh_stream_identity_is_stable() -> None:
    """Evidence can bind the exact reviewed transfer lifetime policy."""
    assert cuda_ordered_dtoh_stream_id() == ORDERED_DTOH_STREAM_ID
