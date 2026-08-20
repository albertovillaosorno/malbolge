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
#   - CUDA-event phase attribution for streamed primitive ticket transfers.
# - Must-Not:
#   - Treat event phases as overlap proof or grant semantic authority.
# - Allows:
#   - Inputs: fake Driver events/copies and exact prepared rotate tickets.
#   - Outputs: ordered upload/kernel/download phases and cleanup evidence.
#   - Side effects: in-memory fake logs or scoped live CUDA resources.
# - Split-When:
#   - Split when phase-derived admission becomes a product policy.
# - Merge-When:
#   - Merge when another test owns this exact transfer timeline contract.
# - Summary:
#   - CUDA-event streamed ticket phase timeline regressions.
# - Description:
#   - Proves contiguous phase markers, cleanup, and live exactness.
# - Usage:
#   - Runs with optimizer tests and skips only live work without CUDA.
# - Defaults:
#   - Phase attribution remains diagnostic and opt-in.
#

"""CUDA-event phase attribution for streamed exact primitive tickets."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import final
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import cuda_independent_ticket_transfer_timeline_id
from accelerator.cuda.runtime import CUDA_EVENT_DEFAULT
from accelerator.cuda.runtime import CudaDeviceToHostTransfer
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.cuda.runtime import CudaHostToDeviceTransfer
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFactory
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFunctions
from accelerator.cuda.runtime import CudaIndependentKernelTimelineFunctions
from accelerator.cuda.runtime import (
    CudaIndependentTicketTransferTimelineFactory,
)
from accelerator.cuda.runtime import CudaIndependentTransferSubmission
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_primitive_batch
import pytest

if TYPE_CHECKING:
    from accelerator.cuda.runtime import (
        CudaIndependentTicketTransferTimelineSample,
    )

CUDA_SUCCESS = 0
LAUNCH_FAILURE = 7
EXPECTED_ID = "cuda-independent-stream-ticket-transfer-timeline-v1"
STREAM_HANDLE = 101
KERNEL_ADDRESS = 303
INPUT_POINTER = 401
OUTPUT_POINTER = 402
ORIGIN_EVENT = 1_000
START_EVENT = 1_001
UPLOAD_END_EVENT = 1_002
KERNEL_END_EVENT = 1_003
END_EVENT = 1_004
WORD_BYTES = 4


@final
class _FakeEventDriver:
    """Record deterministic event creation, timing, and destruction."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.destroyed: list[int] = []
        self.flags: list[int] = []
        self.next_events = [
            ORIGIN_EVENT,
            START_EVENT,
            UPLOAD_END_EVENT,
            KERNEL_END_EVENT,
            END_EVENT,
        ]
        self.records: list[tuple[int, int | None]] = []
        self.synchronized: list[int] = []

    def create(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Assign one deterministic event handle.

        Returns:
            CUDA success.

        """
        event = self.next_events.pop(0)
        self.flags.append(flags)
        self.calls.append(f"create-event:{event}")
        _set_handle(pointer, event)
        return CUDA_SUCCESS

    def destroy(self, event: ctypes.c_void_p) -> int:
        """Record exact event destruction.

        Returns:
            CUDA success.

        """
        value = _handle_value(event)
        self.destroyed.append(value)
        self.calls.append(f"destroy-event:{value}")
        return CUDA_SUCCESS

    @staticmethod
    def elapsed(
        pointer: ctypes.c_void_p,
        start: ctypes.c_void_p,
        end: ctypes.c_void_p,
    ) -> int:
        """Write deterministic elapsed milliseconds.

        Returns:
            CUDA success.

        """
        values = {
            (ORIGIN_EVENT, START_EVENT): 1.0,
            (ORIGIN_EVENT, UPLOAD_END_EVENT): 3.0,
            (ORIGIN_EVENT, KERNEL_END_EVENT): 7.0,
            (ORIGIN_EVENT, END_EVENT): 9.0,
            (START_EVENT, UPLOAD_END_EVENT): 2.0,
            (UPLOAD_END_EVENT, KERNEL_END_EVENT): 4.0,
            (KERNEL_END_EVENT, END_EVENT): 2.0,
            (START_EVENT, END_EVENT): 8.0,
        }
        target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_float))
        target[0] = ctypes.c_float(
            values[_handle_value(start), _handle_value(end)]
        )
        return CUDA_SUCCESS

    def record(
        self,
        event: ctypes.c_void_p,
        stream: ctypes.c_void_p | None,
    ) -> int:
        """Record one event at one exact stream position.

        Returns:
            CUDA success.

        """
        event_value = _handle_value(event)
        stream_value = None if stream is None else _handle_value(stream)
        self.records.append((event_value, stream_value))
        self.calls.append(f"record:{event_value}:{stream_value}")
        return CUDA_SUCCESS

    def synchronize(self, event: ctypes.c_void_p) -> int:
        """Record origin synchronization.

        Returns:
            CUDA success.

        """
        value = _handle_value(event)
        self.synchronized.append(value)
        self.calls.append(f"sync-event:{value}")
        return CUDA_SUCCESS


@final
class _FakeStreamDriver:
    """Record same-stream copies, kernel launch, and teardown."""

    def __init__(
        self,
        calls: list[str],
        *,
        launch_status: int = CUDA_SUCCESS,
    ) -> None:
        self.calls = calls
        self.destroyed: list[int] = []
        self.launch_status = launch_status
        self.synchronized: list[int] = []

    def copy_from_device(self, *arguments: object) -> int:
        """Record one D-to-H enqueue.

        Returns:
            CUDA success.

        """
        self.calls.append(f"dtoh:{_stream_argument(arguments, 3)}")
        return CUDA_SUCCESS

    def copy_to_device(self, *arguments: object) -> int:
        """Record one H-to-D enqueue.

        Returns:
            CUDA success.

        """
        self.calls.append(f"htod:{_stream_argument(arguments, 3)}")
        return CUDA_SUCCESS

    def create(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Create one deterministic nonblocking stream.

        Returns:
            CUDA success.

        """
        self.calls.append(f"create-stream:{flags}")
        _set_handle(pointer, STREAM_HANDLE)
        return CUDA_SUCCESS

    def destroy(self, stream: ctypes.c_void_p) -> int:
        """Record exact stream destruction.

        Returns:
            CUDA success.

        """
        value = _handle_value(stream)
        self.destroyed.append(value)
        self.calls.append(f"destroy-stream:{value}")
        return CUDA_SUCCESS

    def launch(self, *arguments: object) -> int:
        """Record one kernel enqueue.

        Returns:
            Configured launch status.

        """
        self.calls.append(f"kernel:{_stream_argument(arguments, 8)}")
        return self.launch_status

    def synchronize(self, stream: ctypes.c_void_p) -> int:
        """Record stream-specific synchronization.

        Returns:
            CUDA success.

        """
        value = _handle_value(stream)
        self.synchronized.append(value)
        self.calls.append(f"sync-stream:{value}")
        return CUDA_SUCCESS


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _register_success(*arguments: object) -> int:
    """Accept one fake host registration.

    Returns:
        CUDA success.

    """
    del arguments
    return CUDA_SUCCESS


def _handle_value(handle: ctypes.c_void_p) -> int:
    value = handle.value
    if value is None:
        message = "fake CUDA handle is null"
        raise AssertionError(message)
    return value


def _set_handle(pointer: ctypes.c_void_p, value: int) -> None:
    target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))
    target[0] = ctypes.c_void_p(value)


