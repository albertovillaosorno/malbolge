# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Search execution backed by hardware-neutral candidate evaluation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchResult

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateEvaluationResult
    from accelerator.work_ports import CandidateProposal
    from accelerator.work_ports import SearchRequest


type SearchBatchBuilder = Callable[[SearchRequest], CandidateEvaluationBatch]
type SearchProposalSelector = Callable[
    [SearchRequest, CandidateEvaluationBatch, CandidateEvaluationResult],
    tuple[CandidateProposal, ...],
]


@final
class EvaluatedSearchExecutionAdapter(SearchExecutionAdapter):
    """Run one search strategy through a replaceable candidate evaluator."""

    def __init__(
        self,
        algorithm_id: str,
        adapter: CandidateEvaluationAdapter,
        *,
        batch_builder: SearchBatchBuilder,
        proposal_selector: SearchProposalSelector,
    ) -> None:
        """Bind one strategy to one replaceable evidence backend.

        Raises:
            InvalidAcceleratorWorkError: If algorithm identity is empty.

        """
        if not algorithm_id:
            message = "search algorithm ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._adapter = adapter
        self._algorithm_id = algorithm_id
        self._batch_builder = batch_builder
        self._proposal_selector = proposal_selector

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the wrapped candidate-evaluation backend identity.

        Returns:
            Exact capability reported by the wrapped evaluator.

        """
        return self._adapter.capability()

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        """Evaluate a bounded corpus and return untrusted selected proposals.

        Returns:
            Structurally validated proposals selected from evaluated candidates.

        Raises:
            InvalidAcceleratorWorkError: If request identity or budget is
                invalid.

        """
        validated = request.validated()
        if validated.algorithm_id != self._algorithm_id:
            message = "search request selects a different algorithm"
            raise InvalidAcceleratorWorkError(message)
        batch = self._batch_builder(validated).validated()
        if len(batch.items) > validated.evaluation_budget:
            message = (
                "evaluated search batch exceeds declared evaluation budget"
            )
            raise InvalidAcceleratorWorkError(message)
        capability = self.capability()
        evidence = self._adapter.evaluate(batch).validated_against(
            batch,
            capability,
        )
        proposals = self._proposal_selector(validated, batch, evidence)
        _validate_proposal_membership(proposals, batch)
        return SearchResult(
            algorithm_id=self._algorithm_id,
            capability=capability,
            proposals=proposals,
            seed=validated.seed,
        ).validated_against(validated, capability)


def _validate_proposal_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
) -> None:
    candidates = {item.logical_id: item.payload for item in batch.items}
    for proposal in proposals:
        payload = candidates.get(proposal.logical_id)
        if payload is None or payload != proposal.payload:
            message = (
                "evaluated search proposal was not in evaluated candidate batch"
            )
            raise InvalidAcceleratorWorkError(message)
