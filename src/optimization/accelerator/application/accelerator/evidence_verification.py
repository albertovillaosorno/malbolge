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
#   - Verification-assist bridge for candidate-evaluation evidence backends.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Verification-assist bridge for candidate-evaluation evidence backends."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import VerificationAssistAdapter
from accelerator.work_ports import VerificationAssistResult
from accelerator.work_ports import VerificationHint

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import VerificationAssistBatch


@final
class EvidenceVerificationAssistAdapter(VerificationAssistAdapter):
    """Expose untrusted candidate evidence as optional verification hints."""

    def __init__(
        self,
        adapter: CandidateEvaluationAdapter,
        *,
        evaluator_id: str,
        verifier_id: str,
    ) -> None:
        """Bind one evidence evaluator to one verification-assist identity.

        Raises:
            InvalidAcceleratorWorkError: If either bound identity is empty.

        """
        if not evaluator_id:
            message = "verification evidence evaluator ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        if not verifier_id:
            message = "verification assist ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._adapter = adapter
        self._evaluator_id = evaluator_id
        self._verifier_id = verifier_id

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the wrapped evidence backend identity.

        Returns:
            Exact capability reported by the wrapped candidate evaluator.

        """
        return self._adapter.capability()

    @override
    def assist(
        self,
        batch: VerificationAssistBatch,
    ) -> VerificationAssistResult:
        """Evaluate candidates and expose results only as untrusted hints.

        Returns:
            Ordered hints carrying the wrapped candidate evidence payloads.

        Raises:
            InvalidAcceleratorWorkError: If verification identity mismatches.

        """
        validated = batch.validated()
        if validated.verifier_id != self._verifier_id:
            message = "verification batch selects a different assist adapter"
            raise InvalidAcceleratorWorkError(message)
        evaluation_batch = CandidateEvaluationBatch(
            evaluator_id=self._evaluator_id,
            items=validated.items,
        ).validated()
        capability = self.capability()
        evidence = self._adapter.evaluate(evaluation_batch)
        items = evidence.materialized_items_against(
            evaluation_batch,
            capability,
        )
        return VerificationAssistResult(
            capability=capability,
            hints=tuple(
                VerificationHint(
                    logical_id=item.logical_id,
                    payload=item.payload,
                )
                for item in items
            ),
            verifier_id=validated.verifier_id,
        )