def _stream_argument(arguments: tuple[object, ...], index: int) -> int:
    stream = arguments[index]
    if not isinstance(stream, ctypes.c_void_p):
        message = "fake CUDA operation received a non-stream handle"
        raise TypeError(message)
    return _handle_value(stream)


@dataclass(frozen=True, slots=True)
class _FakeRuntime:
    calls: list[str]
    events: _FakeEventDriver
    launches: CudaIndependentKernelLaunchFactory
    registry: CudaHostMemoryRegistry
    streams: _FakeStreamDriver
    timelines: CudaIndependentTicketTransferTimelineFactory


def _factories(
    *,
    launch_status: int = CUDA_SUCCESS,
) -> _FakeRuntime:
    calls: list[str] = []
    events = _FakeEventDriver(calls)
    streams = _FakeStreamDriver(calls, launch_status=launch_status)
    registry = CudaHostMemoryRegistry(
        lambda: None,
        _register_success,
        _register_success,
    )
    launches = CudaIndependentKernelLaunchFactory(
        CudaIndependentKernelLaunchFunctions(
            copy_from_device_fn=streams.copy_from_device,
            copy_to_device_fn=streams.copy_to_device,
            create_fn=streams.create,
            destroy_fn=streams.destroy,
            ensure_open=lambda: None,
            host_memory=registry,
            launch_fn=streams.launch,
            synchronize_fn=streams.synchronize,
        )
    )
    timelines = CudaIndependentTicketTransferTimelineFactory(
        CudaIndependentKernelTimelineFunctions(
            create_fn=events.create,
            destroy_fn=events.destroy,
            elapsed_fn=events.elapsed,
            ensure_open=lambda: None,
            record_fn=events.record,
            synchronize_fn=events.synchronize,
        ),
        launches,
    )
    return _FakeRuntime(
        calls=calls,
        events=events,
        launches=launches,
        registry=registry,
        streams=streams,
        timelines=timelines,
    )


def _submission(
    registry: CudaHostMemoryRegistry,
) -> tuple[CudaIndependentTransferSubmission, int, int]:
    host_input = (ctypes.c_uint32 * 2)(7, 11)
    host_output = (ctypes.c_uint32 * 2)()
    input_address = registry.register(host_input)
    output_address = registry.register(host_output)
    submission = CudaIndependentTransferSubmission(
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
    )
    return submission, input_address, output_address


def _packed(values: tuple[int, ...]) -> bytes:
    return b"".join(value.to_bytes(WORD_BYTES, "little") for value in values)


