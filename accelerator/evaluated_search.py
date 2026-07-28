# File:
#   - evaluated_search.py
# Path:
#   - accelerator/evaluated_search.py
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
#   - Search execution backed by hardware-neutral candidate evaluation.
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

"""Search execution backed by hardware-neutral candidate evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from operator import attrgetter
from operator import itemgetter
from struct import Struct
from time import perf_counter_ns
from typing import Protocol
from typing import Self
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.work_ports import CandidateEvaluationResult
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchResult

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateWorkItem
    from accelerator.work_ports import PreparedCandidateSubset
    from accelerator.work_ports import SearchRequest


type SearchBatchBuilder = Callable[[SearchRequest], CandidateEvaluationBatch]
type SearchProposalSelector = Callable[
    [SearchRequest, CandidateEvaluationBatch, CandidateEvaluationResult],
    tuple[CandidateProposal, ...],
]
type SearchBatchPreparer = Callable[[CandidateEvaluationBatch], object]
type SearchSelectionAwareBatchPreparer = Callable[
    [SearchRequest, CandidateEvaluationBatch, object],
    object,
]
type SearchPreparedEvaluator = Callable[[object], CandidateEvaluationResult]
type SearchCandidateStateCount = Callable[[object], int]
type SearchSelectionPreparer = Callable[
    [SearchRequest, CandidateEvaluationBatch],
    object,
]


class SearchPreparedProposalSelector(Protocol):
    """Prepared proposal callback with explicit selector state."""

    def __call__(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
        evidence: CandidateEvaluationResult,
        *,
        state: object,
    ) -> tuple[CandidateProposal, ...]:
        """Return untrusted proposals from prepared selector state."""
        ...


type SearchSelectionStateCount = Callable[[object], int]
type SearchStrategyKey = tuple[
    str,
    SearchBatchBuilder,
    SearchProposalSelector,
    SearchBatchPreparer | None,
    SearchSelectionAwareBatchPreparer | None,
    SearchCandidateStateCount | None,
    SearchSelectionPreparer | None,
    SearchPreparedProposalSelector | None,
    SearchSelectionStateCount | None,
]
PREPARED_MEMBERSHIP_INDEX_ID = (
    "u32-rotation-or-pair-or-reference-binary-search-v1"
)
_INDEXED_MEMBERSHIP_PAIR = Struct("<II")
_INDEXED_MEMBERSHIP_PAIR_BYTES = _INDEXED_MEMBERSHIP_PAIR.size

_PREPARED_PROOF = object()
_PREPARED_MEMBERSHIP_PROOF = object()
_PREPARED_CANDIDATE_PROJECTION_PROOF = object()
_NO_CANDIDATE_STATE = object()
_NO_SELECTION_STATE = object()


def prepared_membership_index_id() -> str:
    """Return the active exact prepared membership algorithm identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PREPARED_MEMBERSHIP_INDEX_ID


