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
#   - Live CUDA evidence that resident execution is not fixed to known profiles.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Live CUDA evidence that resident execution is not fixed to known profiles."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Final
from typing import TYPE_CHECKING
from typing import cast
from unittest import SkipTest

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.cuda.profile_run import CudaProfileSnapshotOverlapWorkspace
from accelerator.cuda.profile_run import CudaProfileSnapshotStreamWorkspace
from accelerator.cuda.profile_run import CudaProfileSnapshotWorkspace
from accelerator.cuda.profile_run import ProfileSnapshotOverlapSummary
from accelerator.cuda.profile_run import profile_snapshot_host_registration_id
from accelerator.cuda.profile_run import profile_snapshot_overlap_workspace_id
from accelerator.cuda.profile_run import profile_snapshot_stream_workspace_id
from accelerator.cuda.profile_run import profile_snapshot_workspace_id
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda.profile_run import CudaProfileRunSession
    from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration
    from accelerator.cuda.profile_run import ProfileSnapshotWindow
    from accelerator.profile_run import ProfileRunResult

SYNTHETIC_TRITS: Final = 5
SYNTHETIC_WORDS: Final = 243
INITIAL_ACCUMULATOR: Final = 7
EXPECTED_DATA_POINTER: Final = 2
SESSION_BATCH_SIZE: Final = 2
STREAM_BATCH_SIZE: Final = 3
SESSION_RUNS: Final = 3
SNAPSHOT_WORKSPACE_ID: Final = "caller-owned-independent-u32-arrays-v1"
SNAPSHOT_HOST_REGISTRATION_ID: Final = "bounded-all-or-pageable-u32-arrays-v1"
SNAPSHOT_STREAM_WORKSPACE_ID: Final = "caller-owned-windowed-u32-arrays-v1"
SNAPSHOT_OVERLAP_WORKSPACE_ID: Final = (
    "caller-owned-double-window-overlap-u32-arrays-v1"
)
_SNAPSHOT_OVERLAP_SINGLE_BUFFER: Final = "single-buffer-budget"
_HOST_REGISTRATION_DISABLED: Final = "disabled"
OVERLAP_REQUEST_COUNT: Final = 3
OVERLAP_BANK_ITEMS: Final = 2
OVERLAP_BUFFER_COUNT: Final = 2
OVERLAP_WINDOWS: Final = 2
OVERLAP_PREFETCHED_WINDOWS: Final = 1
OVERLAP_REGISTERED_ARRAYS: Final = 4
_DEVICE_WORD_BYTES: Final = 4
_HOST_REGISTRATION_BUDGET_EXCEEDED: Final = "budget-exceeded"
_HOST_REGISTRATION_DRIVER_REJECTED: Final = "driver-rejected"
NO_OP_CELL: Final = 33
ENCRYPTED_NO_OP_CELL: Final = 53
GEOMETRY = ProfileRunGeometry(
    eof_word=SYNTHETIC_WORDS - 1,
    input_instruction=ord("/"),
    memory_words=SYNTHETIC_WORDS,
    output_instruction=ord("<"),
    word_modulus=SYNTHETIC_WORDS,
    word_trits=SYNTHETIC_TRITS,
)


