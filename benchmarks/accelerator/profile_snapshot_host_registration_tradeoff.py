# File:
#   - profile_snapshot_host_registration_tradeoff.py
# Path:
#   - benchmarks/accelerator/profile_snapshot_host_registration_tradeoff.py
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
#   - Bounded page-lock versus pageable snapshot-workspace tradeoff.
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

"""Bounded page-lock versus pageable resident snapshot workspaces."""

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
from accelerator.cuda.profile_run import profile_snapshot_workspace_id
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
    from collections.abc import Callable

    from accelerator.cuda.profile_run import CudaProfileRunSession
    from accelerator.cuda.profile_run import CudaProfileSnapshotWorkspace
    from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration
    from accelerator.cuda.profile_run import ProfileSnapshotPhaseProfile
    from accelerator.profile_run import ProfileRunRequest
    from accelerator.profile_run import ProfileRunResult

BENCHMARK_ID: Final = (
    "current-profile-resident-snapshot-host-registration-tradeoff-v1"
)
WORKSPACE_ID: Final = "caller-owned-independent-u32-arrays-v1"
HOST_REGISTRATION_ID: Final = "bounded-all-or-pageable-u32-arrays-v1"
HOST_REGISTRATION_BUDGET_BYTES: Final = 256 * 1024 * 1024
BATCH_SIZES: Final = (1, 8, 32)
SAMPLE_COUNT: Final = 15
ALLOCATION_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
ROUTE_ORDER: Final = (
    "pageable-first even samples; bounded-first odd samples"
)
_DISABLED: Final = "disabled"
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
class SnapshotRoute:
    """Complete phase timings for one workspace transfer route."""

    decode: Timing
    host_memory_allocate: Timing
    memory_download: Timing
    output_download: Timing
    state_download: Timing
    total: Timing


@dataclass(frozen=True, slots=True)
class WorkspaceRoute:
    """Allocation, registration, and snapshot evidence for one route."""

    allocate: Timing
    registration: ProfileSnapshotHostRegistration
    registration_active: bool
    snapshot: SnapshotRoute


@dataclass(frozen=True, slots=True)
class HostRegistrationTradeoff:
    """One batch compared through pageable and bounded registration."""

    batch_size: int
    buffer_bytes: int
    bounded: WorkspaceRoute
    crossover_snapshots: int | None
    pageable: WorkspaceRoute


@dataclass(frozen=True, slots=True)
class _WorkspacePair:
    """Pageable and bounded workspaces for paired sampling."""

    bounded: CudaProfileSnapshotWorkspace
    pageable: CudaProfileSnapshotWorkspace


