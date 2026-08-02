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
#   - Pure protocol tests for paired snapshot overlap evidence.
# - Must-Not:
#   - Execute CUDA or change product semantics.
# - Allows:
#   - Inputs: route identities and fixed window capacities.
#   - Outputs: deterministic route-order and cardinality assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another benchmark protocol needs distinct pure helpers.
# - Merge-When:
#   - Merge when another test owns the same route-order contract.
# - Summary:
#   - Pure tests for synchronous versus double-buffer snapshot evidence.
# - Description:
#   - Verifies cyclic ordering and exact callback/prefetch cardinality.
# - Usage:
#   - Collected by the repository pytest suite.
# - Defaults:
#   - Unknown route identities fail closed.
#

"""Pure protocol tests for current-profile snapshot overlap evidence."""

from __future__ import annotations

from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    BATCH_SIZE,
)
from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    ROUTE_IDS,
)
from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    expected_prefetch_count,
)
from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    expected_window_count,
)
from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    rotated_route_order,
)
from benchmarks.accelerator.profile_snapshot_double_buffer_overlap import (
    route_spec,
)
import pytest


def test_overlap_route_order_rotates_all_routes() -> None:
    """Every sample rotates the first route without omission or duplication."""
    assert rotated_route_order(0) == ROUTE_IDS
    assert rotated_route_order(1) == ROUTE_IDS[1:] + ROUTE_IDS[:1]
    assert rotated_route_order(2) == ROUTE_IDS[2:] + ROUTE_IDS[:2]
    assert rotated_route_order(len(ROUTE_IDS)) == ROUTE_IDS


def test_overlap_window_and_prefetch_counts_are_exact() -> None:
    """Window one/eight callbacks and prefetches use exact ceilings."""
    assert expected_window_count(1) == BATCH_SIZE
    assert expected_prefetch_count(1) == BATCH_SIZE - 1
    assert expected_window_count(8) == BATCH_SIZE // 8
    assert expected_prefetch_count(8) == (BATCH_SIZE // 8) - 1


def test_overlap_route_spec_is_closed_and_explicit() -> None:
    """Stable route identities resolve one exact overlap/window combination."""
    assert route_spec("sync-window-1") == (False, 1)
    assert route_spec("overlap-window-1") == (True, 1)
    assert route_spec("sync-window-8") == (False, 8)
    assert route_spec("overlap-window-8") == (True, 8)
    with pytest.raises(ValueError, match="unknown snapshot overlap route"):
        _ = route_spec("overlap-window-32")
