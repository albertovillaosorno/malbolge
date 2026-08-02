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
#   - CUDA-event interval attribution for isolated primitive ticket streams.
# - Must-Not:
#   - Treat event duration as pure kernel time or grant semantic authority.
# - Allows:
#   - Inputs: fake Driver events and exact prepared rotate tickets.
#   - Outputs: ordered intervals, exact bytes, and cleanup evidence.
#   - Side effects: in-memory fake call logs or scoped live CUDA resources.
# - Split-When:
#   - Split when asynchronous copies or event-derived admission becomes a
#     product policy.
# - Merge-When:
#   - Merge when another test owns this independent ticket timeline contract.
# - Summary:
#   - CUDA-event independent ticket timeline regressions.
# - Description:
#   - Proves event origin, per-stream intervals, cleanup, and live exactness.
# - Usage:
#   - Runs with optimizer tests and skips only the live route without CUDA.
# - Defaults:
#   - Event intervals stay diagnostic; publication remains CPU-reference
#     checked.
#

"""CUDA-event interval attribution for independent primitive tickets."""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING
from typing import final
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import cuda_independent_kernel_timeline_id
from accelerator.cuda.runtime import CUDA_EVENT_DEFAULT
from accelerator.cuda.runtime import CUDA_STREAM_NON_BLOCKING
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFactory
from accelerator.cuda.runtime import CudaIndependentKernelLaunchFunctions
from accelerator.cuda.runtime import CudaIndependentKernelTimelineFactory
from accelerator.cuda.runtime import CudaIndependentKernelTimelineFunctions
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_primitive_batch
import pytest

if TYPE_CHECKING:
    from accelerator.cuda.runtime import CudaIndependentKernelTimelineSample

EXPECTED_ID = "cuda-independent-stream-kernel-timeline-v1"
KERNEL_ADDRESS = 303
FIRST_STREAM = 101
SECOND_STREAM = 202
ORIGIN_EVENT = 1_000
FIRST_START = 1_001
FIRST_END = 1_002
SECOND_START = 1_003
SECOND_END = 1_004
CUDA_SUCCESS = 0
LAUNCH_FAILURE = 7
WORD_BYTES = 4
EXPECTED_DURATION_MS = 4.0


