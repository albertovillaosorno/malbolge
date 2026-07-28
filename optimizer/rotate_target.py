# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Deterministic exact classic rotate-target corpus search."""

from __future__ import annotations

from dataclasses import dataclass
from struct import Struct
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import EvaluatedSearchStrategy
from accelerator.evaluated_search import PreparedCandidateExecution
from accelerator.evaluated_search import PreparedProposalSelection
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import ROTATE_HIGH_TRIT_WEIGHT
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.primitive_candidates import iter_primitive_evidence_values
from accelerator.primitive_candidates import prepare_rotate_candidate_batch
from accelerator.primitive_candidates import (
    prepared_primitive_reference_word_count,
)
from accelerator.primitive_candidates import primitive_evidence_value_at
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import TrustedCandidateVerifier
from optimizer.pruning import prune_exact_duplicates

if TYPE_CHECKING:
    from accelerator.exact_primitives import ExactPrimitiveAdapter
    from accelerator.work_ports import CandidateEvaluationResult
    from accelerator.work_ports import SearchRequest
    from accelerator.work_ports import VerificationHint

ROTATE_TARGET_ALGORITHM_ID = "classic-rotate-target-search-v1"
_MAGIC = b"MBRTS1\0"
_U32 = Struct("<I")
_MAX_U32 = (1 << 32) - 1
_PREPARED_ROTATE_SELECTION_PROOF = object()


@dataclass(frozen=True, slots=True)
class PreparedRotateTargetSelection:
    """Proof-bound exact candidate positions for one rotate target."""

    request: SearchRequest
    batch: CandidateEvaluationBatch
    target: int
    positions: tuple[int, ...]
    _proof: object

    def for_selection(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
    ) -> tuple[int, tuple[int, ...]]:
        """Return positions only for the request/batch that prepared them.

        Returns:
            Exact target and evaluated request-order candidate positions.

        Raises:
            InvalidAcceleratorWorkError: If state is forged or mismatched.

        """
        if self._proof is not _PREPARED_ROTATE_SELECTION_PROOF:
            message = "prepared rotate selection state is forged"
            raise InvalidAcceleratorWorkError(message)
        if self.request is not request or self.batch is not batch:
            message = "prepared rotate selection state changed request or batch"
            raise InvalidAcceleratorWorkError(message)
        return (self.target, self.positions)

    def position_count(self) -> int:
        """Return proof-validated exact candidate-position count.

        Returns:
            Number of evaluated positions that can rotate to the target.

        Raises:
            InvalidAcceleratorWorkError: If this state was forged.

        """
        if self._proof is not _PREPARED_ROTATE_SELECTION_PROOF:
            message = "prepared rotate selection state is forged"
            raise InvalidAcceleratorWorkError(message)
        return len(self.positions)


class InvalidRotateTargetProblemError(ValueError):
    """Rotate-target search problem encoding or value domain is malformed."""


@dataclass(frozen=True, slots=True)
class RotateTargetProblem:
    """Canonical target plus finite classic-word candidate corpus."""

    target: int
    candidates: tuple[int, ...]

    def validated(self) -> RotateTargetProblem:
        """Validate target and candidate representation invariants.

        Returns:
            This immutable problem after validation succeeds.

        Raises:
            InvalidRotateTargetProblemError: If count or word domain is invalid.

        """
        if not 0 <= self.target <= MAX_WORD:
            message = f"rotate target outside classic domain: {self.target}"
            raise InvalidRotateTargetProblemError(message)
        if len(self.candidates) > _MAX_U32:
            message = "rotate target candidate count exceeds u32 representation"
            raise InvalidRotateTargetProblemError(message)
        for value in self.candidates:
            if not 0 <= value <= MAX_WORD:
                message = f"rotate candidate outside classic domain: {value}"
                raise InvalidRotateTargetProblemError(message)
        return self

    def encode(self) -> bytes:
        """Encode this search problem into canonical little-endian bytes.

        Returns:
            Stable bytes suitable for ``SearchRequest.problem``.

        """
        validated = self.validated()
        parts = [
            _MAGIC,
            _U32.pack(validated.target),
            _U32.pack(len(validated.candidates)),
        ]
        parts.extend(_U32.pack(value) for value in validated.candidates)
        return b"".join(parts)

    @classmethod
    def decode(cls, payload: bytes) -> RotateTargetProblem:
        """Decode canonical rotate-target search bytes.

        Returns:
            Validated immutable rotate-target problem.

        """
        target, count, offset = _decode_header(payload)
        candidates = tuple(
            _U32.unpack_from(payload, offset + (index * _U32.size))[0]
            for index in range(count)
        )
        return cls(target=target, candidates=candidates).validated()

    @classmethod
    def decode_target(cls, payload: bytes) -> int:
        """Decode only the structurally validated classic-domain target.

        Returns:
            Target word without materializing the candidate corpus.

        """
        target, _, _ = _decode_header(payload)
        _ = cls(target=target, candidates=()).validated()
        return target


