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
#   - Pure protocol tests for streamed snapshot window evidence.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Pure protocol tests for streamed snapshot window evidence."""

from __future__ import annotations

from benchmarks.accelerator.profile_snapshot_stream_window_tradeoff import (
    BATCH_SIZE,
)
from benchmarks.accelerator.profile_snapshot_stream_window_tradeoff import (
    WINDOW_ITEMS,
)
from benchmarks.accelerator.profile_snapshot_stream_window_tradeoff import (
    expected_window_count,
)
from benchmarks.accelerator.profile_snapshot_stream_window_tradeoff import (
    rotated_window_order,
)


def test_stream_window_order_rotates_all_routes() -> None:
    """Each consecutive sample moves the first route without omissions."""
    assert rotated_window_order(0) == WINDOW_ITEMS
    assert rotated_window_order(1) == (8, 32, 1)
    assert rotated_window_order(2) == (32, 1, 8)
    assert rotated_window_order(3) == WINDOW_ITEMS


def test_stream_window_count_is_exact_ceiling_division() -> None:
    """Window capacities one/eight/full cover batch thirty-two exactly."""
    assert expected_window_count(1) == BATCH_SIZE
    assert expected_window_count(WINDOW_ITEMS[1]) == (
        BATCH_SIZE // WINDOW_ITEMS[1]
    )
    assert expected_window_count(BATCH_SIZE) == 1
