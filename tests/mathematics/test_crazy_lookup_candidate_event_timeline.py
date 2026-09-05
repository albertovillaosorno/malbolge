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
#   - Deterministic protocol checks for CRAZY candidate CUDA-event timing.
# - Must-Not:
#   - Require CUDA hardware or treat event duration as semantic authority.
# - Allows:
#   - Inputs: event-timeline benchmark constants and shared kernel source.
#   - Outputs: stable identity, ordering, and interpretation assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another event protocol gains independent retained evidence.
# - Merge-When:
#   - Merge when another test owns this exact benchmark protocol.
# - Summary:
#   - Protocol regression for candidate CRAZY CUDA-event timing.
# - Description:
#   - Locks separate identity and isolated-stream interpretation boundaries.
# - Usage:
#   - Run under mathematics validation without a GPU.
# - Defaults:
#   - Fifteen samples mirror the wall-time companion protocol.
#

"""Protocol checks for CRAZY candidate CUDA-event timing."""

from __future__ import annotations

from benchmarks.accelerator.crazy_lookup_address_fanout import WORKLOAD_ID

from benchmarks.accelerator import (
    crazy_lookup_candidate_event_timeline as event,
)
from benchmarks.accelerator import crazy_lookup_candidate_throughput as wall

EXPECTED_BENCHMARK_ID = "cuda-crazy-lookup-candidate-event-timeline-v1"
EXPECTED_TIMELINE_ID = "cuda-independent-stream-kernel-timeline-v1"
EXPECTED_LAUNCH_ID = "cuda-independent-stream-kernel-launch-v1"
EXPECTED_WORKLOAD_ID = "classic-crazy-target-full-domain-multiposition-v1"
TRITWISE_DECLARATION = 'extern "C" __global__ void crazy_tritwise'
LOOKUP_DECLARATION = 'extern "C" __global__ void crazy_lookup'
INTERPRETATION_FRAGMENT = "do not measure default-stream wall time"


def test_candidate_event_timeline_has_separate_stable_protocol() -> None:
    """Device-event timing cannot silently mutate the wall-time benchmark."""
    assert event.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert event.BENCHMARK_ID != wall.BENCHMARK_ID
    assert event.EXPECTED_TIMELINE_ID == EXPECTED_TIMELINE_ID
    assert event.EXPECTED_LAUNCH_ID == EXPECTED_LAUNCH_ID
    assert event.SAMPLE_COUNT == wall.SAMPLE_COUNT
    assert event.WARMUP_COUNT == wall.WARMUP_COUNT
    assert event.GEOMETRIES == wall.GEOMETRIES
    assert WORKLOAD_ID == EXPECTED_WORKLOAD_ID


def test_candidate_event_timeline_alternates_first_geometry() -> None:
    """Odd/even samples reverse which arithmetic geometry is submitted first."""
    assert event.sample_order(0) == (event.TRITWISE, event.LOOKUP)
    assert event.sample_order(1) == (event.LOOKUP, event.TRITWISE)
    assert event.sample_order(2) == event.sample_order(0)


def test_candidate_event_timeline_reuses_exact_kernel_source() -> None:
    """Event timing reuses the same benchmark-only arithmetic kernels."""
    source = wall.candidate_lookup_kernel_source()
    assert TRITWISE_DECLARATION in source
    assert LOOKUP_DECLARATION in source
    assert INTERPRETATION_FRAGMENT in event.INTERPRETATION_LIMIT
