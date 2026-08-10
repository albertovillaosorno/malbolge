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
#   - Validated dynamic consumer-domain contract for diff generation.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validated dynamic consumer-domain contract for diff generation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
from stat import S_ISLNK
from stat import S_ISREG
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
    """Invalid diff consumer-module contract."""


@dataclass(frozen=True, slots=True)
class DiffDomain:
    """Callable hooks required by generic domain-aware authoring."""

    validate_source_provenance: Callable[[Path], SourcePinEvidence]
    validate_authoring_oracle: Callable[[Path], None]
    build_identity_tree: Callable[[Path], IdentityTree]
    map_compatible_file: Callable[[str, bytes], MappedView | None]
    build_behavior_programs: Callable[[], BehaviorPrograms]
    build_behavior_probe_context: Callable[[Path, Path], ProbeRunContext]


def _module_name(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:16]
    return f"_malbolge_diff_domain_{digest}"


def _regular_module_path(path: Path) -> Path:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        message = f"diff domain module is not a regular file: {path}"
        raise DomainContractError(message) from error
    except OSError as error:
        message = f"diff domain module status failed: {path}: {error}"
        raise DomainContractError(message) from error
    if S_ISLNK(mode) or path.is_junction() or not S_ISREG(mode):
        message = f"diff domain module is not a regular file: {path}"
        raise DomainContractError(message)
    try:
        return path.resolve(strict=True)
    except OSError as error:
        message = f"diff domain module resolution failed: {path}: {error}"
        raise DomainContractError(message) from error


def _load_module(path: Path) -> ModuleType:
    resolved = _regular_module_path(path)
    name = _module_name(resolved)
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        message = f"cannot load diff domain module: {resolved}"
        raise DomainContractError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        _ = sys.modules.pop(name, None)
        raise
    return module


def _callable(module: ModuleType, name: str) -> Callable[..., object]:
    value = getattr(module, name, None)
    if not callable(value):
        message = f"diff domain module requires callable {name!r}"
        raise DomainContractError(message)
    return value


def load_diff_domain(path: Path) -> DiffDomain:
    """Load and validate the trusted local consumer module used for authoring.

    Returns:
        Explicit diff-domain hook bundle.

    """
    module = _load_module(path)
    return DiffDomain(
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
