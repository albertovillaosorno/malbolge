# File:
#   - profile_snapshot_double_buffer_overlap.py
# Path:
#   - benchmarks/accelerator/profile_snapshot_double_buffer_overlap.py
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
#   - Paired current-profile snapshot overlap benchmark protocol.
# - Must-Not:
#   - Change VM semantics or infer overlap from configuration alone.
# - Allows:
#   - Inputs: one exact resident current-profile no-op workload.
#   - Outputs: raw paired synchronous and double-buffer timing evidence.
#   - Side effects: CUDA execution and JSON output only.
# - Split-When:
#   - Split when another workload or overlap mechanism needs its own protocol.
# - Merge-When:
#   - Merge when another benchmark owns the exact same measured question.
# - Summary:
#   - Paired synchronous versus double-buffer streamed snapshot evidence.
# - Description:
#   - Measures whether next-window D-to-H prefetch overlaps exact callback work.
# - Usage:
#   - Run from the repository root with the pinned Python environment.
# - Defaults:
#   - Invalid identities, capacities, registrations, or results fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Compare synchronous and double-buffer current-profile snapshots."""

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
from accelerator.cuda.profile_run import CudaProfileSnapshotOverlapWorkspace
from accelerator.cuda.profile_run import CudaProfileSnapshotStreamWorkspace
from accelerator.cuda.profile_run import ProfileSnapshotOverlapSummary
from accelerator.cuda.profile_run import profile_snapshot_host_registration_id
from accelerator.cuda.profile_run import profile_snapshot_overlap_workspace_id
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
    from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration
    from accelerator.cuda.profile_run import ProfileSnapshotStreamSummary
    from accelerator.cuda.profile_run import ProfileSnapshotWindow
    from accelerator.profile_run import ProfileRunRequest

BENCHMARK_ID: Final = "current-profile-snapshot-double-buffer-overlap-v1"
STREAM_WORKSPACE_ID: Final = "caller-owned-windowed-u32-arrays-v1"
OVERLAP_WORKSPACE_ID: Final = (
    "caller-owned-double-window-overlap-u32-arrays-v1"
)
HOST_REGISTRATION_ID: Final = "bounded-all-or-pageable-u32-arrays-v1"
HOST_REGISTRATION_BUDGET_BYTES: Final = 512 * 1024 * 1024
BATCH_SIZE: Final = 32
WINDOW_ITEMS: Final = (1, 8)
ROUTE_IDS: Final = (
    "sync-window-1",
    "overlap-window-1",
    "sync-window-8",
    "overlap-window-8",
)
SAMPLE_COUNT: Final = 15
ALLOCATION_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
ROUTE_ORDER: Final = "rotate four route first positions by sample index"
HYPOTHESIS: Final = (
    "double buffering improves median and paired snapshot latency for the same "
    "registered window while preserving exact callback work"
)
REJECTION_RULE: Final = (
    "do not promote a speedup when overlap median is not lower or paired wins "
    "do not exceed half of retained observations"
)