def _assert_phase_calls(calls: list[str]) -> None:
    phase_calls = [
        f"record:{START_EVENT}:{STREAM_HANDLE}",
        f"htod:{STREAM_HANDLE}",
        f"record:{UPLOAD_END_EVENT}:{STREAM_HANDLE}",
        f"kernel:{STREAM_HANDLE}",
        f"record:{KERNEL_END_EVENT}:{STREAM_HANDLE}",
        f"dtoh:{STREAM_HANDLE}",
        f"record:{END_EVENT}:{STREAM_HANDLE}",
        f"sync-stream:{STREAM_HANDLE}",
    ]
    assert [call for call in calls if call in phase_calls] == phase_calls


def _assert_phase_sample(
    sample: CudaIndependentTicketTransferTimelineSample,
) -> None:
    assert sample.submission_index == 0
    assert sample.start_ms == pytest.approx(1.0)
    assert sample.upload_end_ms == pytest.approx(3.0)
    assert sample.kernel_end_ms == pytest.approx(7.0)
    assert sample.end_ms == pytest.approx(9.0)
    assert sample.upload_duration_ms == pytest.approx(2.0)
    assert sample.kernel_duration_ms == pytest.approx(4.0)
    assert sample.download_duration_ms == pytest.approx(2.0)
    assert sample.total_duration_ms == pytest.approx(8.0)


def _assert_success_cleanup(fake: _FakeRuntime) -> None:
    assert fake.events.flags == [CUDA_EVENT_DEFAULT] * 5
    assert fake.events.synchronized == [ORIGIN_EVENT]
    assert fake.events.destroyed == [
        END_EVENT,
        KERNEL_END_EVENT,
        UPLOAD_END_EVENT,
        START_EVENT,
        ORIGIN_EVENT,
    ]
    assert fake.streams.destroyed == [STREAM_HANDLE]
    assert fake.launches.release_failure() is None
    assert fake.timelines.release_failure() is None


def test_ticket_transfer_timeline_identity_is_stable() -> None:
    """Evidence names the exact four-marker phase timeline."""
    assert cuda_independent_ticket_transfer_timeline_id() == EXPECTED_ID


def test_phase_timeline_records_contiguous_same_stream_work() -> None:
    """Four markers delimit upload, kernel, and download in exact order."""
    fake = _factories()
    timeline = fake.timelines.create()
    submission, input_address, output_address = _submission(fake.registry)
    launch = timeline.submit(submission)

    with pytest.raises(AcceleratorExecutionError, match="active launches"):
        _ = timeline.samples()

    launch.close()
    (sample,) = timeline.samples()
    _assert_phase_calls(fake.calls)
    _assert_phase_sample(sample)
    fake.registry.unregister(input_address)
    fake.registry.unregister(output_address)
    timeline.close()
    _assert_success_cleanup(fake)


def test_kernel_failure_discards_phases_and_releases_every_lifetime() -> None:
    """A rejected kernel drains prior upload work and destroys four events."""
    fake = _factories(launch_status=LAUNCH_FAILURE)
    timeline = fake.timelines.create()
    submission, input_address, output_address = _submission(fake.registry)

    with pytest.raises(AcceleratorExecutionError, match="cuLaunchKernel"):
        _ = timeline.submit(submission)

    assert timeline.samples() == ()
    fake.registry.unregister(input_address)
    fake.registry.unregister(output_address)
    assert fake.streams.synchronized == [STREAM_HANDLE]
    assert fake.streams.destroyed == [STREAM_HANDLE]
    assert fake.events.destroyed == [
        END_EVENT,
        KERNEL_END_EVENT,
        UPLOAD_END_EVENT,
        START_EVENT,
    ]
    timeline.close()
    assert fake.events.destroyed[-1] == ORIGIN_EVENT
    assert fake.launches.release_failure() is None
    assert fake.timelines.release_failure() is None


def test_live_streamed_ticket_publishes_exact_phase_attribution() -> None:
    """Live streamed output stays CPU-equal with monotonic phase markers."""
    values = tuple(range(4_096))
    prepared = prepare_primitive_batch(
        PrimitiveBatch(
            accumulators=(),
            data=values,
            kind=PrimitiveKind.ROTATE,
        )
    )
    expected = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    with _cuda() as cuda:
        timeline = cuda.ticket_transfer_timelines.create()
        observed = timeline.submit(prepared).wait()
        (sample,) = timeline.samples()
        timeline.close()

    assert observed.words_u32le == _packed(expected.values)
    assert sample.submission_index == 0
    assert 0.0 <= sample.start_ms <= sample.upload_end_ms
    assert sample.upload_end_ms <= sample.kernel_end_ms <= sample.end_ms
    assert sample.upload_duration_ms >= 0.0
    assert sample.kernel_duration_ms >= 0.0
    assert sample.download_duration_ms >= 0.0
    phase_sum = (
        sample.upload_duration_ms
        + sample.kernel_duration_ms
        + sample.download_duration_ms
    )
    assert sample.total_duration_ms == pytest.approx(phase_sum, abs=0.01)
