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
#   - Deterministic CPU search over an explicit finite candidate corpus.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Deterministic CPU search over an explicit finite candidate corpus."""

from __future__ import annotations

from dataclasses import dataclass
from struct import Struct
from typing import TYPE_CHECKING

from accelerator.cpu import CpuSearchExecutionAdapter
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from accelerator.work_ports import execute_search

from optimizer.pruning import prune_exact_duplicates

if TYPE_CHECKING:
    from accelerator.work_ports import TrustedCandidateVerifier

ENUMERATIVE_ALGORITHM_ID = "deterministic-corpus-enumeration-v1"
_MAGIC = b"MBENUM1\0"
_U32 = Struct("<I")
_MAX_U32 = (1 << 32) - 1


class InvalidEnumerationProblemError(ValueError):
    """Finite enumeration problem encoding or identity is malformed."""


@dataclass(frozen=True, slots=True)
class EnumerationProblem:
    """Canonical finite candidate corpus for deterministic CPU enumeration."""

    candidates: tuple[bytes, ...]

    def validated(self) -> EnumerationProblem:
        """Validate finite corpus representation invariants.

        Returns:
            This immutable problem after validation succeeds.

        Raises:
            InvalidEnumerationProblemError: If corpus representation is invalid.

        """
        if len(self.candidates) > _MAX_U32:
            message = "enumeration candidate count exceeds u32 representation"
            raise InvalidEnumerationProblemError(message)
        for candidate in self.candidates:
            if len(candidate) > _MAX_U32:
                message = (
                    "enumeration candidate length exceeds u32 representation"
                )
                raise InvalidEnumerationProblemError(message)
        return self

    def encode(self) -> bytes:
        """Encode this problem into canonical little-endian bytes.

        Returns:
            Stable problem bytes suitable for ``SearchRequest.problem``.

        """
        validated = self.validated()
        parts = [_MAGIC, _U32.pack(len(validated.candidates))]
        for candidate in validated.candidates:
            parts.extend((_U32.pack(len(candidate)), candidate))
        return b"".join(parts)

    @classmethod
    def decode(cls, payload: bytes) -> EnumerationProblem:
        """Decode and validate canonical finite-corpus problem bytes.

        Returns:
            Validated immutable enumeration problem.

        Raises:
            InvalidEnumerationProblemError: If encoding is malformed.

        """
        if not payload.startswith(_MAGIC):
            message = "enumeration problem has invalid magic"
            raise InvalidEnumerationProblemError(message)
        count, offset = _read_u32(payload, len(_MAGIC))
        candidates: list[bytes] = []
        for _ in range(count):
            length, offset = _read_u32(payload, offset)
            end = offset + length
            if end > len(payload):
                message = "enumeration problem candidate payload is truncated"
                raise InvalidEnumerationProblemError(message)
            candidates.append(payload[offset:end])
            offset = end
        if offset != len(payload):
            message = "enumeration problem has trailing bytes"
            raise InvalidEnumerationProblemError(message)
        return cls(candidates=tuple(candidates)).validated()


def cpu_enumerative_adapter() -> CpuSearchExecutionAdapter:
    """Construct the mandatory deterministic CPU enumerative search adapter.

    Returns:
        CPU search adapter bound to the enumerative algorithm identity.

    """
    return CpuSearchExecutionAdapter(
        ENUMERATIVE_ALGORITHM_ID,
        enumerate_candidates,
    )


def enumerate_candidates(
    request: SearchRequest,
) -> tuple[CandidateProposal, ...]:
    """Enumerate a seeded bounded prefix of one explicit candidate corpus.

    Returns:
        Unique candidate proposals in deterministic seeded corpus order.

    Raises:
        InvalidAcceleratorWorkError: If request selects another algorithm.

    """
    validated = request.validated()
    if validated.algorithm_id != ENUMERATIVE_ALGORITHM_ID:
        message = "enumerative search request selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    problem = EnumerationProblem.decode(validated.problem)
    pruning = prune_exact_duplicates(problem.candidates)
    representatives = pruning.representative_indices
    if not representatives:
        return ()
    count = min(validated.evaluation_budget, len(representatives))
    start = validated.seed % len(representatives)
    return tuple(
        _proposal(
            problem,
            representatives[(start + offset) % len(representatives)],
        )
        for offset in range(count)
    )


def search_and_verify(
    problem: EnumerationProblem,
    evaluation_budget: int,
    verifier: TrustedCandidateVerifier,
    *,
    seed: int = 0,
) -> tuple[CandidateProposal, ...]:
    """Run CPU enumeration and independently verify candidates.

    Returns:
        Accepted candidates in deterministic search order.

    """
    request = SearchRequest(
        algorithm_id=ENUMERATIVE_ALGORITHM_ID,
        evaluation_budget=evaluation_budget,
        problem=problem.encode(),
        seed=seed,
    )
    reference = cpu_enumerative_adapter()
    result = execute_search(request, reference)
    return admit_search_result(result, verifier)


def _proposal(problem: EnumerationProblem, index: int) -> CandidateProposal:
    return CandidateProposal(
        logical_id=f"corpus-{index}",
        payload=problem.candidates[index],
    )


def _read_u32(payload: bytes, offset: int) -> tuple[int, int]:
    end = offset + _U32.size
    if end > len(payload):
        message = "enumeration problem integer field is truncated"
        raise InvalidEnumerationProblemError(message)
    return (_U32.unpack_from(payload, offset)[0], end)