@final
class _FakeDriver:
    """Record deterministic stream/event calls and elapsed intervals."""

    def __init__(self, *, launch_status: int = CUDA_SUCCESS) -> None:
        self.destroyed_events: list[int] = []
        self.destroyed_streams: list[int] = []
        self.event_flags: list[int] = []
        self.event_records: list[tuple[int, int | None]] = []
        self.event_sync: list[int] = []
        self.launch_status = launch_status
        self.launched: list[int] = []
        self.next_events = [
            ORIGIN_EVENT,
            FIRST_START,
            FIRST_END,
            SECOND_START,
            SECOND_END,
        ]
        self.next_streams = [FIRST_STREAM, SECOND_STREAM]
        self.stream_flags: list[int] = []
        self.stream_sync: list[int] = []

    def create_event(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Assign one deterministic event handle.

        Returns:
            CUDA success.

        """
        self.event_flags.append(flags)
        _set_handle(pointer, self.next_events.pop(0))
        return CUDA_SUCCESS

    def create_stream(self, pointer: ctypes.c_void_p, flags: int) -> int:
        """Assign one deterministic stream handle.

        Returns:
            CUDA success.

        """
        self.stream_flags.append(flags)
        _set_handle(pointer, self.next_streams.pop(0))
        return CUDA_SUCCESS

    def destroy_event(self, event: ctypes.c_void_p) -> int:
        """Record event destruction.

        Returns:
            CUDA success.

        """
        self.destroyed_events.append(_handle_value(event))
        return CUDA_SUCCESS

    def destroy_stream(self, stream: ctypes.c_void_p) -> int:
        """Record stream destruction.

        Returns:
            CUDA success.

        """
        self.destroyed_streams.append(_handle_value(stream))
        return CUDA_SUCCESS

    @staticmethod
    def elapsed(
        pointer: ctypes.c_void_p,
        start: ctypes.c_void_p,
        end: ctypes.c_void_p,
    ) -> int:
        """Write deterministic milliseconds for one event pair.

        Returns:
            CUDA success.

        """
        values = {
            (ORIGIN_EVENT, FIRST_START): 1.0,
            (ORIGIN_EVENT, FIRST_END): 5.0,
            (FIRST_START, FIRST_END): 4.0,
            (ORIGIN_EVENT, SECOND_START): 2.0,
            (ORIGIN_EVENT, SECOND_END): 6.0,
            (SECOND_START, SECOND_END): 4.0,
        }
        key = (_handle_value(start), _handle_value(end))
        target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_float))
        target[0] = ctypes.c_float(values[key])
        return CUDA_SUCCESS

    def launch(self, *arguments: object) -> int:
        """Record the stream supplied to the kernel launch.

        Returns:
            Configured launch status.

        Raises:
            TypeError: If the launch stream has the wrong representation.

        """
        stream = arguments[8]
        if not isinstance(stream, ctypes.c_void_p):
            message = "fake timeline launch received a non-stream handle"
            raise TypeError(message)
        self.launched.append(_handle_value(stream))
        return self.launch_status

    def record_event(
        self,
        event: ctypes.c_void_p,
        stream: ctypes.c_void_p | None,
    ) -> int:
        """Record one event/stream association.

        Returns:
            CUDA success.

        """
        stream_value = None if stream is None else _handle_value(stream)
        self.event_records.append((_handle_value(event), stream_value))
        return CUDA_SUCCESS

    def synchronize_event(self, event: ctypes.c_void_p) -> int:
        """Record origin event synchronization.

        Returns:
            CUDA success.

        """
        self.event_sync.append(_handle_value(event))
        return CUDA_SUCCESS

    def synchronize_stream(self, stream: ctypes.c_void_p) -> int:
        """Record stream-specific synchronization.

        Returns:
            CUDA success.

        """
        self.stream_sync.append(_handle_value(stream))
        return CUDA_SUCCESS


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _factories(
    fake: _FakeDriver,
) -> tuple[
    CudaIndependentKernelLaunchFactory, CudaIndependentKernelTimelineFactory
]:
    launches = CudaIndependentKernelLaunchFactory(
        CudaIndependentKernelLaunchFunctions(
            copy_from_device_fn=_copy_success,
            copy_to_device_fn=_copy_success,
            create_fn=fake.create_stream,
            destroy_fn=fake.destroy_stream,
            ensure_open=lambda: None,
            host_memory=CudaHostMemoryRegistry(
                lambda: None,
                _copy_success,
                _copy_success,
            ),
            launch_fn=fake.launch,
            synchronize_fn=fake.synchronize_stream,
        )
    )
    timelines = CudaIndependentKernelTimelineFactory(
        CudaIndependentKernelTimelineFunctions(
            create_fn=fake.create_event,
            destroy_fn=fake.destroy_event,
            elapsed_fn=fake.elapsed,
            ensure_open=lambda: None,
            record_fn=fake.record_event,
            synchronize_fn=fake.synchronize_event,
        ),
        launches,
    )
    return launches, timelines


def _copy_success(*arguments: object) -> int:
    """Return CUDA success for transfer functions unused in this suite.

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


def _packed(values: tuple[int, ...]) -> bytes:
    return b"".join(value.to_bytes(WORD_BYTES, "little") for value in values)


def _set_handle(pointer: ctypes.c_void_p, value: int) -> None:
    target = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))
    target[0] = ctypes.c_void_p(value)


def _assert_fake_submission_calls(fake: _FakeDriver) -> None:
    assert fake.event_flags == [CUDA_EVENT_DEFAULT] * 5
    assert fake.stream_flags == [
        CUDA_STREAM_NON_BLOCKING,
        CUDA_STREAM_NON_BLOCKING,
    ]
    assert fake.event_records == [
        (ORIGIN_EVENT, None),
        (FIRST_START, FIRST_STREAM),
        (FIRST_END, FIRST_STREAM),
        (SECOND_START, SECOND_STREAM),
        (SECOND_END, SECOND_STREAM),
    ]
    assert fake.event_sync == [ORIGIN_EVENT]
    assert fake.launched == [FIRST_STREAM, SECOND_STREAM]
    assert fake.stream_sync == [SECOND_STREAM, FIRST_STREAM]


