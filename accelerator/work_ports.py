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

from dataclasses import dataclass
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator.exact_primitives import AcceleratorError
from accelerator.exact_primitives import AcceleratorExecutionError

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability

MAX_U64 = (1 << 64) - 1


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
class CandidateEvaluationBatch:
    """Candidate evidence request independent from accelerator hardware."""

    evaluator_id: str
    items: tuple[CandidateWorkItem, ...]

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


def _validate_candidate_items(items: tuple[CandidateWorkItem, ...]) -> None:
    identities = [item.validated().logical_id for item in items]
    _validate_unique(identities, "candidate logical ID")


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
