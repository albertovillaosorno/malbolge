# File:
#   - profile_snapshot_stream_window_tradeoff.py
# Path:
#   - benchmarks/accelerator/profile_snapshot_stream_window_tradeoff.py
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
#   - Bounded host-window tradeoff for streamed profile snapshots.
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

"""Measure bounded host windows for streamed current-profile snapshots."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import gc
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.cuda.profile_run import profile_snapshot_host_registration_id
from accelerator.cuda.profile_run import profile_snapshot_stream_workspace_id
from benchmarks.accelerator.profile_workload import GEOMETRY
from benchmarks.accelerator.profile_workload import PROFILE_TRITS
from benchmarks.accelerator.profile_workload import PROFILE_WORDS
from benchmarks.accelerator.profile_workload import STEP_BUDGET
from benchmarks.accelerator.profile_workload import WORD_BYTES
from benchmarks.accelerator.profile_workload import profile_noop_request
from benchmarks.accelerator.profile_workload import (
    validate_profile_noop_results,
)

if TYPE_CHECKING:
    from accelerator.cuda.profile_run import CudaProfileRunSession
    from accelerator.cuda.profile_run import CudaProfileSnapshotStreamWorkspace
    from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration
    from accelerator.cuda.profile_run import ProfileSnapshotWindow
    from accelerator.profile_run import ProfileRunRequest

BENCHMARK_ID: Final = (
    "current-profile-resident-snapshot-stream-window-tradeoff-v1"
)
STREAM_WORKSPACE_ID: Final = "caller-owned-windowed-u32-arrays-v1"
HOST_REGISTRATION_ID: Final = "bounded-all-or-pageable-u32-arrays-v1"
HOST_REGISTRATION_BUDGET_BYTES: Final = 256 * 1024 * 1024
BATCH_SIZE: Final = 32
WINDOW_ITEMS: Final = (1, 8, 32)
SAMPLE_COUNT: Final = 15
ALLOCATION_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
ROUTE_ORDER: Final = "rotate window 1/8/32 first position by sample index"
_BUDGET_EXCEEDED: Final = "budget-exceeded"


@dataclass(frozen=True, slots=True)
class Timing:
    """Raw and summary nanosecond observations."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class StreamWindowEvidence:
    """Allocation, transfer, registration, and capacity for one window."""

    allocate: Timing
    host_memory_budget_bytes: int
    registration: ProfileSnapshotHostRegistration
    registration_active: bool
    snapshot: Timing
    window_bytes: int
    window_items: int
    windows_per_snapshot: int


@dataclass(slots=True)
class _RouteState:
    """One live route and its retained observations."""

    allocate: Timing
    snapshot_samples: list[int]
    window_items: int
    workspace: CudaProfileSnapshotStreamWorkspace


@dataclass(slots=True)
class _ExactWindowConsumer:
    """Validate exact ordered windows without retaining result memories."""

    expected_start: int = 0
    windows: int = 0

    def __call__(self, window: ProfileSnapshotWindow) -> None:
        if window.start != self.expected_start:
            message = "stream snapshot window order drifted"
            raise RuntimeError(message)
        validate_profile_noop_results(window.results, window.item_count)
        self.expected_start = window.stop
        self.windows += 1

    def validate(self, expected_windows: int) -> None:
        """Require complete batch and exact window cardinality.

        Raises:
            RuntimeError: If item order or callback count is incomplete.

        """
        if (
            self.expected_start != BATCH_SIZE
            or self.windows != expected_windows
        ):
            message = "stream snapshot consumer cardinality drifted"
            raise RuntimeError(message)


def rotated_window_order(sample_index: int) -> tuple[int, ...]:
    """Rotate the first measured route deterministically.

    Returns:
        All window identities exactly once in cyclic order.

    """
    offset = sample_index % len(WINDOW_ITEMS)
    return WINDOW_ITEMS[offset:] + WINDOW_ITEMS[:offset]


def expected_window_count(window_items: int) -> int:
    """Return exact callback count for the fixed benchmark batch.

    Returns:
        Ceiling division of batch items by window capacity.

    """
    return (BATCH_SIZE + window_items - 1) // window_items