@dataclass(frozen=True, slots=True)
class PreparedCandidateMembershipIndex:
    """Immutable exact membership index for one candidate batch."""

    batch: CandidateEvaluationBatch
    items_by_identity: tuple[CandidateWorkItem, ...]
    indexed_pairs_u32le: bytes
    _proof: object = field(repr=False)

    @classmethod
    def prepare(cls, batch: CandidateEvaluationBatch) -> Self:
        """Build one proof-bound index from a validated batch.

        Returns:
            Packed u32 index/position pairs or sorted ordinary item references.

        """
        validated = batch.validated()
        if isinstance(validated.items, IndexedCandidateWorkItems):
            return cls(
                batch=validated,
                items_by_identity=(),
                indexed_pairs_u32le=(
                    b""
                    if validated.items.logical_rotation_pivot is not None
                    else _indexed_membership_pairs(validated.items)
                ),
                _proof=_PREPARED_MEMBERSHIP_PROOF,
            )
        return cls(
            batch=validated,
            items_by_identity=tuple(
                sorted(validated.items, key=attrgetter("logical_id"))
            ),
            indexed_pairs_u32le=b"",
            _proof=_PREPARED_MEMBERSHIP_PROOF,
        )

    def count_for(self, batch: CandidateEvaluationBatch) -> int:
        """Return exact indexed candidate count for the original batch.

        Returns:
            Number of proof-bound candidate references or packed pairs.

        """
        self._validate_for(batch)
        return len(batch.items)

    def contains(
        self,
        batch: CandidateEvaluationBatch,
        proposal: CandidateProposal,
    ) -> bool:
        """Return whether one proposal exactly matches an indexed candidate.

        Returns:
            True only for byte-identical identity and payload membership.

        """
        self._validate_for(batch)
        if isinstance(batch.items, IndexedCandidateWorkItems):
            return self._contains_indexed(batch, proposal)
        return _contains_sorted_items(self.items_by_identity, proposal)

    def _contains_indexed(
        self,
        batch: CandidateEvaluationBatch,
        proposal: CandidateProposal,
    ) -> bool:
        items = batch.items
        if not isinstance(items, IndexedCandidateWorkItems):
            message = "packed membership index requires indexed candidate items"
            raise InvalidAcceleratorWorkError(message)
        logical_index = items.parse_logical_id(proposal.logical_id)
        if logical_index is None:
            return False
        if items.logical_rotation_pivot is not None:
            position = _find_rotated_index_position(items, logical_index)
        else:
            position = _find_indexed_membership_position(
                self.indexed_pairs_u32le,
                logical_index,
            )
        return position is not None and items.payload_matches(
            position,
            proposal.payload,
        )

    def _validate_for(self, batch: CandidateEvaluationBatch) -> None:
        if self._proof is not _PREPARED_MEMBERSHIP_PROOF:
            message = "prepared candidate membership index is forged"
            raise InvalidAcceleratorWorkError(message)
        if self.batch is not batch:
            message = (
                "prepared candidate membership index changed candidate batch"
            )
            raise InvalidAcceleratorWorkError(message)
        _validate_membership_representation(self, batch)


@dataclass(frozen=True, slots=True)
class PreparedCandidateProjection:
    """Proof-bound projected subset paired with strategy candidate state."""

    subset: PreparedCandidateSubset
    state: object
    _proof: object = field(repr=False, compare=False)

    def for_batch(
        self,
        full_batch: CandidateEvaluationBatch,
    ) -> tuple[object, CandidateEvaluationBatch]:
        """Return candidate state and exact sub-batch for one full batch.

        Returns:
            Strategy state plus the proof-bound request-order evaluation batch.

        Raises:
            InvalidAcceleratorWorkError: If the projection proof is forged.

        """
        if self._proof is not _PREPARED_CANDIDATE_PROJECTION_PROOF:
            message = "prepared candidate projection is forged"
            raise InvalidAcceleratorWorkError(message)
        projected, _ = self.subset.for_batch(full_batch)
        return (self.state, projected)


def prepare_candidate_projection(
    full_batch: CandidateEvaluationBatch,
    subset: PreparedCandidateSubset,
    state: object,
) -> PreparedCandidateProjection:
    """Bind strategy state to one exact projected candidate subset.

    Returns:
        Immutable projection authorized for the exact full candidate batch.

    """
    _ = subset.for_batch(full_batch)
    return PreparedCandidateProjection(
        subset=subset,
        state=state,
        _proof=_PREPARED_CANDIDATE_PROJECTION_PROOF,
    )


@dataclass(frozen=True, slots=True)
class PreparedCandidateExecution:
    """Strategy preparation plus backend-specific prepared evaluation."""

    batch_preparer: SearchBatchPreparer | None
    evaluator: SearchPreparedEvaluator
    selection_aware_preparer: SearchSelectionAwareBatchPreparer | None = None
    state_count: SearchCandidateStateCount | None = None


@dataclass(frozen=True, slots=True)
class PreparedProposalSelection:
    """Strategy-owned preparation and exact prepared proposal selection."""

    state_preparer: SearchSelectionPreparer
    selector: SearchPreparedProposalSelector
    state_count: SearchSelectionStateCount


