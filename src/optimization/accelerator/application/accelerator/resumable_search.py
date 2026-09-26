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
#   - Backend-neutral resume execution for ordinary evaluated-search prefixes.
# - Must-Not:
#   - Treat restored evidence or accelerator proposals as acceptance authority.
# - Allows:
#   - Inputs: strategy, evaluator, request, and canonical checkpoint bytes.
#   - Outputs: structurally validated untrusted search proposals.
#   - Side effects: only explicit candidate evaluation of the unfinished suffix.
# - Split-When:
#   - Split when prepared-search resume needs independently durable state.
# - Merge-When:
#   - Merge when ordinary evaluated search directly owns resume execution.
# - Summary:
#   - Resume ordinary evaluated search from a completed evidence prefix.
# - Description:
#   - Rebuilds exact candidates, evaluates only the suffix, then reselects.
# - Usage:
#   - Use after decoding durable evaluated-search checkpoint state.
# - Defaults:
#   - Identity, result, proposal, and checkpoint mismatches fail closed.
#

"""Backend-neutral resume execution for ordinary evaluated search."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import final

from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import PreparedCandidateMembershipIndex
from accelerator.search_checkpoint import decode_search_checkpoint
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchResult
from accelerator.work_ports import candidate_work_items_suffix
from accelerator.work_ports import validated_candidate_evaluation_result

RESUMABLE_EVALUATED_SEARCH_ID = "evaluated-search-prefix-resume-v1"

if TYPE_CHECKING:
    from accelerator.evaluated_search import EvaluatedSearchStrategy
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvidence
    from accelerator.work_ports import CandidateProposal
    from accelerator.work_ports import SearchRequest


def resumable_evaluated_search_id() -> str:
    """Return the stable ordinary evaluated-search resume identity.

    Returns:
        Stable identity for progress and differential evidence.

    """
    return RESUMABLE_EVALUATED_SEARCH_ID


@final
class ResumableEvaluatedSearchExecution:
    """Bind one ordinary evaluated-search strategy to durable resume state."""

    def __init__(
        self,
        algorithm_id: str,
        adapter: CandidateEvaluationAdapter,
        strategy: EvaluatedSearchStrategy,
    ) -> None:
        """Validate and retain one exact search strategy and evaluator."""
        self._execution = EvaluatedSearchExecutionAdapter(
            algorithm_id,
            adapter,
            strategy,
        )
        self._algorithm_id = algorithm_id
        self._adapter = adapter
        self._batch_builder = strategy.batch_builder
        self._proposal_selector = strategy.proposal_selector

    def resume(
        self,
        request: SearchRequest,
        checkpoint: bytes,
    ) -> SearchResult:
        """Resume one ordinary search from exact completed evidence.

        Returns:
            Structurally valid untrusted proposals produced from restored
            evidence plus newly evaluated suffix evidence.

        """
        validated_request = _validated_request(request, self._algorithm_id)
        batch = _validated_batch(
            validated_request,
            self._batch_builder(validated_request),
        )
        state = decode_search_checkpoint(checkpoint, validated_request, batch)
        capability = self._execution.capability()
        remaining_batch = CandidateEvaluationBatch(
            evaluator_id=batch.evaluator_id,
            items=candidate_work_items_suffix(
                batch.items,
                state.completed_units,
            ),
        ).validated()
        remaining = _remaining_evidence(
            self._adapter,
            remaining_batch,
            capability,
        )
        evidence = CandidateEvaluationResult(
            capability=capability,
            evaluator_id=batch.evaluator_id,
            items=state.completed_evidence + remaining,
        ).validated_against(batch, capability)
        proposals = self._proposal_selector(
            validated_request,
            batch,
            evidence,
        )
        result = SearchResult(
            algorithm_id=self._algorithm_id,
            capability=capability,
            proposals=proposals,
            seed=validated_request.seed,
        ).validated_against(validated_request, capability)
        _validate_membership(result.proposals, batch)
        return result


def _validated_request(
    request: SearchRequest,
    algorithm_id: str,
) -> SearchRequest:
    validated = request.validated()
    if validated.algorithm_id != algorithm_id:
        message = "search request selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    return validated


def _validated_batch(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> CandidateEvaluationBatch:
    validated = batch.validated()
    if len(validated.items) > request.evaluation_budget:
        message = "evaluated search batch exceeds declared evaluation budget"
        raise InvalidAcceleratorWorkError(message)
    return validated


def _remaining_evidence(
    adapter: CandidateEvaluationAdapter,
    batch: CandidateEvaluationBatch,
    capability: AcceleratorCapability,
) -> tuple[CandidateEvidence, ...]:
    if not batch.items:
        return ()
    result = validated_candidate_evaluation_result(adapter.evaluate(batch))
    validated = result.validated_against(batch, capability)
    return validated.materialized_items_against(batch, capability)


def _validate_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
) -> None:
    if not proposals:
        return
    membership = PreparedCandidateMembershipIndex.prepare(batch)
    for proposal in proposals:
        if not membership.contains(batch, proposal):
            message = (
                "evaluated search proposal was not in evaluated candidate batch"
            )
            raise InvalidAcceleratorWorkError(message)