@dataclass(frozen=True, slots=True)
class Timing:
    """Raw and summary nanosecond observations."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SnapshotOverlapEvidence:
    """Allocation, capacity, registration, and snapshot timing for one route."""

    allocate: Timing
    buffer_count: int
    host_memory_budget_bytes: int
    overlap_active: bool
    prefetched_windows: int
    registration: ProfileSnapshotHostRegistration
    retained_bytes: int
    route_id: str
    snapshot: Timing
    window_items: int
    windows_per_snapshot: int


@dataclass(slots=True)
class _RouteState:
    """One live benchmark route and retained observations."""

    allocate: Timing
    overlap: bool
    route_id: str
    samples: list[int]
    window_items: int
    workspace: (
        CudaProfileSnapshotStreamWorkspace
        | CudaProfileSnapshotOverlapWorkspace
    )


@dataclass(slots=True)
class _ExactWindowConsumer:
    """Validate complete ordered callback work without retaining memories."""

    expected_start: int = 0
    windows: int = 0

    def __call__(self, window: ProfileSnapshotWindow) -> None:
        if window.start != self.expected_start:
            message = "snapshot overlap window order drifted"
            raise RuntimeError(message)
        validate_profile_noop_results(window.results, window.item_count)
        self.expected_start = window.stop
        self.windows += 1

    def validate(self, expected_windows: int) -> None:
        """Require exact batch and callback cardinality.

        Raises:
            RuntimeError: If order or callback count is incomplete.

        """
        if (
            self.expected_start != BATCH_SIZE
            or self.windows != expected_windows
        ):
            message = "snapshot overlap consumer cardinality drifted"
            raise RuntimeError(message)


def rotated_route_order(sample_index: int) -> tuple[str, ...]:
    """Rotate all route identities in deterministic cyclic order.

    Returns:
        Every configured route exactly once.

    """
    offset = sample_index % len(ROUTE_IDS)
    return ROUTE_IDS[offset:] + ROUTE_IDS[:offset]


def expected_window_count(window_items: int) -> int:
    """Return exact callback count for the fixed benchmark batch.

    Returns:
        Ceiling division of batch size by window capacity.

    """
    return (BATCH_SIZE + window_items - 1) // window_items


def expected_prefetch_count(window_items: int) -> int:
    """Return submissions after the initial blocking window.

    Returns:
        Exact callback-window count minus one.

    """
    return expected_window_count(window_items) - 1


def main() -> int:
    """Run paired overlap routes and emit complete JSON evidence.

    Returns:
        Zero after every identity and sample validates.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = _measure(adapter, request)
        capability = adapter.capability()
    _validate_identities()
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
        "host_registration_id": HOST_REGISTRATION_ID,
        "hypothesis": HYPOTHESIS,
        "overlap_workspace_id": OVERLAP_WORKSPACE_ID,
        "rejection_rule": REJECTION_RULE,
        "route_ids": ROUTE_IDS,
        "route_order": ROUTE_ORDER,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": STEP_BUDGET,
        "stream_workspace_id": STREAM_WORKSPACE_ID,
        "warmup_count": WARMUP_COUNT,
        "window_items": WINDOW_ITEMS,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _validate_identities() -> None:
    observed = (
        profile_snapshot_stream_workspace_id(),
        profile_snapshot_overlap_workspace_id(),
        profile_snapshot_host_registration_id(),
    )
    expected = (
        STREAM_WORKSPACE_ID,
        OVERLAP_WORKSPACE_ID,
        HOST_REGISTRATION_ID,
    )
    if observed != expected:
        message = "snapshot overlap benchmark identity drifted"
        raise RuntimeError(message)


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
) -> tuple[SnapshotOverlapEvidence, ...]:
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
        for route_id in ROUTE_IDS:
            overlap, window_items = route_spec(route_id)
            allocation = _measure_allocations(
                session,
                overlap=overlap,
                window_items=window_items,
            )
            workspace = _open_workspace(
                session,
                overlap=overlap,
                window_items=window_items,
            )
            _validate_workspace(
                workspace, window_items, overlap=overlap
            )
            states.append(_RouteState(
                allocate=allocation,
                overlap=overlap,
                route_id=route_id,
                samples=[],
                window_items=window_items,
                workspace=workspace,
            ))
    except BaseException:
        _close_routes(tuple(states))
        raise
    return tuple(states)


def route_spec(route_id: str) -> tuple[bool, int]:
    """Resolve one stable route identity.

    Returns:
        Overlap activation and exact window capacity.

    Raises:
        ValueError: If the route identity is not configured.

    """
    if route_id not in ROUTE_IDS:
        message = f"unknown snapshot overlap route: {route_id}"
        raise ValueError(message)
    overlap = route_id.startswith("overlap-")
    window_items = int(route_id.rsplit("-", maxsplit=1)[1])
    return overlap, window_items


