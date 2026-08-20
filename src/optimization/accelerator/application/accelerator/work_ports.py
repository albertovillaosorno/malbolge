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
#   - Hardware-neutral candidate, search, and verification-assist ports.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Hardware-neutral candidate, search, and verification-assist ports."""

from __future__ import annotations

from array import array
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from struct import Struct
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast
from typing import overload
from typing import override

from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorError
from accelerator.exact_primitives import AcceleratorExecutionError

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator


INDEXED_CANDIDATE_ITEMS_ID = "u32-index-fixed-width-payloads-rotation-v1"
PREPARED_CANDIDATE_SUBSET_ID = "request-order-position-subset-v1"
MAX_U32 = (1 << 32) - 1
MAX_U64 = (1 << 64) - 1
_U32_BYTES = 4
_U32_DECIMAL_DIGITS = 10
_MIN_ROTATION_SCAN_ITEMS = 2
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"
_U32_LE = Struct("<I")
_INDEXED_CANDIDATE_ITEMS_PROOF = object()
_PREPARED_CANDIDATE_SUBSET_PROOF = object()


def indexed_candidate_items_from_unique_u32(
    *,
    logical_id_prefix: str,
    logical_indices: tuple[int, ...],
    payload_width: int,
    payloads: bytes,
) -> IndexedCandidateWorkItems:
    """Build proof-carrying fixed-width storage from unique u32 indexes.

    Returns:
        Fixed-width storage with validated uniqueness and rotation order.

    """
    _validate_identity(logical_id_prefix, "candidate logical ID prefix")
    _validate_unique_u32_values(logical_indices)
    item = IndexedCandidateWorkItems(
        logical_id_prefix=logical_id_prefix,
        logical_indices_u32le=_pack_u32_values(logical_indices),
        payload_width=payload_width,
        payloads=payloads,
        logical_rotation_pivot=_rotation_pivot(logical_indices),
        _proof=_INDEXED_CANDIDATE_ITEMS_PROOF,
    )
    _validate_indexed_storage(item)
    return item


def indexed_candidate_items_from_rotated_u32le(
    *,
    logical_id_prefix: str,
    logical_indices_u32le: bytes,
    payload_width: int,
    payloads: bytes,
) -> IndexedCandidateWorkItems:
    """Build proof-carrying storage from one strict sorted-index rotation.

    Returns:
        Fixed-width candidate storage validated without tuple materialization.

    """
    _validate_identity(logical_id_prefix, "candidate logical ID prefix")
    pivot = _packed_rotation_pivot(logical_indices_u32le)
    item = IndexedCandidateWorkItems(
        logical_id_prefix=logical_id_prefix,
        logical_indices_u32le=logical_indices_u32le,
        payload_width=payload_width,
        payloads=payloads,
        logical_rotation_pivot=pivot,
        _proof=_INDEXED_CANDIDATE_ITEMS_PROOF,
    )
    _validate_indexed_storage(item)
    return item