def strict_host_registration_crossover(
    incremental_allocate_ns: int,
    pageable_snapshot_ns: int,
    bounded_snapshot_ns: int,
    *,
    registration_active: bool,
) -> int | None:
    """Return first snapshot count where bounded registration costs less.

    Returns:
        Positive crossover count, or ``None`` without a registered hot win.

    """
    if not registration_active or bounded_snapshot_ns >= pageable_snapshot_ns:
        return None
    saving = pageable_snapshot_ns - bounded_snapshot_ns
    return (max(0, incremental_allocate_ns) // saving) + 1


def main() -> int:
    """Measure pageable and bounded workspace snapshots and emit JSON.

    Returns:
        Zero after exact evidence and policy identities are validated.

    Raises:
        RuntimeError: If identity or registration policy evidence drifts.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
    workspace_id = profile_snapshot_workspace_id()
    registration_id = profile_snapshot_host_registration_id()
    if workspace_id != WORKSPACE_ID:
        message = "resident snapshot workspace identity drifted"
        raise RuntimeError(message)
    if registration_id != HOST_REGISTRATION_ID:
        message = "snapshot host registration identity drifted"
        raise RuntimeError(message)
    payload = {
        "allocation_sample_count": ALLOCATION_SAMPLE_COUNT,
        "backend": capability.backend_id,
        "batch_sizes": BATCH_SIZES,
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
        "warmup_count": WARMUP_COUNT,
        "workspace_id": workspace_id,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> HostRegistrationTradeoff:
    buffer_bytes = batch_size * PROFILE_WORDS * WORD_BYTES
    with adapter.open_session(
        (request,) * batch_size,
        max_runs=1,
    ) as session:
        session.advance()
        pageable, bounded = _measure_session_workspaces(
            session,
            batch_size,
            buffer_bytes,
        )
    return HostRegistrationTradeoff(
        batch_size=batch_size,
        buffer_bytes=buffer_bytes,
        bounded=bounded,
        crossover_snapshots=strict_host_registration_crossover(
            bounded.allocate.median_ns - pageable.allocate.median_ns,
            pageable.snapshot.total.median_ns,
            bounded.snapshot.total.median_ns,
            registration_active=bounded.registration_active,
        ),
        pageable=pageable,
    )


def _measure_session_workspaces(
    session: CudaProfileRunSession,
    batch_size: int,
    buffer_bytes: int,
) -> tuple[WorkspaceRoute, WorkspaceRoute]:
    pageable_allocations = _measure_allocations(
        session,
        buffer_bytes,
        budget_bytes=0,
    )
    bounded_allocations = _measure_allocations(
        session,
        buffer_bytes,
        budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
    )
    pair = _allocate_workspace_pair(session)
    try:
        _validate_workspace_pair(pair, batch_size, buffer_bytes)
        pageable_samples, bounded_samples = _paired_snapshot_samples(
            pair,
            batch_size,
        )
    finally:
        _close_workspace_pair(pair)
    pageable = _workspace_route(
        pageable_allocations,
        pageable_samples,
        registration=pair.pageable.registration,
    )
    bounded = _workspace_route(
        bounded_allocations,
        bounded_samples,
        registration=pair.bounded.registration,
    )
    return pageable, bounded


def _allocate_workspace_pair(
    session: CudaProfileRunSession,
) -> _WorkspacePair:
    return _WorkspacePair(
        bounded=session.allocate_snapshot_workspace(
            host_registration_budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
        ),
        pageable=session.allocate_snapshot_workspace(),
    )


def _validate_workspace_pair(
    pair: _WorkspacePair,
    batch_size: int,
    buffer_bytes: int,
) -> None:
    _validate_registration(
        pair.pageable.registration,
        batch_size,
        buffer_bytes,
        budget_bytes=0,
    )
    _validate_registration(
        pair.bounded.registration,
        batch_size,
        buffer_bytes,
        budget_bytes=HOST_REGISTRATION_BUDGET_BYTES,
    )


def _paired_snapshot_samples(
    pair: _WorkspacePair,
    expected_count: int,
) -> tuple[
    list[ProfileSnapshotPhaseProfile],
    list[ProfileSnapshotPhaseProfile],
]:
    _warm_workspaces((pair.pageable, pair.bounded), expected_count)
    pageable: list[ProfileSnapshotPhaseProfile] = []
    bounded: list[ProfileSnapshotPhaseProfile] = []
    for index in range(SAMPLE_COUNT):
        if index % 2:
            bounded.append(_sample_workspace(pair.bounded, expected_count))
            pageable.append(_sample_workspace(pair.pageable, expected_count))
        else:
            pageable.append(_sample_workspace(pair.pageable, expected_count))
            bounded.append(_sample_workspace(pair.bounded, expected_count))
    return pageable, bounded


def _close_workspace_pair(pair: _WorkspacePair) -> None:
    pair.bounded.close()
    pair.pageable.close()
    _ = gc.collect()


def _workspace_route(
    allocation_samples: list[int],
    snapshot_samples: list[ProfileSnapshotPhaseProfile],
    *,
    registration: ProfileSnapshotHostRegistration,
) -> WorkspaceRoute:
    return WorkspaceRoute(
        allocate=_timing(
            tuple(allocation_samples),
            ALLOCATION_SAMPLE_COUNT,
        ),
        registration=registration,
        registration_active=registration.active,
        snapshot=_route(tuple(snapshot_samples)),
    )


def _measure_allocations(
    session: CudaProfileRunSession,
    buffer_bytes: int,
    *,
    budget_bytes: int,
) -> list[int]:
    samples: list[int] = []
    for _ in range(ALLOCATION_SAMPLE_COUNT):
        start = perf_counter_ns()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=budget_bytes,
        )
        samples.append(perf_counter_ns() - start)
        _validate_registration(
            workspace.registration,
            len(workspace.memories),
            buffer_bytes,
            budget_bytes=budget_bytes,
        )
        workspace.close()
        del workspace
        _ = gc.collect()
    return samples


def _warm_workspaces(
    workspaces: tuple[
        CudaProfileSnapshotWorkspace,
        CudaProfileSnapshotWorkspace,
    ],
    expected_count: int,
) -> None:
    for _ in range(WARMUP_COUNT):
        for workspace in workspaces:
            results = workspace.snapshot()
            validate_profile_noop_results(results, expected_count)
            _validate_workspace_aliases(results, workspace)
            del results
            _ = gc.collect()


def _sample_workspace(
    workspace: CudaProfileSnapshotWorkspace,
    expected_count: int,
) -> ProfileSnapshotPhaseProfile:
    results, profile = workspace.profile_snapshot()
    validate_profile_noop_results(results, expected_count)
    _validate_workspace_aliases(results, workspace)
    _validate_profile(profile)
    del results
    _ = gc.collect()
    return profile


def _validate_registration(
    registration: ProfileSnapshotHostRegistration,
    batch_size: int,
    buffer_bytes: int,
    *,
    budget_bytes: int,
) -> None:
    if (
        registration.budget_bytes != budget_bytes
        or registration.requested_bytes != buffer_bytes
    ):
        message = "snapshot host registration byte evidence drifted"
        raise RuntimeError(message)
    if budget_bytes == 0:
        expected_reason: str | None = _DISABLED
    elif buffer_bytes > budget_bytes:
        expected_reason = _BUDGET_EXCEEDED
    else:
        expected_reason = None
    expected_arrays = batch_size if expected_reason is None else 0
    expected_bytes = buffer_bytes if expected_reason is None else 0
    observed = (
        registration.fallback_reason,
        registration.registered_arrays,
        registration.registered_bytes,
        registration.active,
    )
    expected = (
        expected_reason,
        expected_arrays,
        expected_bytes,
        expected_reason is None,
    )
    if observed != expected:
        message = "snapshot host registration policy evidence drifted"
        raise RuntimeError(message)


def _validate_workspace_aliases(
    results: tuple[ProfileRunResult, ...],
    workspace: CudaProfileSnapshotWorkspace,
) -> None:
    if any(
        result.memory is not workspace.memories[index]
        for index, result in enumerate(results)
    ):
        message = "registered workspace did not return caller-owned arrays"
        raise RuntimeError(message)


def _validate_profile(profile: ProfileSnapshotPhaseProfile) -> None:
    named = (
        profile.host_memory_allocate_ns
        + profile.state_download_ns
        + profile.memory_download_ns
        + profile.output_download_ns
        + profile.decode_ns
    )
    if (
        profile.chunks <= 0
        or profile.host_memory_allocate_ns != 0
        or named > profile.total_ns
    ):
        message = "registered workspace profile contains invalid phase evidence"
        raise RuntimeError(message)


def _route(
    samples: tuple[ProfileSnapshotPhaseProfile, ...],
) -> SnapshotRoute:
    return SnapshotRoute(
        decode=_profile_timing(samples, lambda item: item.decode_ns),
        host_memory_allocate=_profile_timing(
            samples,
            lambda item: item.host_memory_allocate_ns,
        ),
        memory_download=_profile_timing(
            samples,
            lambda item: item.memory_download_ns,
        ),
        output_download=_profile_timing(
            samples,
            lambda item: item.output_download_ns,
        ),
        state_download=_profile_timing(
            samples,
            lambda item: item.state_download_ns,
        ),
        total=_profile_timing(samples, lambda item: item.total_ns),
    )


def _profile_timing(
    samples: tuple[ProfileSnapshotPhaseProfile, ...],
    value: Callable[[ProfileSnapshotPhaseProfile], int],
) -> Timing:
    return _timing(tuple(value(item) for item in samples), SAMPLE_COUNT)


def _timing(samples: tuple[int, ...], expected_count: int) -> Timing:
    if len(samples) != expected_count:
        message = "snapshot host registration sample count drifted"
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