def rotate_target_search_adapter(
    primitive: ExactPrimitiveAdapter,
) -> EvaluatedSearchExecutionAdapter:
    """Bind rotate-target search to one exact primitive backend.

    Returns:
        Search adapter whose capability is inherited from ``primitive``.

    """
    evaluator = PrimitiveCandidateEvaluationAdapter(
        primitive,
        PrimitiveKind.ROTATE,
    )
    return EvaluatedSearchExecutionAdapter(
        ROTATE_TARGET_ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=build_rotate_target_batch,
            proposal_selector=select_rotate_target_proposals,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=prepare_rotate_candidate_batch,
                evaluator=evaluator.evaluate_prepared,
                state_count=prepared_primitive_reference_word_count,
            ),
            prepared_selection=PreparedProposalSelection(
                state_preparer=prepare_rotate_target_selection,
                selector=select_prepared_rotate_target_proposals,
                state_count=count_prepared_rotate_target_positions,
            ),
        ),
    )


def cpu_rotate_target_search_adapter() -> EvaluatedSearchExecutionAdapter:
    """Construct the mandatory scalar rotate-target search reference.

    Returns:
        CPU-backed exact rotate-target search adapter.

    """
    return rotate_target_search_adapter(CpuExactPrimitiveAdapter())


def build_rotate_target_batch(
    request: SearchRequest,
) -> CandidateEvaluationBatch:
    """Build the deterministic seeded evaluation batch for one search request.

    Returns:
        Stable first representatives bounded by the declared evaluation budget.

    Raises:
        InvalidAcceleratorWorkError: If request selects another algorithm.

    """
    validated = request.validated()
    if validated.algorithm_id != ROTATE_TARGET_ALGORITHM_ID:
        message = "rotate target search request selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    problem = RotateTargetProblem.decode(validated.problem)
    encoded = tuple(
        encode_rotate_candidate(value) for value in problem.candidates
    )
    representatives = prune_exact_duplicates(encoded).representative_indices
    if not representatives:
        selected: tuple[int, ...] = ()
    else:
        count = min(validated.evaluation_budget, len(representatives))
        start = validated.seed % len(representatives)
        selected = tuple(
            representatives[(start + offset) % len(representatives)]
            for offset in range(count)
        )
    return CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=tuple(
            CandidateWorkItem(
                logical_id=f"corpus-{index}",
                payload=encoded[index],
            )
            for index in selected
        ),
    )