def indexed_candidate_items_id() -> str:
    """Return the active fixed-width indexed candidate storage identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return INDEXED_CANDIDATE_ITEMS_ID


class InvalidAcceleratorWorkError(ValueError):
    """A hardware-neutral work request violates its declared contract."""


class InvalidAcceleratorResultError(AcceleratorExecutionError, ValueError):
    """An adapter returned a malformed hardware-neutral result."""


@dataclass(frozen=True, slots=True)
class CandidateWorkItem:
    """One immutable candidate payload with stable logical identity."""

    logical_id: str
    payload: bytes

    def validated(self) -> CandidateWorkItem:
        """Validate candidate identity and return this immutable item.

        Returns:
            This item after identity validation succeeds.

        """
        _validate_identity(self.logical_id, "candidate logical ID")
        _validate_work_payload(self.payload, "candidate payload")
        return self


@dataclass(frozen=True, slots=True)
class IndexedCandidateWorkItems(Sequence[CandidateWorkItem]):
    """Fixed-width candidates with u32-derived logical identities."""

    logical_id_prefix: str
    logical_indices_u32le: bytes
    payload_width: int
    payloads: bytes
    logical_rotation_pivot: int | None = None
    _proof: object | None = field(default=None, repr=False, compare=False)

    def validated(self) -> IndexedCandidateWorkItems:
        """Validate packed shape, identity derivation, and index uniqueness.

        Returns:
            This immutable indexed collection after every invariant succeeds.

        """
        if self._proof is _INDEXED_CANDIDATE_ITEMS_PROOF:
            return self
        _validate_identity(
            self.logical_id_prefix, "candidate logical ID prefix"
        )
        _validate_indexed_storage(self)
        logical_indices = _unpack_u32_values(self.logical_indices_u32le)
        _validate_unique_u32_values(logical_indices)
        _validate_rotation_pivot(self.logical_rotation_pivot, logical_indices)
        return self

    @override
    def __len__(self) -> int:
        """Return the exact candidate count.

        Returns:
            Number of fixed-width indexed candidates.

        """
        return len(self.logical_indices_u32le) // _U32_BYTES

    @override
    def __iter__(self) -> Iterator[CandidateWorkItem]:
        """Yield materialized candidates in request order.

        Yields:
            Candidate objects derived from packed identity and payload storage.

        """
        for index in range(len(self)):
            yield self.item_at(index)

    @overload
    def __getitem__(self, index: int) -> CandidateWorkItem: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[CandidateWorkItem, ...]: ...

    @override
    def __getitem__(
        self,
        index: int | slice,
    ) -> CandidateWorkItem | tuple[CandidateWorkItem, ...]:
        """Materialize one candidate or an immutable request-order slice.

        Returns:
            One candidate for an integer or a tuple for a slice.

        """
        if isinstance(index, slice):
            return tuple(
                self.item_at(position)
                for position in range(*index.indices(len(self)))
            )
        return self.item_at(index)

    def item_at(self, index: int) -> CandidateWorkItem:
        """Materialize one candidate object at an exact request-order index.

        Returns:
            Candidate identity and payload for the requested position.

        """
        return CandidateWorkItem(
            logical_id=self.logical_id_at(index),
            payload=self.payload_at(index),
        )

    def logical_index_at(self, index: int) -> int:
        """Return the packed logical u32 index at one request-order position.

        Returns:
            Canonical logical index used to derive the candidate identity.

        """
        position = _normalized_item_index(index, len(self))
        offset = position * _U32_BYTES
        return cast(
            "int",
            _U32_LE.unpack_from(self.logical_indices_u32le, offset)[0],
        )

    def logical_id_at(self, index: int) -> str:
        """Return one identity without retaining a string table.

        Returns:
            Prefix plus canonical decimal u32 index.

        """
        return f"{self.logical_id_prefix}{self.logical_index_at(index)}"

    def payload_at(self, index: int) -> bytes:
        """Materialize one fixed-width candidate payload.

        Returns:
            Exact payload bytes at the requested position.

        """
        position = _normalized_item_index(index, len(self))
        start = position * self.payload_width
        return self.payloads[start : start + self.payload_width]

    def payload_matches(self, index: int, payload: bytes) -> bool:
        """Return whether one position contains exact candidate payload bytes.

        Returns:
            True only when width and bytes match exactly.

        """
        if len(payload) != self.payload_width:
            return False
        position = _normalized_item_index(index, len(self))
        start = position * self.payload_width
        end = start + self.payload_width
        return self.payloads.startswith(payload, start, end)

    def parse_logical_id(self, logical_id: str) -> int | None:
        """Parse one exact identity produced by this indexed collection.

        Returns:
            Canonical u32 suffix, or ``None`` for another identity grammar.

        """
        result: int | None = None
        if logical_id.startswith(self.logical_id_prefix):
            suffix = logical_id[len(self.logical_id_prefix) :]
            if _is_canonical_u32_suffix(suffix):
                value = int(suffix)
                if value <= MAX_U32 and str(value) == suffix:
                    result = value
        return result


type CandidateWorkItems = (
    tuple[CandidateWorkItem, ...] | IndexedCandidateWorkItems
)


@dataclass(frozen=True, slots=True)
class CandidateEvaluationBatch:
    """Candidate evidence request independent from accelerator hardware."""

    evaluator_id: str
    items: CandidateWorkItems

    def validated(self) -> CandidateEvaluationBatch:
        """Validate evaluator and candidate identities.

        Returns:
            This immutable batch after validation succeeds.

        """
        _validate_identity(self.evaluator_id, "candidate evaluator ID")
        _validate_candidate_items(self.items)
        return self


@dataclass(frozen=True, slots=True)
class PreparedCandidateSubset:
    """Proof-bound request-order subset of one validated candidate batch."""

    full_batch: CandidateEvaluationBatch
    batch: CandidateEvaluationBatch
    positions: tuple[int, ...]
    _proof: object = field(repr=False, compare=False)

    def for_batch(
        self,
        full_batch: CandidateEvaluationBatch,
    ) -> tuple[CandidateEvaluationBatch, tuple[int, ...]]:
        """Return the projected batch only for its exact full batch.

        Returns:
            Exact request-order sub-batch and its strictly increasing positions.

        Raises:
            InvalidAcceleratorWorkError: If proof or full-batch identity
                changed.

        """
        if self._proof is not _PREPARED_CANDIDATE_SUBSET_PROOF:
            message = "prepared candidate subset is forged"
            raise InvalidAcceleratorWorkError(message)
        if self.full_batch is not full_batch:
            message = "prepared candidate subset changed full candidate batch"
            raise InvalidAcceleratorWorkError(message)
        return (self.batch, self.positions)


def prepare_candidate_subset(
    full_batch: CandidateEvaluationBatch,
    positions: tuple[int, ...],
) -> PreparedCandidateSubset:
    """Build one exact request-order subset from validated candidate positions.

    Returns:
        Proof-bound projected batch tied to the exact full-batch object.

    """
    validated = full_batch.validated()
    _validate_candidate_subset_positions(positions, len(validated.items))
    projected = CandidateEvaluationBatch(
        evaluator_id=validated.evaluator_id,
        items=tuple(validated.items[position] for position in positions),
    ).validated()
    return PreparedCandidateSubset(
        full_batch=validated,
        batch=projected,
        positions=positions,
        _proof=_PREPARED_CANDIDATE_SUBSET_PROOF,
    )


def prepared_candidate_subset_id() -> str:
    """Return the active exact request-order subset identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PREPARED_CANDIDATE_SUBSET_ID