@dataclass(frozen=True, slots=True)
class EvaluatedSearchStrategy:
    """Hardware-neutral evaluated-search strategy callbacks."""

    batch_builder: SearchBatchBuilder
    proposal_selector: SearchProposalSelector
    prepared_execution: PreparedCandidateExecution | None = None
    prepared_selection: PreparedProposalSelection | None = None


@dataclass(frozen=True, slots=True)
class PreparedEvaluatedSearch:
    """Validated request/batch state reusable across exact backends."""

    request: SearchRequest
    batch: CandidateEvaluationBatch
    _candidate_state: object = field(repr=False)
    _evaluation_batch: CandidateEvaluationBatch = field(repr=False)
    _membership_index: PreparedCandidateMembershipIndex = field(repr=False)
    _proof: object = field(repr=False)
    _selection_state: object = field(repr=False)
    _strategy_key: SearchStrategyKey = field(repr=False)

    def for_strategy(
        self,
        strategy_key: SearchStrategyKey,
    ) -> tuple[
        SearchRequest,
        CandidateEvaluationBatch,
        object,
        CandidateEvaluationBatch,
        PreparedCandidateMembershipIndex,
        object,
    ]:
        """Return state only to the exact strategy that prepared it.

        Returns:
            Validated request, full batch, candidate state, exact evaluation
            sub-batch, membership index, and prepared proposal-selection state.

        Raises:
            InvalidAcceleratorWorkError: If this state is forged or belongs to a
                different strategy implementation.

        """
        if self._proof is not _PREPARED_PROOF:
            message = "prepared search state was not created by prepare"
            raise InvalidAcceleratorWorkError(message)
        if self._strategy_key != strategy_key:
            message = "prepared search state belongs to a different strategy"
            raise InvalidAcceleratorWorkError(message)
        return (
            self.request,
            self.batch,
            self._candidate_state,
            self._evaluation_batch,
            self._membership_index,
            self._selection_state,
        )


@dataclass(frozen=True, slots=True)
class EvaluatedSearchPhaseProfile:
    """Wall-clock phase diagnostics for one ordinary search execution."""

    backend_evaluation_ns: int
    batch_build_ns: int
    batch_validation_ns: int
    proposal_selection_ns: int
    request_validation_ns: int
    result_validation_ns: int
    total_ns: int


@dataclass(frozen=True, slots=True)
class PreparedSearchPhaseProfile:
    """Wall-clock phases after validated search state is prepared."""

    backend_evaluation_ns: int
    prepared_validation_ns: int
    proposal_selection_ns: int
    result_validation_ns: int
    total_ns: int


@dataclass(frozen=True, slots=True)
class ProfiledSearchResult:
    """One ordinary search result paired with timing diagnostics."""

    phases: EvaluatedSearchPhaseProfile
    result: SearchResult


@dataclass(frozen=True, slots=True)
class ProfiledPreparedSearchResult:
    """One prepared search result paired with timing diagnostics."""

    phases: PreparedSearchPhaseProfile
    result: SearchResult


@dataclass(frozen=True, slots=True)
class _ResolvedPreparedSearch:
    request: SearchRequest
    batch: CandidateEvaluationBatch
    candidate_state: object
    evaluation_batch: CandidateEvaluationBatch
    membership_index: PreparedCandidateMembershipIndex
    selection_state: object