def prepare_rotate_target_selection(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare exact request-order positions for the rotate target preimage.

    Returns:
        Strategy-bound immutable selector state.

    Raises:
        InvalidAcceleratorWorkError: If algorithm/evaluator identity mismatches.

    """
    validated_request = request.validated()
    if validated_request.algorithm_id != ROTATE_TARGET_ALGORITHM_ID:
        message = "rotate target selection selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    validated_batch = batch.validated()
    if validated_batch.evaluator_id != ROTATE_EVALUATOR_ID:
        message = "rotate target selection uses a different evaluator"
        raise InvalidAcceleratorWorkError(message)
    target = RotateTargetProblem.decode_target(validated_request.problem)
    payload = encode_rotate_candidate(_inverse_rotate(target))
    positions = tuple(
        index
        for index, item in enumerate(validated_batch.items)
        if item.payload == payload
    )
    return PreparedRotateTargetSelection(
        request=validated_request,
        batch=validated_batch,
        target=target,
        positions=positions,
        _proof=_PREPARED_ROTATE_SELECTION_PROOF,
    )


def count_prepared_rotate_target_positions(state: object) -> int:
    """Return proof-validated prepared rotate candidate-position count.

    Returns:
        Number of exact preimage positions in the evaluated batch.

    Raises:
        InvalidAcceleratorWorkError: If selector state has wrong type/proof.

    """
    if not isinstance(state, PreparedRotateTargetSelection):
        message = "prepared rotate selection state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    return state.position_count()


def select_prepared_rotate_target_proposals(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
    *,
    state: object,
) -> tuple[CandidateProposal, ...]:
    """Verify exact evidence only at prepared rotate-target positions.

    Returns:
        Untrusted matching proposals in evaluation order.

    Raises:
        InvalidAcceleratorWorkError: If selector state is forged/mismatched.

    """
    if not isinstance(state, PreparedRotateTargetSelection):
        message = "prepared rotate selection state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    target, positions = state.for_selection(request, batch)
    proposals: list[CandidateProposal] = []
    for index in positions:
        if primitive_evidence_value_at(evidence, index) != target:
            continue
        item = batch.items[index]
        proposals.append(
            CandidateProposal(
                logical_id=item.logical_id,
                payload=item.payload,
            )
        )
    return tuple(proposals)


def select_rotate_target_proposals(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    """Select evaluated candidates whose exact rotate evidence equals target.

    Returns:
        Untrusted matching proposals in evaluation order.

    """
    target = RotateTargetProblem.decode_target(request.problem)
    proposals: list[CandidateProposal] = []
    observed_values = iter_primitive_evidence_values(evidence)
    for item, observed in zip(batch.items, observed_values, strict=True):
        if observed == target:
            proposals.append(
                CandidateProposal(
                    logical_id=item.logical_id,
                    payload=item.payload,
                )
            )
    return tuple(proposals)


@final
class RotateTargetVerifier(TrustedCandidateVerifier):
    """Independent CPU authority for rotate-target candidate admission."""

    def __init__(self, target: int) -> None:
        """Bind one validated classic-domain target."""
        _ = RotateTargetProblem(target=target, candidates=()).validated()
        self._target = target

    @override
    def accepts(
        self,
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        """Recompute exact rotate on CPU and ignore untrusted hints.

        Returns:
            Whether the candidate independently rotates to the bound target.

        """
        _ = hint
        if len(candidate.payload) != _U32.size:
            return False
        value = int.from_bytes(candidate.payload, "little")
        if value > MAX_WORD:
            return False
        result = CpuExactPrimitiveAdapter().evaluate(
            PrimitiveBatch(
                accumulators=(),
                data=(value,),
                kind=PrimitiveKind.ROTATE,
            )
        )
        return result.values == (self._target,)


def _inverse_rotate(target: int) -> int:
    # For x = 3q + r, rotate(x) = q + r * 3^9.
    low_trit = target // ROTATE_HIGH_TRIT_WEIGHT
    quotient = target % ROTATE_HIGH_TRIT_WEIGHT
    return (quotient * 3) + low_trit


def _decode_header(payload: bytes) -> tuple[int, int, int]:
    if not payload.startswith(_MAGIC):
        message = "rotate target problem has invalid magic"
        raise InvalidRotateTargetProblemError(message)
    target, offset = _read_u32(payload, len(_MAGIC))
    count, offset = _read_u32(payload, offset)
    expected = offset + (count * _U32.size)
    if expected != len(payload):
        message = "rotate target problem has invalid candidate byte length"
        raise InvalidRotateTargetProblemError(message)
    return (target, count, offset)


def _read_u32(payload: bytes, offset: int) -> tuple[int, int]:
    end = offset + _U32.size
    if end > len(payload):
        message = "rotate target problem integer field is truncated"
        raise InvalidRotateTargetProblemError(message)
    return (_U32.unpack_from(payload, offset)[0], end)
