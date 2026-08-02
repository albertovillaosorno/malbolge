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
#   - Portable CPU callback adapters for hardware-neutral work ports.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Portable CPU callback adapters for hardware-neutral work ports."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.exact_primitives import AcceleratorCapability
from accelerator.work_ports import CandidateEvaluationAdapter
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateEvidence
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchResult

if TYPE_CHECKING:
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchRequest

CPU_WORK_CAPABILITY = AcceleratorCapability(
    backend_id="cpu-reference",
    device_arch="scalar",
    device_name="portable-cpu",
)

type CandidateEvaluationHandler = Callable[[bytes], bytes]
type SearchHandler = Callable[[SearchRequest], tuple[CandidateProposal, ...]]


@final
class CpuCandidateEvaluationAdapter(CandidateEvaluationAdapter):
    """Mandatory CPU execution capacity for one candidate evaluator."""

    def __init__(
        self,
        evaluator_id: str,
        handler: CandidateEvaluationHandler,
    ) -> None:
        """Bind one evaluator identity to a deterministic CPU callback.

        Raises:
            InvalidAcceleratorWorkError: If the evaluator identity is empty.

        """
        if not evaluator_id:
            message = "candidate evaluator ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._evaluator_id = evaluator_id
        self._handler = handler

    @override
    def capability(self) -> AcceleratorCapability:
        """Return stable portable CPU backend identity.

        Returns:
            Portable scalar CPU capability identity.

        """
        return CPU_WORK_CAPABILITY

    @override
    def evaluate(
        self, batch: CandidateEvaluationBatch
    ) -> CandidateEvaluationResult:
        """Evaluate every candidate through the configured CPU callback.

        Returns:
            Ordered untrusted candidate evidence from the CPU callback.

        Raises:
            InvalidAcceleratorWorkError: If the evaluator identity differs.

        """
        validated = batch.validated()
        if validated.evaluator_id != self._evaluator_id:
            message = "candidate batch selects a different evaluator"
            raise InvalidAcceleratorWorkError(message)
        items = tuple(
            CandidateEvidence(
                logical_id=item.logical_id,
                payload=self._handler(item.payload),
            )
            for item in validated.items
        )
        return CandidateEvaluationResult(
            capability=CPU_WORK_CAPABILITY,
            evaluator_id=self._evaluator_id,
            items=items,
        )


@final
class CpuSearchExecutionAdapter(SearchExecutionAdapter):
    """Mandatory CPU execution capacity for one explicit search strategy."""

    def __init__(self, algorithm_id: str, handler: SearchHandler) -> None:
        """Bind one search identity to a deterministic CPU callback.

        Raises:
            InvalidAcceleratorWorkError: If the algorithm identity is empty.

        """
        if not algorithm_id:
            message = "search algorithm ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._algorithm_id = algorithm_id
        self._handler = handler

    @override
    def capability(self) -> AcceleratorCapability:
        """Return stable portable CPU backend identity.

        Returns:
            Portable scalar CPU capability identity.

        """
        return CPU_WORK_CAPABILITY

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        """Execute one validated search request on the CPU callback.

        Returns:
            Structurally validated untrusted search proposals.

        Raises:
            InvalidAcceleratorWorkError: If the algorithm identity differs.

        """
        validated = request.validated()
        if validated.algorithm_id != self._algorithm_id:
            message = "search request selects a different algorithm"
            raise InvalidAcceleratorWorkError(message)
        proposals = self._handler(validated)
        result = SearchResult(
            algorithm_id=self._algorithm_id,
            capability=CPU_WORK_CAPABILITY,
            proposals=proposals,
            seed=validated.seed,
        )
        return result.validated_against(validated, CPU_WORK_CAPABILITY)
