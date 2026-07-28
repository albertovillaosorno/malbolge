# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Validated dynamic consumer-domain contract for compatible generation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import sys
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import ModuleType

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.behavior_programs import BehaviorPrograms
    from algorithms.diff.mapped import MappedView
    from algorithms.diff.probe_exec import ProbeRunContext
    from algorithms.diff.provenance import SourcePinEvidence


class DomainContractError(ValueError):
    """Invalid compatible consumer-module contract."""


@dataclass(frozen=True, slots=True)
class CompatibleDomain:
    """Callable hooks required by generic compatible authoring."""

    validate_source_provenance: Callable[[Path], SourcePinEvidence]
    validate_authoring_oracle: Callable[[Path], None]
    build_identity_tree: Callable[[Path], IdentityTree]
    map_compatible_file: Callable[[str, bytes], MappedView | None]
    build_behavior_programs: Callable[[], BehaviorPrograms]
    build_behavior_probe_context: Callable[[Path, Path], ProbeRunContext]


def _module_name(path: Path) -> str:
    digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    return f"_malbolge_diff_domain_{digest}"


def _load_module(path: Path) -> ModuleType:
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        message = f"compatible domain module is not a regular file: {path}"
        raise DomainContractError(message)
    name = _module_name(resolved)
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        message = f"cannot load compatible domain module: {resolved}"
        raise DomainContractError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _callable(module: ModuleType, name: str) -> Callable[..., object]:
    value = getattr(module, name, None)
    if not callable(value):
        message = f"compatible domain module requires callable {name!r}"
        raise DomainContractError(message)
    return cast("Callable[..., object]", value)


def load_compatible_domain(path: Path) -> CompatibleDomain:
    """Load and validate the trusted local consumer module used for authoring.

    Returns:
        Explicit compatible-domain hook bundle.

    """
    module = _load_module(path)
    return CompatibleDomain(
        validate_source_provenance=cast(
            "Callable[[Path], SourcePinEvidence]",
            _callable(module, "validate_source_provenance"),
        ),
        validate_authoring_oracle=cast(
            "Callable[[Path], None]",
            _callable(module, "validate_authoring_oracle"),
        ),
        build_identity_tree=cast(
            "Callable[[Path], IdentityTree]",
            _callable(module, "build_identity_tree"),
        ),
        map_compatible_file=cast(
            "Callable[[str, bytes], MappedView | None]",
            _callable(module, "map_compatible_file"),
        ),
        build_behavior_programs=cast(
            "Callable[[], BehaviorPrograms]",
            _callable(module, "build_behavior_programs"),
        ),
        build_behavior_probe_context=cast(
            "Callable[[Path, Path], ProbeRunContext]",
            _callable(module, "build_behavior_probe_context"),
        ),
    )
