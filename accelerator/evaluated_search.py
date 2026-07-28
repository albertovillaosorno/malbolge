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
type SearchStrategyKey = tuple[
    str,
    SearchBatchBuilder,
    SearchProposalSelector,
]

_PREPARED_PROOF = object()


@dataclass(frozen=True, slots=True)
class PreparedEvaluatedSearch:
    """Validated request/batch state reusable across exact backends."""

    request: SearchRequest
    batch: CandidateEvaluationBatch
    _proof: object = field(repr=False)
    _strategy_key: SearchStrategyKey = field(repr=False)

    def for_strategy(
        self,
        strategy_key: SearchStrategyKey,
    ) -> tuple[SearchRequest, CandidateEvaluationBatch]:
        """Return state only to the exact strategy that prepared it.

        Returns:
            Immutable validated request and candidate batch.

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
        return (self.request, self.batch)


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
        *,
        batch_builder: SearchBatchBuilder,
        proposal_selector: SearchProposalSelector,
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
        self._batch_builder = batch_builder
        self._proposal_selector = proposal_selector
        self._strategy_key: SearchStrategyKey = (
            algorithm_id,
            batch_builder,
            proposal_selector,
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
        request, batch = self._prepared(prepared)
        return self._search_validated(request, batch)

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
        request, batch = recorder.measure(
            "prepared_validation_ns",
            lambda: self._prepared(prepared),
        )
        capability = self.capability()
        evidence = recorder.measure(
            "backend_evaluation_ns",
            lambda: self._evaluated(batch, capability),
        )
        proposals = recorder.measure(
            "proposal_selection_ns",
            lambda: self._selected(request, batch, evidence),
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
    ) -> tuple[SearchRequest, CandidateEvaluationBatch]:
        return prepared.for_strategy(self._strategy_key)

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
    ) -> tuple[CandidateProposal, ...]:
        proposals = self._proposal_selector(request, batch, evidence)
        _validate_proposal_membership(proposals, batch)
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


def _validate_proposal_membership(
    proposals: tuple[CandidateProposal, ...],
    batch: CandidateEvaluationBatch,
) -> None:
    candidates = {item.logical_id: item.payload for item in batch.items}
    for proposal in proposals:
        payload = candidates.get(proposal.logical_id)
        if payload is None or payload != proposal.payload:
            message = (
                "evaluated search proposal was not in evaluated candidate batch"
            )
            raise InvalidAcceleratorWorkError(message)