def _measure_allocations(
    session: CudaProfileRunSession,
    *,
    overlap: bool,
    window_items: int,
) -> Timing:
    samples: list[int] = []
    for _ in range(ALLOCATION_SAMPLE_COUNT):
        start = perf_counter_ns()
        workspace = _open_workspace(
            session,
            overlap=overlap,
            window_items=window_items,
        )
        samples.append(perf_counter_ns() - start)
        _validate_workspace(
                workspace, window_items, overlap=overlap
            )
        workspace.close()
        del workspace
        _ = gc.collect()
    return _timing(tuple(samples), ALLOCATION_SAMPLE_COUNT)


def _open_workspace(
    session: CudaProfileRunSession,
    *,
    overlap: bool,
    window_items: int,
) -> CudaProfileSnapshotStreamWorkspace | CudaProfileSnapshotOverlapWorkspace:
    memory_bytes = PROFILE_WORDS * WORD_BYTES
    if overlap:
        return session.allocate_snapshot_overlap_workspace(
            host_memory_budget_bytes=2 * window_items * memory_bytes,
            host_registration_budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
        )
    return session.allocate_snapshot_stream_workspace(
        host_memory_budget_bytes=window_items * memory_bytes,
        host_registration_budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
    )


def _validate_workspace(
    workspace: CudaProfileSnapshotStreamWorkspace
    | CudaProfileSnapshotOverlapWorkspace,
    window_items: int,
    *,
    overlap: bool,
) -> None:
    if overlap:
        _validate_overlap_workspace(workspace, window_items)
        return
    _validate_sync_workspace(workspace, window_items)


def _validate_sync_workspace(
    workspace: CudaProfileSnapshotStreamWorkspace
    | CudaProfileSnapshotOverlapWorkspace,
    window_items: int,
) -> None:
    if not isinstance(workspace, CudaProfileSnapshotStreamWorkspace):
        message = "synchronous snapshot route workspace type drifted"
        raise TypeError(message)
    memory_bytes = PROFILE_WORDS * WORD_BYTES
    expected_bytes = window_items * memory_bytes
    capacity = workspace.capacity
    observed = (
        capacity.host_memory_budget_bytes,
        capacity.total_items,
        capacity.window_bytes,
        capacity.window_items,
    )
    expected = (expected_bytes, BATCH_SIZE, expected_bytes, window_items)
    if observed != expected:
        message = "synchronous snapshot route capacity drifted"
        raise RuntimeError(message)
    _validate_registration(
        workspace.registration,
        expected_arrays=window_items,
        expected_bytes=expected_bytes,
    )


def _validate_overlap_workspace(
    workspace: CudaProfileSnapshotStreamWorkspace
    | CudaProfileSnapshotOverlapWorkspace,
    window_items: int,
) -> None:
    if not isinstance(workspace, CudaProfileSnapshotOverlapWorkspace):
        message = "overlap snapshot route workspace type drifted"
        raise TypeError(message)
    memory_bytes = PROFILE_WORDS * WORD_BYTES
    bank_bytes = window_items * memory_bytes
    retained_bytes = 2 * bank_bytes
    capacity = workspace.capacity
    observed = (
        capacity.bank_bytes,
        capacity.bank_items,
        capacity.buffer_count,
        capacity.host_memory_budget_bytes,
        capacity.planned_windows,
        capacity.retained_bytes,
        capacity.total_items,
    )
    expected = (
        bank_bytes,
        window_items,
        2,
        retained_bytes,
        expected_window_count(window_items),
        retained_bytes,
        BATCH_SIZE,
    )
    if observed != expected or not workspace.admission.active:
        message = "overlap snapshot route admission or capacity drifted"
        raise RuntimeError(message)
    _validate_registration(
        workspace.registration,
        expected_arrays=2 * window_items,
        expected_bytes=retained_bytes,
    )


def _validate_registration(
    registration: ProfileSnapshotHostRegistration,
    *,
    expected_arrays: int,
    expected_bytes: int,
) -> None:
    observed = (
        registration.active,
        registration.budget_bytes,
        registration.fallback_reason,
        registration.registered_arrays,
        registration.registered_bytes,
        registration.requested_bytes,
    )
    expected = (
        True,
        HOST_REGISTRATION_BUDGET_BYTES,
        None,
        expected_arrays,
        expected_bytes,
        expected_bytes,
    )
    if observed != expected:
        message = "snapshot overlap registration evidence drifted"
        raise RuntimeError(message)


