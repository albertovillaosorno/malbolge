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
#   - Versioned finite classic crazy-preimage comparison challenge identity.
# - Must-Not:
#   - Import production crazy search helpers or infer timing conclusions.
# - Allows:
#   - Inputs: the frozen classic ten-trit one-trit multiplicity construction.
# - Outputs: twelve fixed accumulator/target problems and one workload hash.
# - Side effects: none.
# - Split-When:
#   - Another profile width or challenge sampling rule needs an independent ID.
# - Merge-When:
#   - Another module owns this exact finite problem corpus and encoding.
# - Summary:
#   - Frozen cardinality-spanning classic crazy-preimage challenge.
# - Description:
#   - Covers unreachable and every power-of-two preimage cardinality through
#     1024.
# - Usage:
#   - Consumed by the preregistered crazy-preimage comparison runner.
# - Defaults:
#   - Accumulator zero and exact complete-domain cardinality classes only.
#

"""Finite cardinality-spanning classic crazy-preimage challenge."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from struct import Struct
from typing import Final

CHALLENGE_ID: Final = "classic-crazy-preimage-cardinality-span-v1"
VERIFIER_ID: Final = "classic-crazy-independent-table-v1"
_TRIT_COUNT: Final = 10
_RADIX: Final = 3
_UNREACHABLE_TARGET: Final = 0
_ZERO_ACCUMULATOR: Final = 0
_RECORD = Struct("<III")


@dataclass(frozen=True, slots=True)
class CrazyPreimageChallengeProblem:
    """One fixed classic accumulator/target problem and exact cardinality."""

    accumulator: int
    target: int
    expected_preimages: int


@dataclass(frozen=True, slots=True)
class CrazyPreimageChallenge:
    """Canonical finite problem corpus plus byte-exact workload identity."""

    challenge_id: str
    verifier_id: str
    problems: tuple[CrazyPreimageChallengeProblem, ...]
    workload_sha256: str


def _target_for_exponent(exponent: int) -> int:
    target = 0
    place = 1
    for position in range(_TRIT_COUNT):
        target_trit = 1 if position < exponent else 2
        target += target_trit * place
        place *= _RADIX
    return target


def _problems() -> tuple[CrazyPreimageChallengeProblem, ...]:
    unreachable = CrazyPreimageChallengeProblem(
        accumulator=_ZERO_ACCUMULATOR,
        target=_UNREACHABLE_TARGET,
        expected_preimages=0,
    )
    reachable = tuple(
        CrazyPreimageChallengeProblem(
            accumulator=_ZERO_ACCUMULATOR,
            target=_target_for_exponent(exponent),
            expected_preimages=1 << exponent,
        )
        for exponent in range(_TRIT_COUNT + 1)
    )
    return (unreachable, *reachable)


def _workload_bytes(
    problems: tuple[CrazyPreimageChallengeProblem, ...],
) -> bytes:
    return b"".join(
        _RECORD.pack(
            problem.accumulator,
            problem.target,
            problem.expected_preimages,
        )
        for problem in problems
    )


def challenge() -> CrazyPreimageChallenge:
    """Return the frozen cardinality-spanning challenge.

    Returns:
        Versioned problems and the SHA-256 of their canonical little-endian
        triples ``(accumulator, target, expected_preimages)``.

    """
    problems = _problems()
    return CrazyPreimageChallenge(
        challenge_id=CHALLENGE_ID,
        verifier_id=VERIFIER_ID,
        problems=problems,
        workload_sha256=sha256(_workload_bytes(problems)).hexdigest(),
    )
