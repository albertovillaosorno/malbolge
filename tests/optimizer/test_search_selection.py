# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Selection tests for independent search algorithms and hardware backends."""

from __future__ import annotations

from typing import final
from typing import override

from accelerator.cpu import CpuSearchExecutionAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.search_selection import CPU_REFERENCE_BACKEND
from accelerator.search_selection import SearchAdapterBinding
from accelerator.search_selection import SearchSelection
from accelerator.search_selection import SearchSelectionError
from accelerator.search_selection import resolve_search_execution
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import SearchResult

ALPHA_ALGORITHM = "alpha"
BETA_ALGORITHM = "beta"
ALPHA_CPU_PAYLOAD = b"problem-alpha"
BETA_CPU_PAYLOAD = b"problem-beta"
GPU_PAYLOAD = b"problem-gpu"
GPU_BACKEND = "test-gpu"
GPU_CAPABILITY = AcceleratorCapability(
    backend_id=GPU_BACKEND,
    device_arch="test-gpu-arch",
    device_name="test-gpu-device",
)


def _alpha_search(request: SearchRequest) -> tuple[CandidateProposal, ...]:
    return (
        CandidateProposal(
            logical_id=f"alpha-{request.seed}",
            payload=request.problem + b"-alpha",
        ),
    )


def _beta_search(request: SearchRequest) -> tuple[CandidateProposal, ...]:
    return (
        CandidateProposal(
            logical_id=f"beta-{request.seed}",
            payload=request.problem + b"-beta",
        ),
    )


@final
class _GpuSearchAdapter(SearchExecutionAdapter):
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    @override
    def capability(self) -> AcceleratorCapability:
        return GPU_CAPABILITY

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        validated = request.validated()
        if self._fail:
            message = "optional GPU search failed"
            raise AcceleratorExecutionError(message)
        proposals = (
            CandidateProposal(
                logical_id=f"gpu-{validated.seed}",
                payload=validated.problem + b"-gpu",
            ),
        )
        return SearchResult(
            algorithm_id=validated.algorithm_id,
            capability=GPU_CAPABILITY,
            proposals=proposals,
            seed=validated.seed,
        )


def _bindings(*, failing_gpu: bool = False) -> tuple[SearchAdapterBinding, ...]:
    return (
        SearchAdapterBinding(
            adapter=CpuSearchExecutionAdapter(ALPHA_ALGORITHM, _alpha_search),
            algorithm_id=ALPHA_ALGORITHM,
        ),
        SearchAdapterBinding(
            adapter=CpuSearchExecutionAdapter(BETA_ALGORITHM, _beta_search),
            algorithm_id=BETA_ALGORITHM,
        ),
        SearchAdapterBinding(
            adapter=_GpuSearchAdapter(fail=failing_gpu),
            algorithm_id=ALPHA_ALGORITHM,
        ),
    )


def _request(algorithm_id: str) -> SearchRequest:
    return SearchRequest(
        algorithm_id=algorithm_id,
        evaluation_budget=4,
        problem=b"problem",
        seed=23,
    )


def _expect_selection_error(message: str, action: object) -> None:
    if not callable(action):
        raise TypeError
    try:
        _ = action()
    except SearchSelectionError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


def test_algorithm_and_backend_are_selected_independently() -> None:
    """Algorithm and hardware selection remain independent."""
    plan = resolve_search_execution(
        _bindings(),
        SearchSelection(algorithm_id=ALPHA_ALGORITHM, backend_id=GPU_BACKEND),
    )

    record = plan.run(_request(ALPHA_ALGORITHM))

    assert record.identity.algorithm_id == ALPHA_ALGORITHM
    assert record.identity.configured_backend_id == GPU_BACKEND
    assert record.identity.actual_backend_id == GPU_BACKEND
    assert record.result.proposals[0].payload == GPU_PAYLOAD