def _validate_candidate_subset_positions(
    positions: tuple[int, ...],
    full_count: int,
) -> None:
    if type(positions) is not tuple:
        message = "candidate subset positions must use an immutable tuple"
        raise InvalidAcceleratorWorkError(message)
    previous = -1
    for position in positions:
        if type(position) is not int or position < 0 or position >= full_count:
            message = "candidate subset position outside candidate batch"
            raise InvalidAcceleratorWorkError(message)
        if position <= previous:
            message = "candidate subset positions must be strictly increasing"
            raise InvalidAcceleratorWorkError(message)
        previous = position


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    """Untrusted accelerator evidence for one candidate."""

    logical_id: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class PackedCandidateEvidence:
    """Fixed-width opaque evidence payloads in request order."""

    payload_width: int
    payloads: bytes

    def validated_for_count(self, count: int) -> PackedCandidateEvidence:
        """Validate fixed-width storage for one candidate count.

        Returns:
            This packed representation after exact-size validation.

        Raises:
            InvalidAcceleratorResultError: If width, storage type, or size is
                malformed.

        """
        if type(self.payload_width) is not int or self.payload_width <= 0:
            message = "packed candidate evidence width must be positive"
            raise InvalidAcceleratorResultError(message)
        if type(self.payloads) is not bytes:
            message = "packed candidate evidence storage must be bytes"
            raise InvalidAcceleratorResultError(message)
        expected = count * self.payload_width
        if len(self.payloads) != expected:
            message = "packed candidate evidence size does not match request"
            raise InvalidAcceleratorResultError(message)
        return self

    def payload_at(self, index: int) -> bytes:
        """Materialize one fixed-width evidence payload.

        Returns:
            The requested opaque payload bytes.

        """
        start = index * self.payload_width
        end = start + self.payload_width
        return self.payloads[start:end]


