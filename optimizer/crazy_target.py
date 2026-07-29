# File:
#   - crazy_target.py
# Path:
#   - optimizer/crazy_target.py
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
#   - Deterministic exact classic crazy-target corpus search.
# - Must-Not:
#   - Use heuristic filtering or grant proposal acceptance authority.
# - Allows:
#   - Inputs: fixed-accumulator crazy targets and finite classic-word corpora.
#   - Outputs: exact multi-position projected candidate search results.
#   - Side effects: replaceable CPU/CUDA primitive evaluation only.
# - Split-When:
#   - Split when another non-invertible strategy gains independent state.
# - Merge-When:
#   - Merge when another module owns the same crazy-target strategy contract.
# - Summary:
#   - Exact non-invertible classic crazy-target search.
# - Description:
#   - Computes exact digitwise preimage positions before backend evaluation.
# - Usage:
#   - Build a search adapter or use the CPU reference constructor.
# - Defaults:
#   - Full membership and independent trusted admission remain authoritative.
#
# Related documents:
# - docs/technical/integrations/accelerators/replaceable-accelerator-boundary.md
#
# Large file:
#   - false
#

"""Deterministic exact non-invertible classic crazy-target search."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from struct import Struct
import sys
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
from accelerator.evaluated_search import EvaluatedSearchStrategy
from accelerator.evaluated_search import PreparedCandidateExecution
from accelerator.evaluated_search import PreparedProposalSelection
from accelerator.evaluated_search import prepare_candidate_projection
from accelerator.exact_primitives import CRAZY_TRIT_TABLE
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import TRIT_COUNT
from accelerator.primitive_candidates import CRAZY_EVALUATOR_ID
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import iter_primitive_evidence_values
from accelerator.primitive_candidates import prepare_crazy_candidate_batch
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
from accelerator.work_ports import prepare_candidate_subset

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence

    from accelerator.exact_primitives import ExactPrimitiveAdapter
    from accelerator.work_ports import CandidateEvaluationResult
    from accelerator.work_ports import SearchRequest
    from accelerator.work_ports import VerificationHint

CRAZY_TARGET_ALGORITHM_ID = "classic-crazy-target-search-v1"
CRAZY_TARGET_BATCH_BUILDER_ID = (
    "classic-crazy-u32le-bitset-first-representatives-v1"
)
CRAZY_TARGET_SELECTION_PREPARER_ID = "classic-crazy-digitwise-exact-preimage-v1"
CRAZY_TARGET_PROJECTED_EVALUATION_ID = (
    "classic-crazy-preimage-position-subset-v1"
)
_MAGIC = b"MBCTS1\0"
_U32 = Struct("<I")
_CRAZY = Struct("<II")
_MAX_U32 = (1 << 32) - 1
_PREPARED_CRAZY_SELECTION_PROOF = object()
_CORPUS_ID_PREFIX = "corpus-"
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"


@dataclass(frozen=True, slots=True)
class PreparedCrazyTargetSelection:
    """Proof-bound exact candidate positions for one crazy target."""

    accumulator: int
    batch: CandidateEvaluationBatch
    positions: tuple[int, ...]
    request: SearchRequest
    target: int
    _proof: object

    def for_selection(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
    ) -> tuple[int, int, tuple[int, ...]]:
        """Return state only for the request and batch that prepared it.

        Returns:
            Target, fixed accumulator, and exact request-order positions.

        Raises:
            InvalidAcceleratorWorkError: If state is forged or mismatched.

        """
        if self._proof is not _PREPARED_CRAZY_SELECTION_PROOF:
            message = "prepared crazy selection state is forged"
            raise InvalidAcceleratorWorkError(message)
        if self.request is not request or self.batch is not batch:
            message = "prepared crazy selection state changed request or batch"
            raise InvalidAcceleratorWorkError(message)
        return (self.target, self.accumulator, self.positions)

    def position_count(self) -> int:
        """Return proof-validated exact preimage-position count.

        Returns:
            Number of evaluated positions that can produce the target.

        Raises:
            InvalidAcceleratorWorkError: If this state was forged.

        """
        if self._proof is not _PREPARED_CRAZY_SELECTION_PROOF:
            message = "prepared crazy selection state is forged"
            raise InvalidAcceleratorWorkError(message)
        return len(self.positions)


class InvalidCrazyTargetProblemError(ValueError):
    """Crazy-target search problem encoding or word domain is malformed."""


@dataclass(frozen=True, slots=True)
class CrazyTargetProblem:
    """Canonical fixed accumulator, target, and candidate-data corpus."""

    accumulator: int
    target: int
    candidates: tuple[int, ...]

    def validated(self) -> CrazyTargetProblem:
        """Validate target, accumulator, count, and candidate words.

        Returns:
            This immutable problem after every invariant succeeds.

        Raises:
            InvalidCrazyTargetProblemError: If representation is malformed.

        """
        _validate_problem_word(self.target, "target")
        _validate_problem_word(self.accumulator, "accumulator")
        if len(self.candidates) > _MAX_U32:
            message = "crazy target candidate count exceeds u32 representation"
            raise InvalidCrazyTargetProblemError(message)
        for value in self.candidates:
            _validate_problem_word(value, "candidate")
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
            _U32.pack(validated.accumulator),
            _U32.pack(len(validated.candidates)),
        ]
        parts.extend(_U32.pack(value) for value in validated.candidates)
        return b"".join(parts)

    @classmethod
    def decode(cls, payload: bytes) -> CrazyTargetProblem:
        """Decode canonical crazy-target search bytes.

        Returns:
            Validated immutable crazy-target problem.

        """
        target, accumulator, count, offset = _decode_header(payload)
        candidates = tuple(
            _U32.unpack_from(payload, offset + (index * _U32.size))[0]
            for index in range(count)
        )
        return cls(
            accumulator=accumulator,
            target=target,
            candidates=candidates,
        ).validated()

    @classmethod
    def decode_parameters(cls, payload: bytes) -> tuple[int, int]:
        """Decode only validated target and fixed accumulator.

        Returns:
            Target and accumulator without materializing the candidate corpus.

        """
        target, accumulator, _, _ = _decode_header(payload)
        _ = cls(
            accumulator=accumulator,
            target=target,
            candidates=(),
        ).validated()
        return (target, accumulator)


def crazy_target_search_adapter(
    primitive: ExactPrimitiveAdapter,
) -> EvaluatedSearchExecutionAdapter:
    """Bind crazy-target search to one exact primitive backend.

    Returns:
        Search adapter whose capability is inherited from ``primitive``.

    """
    evaluator = PrimitiveCandidateEvaluationAdapter(
        primitive,
        PrimitiveKind.CRAZY,
    )
    return EvaluatedSearchExecutionAdapter(
        CRAZY_TARGET_ALGORITHM_ID,
        evaluator,
        EvaluatedSearchStrategy(
            batch_builder=build_crazy_target_batch,
            proposal_selector=select_crazy_target_proposals,
            prepared_execution=PreparedCandidateExecution(
                batch_preparer=None,
                evaluator=evaluator.evaluate_prepared,
                selection_aware_preparer=(
                    prepare_projected_crazy_candidate_batch
                ),
                state_count=prepared_primitive_reference_word_count,
            ),
            prepared_selection=PreparedProposalSelection(
                state_preparer=prepare_crazy_target_selection,
                selector=select_prepared_crazy_target_proposals,
                state_count=count_prepared_crazy_target_positions,
            ),
        ),
    )


def cpu_crazy_target_search_adapter() -> EvaluatedSearchExecutionAdapter:
    """Construct the mandatory scalar crazy-target search reference.

    Returns:
        CPU-backed exact crazy-target search adapter.

    """
    return crazy_target_search_adapter(CpuExactPrimitiveAdapter())


def build_crazy_target_batch(
    request: SearchRequest,
) -> CandidateEvaluationBatch:
    """Build the seeded distinct-data batch for one crazy-target request.

    Returns:
        Stable first representatives bounded by the evaluation budget.

    Raises:
        InvalidAcceleratorWorkError: If request selects another algorithm.

    """
    validated = request.validated()
    if validated.algorithm_id != CRAZY_TARGET_ALGORITHM_ID:
        message = "crazy target search request selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    target, accumulator, count, offset = _decode_header(validated.problem)
    _validate_problem_word(target, "target")
    _validate_problem_word(accumulator, "accumulator")
    representatives = _packed_representative_indices(
        validated.problem,
        count,
        offset,
    )
    logical_indices = _selected_packed_indices(
        representatives,
        evaluation_budget=validated.evaluation_budget,
        seed=validated.seed,
    )
    del representatives
    payloads = _packed_selected_payloads(
        validated.problem,
        offset,
        logical_indices,
        accumulator=accumulator,
    )
    return CandidateEvaluationBatch(
        evaluator_id=CRAZY_EVALUATOR_ID,
        items=indexed_candidate_items_from_rotated_u32le(
            logical_id_prefix=_CORPUS_ID_PREFIX,
            logical_indices_u32le=logical_indices,
            payload_width=_CRAZY.size,
            payloads=payloads,
        ),
    )


def crazy_target_batch_builder_id() -> str:
    """Return the exact packed crazy-target batch-builder identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return CRAZY_TARGET_BATCH_BUILDER_ID


