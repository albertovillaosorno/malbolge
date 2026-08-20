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
#   - Caller-owned versus independent resident snapshot tradeoff.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Caller-owned versus independently allocated resident snapshots."""

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
    from accelerator.cuda.profile_run import ProfileSnapshotPhaseProfile
    from accelerator.profile_run import ProfileRunRequest
    from accelerator.profile_run import ProfileRunResult

BENCHMARK_ID: Final = "current-profile-resident-snapshot-workspace-tradeoff-v1"
WORKSPACE_ID: Final = "caller-owned-independent-u32-arrays-v1"
BATCH_SIZES: Final = (1, 8, 32)
SAMPLE_COUNT: Final = 15
ALLOCATION_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
PAIRED_ORDER: Final = (
    "ordinary-first on even samples; workspace-first on odd samples"
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
class SnapshotRoute:
    """Complete phase timings for one snapshot ownership route."""

    decode: Timing
    host_memory_allocate: Timing
    memory_download: Timing
    output_download: Timing
    state_download: Timing
    total: Timing


@dataclass(frozen=True, slots=True)
class WorkspaceTradeoff:
    """One exact batch compared through ordinary and reusable ownership."""

    batch_size: int
    buffer_bytes: int
    crossover_snapshots: int | None
    ordinary: SnapshotRoute
    workspace: SnapshotRoute
    workspace_allocate: Timing


def strict_workspace_crossover(
    allocation_ns: int,
    ordinary_snapshot_ns: int,
    workspace_snapshot_ns: int,
) -> int | None:
    """Return the first snapshot count where workspace total is strictly lower.

    Returns:
        Positive crossover count, or ``None`` when hot reuse cannot amortize.

    """
    if workspace_snapshot_ns >= ordinary_snapshot_ns:
        return None
    saving = ordinary_snapshot_ns - workspace_snapshot_ns
    return (allocation_ns // saving) + 1


def main() -> int:
    """Measure ordinary and caller-owned resident snapshots and emit JSON.

    Returns:
        Zero after every exact sample and workspace identity is validated.

    Raises:
        RuntimeError: If active workspace identity or exact evidence drifts.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
    identity = profile_snapshot_workspace_id()
    if identity != WORKSPACE_ID:
        message = "resident snapshot workspace identity drifted"
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
        "paired_order": PAIRED_ORDER,
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": STEP_BUDGET,
        "warmup_count": WARMUP_COUNT,
        "workspace_id": identity,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> WorkspaceTradeoff:
    requests = (request,) * batch_size
    with adapter.open_session(requests, max_runs=1) as session:
        session.advance()
        allocation_samples = _measure_workspace_allocations(session)
        workspace = session.allocate_snapshot_workspace()
        _warm_routes(session, workspace, batch_size)
        ordinary_samples: list[ProfileSnapshotPhaseProfile] = []
        workspace_samples: list[ProfileSnapshotPhaseProfile] = []
        for index in range(SAMPLE_COUNT):
            routes = (
                (_sample_ordinary, ordinary_samples),
                (_sample_workspace, workspace_samples),
            )
            if index % 2:
                routes = tuple(reversed(routes))
            for action, destination in routes:
                destination.append(action(session, workspace, batch_size))
    ordinary = _route(tuple(ordinary_samples))
    reused = _route(tuple(workspace_samples))
    allocation = _timing(tuple(allocation_samples), ALLOCATION_SAMPLE_COUNT)
    return WorkspaceTradeoff(
        batch_size=batch_size,
        buffer_bytes=batch_size * PROFILE_WORDS * WORD_BYTES,
        crossover_snapshots=strict_workspace_crossover(
            allocation.median_ns,
            ordinary.total.median_ns,
            reused.total.median_ns,
        ),
        ordinary=ordinary,
        workspace=reused,
        workspace_allocate=allocation,
    )


def _measure_workspace_allocations(
    session: CudaProfileRunSession,
) -> list[int]:
    samples: list[int] = []
    for _ in range(ALLOCATION_SAMPLE_COUNT):
        start = perf_counter_ns()
        workspace = session.allocate_snapshot_workspace()
        samples.append(perf_counter_ns() - start)
        del workspace
        _ = gc.collect()
    return samples


def _warm_routes(
    session: CudaProfileRunSession,
    workspace: CudaProfileSnapshotWorkspace,
    expected_count: int,
) -> None:
    for _ in range(WARMUP_COUNT):
        ordinary = session.snapshot()
        validate_profile_noop_results(ordinary, expected_count)
        reused = workspace.snapshot()
        validate_profile_noop_results(reused, expected_count)
        _validate_workspace_aliases(reused, workspace)
        del ordinary, reused
        _ = gc.collect()


def _sample_ordinary(
    session: CudaProfileRunSession,
    workspace: CudaProfileSnapshotWorkspace,
    expected_count: int,
) -> ProfileSnapshotPhaseProfile:
    del workspace
    results, profile = session.profile_snapshot()
    validate_profile_noop_results(results, expected_count)
    _validate_profile(profile, allow_allocation=True)
    _validate_independent_results(results)
    del results
    _ = gc.collect()
    return profile


def _sample_workspace(
    session: CudaProfileRunSession,
    workspace: CudaProfileSnapshotWorkspace,
    expected_count: int,
) -> ProfileSnapshotPhaseProfile:
    del session
    results, profile = workspace.profile_snapshot()
    validate_profile_noop_results(results, expected_count)
    _validate_profile(profile, allow_allocation=False)
    _validate_workspace_aliases(results, workspace)
    del results
    _ = gc.collect()
    return profile


def _validate_independent_results(
    results: tuple[ProfileRunResult, ...],
) -> None:
    identities = tuple(id(result.memory) for result in results)
    if len(identities) != len(set(identities)):
        message = "ordinary snapshot returned aliased result memories"
        raise RuntimeError(message)


def _validate_workspace_aliases(
    results: tuple[ProfileRunResult, ...],
    workspace: CudaProfileSnapshotWorkspace,
) -> None:
    if any(
        result.memory is not workspace.memories[index]
        for index, result in enumerate(results)
    ):
        message = "workspace snapshot did not return caller-owned arrays"
        raise RuntimeError(message)


def _validate_profile(
    profile: ProfileSnapshotPhaseProfile,
    *,
    allow_allocation: bool,
) -> None:
    if not allow_allocation and profile.host_memory_allocate_ns != 0:
        message = "workspace snapshot unexpectedly allocated result memories"
        raise RuntimeError(message)
    named = (
        profile.host_memory_allocate_ns
        + profile.state_download_ns
        + profile.memory_download_ns
        + profile.output_download_ns
        + profile.decode_ns
    )
    if profile.chunks <= 0 or named > profile.total_ns:
        message = "snapshot workspace profile contains invalid phase evidence"
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
        message = "snapshot workspace benchmark sample count drifted"
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