@dataclass(frozen=True, slots=True)
class CandidateEvaluationResult:
    """Ordered untrusted candidate evidence from one backend."""

    capability: AcceleratorCapability
    evaluator_id: str
    items: tuple[CandidateEvidence, ...] = ()
    packed: PackedCandidateEvidence | None = None

    def validated_against(
        self,
        batch: CandidateEvaluationBatch,
        capability: AcceleratorCapability,
    ) -> CandidateEvaluationResult:
        """Validate result identity and shape against one request.

        Returns:
            This result when backend, evaluator, and item order match.

        Raises:
            InvalidAcceleratorResultError: If returned metadata is malformed.

        """
        _validate_result_capability(self.capability, capability)
        _validate_result_identity(self.evaluator_id, "candidate evaluator ID")
        if self.evaluator_id != batch.evaluator_id:
            message = "candidate evaluator ID changed during backend execution"
            raise InvalidAcceleratorResultError(message)
        _validate_result_tuple(self.items, "candidate evidence items")
        if self.packed is not None:
            _validate_packed_candidate_result(
                self.items,
                self.packed,
                len(batch.items),
            )
            return self
        _validate_candidate_evidence(self.items)
        expected = tuple(item.logical_id for item in batch.items)
        observed = tuple(item.logical_id for item in self.items)
        if observed != expected:
            message = "candidate evidence identities do not match request order"
            raise InvalidAcceleratorResultError(message)
        return self

    def materialized_items_against(
        self,
        batch: CandidateEvaluationBatch,
        capability: AcceleratorCapability,
    ) -> tuple[CandidateEvidence, ...]:
        """Materialize ordered evidence only for consumers that require objects.

        Returns:
            Candidate evidence with logical IDs restored from request order.

        """
        validated = self.validated_against(batch, capability)
        if validated.packed is None:
            return validated.items
        return tuple(
            CandidateEvidence(
                logical_id=item.logical_id,
                payload=validated.packed.payload_at(index),
            )
            for index, item in enumerate(batch.items)
        )


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Deterministic search submission independent from hardware selection."""

    algorithm_id: str
    evaluation_budget: int
    problem: bytes
    seed: int

    def validated(self) -> SearchRequest:
        """Validate algorithm identity, seed, and evaluation budget.

        Returns:
            This immutable request after validation succeeds.

        Raises:
            InvalidAcceleratorWorkError: If a scalar invariant is invalid.

        """
        _validate_identity(self.algorithm_id, "search algorithm ID")
        _validate_work_payload(self.problem, "search problem")
        _validate_u64(self.seed, "search seed")
        if (
            type(self.evaluation_budget) is not int
            or not 1 <= self.evaluation_budget <= MAX_U64
        ):
            message = "search evaluation budget must be a positive u64"
            raise InvalidAcceleratorWorkError(message)
        return self


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    """Untrusted search proposal requiring independent verification."""

    logical_id: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Untrusted candidate proposals produced by one search backend."""

    algorithm_id: str
    capability: AcceleratorCapability
    proposals: tuple[CandidateProposal, ...]
    seed: int

    def validated_against(
        self,
        request: SearchRequest,
        capability: AcceleratorCapability,
    ) -> SearchResult:
        """Validate search result metadata without accepting any candidate.

        Returns:
            This result after structural validation succeeds.

        Raises:
            InvalidAcceleratorResultError: If structural metadata is invalid.

        """
        _validate_result_capability(self.capability, capability)
        _validate_result_identity(self.algorithm_id, "search algorithm ID")
        _validate_result_u64(self.seed, "search seed")
        _validate_result_tuple(self.proposals, "search proposals")
        if (
            self.algorithm_id != request.algorithm_id
            or self.seed != request.seed
        ):
            message = "search result changed algorithm identity or seed"
            raise InvalidAcceleratorResultError(message)
        if len(self.proposals) > request.evaluation_budget:
            message = "search result exceeds declared evaluation budget"
            raise InvalidAcceleratorResultError(message)
        _validate_proposals(self.proposals)
        return self


@dataclass(frozen=True, slots=True)
class VerificationAssistBatch:
    """Optional verification-hint request with no acceptance authority."""

    items: tuple[CandidateWorkItem, ...]
    verifier_id: str

    def validated(self) -> VerificationAssistBatch:
        """Validate verifier and candidate identities.

        Returns:
            This immutable batch after validation succeeds.

        """
        _validate_identity(self.verifier_id, "verification assist ID")
        _validate_candidate_items(self.items)
        return self


@dataclass(frozen=True, slots=True)
class VerificationHint:
    """Untrusted optional evidence consumed only by a trusted verifier."""

    logical_id: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class VerificationAssistResult:
    """Ordered optional verification hints from one accelerator backend."""

    capability: AcceleratorCapability
    hints: tuple[VerificationHint, ...]
    verifier_id: str

    def validated_against(
        self,
        batch: VerificationAssistBatch,
        capability: AcceleratorCapability,
    ) -> VerificationAssistResult:
        """Validate hint identity and shape without deciding acceptance.

        Returns:
            This result when backend and request identity match exactly.

        Raises:
            InvalidAcceleratorResultError: If returned metadata is malformed.

        """
        _validate_result_capability(self.capability, capability)
        _validate_result_identity(self.verifier_id, "verification assist ID")
        _validate_hints(self.hints)
        if self.verifier_id != batch.verifier_id:
            message = "verification assist ID changed during backend execution"
            raise InvalidAcceleratorResultError(message)
        expected = tuple(item.logical_id for item in batch.items)
        observed = tuple(hint.logical_id for hint in self.hints)
        if observed != expected:
            message = "verification hint identities do not match request order"
            raise InvalidAcceleratorResultError(message)
        return self


class CandidateEvaluationAdapter(Protocol):
    """Replaceable backend for untrusted candidate evidence production."""

    def capability(self) -> AcceleratorCapability:
        """Return stable backend identity."""
        ...

    def evaluate(
        self, batch: CandidateEvaluationBatch
    ) -> CandidateEvaluationResult:
        """Return untrusted evidence for every candidate in request order."""
        ...


class SearchExecutionAdapter(Protocol):
    """Replaceable execution capacity for one explicit search algorithm."""

    def capability(self) -> AcceleratorCapability:
        """Return stable backend identity."""
        ...

    def search(self, request: SearchRequest) -> SearchResult:
        """Return untrusted proposals for independent verification."""
        ...


