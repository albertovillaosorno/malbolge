# File:
#   - submission.py
# Path:
#   - accelerator/cuda/submission.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - CUDA implementation of neutral exact primitive candidate submission.
# - Must-Not:
#   - Publish before wait, reuse resident buffers, or accept candidates.
# - Allows:
#   - Inputs: exact classic primitive candidate batches.
#   - Outputs: validated untrusted evidence through the neutral ticket port.
#   - Side effects: one-shot CUDA uploads, launch, download, and cleanup.
# - Split-When:
#   - Split when another candidate family gains an independent CUDA lifetime.
# - Merge-When:
#   - Merge when another adapter owns identical primitive candidate submission.
# - Summary:
#   - One-shot CUDA tickets for neutral primitive candidate evaluation.
# - Description:
#   - Binds prepared CPU-reference proof to explicit CUDA launch completion.
# - Usage:
#   - Pass as the preferred adapter to submit_candidate_evaluation.
# - Defaults:
#   - No threads; malformed work fails before device submission.
#
# Related documents:
# - accelerator/submission.py
# - docs/technical/integrations/accelerators/cuda-exact-vm-adapter.md
#
# Large file:
#   - false
#

"""CUDA candidate submission through the hardware-neutral ticket contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import CRAZY_EVALUATOR_ID
from accelerator.primitive_candidates import (
    PreparedPrimitiveCandidateEvaluation,
)
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_prepared_primitive_result
from accelerator.primitive_candidates import prepare_crazy_candidate_batch
from accelerator.primitive_candidates import prepare_rotate_candidate_batch
from accelerator.submission import CandidateEvaluationTicket
from accelerator.submission import CandidateSubmissionAdapter
from accelerator.work_ports import InvalidAcceleratorWorkError

if TYPE_CHECKING:
    from accelerator.cuda.exact_primitives import CudaExactPrimitiveAdapter
    from accelerator.cuda.exact_primitives import CudaPrimitiveEvaluationTicket
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateEvaluationResult


@dataclass(frozen=True, slots=True)
class _CudaCandidateTicketBinding:
    capability: AcceleratorCapability
    primitive: CudaPrimitiveEvaluationTicket
    state: PreparedPrimitiveCandidateEvaluation


@final
class CudaPrimitiveCandidateTicket(CandidateEvaluationTicket):
    """Candidate ticket that publishes only exact prepared CUDA evidence."""

    def __init__(self, binding: _CudaCandidateTicketBinding) -> None:
        """Adopt one prepared candidate proof and one CUDA primitive ticket."""
        self._binding = binding
        self._closed = False
        self._result: CandidateEvaluationResult | None = None

    @override
    def close(self) -> None:
        """Drain the primitive ticket without publishing candidate evidence."""
        if self._closed:
            return
        self._binding.primitive.close()
        self._closed = True

    @override
    def wait(self) -> CandidateEvaluationResult:
        """Complete CUDA work and validate exact candidate publication.

        Returns:
            Ordered untrusted evidence equal to the prepared CPU reference.

        Raises:
            AcceleratorExecutionError: If the ticket was explicitly closed.

        """
        if self._result is not None:
            return self._result
        if self._closed:
            message = "CUDA primitive candidate ticket is closed"
            raise AcceleratorExecutionError(message)
        primitive = self._binding.primitive.wait()
        result = encode_prepared_primitive_result(
            self._binding.state,
            primitive,
            self._binding.capability,
        )
        self._result = result
        return result


@final
class CudaPrimitiveCandidateSubmissionAdapter(CandidateSubmissionAdapter):
    """Submit exact classic primitive candidate batches to one CUDA adapter."""

    def __init__(
        self,
        adapter: CudaExactPrimitiveAdapter,
        kind: PrimitiveKind,
    ) -> None:
        """Bind one CUDA adapter to one exact candidate evaluator identity."""
        self._adapter = adapter
        self._evaluator_id = _evaluator_id(kind)
        self._kind = kind

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the wrapped CUDA device identity.

        Returns:
            Stable capability of the exact primitive adapter.

        """
        return self._adapter.capability()

    @override
    def submit(
        self,
        batch: CandidateEvaluationBatch,
    ) -> CandidateEvaluationTicket:
        """Prepare exact proof and submit one one-shot CUDA primitive launch.

        Returns:
            Candidate ticket owning proof, launch, output, and cleanup lifetime.

        Raises:
            InvalidAcceleratorWorkError: If preparation loses exact proof.

        """
        state = _prepare_state(batch, self._kind)
        candidate_batch, primitive, expected = state.for_adapter(
            self._evaluator_id,
            self._kind,
        )
        if candidate_batch is not batch or expected is None:
            message = "CUDA candidate submission lost prepared reference proof"
            raise InvalidAcceleratorWorkError(message)
        ticket = self._adapter.submit_prepared(primitive)
        return CudaPrimitiveCandidateTicket(
            _CudaCandidateTicketBinding(
                capability=self.capability(),
                primitive=ticket,
                state=state,
            )
        )


def _evaluator_id(kind: PrimitiveKind) -> str:
    if kind is PrimitiveKind.CRAZY:
        return CRAZY_EVALUATOR_ID
    return ROTATE_EVALUATOR_ID


def _prepare_state(
    batch: CandidateEvaluationBatch,
    kind: PrimitiveKind,
) -> PreparedPrimitiveCandidateEvaluation:
    prepared = (
        prepare_crazy_candidate_batch(batch)
        if kind is PrimitiveKind.CRAZY
        else prepare_rotate_candidate_batch(batch)
    )
    if not isinstance(prepared, PreparedPrimitiveCandidateEvaluation):
        message = "primitive candidate preparation returned invalid state"
        raise InvalidAcceleratorWorkError(message)
    return prepared
