# File:
#   - rotate_target.py
# Path:
#   - optimizer/rotate_target.py
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
#   - Deterministic exact classic rotate-target corpus search.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Deterministic exact classic rotate-target corpus search."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from struct import Struct
import sys
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
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import TrustedCandidateVerifier
from accelerator.work_ports import indexed_candidate_items_from_rotated_u32le

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence

    from accelerator.exact_primitives import ExactPrimitiveAdapter
    from accelerator.work_ports import CandidateEvaluationResult
    from accelerator.work_ports import SearchRequest
    from accelerator.work_ports import VerificationHint

ROTATE_TARGET_ALGORITHM_ID = "classic-rotate-target-search-v1"
ROTATE_TARGET_BATCH_BUILDER_ID = (
    "classic-u32le-bitset-inplace-first-representatives-v2"
)
_MAGIC = b"MBRTS1\0"
_U32 = Struct("<I")
_MAX_U32 = (1 << 32) - 1
_PREPARED_ROTATE_SELECTION_PROOF = object()
_CORPUS_ID_PREFIX = "corpus-"
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"


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
    target, candidate_count, candidate_offset = _decode_header(
        validated.problem
    )
    _validate_target(target)
    representatives = _packed_representative_indices(
        validated.problem,
        candidate_count,
        candidate_offset,
    )
    logical_indices = _selected_packed_indices(
        representatives,
        evaluation_budget=validated.evaluation_budget,
        seed=validated.seed,
    )
    del representatives
    payloads = _packed_selected_payloads(
        validated.problem,
        candidate_offset,
        logical_indices,
    )
    return CandidateEvaluationBatch(
        evaluator_id=ROTATE_EVALUATOR_ID,
        items=indexed_candidate_items_from_rotated_u32le(
            logical_id_prefix=_CORPUS_ID_PREFIX,
            logical_indices_u32le=logical_indices,
            payload_width=_U32.size,
            payloads=payloads,
        ),
    )


def rotate_target_batch_builder_id() -> str:
    """Return the active packed rotate-target batch-builder identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return ROTATE_TARGET_BATCH_BUILDER_ID


def _packed_representative_indices(
    problem: bytes,
    candidate_count: int,
    candidate_offset: int,
) -> array[int]:
    values = _native_u32_values(problem, candidate_offset)
    if len(values) != candidate_count:
        message = "rotate target problem has invalid candidate byte length"
        raise InvalidRotateTargetProblemError(message)
    seen = bytearray((MAX_WORD + 8) // 8)
    representatives = array(_NATIVE_WORD_FORMAT)
    for index, value in enumerate(values):
        if value > MAX_WORD:
            message = f"rotate candidate outside classic domain: {value}"
            raise InvalidRotateTargetProblemError(message)
        byte_index, bit_index = divmod(value, 8)
        mask = 1 << bit_index
        if seen[byte_index] & mask:
            continue
        seen[byte_index] |= mask
        representatives.append(index)
    return representatives


def _selected_packed_indices(
    representatives: array[int],
    *,
    evaluation_budget: int,
    seed: int,
) -> bytes:
    representative_count = len(representatives)
    if not representative_count:
        return b""
    start = seed % representative_count
    _rotate_array_left(representatives, start)
    count = min(evaluation_budget, representative_count)
    del representatives[count:]
    return _u32le_bytes(representatives)


def _rotate_array_left(values: array[int], start: int) -> None:
    if not start:
        return
    prefix = array(_NATIVE_WORD_FORMAT, values[:start])
    view = memoryview(values)
    view[:-start] = view[start:]
    view[-start:] = memoryview(prefix)


def _packed_selected_payloads(
    problem: bytes,
    candidate_offset: int,
    logical_indices_u32le: bytes,
) -> bytes:
    candidates = _native_u32_values(problem, candidate_offset)
    logical_indices = _native_u32_values(logical_indices_u32le, 0)
    payloads = array(_NATIVE_WORD_FORMAT)
    payloads.extend(candidates[index] for index in logical_indices)
    return _u32le_bytes(payloads)


def _native_u32_values(payload: bytes, offset: int) -> Sequence[int]:
    view = memoryview(payload)[offset:]
    if sys.byteorder == _LITTLE_ENDIAN:
        return view.cast(_NATIVE_WORD_FORMAT)
    values = array(_NATIVE_WORD_FORMAT)
    values.frombytes(view)
    values.byteswap()
    return values


def _u32le_bytes(values: array[int]) -> bytes:
    if values.itemsize != _U32.size:
        return b"".join(
            value.to_bytes(_U32.size, _LITTLE_ENDIAN) for value in values
        )
    if sys.byteorder != _LITTLE_ENDIAN:
        values.byteswap()
    return values.tobytes()


def _validate_target(target: int) -> None:
    if target > MAX_WORD:
        message = f"rotate target outside classic domain: {target}"
        raise InvalidRotateTargetProblemError(message)


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
    items = validated_batch.items
    if isinstance(items, IndexedCandidateWorkItems):
        positions = _indexed_rotate_positions(items, payload)
    else:
        positions = tuple(
            index for index, item in enumerate(items) if item.payload == payload
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
    observed_values = iter_primitive_evidence_values(evidence)
    if isinstance(batch.items, IndexedCandidateWorkItems):
        return _select_indexed_rotate_target_proposals(
            batch.items,
            observed_values,
            target,
        )
    proposals: list[CandidateProposal] = []
    for item, observed in zip(batch.items, observed_values, strict=True):
        if observed == target:
            proposals.append(
                CandidateProposal(
                    logical_id=item.logical_id,
                    payload=item.payload,
                )
            )
    return tuple(proposals)


def _select_indexed_rotate_target_proposals(
    items: IndexedCandidateWorkItems,
    observed_values: Iterator[int],
    target: int,
) -> tuple[CandidateProposal, ...]:
    proposals: list[CandidateProposal] = []
    observed_count = 0
    for index, observed in enumerate(observed_values):
        observed_count += 1
        if observed == target:
            proposals.append(
                CandidateProposal(
                    logical_id=items.logical_id_at(index),
                    payload=items.payload_at(index),
                )
            )
    if observed_count != len(items):
        message = "rotate evidence count does not match indexed candidate batch"
        raise InvalidAcceleratorWorkError(message)
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
        value = int.from_bytes(candidate.payload, _LITTLE_ENDIAN)
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


def _indexed_rotate_positions(
    items: IndexedCandidateWorkItems,
    payload: bytes,
) -> tuple[int, ...]:
    if items.payload_width != _U32.size or len(payload) != _U32.size:
        message = "indexed rotate payload width changed"
        raise InvalidAcceleratorWorkError(message)
    target = int.from_bytes(payload, _LITTLE_ENDIAN)
    values = array("I")
    if values.itemsize == _U32.size:
        values.frombytes(items.payloads)
        if sys.byteorder != _LITTLE_ENDIAN:
            values.byteswap()
        positions = tuple(
            index for index, value in enumerate(values) if value == target
        )
    else:
        positions = tuple(
            index
            for index in range(len(items))
            if int.from_bytes(items.payload_at(index), _LITTLE_ENDIAN) == target
        )
    if len(positions) > 1:
        message = "rotate candidate batch retained duplicate payload"
        raise InvalidAcceleratorWorkError(message)
    return positions


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