class VerificationAssistAdapter(Protocol):
    """Optional hint backend without candidate acceptance authority."""

    def capability(self) -> AcceleratorCapability:
        """Return stable backend identity."""
        ...

    def assist(
        self, batch: VerificationAssistBatch
    ) -> VerificationAssistResult:
        """Return optional untrusted hints for a trusted verifier."""
        ...


class TrustedCandidateVerifier(Protocol):
    """Trusted authority that alone decides whether a proposal is accepted."""

    def accepts(
        self,
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        """Return whether one candidate satisfies trusted acceptance rules."""
        ...


def evaluate_candidates(
    batch: CandidateEvaluationBatch,
    reference: CandidateEvaluationAdapter,
    preferred: CandidateEvaluationAdapter | None = None,
) -> CandidateEvaluationResult:
    """Evaluate candidates with optional best-effort backend fallback.

    Returns:
        Structurally valid untrusted evidence from the selected backend.

    """
    validated = batch.validated()
    admitted_reference = validated_candidate_evaluation_adapter(reference)
    if preferred is not None:
        result = _try_candidate_backend(validated, preferred)
        if result is not None:
            return result
    return _candidate_backend(validated, admitted_reference)


def execute_search(
    request: SearchRequest,
    reference: SearchExecutionAdapter,
    preferred: SearchExecutionAdapter | None = None,
) -> SearchResult:
    """Execute search with fallback and no candidate acceptance authority.

    Returns:
        Structurally valid untrusted proposals from preferred or reference.

    """
    validated = request.validated()
    admitted_reference = validated_search_execution_adapter(reference)
    if preferred is not None:
        result = _try_search_backend(validated, preferred)
        if result is not None:
            return result
    return _search_backend(validated, admitted_reference)


def request_verification_hints(
    batch: VerificationAssistBatch,
    preferred: VerificationAssistAdapter | None = None,
) -> tuple[VerificationHint, ...]:
    """Request optional hints while preserving verifier-only acceptance.

    Returns:
        Valid hints, or empty when assistance is unavailable or invalid.

    """
    validated = batch.validated()
    if preferred is None:
        return ()
    try:
        admitted = validated_verification_assist_adapter(preferred)
        capability = validated_accelerator_capability(
            admitted.capability(),
            "verification accelerator capability",
        )
        result = validated_verification_assist_result(
            admitted.assist(validated),
        )
        return result.validated_against(validated, capability).hints
    except AcceleratorError:
        return ()


def admit_search_result(
    result: SearchResult,
    verifier: TrustedCandidateVerifier,
    hints: tuple[VerificationHint, ...] = (),
) -> tuple[CandidateProposal, ...]:
    """Admit only proposals accepted by the independent trusted verifier.

    Returns:
        Candidate proposals independently accepted by ``verifier``.

    Raises:
        InvalidAcceleratorResultError: If verifier shape or verdict is invalid.

    """
    validated_result = validated_search_result(result)
    _validate_proposals(validated_result.proposals)
    hint_map = _validated_hint_map(validated_result.proposals, hints)
    accepts = _validated_verifier(verifier)
    admitted: list[CandidateProposal] = []
    for candidate in validated_result.proposals:
        verdict = accepts(candidate, hint_map.get(candidate.logical_id))
        if type(verdict) is not bool:
            message = "trusted candidate verifier returned non-boolean verdict"
            raise InvalidAcceleratorResultError(message)
        if verdict:
            admitted.append(candidate)
    return tuple(admitted)


def _validated_verifier(
    verifier: TrustedCandidateVerifier,
) -> Callable[[CandidateProposal, VerificationHint | None], object]:
    runtime_verifier = cast("object", verifier)
    accepts = getattr(runtime_verifier, "accepts", None)
    if not callable(accepts):
        message = "trusted candidate verifier has wrong type"
        raise InvalidAcceleratorResultError(message)
    return cast(
        "Callable[[CandidateProposal, VerificationHint | None], object]",
        accepts,
    )


def _candidate_backend(
    batch: CandidateEvaluationBatch,
    adapter: CandidateEvaluationAdapter,
) -> CandidateEvaluationResult:
    admitted = validated_candidate_evaluation_adapter(adapter)
    capability = validated_accelerator_capability(
        admitted.capability(),
        "candidate accelerator capability",
    )
    result = validated_candidate_evaluation_result(admitted.evaluate(batch))
    return result.validated_against(batch, capability)


def _search_backend(
    request: SearchRequest,
    adapter: SearchExecutionAdapter,
) -> SearchResult:
    admitted = validated_search_execution_adapter(adapter)
    capability = validated_accelerator_capability(
        admitted.capability(),
        "search accelerator capability",
    )
    result = validated_search_result(admitted.search(request))
    return result.validated_against(request, capability)


def _try_candidate_backend(
    batch: CandidateEvaluationBatch,
    adapter: CandidateEvaluationAdapter,
) -> CandidateEvaluationResult | None:
    try:
        return _candidate_backend(batch, adapter)
    except AcceleratorError:
        return None


def _try_search_backend(
    request: SearchRequest,
    adapter: SearchExecutionAdapter,
) -> SearchResult | None:
    try:
        return _search_backend(request, adapter)
    except AcceleratorError:
        return None


def _validate_candidate_items(items: CandidateWorkItems) -> None:
    if type(items) is IndexedCandidateWorkItems:
        _ = items.validated()
        return
    if type(items) is not tuple:
        message = "candidate items must use an immutable tuple"
        raise InvalidAcceleratorWorkError(message)
    identities: list[str] = []
    for item in items:
        if type(item) is not CandidateWorkItem:
            message = "candidate item has wrong type"
            raise InvalidAcceleratorWorkError(message)
        identities.append(item.validated().logical_id)
    _validate_unique(identities, "candidate logical ID")


def _validate_indexed_storage(items: IndexedCandidateWorkItems) -> None:
    _validate_index_storage(items.logical_indices_u32le)
    _validate_candidate_payload_storage(items)


def _validate_index_storage(indexes_u32le: bytes) -> None:
    if type(indexes_u32le) is not bytes:
        message = "indexed candidate logical indexes must use immutable bytes"
        raise InvalidAcceleratorWorkError(message)
    if len(indexes_u32le) % _U32_BYTES != 0:
        message = "indexed candidate logical indexes must contain complete u32s"
        raise InvalidAcceleratorWorkError(message)


def _validate_candidate_payload_storage(
    items: IndexedCandidateWorkItems,
) -> None:
    if type(items.payload_width) is not int or items.payload_width <= 0:
        message = "indexed candidate payload width must be positive"
        raise InvalidAcceleratorWorkError(message)
    if type(items.payloads) is not bytes:
        message = "indexed candidate payload storage must use immutable bytes"
        raise InvalidAcceleratorWorkError(message)
    if len(items.payloads) != len(items) * items.payload_width:
        message = (
            "indexed candidate payload size does not match logical indexes"
        )
        raise InvalidAcceleratorWorkError(message)


def _is_canonical_u32_suffix(suffix: str) -> bool:
    if not suffix or len(suffix) > _U32_DECIMAL_DIGITS:
        return False
    return suffix.isascii() and suffix.isdigit()


def _pack_u32_values(values: tuple[int, ...]) -> bytes:
    packed = bytearray(len(values) * _U32_BYTES)
    for index, value in enumerate(values):
        packed[index * _U32_BYTES : (index + 1) * _U32_BYTES] = value.to_bytes(
            _U32_BYTES,
            "little",
        )
    return bytes(packed)


def _unpack_u32_values(values_u32le: bytes) -> tuple[int, ...]:
    return tuple(
        int.from_bytes(
            values_u32le[offset : offset + _U32_BYTES],
            "little",
        )
        for offset in range(0, len(values_u32le), _U32_BYTES)
    )


def _validate_unique_u32_values(values: tuple[int, ...]) -> None:
    if any(
        type(value) is not int or value < 0 or value > MAX_U32
        for value in values
    ):
        message = "indexed candidate logical index outside u32 domain"
        raise InvalidAcceleratorWorkError(message)
    if len(values) != len(set(values)):
        message = "duplicate candidate logical ID"
        raise InvalidAcceleratorWorkError(message)


def _packed_rotation_pivot(values_u32le: bytes) -> int:
    _validate_index_storage(values_u32le)
    values = _native_u32_values(values_u32le)
    if len(values) < _MIN_ROTATION_SCAN_ITEMS:
        return 0
    first = values[0]
    pivot, descents, last = _scan_packed_rotation(values, first)
    if descents and last >= first:
        _raise_invalid_packed_rotation()
    return pivot


def _native_u32_values(values_u32le: bytes) -> Sequence[int]:
    if sys.byteorder == _LITTLE_ENDIAN:
        return memoryview(values_u32le).cast(_NATIVE_WORD_FORMAT)
    values = array(_NATIVE_WORD_FORMAT)
    values.frombytes(values_u32le)
    values.byteswap()
    return values


def _scan_packed_rotation(
    values: Sequence[int],
    first: int,
) -> tuple[int, int, int]:
    previous = first
    state = (0, 0)
    for index in range(1, len(values)):
        current = values[index]
        state = _updated_rotation_state(
            previous,
            current,
            index,
            state=state,
        )
        previous = current
    pivot, descents = state
    return (pivot, descents, previous)


def _updated_rotation_state(
    previous: int,
    current: int,
    index: int,
    *,
    state: tuple[int, int],
) -> tuple[int, int]:
    _, descents = state
    if current == previous:
        message = "duplicate candidate logical ID"
        raise InvalidAcceleratorWorkError(message)
    if current >= previous:
        return state
    if descents:
        _raise_invalid_packed_rotation()
    return (index, 1)


def _raise_invalid_packed_rotation() -> None:
    message = "candidate logical indexes must form one strict rotation"
    raise InvalidAcceleratorWorkError(message)


def _rotation_pivot(values: tuple[int, ...]) -> int | None:
    pivot = 0
    descents = 0
    for index in range(1, len(values)):
        if values[index] < values[index - 1]:
            pivot = index
            descents += 1
    return pivot if descents <= 1 else None


def _validate_rotation_pivot(
    observed: int | None,
    values: tuple[int, ...],
) -> None:
    if observed is None:
        return
    if observed != _rotation_pivot(values):
        message = (
            "indexed candidate rotation pivot does not match logical order"
        )
        raise InvalidAcceleratorWorkError(message)


def _normalized_item_index(index: int, count: int) -> int:
    if type(index) is not int:
        message = "candidate item index must be integer"
        raise TypeError(message)
    normalized = index + count if index < 0 else index
    if normalized < 0 or normalized >= count:
        message = "candidate item index outside request order"
        raise IndexError(message)
    return normalized


def _validate_identity(value: str, label: str) -> None:
    if type(value) is not str:
        message = f"{label} must use the exact string type"
        raise InvalidAcceleratorWorkError(message)
    if not value:
        message = f"{label} must not be empty"
        raise InvalidAcceleratorWorkError(message)


def _validate_work_payload(value: bytes, label: str) -> None:
    if type(value) is not bytes:
        message = f"{label} must use immutable bytes"
        raise InvalidAcceleratorWorkError(message)


def _validate_result_tuple(value: object, label: str) -> None:
    if type(value) is not tuple:
        message = f"{label} must use an immutable tuple"
        raise InvalidAcceleratorResultError(message)


def _validate_result_identity(value: str, label: str) -> None:
    if type(value) is not str:
        message = f"{label} must use the exact string type"
        raise InvalidAcceleratorResultError(message)
    if not value:
        message = f"{label} must not be empty"
        raise InvalidAcceleratorResultError(message)


def _validate_result_payload(value: bytes, label: str) -> None:
    if type(value) is not bytes:
        message = f"{label} must use immutable bytes"
        raise InvalidAcceleratorResultError(message)


def _validate_packed_candidate_result(
    items: tuple[CandidateEvidence, ...],
    packed: PackedCandidateEvidence,
    count: int,
) -> None:
    if type(packed) is not PackedCandidateEvidence:
        message = "packed candidate evidence has wrong type"
        raise InvalidAcceleratorResultError(message)
    if items:
        message = "candidate evidence cannot mix packed and item forms"
        raise InvalidAcceleratorResultError(message)
    _ = packed.validated_for_count(count)


def _validate_candidate_evidence(
    items: tuple[CandidateEvidence, ...],
) -> None:
    for item in items:
        if type(item) is not CandidateEvidence:
            message = "candidate evidence item has wrong type"
            raise InvalidAcceleratorResultError(message)
        _validate_result_identity(item.logical_id, "candidate logical ID")
        _validate_result_payload(item.payload, "candidate evidence payload")


def _validate_proposals(proposals: tuple[CandidateProposal, ...]) -> None:
    _validate_result_tuple(proposals, "search proposals")
    identities: list[str] = []
    for proposal in proposals:
        if type(proposal) is not CandidateProposal:
            message = "search proposal has wrong type"
            raise InvalidAcceleratorResultError(message)
        _validate_result_identity(
            proposal.logical_id,
            "search candidate logical ID",
        )
        _validate_result_payload(proposal.payload, "search proposal payload")
        identities.append(proposal.logical_id)
    _validate_unique_result(identities, "search candidate logical ID")


def _validate_hints(hints: tuple[VerificationHint, ...]) -> None:
    _validate_result_tuple(hints, "verification hints")
    for hint in hints:
        if type(hint) is not VerificationHint:
            message = "verification hint has wrong type"
            raise InvalidAcceleratorResultError(message)
        _validate_result_identity(
            hint.logical_id,
            "verification hint logical ID",
        )
        _validate_result_payload(hint.payload, "verification hint payload")


def _validate_result_capability(
    observed: AcceleratorCapability,
    expected: AcceleratorCapability,
) -> None:
    _ = validated_accelerator_capability(
        observed,
        "accelerator result capability",
    )
    _ = validated_accelerator_capability(expected, "adapter capability")
    if observed != expected:
        message = "accelerator result capability does not match adapter"
        raise InvalidAcceleratorResultError(message)


def validated_candidate_evaluation_adapter(
    value: object,
) -> CandidateEvaluationAdapter:
    """Return one structural candidate-evaluation adapter.

    Returns:
        Adapter exposing callable capability and evaluation operations.

    """
    _validate_adapter_surface(
        value,
        ("capability", "evaluate"),
        "candidate evaluation adapter",
    )
    return cast("CandidateEvaluationAdapter", value)


def validated_search_execution_adapter(
    value: object,
) -> SearchExecutionAdapter:
    """Return one structural search-execution adapter.

    Returns:
        Adapter exposing callable capability and search operations.

    """
    _validate_adapter_surface(
        value,
        ("capability", "search"),
        "search execution adapter",
    )
    return cast("SearchExecutionAdapter", value)


def validated_verification_assist_adapter(
    value: object,
) -> VerificationAssistAdapter:
    """Return one structural verification-assist adapter.

    Returns:
        Adapter exposing callable capability and assistance operations.

    """
    _validate_adapter_surface(
        value,
        ("capability", "assist"),
        "verification assist adapter",
    )
    return cast("VerificationAssistAdapter", value)


def _validate_adapter_surface(
    value: object,
    methods: tuple[str, ...],
    label: str,
) -> None:
    if not all(callable(getattr(value, name, None)) for name in methods):
        message = f"{label} has wrong type"
        raise InvalidAcceleratorResultError(message)


def validated_candidate_evaluation_result(
    value: object,
) -> CandidateEvaluationResult:
    """Return one exact candidate result before structural validation.

    Returns:
        The exact candidate result record.

    Raises:
        InvalidAcceleratorResultError: If the backend returned another type.

    """
    if type(value) is not CandidateEvaluationResult:
        message = "candidate backend result has wrong type"
        raise InvalidAcceleratorResultError(message)
    return value


def validated_search_result(value: object) -> SearchResult:
    """Return one exact search result before structural validation.

    Returns:
        The exact search result record.

    Raises:
        InvalidAcceleratorResultError: If the backend returned another type.

    """
    if type(value) is not SearchResult:
        message = "search backend result has wrong type"
        raise InvalidAcceleratorResultError(message)
    return value


def validated_verification_assist_result(
    value: object,
) -> VerificationAssistResult:
    """Return one exact verification result before structural validation.

    Returns:
        The exact verification-assist result record.

    Raises:
        InvalidAcceleratorResultError: If the backend returned another type.

    """
    if type(value) is not VerificationAssistResult:
        message = "verification backend result has wrong type"
        raise InvalidAcceleratorResultError(message)
    return value


def validated_accelerator_capability(
    value: object,
    label: str,
) -> AcceleratorCapability:
    """Return one exact capability record for status or result publication.

    Returns:
        The exact immutable capability after validating all identity fields.

    Raises:
        InvalidAcceleratorResultError: If type or identity fields are invalid.

    """
    if type(value) is not AcceleratorCapability:
        message = f"{label} has wrong type"
        raise InvalidAcceleratorResultError(message)
    _validate_result_identity(value.backend_id, f"{label} backend ID")
    _validate_result_identity(
        value.device_arch,
        f"{label} device architecture",
    )
    _validate_result_identity(value.device_name, f"{label} device name")
    return value


def _validate_result_u64(value: int, label: str) -> None:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        message = f"{label} outside unsigned 64-bit domain: {value!r}"
        raise InvalidAcceleratorResultError(message)


def _validate_u64(value: int, label: str) -> None:
    if type(value) is not int or not 0 <= value <= MAX_U64:
        message = f"{label} outside unsigned 64-bit domain: {value}"
        raise InvalidAcceleratorWorkError(message)


def _validate_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        message = f"duplicate {label}"
        raise InvalidAcceleratorWorkError(message)


def _validate_unique_result(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        message = f"duplicate {label}"
        raise InvalidAcceleratorResultError(message)


def _validated_hint_map(
    proposals: tuple[CandidateProposal, ...],
    hints: tuple[VerificationHint, ...],
) -> dict[str, VerificationHint]:
    _validate_proposals(proposals)
    _validate_hints(hints)
    proposal_ids = {proposal.logical_id for proposal in proposals}
    hint_map: dict[str, VerificationHint] = {}
    for hint in hints:
        if hint.logical_id not in proposal_ids:
            message = "verification hint does not name a search proposal"
            raise InvalidAcceleratorResultError(message)
        if hint.logical_id in hint_map:
            message = "duplicate verification hint logical ID"
            raise InvalidAcceleratorResultError(message)
        hint_map[hint.logical_id] = hint
    return hint_map