def _corrupt_attribute(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


def _cuda() -> CudaProfileRunAdapter:
    try:
        return CudaProfileRunAdapter(GEOMETRY)
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _request() -> ProfileRunRequest:
    memory = array("I", [0]) * SYNTHETIC_WORDS
    memory[0] = NO_OP_CELL
    return ProfileRunRequest(
        accumulator=INITIAL_ACCUMULATOR,
        code_pointer=0,
        data_pointer=1,
        input_bytes=(),
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def test_cuda_resident_kernel_executes_synthetic_five_trit_geometry() -> None:
    """Execute a valid NVRTC profile distinct from 10/14 trits."""
    request = _request()

    with _cuda() as adapter:
        (result,) = adapter.evaluate((request,))

    assert result.accumulator == INITIAL_ACCUMULATOR
    assert result.code_pointer == 1
    assert isinstance(request.memory, array)
    assert result.memory is not request.memory
    assert request.memory[0] == NO_OP_CELL
    assert result.data_pointer == EXPECTED_DATA_POINTER
    assert result.error is RunError.NONE
    assert result.input_consumed == 0
    assert result.memory[0] == ENCRYPTED_NO_OP_CELL
    assert isinstance(request.memory, array)
    assert result.memory[1:] == request.memory[1:]
    assert result.output_bytes == ()
    assert result.status is RunStatus.BUDGET_EXHAUSTED
    assert result.steps == 1
    assert result.termination is StepTermination.NONE


def test_cuda_profile_diagnostics_preserve_exact_results() -> None:
    """Phase instrumentation must not change the scalable execution result."""
    request = _request()
    with _cuda() as adapter:
        expected = adapter.evaluate((request,))
        observed, profile = adapter.profile_evaluate((request,))

    assert observed == expected
    assert profile.chunks == 1
    assert profile.total_ns >= profile.validation_plan_ns
    assert profile.host_build_ns >= 0
    assert profile.kernel_ns >= 0
    assert profile.decode_ns >= 0


def test_cuda_shared_profile_memory_is_replicated_per_vm() -> None:
    """Initialize private device memories from one shared host image."""
    request = _request()
    with _cuda() as adapter:
        first, second = adapter.evaluate((request, request))

    assert first == second
    assert first.memory == second.memory
    first.memory[1] = 1
    assert second.memory[1] == 0


def _resident_session_request() -> ProfileRunRequest:
    memory = array("I", [0]) * SYNTHETIC_WORDS
    target_index = XLAT1.index(ord("+"))
    for code_pointer in range(SESSION_RUNS):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        memory[code_pointer] = 33 + encoded_index
    return ProfileRunRequest(
        accumulator=INITIAL_ACCUMULATOR,
        code_pointer=0,
        data_pointer=1,
        input_bytes=(),
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def _stream_requests() -> tuple[ProfileRunRequest, ProfileRunRequest]:
    running = _resident_session_request()
    halted = replace(running, termination=StepTermination.HALT)
    return running, halted


def _durable_result(result: ProfileRunResult) -> ProfileRunResult:
    return replace(result, memory=array("I", result.memory))


@dataclass(slots=True)
class _StreamCapture:
    workspace: CudaProfileSnapshotStreamWorkspace
    durable: list[ProfileRunResult] = field(default_factory=list)
    first_alias: ProfileRunResult | None = None
    first_memory: array[int] | None = None
    ranges: list[tuple[int, int]] = field(default_factory=list)

    def __call__(self, window: ProfileSnapshotWindow) -> None:
        self.ranges.append((window.start, window.stop))
        assert window.item_count == 1
        (result,) = window.results
        assert result.memory is self.workspace.memories[0]
        if self.first_alias is None:
            self.first_alias = result
            self.first_memory = array("I", result.memory)
        else:
            assert self.first_memory is not None
            assert self.first_alias.memory is result.memory
            assert self.first_alias.memory != self.first_memory
        self.durable.append(_durable_result(result))


@dataclass(slots=True)
class _OverlapCapture:
    durable: list[ProfileRunResult] = field(default_factory=list)
    memory_ids: list[tuple[int, ...]] = field(default_factory=list)
    ranges: list[tuple[int, int]] = field(default_factory=list)

    def __call__(self, window: ProfileSnapshotWindow) -> None:
        self.ranges.append((window.start, window.stop))
        self.memory_ids.append(
            tuple(id(result.memory) for result in window.results)
        )
        self.durable.extend(
            _durable_result(result) for result in window.results
        )


@dataclass(slots=True)
class _PrefetchRejector:
    session: CudaProfileRunSession
    workspace: CudaProfileSnapshotOverlapWorkspace

    def __call__(self, window: ProfileSnapshotWindow) -> None:
        del window
        with pytest.raises(
            AcceleratorExecutionError,
            match="snapshot stream is active",
        ):
            _ = self.session.snapshot()
        with pytest.raises(
            AcceleratorExecutionError,
            match="overlap workspace is active",
        ):
            self.workspace.close()
        message = "synthetic prefetched consumer failure"
        raise RuntimeError(message)


def _ignore_snapshot_window(window: ProfileSnapshotWindow) -> None:
    del window


def _assert_active_overlap(
    workspace: CudaProfileSnapshotOverlapWorkspace,
    summary: ProfileSnapshotOverlapSummary,
    retained_bytes: int,
) -> None:
    assert isinstance(summary, ProfileSnapshotOverlapSummary)
    capacity = workspace.capacity
    assert summary.items == OVERLAP_REQUEST_COUNT
    assert summary.windows == OVERLAP_WINDOWS
    assert summary.prefetched_windows == OVERLAP_PREFETCHED_WINDOWS
    assert workspace.admission.active
    assert workspace.admission.fallback_reason is None
    assert capacity.bank_items == OVERLAP_BANK_ITEMS
    assert capacity.buffer_count == OVERLAP_BUFFER_COUNT
    assert capacity.planned_windows == OVERLAP_WINDOWS
    assert capacity.retained_bytes == retained_bytes
    assert workspace.registration.active
    assert workspace.registration.registered_arrays == OVERLAP_REGISTERED_ARRAYS


def test_cuda_profile_session_matches_contiguous_execution() -> None:
    """Repeated resident segments preserve exact scalable VM state."""
    request = _resident_session_request()
    contiguous = replace(request, step_budget=SESSION_RUNS)
    with _cuda() as adapter:
        expected = adapter.evaluate((contiguous, contiguous))
        with adapter.open_session(
            (request, request), max_runs=SESSION_RUNS
        ) as session:
            for _ in range(SESSION_RUNS):
                session.advance()
            observations = session.observe()
            observed = session.snapshot()
            runs_executed = session.runs_executed

    expected_segmented = tuple(replace(result, steps=1) for result in expected)
    assert observed == expected_segmented
    assert runs_executed == SESSION_RUNS
    assert len(observations) == SESSION_BATCH_SIZE
    assert all(item.code_pointer == SESSION_RUNS for item in observations)
    assert all(item.steps == 1 for item in observations)
    assert all(
        item.status is RunStatus.BUDGET_EXHAUSTED for item in observations
    )


def test_cuda_profile_session_snapshot_phases_preserve_exact_results() -> None:
    """Snapshot profiling separates host allocation, transfers, and decode."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=SESSION_RUNS,
        ) as session,
    ):
        for _ in range(SESSION_RUNS):
            session.advance()
        expected = session.snapshot()
        observed, profile = session.profile_snapshot()

    assert observed == expected
    assert profile.chunks == 1
    components = (
        profile.host_memory_allocate_ns,
        profile.state_download_ns,
        profile.memory_download_ns,
        profile.output_download_ns,
        profile.decode_ns,
    )
    assert all(value >= 0 for value in components)
    assert profile.total_ns >= sum(components)


def test_cuda_profile_session_snapshots_are_independent_between_calls() -> None:
    """Ordinary snapshots never alias a prior snapshot memory array."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request,),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        first = session.snapshot()
        second = session.snapshot()

    assert first == second
    assert first[0].memory is not second[0].memory
    first[0].memory[0] = 0
    assert second[0].memory[0] != 0


def test_cuda_profile_snapshot_workspace_reuses_explicit_arrays() -> None:
    """Workspace snapshots alias and overwrite only caller-owned arrays."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace()
        first = workspace.snapshot()
        first_value = first[0].memory[0]
        workspace.memories[0][0] = 0
        second, profile = workspace.profile_snapshot()

    assert first == expected
    assert second == expected
    assert all(
        result.memory is workspace.memories[index]
        for index, result in enumerate(second)
    )
    assert first[0].memory is second[0].memory
    assert first[0].memory[0] == first_value
    assert profile.host_memory_allocate_ns == 0
    assert profile.total_ns >= (
        profile.state_download_ns
        + profile.memory_download_ns
        + profile.output_download_ns
        + profile.decode_ns
    )


def test_cuda_profile_snapshot_workspace_registers_within_budget() -> None:
    """One stable workspace is page-locked and released explicitly."""
    request = _resident_session_request()
    expected_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=expected_bytes,
        )
        registration = workspace.registration
        with pytest.raises(
            BufferError,
            match=r"cannot resize.*exporting buffers",
        ):
            workspace.memories[0].append(0)
        observed = workspace.snapshot()
        workspace.close()
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError,
            match="workspace is closed",
        ):
            _ = workspace.snapshot()

    assert observed == expected
    assert registration.active
    assert registration.budget_bytes == expected_bytes
    assert registration.fallback_reason is None
    assert registration.registered_arrays == 1
    assert registration.registered_bytes == expected_bytes
    assert registration.requested_bytes == expected_bytes


def test_cuda_profile_snapshot_workspace_falls_back_for_budget() -> None:
    """An insufficient explicit budget preserves the pageable contract."""
    request = _resident_session_request()
    requested_bytes = SESSION_BATCH_SIZE * SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=requested_bytes - 1,
        )
        registration = workspace.registration
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        observed = workspace.snapshot()

    assert observed == expected
    assert not registration.active
    assert registration.fallback_reason == _HOST_REGISTRATION_BUDGET_EXCEEDED
    assert registration.registered_arrays == 0
    assert registration.registered_bytes == 0
    assert registration.requested_bytes == requested_bytes


def _measure_driver_rejection_fallback(
    monkeypatch: pytest.MonkeyPatch,
    request: ProfileRunRequest,
    requested_bytes: int,
) -> tuple[
    tuple[object, ...],
    tuple[object, ...],
    ProfileSnapshotHostRegistration,
    int,
]:
    original = cast("Callable[..., int]", CudaHostMemoryRegistry.register)
    calls = 0

    def reject_second(registry: object, host: object) -> int:
        nonlocal calls
        calls += 1
        if calls == SESSION_BATCH_SIZE:
            message = "synthetic CUDA host registration rejection"
            raise AcceleratorExecutionError(message)
        return original(registry, host)

    monkeypatch.setattr(CudaHostMemoryRegistry, "register", reject_second)
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=requested_bytes,
        )
        registration = workspace.registration
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        observed = workspace.snapshot()
    return expected, observed, registration, calls


def test_cuda_profile_snapshot_workspace_rolls_back_driver_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later registration rejection releases earlier page locks."""
    requested_bytes = SESSION_BATCH_SIZE * SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    measured = _measure_driver_rejection_fallback(
        monkeypatch,
        _resident_session_request(),
        requested_bytes,
    )
    expected, observed, registration, calls = measured

    assert calls == SESSION_BATCH_SIZE
    assert observed == expected
    assert not registration.active
    assert registration.fallback_reason == _HOST_REGISTRATION_DRIVER_REJECTED
    assert registration.registered_arrays == 0
    assert registration.registered_bytes == 0


def test_cuda_profile_snapshot_workspace_rejects_invalid_budget() -> None:
    """Registration budgets require exact nonnegative integer authority."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        for budget in (-1, True):
            with pytest.raises(
                AcceleratorExecutionError,
                match="nonnegative integer",
            ):
                _ = session.allocate_snapshot_workspace(
                    host_registration_budget_bytes=budget,
                )


def test_cuda_profile_snapshot_session_close_releases_registration() -> None:
    """Session close releases page locks before closed-session errors."""
    request = _resident_session_request()
    expected_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with _cuda() as adapter:
        session = adapter.open_session((request,), max_runs=1)
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=expected_bytes,
        )
        assert workspace.registration.active
        session.close()
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError,
            match="session is closed",
        ):
            _ = workspace.snapshot()


def test_cuda_profile_snapshot_overlap_prefetches_exact_banks() -> None:
    """Two registered banks prefetch exact partial final results."""
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    retained_bytes = OVERLAP_REGISTERED_ARRAYS * memory_bytes
    capture = _OverlapCapture()
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=retained_bytes,
            host_registration_budget_bytes=retained_bytes,
        )
        summary = workspace.stream_snapshot(capture)

    assert tuple(capture.durable) == expected
    assert capture.ranges == [(0, OVERLAP_BANK_ITEMS), (2, 3)]
    assert capture.memory_ids == [
        tuple(id(memory) for memory in workspace.memory_banks[0]),
        (id(workspace.memory_banks[1][0]),),
    ]
    _assert_active_overlap(workspace, summary, retained_bytes)
    assert isinstance(workspace, CudaProfileSnapshotOverlapWorkspace)
    assert (
        profile_snapshot_overlap_workspace_id() == SNAPSHOT_OVERLAP_WORKSPACE_ID
    )


def test_cuda_profile_snapshot_overlap_fallback_without_registration() -> None:
    """Disabled registration preserves exact synchronous callback delivery."""
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    durable: list[ProfileRunResult] = []
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=4 * memory_bytes,
        )

        def consume(window: ProfileSnapshotWindow) -> None:
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(consume)

    assert tuple(durable) == expected
    assert not workspace.admission.active
    assert workspace.admission.fallback_reason == _HOST_REGISTRATION_DISABLED
    assert not workspace.registration.active
    assert summary.prefetched_windows == 0
    assert summary.windows == OVERLAP_WINDOWS


def test_cuda_profile_snapshot_overlap_falls_back_to_one_bank_budget() -> None:
    """A one-memory budget remains usable through exact synchronous windows."""
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    durable: list[ProfileRunResult] = []
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=memory_bytes,
            host_registration_budget_bytes=memory_bytes,
        )

        def consume(window: ProfileSnapshotWindow) -> None:
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(consume)

    assert tuple(durable) == expected
    assert workspace.capacity.buffer_count == 1
    assert workspace.capacity.bank_items == 1
    assert (
        workspace.admission.fallback_reason == _SNAPSHOT_OVERLAP_SINGLE_BUFFER
    )
    assert workspace.registration.active
    assert summary.prefetched_windows == 0
    assert summary.windows == OVERLAP_REQUEST_COUNT


def test_cuda_profile_snapshot_overlap_falls_back_after_driver_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registration rejection rolls back and keeps synchronous exactness."""
    original = cast("Callable[..., int]", CudaHostMemoryRegistry.register)

    def reject(registry: object, host: object) -> int:
        del registry, host
        message = "synthetic overlap registration rejection"
        raise AcceleratorExecutionError(message)

    monkeypatch.setattr(CudaHostMemoryRegistry, "register", reject)
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    durable: list[ProfileRunResult] = []
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=4 * memory_bytes,
            host_registration_budget_bytes=4 * memory_bytes,
        )
        monkeypatch.setattr(CudaHostMemoryRegistry, "register", original)

        def consume(window: ProfileSnapshotWindow) -> None:
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(consume)

    assert tuple(durable) == expected
    assert (
        workspace.admission.fallback_reason
        == _HOST_REGISTRATION_DRIVER_REJECTED
    )
    assert not workspace.registration.active
    assert summary.prefetched_windows == 0


def test_cuda_profile_snapshot_overlap_recovers_after_failure() -> None:
    """Consumer failure drains prefetch and releases both locks."""
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    retained_bytes = 4 * memory_bytes
    durable: list[ProfileRunResult] = []
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=retained_bytes,
            host_registration_budget_bytes=retained_bytes,
        )

        with pytest.raises(
            RuntimeError,
            match="synthetic prefetched consumer failure",
        ):
            _ = workspace.stream_snapshot(_PrefetchRejector(session, workspace))

        def consume(window: ProfileSnapshotWindow) -> None:
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(consume)
        observed = session.snapshot()

    assert tuple(durable) == expected
    assert observed == expected
    assert summary.prefetched_windows == OVERLAP_PREFETCHED_WINDOWS


def test_cuda_profile_snapshot_overlap_close_releases_all_banks() -> None:
    """Explicit close releases every bank registration and rejects reuse."""
    requests = (*_stream_requests(), _resident_session_request())
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    retained_bytes = 4 * memory_bytes
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        workspace = session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=retained_bytes,
            host_registration_budget_bytes=retained_bytes,
        )
        workspace.close()
        for bank in workspace.memory_banks:
            for memory in bank:
                memory.append(0)
                _ = memory.pop()
        with pytest.raises(
            AcceleratorExecutionError,
            match="overlap workspace is closed",
        ):
            _ = workspace.stream_snapshot(_ignore_snapshot_window)


