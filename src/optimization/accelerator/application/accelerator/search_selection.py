# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
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
#   - Deterministic search-algorithm and accelerator-backend selection.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Deterministic search-algorithm and accelerator-backend selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from accelerator.work_ports import execute_search

if TYPE_CHECKING:
    from collections.abc import Iterable

    from accelerator.work_ports import SearchExecutionAdapter
    from accelerator.work_ports import SearchRequest
    from accelerator.work_ports import SearchResult

CPU_REFERENCE_BACKEND = "cpu-reference"


class SearchSelectionError(ValueError):
    """Search algorithm/backend configuration is incomplete or unsupported."""


@dataclass(frozen=True, slots=True)
class SearchSelection:
    """Independent algorithm and preferred-backend configuration."""

    algorithm_id: str
    backend_id: str

    def validated(self) -> SearchSelection:
        """Validate nonempty independent selection identities.

        Returns:
            This immutable selection after validation succeeds.

        """
        _require_identity(self.algorithm_id, "search algorithm ID")
        _require_identity(self.backend_id, "search backend ID")
        return self


@dataclass(frozen=True, slots=True)
class SearchAdapterBinding:
    """One algorithm/backend implementation binding in the runtime registry."""

    adapter: SearchExecutionAdapter
    algorithm_id: str

    def key(self) -> tuple[str, str]:
        """Return deterministic registry identity for this binding.

        Returns:
            Algorithm ID plus backend capability ID.

        """
        _require_identity(self.algorithm_id, "search algorithm ID")
        backend_id = self.adapter.capability().backend_id
        _require_identity(backend_id, "search backend ID")
        return (self.algorithm_id, backend_id)


@dataclass(frozen=True, slots=True)
class SearchRunIdentity:
    """Exact configured and actual identity for one search execution."""

    actual_backend_id: str
    algorithm_id: str
    configured_backend_id: str
    device_arch: str
    device_name: str
    evaluation_budget: int
    seed: int


@dataclass(frozen=True, slots=True)
class SearchExecutionRecord:
    """Search result paired with reproducible execution identity."""

    identity: SearchRunIdentity
    result: SearchResult


@dataclass(frozen=True, slots=True)
class SearchExecutionPlan:
    """Resolved CPU reference plus optional preferred search capacity."""

    preferred: SearchExecutionAdapter | None
    reference: SearchExecutionAdapter
    selection: SearchSelection

    def run(self, request: SearchRequest) -> SearchExecutionRecord:
        """Execute one request through this resolved selection.

        Returns:
            Untrusted proposals plus exact configured/actual execution identity.

        Raises:
            SearchSelectionError: If request and plan algorithm IDs differ.

        """
        validated = request.validated()
        if validated.algorithm_id != self.selection.algorithm_id:
            message = (
                "search request algorithm does not match resolved selection"
            )
            raise SearchSelectionError(message)
        result = execute_search(validated, self.reference, self.preferred)
        return SearchExecutionRecord(
            identity=_run_identity(self.selection, validated, result),
            result=result,
        )


def resolve_search_execution(
    bindings: Iterable[SearchAdapterBinding],
    selection: SearchSelection,
    *,
    algorithm_override: str | None = None,
    backend_override: str | None = None,
) -> SearchExecutionPlan:
    """Resolve deterministic algorithm/backend selection with overrides.

    Returns:
        A plan with mandatory CPU reference and optional preferred backend.

    """
    effective = _effective_selection(
        selection,
        algorithm_override=algorithm_override,
        backend_override=backend_override,
    )
    registry = _binding_registry(bindings)
    reference = _required_binding(
        registry,
        (effective.algorithm_id, CPU_REFERENCE_BACKEND),
    )
    preferred = _preferred_binding(registry, effective)
    return SearchExecutionPlan(
        preferred=preferred,
        reference=reference,
        selection=effective,
    )


def _binding_registry(
    bindings: Iterable[SearchAdapterBinding],
) -> dict[tuple[str, str], SearchExecutionAdapter]:
    registry: dict[tuple[str, str], SearchExecutionAdapter] = {}
    for binding in bindings:
        key = binding.key()
        if key in registry:
            message = f"duplicate search adapter binding: {key[0]} / {key[1]}"
            raise SearchSelectionError(message)
        registry[key] = binding.adapter
    return registry


def _effective_selection(
    selection: SearchSelection,
    *,
    algorithm_override: str | None,
    backend_override: str | None,
) -> SearchSelection:
    validated = selection.validated()
    algorithm_id = (
        validated.algorithm_id
        if algorithm_override is None
        else algorithm_override
    )
    backend_id = (
        validated.backend_id if backend_override is None else backend_override
    )
    return SearchSelection(
        algorithm_id=algorithm_id,
        backend_id=backend_id,
    ).validated()


def _preferred_binding(
    registry: dict[tuple[str, str], SearchExecutionAdapter],
    selection: SearchSelection,
) -> SearchExecutionAdapter | None:
    if selection.backend_id == CPU_REFERENCE_BACKEND:
        return None
    return _required_binding(
        registry,
        (selection.algorithm_id, selection.backend_id),
    )


def _required_binding(
    registry: dict[tuple[str, str], SearchExecutionAdapter],
    key: tuple[str, str],
) -> SearchExecutionAdapter:
    adapter = registry.get(key)
    if adapter is None:
        message = f"unsupported search algorithm/backend: {key[0]} / {key[1]}"
        raise SearchSelectionError(message)
    return adapter


def _require_identity(value: str, label: str) -> None:
    if not value:
        message = f"{label} must not be empty"
        raise SearchSelectionError(message)


def _run_identity(
    selection: SearchSelection,
    request: SearchRequest,
    result: SearchResult,
) -> SearchRunIdentity:
    capability = result.capability
    return SearchRunIdentity(
        actual_backend_id=capability.backend_id,
        algorithm_id=request.algorithm_id,
        configured_backend_id=selection.backend_id,
        device_arch=capability.device_arch,
        device_name=capability.device_name,
        evaluation_budget=request.evaluation_budget,
        seed=request.seed,
    )