def test_backend_override_selects_cpu_reference() -> None:
    """A backend override can disable optional acceleration."""
    plan = resolve_search_execution(
        _bindings(),
        SearchSelection(algorithm_id=ALPHA_ALGORITHM, backend_id=GPU_BACKEND),
        backend_override=CPU_REFERENCE_BACKEND,
    )

    record = plan.run(_request(ALPHA_ALGORITHM))

    assert record.identity.configured_backend_id == CPU_REFERENCE_BACKEND
    assert record.identity.actual_backend_id == CPU_REFERENCE_BACKEND
    assert record.result.proposals[0].payload == ALPHA_CPU_PAYLOAD


def test_algorithm_override_changes_strategy_without_backend_recompile() -> (
    None
):
    """Algorithm override resolves another registered CPU strategy."""
    plan = resolve_search_execution(
        _bindings(),
        SearchSelection(algorithm_id=ALPHA_ALGORITHM, backend_id=GPU_BACKEND),
        algorithm_override=BETA_ALGORITHM,
        backend_override=CPU_REFERENCE_BACKEND,
    )

    record = plan.run(_request(BETA_ALGORITHM))

    assert record.identity.algorithm_id == BETA_ALGORITHM
    assert record.result.proposals[0].payload == BETA_CPU_PAYLOAD


def test_unsupported_algorithm_backend_combination_fails_explicitly() -> None:
    """Selection never silently substitutes an unregistered hardware pairing."""
    _expect_selection_error(
        "unsupported search algorithm/backend: beta / test-gpu",
        lambda: resolve_search_execution(
            _bindings(),
            SearchSelection(
                algorithm_id=BETA_ALGORITHM, backend_id=GPU_BACKEND
            ),
        ),
    )


def test_duplicate_registry_binding_fails_closed() -> None:
    """Registry identity cannot be ambiguous for one algorithm/backend pair."""
    duplicate = SearchAdapterBinding(
        adapter=CpuSearchExecutionAdapter(ALPHA_ALGORITHM, _alpha_search),
        algorithm_id=ALPHA_ALGORITHM,
    )
    bindings = (*_bindings(), duplicate)

    _expect_selection_error(
        "duplicate search adapter binding: alpha / cpu-reference",
        lambda: resolve_search_execution(
            bindings,
            SearchSelection(
                algorithm_id=ALPHA_ALGORITHM,
                backend_id=CPU_REFERENCE_BACKEND,
            ),
        ),
    )


def test_optional_backend_fallback_records_actual_cpu_execution() -> None:
    """Execution identity records actual CPU fallback."""
    plan = resolve_search_execution(
        _bindings(failing_gpu=True),
        SearchSelection(algorithm_id=ALPHA_ALGORITHM, backend_id=GPU_BACKEND),
    )

    record = plan.run(_request(ALPHA_ALGORITHM))

    assert record.identity.configured_backend_id == GPU_BACKEND
    assert record.identity.actual_backend_id == CPU_REFERENCE_BACKEND
    assert record.result.proposals[0].payload == ALPHA_CPU_PAYLOAD


def test_request_algorithm_must_match_resolved_plan() -> None:
    """A resolved backend cannot execute a request for another algorithm."""
    plan = resolve_search_execution(
        _bindings(),
        SearchSelection(
            algorithm_id=ALPHA_ALGORITHM,
            backend_id=CPU_REFERENCE_BACKEND,
        ),
    )

    _expect_selection_error(
        "search request algorithm does not match resolved selection",
        lambda: plan.run(_request(BETA_ALGORITHM)),
    )


def test_empty_override_fails_instead_of_reusing_default() -> None:
    """An explicitly empty override is invalid configuration."""
    _expect_selection_error(
        "search backend ID must not be empty",
        lambda: resolve_search_execution(
            _bindings(),
            SearchSelection(
                algorithm_id=ALPHA_ALGORITHM,
                backend_id=GPU_BACKEND,
            ),
            backend_override="",
        ),
    )
