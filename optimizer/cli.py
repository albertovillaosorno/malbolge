# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Command-line runner for reproducible hardware-neutral search execution."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorError
from accelerator.search_config import load_search_configuration
from accelerator.search_selection import CPU_REFERENCE_BACKEND
from accelerator.search_selection import SearchAdapterBinding
from accelerator.search_selection import SearchSelectionError
from accelerator.search_selection import resolve_search_execution
from accelerator.work_ports import SearchExecutionAdapter
from accelerator.work_ports import SearchRequest
from optimizer.enumerative import ENUMERATIVE_ALGORITHM_ID
from optimizer.enumerative import cpu_enumerative_adapter
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

    from accelerator.search_config import SearchConfiguration
    from accelerator.search_selection import SearchExecutionRecord
    from accelerator.search_selection import SearchSelection
    from accelerator.work_ports import SearchResult

CUDA_BACKEND = "cuda"
CONFIGURATION_ERROR = 2
OUTPUT_SCHEMA_VERSION = 1
PROPOSAL_TRUST = "untrusted"

type CudaAdapterFactory = Callable[[], CudaExactPrimitiveAdapter]


class SearchCliError(ValueError):
    """Search runner input, configuration, or registry state is invalid."""


@dataclass(frozen=True, slots=True)
class SearchRunOptions:
    """Deterministic request values plus optional selection overrides."""

    evaluation_budget: int
    seed: int = 0
    algorithm_override: str | None = None
    backend_override: str | None = None


class _Arguments(argparse.Namespace):
    algorithm: str | None
    backend: str | None
    budget: int
    config: Path
    problem: Path
    seed: int

    def __init__(self) -> None:
        """Initialize typed defaults before argparse mutates this namespace."""
        super().__init__()
        self.algorithm = None
        self.backend = None
        self.budget = 0
        self.config = Path()
        self.problem = Path()
        self.seed = 0


@final
class _UnavailableSearchAdapter(SearchExecutionAdapter):
    """Optional backend registration that triggers safe CPU fallback."""

    def __init__(self, backend_id: str, error: AcceleratorError) -> None:
        """Preserve requested backend identity and its setup failure."""
        self._capability = AcceleratorCapability(
            backend_id=backend_id,
            device_arch="unavailable",
            device_name="unavailable",
        )
        self._error = error

    @override
    def capability(self) -> AcceleratorCapability:
        """Return configured optional backend identity.

        Returns:
            Stable unavailable capability used only for registry resolution.

        """
        return self._capability

    @override
    def search(self, request: SearchRequest) -> SearchResult:
        """Raise retained setup failure after validating the search request."""
        _ = request.validated()
        raise self._error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one versioned Malbolge search configuration and emit "
            "reproducible untrusted proposal evidence as JSON."
        )
    )
    _ = parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Search Configuration v1 TOML file.",
    )
    _ = parser.add_argument(
        "--problem",
        type=Path,
        required=True,
        help="Canonical binary problem payload for the selected algorithm.",
    )
    _ = parser.add_argument(
        "--budget",
        type=int,
        required=True,
        help="Positive u64 candidate-evaluation budget.",
    )
    _ = parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic u64 search seed (default: 0).",
    )
    _ = parser.add_argument(
        "--algorithm",
        help="Explicit search algorithm override.",
    )
    _ = parser.add_argument(
        "--backend",
        help="Explicit search backend override.",
    )
    return parser


def _parse_arguments(argv: Sequence[str] | None) -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(argv, namespace=arguments)
    return arguments


def run_configured_search(
    configuration: SearchConfiguration,
    problem: bytes,
    options: SearchRunOptions,
    *,
    cuda_factory: CudaAdapterFactory = CudaExactPrimitiveAdapter,
) -> SearchExecutionRecord:
    """Run configured search through registered CPU/optional CUDA adapters.

    Returns:
        Search result plus configured-versus-actual execution identity.

    Raises:
        SearchCliError: If the selected algorithm/backend is unsupported.

    """
    selection = configuration.resolved(
        algorithm_override=options.algorithm_override,
        backend_override=options.backend_override,
    )
    request = SearchRequest(
        algorithm_id=selection.algorithm_id,
        evaluation_budget=options.evaluation_budget,
        problem=problem,
        seed=options.seed,
    ).validated()
    with ExitStack() as stack:
        bindings = list(_cpu_bindings())
        _extend_optional_bindings(
            bindings,
            selection,
            stack,
            cuda_factory=cuda_factory,
        )
        try:
            plan = resolve_search_execution(bindings, selection)
        except SearchSelectionError as error:
            raise SearchCliError(str(error)) from error
        return plan.run(request)


def search_record_json(
    configuration: SearchConfiguration,
    problem: bytes,
    record: SearchExecutionRecord,
) -> str:
    """Serialize one search record as deterministic JSON evidence.

    Returns:
        Stable JSON containing configuration, execution identity, and proposals.

    """
    identity = record.identity
    payload = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "configuration_source": configuration.source,
        "problem_sha256": sha256(problem).hexdigest(),
        "proposal_trust": PROPOSAL_TRUST,
        "algorithm_id": identity.algorithm_id,
        "configured_backend_id": identity.configured_backend_id,
        "actual_backend_id": identity.actual_backend_id,
        "device_arch": identity.device_arch,
        "device_name": identity.device_name,
        "evaluation_budget": identity.evaluation_budget,
        "seed": identity.seed,
        "proposals": [
            {
                "logical_id": proposal.logical_id,
                "payload_hex": proposal.payload.hex(),
            }
            for proposal in record.result.proposals
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _cpu_bindings() -> tuple[SearchAdapterBinding, ...]:
    return (
        SearchAdapterBinding(
            adapter=cpu_enumerative_adapter(),
            algorithm_id=ENUMERATIVE_ALGORITHM_ID,
        ),
        SearchAdapterBinding(
            adapter=cpu_rotate_target_search_adapter(),
            algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        ),
    )


def _extend_optional_bindings(
    bindings: list[SearchAdapterBinding],
    selection: SearchSelection,
    stack: ExitStack,
    *,
    cuda_factory: CudaAdapterFactory,
) -> None:
    if selection.backend_id == CPU_REFERENCE_BACKEND:
        return
    if (
        selection.algorithm_id != ROTATE_TARGET_ALGORITHM_ID
        or selection.backend_id != CUDA_BACKEND
    ):
        return
    try:
        cuda = stack.enter_context(cuda_factory())
        adapter: SearchExecutionAdapter = rotate_target_search_adapter(cuda)
    except AcceleratorError as error:
        adapter = _UnavailableSearchAdapter(CUDA_BACKEND, error)
    bindings.append(
        SearchAdapterBinding(
            adapter=adapter,
            algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        )
    )


def _write_error(error: object) -> None:
    _ = sys.stderr.write(f"error: {error}\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run configured search and write deterministic JSON proposal evidence.

    Returns:
        Zero on successful search execution, otherwise a configuration error.

    """
    arguments = _parse_arguments(argv)
    try:
        configuration = load_search_configuration(arguments.config)
        problem = arguments.problem.read_bytes()
        options = SearchRunOptions(
            algorithm_override=arguments.algorithm,
            backend_override=arguments.backend,
            evaluation_budget=arguments.budget,
            seed=arguments.seed,
        )
        record = run_configured_search(configuration, problem, options)
        rendered = search_record_json(configuration, problem, record)
    except (AcceleratorError, OSError, ValueError) as error:
        _write_error(error)
        return CONFIGURATION_ERROR
    _ = sys.stdout.write(f"{rendered}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