def crazy_target_selection_preparer_id() -> str:
    """Return the exact digitwise preimage selector identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return CRAZY_TARGET_SELECTION_PREPARER_ID


def crazy_target_projected_evaluation_id() -> str:
    """Return the exact multiposition projection identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return CRAZY_TARGET_PROJECTED_EVALUATION_ID


def prepare_crazy_target_selection(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> object:
    """Prepare exact positions using only the normative ternary relation.

    Returns:
        Strategy-bound immutable multiposition selector state.

    Raises:
        InvalidAcceleratorWorkError: If algorithm/evaluator identity mismatches.

    """
    validated_request = request.validated()
    if validated_request.algorithm_id != CRAZY_TARGET_ALGORITHM_ID:
        message = "crazy target selection selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    validated_batch = batch.validated()
    if validated_batch.evaluator_id != CRAZY_EVALUATOR_ID:
        message = "crazy target selection uses a different evaluator"
        raise InvalidAcceleratorWorkError(message)
    target, accumulator = CrazyTargetProblem.decode_parameters(
        validated_request.problem
    )
    positions = _crazy_positions(validated_batch, target, accumulator)
    return PreparedCrazyTargetSelection(
        accumulator=accumulator,
        batch=validated_batch,
        positions=positions,
        request=validated_request,
        target=target,
        _proof=_PREPARED_CRAZY_SELECTION_PROOF,
    )


def prepare_projected_crazy_candidate_batch(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    selection_state: object,
) -> object:
    """Prepare only exact selector-relevant crazy candidates.

    Returns:
        Proof-bound primitive state for every exact preimage position.

    Raises:
        InvalidAcceleratorWorkError: If selector state is forged or mismatched.

    """
    if not isinstance(selection_state, PreparedCrazyTargetSelection):
        message = "prepared crazy projection has wrong selector state"
        raise InvalidAcceleratorWorkError(message)
    _, _, positions = selection_state.for_selection(request, batch)
    subset = prepare_candidate_subset(batch, positions)
    projected, _ = subset.for_batch(batch)
    primitive_state = prepare_crazy_candidate_batch(projected)
    return prepare_candidate_projection(batch, subset, primitive_state)


def count_prepared_crazy_target_positions(state: object) -> int:
    """Return proof-validated exact crazy preimage count.

    Returns:
        Number of exact request-order positions in the projected subset.

    Raises:
        InvalidAcceleratorWorkError: If selector state has wrong type/proof.

    """
    if not isinstance(state, PreparedCrazyTargetSelection):
        message = "prepared crazy selection state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    return state.position_count()


def select_prepared_crazy_target_proposals(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
    *,
    state: object,
) -> tuple[CandidateProposal, ...]:
    """Verify exact evidence only at prepared crazy-target positions.

    Returns:
        Untrusted matching proposals in full-batch request order.

    Raises:
        InvalidAcceleratorWorkError: If selector state is forged/mismatched.

    """
    if not isinstance(state, PreparedCrazyTargetSelection):
        message = "prepared crazy selection state has wrong type"
        raise InvalidAcceleratorWorkError(message)
    target, _, positions = state.for_selection(request, batch)
    proposals: list[CandidateProposal] = []
    for evidence_index, candidate_index in enumerate(positions):
        if primitive_evidence_value_at(evidence, evidence_index) != target:
            continue
        item = batch.items[candidate_index]
        proposals.append(
            CandidateProposal(
                logical_id=item.logical_id,
                payload=item.payload,
            )
        )
    return tuple(proposals)


def select_crazy_target_proposals(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: CandidateEvaluationResult,
) -> tuple[CandidateProposal, ...]:
    """Select candidates whose exact crazy evidence equals the target.

    Returns:
        Untrusted matching proposals in evaluation order.

    """
    target, _ = CrazyTargetProblem.decode_parameters(request.problem)
    observed_values = iter_primitive_evidence_values(evidence)
    if isinstance(batch.items, IndexedCandidateWorkItems):
        return _select_indexed_crazy_target_proposals(
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


@final
class CrazyTargetVerifier(TrustedCandidateVerifier):
    """Independent CPU authority for crazy-target candidate admission."""

    def __init__(self, target: int, accumulator: int) -> None:
        """Bind one validated target and fixed accumulator."""
        _ = CrazyTargetProblem(
            accumulator=accumulator,
            target=target,
            candidates=(),
        ).validated()
        self._accumulator = accumulator
        self._target = target

    @override
    def accepts(
        self,
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        """Recompute exact crazy on CPU and ignore untrusted hints.

        Returns:
            Whether candidate data with the bound accumulator reaches target.

        """
        _ = hint
        try:
            data, accumulator = _decode_candidate_payload(candidate.payload)
        except InvalidAcceleratorWorkError:
            return False
        if accumulator != self._accumulator:
            return False
        result = CpuExactPrimitiveAdapter().evaluate(
            PrimitiveBatch(
                accumulators=(accumulator,),
                data=(data,),
                kind=PrimitiveKind.CRAZY,
            )
        )
        return result.values == (self._target,)


def _crazy_positions(
    batch: CandidateEvaluationBatch,
    target: int,
    accumulator: int,
) -> tuple[int, ...]:
    items = batch.items
    if isinstance(items, IndexedCandidateWorkItems):
        return _indexed_crazy_positions(items, target, accumulator)
    positions: list[int] = []
    for index, item in enumerate(items):
        data, observed_accumulator = _decode_candidate_payload(item.payload)
        _require_accumulator(observed_accumulator, accumulator)
        if _crazy_matches_target(data, accumulator, target):
            positions.append(index)
    return tuple(positions)


def _indexed_crazy_positions(
    items: IndexedCandidateWorkItems,
    target: int,
    accumulator: int,
) -> tuple[int, ...]:
    if items.payload_width != _CRAZY.size:
        message = "indexed crazy payload width changed"
        raise InvalidAcceleratorWorkError(message)
    positions: list[int] = []
    for index in range(len(items)):
        data, observed_accumulator = cast(
            "tuple[int, int]",
            _CRAZY.unpack_from(items.payloads, index * _CRAZY.size),
        )
        _validate_candidate_word(data)
        _require_accumulator(observed_accumulator, accumulator)
        if _crazy_matches_target(data, accumulator, target):
            positions.append(index)
    return tuple(positions)


def _crazy_matches_target(data: int, accumulator: int, target: int) -> bool:
    for _ in range(TRIT_COUNT):
        data_trit, data = divmod(data, 3)[1], data // 3
        accumulator_trit, accumulator = (
            divmod(accumulator, 3)[1],
            accumulator // 3,
        )
        target_trit, target = divmod(target, 3)[1], target // 3
        if CRAZY_TRIT_TABLE[data_trit][accumulator_trit] != target_trit:
            return False
    return True


def _select_indexed_crazy_target_proposals(
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
        message = "crazy evidence count does not match indexed candidate batch"
        raise InvalidAcceleratorWorkError(message)
    return tuple(proposals)


def _packed_representative_indices(
    problem: bytes,
    candidate_count: int,
    candidate_offset: int,
) -> array[int]:
    values = _native_u32_values(problem, candidate_offset)
    if len(values) != candidate_count:
        message = "crazy target problem has invalid candidate byte length"
        raise InvalidCrazyTargetProblemError(message)
    seen = bytearray((MAX_WORD + 8) // 8)
    representatives = array(_NATIVE_WORD_FORMAT)
    for index, value in enumerate(values):
        _validate_problem_word(value, "candidate")
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
    *,
    accumulator: int,
) -> bytes:
    candidates = _native_u32_values(problem, candidate_offset)
    logical_indices = _native_u32_values(logical_indices_u32le, 0)
    payloads = bytearray(len(logical_indices) * _CRAZY.size)
    for index, logical_index in enumerate(logical_indices):
        _CRAZY.pack_into(
            payloads,
            index * _CRAZY.size,
            candidates[logical_index],
            accumulator,
        )
    return bytes(payloads)


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


def _decode_candidate_payload(payload: bytes) -> tuple[int, int]:
    if len(payload) != _CRAZY.size:
        message = "crazy candidate payload must contain exactly two u32 words"
        raise InvalidAcceleratorWorkError(message)
    data, accumulator = cast("tuple[int, int]", _CRAZY.unpack(payload))
    _validate_candidate_word(data)
    _validate_candidate_word(accumulator)
    return (data, accumulator)


def _require_accumulator(observed: int, expected: int) -> None:
    _validate_candidate_word(observed)
    if observed != expected:
        message = "crazy candidate changed fixed accumulator"
        raise InvalidAcceleratorWorkError(message)


def _validate_candidate_word(value: int) -> None:
    if value > MAX_WORD:
        message = f"crazy candidate word outside classic domain: {value}"
        raise InvalidAcceleratorWorkError(message)


def _validate_problem_word(value: int, label: str) -> None:
    if not 0 <= value <= MAX_WORD:
        message = f"crazy {label} outside classic domain: {value}"
        raise InvalidCrazyTargetProblemError(message)


def _decode_header(payload: bytes) -> tuple[int, int, int, int]:
    if not payload.startswith(_MAGIC):
        message = "crazy target problem has invalid magic"
        raise InvalidCrazyTargetProblemError(message)
    target, offset = _read_u32(payload, len(_MAGIC))
    accumulator, offset = _read_u32(payload, offset)
    count, offset = _read_u32(payload, offset)
    expected = offset + (count * _U32.size)
    if expected != len(payload):
        message = "crazy target problem has invalid candidate byte length"
        raise InvalidCrazyTargetProblemError(message)
    return (target, accumulator, count, offset)


def _read_u32(payload: bytes, offset: int) -> tuple[int, int]:
    end = offset + _U32.size
    if end > len(payload):
        message = "crazy target problem integer field is truncated"
        raise InvalidCrazyTargetProblemError(message)
    return (_U32.unpack_from(payload, offset)[0], end)