@final
class EvaluatedSearchExecutionAdapter(SearchExecutionAdapter):
    """Run one search strategy through a replaceable candidate evaluator."""

    def __init__(
        self,
        algorithm_id: str,
        adapter: CandidateEvaluationAdapter,
        strategy: EvaluatedSearchStrategy,
    ) -> None:
        """Bind one strategy to one replaceable evidence backend.

        Raises:
            InvalidAcceleratorWorkError: If algorithm identity is empty.

        """
        if not algorithm_id:
            message = "search algorithm ID must not be empty"
            raise InvalidAcceleratorWorkError(message)
        self._adapter = adapter
        self._algorithm_id = algorithm_id
        self._batch_builder = strategy.batch_builder
        self._batch_preparer = (
            None
            if strategy.prepared_execution is None
            else strategy.prepared_execution.batch_preparer
        )
        self._prepared_evaluator = (
            None
            if strategy.prepared_execution is None
            else strategy.prepared_execution.evaluator
        )
        self._selection_aware_batch_preparer = (
            None
            if strategy.prepared_execution is None
            else strategy.prepared_execution.selection_aware_preparer
        )
        self._candidate_state_count = (
            None
            if strategy.prepared_execution is None
            else strategy.prepared_execution.state_count
        )
        if strategy.prepared_execution is not None:
            preparer_count = int(self._batch_preparer is not None) + int(
                self._selection_aware_batch_preparer is not None
            )
            if preparer_count != 1:
                message = (
                    "prepared candidate execution requires exactly one preparer"
                )
                raise InvalidAcceleratorWorkError(message)
        self._proposal_selector = strategy.proposal_selector
        self._selection_preparer = (
            None
            if strategy.prepared_selection is None
            else strategy.prepared_selection.state_preparer
        )
        self._prepared_proposal_selector = (
            None
            if strategy.prepared_selection is None
            else strategy.prepared_selection.selector
        )
        self._selection_state_count = (
            None
            if strategy.prepared_selection is None
            else strategy.prepared_selection.state_count
        )
        self._strategy_key: SearchStrategyKey = (
            algorithm_id,
            strategy.batch_builder,
            strategy.proposal_selector,
            self._batch_preparer,
            self._selection_aware_batch_preparer,
            self._candidate_state_count,
            self._selection_preparer,
            self._prepared_proposal_selector,
            self._selection_state_count,
        )

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the wrapped candidate-evaluation backend identity.

        Returns:
            Exact capability reported by the wrapped evaluator.

        """
        return self._adapter.capability()

    def prepare(self, request: SearchRequest) -> PreparedEvaluatedSearch:
        """Build and validate immutable search state once for later reuse.

        Returns:
            Hardware-neutral request and candidate batch bound to this exact
            strategy identity.

        """
        validated = self._validated_request(request)
        batch = self._validated_batch(validated)
        membership_index = _candidate_membership_index(batch)
        selection_state = self._prepare_selection_state(validated, batch)
        candidate_state, evaluation_batch = self._prepare_candidate_state(
            validated,
            batch,
            selection_state,
        )
        return PreparedEvaluatedSearch(
            request=validated,
            batch=batch,
            _candidate_state=candidate_state,
            _evaluation_batch=evaluation_batch,
            _membership_index=membership_index,
            _proof=_PREPARED_PROOF,
            _selection_state=selection_state,
            _strategy_key=self._strategy_key,
        )

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        """Evaluate a bounded corpus and return untrusted selected proposals.

        Returns:
            Structurally validated proposals selected from evaluated candidates.

        """
        validated = self._validated_request(request)
        batch = self._validated_batch(validated)
        return self._search_validated(validated, batch)

    def search_prepared(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> SearchResult:
        """Evaluate already prepared immutable state through this backend.

        Returns:
            Structurally validated untrusted proposals.

        """
        resolved = self._prepared(prepared)
        return self._search_prepared_validated(resolved)

    def prepared_candidate_state_count(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> int:
        """Return strategy-defined prepared candidate-state cardinality.

        Returns:
            Nonnegative candidate-state item count, or zero when unavailable.

        Raises:
            InvalidAcceleratorWorkError: If strategy/count identity fails.

        """
        resolved = self._prepared(prepared)
        if resolved.candidate_state is _NO_CANDIDATE_STATE:
            return 0
        if self._candidate_state_count is None:
            return 0
        count = self._candidate_state_count(resolved.candidate_state)
        if type(count) is not int or count < 0:
            message = (
                "prepared candidate state count must be nonnegative integer"
            )
            raise InvalidAcceleratorWorkError(message)
        return count

    def prepared_membership_count(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> int:
        """Return exact candidate membership count after strategy validation.

        Returns:
            Number of immutable candidate identity/payload pairs in the index.

        """
        resolved = self._prepared(prepared)
        return resolved.membership_index.count_for(resolved.batch)

    def prepared_selection_count(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> int:
        """Return strategy-defined prepared selector state cardinality.

        Returns:
            Nonnegative selector-state item count, or zero when disabled.

        Raises:
            InvalidAcceleratorWorkError: If state/strategy/count identity fails.

        """
        resolved = self._prepared(prepared)
        if resolved.selection_state is _NO_SELECTION_STATE:
            return 0
        if self._selection_state_count is None:
            message = "prepared selection state has no count function"
            raise InvalidAcceleratorWorkError(message)
        count = self._selection_state_count(resolved.selection_state)
        if type(count) is not int or count < 0:
            message = (
                "prepared selection state count must be nonnegative integer"
            )
            raise InvalidAcceleratorWorkError(message)
        return count

    def profile_search(self, request: SearchRequest) -> ProfiledSearchResult:
        """Execute one ordinary search with wall-clock phase diagnostics.

        Returns:
            The ordinary validated result plus diagnostic phase durations.

        """
        recorder = _PhaseRecorder()
        validated = recorder.measure(
            "request_validation_ns",
            lambda: self._validated_request(request),
        )
        batch = recorder.measure(
            "batch_build_ns",
            lambda: self._batch_builder(validated),
        )
        batch = recorder.measure(
            "batch_validation_ns",
            lambda: _validate_batch(validated, batch),
        )
        capability = self.capability()
        evidence = recorder.measure(
            "backend_evaluation_ns",
            lambda: self._evaluated(batch, capability),
        )
        proposals = recorder.measure(
            "proposal_selection_ns",
            lambda: self._selected(validated, batch, evidence),
        )
        result = recorder.measure(
            "result_validation_ns",
            lambda: self._result(validated, capability, proposals),
        )
        return ProfiledSearchResult(
            phases=recorder.finish_ordinary(),
            result=result,
        )

    def profile_prepared_search(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> ProfiledPreparedSearchResult:
        """Execute prepared state with post-preparation phase diagnostics.

        Returns:
            Validated untrusted proposals plus amortized-path phase durations.

        """
        recorder = _PhaseRecorder()
        resolved = recorder.measure(
            "prepared_validation_ns",
            lambda: self._prepared(prepared),
        )
        capability = self.capability()
        evidence = recorder.measure(
            "backend_evaluation_ns",
            lambda: self._evaluated_prepared(
                resolved.evaluation_batch,
                resolved.candidate_state,
                capability,
            ),
        )
        proposals = recorder.measure(
            "proposal_selection_ns",
            lambda: self._selected_prepared(resolved, evidence),
        )
        result = recorder.measure(
            "result_validation_ns",
            lambda: self._result(
                resolved.request,
                capability,
                proposals,
            ),
        )
        return ProfiledPreparedSearchResult(
            phases=recorder.finish_prepared(),
            result=result,
        )

    def _prepared(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> _ResolvedPreparedSearch:
        (
            request,
            batch,
            candidate_state,
            evaluation_batch,
            membership_index,
            selection_state,
        ) = prepared.for_strategy(self._strategy_key)
        return _ResolvedPreparedSearch(
            request=request,
            batch=batch,
            candidate_state=candidate_state,
            evaluation_batch=evaluation_batch,
            membership_index=membership_index,
            selection_state=selection_state,
        )

    def _prepare_candidate_state(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
        selection_state: object,
    ) -> tuple[object, CandidateEvaluationBatch]:
        if self._selection_aware_batch_preparer is not None:
            projection = self._selection_aware_batch_preparer(
                request,
                batch,
                selection_state,
            )
            if not isinstance(projection, PreparedCandidateProjection):
                message = (
                    "selection-aware preparer returned wrong projection type"
                )
                raise InvalidAcceleratorWorkError(message)
            state, evaluation_batch = projection.for_batch(batch)
        elif self._batch_preparer is not None:
            state = self._batch_preparer(batch)
            evaluation_batch = batch
        else:
            return (_NO_CANDIDATE_STATE, batch)
        if state is _NO_CANDIDATE_STATE:
            message = "candidate batch preparer returned reserved state"
            raise InvalidAcceleratorWorkError(message)
        return (state, evaluation_batch)

    def _prepare_selection_state(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
    ) -> object:
        if self._selection_preparer is None:
            return _NO_SELECTION_STATE
        state = self._selection_preparer(request, batch)
        if state is _NO_SELECTION_STATE:
            message = "proposal selection preparer returned reserved state"
            raise InvalidAcceleratorWorkError(message)
        return state

    def _validated_request(self, request: SearchRequest) -> SearchRequest:
        validated = request.validated()
        if validated.algorithm_id != self._algorithm_id:
            message = "search request selects a different algorithm"
            raise InvalidAcceleratorWorkError(message)
        return validated

    def _validated_batch(
        self,
        request: SearchRequest,
    ) -> CandidateEvaluationBatch:
        return _validate_batch(request, self._batch_builder(request))

    def _search_validated(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
    ) -> SearchResult:
        capability = self.capability()
        evidence = self._evaluated(batch, capability)
        proposals = self._selected(request, batch, evidence)
        return self._result(request, capability, proposals)

    def _search_prepared_validated(
        self,
        resolved: _ResolvedPreparedSearch,
    ) -> SearchResult:
        capability = self.capability()
        evidence = self._evaluated_prepared(
            resolved.evaluation_batch,
            resolved.candidate_state,
            capability,
        )
        proposals = self._selected_prepared(resolved, evidence)
        return self._result(resolved.request, capability, proposals)

    def _evaluated_prepared(
        self,
        evaluation_batch: CandidateEvaluationBatch,
        candidate_state: object,
        capability: AcceleratorCapability,
    ) -> CandidateEvaluationResult:
        if candidate_state is _NO_CANDIDATE_STATE:
            return self._evaluated(evaluation_batch, capability)
        if not evaluation_batch.items:
            return CandidateEvaluationResult(
                capability=capability,
                evaluator_id=evaluation_batch.evaluator_id,
            )
        if self._prepared_evaluator is None:
            message = "prepared candidate state has no evaluator"
            raise InvalidAcceleratorWorkError(message)
        return self._prepared_evaluator(candidate_state).validated_against(
            evaluation_batch,
            capability,
        )

    def _evaluated(
        self,
        batch: CandidateEvaluationBatch,
        capability: AcceleratorCapability,
    ) -> CandidateEvaluationResult:
        return self._adapter.evaluate(batch).validated_against(
            batch,
            capability,
        )

    def _selected(
        self,
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
        evidence: CandidateEvaluationResult,
        *,
        membership_index: PreparedCandidateMembershipIndex | None = None,
    ) -> tuple[CandidateProposal, ...]:
        proposals = self._proposal_selector(request, batch, evidence)
        _validate_proposal_membership(
            proposals,
            batch,
            membership_index=membership_index,
        )
        return proposals

    def _selected_prepared(
        self,
        resolved: _ResolvedPreparedSearch,
        evidence: CandidateEvaluationResult,
    ) -> tuple[CandidateProposal, ...]:
        if resolved.selection_state is _NO_SELECTION_STATE:
            return self._selected(
                resolved.request,
                resolved.batch,
                evidence,
                membership_index=resolved.membership_index,
            )
        if self._prepared_proposal_selector is None:
            message = "prepared selection state has no selector"
            raise InvalidAcceleratorWorkError(message)
        proposals = self._prepared_proposal_selector(
            resolved.request,
            resolved.batch,
            evidence,
            state=resolved.selection_state,
        )
        _validate_proposal_membership(
            proposals,
            resolved.batch,
            membership_index=resolved.membership_index,
        )
        return proposals

    def _result(
        self,
        request: SearchRequest,
        capability: AcceleratorCapability,
        proposals: tuple[CandidateProposal, ...],
    ) -> SearchResult:
        return SearchResult(
            algorithm_id=self._algorithm_id,
            capability=capability,
            proposals=proposals,
            seed=request.seed,
        ).validated_against(request, capability)


@final
class _PhaseRecorder:
    """Collect named wall-clock intervals without affecting ordinary search."""

    def __init__(self) -> None:
        self._durations: dict[str, int] = {}
        self._total_start = perf_counter_ns()

    def measure[T](self, name: str, action: Callable[[], T]) -> T:
        """Run one action and retain its elapsed wall-clock duration.

        Returns:
            The action result unchanged.

        """
        start = perf_counter_ns()
        result = action()
        self._durations[name] = perf_counter_ns() - start
        return result

    def finish_ordinary(self) -> EvaluatedSearchPhaseProfile:
        """Materialize immutable ordinary-search phase diagnostics.

        Returns:
            Complete phase durations plus inclusive total wall time.

        """
        return EvaluatedSearchPhaseProfile(
            backend_evaluation_ns=self._duration("backend_evaluation_ns"),
            batch_build_ns=self._duration("batch_build_ns"),
            batch_validation_ns=self._duration("batch_validation_ns"),
            proposal_selection_ns=self._duration("proposal_selection_ns"),
            request_validation_ns=self._duration("request_validation_ns"),
            result_validation_ns=self._duration("result_validation_ns"),
            total_ns=perf_counter_ns() - self._total_start,
        )

    def finish_prepared(self) -> PreparedSearchPhaseProfile:
        """Materialize immutable prepared-search phase diagnostics.

        Returns:
            Post-preparation phase durations plus inclusive total wall time.

        """
        return PreparedSearchPhaseProfile(
            backend_evaluation_ns=self._duration("backend_evaluation_ns"),
            prepared_validation_ns=self._duration("prepared_validation_ns"),
            proposal_selection_ns=self._duration("proposal_selection_ns"),
            result_validation_ns=self._duration("result_validation_ns"),
            total_ns=perf_counter_ns() - self._total_start,
        )

    def _duration(self, name: str) -> int:
        value = self._durations.get(name)
        if value is None:
            message = f"evaluated search phase was not measured: {name}"
            raise RuntimeError(message)
        return value


def _validate_batch(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> CandidateEvaluationBatch:
    validated = batch.validated()
    if len(validated.items) > request.evaluation_budget:
        message = "evaluated search batch exceeds declared evaluation budget"
        raise InvalidAcceleratorWorkError(message)
    return validated


def _contains_sorted_items(
    items: tuple[CandidateWorkItem, ...],
    proposal: CandidateProposal,
) -> bool:
    lower = 0
    upper = len(items)
    while lower < upper:
        middle = (lower + upper) // 2
        if items[middle].logical_id < proposal.logical_id:
            lower = middle + 1
        else:
            upper = middle
    if lower == len(items):
        return False
    item = items[lower]
    return (
        item.logical_id == proposal.logical_id
        and item.payload == proposal.payload
    )


def _find_rotated_index_position(
    items: IndexedCandidateWorkItems,
    logical_index: int,
) -> int | None:
    pivot = items.logical_rotation_pivot
    if pivot is None:
        message = "rotated index search requires a validated rotation pivot"
        raise InvalidAcceleratorWorkError(message)
    position = _binary_search_logical_index(
        items,
        logical_index,
        lower=0,
        upper=pivot,
    )
    if position is not None:
        return position
    return _binary_search_logical_index(
        items,
        logical_index,
        lower=pivot,
        upper=len(items),
    )


def _binary_search_logical_index(
    items: IndexedCandidateWorkItems,
    logical_index: int,
    *,
    lower: int,
    upper: int,
) -> int | None:
    while lower < upper:
        middle = (lower + upper) // 2
        observed = items.logical_index_at(middle)
        if observed < logical_index:
            lower = middle + 1
        else:
            upper = middle
    if lower == len(items) or items.logical_index_at(lower) != logical_index:
        return None
    return lower


def _indexed_membership_pairs(items: IndexedCandidateWorkItems) -> bytes:
    ordered = sorted(
        (
            (items.logical_index_at(position), position)
            for position in range(len(items))
        ),
        key=itemgetter(0),
    )
    packed = bytearray(len(ordered) * _INDEXED_MEMBERSHIP_PAIR_BYTES)
    for pair_index, pair in enumerate(ordered):
        _INDEXED_MEMBERSHIP_PAIR.pack_into(
            packed,
            pair_index * _INDEXED_MEMBERSHIP_PAIR_BYTES,
            *pair,
        )
    return bytes(packed)


def _find_indexed_membership_position(
    pairs_u32le: bytes,
    logical_index: int,
) -> int | None:
    lower = 0
    upper = len(pairs_u32le) // _INDEXED_MEMBERSHIP_PAIR_BYTES
    while lower < upper:
        middle = (lower + upper) // 2
        observed, _ = _indexed_membership_pair_at(pairs_u32le, middle)
        if observed < logical_index:
            lower = middle + 1
        else:
            upper = middle
    if lower == len(pairs_u32le) // _INDEXED_MEMBERSHIP_PAIR_BYTES:
        return None
    observed, position = _indexed_membership_pair_at(pairs_u32le, lower)
    return position if observed == logical_index else None


def _indexed_membership_pair_at(
    pairs_u32le: bytes,
    index: int,
) -> tuple[int, int]:
    return _INDEXED_MEMBERSHIP_PAIR.unpack_from(
        pairs_u32le,
        index * _INDEXED_MEMBERSHIP_PAIR_BYTES,
    )


def _validate_membership_representation(
    index: PreparedCandidateMembershipIndex,
    batch: CandidateEvaluationBatch,
) -> None:
    if isinstance(batch.items, IndexedCandidateWorkItems):
        _validate_indexed_membership_representation(index, batch.items)
        return
    _validate_ordinary_membership_representation(index, len(batch.items))


def _validate_indexed_membership_representation(
    index: PreparedCandidateMembershipIndex,
    items: IndexedCandidateWorkItems,
) -> None:
    if index.items_by_identity:
        message = "indexed membership retained ordinary candidate references"
        raise InvalidAcceleratorWorkError(message)
    if items.logical_rotation_pivot is not None:
        if index.indexed_pairs_u32le:
            message = "rotated membership retained redundant packed pairs"
            raise InvalidAcceleratorWorkError(message)
        return
    expected = len(items) * _INDEXED_MEMBERSHIP_PAIR_BYTES
    if len(index.indexed_pairs_u32le) != expected:
        message = "packed membership index does not cover candidate batch"
        raise InvalidAcceleratorWorkError(message)


def _validate_ordinary_membership_representation(
    index: PreparedCandidateMembershipIndex,
    count: int,
) -> None:
    if index.indexed_pairs_u32le:
        message = "ordinary membership retained packed index pairs"
        raise InvalidAcceleratorWorkError(message)
    if len(index.items_by_identity) != count:
        message = "prepared membership index does not cover candidate batch"
        raise InvalidAcceleratorWorkError(message)


def _candidate_membership_index(
    batch: CandidateEvaluationBatch,
) -> PreparedCandidateMembershipIndex:
    return PreparedCandidateMembershipIndex.prepare(batch)


def _validate_proposal_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
    *,
    membership_index: PreparedCandidateMembershipIndex | None = None,
) -> None:
    if not proposals:
        return
    resolved_index = _resolved_membership_index(batch, membership_index)
    if resolved_index is not None:
        _validate_indexed_membership(proposals, batch, resolved_index)
        return
    _validate_ordinary_tuple_membership(proposals, batch)


def _resolved_membership_index(
    batch: CandidateEvaluationBatch,
    membership_index: PreparedCandidateMembershipIndex | None,
) -> PreparedCandidateMembershipIndex | None:
    if membership_index is not None:
        return membership_index
    if isinstance(batch.items, IndexedCandidateWorkItems):
        return PreparedCandidateMembershipIndex.prepare(batch)
    return None


def _validate_ordinary_tuple_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
) -> None:
    candidates = {item.logical_id: item.payload for item in batch.items}
    for proposal in proposals:
        payload = candidates.get(proposal.logical_id)
        if payload is None or payload != proposal.payload:
            _raise_invalid_proposal_membership()


def _validate_indexed_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
    membership_index: PreparedCandidateMembershipIndex,
) -> None:
    for proposal in proposals:
        if not membership_index.contains(batch, proposal):
            _raise_invalid_proposal_membership()


def _raise_invalid_proposal_membership() -> None:
    message = "evaluated search proposal was not in evaluated candidate batch"
    raise InvalidAcceleratorWorkError(message)
