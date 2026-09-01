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
#   - Dense concatenation of the nine proved exact-S5 stabilizer rank strata.
# - Must-Not:
#   - Re-prove any stratum-local rank or alter its canonical ordering.
# - Allows:
#   - Inputs: a stabilizer-stratum identifier and its proved dense local rank.
#   - Outputs: one complete dense S5 rank and inverse block dispatch.
#   - Side effects: none.
# - Split-When:
#   - Another endpoint arity needs a separate stabilizer-stratum composition.
# - Merge-When:
#   - A generic finite-stratum dense-rank concatenation theorem is introduced.
# - Summary:
#   - Prefix disjoint stabilizer blocks and preserve each local dense rank.
# - Description:
#   - Dense local bijections compose by cumulative cardinality offsets.
# - Usage:
#   - Complete order-120 S5 rank after all nine local strata are proved.
# - Defaults:
#   - The exact mass-fourteen block vector is retained as boundary evidence.
#

"""Dense composition of every exact-S5 stabilizer rank stratum."""

from __future__ import annotations

_STRATA = (
    "trivial",
    "transposition",
    "double-transposition",
    "v4-disjoint",
    "s3",
    "order8",
    "order12",
    "order24",
    "v4-transitive",
)
_MASS_FOURTEEN_COUNTS = (
    6_689_862,
    239_656,
    21_920,
    10_466,
    402,
    106,
    174,
    6,
    194,
)
_MASS_FOURTEEN_TOTAL = 6_962_786


def _offset(counts: tuple[int, ...], stratum: int) -> int:
    return sum(counts[:stratum])


def _rank(counts: tuple[int, ...], stratum: int, local_rank: int) -> int | None:
    if stratum < 0 or stratum >= len(counts):
        return None
    if local_rank < 0 or local_rank >= counts[stratum]:
        return None
    return _offset(counts, stratum) + local_rank


def _unrank(counts: tuple[int, ...], rank: int) -> tuple[int, int] | None:
    if rank < 0 or rank >= sum(counts):
        return None
    remaining = rank
    for stratum, count in enumerate(counts):
        if remaining < count:
            return stratum, remaining
        remaining -= count
    raise AssertionError


def test_finite_dense_strata_concatenate_without_gaps() -> None:
    """Finite dense local counts compose to one dense interval."""
    for counts in ((1,), (2, 3), (0, 2, 1), (4, 0, 3, 2)):
        observed: list[int] = []
        for stratum, count in enumerate(counts):
            observed.extend(
                rank
                for local in range(count)
                if (rank := _rank(counts, stratum, local)) is not None
            )
        assert observed == list(range(sum(counts)))
        for rank in observed:
            decoded = _unrank(counts, rank)
            assert decoded is not None
            stratum, local = decoded
            assert _rank(counts, stratum, local) == rank


def test_mass_fourteen_complete_s5_blocks_are_exact_and_dense() -> None:
    """The nine proved mass-14 strata exactly fill the full S5 quotient."""
    assert len(_STRATA) == len(_MASS_FOURTEEN_COUNTS)
    assert sum(_MASS_FOURTEEN_COUNTS) == _MASS_FOURTEEN_TOTAL
    boundaries: list[int] = []
    for stratum, count in enumerate(_MASS_FOURTEEN_COUNTS):
        first = _rank(_MASS_FOURTEEN_COUNTS, stratum, 0)
        last = _rank(_MASS_FOURTEEN_COUNTS, stratum, count - 1)
        assert first is not None
        assert last is not None
        boundaries.extend((first, last))
        assert _unrank(_MASS_FOURTEEN_COUNTS, first) == (stratum, 0)
        assert _unrank(_MASS_FOURTEEN_COUNTS, last) == (stratum, count - 1)
    assert boundaries[0] == 0
    assert boundaries[-1] == _MASS_FOURTEEN_TOTAL - 1
