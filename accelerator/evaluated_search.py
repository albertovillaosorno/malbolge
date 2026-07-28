# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Search execution backed by hardware-neutral candidate evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from time import perf_counter_ns
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchResult

if TYPE_CHECKING:
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationAdapter
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateEvaluationResult
    from accelerator.work_ports import CandidateProposal
    from accelerator.work_ports import SearchRequest


type SearchBatchBuilder = Callable[[SearchRequest], CandidateEvaluationBatch]
type SearchProposalSelector = Callable[
    [SearchRequest, CandidateEvaluationBatch, CandidateEvaluationResult],
    tuple[CandidateProposal, ...],
]
type SearchBatchPreparer = Callable[[CandidateEvaluationBatch], object]
type SearchPreparedEvaluator = Callable[[object], CandidateEvaluationResult]
type SearchStrategyKey = tuple[
    str,
    SearchBatchBuilder,
    SearchProposalSelector,
    SearchBatchPreparer | None,
]
type CandidateMembershipIndex = frozenset[tuple[str, bytes]]

_PREPARED_PROOF = object()
_NO_CANDIDATE_STATE = object()


@dataclass(frozen=True, slots=True)
class PreparedCandidateExecution:
    """Strategy preparation plus backend-specific prepared evaluation."""

    batch_preparer: SearchBatchPreparer
    evaluator: SearchPreparedEvaluator


@dataclass(frozen=True, slots=True)
class EvaluatedSearchStrategy:
    """Hardware-neutral evaluated-search strategy callbacks."""

    batch_builder: SearchBatchBuilder
    proposal_selector: SearchProposalSelector
    prepared_execution: PreparedCandidateExecution | None = None


@dataclass(frozen=True, slots=True)
class PreparedEvaluatedSearch:
    """Validated request/batch state reusable across exact backends."""

    request: SearchRequest
    batch: CandidateEvaluationBatch
    _candidate_state: object = field(repr=False)
    _membership_index: CandidateMembershipIndex = field(repr=False)
    _proof: object = field(repr=False)
    _strategy_key: SearchStrategyKey = field(repr=False)

    def for_strategy(
        self,
        strategy_key: SearchStrategyKey,
    ) -> tuple[
        SearchRequest,
        CandidateEvaluationBatch,
        object,
        CandidateMembershipIndex,
    ]:
        """Return state only to the exact strategy that prepared it.

        Returns:
            Validated request, batch, candidate state, and membership index.

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
            self._membership_index,
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
        self._proposal_selector = strategy.proposal_selector
        self._strategy_key: SearchStrategyKey = (
            algorithm_id,
            strategy.batch_builder,
            strategy.proposal_selector,
            self._batch_preparer,
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
        return PreparedEvaluatedSearch(
            request=validated,
            batch=batch,
            _candidate_state=self._prepare_candidate_state(batch),
            _membership_index=_candidate_membership_index(batch),
            _proof=_PREPARED_PROOF,
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
        request, batch, candidate_state, membership_index = self._prepared(
            prepared
        )
        return self._search_prepared_validated(
            request,
            batch,
            candidate_state,
            membership_index=membership_index,
        )

    def prepared_membership_count(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> int:
        """Return exact candidate membership count after strategy validation.

        Returns:
            Number of immutable candidate identity/payload pairs in the index.

        Raises:
            InvalidAcceleratorWorkError: If state/strategy/index identity fails.

        """
        _, batch, _, membership_index = self._prepared(prepared)
        if len(membership_index) != len(batch.items):
            message = "prepared membership index does not cover candidate batch"
            raise InvalidAcceleratorWorkError(message)
        return len(membership_index)

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
        request, batch, candidate_state, membership_index = recorder.measure(
            "prepared_validation_ns",
            lambda: self._prepared(prepared),
        )
        capability = self.capability()
        evidence = recorder.measure(
            "backend_evaluation_ns",
            lambda: self._evaluated_prepared(
                batch,
                candidate_state,
                capability,
            ),
        )
        proposals = recorder.measure(
            "proposal_selection_ns",
            lambda: self._selected(
                request,
                batch,
                evidence,
                membership_index=membership_index,
            ),
        )
        result = recorder.measure(
            "result_validation_ns",
            lambda: self._result(request, capability, proposals),
        )
        return ProfiledPreparedSearchResult(
            phases=recorder.finish_prepared(),
            result=result,
        )

    def _prepared(
        self,
        prepared: PreparedEvaluatedSearch,
    ) -> tuple[
        SearchRequest,
        CandidateEvaluationBatch,
        object,
        CandidateMembershipIndex,
    ]:
        return prepared.for_strategy(self._strategy_key)

    def _prepare_candidate_state(
        self,
        batch: CandidateEvaluationBatch,
    ) -> object:
        if self._batch_preparer is None:
            return _NO_CANDIDATE_STATE
        state = self._batch_preparer(batch)
        if state is _NO_CANDIDATE_STATE:
            message = "candidate batch preparer returned reserved state"
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
        request: SearchRequest,
        batch: CandidateEvaluationBatch,
        candidate_state: object,
        *,
        membership_index: CandidateMembershipIndex,
    ) -> SearchResult:
        capability = self.capability()
        evidence = self._evaluated_prepared(
            batch,
            candidate_state,
            capability,
        )
        proposals = self._selected(
            request,
            batch,
            evidence,
            membership_index=membership_index,
        )
        return self._result(request, capability, proposals)

    def _evaluated_prepared(
        self,
        batch: CandidateEvaluationBatch,
        candidate_state: object,
        capability: AcceleratorCapability,
    ) -> CandidateEvaluationResult:
        if candidate_state is _NO_CANDIDATE_STATE:
            return self._evaluated(batch, capability)
        if self._prepared_evaluator is None:
            message = "prepared candidate state has no evaluator"
            raise InvalidAcceleratorWorkError(message)
        return self._prepared_evaluator(candidate_state).validated_against(
            batch,
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
        membership_index: CandidateMembershipIndex | None = None,
    ) -> tuple[CandidateProposal, ...]:
        proposals = self._proposal_selector(request, batch, evidence)
        _validate_proposal_membership(
            proposals,
            batch,
            membership_index=membership_index,
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


def _candidate_membership_index(
    batch: CandidateEvaluationBatch,
) -> CandidateMembershipIndex:
    return frozenset((item.logical_id, item.payload) for item in batch.items)


def _validate_proposal_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
    *,
    membership_index: CandidateMembershipIndex | None = None,
) -> None:
    if not proposals:
        return
    if membership_index is not None:
        _validate_indexed_membership(proposals, membership_index)
        return
    candidates = {item.logical_id: item.payload for item in batch.items}
    for proposal in proposals:
        payload = candidates.get(proposal.logical_id)
        if payload is None or payload != proposal.payload:
            _raise_invalid_proposal_membership()


def _validate_indexed_membership(
    proposals: tuple[CandidateProposal, ...],
    membership_index: CandidateMembershipIndex,
) -> None:
    for proposal in proposals:
        if (proposal.logical_id, proposal.payload) not in membership_index:
            _raise_invalid_proposal_membership()


def _raise_invalid_proposal_membership() -> None:
    message = "evaluated search proposal was not in evaluated candidate batch"
    raise InvalidAcceleratorWorkError(message)