def main() -> int:
    """Measure three bounded streaming windows and emit JSON.

    Returns:
        Zero after every sample and policy identity is validated.

    Raises:
        RuntimeError: If exactness, capacity, or policy identity drifts.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = _measure(adapter, request)
        capability = adapter.capability()
    stream_id = profile_snapshot_stream_workspace_id()
    registration_id = profile_snapshot_host_registration_id()
    if stream_id != STREAM_WORKSPACE_ID:
        message = "snapshot stream workspace identity drifted"
        raise RuntimeError(message)
    if registration_id != HOST_REGISTRATION_ID:
        message = "snapshot host registration identity drifted"
        raise RuntimeError(message)
    payload = {
        "allocation_sample_count": ALLOCATION_SAMPLE_COUNT,
        "backend": capability.backend_id,
        "batch_size": BATCH_SIZE,
        "benchmark_id": BENCHMARK_ID,
        "device": {
            "arch": capability.device_arch,
            "name": capability.device_name,
        },
        "geometry": {
            "memory_bytes_per_vm": PROFILE_WORDS * WORD_BYTES,
            "memory_words": PROFILE_WORDS,
            "word_trits": PROFILE_TRITS,
        },
        "host_registration_budget_bytes": (
            HOST_REGISTRATION_BUDGET_BYTES
        ),
        "host_registration_id": registration_id,
        "route_order": ROUTE_ORDER,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": STEP_BUDGET,
        "stream_workspace_id": stream_id,
        "warmup_count": WARMUP_COUNT,
        "window_items": WINDOW_ITEMS,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
) -> tuple[StreamWindowEvidence, ...]:
    with adapter.open_session((request,) * BATCH_SIZE, max_runs=1) as session:
        session.advance()
        states = _open_route_states(session)
        try:
            _warm_routes(states)
            _sample_routes(states)
        finally:
            _close_routes(states)
    return tuple(_freeze_route(state) for state in states)


def _open_route_states(
    session: CudaProfileRunSession,
) -> tuple[_RouteState, ...]:
    states: list[_RouteState] = []
    try:
        for window_items in WINDOW_ITEMS:
            allocation = _measure_allocations(session, window_items)
            workspace = _open_workspace(session, window_items)
            _validate_workspace(workspace, window_items)
            states.append(_RouteState(
                allocate=allocation,
                snapshot_samples=[],
                window_items=window_items,
                workspace=workspace,
            ))
    except BaseException:
        _close_routes(tuple(states))
        raise
    return tuple(states)


def _measure_allocations(
    session: CudaProfileRunSession,
    window_items: int,
) -> Timing:
    samples: list[int] = []
    for _ in range(ALLOCATION_SAMPLE_COUNT):
        start = perf_counter_ns()
        workspace = _open_workspace(session, window_items)
        samples.append(perf_counter_ns() - start)
        _validate_workspace(workspace, window_items)
        workspace.close()
        del workspace
        _ = gc.collect()
    return _timing(tuple(samples), ALLOCATION_SAMPLE_COUNT)


def _open_workspace(
    session: CudaProfileRunSession,
    window_items: int,
) -> CudaProfileSnapshotStreamWorkspace:
    memory_bytes = PROFILE_WORDS * WORD_BYTES
    return session.allocate_snapshot_stream_workspace(
        host_memory_budget_bytes=window_items * memory_bytes,
        host_registration_budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
    )


def _validate_workspace(
    workspace: CudaProfileSnapshotStreamWorkspace,
    window_items: int,
) -> None:
    window_bytes = window_items * PROFILE_WORDS * WORD_BYTES
    _validate_stream_capacity(workspace, window_items, window_bytes)
    _validate_stream_registration(workspace, window_items, window_bytes)


def _validate_stream_capacity(
    workspace: CudaProfileSnapshotStreamWorkspace,
    window_items: int,
    window_bytes: int,
) -> None:
    capacity = workspace.capacity
    if capacity.host_memory_budget_bytes != window_bytes:
        message = "stream snapshot host budget drifted"
        raise RuntimeError(message)
    observed = (
        capacity.total_items,
        capacity.window_bytes,
        capacity.window_items,
    )
    expected = (BATCH_SIZE, window_bytes, window_items)
    if observed != expected:
        message = "stream snapshot capacity drifted"
        raise RuntimeError(message)


def _validate_stream_registration(
    workspace: CudaProfileSnapshotStreamWorkspace,
    window_items: int,
    window_bytes: int,
) -> None:
    registration = workspace.registration
    expected_reason = (
        None
        if window_bytes <= HOST_REGISTRATION_BUDGET_BYTES
        else _BUDGET_EXCEEDED
    )
    expected_arrays = window_items if expected_reason is None else 0
    expected_bytes = window_bytes if expected_reason is None else 0
    observed = (
        registration.budget_bytes,
        registration.fallback_reason,
        registration.registered_arrays,
        registration.registered_bytes,
        registration.requested_bytes,
    )
    expected = (
        HOST_REGISTRATION_BUDGET_BYTES,
        expected_reason,
        expected_arrays,
        expected_bytes,
        window_bytes,
    )
    if observed != expected:
        message = "stream snapshot registration evidence drifted"
        raise RuntimeError(message)


def _warm_routes(states: tuple[_RouteState, ...]) -> None:
    for _ in range(WARMUP_COUNT):
        for state in states:
            _ = _sample_workspace(state.workspace, state.window_items)


def _sample_routes(states: tuple[_RouteState, ...]) -> None:
    by_window = {state.window_items: state for state in states}
    for sample_index in range(SAMPLE_COUNT):
        for window_items in rotated_window_order(sample_index):
            state = by_window[window_items]
            state.snapshot_samples.append(
                _sample_workspace(state.workspace, window_items)
            )


def _sample_workspace(
    workspace: CudaProfileSnapshotStreamWorkspace,
    window_items: int,
) -> int:
    consumer = _ExactWindowConsumer()
    start = perf_counter_ns()
    summary = workspace.stream_snapshot(consumer)
    elapsed = perf_counter_ns() - start
    expected_windows = expected_window_count(window_items)
    consumer.validate(expected_windows)
    if summary.items != BATCH_SIZE or summary.windows != expected_windows:
        message = "stream snapshot summary drifted"
        raise RuntimeError(message)
    return elapsed


def _freeze_route(state: _RouteState) -> StreamWindowEvidence:
    return StreamWindowEvidence(
        allocate=state.allocate,
        host_memory_budget_bytes=(
            state.workspace.capacity.host_memory_budget_bytes
        ),
        registration=state.workspace.registration,
        registration_active=state.workspace.registration.active,
        snapshot=_timing(tuple(state.snapshot_samples), SAMPLE_COUNT),
        window_bytes=state.workspace.capacity.window_bytes,
        window_items=state.window_items,
        windows_per_snapshot=expected_window_count(state.window_items),
    )


def _close_routes(states: tuple[_RouteState, ...]) -> None:
    for state in reversed(states):
        state.workspace.close()
    _ = gc.collect()


def _timing(samples: tuple[int, ...], expected_count: int) -> Timing:
    if len(samples) != expected_count:
        message = "stream snapshot benchmark sample count drifted"
        raise RuntimeError(message)
    return Timing(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=samples,
    )


if __name__ == "__main__":
    raise SystemExit(main())