def _warm_routes(states: tuple[_RouteState, ...]) -> None:
    for _ in range(WARMUP_COUNT):
        for state in states:
            _ = _sample_workspace(state)


def _sample_routes(states: tuple[_RouteState, ...]) -> None:
    by_id = {state.route_id: state for state in states}
    for sample_index in range(SAMPLE_COUNT):
        for route_id in rotated_route_order(sample_index):
            state = by_id[route_id]
            state.samples.append(_sample_workspace(state))


def _sample_workspace(state: _RouteState) -> int:
    consumer = _ExactWindowConsumer()
    start = perf_counter_ns()
    summary = state.workspace.stream_snapshot(consumer)
    elapsed = perf_counter_ns() - start
    expected_windows = expected_window_count(state.window_items)
    consumer.validate(expected_windows)
    _validate_summary(
        summary,
        overlap=state.overlap,
        window_items=state.window_items,
    )
    return elapsed


def _validate_summary(
    summary: ProfileSnapshotStreamSummary | ProfileSnapshotOverlapSummary,
    *,
    overlap: bool,
    window_items: int,
) -> None:
    expected_windows = expected_window_count(window_items)
    if summary.items != BATCH_SIZE or summary.windows != expected_windows:
        message = "snapshot overlap summary cardinality drifted"
        raise RuntimeError(message)
    if overlap and (
        not isinstance(summary, ProfileSnapshotOverlapSummary)
        or summary.prefetched_windows
        != expected_prefetch_count(window_items)
    ):
        message = "snapshot overlap prefetch count drifted"
        raise RuntimeError(message)


def _freeze_route(state: _RouteState) -> SnapshotOverlapEvidence:
    if state.overlap:
        return _freeze_overlap_route(state)
    return _freeze_sync_route(state)


def _freeze_sync_route(state: _RouteState) -> SnapshotOverlapEvidence:
    if not isinstance(state.workspace, CudaProfileSnapshotStreamWorkspace):
        message = "synchronous route freeze type drifted"
        raise TypeError(message)
    capacity = state.workspace.capacity
    return SnapshotOverlapEvidence(
        allocate=state.allocate,
        buffer_count=1,
        host_memory_budget_bytes=capacity.host_memory_budget_bytes,
        overlap_active=False,
        prefetched_windows=0,
        registration=state.workspace.registration,
        retained_bytes=capacity.window_bytes,
        route_id=state.route_id,
        snapshot=_timing(tuple(state.samples), SAMPLE_COUNT),
        window_items=state.window_items,
        windows_per_snapshot=expected_window_count(state.window_items),
    )


def _freeze_overlap_route(state: _RouteState) -> SnapshotOverlapEvidence:
    if not isinstance(state.workspace, CudaProfileSnapshotOverlapWorkspace):
        message = "overlap route freeze type drifted"
        raise TypeError(message)
    capacity = state.workspace.capacity
    return SnapshotOverlapEvidence(
        allocate=state.allocate,
        buffer_count=capacity.buffer_count,
        host_memory_budget_bytes=capacity.host_memory_budget_bytes,
        overlap_active=state.workspace.admission.active,
        prefetched_windows=expected_prefetch_count(state.window_items),
        registration=state.workspace.registration,
        retained_bytes=capacity.retained_bytes,
        route_id=state.route_id,
        snapshot=_timing(tuple(state.samples), SAMPLE_COUNT),
        window_items=state.window_items,
        windows_per_snapshot=expected_window_count(state.window_items),
    )


def _close_routes(states: tuple[_RouteState, ...]) -> None:
    for state in reversed(states):
        state.workspace.close()
    _ = gc.collect()


def _timing(samples: tuple[int, ...], expected_count: int) -> Timing:
    if len(samples) != expected_count:
        message = "snapshot overlap benchmark sample count drifted"
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
