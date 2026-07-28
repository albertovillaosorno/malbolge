# File:
#   - work_ports.py
# Path:
#   - accelerator/work_ports.py
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
#   - Hardware-neutral candidate, search, and verification-assist ports.
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

from accelerator.exact_primitives import AcceleratorError
from accelerator.exact_primitives import AcceleratorExecutionError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from accelerator.exact_primitives import AcceleratorCapability

INDEXED_CANDIDATE_ITEMS_ID = "u32-index-fixed-width-payloads-rotation-v1"
MAX_U32 = (1 << 32) - 1
MAX_U64 = (1 << 64) - 1
_U32_BYTES = 4
_U32_DECIMAL_DIGITS = 10
_MIN_ROTATION_SCAN_ITEMS = 2
_LITTLE_ENDIAN = "little"
_NATIVE_WORD_FORMAT = "I"
_U32_LE = Struct("<I")
_INDEXED_CANDIDATE_ITEMS_PROOF = object()


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
        if self.evaluator_id != batch.evaluator_id:
            message = "candidate evaluator ID changed during backend execution"
            raise InvalidAcceleratorResultError(message)
        if self.packed is not None:
            if self.items:
                message = "candidate evidence cannot mix packed and item forms"
                raise InvalidAcceleratorResultError(message)
            _ = self.packed.validated_for_count(len(batch.items))
            return self
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
        _validate_u64(self.seed, "search seed")
        if not 1 <= self.evaluation_budget <= MAX_U64:
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
    if preferred is not None:
        result = _try_candidate_backend(validated, preferred)
        if result is not None:
            return result
    return _candidate_backend(validated, reference)


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
    if preferred is not None:
        result = _try_search_backend(validated, preferred)
        if result is not None:
            return result
    return _search_backend(validated, reference)


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
        result = preferred.assist(validated)
        capability = preferred.capability()
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

    """
    _validate_proposals(result.proposals)
    hint_map = _validated_hint_map(result.proposals, hints)
    return tuple(
        candidate
        for candidate in result.proposals
        if verifier.accepts(candidate, hint_map.get(candidate.logical_id))
    )


def _candidate_backend(
    batch: CandidateEvaluationBatch,
    adapter: CandidateEvaluationAdapter,
) -> CandidateEvaluationResult:
    result = adapter.evaluate(batch)
    return result.validated_against(batch, adapter.capability())


def _search_backend(
    request: SearchRequest,
    adapter: SearchExecutionAdapter,
) -> SearchResult:
    result = adapter.search(request)
    return result.validated_against(request, adapter.capability())


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
    if isinstance(items, IndexedCandidateWorkItems):
        _ = items.validated()
        return
    identities = [item.validated().logical_id for item in items]
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
    if not value:
        message = f"{label} must not be empty"
        raise InvalidAcceleratorWorkError(message)


def _validate_proposals(proposals: tuple[CandidateProposal, ...]) -> None:
    identities = [proposal.logical_id for proposal in proposals]
    for identity in identities:
        if not identity:
            message = "search candidate logical ID must not be empty"
            raise InvalidAcceleratorResultError(message)
    _validate_unique_result(identities, "search candidate logical ID")


def _validate_result_capability(
    observed: AcceleratorCapability,
    expected: AcceleratorCapability,
) -> None:
    if observed != expected:
        message = "accelerator result capability does not match adapter"
        raise InvalidAcceleratorResultError(message)


def _validate_u64(value: int, label: str) -> None:
    if not 0 <= value <= MAX_U64:
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
    proposal_ids = {proposal.logical_id for proposal in proposals}
    hint_map: dict[str, VerificationHint] = {}
    for hint in hints:
        if not hint.logical_id or hint.logical_id not in proposal_ids:
            message = "verification hint does not name a search proposal"
            raise InvalidAcceleratorResultError(message)
        if hint.logical_id in hint_map:
            message = "duplicate verification hint logical ID"
            raise InvalidAcceleratorResultError(message)
        hint_map[hint.logical_id] = hint
    return hint_map
