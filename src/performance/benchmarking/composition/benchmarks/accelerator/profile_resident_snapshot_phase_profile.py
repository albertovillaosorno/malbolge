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
#   - Phase-separated resident current-profile CUDA snapshots.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Phase-separated resident current-profile CUDA snapshots."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import gc
import json
from statistics import median
from statistics import pstdev
import sys
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.profile_run import CudaProfileRunAdapter

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
    from accelerator.cuda.profile_run import ProfileSnapshotPhaseProfile
    from accelerator.profile_run import ProfileRunRequest

BENCHMARK_ID: Final = "current-profile-resident-snapshot-phase-profile-v1"
BATCH_SIZES: Final = (1, 8, 32)
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1


@dataclass(frozen=True, slots=True)
class Timing:
    """Raw and summary nanosecond observations for one snapshot phase."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Coverage:
    """Named phase coverage over inclusive snapshot wall time."""

    max_ratio: float
    median_ratio: float
    min_ratio: float
    raw_ratio: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SnapshotPhaseRow:
    """Phase summaries for one complete resident snapshot batch."""

    batch_size: int
    chunks: int
    decode: Timing
    host_memory_allocate: Timing
    memory_download: Timing
    named_coverage: Coverage
    output_download: Timing
    state_download: Timing
    total: Timing


def main() -> int:
    """Measure complete resident snapshot phases and emit raw JSON evidence.

    Returns:
        Zero after all exact samples are validated and emitted.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
    payload = {
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
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "segment_steps": STEP_BUDGET,
        "timed_region": "CudaProfileRunSession.profile_snapshot only",
        "warmup_count": WARMUP_COUNT,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> SnapshotPhaseRow:
    requests = (request,) * batch_size
    with adapter.open_session(requests, max_runs=1) as session:
        session.advance()
        _warm_snapshot(session, batch_size)
        samples = tuple(
            _sample_snapshot(session, batch_size) for _ in range(SAMPLE_COUNT)
        )
    chunks = samples[0].chunks
    if any(item.chunks != chunks for item in samples):
        message = "resident snapshot chunk count changed between samples"
        raise RuntimeError(message)
    return SnapshotPhaseRow(
        batch_size=batch_size,
        chunks=chunks,
        decode=_timing(samples, lambda item: item.decode_ns),
        host_memory_allocate=_timing(
            samples,
            lambda item: item.host_memory_allocate_ns,
        ),
        memory_download=_timing(samples, lambda item: item.memory_download_ns),
        named_coverage=_coverage(samples),
        output_download=_timing(samples, lambda item: item.output_download_ns),
        state_download=_timing(samples, lambda item: item.state_download_ns),
        total=_timing(samples, lambda item: item.total_ns),
    )


def _warm_snapshot(session: CudaProfileRunSession, expected_count: int) -> None:
    for _ in range(WARMUP_COUNT):
        results = session.snapshot()
        validate_profile_noop_results(results, expected_count)
        del results
        _ = gc.collect()


def _sample_snapshot(
    session: CudaProfileRunSession,
    expected_count: int,
) -> ProfileSnapshotPhaseProfile:
    results, profile = session.profile_snapshot()
    validate_profile_noop_results(results, expected_count)
    _validate_profile(profile)
    del results
    _ = gc.collect()
    return profile


def _validate_profile(profile: ProfileSnapshotPhaseProfile) -> None:
    components = (
        profile.host_memory_allocate_ns,
        profile.state_download_ns,
        profile.memory_download_ns,
        profile.output_download_ns,
        profile.decode_ns,
    )
    if profile.chunks <= 0 or any(value < 0 for value in components):
        message = "resident snapshot profile contains invalid phase evidence"
        raise RuntimeError(message)
    if sum(components) > profile.total_ns:
        message = "resident snapshot named phases exceed inclusive total"
        raise RuntimeError(message)


def _timing(
    samples: tuple[ProfileSnapshotPhaseProfile, ...],
    value: Callable[[ProfileSnapshotPhaseProfile], int],
) -> Timing:
    raw = tuple(value(item) for item in samples)
    return Timing(
        max_ns=max(raw),
        median_ns=int(median(raw)),
        min_ns=min(raw),
        pstdev_ns=pstdev(raw),
        raw_ns=raw,
    )


def _coverage(
    samples: tuple[ProfileSnapshotPhaseProfile, ...],
) -> Coverage:
    raw = tuple(_named_total(item) / item.total_ns for item in samples)
    return Coverage(
        max_ratio=max(raw),
        median_ratio=median(raw),
        min_ratio=min(raw),
        raw_ratio=raw,
    )


def _named_total(profile: ProfileSnapshotPhaseProfile) -> int:
    return (
        profile.host_memory_allocate_ns
        + profile.state_download_ns
        + profile.memory_download_ns
        + profile.output_download_ns
        + profile.decode_ns
    )


if __name__ == "__main__":
    raise SystemExit(main())
