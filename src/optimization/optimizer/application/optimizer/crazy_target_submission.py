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
#   - Deferred exact crazy-target search over candidate submission tickets.
# - Must-Not:
#   - Accept proposals, invent candidates, or evaluate outside exact projection.
# - Allows:
#   - Inputs: one crazy-target request and candidate submission adapter.
#   - Outputs: one neutral search ticket with untrusted exact proposals.
#   - Side effects: candidate-ticket work retained until wait or close.
# - Split-When:
#   - Split when another strategy gains an independent submission lifetime.
# - Merge-When:
#   - Merge when another module owns the same crazy-target ticket contract.
# - Summary:
#   - Exact projected crazy-target search submission.
# - Description:
#   - Retains selector/projection proofs across deferred candidate evaluation.
# - Usage:
#   - Pass as the preferred adapter to submit_search.
# - Defaults:
#   - Candidate protocol violations fail closed before CPU search fallback.
#

"""Deferred exact crazy-target search over candidate submission tickets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.evaluated_search import PreparedCandidateProjection
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.search_submission import SearchExecutionTicket
from accelerator.search_submission import SearchSubmissionAdapter
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchResult

from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import prepare_crazy_target_selection
from optimizer.crazy_target import prepare_projected_crazy_candidate_batch
from optimizer.crazy_target import select_prepared_crazy_target_proposals

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.submission import CandidateEvaluationTicket
    from accelerator.submission import CandidateSubmissionAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchRequest

CRAZY_TARGET_SUBMISSION_ID = "classic-crazy-target-search-submission-v1"


@dataclass(frozen=True, slots=True)
class _CrazyTargetTicketBinding:
    batch: CandidateEvaluationBatch
    candidate: CandidateEvaluationTicket
    capability: AcceleratorCapability
    evaluation_batch: CandidateEvaluationBatch
    request: SearchRequest
    selection_state: object


@final
class CrazyTargetSearchTicket(SearchExecutionTicket):
    """One deferred projected crazy evaluation plus exact selector state."""

    def __init__(self, binding: _CrazyTargetTicketBinding) -> None:
        """Adopt one proof-bound search and candidate-ticket lifetime."""
        self._binding = binding
        self._closed = False
        self._result: SearchResult | None = None

    @override
    def close(self) -> None:
        """Drain candidate work without publishing proposals."""
        if self._closed:
            return
        self._binding.candidate.close()
        self._closed = True

    @override
    def wait(self) -> SearchResult:
        """Complete projected evaluation and publish untrusted proposals.

        Returns:
            Exact proposals selected from the full candidate batch.

        Raises:
            AcceleratorExecutionError: If explicitly closed before completion.

        """
        if self._result is not None:
            return self._result
        if self._closed:
            message = "crazy-target search ticket is closed"
            raise AcceleratorExecutionError(message)
        evidence = self._binding.candidate.wait().validated_against(
            self._binding.evaluation_batch,
            self._binding.capability,
        )
        proposals = select_prepared_crazy_target_proposals(
            self._binding.request,
            self._binding.batch,
            evidence,
            state=self._binding.selection_state,
        )
        result = SearchResult(
            algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
            capability=self._binding.capability,
            proposals=proposals,
            seed=self._binding.request.seed,
        ).validated_against(
            self._binding.request,
            self._binding.capability,
        )
        self._result = result
        return result


@final
class CrazyTargetSearchSubmissionAdapter(SearchSubmissionAdapter):
    """Submit exact projected crazy-target work through candidate tickets."""

    def __init__(self, candidate: CandidateSubmissionAdapter) -> None:
        """Bind one candidate ticket backend to crazy-target search."""
        self._candidate = candidate

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the candidate ticket backend identity.

        Returns:
            Stable capability used for evidence and search result identity.

        """
        return self._candidate.capability()

    @override
    def submit(self, request: SearchRequest) -> SearchExecutionTicket:
        """Prepare exact projection and submit only selector-relevant work.

        Returns:
            Ticket retaining request, batch, projection, and candidate work.

        Raises:
            InvalidAcceleratorWorkError: If strategy projection is invalid.

        """
        validated = request.validated()
        batch = build_crazy_target_batch(validated).validated()
        selection = prepare_crazy_target_selection(validated, batch)
        projection = prepare_projected_crazy_candidate_batch(
            validated,
            batch,
            selection,
        )
        if not isinstance(projection, PreparedCandidateProjection):
            message = "crazy-target projection returned invalid proof type"
            raise InvalidAcceleratorWorkError(message)
        _, evaluation_batch = projection.for_batch(batch)
        ticket = _candidate_ticket(self._candidate.submit(evaluation_batch))
        return CrazyTargetSearchTicket(
            _CrazyTargetTicketBinding(
                batch=batch,
                candidate=ticket,
                capability=self.capability(),
                evaluation_batch=evaluation_batch,
                request=validated,
                selection_state=selection,
            )
        )


def crazy_target_submission_id() -> str:
    """Return the stable projected crazy-target submission identity.

    Returns:
        Versioned identity for contract and live evidence provenance.

    """
    return CRAZY_TARGET_SUBMISSION_ID


def _candidate_ticket(ticket: object) -> CandidateEvaluationTicket:
    if not callable(getattr(ticket, "close", None)) or not callable(
        getattr(ticket, "wait", None)
    ):
        message = "candidate submission adapter returned invalid ticket"
        raise InvalidAcceleratorResultError(message)
    return cast("CandidateEvaluationTicket", ticket)