def _assert_overlap_samples(
    samples: tuple[CudaIndependentKernelTimelineSample, ...],
) -> None:
    first = samples[0]
    second = samples[1]
    assert first.submission_index == 0
    assert second.submission_index == 1
    assert (first.start_ms, first.end_ms) == pytest.approx((1.0, 5.0))
    assert (second.start_ms, second.end_ms) == pytest.approx((2.0, 6.0))
    assert first.duration_ms == pytest.approx(EXPECTED_DURATION_MS)
    assert second.duration_ms == pytest.approx(EXPECTED_DURATION_MS)
    assert first.end_ms > second.start_ms
    assert second.end_ms > first.start_ms


def _assert_fake_cleanup(fake: _FakeDriver) -> None:
    assert fake.destroyed_events == [
        SECOND_END,
        SECOND_START,
        FIRST_END,
        FIRST_START,
        ORIGIN_EVENT,
    ]
    assert fake.destroyed_streams == [SECOND_STREAM, FIRST_STREAM]


def test_independent_kernel_timeline_identity_is_stable() -> None:
    """Evidence names the exact CUDA-event timeline contract."""
    assert cuda_independent_kernel_timeline_id() == EXPECTED_ID


def test_reverse_close_publishes_submission_order_and_overlap() -> None:
    """Reverse cleanup retains submission order and overlapping intervals."""
    fake = _FakeDriver()
    launches, timelines = _factories(fake)
    timeline = timelines.create()
    first = timeline.submit(ctypes.c_void_p(KERNEL_ADDRESS), (11, 22), 257)
    second = timeline.submit(ctypes.c_void_p(KERNEL_ADDRESS), (33, 44), 257)

    with pytest.raises(AcceleratorExecutionError, match="active launches"):
        _ = timeline.samples()

    second.close()
    first.close()
    samples = timeline.samples()

    _assert_fake_submission_calls(fake)
    _assert_overlap_samples(samples)

    timeline.close()
    _assert_fake_cleanup(fake)
    assert launches.release_failure() is None
    assert timelines.release_failure() is None


def test_launch_failure_releases_profile_events_and_stream() -> None:
    """A rejected profiled launch leaves no active event or stream lifetime."""
    fake = _FakeDriver(launch_status=LAUNCH_FAILURE)
    launches, timelines = _factories(fake)
    timeline = timelines.create()

    with pytest.raises(AcceleratorExecutionError, match="cuLaunchKernel"):
        _ = timeline.submit(ctypes.c_void_p(KERNEL_ADDRESS), (11, 22), 257)

    assert timeline.samples() == ()
    assert fake.destroyed_events == [FIRST_END, FIRST_START]
    assert fake.destroyed_streams == [FIRST_STREAM]
    timeline.close()
    assert fake.destroyed_events[-1] == ORIGIN_EVENT
    assert launches.release_failure() is None
    assert timelines.release_failure() is None


def test_live_profiled_tickets_preserve_exact_output() -> None:
    """Live reverse-wait tickets publish valid intervals and CPU-equal bytes."""
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
        timeline = cuda.ticket_timelines.create()
        first = timeline.submit(prepared)
        second = timeline.submit(prepared)
        observed_second = second.wait()
        observed_first = first.wait()
        samples = timeline.samples()
        timeline.close()

    expected_bytes = _packed(expected.values)
    assert observed_first.words_u32le == expected_bytes
    assert observed_second.words_u32le == expected_bytes
    assert tuple(sample.submission_index for sample in samples) == (0, 1)
    for sample in samples:
        assert sample.start_ms >= 0.0
        assert sample.end_ms >= sample.start_ms
        assert sample.duration_ms >= 0.0