def test_cuda_profile_snapshot_stream_is_exact_ordered_and_windowed() -> None:
    """One-memory window emits exact request order through reused aliases."""
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session(_stream_requests(), max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_stream_workspace(
            host_memory_budget_bytes=memory_bytes,
            host_registration_budget_bytes=memory_bytes,
        )
        capture = _StreamCapture(workspace)
        summary = workspace.stream_snapshot(capture)
        capacity = workspace.capacity
        registration = workspace.registration

    assert tuple(capture.durable) == expected
    assert capture.ranges == [(0, 1), (1, SESSION_BATCH_SIZE)]
    assert summary.items == SESSION_BATCH_SIZE
    assert summary.windows == SESSION_BATCH_SIZE
    assert capacity.host_memory_budget_bytes == memory_bytes
    assert capacity.total_items == SESSION_BATCH_SIZE
    assert capacity.window_bytes == memory_bytes
    assert capacity.window_items == 1
    assert registration.active
    assert registration.registered_arrays == 1
    assert isinstance(workspace, CudaProfileSnapshotStreamWorkspace)
    assert (
        profile_snapshot_stream_workspace_id() == SNAPSHOT_STREAM_WORKSPACE_ID
    )


def test_cuda_profile_snapshot_stream_emits_partial_final_window() -> None:
    """A non-divisible batch emits one smaller final prefix in exact order."""
    running, halted = _stream_requests()
    requests = (running, halted, running)
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    durable: list[ProfileRunResult] = []
    ranges: list[tuple[int, int]] = []
    with (
        _cuda() as adapter,
        adapter.open_session(requests, max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_stream_workspace(
            host_memory_budget_bytes=2 * memory_bytes,
        )

        def consume(window: ProfileSnapshotWindow) -> None:
            ranges.append((window.start, window.stop))
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(consume)

    assert tuple(durable) == expected
    assert ranges == [
        (0, SESSION_BATCH_SIZE),
        (SESSION_BATCH_SIZE, STREAM_BATCH_SIZE),
    ]
    assert summary.items == STREAM_BATCH_SIZE
    assert summary.windows == SESSION_BATCH_SIZE
    assert workspace.capacity.window_items == SESSION_BATCH_SIZE


def test_cuda_profile_snapshot_stream_locks_session_and_workspace() -> None:
    """Callbacks cannot mix advances, snapshots, closure, or nested streams."""
    request = _resident_session_request()
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        session.advance()
        workspace = session.allocate_snapshot_stream_workspace(
            host_memory_budget_bytes=memory_bytes,
        )

        def consume(window: ProfileSnapshotWindow) -> None:
            del window
            with pytest.raises(
                AcceleratorExecutionError,
                match="snapshot stream is active",
            ):
                session.advance()
            with pytest.raises(
                AcceleratorExecutionError,
                match="snapshot stream is active",
            ):
                _ = session.snapshot()
            with pytest.raises(
                AcceleratorExecutionError,
                match="snapshot stream is active",
            ):
                session.close()
            with pytest.raises(
                AcceleratorExecutionError,
                match="stream workspace is active",
            ):
                workspace.close()

            def nested(window: ProfileSnapshotWindow) -> None:
                del window

            with pytest.raises(
                AcceleratorExecutionError,
                match="stream workspace is active",
            ):
                _ = workspace.stream_snapshot(nested)

        summary = workspace.stream_snapshot(consume)
        observed = session.snapshot()
        workspace.close()

    assert summary.items == 1
    assert len(observed) == 1


def test_cuda_profile_snapshot_stream_recovers_after_consumer_failure() -> None:
    """Consumer exceptions release both stream locks for an exact retry."""
    request = _resident_session_request()
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_stream_workspace(
            host_memory_budget_bytes=memory_bytes,
        )

        def reject(window: ProfileSnapshotWindow) -> None:
            del window
            message = "synthetic consumer failure"
            raise RuntimeError(message)

        with pytest.raises(RuntimeError, match="synthetic consumer failure"):
            _ = workspace.stream_snapshot(reject)
        durable: list[ProfileRunResult] = []

        def capture(window: ProfileSnapshotWindow) -> None:
            durable.extend(_durable_result(result) for result in window.results)

        summary = workspace.stream_snapshot(capture)

    assert tuple(durable) == expected
    assert summary.items == 1
    assert summary.windows == 1


def test_cuda_profile_snapshot_stream_rejects_budget_and_shape_drift() -> None:
    """A full VM must fit and callback-driven resize fails before completion."""
    request = _resident_session_request()
    memory_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        for budget, pattern in (
            (0, "positive integer"),
            (-1, "positive integer"),
            (True, "positive integer"),
            (memory_bytes - 1, "cannot hold one memory"),
        ):
            with pytest.raises(AcceleratorExecutionError, match=pattern):
                _ = session.allocate_snapshot_stream_workspace(
                    host_memory_budget_bytes=budget,
                )
        workspace = session.allocate_snapshot_stream_workspace(
            host_memory_budget_bytes=memory_bytes,
        )
        with pytest.raises(
            AcceleratorExecutionError,
            match="consumer must be callable",
        ):
            _ = workspace.stream_snapshot(None)

        def resize(window: ProfileSnapshotWindow) -> None:
            del window
            _ = workspace.memories[0].pop()

        with pytest.raises(
            AcceleratorExecutionError,
            match="word count changed",
        ):
            _ = workspace.stream_snapshot(resize)


def test_cuda_profile_snapshot_workspace_rejects_mutated_shape() -> None:
    """Resized or duplicated caller arrays fail before a snapshot download."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError, match="word count changed"
        ):
            _ = workspace.snapshot()

        replacement = session.allocate_snapshot_workspace()
        same = replacement.memories[0]
        _corrupt_attribute(replacement, "_memories", (same, same))
        with pytest.raises(
            AcceleratorExecutionError, match="independent arrays"
        ):
            _ = replacement.snapshot()


def test_cuda_profile_snapshot_workspace_rejects_forged_or_closed_use() -> None:
    """Proof drift and closed-session actions fail explicitly."""
    request = _resident_session_request()
    with _cuda() as adapter:
        session = adapter.open_session((request,), max_runs=1)
        workspace = session.allocate_snapshot_workspace()
        _corrupt_attribute(workspace, "_proof", object())
        with pytest.raises(
            AcceleratorExecutionError, match="workspace is forged"
        ):
            _ = workspace.snapshot()

        valid = session.allocate_snapshot_workspace()
        session.close()
        with pytest.raises(
            AcceleratorExecutionError, match="session is closed"
        ):
            _ = valid.snapshot()


def test_cuda_profile_snapshot_workspace_rejects_count_drift() -> None:
    """Workspace cardinality remains bound to its exact resident session."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()
        _corrupt_attribute(workspace, "_memories", workspace.memories[:1])
        with pytest.raises(
            AcceleratorExecutionError, match="workspace count changed"
        ):
            _ = workspace.snapshot()


def test_cuda_profile_snapshot_workspace_type_is_public() -> None:
    """The caller-owned workspace has an explicit public runtime type."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request,),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()

    assert isinstance(workspace, CudaProfileSnapshotWorkspace)
    assert profile_snapshot_workspace_id() == SNAPSHOT_WORKSPACE_ID
    assert (
        profile_snapshot_host_registration_id() == SNAPSHOT_HOST_REGISTRATION_ID
    )


def test_cuda_profile_accepts_validated_memory_image() -> None:
    """Immutable validated memory images preserve exact CUDA execution."""
    request = _request()
    assert isinstance(request.memory, array)
    image_request = replace(
        request,
        memory=ProfileMemoryImage(GEOMETRY, request.memory),
    )
    with _cuda() as adapter:
        expected = adapter.evaluate((request,))
        observed = adapter.evaluate((image_request,))

    assert observed == expected
