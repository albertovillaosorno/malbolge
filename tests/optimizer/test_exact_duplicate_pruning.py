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
#   - Production evidence for conservative exact duplicate pruning.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Production evidence for conservative exact duplicate pruning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from accelerator.work_ports import CandidateProposal
from optimizer import prune_exact_duplicates

if TYPE_CHECKING:
    from accelerator.work_ports import VerificationHint

DUPLICATE_SAVED = 3


def test_duplicate_rich_partition_matches_research_fixture() -> None:
    """Production partition matches duplicate-rich research evidence."""
    pruning = prune_exact_duplicates((
        b"a",
        b"b",
        b"a",
        b"c",
        b"b",
        b"d",
        b"d",
        b"e",
    ))

    assert pruning.representative_indices == (0, 1, 3, 5, 7)
    assert pruning.canonical_indices == (0, 1, 0, 3, 1, 5, 5, 7)
    assert pruning.saved_evaluations() == DUPLICATE_SAVED


def test_unique_partition_retains_null_result() -> None:
    """Production pruning preserves the all-unique research null result."""
    pruning = prune_exact_duplicates((b"a", b"b", b"c", b"d"))

    assert pruning.representative_indices == (0, 1, 2, 3)
    assert pruning.canonical_indices == (0, 1, 2, 3)
    assert pruning.saved_evaluations() == 0


def test_prefix_length_and_one_byte_differences_remain_distinct() -> None:
    """Production pruning uses no similarity relation beyond exact bytes."""
    pruning = prune_exact_duplicates((
        b"abc",
        b"abcd",
        b"ab",
        b"abc\0",
        b"abd",
        b"abc",
    ))

    assert pruning.representative_indices == (0, 1, 2, 3, 4)
    assert pruning.canonical_indices == (0, 1, 2, 3, 4, 0)


def test_byte_distinct_candidates_can_be_distinguished_by_verification() -> (
    None
):
    """Generic verifier authority forbids coarser universal equivalence."""
    accepted_payload = b"prefix-A"
    rejected_payload = b"prefix-B"

    def accepts(
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        return hint is None and candidate.payload == accepted_payload

    accepted = CandidateProposal(
        logical_id="accepted", payload=accepted_payload
    )
    rejected = CandidateProposal(
        logical_id="rejected", payload=rejected_payload
    )

    assert accepts(accepted, None)
    assert not accepts(rejected, None)


def test_exact_duplicate_pruning_supports_injective_u32_values() -> None:
    """Exact integer equality retains the same stable partition contract."""
    pruning = prune_exact_duplicates((7, 1, 7, 4, 1))

    assert pruning.representative_indices == (0, 1, 3)
    assert pruning.canonical_indices == (0, 1, 0, 3, 1)
