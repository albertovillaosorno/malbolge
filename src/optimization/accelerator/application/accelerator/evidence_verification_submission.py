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
#   - Candidate-ticket-backed optional verification-assist submission.
# - Must-Not:
#   - Accept candidates, invent hints, or expose candidate backend handles.
# - Allows:
#   - Inputs: one verification batch and one candidate submission adapter.
#   - Outputs: one ticket publishing exact candidate evidence as hints.
#   - Side effects: nested candidate work retained until wait or close.
# - Split-When:
#   - Split when another evidence family gains an independent hint lifetime.
# - Merge-When:
#   - Merge when another adapter owns identical candidate-backed assistance.
# - Summary:
#   - Candidate-ticket-backed verification-assist submission.
# - Description:
#   - Preserves evaluator/verifier identity across deferred candidate evidence.
# - Usage:
#   - Pass as preferred adapter to submit_verification_hints.
# - Defaults:
#   - Nested protocol violations fail closed before optional empty completion.
#

"""Candidate-ticket-backed optional verification-assist submission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.verification_submission import VerificationAssistTicket
from accelerator.verification_submission import VerificationSubmissionAdapter
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import VerificationAssistResult
from accelerator.work_ports import VerificationHint

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.submission import CandidateEvaluationTicket
    from accelerator.submission import CandidateSubmissionAdapter
    from accelerator.work_ports import VerificationAssistBatch

EVIDENCE_VERIFICATION_SUBMISSION_ID = (
    "candidate-evidence-verification-submission-v1"
)


@dataclass(frozen=True, slots=True)
class _EvidenceVerificationTicketBinding:
    candidate: CandidateEvaluationTicket
    capability: AcceleratorCapability
    evaluation_batch: CandidateEvaluationBatch
    verification_batch: VerificationAssistBatch


@final
class EvidenceVerificationTicket(VerificationAssistTicket):
    """Optional hint ticket retaining exact nested candidate work."""

    def __init__(self, binding: _EvidenceVerificationTicketBinding) -> None:
        """Adopt one exact verification request and candidate ticket."""
        self._binding = binding
        self._closed = False
        self._result: VerificationAssistResult | None = None

    @override
    def close(self) -> None:
        """Drain candidate work without publishing verification hints."""
        if self._closed:
            return
        self._binding.candidate.close()
        self._closed = True

    @override
    def wait(self) -> VerificationAssistResult:
        """Complete candidate work and publish exact untrusted hints.

        Returns:
            Ordered hints carrying the exact candidate evidence payloads.

        Raises:
            AcceleratorExecutionError: If explicitly closed before completion.

        """
        if self._result is not None:
            return self._result
        if self._closed:
            message = "evidence verification ticket is closed"
            raise AcceleratorExecutionError(message)
        evidence = self._binding.candidate.wait()
        items = evidence.materialized_items_against(
            self._binding.evaluation_batch,
            self._binding.capability,
        )
        result = VerificationAssistResult(
            capability=self._binding.capability,
            hints=tuple(
                VerificationHint(
                    logical_id=item.logical_id,
                    payload=item.payload,
                )
                for item in items
            ),
            verifier_id=self._binding.verification_batch.verifier_id,
        ).validated_against(
            self._binding.verification_batch,
            self._binding.capability,
        )
        self._result = result
        return result


@final
class EvidenceVerificationSubmissionAdapter(VerificationSubmissionAdapter):
    """Submit candidate evidence as deferred optional verification hints."""

    def __init__(
        self,
        candidate: CandidateSubmissionAdapter,
        *,
        evaluator_id: str,
        verifier_id: str,
    ) -> None:
        """Bind one candidate ticket backend to one verification identity.

        Raises:
            InvalidAcceleratorWorkError: If either bound identity is empty.

        """
        if not evaluator_id:
            message = "verification evidence evaluator ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        if not verifier_id:
            message = "verification assist ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._candidate = candidate
        self._evaluator_id = evaluator_id
        self._verifier_id = verifier_id

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the candidate ticket backend identity.

        Returns:
            Stable capability used for evidence and hint result identity.

        """
        return self._candidate.capability()

    @override
    def submit(
        self,
        batch: VerificationAssistBatch,
    ) -> VerificationAssistTicket:
        """Submit exact candidate evidence without publishing hints.

        Returns:
            Ticket retaining verification and candidate-evaluation lifetimes.

        Raises:
            InvalidAcceleratorWorkError: If verifier identity mismatches.

        """
        validated = batch.validated()
        if validated.verifier_id != self._verifier_id:
            message = "verification batch selects a different assist adapter"
            raise InvalidAcceleratorWorkError(message)
        evaluation_batch = CandidateEvaluationBatch(
            evaluator_id=self._evaluator_id,
            items=validated.items,
        ).validated()
        ticket = _candidate_ticket(self._candidate.submit(evaluation_batch))
        return EvidenceVerificationTicket(
            _EvidenceVerificationTicketBinding(
                candidate=ticket,
                capability=self.capability(),
                evaluation_batch=evaluation_batch,
                verification_batch=validated,
            )
        )


def evidence_verification_submission_id() -> str:
    """Return the stable candidate-backed hint submission identity.

    Returns:
        Versioned identity for contract and live evidence provenance.

    """
    return EVIDENCE_VERIFICATION_SUBMISSION_ID


def _candidate_ticket(ticket: object) -> CandidateEvaluationTicket:
    if not callable(getattr(ticket, "close", None)) or not callable(
        getattr(ticket, "wait", None)
    ):
        message = "candidate submission adapter returned invalid ticket"
        raise InvalidAcceleratorResultError(message)
    return cast("CandidateEvaluationTicket", ticket)
